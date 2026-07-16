"""Cartographe — moisson déterministe de signaux sur le corpus de recherche AGAGI.

Lit le registre (docs/roadmap/SPECIALITES.md), les records (via consolidate),
la mémoire, et extrait des SIGNAUX (gaps, verdicts ouverts, territoires dormants,
termes-verrou, orphelins) dans un JSON reproductible. Pur : aucun LLM, aucun réseau.
La passe sémantique (interprétation) est un prompt séparé (docs/roadmap/cartographie/).
Design : docs/superpowers/specs/2026-07-01-territoires-recherche-cartographe-design.md (Partie 2)."""
import os
import re
import sys
import json
import argparse
import unicodedata
from collections import Counter
from datetime import date as _date

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.consolidate_records import scan_records, _prefix_of


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s))
                   if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    """Majuscule + sans accents : pour comparer INDÉTERMINÉ == INDETERMINE, etc."""
    return _strip_accents(s).upper()


_TERR_HEAD = re.compile(r"^###\s+([A-Z]+)\s+[—-]\s+(.*)$")
_FIELD = re.compile(r"^-\s+([a-z_]+):\s*(.*)$")


def parse_territories(text: str) -> list[dict]:
    """Parse les sections territoire de SPECIALITES.md. Chaque `### CODE — Label`
    suivi de lignes `- champ: valeur` -> dict. `legacy_edr` -> list[int] : SEULE
    la liste numérique propre en tête est parsée ; toute annotation qui suit (avec
    ses propres chiffres) ou un préfixe '—'/texte donne [] pour cette partie."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    terrs: list[dict] = []
    cur = None
    for line in text.split("\n"):
        mh = _TERR_HEAD.match(line)
        if mh:
            cur = {"code": mh.group(1), "label": mh.group(2).strip(), "legacy_edr": []}
            terrs.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("## "):        # section suivante -> hors zone territoire
            cur = None
            continue
        mf = _FIELD.match(line)
        if mf:
            key, val = mf.group(1), mf.group(2).strip()
            if key == "legacy_edr":
                # Ne parse QUE la liste propre en tête (chiffres/virgules/espaces).
                # Toute annotation qui suit — même avec ses propres chiffres — est
                # ignorée ; une valeur commençant par '—' ou du texte -> [].
                lead = re.match(r"[\d,\s]*", val).group(0)
                cur["legacy_edr"] = [int(n) for n in re.findall(r"\d{1,3}", lead)]
            else:
                cur[key] = val
    return terrs


def _edr_number(rec_id) -> int | None:
    """Numéro legacy d'un id EDR. 'EDR-140'->140, 'EDR-093'->93 ;
    'EDR-SUB-012' (préfixé) -> None ; None -> None."""
    if not rec_id:
        return None
    m = re.fullmatch(r"EDR-(\d{1,3})", str(rec_id))
    return int(m.group(1)) if m else None


def territory_of(edr_num, territories) -> str | None:
    """Code du territoire dont legacy_edr contient ce numéro, sinon None."""
    if edr_num is None:
        return None
    for t in territories:
        if edr_num in t.get("legacy_edr", []):
            return t["code"]
    return None


def orphan_edrs(records, territories) -> list[dict]:
    """EDR non rattachables. Legacy : orphelin si son numéro > max des legacy_edr connus
    (plus récent que tout ce que le registre mappe). Préfixé : orphelin si son préfixe
    n'est pas un territoire connu (REF exclu). Advisory (aucune suppression)."""
    codes = {t["code"] for t in territories}
    mapped: set = set()
    for t in territories:
        mapped.update(t.get("legacy_edr", []))
    max_mapped = max(mapped) if mapped else 0
    out: list[dict] = []
    for r in records:
        if r.get("type") != "EDR":
            continue
        num = _edr_number(r["id"])
        if num is not None:
            if num not in mapped and num > max_mapped:
                out.append({"id": r["id"], "file": r.get("file"),
                            "reason": "legacy récent non mappé"})
        else:
            prefix = _prefix_of(r["id"])
            if prefix not in codes and prefix != "REF":
                out.append({"id": r["id"], "file": r.get("file"),
                            "reason": f"préfixe {prefix} inconnu"})
    return out


_UNRESOLVED = ("INCONCLUSIF", "INCONCLUSIVE", "VOID", "INDETERMINATE", "INDETERMINE")


def unresolved_verdicts(records) -> list[dict]:
    """EDR dont le verdict OU le titre porte un marqueur non tranché
    (INCONCLUSIF/VOID/INDÉTERMINÉ), comparaison sans accents ni casse. Advisory."""
    out: list[dict] = []
    for r in records:
        if r.get("type") != "EDR":
            continue
        hay = _norm(r.get("verdict") or "") + " " + _norm(r.get("title") or "")
        marker = next((m for m in _UNRESOLVED if m in hay), None)
        if marker:
            out.append({"id": r["id"], "file": r.get("file"),
                        "marker": marker, "verdict": r.get("verdict")})
    return out


_LEAD_MARKERS = ("piste suivante", "prochain chantier", "prochaine piste",
                 "prochain levier", "prochaine sonde", "prochain build",
                 "piste principale", "piste prioritaire", "piste amont",
                 "actionnable")


def pending_leads(files) -> list[dict]:
    """Scanne des (relpath, texte) pour des marqueurs de piste ouverte. Retourne
    {file, line, marker, snippet}. Une entrée par ligne (1re correspondance).
    Sans accents ni casse. Advisory (l'agent croise avec l'aval)."""
    markers = [(_norm(m), m) for m in _LEAD_MARKERS]
    out: list[dict] = []
    for relpath, text in files:
        for i, raw in enumerate((text or "").replace("\r\n", "\n").split("\n"), 1):
            hn = _norm(raw)
            for mn, m in markers:
                if mn in hn:
                    out.append({"file": relpath, "line": i, "marker": m,
                                "snippet": raw.strip()[:200]})
                    break
    return out


# Racines avec bornes de mot : capturent les formes fléchies/accentuées
# (verrouillent, réfutée, réfutent) sans faux positifs (murmure, muraille).
_LOCK_PATTERNS = {
    "verrou": r"\bVERROU",
    "mur": r"\bMURS?\b",
    "refute": r"\bREFUT",
    "bassin": r"\bBASSIN",
    "plancher": r"\bPLANCH",
}


def lock_term_counts(edr_texts, territories) -> dict:
    """Compte les termes-verrou par territoire (mappé via territory_of/préfixe) et
    transverse. edr_texts: [{num, prefix, text}]. `systemic` = terme dans ≥3 territoires."""
    per_territory: dict = {}
    per_term = {t: {"total": 0, "territories": set()} for t in _LOCK_PATTERNS}
    compiled = {t: re.compile(p) for t, p in _LOCK_PATTERNS.items()}
    for e in edr_texts:
        code = territory_of(e.get("num"), territories)
        if code is None and e.get("prefix") not in (None, "LEGACY", "REF"):
            code = e["prefix"]
        hay = _norm(e.get("text") or "")
        for term, rx in compiled.items():
            c = len(rx.findall(hay))
            if not c:
                continue
            per_term[term]["total"] += c
            if code:
                per_territory[code] = per_territory.get(code, 0) + c
                per_term[term]["territories"].add(code)
    per_term_out = {t: {"total": v["total"],
                        "territories": sorted(v["territories"]),
                        "systemic": len(v["territories"]) >= 3}
                    for t, v in per_term.items()}
    return {"per_territory": per_territory, "per_term": per_term_out}


def dormant_territories(territories, k: int = 30) -> list[dict]:
    """Dormance par écart de records : gap = (max legacy global) - (max legacy du territoire).
    dormant si gap >= k. Proxy de récence sans dates (le numéro EDR est ~monotone)."""
    global_max = 0
    for t in territories:
        if t.get("legacy_edr"):
            global_max = max(global_max, max(t["legacy_edr"]))
    out: list[dict] = []
    for t in territories:
        last = max(t["legacy_edr"]) if t.get("legacy_edr") else 0
        gap = global_max - last
        out.append({"code": t["code"], "statut": t.get("statut", ""),
                    "dernier_edr": last, "gap": gap, "dormant": gap >= k})
    return out


def _read_texts(relpaths) -> list:
    """Lit (relpath, texte) pour chaque chemin. Les relpath viennent de scan_records,
    qui les étiquette relativement au _ROOT du module (consolidate partage le même _ROOT) :
    on les résout donc contre _ROOT — round-trip correct quel que soit --root, sans
    dépendance au CWD."""
    files = []
    for rel in relpaths:
        try:
            with open(os.path.join(_ROOT, rel), encoding="utf-8") as fh:
                files.append((rel, fh.read()))
        except OSError:
            continue
    return files


def _memory_files(memory_dir) -> list:
    """Lit (memory/<nom>, texte) pour chaque .md du dossier mémoire, s'il existe."""
    if not memory_dir or not os.path.isdir(memory_dir):
        return []
    out = []
    for name in sorted(os.listdir(memory_dir)):
        if not name.endswith(".md"):
            continue
        try:
            with open(os.path.join(memory_dir, name), encoding="utf-8") as fh:
                out.append((f"memory/{name}", fh.read()))
        except OSError:
            continue
    return out


def build_signals(root, memory_dir, the_date, dormant_gap) -> dict:
    """Assemble tous les signaux (pur, sans écriture disque)."""
    with open(os.path.join(root, "docs", "roadmap", "SPECIALITES.md"),
              encoding="utf-8") as fh:
        territories = parse_territories(fh.read())

    records = scan_records(root)
    edr_records = [r for r in records if r.get("type") == "EDR"]
    edr_files = _read_texts([r["file"] for r in edr_records])
    text_by_file = dict(edr_files)
    edr_texts = [{"num": _edr_number(r["id"]), "prefix": _prefix_of(r["id"]),
                  "text": text_by_file.get(r["file"], "")} for r in edr_records]
    mem_files = _memory_files(memory_dir)

    return {
        "date": the_date,
        "prefix_counts": dict(Counter(_prefix_of(r["id"]) for r in records)),
        "dormant_territories": dormant_territories(territories, dormant_gap),
        "orphans": orphan_edrs(records, territories),
        "unresolved_verdicts": unresolved_verdicts(records),
        "pending_leads": pending_leads(edr_files + mem_files),
        "lock_terms": lock_term_counts(edr_texts, territories),
    }


def main(argv=None) -> int:
    """Moissonne les signaux et écrit docs/roadmap/cartographie/signals-<date>.json."""
    ap = argparse.ArgumentParser(description="Cartographe — moisson de signaux déterministes.")
    ap.add_argument("--root", default=_ROOT)
    ap.add_argument("--memory-dir", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--date", default=None)
    ap.add_argument("--dormant-gap", type=int, default=30)
    args = ap.parse_args(argv)

    the_date = args.date or _date.today().isoformat()
    out_dir = args.out_dir or os.path.join(args.root, "docs", "roadmap", "cartographie")
    signals = build_signals(args.root, args.memory_dir, the_date, args.dormant_gap)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"signals-{the_date}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(signals, fh, ensure_ascii=False, indent=2)

    print(f"cartographie {the_date}: "
          f"orphelins={len(signals['orphans'])} "
          f"verdicts_ouverts={len(signals['unresolved_verdicts'])} "
          f"leads={len(signals['pending_leads'])} "
          f"-> {os.path.relpath(out_path, args.root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
