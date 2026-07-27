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
