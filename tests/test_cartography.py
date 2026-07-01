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


def _rec(id, type="EDR", file="f.md"):
    return {"id": id, "type": type, "file": file}


TERRS = [
    {"code": "SUB", "label": "S", "legacy_edr": [134, 135]},
    {"code": "BIND", "label": "B", "legacy_edr": [128, 129]},
]


def test_edr_number_parsing():
    from tools.cartography import _edr_number
    assert _edr_number("EDR-140") == 140
    assert _edr_number("EDR-093") == 93
    assert _edr_number("EDR-SUB-012") is None
    assert _edr_number(None) is None


def test_territory_of_maps_by_legacy():
    from tools.cartography import territory_of
    assert territory_of(134, TERRS) == "SUB"
    assert territory_of(128, TERRS) == "BIND"
    assert territory_of(999, TERRS) is None
    assert territory_of(None, TERRS) is None


def test_orphan_edrs_recent_legacy_and_unknown_prefix():
    from tools.cartography import orphan_edrs
    records = [
        _rec("EDR-134"),                 # mappé SUB -> pas orphelin
        _rec("EDR-100"),                 # legacy non mappé MAIS < max(135) -> pas orphelin
        _rec("EDR-200"),                 # legacy > max mappé (135) -> ORPHELIN
        _rec("EDR-SUB-012"),             # préfixe connu -> pas orphelin
        _rec("EDR-ZZZ-001"),             # préfixe inconnu -> ORPHELIN
        _rec("REF-NEAT-2002", type="REF"),  # pas un EDR -> ignoré
    ]
    orphans = orphan_edrs(records, TERRS)
    ids = sorted(o["id"] for o in orphans)
    assert ids == ["EDR-200", "EDR-ZZZ-001"]


def test_unresolved_verdicts_matches_verdict_and_title():
    from tools.cartography import unresolved_verdicts
    records = [
        {"id": "EDR-121", "type": "EDR", "file": "a.md",
         "title": "Stockage INCONCLUSIVE", "verdict": "INCONCLUSIF"},
        {"id": "EDR-151", "type": "EDR", "file": "b.md",
         "title": "ToM comportementale INDÉTERMINÉ", "verdict": None},
        {"id": "EDR-112", "type": "EDR", "file": "c.md",
         "title": "Le monde exige", "verdict": "EXIGE"},
        {"id": "SDR-G1", "type": "SDR", "file": "d.md",
         "title": "porte VOID", "verdict": None},   # pas un EDR -> ignoré
    ]
    res = unresolved_verdicts(records)
    ids = sorted(r["id"] for r in res)
    assert ids == ["EDR-121", "EDR-151"]
    by_id = {r["id"]: r for r in res}
    assert by_id["EDR-121"]["marker"] == "INCONCLUSIF"
    assert by_id["EDR-151"]["marker"] == "INDETERMINE"


def test_pending_leads_scans_markers_case_insensitive():
    from tools.cartography import pending_leads
    files = [
        ("docs/EDR/131_x.md",
         "Contexte.\nintervention précoce (warm-start) → c'est la piste suivante directe.\nFin."),
        ("memory/edr090.md", "Le prochain levier est l'adaptation du substrat."),
        ("docs/EDR/010_y.md", "Rien à signaler ici."),
    ]
    leads = pending_leads(files)
    assert len(leads) == 2
    by_file = {l["file"]: l for l in leads}
    assert by_file["docs/EDR/131_x.md"]["line"] == 2
    assert by_file["docs/EDR/131_x.md"]["marker"] == "piste suivante"
    assert by_file["memory/edr090.md"]["marker"] == "prochain levier"
    assert "warm-start" in by_file["docs/EDR/131_x.md"]["snippet"]


def test_lock_term_counts_by_territory_and_systemic():
    from tools.cartography import lock_term_counts
    territories = [
        {"code": "SUB", "legacy_edr": [134]},
        {"code": "BIND", "legacy_edr": [128]},
        {"code": "NAV", "legacy_edr": [110]},
    ]
    edr_texts = [
        {"num": 134, "prefix": "LEGACY", "text": "le VERROU tient, les seeds verrouillent"},
        {"num": 128, "prefix": "LEGACY", "text": "hypothèse RÉFUTÉE ; c'est un bassin"},
        {"num": 110, "prefix": "LEGACY", "text": "au plancher, le mur reste ; réfutée aussi"},
        {"num": 999, "prefix": "LEGACY", "text": "un murmure sans verrou-mot"},  # non mappé
    ]
    res = lock_term_counts(edr_texts, territories)
    # "verrou" (VERROU + verrouillent) compte 2 sur SUB
    assert res["per_territory"]["SUB"] == 2
    # "réfuté" apparaît sur BIND et NAV -> 2 territoires, pas systémique (<3)
    assert res["per_term"]["refute"]["systemic"] is False
    assert sorted(res["per_term"]["refute"]["territories"]) == ["BIND", "NAV"]
    # "murmure" ne doit PAS compter comme "mur"
    assert "mur" not in res["per_territory"] or res["per_term"]["mur"]["total"] == 1
