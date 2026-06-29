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
