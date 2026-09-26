# -*- coding: utf-8 -*-
"""E4 (occ. doctor, 2026-09-22) — le DOCTOR affirmait un état NÉGATIF que sa propre fonction de vérité
contredisait, sur les deux moitiés de son rapport.

Mesuré le 2026-09-22, sur un run RÉEL de six jours (`python -m tools.evo_runs.s2_blind_champion_bis
--decomp`, pid 54476, 623 Mo, 5/7 seeds faits) :

 * `python -m tools.jobs.doctor` affichait **« processus python du projet : 0 »** alors que ce run
   tournait. Cause : `project_processes` filtre `PROJECT_MARKERS = ("AGAGI",)` sur la LIGNE DE COMMANDE.
   Or la forme canonique du dépôt — celle que CLAUDE.md prescrit, `python -m tools.…` lancé DEPUIS le
   projet — ne contient pas le nom du projet. Le `cwd` du processus, lui, EST le projet ; le code ne le
   regardait jamais. C'est la garde même d'E4 : « quand un instrument réel passe à travers, élargir
   l'heuristique dans la MÊME passe — sinon le compteur ment dans le sens rassurant ».
 * la ligne de tête disait **« bails : 0 vivant(s), 1 mort(s) »** pour un bail dont le détenteur VIT
   (TTL dépassé parce que la machine a dormi, heartbeat manquant). `is_holder_alive()` existe, rend
   `True`, et le chemin `--kill` l'appelle (il REFUSE de tuer) — mais le RAPPORT ne l'appelait pas :
   « mort » était l'étiquette, « détenteur vivant » un détail entre crochets.

Les deux ensemble se lisent « le run est mort » : c'est la conclusion que j'en ai tirée, et elle était
fausse. Ce que l'outil doit dire d'un détenteur vivant sans heartbeat, c'est EXPIRÉ, jamais ORPHELIN.

⚠️ Les deux cas de visibilité lancent un VRAI processus (une veille de quelques secondes, tuée en
`finally`) : un mock de `psutil` testerait le mock, pas la détection. Le contrôle de SPÉCIFICITÉ est
apparié — même commande, même interpréteur, `cwd` HORS du projet — sinon « tout détecter » passerait.
"""
import os
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.jobs import doctor as D  # noqa: E402
from tools.jobs import lease as _lease  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SLEEP = "import time; time.sleep(45)"


@pytest.fixture
def dormeur():
    """Lance un python de veille dans un cwd donné ; le tue en sortie. Rend (spawn, procs)."""
    enfants = []

    def spawn(cwd):
        p = subprocess.Popen([sys.executable, "-c", _SLEEP], cwd=str(cwd),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        enfants.append(p)
        for _ in range(100):                     # psutil doit voir le processus avant qu'on l'interroge
            if _lease.proc_create_time(p.pid) is not None:
                break
            time.sleep(0.05)
        return p

    try:
        yield spawn
    finally:
        for p in enfants:
            p.kill()
            p.wait(timeout=10)


def _pids(procs):
    return {p["pid"] for p in procs}


def test_un_run_lance_a_la_FORME_CANONIQUE_est_VU(dormeur):
    """Le cas RÉEL : `python -c/-m …` depuis le projet — aucun « AGAGI » dans la ligne de commande."""
    p = dormeur(_ROOT)
    cmdline_du_cas = f"{sys.executable} -c {_SLEEP}"
    assert not any(m in cmdline_du_cas for m in D.PROJECT_MARKERS), (
        "prémisse du test : la ligne de commande ne doit PAS porter le marqueur, sinon le cas "
        "ne reproduit pas le défaut")
    assert p.pid in _pids(D.project_processes()), (
        "un run lancé depuis le projet est INVISIBLE au doctor -> « 0 processus » lu comme « rien ne tourne »")


def test_un_processus_HORS_projet_n_est_PAS_vu(dormeur, tmp_path):
    """SPÉCIFICITÉ appariée : même interpréteur, même commande, cwd hors du projet -> non détecté.
    Sans ce cas, « détecter tout » ferait passer le test précédent."""
    p = dormeur(tmp_path)
    assert p.pid not in _pids(D.project_processes())


def test_un_processus_lance_depuis_un_worktree_FRERE_est_VU(dormeur, tmp_path, monkeypatch):
    """CONTRE-EXEMPLE GELÉ (2026-09-26, trouvé par agagi-40) : le doctor lancé DEPUIS un worktree ne voyait ni l'arbre
    principal ni les worktrees frères — `_ROOT` valait la racine de SON worktree. Un vrai dépôt jetable A, deux
    worktrees W1 et W2 ; le doctor « tourne » depuis W1 (`_ROOT`). Un processus dans W2 et un dans A sont VUS ; un
    processus hors du dépôt ne l'est pas (spécificité appariée, même commande)."""
    import shutil
    if shutil.which("git") is None:
        pytest.skip("git introuvable")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    a = tmp_path / "A"
    a.mkdir()
    for args in (["init", "-q"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "b"],
                 ["worktree", "add", "-q", str(tmp_path / "W1"), "-b", "w1"],
                 ["worktree", "add", "-q", str(tmp_path / "W2"), "-b", "w2"]):
        subprocess.run(["git", *args], cwd=str(a), env=env, check=True, capture_output=True)
    hors = tmp_path / "hors"
    hors.mkdir()
    monkeypatch.setattr(D, "_ROOT", str(tmp_path / "W1"))    # le doctor tourne DEPUIS le worktree W1
    monkeypatch.setattr(D, "_RACINES", None)
    import psutil
    frere, principal, dehors = dormeur(tmp_path / "W2"), dormeur(a), dormeur(hors)
    assert D._works_in_project(psutil.Process(frere.pid)), "un run dans un worktree FRÈRE est invisible"
    assert D._works_in_project(psutil.Process(principal.pid)), "un run dans l'arbre PRINCIPAL est invisible"
    assert not D._works_in_project(psutil.Process(dehors.pid)), "un processus HORS du dépôt est compté"


def _bail(tmp_path, pid, *, expire, resource="kuzu-test"):
    """Écrit un bail sur `pid` (create_time RÉEL, sinon is_holder_alive le juge réattribué)."""
    ct = _lease.proc_create_time(pid) or 0.0
    now = time.time()
    lz = _lease.Lease(resource=resource, pid=pid, proc_create_time=ct, owner="cas-de-test",
                      created=now - 10_000, ttl_s=5400.0,
                      expires_at=(now - 1.0) if expire else (now + 5400.0),
                      last_heartbeat=now - 10_000)
    _lease._write(lz, tmp_path)
    return lz


def test_un_bail_EXPIRE_dont_le_detenteur_VIT_n_est_pas_un_ORPHELIN(dormeur, tmp_path):
    """Le cas RÉEL : la machine a dormi, le TTL est dépassé, le run TOURNE. `expired_alive`, pas `orphan`."""
    p = dormeur(_ROOT)
    lz = _bail(tmp_path, p.pid, expire=True)
    assert _lease.is_holder_alive(lz) is True, "prémisse : le détenteur doit être vivant"
    cls = D.classify_leases(leases_dir=tmp_path)
    assert [x.pid for x in cls["expired_alive"]] == [p.pid]
    assert cls["orphan"] == []
    assert cls["live"] == []
    assert [x.pid for x in cls["dead"]] == [p.pid], "compat : `dead` reste l'union (le --kill le lit)"


def test_un_bail_dont_le_detenteur_est_MORT_est_un_ORPHELIN(dormeur, tmp_path):
    """CONTRÔLE apparié qui peut échouer : même bail, détenteur RÉELLEMENT parti -> orphelin."""
    p = dormeur(_ROOT)
    pid, ct = p.pid, _lease.proc_create_time(p.pid)
    p.kill()
    p.wait(timeout=10)
    for _ in range(50):
        if _lease.proc_create_time(pid) is None:
            break
        time.sleep(0.1)
    lz = _lease.Lease(resource="kuzu-test", pid=pid, proc_create_time=ct or 0.0, owner="cas-de-test",
                      created=time.time() - 10_000, ttl_s=5400.0, expires_at=time.time() - 1.0,
                      last_heartbeat=time.time() - 10_000)
    _lease._write(lz, tmp_path)
    cls = D.classify_leases(leases_dir=tmp_path)
    assert [x.pid for x in cls["orphan"]] == [pid]
    assert cls["expired_alive"] == []


def test_un_bail_VIVANT_n_est_ni_expire_ni_orphelin(dormeur, tmp_path):
    p = dormeur(_ROOT)
    _bail(tmp_path, p.pid, expire=False)
    cls = D.classify_leases(leases_dir=tmp_path)
    assert [x.pid for x in cls["live"]] == [p.pid]
    assert cls["expired_alive"] == [] and cls["orphan"] == [] and cls["dead"] == []


def test_le_RAPPORT_ne_dit_pas_mort_pour_un_detenteur_vivant(dormeur, tmp_path, capsys, monkeypatch):
    """Ce que l'humain LIT — la ligne de tête et l'étiquette. C'est CE texte qui m'a fait écrire « le run
    est mort » : « mort » ne doit jamais y désigner un détenteur vivant."""
    p = dormeur(_ROOT)
    _bail(tmp_path, p.pid, expire=True)
    vrai = D.classify_leases
    monkeypatch.setattr(D, "classify_leases", lambda **kw: vrai(leases_dir=tmp_path))
    monkeypatch.setattr(D, "project_processes", lambda older_min=0.0: [])
    assert D.main([]) == 0
    out = capsys.readouterr().out
    assert "EXPIRÉ" in out and "détenteur VIVANT" in out, out
    assert f"pid={p.pid}" in out
    assert "0 orphelin" in out.lower(), out
    tete = out.splitlines()[0].lower()
    assert "mort" not in tete, f"la ligne de tête dit encore « mort » pour un détenteur vivant : {tete!r}"
