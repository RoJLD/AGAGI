import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_ROOT, "data", "agi_taxonomy")


def _load(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_capabilities_v0_shape_and_files_exist():
    caps = _load("capabilities.json")
    assert [c["id"] for c in caps] == ["perception", "memory", "language", "generalization"]
    for c in caps:
        assert set(c) >= {"id", "title", "description", "evidence_criterion", "probe", "record"}
        assert os.path.isfile(os.path.join(_ROOT, c["probe"])), f"probe absent : {c['probe']}"
        assert os.path.isfile(os.path.join(_ROOT, c["record"])), f"record absent : {c['record']}"


def test_demands_shipped_graph_validates():
    from tools.check_agi_taxonomy import validate_graph
    caps = _load("capabilities.json")
    demands = _load("demands.json")
    assert validate_graph(caps, demands) == [], "le graphe LIVRÉ (capabilities + demands) doit valider sans violation"
    assert len(demands) >= 1, "demands.json porte au moins la 1ère arête mesurée (SP-2)"


_ABSENT = object()   # sentinelle : `_valid_edge(champ=_ABSENT)` RETIRE le champ de l'evidence


def _valid_edge(**evidence_over):
    """Arête FIXTURE valide-de-forme (record = un vrai EDR pour que _exists passe). Les tests écrasent
    un champ d'evidence — ou le retirent avec `_ABSENT` — pour vérifier chaque règle de rejet.

    ⚠️ `specificity_control='pass'` fait partie du DÉFAUT depuis le durcissement du 2026-09-01 : le
    contrôle de demande est désormais exigé TOUJOURS, pas seulement dans la branche `n/a`. Le trou
    fermé (fa='pass' seul) est gelé comme contre-exemple dans
    `tests/sandbox/test_agi_taxonomy_gate.py`."""
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "functional_aliasing": "pass",
          "specificity_control": "pass",
          "record": "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"}
    ev.update(evidence_over)
    ev = {k: val for k, val in ev.items() if val is not _ABSENT}
    return {"capability": "memory", "prerequisite": "perception", "strength": "hard", "evidence": ev}


def test_edge_accepts_na_aliasing_with_specificity_control():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge(functional_aliasing="n/a", specificity_control="pass")
    assert validate_edge(e, _IDS) == []


def test_edge_rejects_na_aliasing_without_specificity_control():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge(functional_aliasing="n/a", specificity_control=_ABSENT)
    v = validate_edge(e, _IDS)
    assert any("specificity_control" in x for x in v)


def test_edge_rejects_na_aliasing_with_failed_specificity():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge(functional_aliasing="n/a", specificity_control="fail")
    v = validate_edge(e, _IDS)
    assert any("specificity_control" in x for x in v)


def test_edge_still_accepts_pass_aliasing():
    """`functional_aliasing='pass'` reste un chemin d'acceptation — mais PLUS À LUI SEUL : depuis le
    durcissement du 2026-09-01 il lui faut aussi `specificity_control='pass'` (fourni par la fixture).
    Le refus de `fa='pass'` SANS contrôle de demande est testé dans
    `tests/sandbox/test_agi_taxonomy_gate.py::test_gate_REFUSES_aliasing_pass_without_specificity_control`."""
    from tools.check_agi_taxonomy import validate_edge
    assert validate_edge(_valid_edge(functional_aliasing="pass"), _IDS) == []


_IDS = {"perception", "memory", "language", "generalization"}


def test_real_capabilities_pass_validation():
    from tools.check_agi_taxonomy import validate_graph
    assert validate_graph(_load("capabilities.json"), []) == []


def test_empty_graph_has_no_violations():
    from tools.check_agi_taxonomy import main
    assert main([]) == 0


def test_valid_edge_is_accepted():
    from tools.check_agi_taxonomy import validate_edge
    assert validate_edge(_valid_edge(), _IDS) == []


def test_edge_rejected_when_verdict_not_demanded():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(ablation_verdict="INCONCLUSIVE"), _IDS)
    assert any("X_DEMANDED" in x for x in v)


def test_edge_rejected_when_underpowered():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(n=8), _IDS)
    assert any("n=" in x or ">= 12" in x for x in v)


def test_edge_rejected_when_functional_aliasing_not_pass():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(functional_aliasing="fail"), _IDS)
    assert any("functional_aliasing" in x for x in v)


def test_edge_rejected_when_record_missing():
    from tools.check_agi_taxonomy import validate_edge
    v = validate_edge(_valid_edge(record="docs/EDR/DOES_NOT_EXIST.md"), _IDS)
    assert any("record" in x for x in v)


def test_edge_rejected_when_prerequisite_unknown():
    from tools.check_agi_taxonomy import validate_edge
    e = _valid_edge()
    e["prerequisite"] = "telepathy"
    v = validate_edge(e, _IDS)
    assert any("telepathy" in x for x in v)
