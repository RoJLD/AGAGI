import os
import re
import json
import pathlib

import pytest

from tools.consolidate_records import (
    parse_record, scan_records, build_graph, validate_graph, roadmap_state, main,
)


def _write(p: pathlib.Path, text: str) -> str:
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_record_reads_frontmatter(tmp_path):
    f = _write(tmp_path / "G1_transfer.md", (
        "---\n"
        "id: SDR-G1\n"
        "type: SDR\n"
        "title: La competence generalise-t-elle\n"
        "status: open\n"
        "gate: G1\n"
        "motivates: [EDR-105, EDR-108]\n"
        "---\n"
        "# corps libre\n"
    ))
    rec = parse_record(f)
    assert rec["id"] == "SDR-G1"
    assert rec["type"] == "SDR"
    assert rec["gate"] == "G1"
    assert rec["motivates"] == ["EDR-105", "EDR-108"]
    assert rec["triggers"] == [] and rec["tests"] == []
    assert rec["linked"] is True


def test_parse_record_tolerates_edr_without_frontmatter(tmp_path):
    f = _write(tmp_path / "105_Forage_Bottleneck.md", "# EDR 105 sans frontmatter\n")
    rec = parse_record(f)
    assert rec["id"] == "EDR-105"
    assert rec["type"] == "EDR"
    assert rec["linked"] is False


def test_parse_record_returns_none_for_non_record(tmp_path):
    f = _write(tmp_path / "README.md", "# pas un record\n")
    assert parse_record(f) is None


def test_scan_records_collects_all_types(tmp_path):
    (tmp_path / "docs" / "SDR").mkdir(parents=True)
    (tmp_path / "docs" / "EDR").mkdir(parents=True)
    _write(tmp_path / "docs" / "SDR" / "G0_validity.md",
           "---\nid: SDR-G0\ntype: SDR\ntitle: t\nstatus: open\ngate: G0\n---\n")
    _write(tmp_path / "docs" / "EDR" / "105_Forage.md", "# edr\n")
    _write(tmp_path / "docs" / "EDR" / "not_an_edr.md", "# noise\n")
    recs = scan_records(str(tmp_path))
    ids = sorted(r["id"] for r in recs)
    assert ids == ["EDR-105", "SDR-G0"]


def test_build_graph_emits_typed_edges():
    recs = [
        {"id": "SDR-G1", "type": "SDR", "title": "t", "status": "open", "gate": "G1",
         "motivates": ["EDR-105"], "triggers": [], "tests": [], "verdict": None,
         "file": "f", "linked": True},
        {"id": "EDR-105", "type": "EDR", "title": "t", "status": "refuted", "gate": "G1",
         "motivates": [], "triggers": ["ADR-007"], "tests": ["SDR-G1"], "verdict": "NEUTRE",
         "file": "f", "linked": True},
    ]
    g = build_graph(recs)
    rels = sorted((e["from"], e["to"], e["rel"]) for e in g["edges"])
    assert rels == [
        ("EDR-105", "ADR-007", "DECLENCHE"),
        ("EDR-105", "SDR-G1", "TESTE"),
        ("SDR-G1", "EDR-105", "MOTIVE"),
    ]
    assert {n["id"] for n in g["nodes"]} == {"SDR-G1", "EDR-105"}


def _rec(id, type, **kw):
    base = {"id": id, "type": type, "title": "t", "status": "open", "gate": None,
            "motivates": [], "triggers": [], "tests": [], "verdict": None,
            "file": "f", "linked": True}
    base.update(kw)
    return base


def test_validate_flags_broken_link():
    recs = [_rec("SDR-G1", "SDR", gate="G1", motivates=["EDR-999"])]
    probs = validate_graph(recs)
    assert any(p["kind"] == "broken_link" and "EDR-999" in p["detail"] for p in probs)


def test_validate_flags_validated_gate_without_validated_edr():
    recs = [
        _rec("SDR-G1", "SDR", gate="G1", status="validated"),
        _rec("EDR-105", "EDR", gate="G1", status="refuted", tests=["SDR-G1"]),
    ]
    probs = validate_graph(recs)
    assert any(p["kind"] == "unsupported_gate" and p["record"] == "SDR-G1" for p in probs)


def test_validate_clean_graph_has_no_problems():
    recs = [
        _rec("SDR-G1", "SDR", gate="G1", status="validated", motivates=["EDR-105"]),
        _rec("EDR-105", "EDR", gate="G1", status="validated", tests=["SDR-G1"]),
    ]
    assert validate_graph(recs) == []


def test_roadmap_state_maps_gate_to_records():
    recs = [
        _rec("SDR-G1", "SDR", gate="G1", status="open", motivates=["EDR-105"]),
        _rec("EDR-105", "EDR", gate="G1", status="refuted", tests=["SDR-G1"],
             triggers=["ADR-007"]),
    ]
    state = roadmap_state(recs)
    assert state["G1"]["sdr"] == "SDR-G1"
    assert state["G1"]["tested_by"] == ["EDR-105"]
    assert state["G1"]["triggered_adr"] == ["ADR-007"]
    assert state["G0"]["sdr"] is None


def test_main_exits_nonzero_on_broken_link(tmp_path, monkeypatch, capsys):
    (tmp_path / "docs" / "SDR").mkdir(parents=True)
    (tmp_path / "results").mkdir()
    _write(tmp_path / "docs" / "SDR" / "G1_x.md",
           "---\nid: SDR-G1\ntype: SDR\ntitle: t\nstatus: open\ngate: G1\n"
           "motivates: [EDR-999]\n---\n")
    rc = main(["--root", str(tmp_path)])
    assert rc == 1
    out = json.loads((tmp_path / "results" / "records_graph.json").read_text(encoding="utf-8"))
    assert out["problems"]
