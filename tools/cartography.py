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
    suivi de lignes `- champ: valeur` -> dict. `legacy_edr` -> list[int]
    (vide si la valeur commence par '—', même si le texte contient des chiffres)."""
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
                cur["legacy_edr"] = ([int(n) for n in re.findall(r"\d{1,3}", val)]
                                    if not val.startswith("—") else [])
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


_UNRESOLVED = ("INCONCLUSIF", "INCONCLUSIVE", "VOID", "INDETERMINE")


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
