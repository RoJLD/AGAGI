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

# Baseline dans tools/ (tracké) et non results/ (gitignored) -> la dette gelée est versionnée/portable.
_BASELINE = os.path.join(_ROOT, "tools", "record_link_baseline.json")


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

    orphans, gate_unlinked = [], []
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

    return {"orphans": orphans, "collisions": collisions, "gate_unlinked": gate_unlinked,
            "n_records": len(records)}


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
                   "_note": "Dette légataire gelée. Le ratchet interdit tout NOUVEL orphelin/collision."}
        os.makedirs(os.path.dirname(_BASELINE), exist_ok=True)
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"baseline gelé : {n_orph} orphelins, {n_coll} collisions (dette légataire).")
        return 0

    if args.report:
        print(f"records={st['n_records']} orphelins={n_orph} collisions={n_coll} "
              f"gate_non_raccordés={len(st['gate_unlinked'])}")
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

    # scope optionnel aux fichiers du commit courant (hook pre-commit) : ne bloque pas sur le travail // non-committé
    if args.only is not None:
        only = {f.replace(os.sep, "/") for f in args.only}
        new_orph = [o for o in new_orph if o["file"] in only]
        new_coll = [c for c in new_coll if any(f in only for f in c["files"])]

    if not new_orph and not new_coll:
        print(f"OK : {n_orph} orphelins / {n_coll} collisions, tous légataires (baseline). Aucun nouveau.")
        return 0

    print("ÉCHEC : nouveaux orphelins/collisions détectés (raccorde-les à une porte / dé-duplique l'id) :")
    for o in new_orph:
        print(f"  [NOUVEL ORPHELIN] {o['id']}  ({o['file']}) — ajoute frontmatter gate:/tests:[SDR-Gx] ou adopt REF")
    for c in new_coll:
        print(f"  [NOUVELLE COLLISION] {c['id']}  ->  {', '.join(c['files'])}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
