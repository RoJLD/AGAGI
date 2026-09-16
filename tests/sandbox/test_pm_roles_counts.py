"""Compteurs des roles : recomputes depuis le journal et les fichiers modifies, jamais recopies."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import roles_counts as RC  # noqa: E402

T0 = 1_800_000_000.0


def test_bucket_par_chemin_science_methodo_autre():
    assert RC.bucket("docs/EDR/X.md") == "science" and RC.bucket("results/a.json") == "science"
    assert RC.bucket("docs/preregistrations/R.json") == "science"
    for p in ("tools/check_x.py", "tests/sandbox/test_y.py", "docs/REF/Z.md", "docs/roadmap/P.md", "CLAUDE.md"):
        assert RC.bucket(p) == "methodo", p
    assert RC.bucket("src/agents/x.py") == "autre" and RC.bucket("tools/evo_runs/r.py") == "autre"


def test_compute_counts_ratio_et_None_sans_methodo():
    c = RC.compute_counts([], ["docs/EDR/a.md", "results/b.json", "tools/check_c.py", "src/d.py"], T0)
    assert c["fichiers"] == {"science": 2, "methodo": 1, "autre": 1} and c["ratio_science_methodo"] == 2.0
    c2 = RC.compute_counts([], ["docs/EDR/a.md"], T0)
    assert c2["ratio_science_methodo"] is None                   # pas de dénominateur : « je ne sais pas », pas inf
    assert c["alertes"]["emises"] == 0 and c["depuis"] == RC.DEBUT


def test_main_ecrit_ROLES_COUNTS_sous_pm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    assert RC.main(["--repo-root", os.getcwd()]) == 0
    j = json.loads((tmp_path / "pm" / "ROLES_COUNTS.json").read_text(encoding="utf-8"))
    assert set(j) >= {"alertes", "fichiers", "ratio_science_methodo", "depuis", "generated_at"}
