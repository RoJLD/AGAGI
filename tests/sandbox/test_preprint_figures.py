"""P5.1 — les figures du preprint ne contiennent AUCUNE valeur en dur : chaque CSV est recomputé depuis les JSON
cités, et une source absente est RAPPORTÉE, jamais remplacée. Deux cas : F5 relu contre son JSON ; source
manquante -> FileNotFoundError (pas de figure vide)."""
import csv
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.paths import results_file  # noqa: E402
from tools.preprint import figures as F  # noqa: E402


def test_F5_csv_is_recomputed_from_the_cited_json(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "OUT_DIR", str(tmp_path))
    p_csv, _ = F.f5_e28()
    rows = list(csv.DictReader(open(p_csv, encoding="utf-8")))
    r2 = json.load(open(str(results_file("legacy_lr_curve_r2.json")), encoding="utf-8"))
    for row in rows:
        if row["condition"].startswith("sous garde"):
            v = r2["_lecture"]["par_lr"][str(float(row["lr"])) if "." in row["lr"] else row["lr"]]
            assert float(row["resurrections_mediane"]) == v["resurrections"]
            assert float(row["hit_last_mediane"]) == v["mediane_hit_last"]


def test_a_missing_source_is_REPORTED_not_replaced(monkeypatch, tmp_path):
    monkeypatch.setattr(F, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(F, "results_file", lambda name: tmp_path / name)      # aucun JSON ici
    with pytest.raises(FileNotFoundError, match="ABSENTE"):
        F.f4_dose()
