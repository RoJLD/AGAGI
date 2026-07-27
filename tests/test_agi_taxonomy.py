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


def test_demands_v0_is_empty():
    assert _load("demands.json") == [], "demands.json doit être VIDE en v0 (arêtes = livrable SP-2)"


def _valid_edge(**evidence_over):
    """Arête FIXTURE valide-de-forme (record = un vrai EDR pour que _exists passe). Les tests écrasent
    un champ d'evidence pour vérifier chaque règle de rejet."""
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "functional_aliasing": "pass",
          "record": "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"}
    ev.update(evidence_over)
    return {"capability": "memory", "prerequisite": "perception", "strength": "hard", "evidence": ev}


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
