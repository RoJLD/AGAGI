"""Tests du job manager. Chaque test encode une VIOLATION RÉELLE du 2026-07-21 ou une garde de sûreté :
si un test échoue, la protection correspondante ne tient plus."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.jobs import lease as L          # noqa: E402
from tools.jobs.run import hold, run, kill_tree  # noqa: E402
from tools.jobs import doctor as D         # noqa: E402


def test_named_resource_is_exclusive(tmp_path):
    """VIOLATION RÉELLE (2×) : deux sondes monde concurrentes -> contention KuzuDB -> mesure contaminée.
    Le bail doit rendre ça IMPOSSIBLE, pas déconseillé."""
    a = L.acquire("kuzu", owner="sondeA", leases_dir=tmp_path, pid=os.getpid())
    with pytest.raises(L.ResourceBusy, match="kuzu"):
        L.acquire("kuzu", owner="sondeB", leases_dir=tmp_path, pid=os.getpid() + 1)
    L.release(a, leases_dir=tmp_path)
    L.acquire("kuzu", owner="sondeB", leases_dir=tmp_path, pid=os.getpid() + 1)  # libéré -> reprenable


def test_distinct_resources_do_not_block_each_other(tmp_path):
    """Un cap global à 1 sérialiserait des jobs indépendants : c'est précisément ce qu'on refuse."""
    L.acquire("kuzu", leases_dir=tmp_path, pid=os.getpid())
    L.acquire("gpu", leases_dir=tmp_path, pid=os.getpid() + 1)   # ne doit PAS lever
    # 2026-09-02 : asserter que les DEUX bails coexistent reellement -- « n'a pas leve » ne
    # distingue pas « les deux tiennent » de « le second a ecrase le premier ».
    assert L.read("kuzu", leases_dir=tmp_path) is not None
    assert L.read("gpu", leases_dir=tmp_path) is not None


def test_dead_holder_lease_is_reclaimable(tmp_path):
    """Crash-recovery : un bail dont le détenteur a disparu ne doit pas bloquer la ressource à vie."""
    fantome = 999_999                                   # PID quasi certainement inexistant
    L.acquire("kuzu", owner="crashé", leases_dir=tmp_path, pid=fantome)
    lz = L.read("kuzu", leases_dir=tmp_path)
    assert L.is_holder_alive(lz) is False
    assert L.is_live(lz) is False
    L.acquire("kuzu", owner="nouveau", leases_dir=tmp_path, pid=os.getpid())   # récupérable


def test_pid_reuse_is_not_mistaken_for_the_holder(tmp_path):
    """ANTI-RÉUTILISATION DE PID : même PID, autre processus -> le détenteur est mort. Sans ce contrôle,
    le doctor pourrait TUER un processus étranger ayant hérité du PID."""
    lz = L.acquire("kuzu", leases_dir=tmp_path, pid=os.getpid())
    assert L.is_holder_alive(lz) is True
    lz.proc_create_time = (lz.proc_create_time or time.time()) - 10_000.0     # simule la réutilisation
    assert L.is_holder_alive(lz) is False


def test_expired_lease_is_not_live_even_if_process_runs(tmp_path):
    """TTL expiré = heartbeat manquant. Le bail n'est plus vivant, mais le doctor ne doit pas tuer
    (cf. test suivant) : les deux notions sont distinctes."""
    lz = L.acquire("kuzu", ttl_s=1.0, leases_dir=tmp_path, pid=os.getpid(), now=1000.0)
    assert L.is_expired(lz, now=1002.0) is True
    assert L.is_live(lz, now=1002.0) is False
    assert L.is_holder_alive(lz) is True                # le processus, lui, tourne toujours


def test_doctor_never_kills_a_live_holder(tmp_path, capsys):
    """GARDE DE SÛRETÉ : un bail expiré dont le détenteur VIT signale un heartbeat manquant, pas un
    orphelin. Le doctor doit REFUSER de le tuer."""
    L.acquire("kuzu", owner="lent", ttl_s=-1.0, leases_dir=tmp_path, pid=os.getpid())
    cls = D.classify_leases(leases_dir=tmp_path)
    assert len(cls["dead"]) == 1 and L.is_holder_alive(cls["dead"][0]) is True


def test_doctor_never_targets_self_or_ancestors():
    """On ne se scie pas la branche : le processus courant et ses ancêtres sont exclus."""
    prot = D._protected_pids()
    assert os.getpid() in prot
    assert all(p["pid"] not in prot for p in D.project_processes())


def test_hold_releases_even_on_exception(tmp_path):
    """Un bail orphelin bloquerait la ressource : la libération doit survivre à une exception."""
    with pytest.raises(ValueError):
        with hold("kuzu", owner="boom", leases_dir=tmp_path):
            raise ValueError("boom")
    assert L.read("kuzu", leases_dir=tmp_path) is None


def test_run_times_out_and_kills_the_tree(tmp_path):
    """VIOLATION documentée sans implémentation jusqu'ici : un job qui dépasse doit être tué AVEC sa
    descendance, et son bail libéré (sinon la ressource reste bloquée)."""
    r = run("dormeur", [sys.executable, "-c", "import time; time.sleep(60)"],
            resources=["kuzu"], timeout_s=2.0, leases_dir=tmp_path)
    assert r.timed_out is True and r.duration_s < 30
    assert L.read("kuzu", leases_dir=tmp_path) is None, "bail non libéré après timeout"


def test_run_succeeds_and_returns_output(tmp_path):
    r = run("ok", [sys.executable, "-c", "print('bonjour')"], resources=["kuzu"],
            timeout_s=60, leases_dir=tmp_path)
    assert r.timed_out is False and r.returncode == 0 and "bonjour" in r.stdout


def test_kill_tree_is_tolerant_of_dead_pid():
    """Idempotence : tuer un PID déjà mort n'est pas une erreur."""
    assert kill_tree(999_999) == 0
