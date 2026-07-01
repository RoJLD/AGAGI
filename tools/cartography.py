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
