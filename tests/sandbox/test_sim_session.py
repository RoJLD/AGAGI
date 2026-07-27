"""Tests de la primitive d'isolation. Chaque test encode une violation RÉELLE du 2026-07-21 :
si un test échoue, la garde correspondante ne protège plus contre une erreur déjà commise."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.sim_session import sim_session, SimBusyError, _LOCK_PATH  # noqa: E402


def test_lock_forbids_concurrent_sims():
    """VIOLATION RÉELLE (moi, 2×) : sonde monde lancée en parallèle de la suite -> contention KuzuDB,
    mesure contaminée + suite en timeout. Le verrou doit rendre ça IMPOSSIBLE, pas déconseillé."""
    with sim_session():
        with pytest.raises(SimBusyError, match="parallél|contention|détient"):
            with sim_session():
                pass


def test_lock_is_released_even_on_exception():
    """Un verrou orphelin bloquerait toutes les sessions suivantes : la libération doit survivre
    à une exception."""
    with pytest.raises(ValueError):
        with sim_session():
            raise ValueError("boom")
    assert not os.path.exists(_LOCK_PATH), "verrou ORPHELIN laissé après exception"
    with sim_session():                                   # doit pouvoir re-verrouiller
        pass


def test_isolate_stops_the_retriever_before_the_loop():
    """VIOLATION RÉELLE (code d'instrument) : `_torch_survival_eras` laissait `memory_retriever` ACTIF
    pendant la boucle de simulation — mémoire ambiante KuzuDB, runs non reproductibles."""
    class _Retriever:
        def __init__(self):
            self._running = True
            self.cleared = False

        def stop(self):
            self._running = False

        def clear(self):
            self.cleared = True

    class _World:
        def __init__(self):
            self.memory_retriever = _Retriever()

    w = _World()
    with sim_session() as s:
        assert w.memory_retriever._running is True        # avant : actif
        s.isolate(w)
        assert w.memory_retriever._running is False, "retriever non arrêté"
        assert w.memory_retriever.cleared is True, "retriever non vidé"
        assert s.assert_isolated(w) is True


def test_assert_isolated_rejects_a_running_retriever():
    """Le témoin doit ÉCHOUER sur un monde non isolé — sinon il ne protège de rien."""
    class _R:
        _running = True

    class _W:
        memory_retriever = _R()

    with sim_session() as s:
        with pytest.raises(AssertionError, match="ACTIF"):
            s.assert_isolated(_W())


def test_real_world_is_isolated_by_the_primitive():
    """Bout-en-bout sur un vrai monde : après `isolate`, plus aucun retriever ne tourne."""
    pytest.importorskip("torch")
    from tools.ground_truth_worlds import GroundTruthCarryWorld
    with sim_session() as s:
        w = GroundTruthCarryWorld()
        w.benchmark_mode = True
        w.night_enabled = False
        s.isolate(w)
        assert s.assert_isolated(w) is True
