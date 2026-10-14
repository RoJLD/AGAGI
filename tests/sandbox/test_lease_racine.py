"""P2.175 (2026-10-14, trouvé par INTEGRATION-LU) — contre-exemples GELÉS : le dossier des bails ne dépend JAMAIS du cwd.

Le bail de la purge KuzuDB, lancée depuis un scratchpad hors dépôt, est parti dans `<scratchpad>/runs/leases` :
`_repo_root` partait du cwd et s'y rabattait en silence. Invisible à la flotte ; le doctor aurait lu 0 pendant 93 s.
Ici chaque cas tourne dans un VRAI sous-processus dont le cwd est HORS du dépôt, et ne fait que CALCULER le dossier
(`_dir(None)`) : aucun bail n'est écrit, ni ici ni dans le dossier de la flotte. `GIT_*` est retiré de l'environnement
des sous-processus (règle à deux faces), sauf là où un GIT_DIR étranger est posé exprès.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_LEASE_GUARD_EXEMPT = True
_ROOT = Path(__file__).resolve().parents[2]
_LEASE = _ROOT / "tools" / "jobs" / "lease.py"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git introuvable : la racine n'est pas mesurable")


def _env_sans_git(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("PYTHONPATH", None)
    env.update(PYTHONIOENCODING="utf-8", **extra)
    return env


def _racine_commune():
    common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=str(_ROOT), text=True,
                                     env=_env_sans_git()).strip()
    c = Path(common)
    return (c if c.is_absolute() else _ROOT / c).resolve().parent


def _dossier_calcule(cwd, chemin_lease, env):
    """Le `_dir(None)` d'un module lease chargé PAR SON CHEMIN dans un processus neuf, cwd donné."""
    code = ("import importlib.util, sys\n"
            f"spec = importlib.util.spec_from_file_location('lease_temoin', {str(chemin_lease)!r})\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "sys.modules['lease_temoin'] = m\n"
            "spec.loader.exec_module(m)\n"
            "print(m._dir(None))\n")
    r = subprocess.run([sys.executable, "-c", code], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=120)
    assert r.returncode == 0, r.stderr
    return Path(r.stdout.strip().splitlines()[-1]).resolve(), r.stderr


def _hors_depot(tmp_path):
    d = tmp_path / "hors_depot"
    d.mkdir()
    r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=str(d), capture_output=True, text=True,
                       env=_env_sans_git())
    if r.returncode == 0:
        pytest.skip(f"prémisse fausse : {d} est DANS un dépôt git ({r.stdout.strip()})")
    return d


def test_P2_175_CONTRE_EXEMPLE_un_bail_pris_HORS_du_depot_va_dans_runs_leases_du_DEPOT(tmp_path):
    """La forme exacte de l'incident : un processus dont le cwd est hors dépôt, qui importe le module du dépôt."""
    d, err = _dossier_calcule(_hors_depot(tmp_path), _LEASE, _env_sans_git())
    attendu = (_racine_commune() / "runs" / "leases").resolve()
    assert d == attendu, f"bails dans {d}, attendus dans {attendu} : le cwd décide encore"
    assert not str(d).startswith(str(tmp_path.resolve())), d


def test_P2_175_un_GIT_DIR_herite_d_un_AUTRE_depot_ne_detourne_pas_les_bails(tmp_path):
    """Un crochet exporte GIT_DIR : la racine est celle de l'emplacement du MODULE, jamais celle d'un GIT_DIR hérité."""
    autre = tmp_path / "autre_depot"
    autre.mkdir()
    subprocess.run(["git", "init", "-q", str(autre)], check=True, capture_output=True, env=_env_sans_git())
    env = _env_sans_git(GIT_DIR=str(autre / ".git"))
    d, _ = _dossier_calcule(_hors_depot(tmp_path), _LEASE, env)
    assert d == (_racine_commune() / "runs" / "leases").resolve(), d


def test_P2_175_une_COPIE_sans_git_a_ses_bails_dans_SON_arbre_et_le_DIT(tmp_path):
    """Sans dépôt git autour du module (l'image du runner exclut .git/) : l'arbre du module, jamais le cwd, et une
    ligne sur stderr qui le dit."""
    copie = tmp_path / "copie"
    (copie / "tools" / "jobs").mkdir(parents=True)
    shutil.copyfile(_LEASE, copie / "tools" / "jobs" / "lease.py")
    if subprocess.run(["git", "rev-parse"], cwd=str(copie), capture_output=True, env=_env_sans_git()).returncode == 0:
        pytest.skip("prémisse fausse : la copie est dans un dépôt git")
    d, err = _dossier_calcule(_hors_depot(tmp_path), copie / "tools" / "jobs" / "lease.py", _env_sans_git())
    assert d == (copie / "runs" / "leases").resolve(), d
    assert "COPIE isolée" in err, err


def test_P2_175_une_copie_sans_git_LANCEE_depuis_sa_racine_garde_la_racine_d_avant(tmp_path):
    """Le cas du pod nexus (code dans /work, cwd = /work) : l'arbre du module ET le cwd coïncident, donc la racine est
    celle qu'avait l'ancien code — le correctif ne change rien là où le cwd était déjà juste."""
    copie = tmp_path / "work"
    (copie / "tools" / "jobs").mkdir(parents=True)
    shutil.copyfile(_LEASE, copie / "tools" / "jobs" / "lease.py")
    if subprocess.run(["git", "rev-parse"], cwd=str(copie), capture_output=True, env=_env_sans_git()).returncode == 0:
        pytest.skip("prémisse fausse : la copie est dans un dépôt git")
    d, _ = _dossier_calcule(copie, copie / "tools" / "jobs" / "lease.py", _env_sans_git())
    assert d == (copie / "runs" / "leases").resolve(), d


def test_P2_175_un_cwd_EXPLICITE_garde_le_comportement_choisi_par_l_appelant(tmp_path):
    """Spécificité : l'ancre au module ne vaut que SANS argument ; `_repo_root(cwd=…)` (doctor, tests) part de ce cwd."""
    from tools.jobs import lease as L
    hors = _hors_depot(tmp_path)
    assert L._repo_root(cwd=hors).resolve() == hors.resolve()
