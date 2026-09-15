# -*- coding: utf-8 -*-
"""Contre-exemples GELÉS de la PROVENANCE MINIMALE du Harness (P2.61) — une évidence citée ne se
réécrit plus en silence.

Défaut mesuré (git status du 2026-09-14) : 11 fichiers `results/*.json` cités par des records —
`competence_profile_99240`, `lewis_capacity_nav_12345`, `lewis_evolve_nav_107`, `s2_demand_2026`,
`tom_probe_99280`, … — étaient MODIFIÉS à chaque passe de la suite de tests. Le mécanisme : un test
de fumée appelle le runner RÉEL avec le SEED de la mesure publiée (R=1, eras=2, max_ticks=80), le
runner appelle `Harness.save`, et `Harness.save` écrivait `results/<name>_<seed>.json` — le chemin
même de l'évidence. L'évidence sur disque n'était alors plus la mesure que le record décrit, et rien
ne le disait : un `M` dans `git status` que personne ne lit.

La garde vit dans `Harness.__init__` — PAS dans `save`, appelé en FIN de run : une décision prise là
serait un E13 fabriqué par la garde (le run est déjà payé quand elle parle). Elle détourne vers
`_rerun` tout chemin nominal qui EXISTE et est SUIVI par git ; non suivi, absent, ou hors dépôt (suivi
INDÉCIDABLE), le chemin est le nominal. Chaque cas construit un dépôt git JOUET dans `tmp_path`.

EXEMPTION DÉCLARÉE de la garde de bail : aucun monde n'est construit.
"""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai import harness as H  # noqa: E402
from src.seed_ai.harness import Harness  # noqa: E402

_LEASE_GUARD_EXEMPT = True

_EVIDENCE = {"name": "t", "seed": 1, "commit": "abc1234", "git_dirty": False, "data": {"kpi": 0.5}}


@pytest.fixture(autouse=True)
def _environnement_vierge(monkeypatch):
    """⚠️ Un GIT_INDEX_FILE / GIT_DIR hérité (commit depuis un index temporaire, hook pre-commit) ferait
    écrire le dépôt jouet DANS L'INDEX DU VRAI DÉPÔT (mesuré le 2026-09-14 sous le harnais de mutation,
    cf. `test_backlog_freshness.py`). Et la racine des résultats ne doit venir que du test, jamais de la
    configuration de la machine."""
    for k in list(os.environ):
        if k.startswith("GIT_"):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("AGAGI_RESULTS_ROOT", raising=False)


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


def _depot_jouet(tmp_path, suivis=("t_1.json",), libres=("libre_2.json",)):
    """Un dépôt git minimal portant un `results/` : `suivis` COMMITTÉS, `libres` présents mais JAMAIS
    ajoutés — les deux avec un contenu d'évidence connu."""
    repo = tmp_path / "repo"
    (repo / "results").mkdir(parents=True)
    _git(repo, "init", "-q")
    for nom in suivis:
        (repo / "results" / nom).write_text(json.dumps(_EVIDENCE), encoding="utf-8")
        _git(repo, "add", "results/" + nom)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "evidence")
    for nom in libres:
        (repo / "results" / nom).write_text(json.dumps(_EVIDENCE), encoding="utf-8")
    return repo


def _interdit(path):
    raise AssertionError(f"git a été interrogé ({path!r}) alors qu'il ne devait pas l'être")


def _lire(p):
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------------
# Le défaut : un fichier SUIVI est réécrit. Après la garde : DÉTOURNÉ, et l'évidence est bit-identique.
# --------------------------------------------------------------------------------------------------

def test_un_fichier_SUIVI_par_git_est_DETOURNE_vers_rerun_et_l_evidence_reste_bit_identique(tmp_path, monkeypatch):
    repo = _depot_jouet(tmp_path)
    monkeypatch.chdir(repo)
    avant = (repo / "results" / "t_1.json").read_bytes()
    h = Harness(seed=1, name="t", with_db=False)
    assert h.results_path == "results/t_1_rerun.json", h.results_path
    p = h.save({"kpi": 0.9})
    assert p == h.results_path
    assert (repo / "results" / "t_1.json").read_bytes() == avant, "l'évidence citée a été RÉÉCRITE"
    out = _lire(repo / "results" / "t_1_rerun.json")
    assert out["data"]["kpi"] == 0.9
    assert out["rerun_of"] == "results/t_1.json"        # le JSON dit de QUOI il est la reprise


def test_un_fichier_NON_SUIVI_prend_le_chemin_NOMINAL_et_est_ecrase(tmp_path, monkeypatch):
    """Spécificité : un JSON présent mais jamais ajouté n'est l'évidence de rien — l'écraser est le
    comportement historique, et il reste."""
    repo = _depot_jouet(tmp_path)
    monkeypatch.chdir(repo)
    h = Harness(seed=2, name="libre", with_db=False)
    assert h.results_dir == "results"                    # défaut de `src/paths.py`, bit-identique
    assert h.results_path == "results/libre_2.json"
    h.save({"kpi": 0.9})
    out = _lire(repo / "results" / "libre_2.json")
    assert out["data"]["kpi"] == 0.9 and "rerun_of" not in out


def test_HORS_de_tout_depot_git_le_suivi_est_INDECIDABLE_et_le_chemin_est_NOMINAL(tmp_path, monkeypatch):
    """Hors dépôt on n'invente ni un détour ni un refus : même règle que
    `tools/check_backlog_freshness.py::_tracked_by_git`."""
    d = tmp_path / "nulle_part"
    (d / "results").mkdir(parents=True)
    (d / "results" / "t_1.json").write_text(json.dumps(_EVIDENCE), encoding="utf-8")
    dedans = subprocess.run(["git", "-C", str(d), "rev-parse", "--is-inside-work-tree"],
                            capture_output=True).returncode == 0
    if dedans:
        pytest.skip("tmp_path vit DANS un dépôt git sur cette machine : le cas « hors dépôt » n'y est pas constructible")
    monkeypatch.chdir(d)
    assert H._tracked_by_git(str(d / "results" / "t_1.json")) is None
    h = Harness(seed=1, name="t", with_db=False)
    assert h.results_path == "results/t_1.json"


def test_un_fichier_ABSENT_prend_le_chemin_NOMINAL_sans_interroger_git(tmp_path, monkeypatch):
    """Spécificité ET coût : le cas de loin le plus fréquent (premier run) ne lance aucun sous-processus."""
    repo = _depot_jouet(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(H, "_tracked_by_git", _interdit)
    h = Harness(seed=3, name="neuf", with_db=False)
    assert h.results_path == "results/neuf_3.json"


# --------------------------------------------------------------------------------------------------
# OÙ la décision est prise (E13), et ce qu'elle protège d'elle-même
# --------------------------------------------------------------------------------------------------

def test_la_decision_est_prise_a_l_INIT_et_jamais_au_save(tmp_path, monkeypatch):
    """`save` est appelé en FIN de run : y décider serait un E13 fabriqué par la garde. Après
    `__init__`, plus AUCUNE interrogation de git — et le détour tient."""
    repo = _depot_jouet(tmp_path)
    monkeypatch.chdir(repo)
    h = Harness(seed=1, name="t", with_db=False)
    monkeypatch.setattr(H, "_tracked_by_git", _interdit)
    assert h.save({"kpi": 0.1}) == "results/t_1_rerun.json"


def test_un_rerun_lui_meme_SUIVI_est_detourne_a_son_tour(tmp_path, monkeypatch):
    """`_rerun.json` est un `.json` sous `results/` : un `git add results` l'emporte, et committé il
    devient une évidence. La garde doit le protéger comme l'original — sinon le défaut se reforme
    exactement là où on l'a déplacé."""
    repo = _depot_jouet(tmp_path, suivis=("t_1.json", "t_1_rerun.json"))
    monkeypatch.chdir(repo)
    h = Harness(seed=1, name="t", with_db=False)
    assert h.results_path == "results/t_1_rerun2.json"
    assert h.rerun_of == "results/t_1.json"


# --------------------------------------------------------------------------------------------------
# La racine vient de `src/paths.py` (porte 12) — et c'est le mécanisme qui sort les tests de l'arbre
# --------------------------------------------------------------------------------------------------

def test_une_racine_ABSOLUE_via_AGAGI_RESULTS_ROOT_est_interrogee_depuis_SON_depot_pas_depuis_le_cwd(tmp_path, monkeypatch):
    repo = _depot_jouet(tmp_path)
    ailleurs = tmp_path / "ailleurs"
    ailleurs.mkdir()
    monkeypatch.chdir(ailleurs)
    racine = str(repo / "results")
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", racine)
    h = Harness(seed=1, name="t", with_db=False)
    assert h.results_dir == racine
    assert h.results_path == racine + "/t_1_rerun.json"   # `src/paths._sous` joint avec `/`


def test_AGAGI_RESULTS_ROOT_sur_tmp_path_sort_l_ecriture_de_l_arbre(tmp_path, monkeypatch):
    """C'est par ce mécanisme que les tests de fumée des runners (11 fichiers, seeds des mesures
    PUBLIÉES : 99240, 107, 12345, 88113, 88114, 99167, 99140, 99260, 99300, 99280, 2026) n'écrivent
    plus sous `results/` : la racine est relue à CHAQUE construction du Harness."""
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "sorties"))
    h = Harness(seed=99240, name="competence_profile", with_db=False)
    p = h.save({"kpi": 1.0})
    assert os.path.abspath(p).startswith(os.path.abspath(str(tmp_path)))
    assert (tmp_path / "sorties" / "competence_profile_99240.json").exists()
