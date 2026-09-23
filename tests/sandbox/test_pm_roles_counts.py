"""Compteurs des roles : recomputes depuis le journal et les fichiers modifies, jamais recopies."""
import datetime
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import roles_counts as RC  # noqa: E402

T0 = 1_800_000_000.0


def test_bucket_par_chemin_science_methodo_autre():
    assert RC.bucket("docs/EDR/X.md") == "science" and RC.bucket("results/a.json") == "science"
    assert RC.bucket("docs/preregistrations/R.json") == "science"
    for p in ("tools/check_x.py", "tests/sandbox/test_y.py", "docs/REF/Z.md", "docs/roadmap/P.md", "CLAUDE.md"):
        assert RC.bucket(p) == "methodo", p
    assert RC.bucket("src/agents/x.py") == "autre" and RC.bucket("tools/evo_runs/r.py") == "autre"


def test_bucket_compte_la_COUCHE_DES_ROLES_les_hooks_et_les_specs_comme_METHODO():
    """I9 (b) : `tools/pm/`, `.claude/` et `docs/superpowers/` tombaient en « autre », donc le
    denominateur du ratio 1:1 excluait precisement le travail que ce ratio est cense borner — la
    regle des roles se mesurait elle-meme a cote."""
    for p in ("tools/pm/board.py", "tools/pm/snapshot.py", ".claude/settings.json",
              ".claude/skills/pm/SKILL.md", "docs/superpowers/specs/2026-09-16-pm.md"):
        assert RC.bucket(p) == "methodo", p
    assert RC.bucket("tools/ablation.py") == "autre"             # `tools/` NU reste « autre »


def test_compute_counts_ratio_et_None_sans_methodo():
    c = RC.compute_counts([], ["docs/EDR/a.md", "results/b.json", "tools/check_c.py", "src/d.py"], T0)
    assert c["fichiers"] == {"science": 2, "methodo": 1, "autre": 1} and c["ratio_science_methodo"] == 2.0
    c2 = RC.compute_counts([], ["docs/EDR/a.md"], T0)
    assert c2["ratio_science_methodo"] is None                   # pas de dénominateur : « je ne sais pas », pas inf
    assert c["alertes"]["emises"] == 0 and c["depuis"] == RC.DEBUT


def test_compute_counts_PUBLIE_la_fenetre_glissante_et_non_seulement_le_point_de_depart():
    c = RC.compute_counts([], ["docs/EDR/a.md"], T0)
    attendu = time.strftime("%Y-%m-%d", time.localtime(T0 - 30 * 86400))
    assert c["fenetre"] == {"depuis": attendu, "jours": 30}
    assert c["depuis"] == RC.DEBUT                               # le point de DEPART publie, pas la borne de mesure
    c7 = RC.compute_counts([], [], T0, fenetre_jours=7)
    assert c7["fenetre"] == {"depuis": time.strftime("%Y-%m-%d", time.localtime(T0 - 7 * 86400)), "jours": 7}


def test_fichiers_modifies_sans_depuis_demande_une_FENETRE_GLISSANTE_de_30_jours(monkeypatch):
    """I9 (c) : la borne etait FIXE (`DEBUT`), donc le ratio agregeait de plus en plus — « le ratio du
    mois » devenait « le ratio depuis toujours » sans que rien ne le dise. La date attendue est
    CALCULEE ici, jamais ecrite en dur : un test a date gelee perimerait en silence."""
    vu = {}

    class Faux:
        returncode, stdout = 0, ""

    def faux_run(cmd, **kw):
        vu["since"] = [a for a in cmd if a.startswith("--since=")][0]
        return Faux()

    monkeypatch.setattr(RC.subprocess, "run", faux_run)
    RC.fichiers_modifies("/peu importe", now=T0)
    assert vu["since"] == "--since=%s 00:00" % time.strftime("%Y-%m-%d", time.localtime(T0 - 30 * 86400))
    RC.fichiers_modifies("/peu importe", depuis="2026-01-01", now=T0)
    assert vu["since"] == "--since=2026-01-01 00:00"             # une borne EXPLICITE reste respectee


def test_fichiers_disponibles_est_FALSE_quand_git_est_muet_jamais_zero_fichier(monkeypatch):
    monkeypatch.setattr(RC, "fichiers_modifies", lambda *a, **k: None)
    c = RC.compute_counts([], RC.fichiers_modifies("/x"), T0)
    assert c["fichiers_disponibles"] is False
    assert c["fichiers"] == {"science": 0, "methodo": 0, "autre": 0}     # des zeros AVOUES par le drapeau
    assert RC.compute_counts([], [], T0)["fichiers_disponibles"] is True


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
