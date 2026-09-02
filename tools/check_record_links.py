"""Garde-fou d'hygiène du graphe de records : ORPHELINS + COLLISIONS d'ID.

`consolidate_records.py` ne détecte ni les orphelins (records sans aucune arête ni porte) ni les collisions
d'ID (deux fichiers → même id, le dict `by_id` en écrase un silencieusement). Cet outil séparé (non-invasif :
il réutilise le parseur canonique) les détecte et applique une RÈGLE À CLIQUET (ratchet) : les orphelins/
collisions LÉGATAIRES sont tolérés via un baseline gelé, mais AUCUN NOUVEAU ne doit apparaître.

Un record est RACCORDÉ s'il est un ancrage (SDR/REF), OU porte une `gate:`, OU possède au moins une arête
(motivates/triggers/tests/adopt_for/...). Un EDR/ADR ne satisfaisant rien de tout ça est ORPHELIN.

Usage :
  python tools/check_record_links.py                 # ratchet : échoue (exit 1) sur tout NOUVEL orphelin/collision
  python tools/check_record_links.py --report        # état complet (liste tout), exit 0
  python tools/check_record_links.py --update-baseline  # gèle l'état courant comme référence légataire
"""
import os
import re
import sys
import json
import argparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.consolidate_records import scan_records, build_graph, _GATES

# Ancres de raccordement tolérées : les 5 portes G0-G4 + « foundational » (infra/NAS/méthodo qui n'appartient
# légitimement à aucune porte — évite de forcer un rattachement artificiel lors de la dé-orphanisation légataire).
_ANCHORS = set(_GATES) | {"foundational"}
# C3 (2026-09-02) : mismatch gate<->tests. `roadmap_state` compte un EDR pour une porte si gate==g
# OU SDR-Gg dans tests -> un mismatch fait apparaitre le MEME record dans DEUX portes. Semantique
# tranchee : gate dans _GATES ET tests declare des SDR-Gy ET gate absent des declares ; un gate sans
# aucun tests = dette `gate_unlinked` (autre chantier) ; `foundational` n'est PAS une porte -> jamais
# un mismatch (contre-exemple gele). Reponse connue confrontee AVANT de croire le cliquet :
# l'arbre PRE-retaggage portait exactement {EDR-S2-007 (G4/[SDR-G0]), EDR-S2-008 (G2/[SDR-G0])} --
# le draft du panel n'en voyait qu'un, le refutateur a trouve le second (F1).
_SDR_GATE = re.compile(r"^SDR-(G\d)$")

# Baseline dans tools/ (tracké) et non results/ (gitignored) -> la dette gelée est versionnée/portable.
_BASELINE = os.path.join(_ROOT, "tools", "record_link_baseline.json")


# --- FERMETURE DU SILENCE (2026-09-01) -------------------------------------------------------------
# `parse_record` jette EN SILENCE toute clé de frontmatter absente de `_LIST_KEYS` (branche
# `elif k in rec`). C'est ce silence qui a laissé **122 arêtes déclarées hors du graphe**, dont TOUTES
# les arêtes de rétractation — un graphe de records qui ne lit pas ses rétractations ne peut pas
# signaler une conclusion périmée, ce pour quoi il existe.
#
# Deux corruptions silencieuses, distinctes, détectées séparément :
#   * CLÉ NON LUE — un auteur déclare `adopts:` (que CLAUDE.md prescrit !) et rien ne la lit.
#   * VALEUR SCALAIRE — `supersedes_mechanism_of: EDR-162` au lieu de `[EDR-162]`. Le code itère la
#     CHAÎNE, donc produit une arête PAR CARACTÈRE ('E','D','R','-','1','6','2'). Trouvé sur EDR-164 à
#     la seconde où les clés manquantes ont été branchées.
_ID_LIKE = re.compile(r"^(EDR|SDR|ADR|REF)-[A-Za-z0-9\-]+$")


def edge_key_silences(root: str = _ROOT) -> dict:
    """{'non_lues': [(fichier, clé)], 'scalaires': [(fichier, clé, valeur)]}."""
    from tools.consolidate_records import _LIST_KEYS, _empty_record
    # ⚠️ Les champs SCALAIRES du schéma (`id`, `gate`, `verdict`, …) ont souvent la FORME d'un id de
    # record — `id: SDR-G0` en est un. Les exclure via le schéma DÉJÀ DÉCLARÉ plutôt qu'une liste ad hoc :
    # une liste écrite à la main se serait désynchronisée du schéma à la première évolution.
    _SCALAIRES_DU_SCHEMA = {k for k in _empty_record("") if k not in _LIST_KEYS}
    non_lues, scalaires = [], []
    for sub in ("docs/SDR", "docs/ADR", "docs/EDR", "docs/REF"):
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            path = os.path.join(d, name)
            try:
                txt = open(path, encoding="utf-8", errors="ignore").read(6000)
            except OSError:
                continue
            if not txt.startswith("---"):
                continue
            fm = txt.split("---", 2)[1]
            rel = os.path.join(sub, name).replace(os.sep, "/")
            for m in re.finditer(r"^([a-z_]+):[ \t]*(\S.*)$", fm, re.M):
                key, raw = m.group(1), m.group(2).strip()
                ressemble = raw.startswith("[") and _ID_LIKE.match(raw.strip("[]").split(",")[0].strip())
                if key in _LIST_KEYS:
                    # déclarée et lue : reste à vérifier qu'elle est bien une LISTE
                    if _ID_LIKE.match(raw):
                        scalaires.append((rel, key, raw))
                elif key in _SCALAIRES_DU_SCHEMA:
                    continue                       # champ scalaire connu du schéma, pas une arête
                elif ressemble or _ID_LIKE.match(raw):
                    non_lues.append((rel, key))
    return {"non_lues": non_lues, "scalaires": scalaires}


def analyze(root: str = _ROOT) -> dict:
    """Renvoie {'orphans': [{id,file}], 'collisions': [{id,files}], 'gate_unlinked': [{id,file}]}."""
    records = scan_records(root)
    edges = build_graph(records)["edges"]
    edge_ids = {e["from"] for e in edges} | {e["to"] for e in edges}

    # collisions : un même id porté par plusieurs fichiers
    by_id: dict[str, list[str]] = {}
    for r in records:
        by_id.setdefault(r["id"], []).append(r["file"])
    collisions = [{"id": i, "files": sorted(fs)} for i, fs in sorted(by_id.items()) if len(fs) > 1]

    orphans, gate_unlinked, gate_tests_mismatch = [], [], []
    for r in records:
        if r["type"] not in ("EDR", "ADR"):          # SDR/REF = ancrages structurels
            continue
        has_gate = r.get("gate") in _ANCHORS
        has_edge = r["id"] in edge_ids
        if not has_gate and not has_edge:
            orphans.append({"id": r["id"], "file": r["file"]})
        # cible plus stricte (raccord à une PORTE) : ni gate, ni tests vers une SDR
        tests_sdr = any(str(t).startswith("SDR-") for t in (r.get("tests") or []))
        if r["type"] == "EDR" and not has_gate and not tests_sdr:
            gate_unlinked.append({"id": r["id"], "file": r["file"]})
        # C3 : mismatch gate<->tests (EDR seulement -- N6 du refutateur)
        if r["type"] == "EDR":
            declared = [m.group(1) for t in (r.get("tests") or [])
                        if (m := _SDR_GATE.match(str(t)))]
            if r.get("gate") in _GATES and declared and r["gate"] not in declared:
                gate_tests_mismatch.append({"id": r["id"], "file": r["file"],
                                            "gate": r["gate"], "tests_gates": declared})

    return {"orphans": orphans, "collisions": collisions, "gate_unlinked": gate_unlinked,
            "gate_tests_mismatch": gate_tests_mismatch, "n_records": len(records)}


def _load_baseline() -> dict:
    if os.path.exists(_BASELINE):
        with open(_BASELINE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"orphan_files": [], "collision_ids": []}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Garde-fou orphelins/collisions du graphe de records.")
    ap.add_argument("--report", action="store_true", help="Affiche l'état complet et sort (exit 0).")
    ap.add_argument("--update-baseline", action="store_true", help="Gèle l'état courant comme référence.")
    ap.add_argument("--only", nargs="*", default=None,
                    help="Ratchet scopé : n'échoue que sur les orphelins/collisions touchant CES fichiers "
                         "(chemins relatifs au repo). Utilisé par le hook pre-commit (fichiers stagés) pour "
                         "ne pas bloquer un commit à cause du travail non-committé d'une session //.")
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)

    st = analyze(args.root)
    n_orph, n_coll = len(st["orphans"]), len(st["collisions"])

    if args.update_baseline:
        payload = {"orphan_files": sorted(o["file"] for o in st["orphans"]),
                   "collision_ids": sorted(c["id"] for c in st["collisions"]),
                   "mismatch_files": sorted(m["file"] for m in st["gate_tests_mismatch"]),
                   "_note": "Dette légataire gelée. Le ratchet interdit tout NOUVEL orphelin/collision."}
        os.makedirs(os.path.dirname(_BASELINE), exist_ok=True)
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"baseline gelé : {n_orph} orphelins, {n_coll} collisions (dette légataire).")
        return 0

    # ⚠️ SILENCES D'ARÊTES — vérifiés à CHAQUE appel, jamais gelés dans un baseline. Une arête
    # déclarée mais non lue n'est pas de la « dette légataire tolérable » : c'est une information que
    # le graphe possède et n'utilise pas. 122 arêtes étaient dans ce cas jusqu'au 2026-09-01, dont
    # TOUTES les rétractations.
    sil = edge_key_silences()
    if sil["non_lues"] or sil["scalaires"]:
        print("ÉCHEC : le graphe IGNORE des arêtes pourtant déclarées." + chr(10))
        for f, k in sil["non_lues"]:
            print(f"  [clé jamais lue] {k}  ({f})  -> l'ajouter à `_LIST_KEYS` et `_REL`, "
                  f"ou renommer la clé")
        for f, k, v in sil["scalaires"]:
            print(f"  [valeur scalaire] {k}: {v}  ({f})  -> mettre des crochets : [{v}]. "
                  f"Sans eux, la CHAÎNE est itérée et produit une arête PAR CARACTÈRE.")
        print(chr(10) + "Un graphe qui ne lit pas ses rétractations ne peut pas signaler une "
              "conclusion périmée.")
        return 1

    if args.report:
        print(f"records={st['n_records']} orphelins={n_orph} collisions={n_coll} "
              f"gate_non_raccordés={len(st['gate_unlinked'])} "
              f"mismatches_gate_tests={len(st['gate_tests_mismatch'])}")
        for m in st["gate_tests_mismatch"]:
            print(f"  [mismatch] {m['id']} gate: {m['gate']} vs tests: {m['tests_gates']}")
        for o in st["orphans"]:
            print(f"  [orphelin] {o['id']}  ({o['file']})")
        for c in st["collisions"]:
            print(f"  [collision] {c['id']}  ->  {', '.join(c['files'])}")
        return 0

    # mode ratchet : n'échoue que sur les NOUVEAUX (hors baseline gelé)
    base = _load_baseline()
    base_orph, base_coll = set(base.get("orphan_files", [])), set(base.get("collision_ids", []))
    new_orph = [o for o in st["orphans"] if o["file"] not in base_orph]
    new_coll = [c for c in st["collisions"] if c["id"] not in base_coll]
    base_mism = set(base.get("mismatch_files", []))
    new_mism = [m for m in st["gate_tests_mismatch"] if m["file"] not in base_mism]

    # scope optionnel aux fichiers du commit courant (hook pre-commit) : ne bloque pas sur le travail // non-committé
    if args.only is not None:
        only = {f.replace(os.sep, "/") for f in args.only}
        new_orph = [o for o in new_orph if o["file"] in only]
        new_coll = [c for c in new_coll if any(f in only for f in c["files"])]
        new_mism = [m for m in new_mism if m["file"] in only]

    if not new_orph and not new_coll and not new_mism:
        print(f"OK : {n_orph} orphelins / {n_coll} collisions / "
              f"{len(st['gate_tests_mismatch'])} mismatches gate<->tests, tous légataires (baseline). "
              f"Aucun nouveau.")
        return 0

    print("ÉCHEC : nouveaux orphelins/collisions détectés (raccorde-les à une porte / dé-duplique l'id) :")
    for o in new_orph:
        print(f"  [NOUVEL ORPHELIN] {o['id']}  ({o['file']}) — ajoute frontmatter gate:/tests:[SDR-Gx] ou adopt REF")
    for c in new_coll:
        print(f"  [NOUVELLE COLLISION] {c['id']}  ->  {', '.join(c['files'])}")
    for m in new_mism:
        print(f"  [NOUVEAU MISMATCH] {m['id']} gate: {m['gate']} mais tests: {m['tests_gates']} "
              f"-- aligne gate: ou tests: ({m['file']})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
