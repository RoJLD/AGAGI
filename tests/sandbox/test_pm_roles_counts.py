"""Compteurs des roles : recomputes depuis le journal et les fichiers modifies, jamais recopies."""
import datetime
import json
import os
import subprocess
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


def test_fichiers_modifies_CONTROLE_POSITIF_since_ancre_a_minuit(tmp_path):
    """CONTRE-EXEMPLE GELE : une date NUE passée à `git --since` vaut « depuis l'heure COURANTE de ce
    jour-là », donc ZÉRO commit si le run a lieu APRÈS minuit le jour même de `depuis` sans l'heure
    fixée — c'est exactement le bug mesuré (0 contre 44 commits). Un dépôt jetable, un commit RÉEL du
    jour, et l'assertion positive : le fichier touché DOIT apparaître. Et un chemin qui n'est PAS un
    dépôt git rend None, jamais une liste vide (« je ne sais pas » ≠ « rien de modifié »)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)
    run("git", "init", "-b", "main")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test")
    run("git", "config", "commit.gpgsign", "false")          # dépôt JETABLE, sans rapport avec l'auteur réel
    (repo / "docs" / "EDR").mkdir(parents=True)
    (repo / "docs" / "EDR" / "a.md").write_text("x", encoding="utf-8")
    run("git", "add", "docs/EDR/a.md")
    run("git", "commit", "-m", "test")

    aujourdhui = datetime.date.today().isoformat()
    fichiers = RC.fichiers_modifies(str(repo), depuis=aujourdhui)
    assert fichiers is not None and "docs/EDR/a.md" in fichiers, fichiers

    assert RC.fichiers_modifies(str(tmp_path / "pas_un_depot")) is None
