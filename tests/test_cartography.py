import os
import json

import pytest

from tools.cartography import parse_territories


SPEC_SNIPPET = """# Registre

## Territoires

### SUB — Substrat & Moteur d'apprentissage
- statut: actif
- couche: Substrat/Moteur
- question_phare: Moteur torch ≥ legacy
- fichiers_possedes: tools/substrate_world_ab.py
- legacy_edr: 134,135,137
- ponts_actifs: [BIND]
- filiation: —

### FAM — Famine
- statut: dormant
- couche: Monde
- question_phare: Spécialisation
- legacy_edr: — (fil suivi en mémoire, 129_*/130_* = BIND)
- filiation: —

## Doublons legacy connus

EDR-093 ...
"""


def test_parse_territories_extracts_fields():
    terrs = parse_territories(SPEC_SNIPPET)
    assert [t["code"] for t in terrs] == ["SUB", "FAM"]
    sub = terrs[0]
    assert sub["label"].startswith("Substrat")
    assert sub["statut"] == "actif"
    assert sub["question_phare"] == "Moteur torch ≥ legacy"
    assert sub["legacy_edr"] == [134, 135, 137]


def test_parse_territories_empty_legacy_when_dash():
    terrs = parse_territories(SPEC_SNIPPET)
    fam = terrs[1]
    # valeur commençant par — : legacy_edr vide MÊME si le texte contient 129/130
    assert fam["legacy_edr"] == []
    assert fam["statut"] == "dormant"


def test_parse_territories_stops_at_next_h2():
    terrs = parse_territories(SPEC_SNIPPET)
    # la section "## Doublons" ne crée pas de territoire
    assert len(terrs) == 2
