import numpy as np
from src.agents.mamba_agent import _resolve_dreaming


def _inputs():
    has_mcts = np.array([True, True, False], dtype=bool)
    do_dream = np.array([0.5, 0.05, 0.9], dtype=np.float32)   # agent1 logit haut, agent2 bas
    surprise = np.array([0.9, 0.9, 0.9], dtype=np.float32)    # surprise haute partout
    return has_mcts, do_dream, surprise


def test_resolve_none_is_normal_autoselection():
    has_mcts, do_dream, surprise = _inputs()
    is_dream, K = _resolve_dreaming(None, has_mcts, do_dream, surprise, 0.1, 0.05)
    # agent0 : organe + logit 0.5>0.1 + surprise -> rêve ; agent1 : logit 0.05<0.1 -> non ; agent2 : pas d'organe -> non
    assert list(is_dream) == [True, False, False]
    assert K[0] == int(np.clip(0.5 * 8, 1, 8)) and K[1] == 0 and K[2] == 0


def test_resolve_off_nobody_dreams():
    has_mcts, do_dream, surprise = _inputs()
    is_dream, K = _resolve_dreaming("off", has_mcts, do_dream, surprise, 0.1, 0.05)
    assert not is_dream.any()
    assert (K == 0).all()


def test_resolve_int_forces_carriers_at_depth_K():
    has_mcts, do_dream, surprise = _inputs()
    is_dream, K = _resolve_dreaming(4, has_mcts, do_dream, surprise, 0.1, 0.05)
    # tous les porteurs d'organe rêvent (logit/surprise ignorés), profondeur fixe 4
    assert list(is_dream) == [True, True, False]
    assert K[0] == 4 and K[1] == 4 and K[2] == 0


def test_resolve_bool_not_treated_as_int_K():
    """bool est sous-classe d'int : True NE DOIT PAS forcer K=1 (sinon ABLATE-like accidentel)."""
    has_mcts, do_dream, surprise = _inputs()
    is_dream_true, _ = _resolve_dreaming(True, has_mcts, do_dream, surprise, 0.1, 0.05)
    is_dream_none, _ = _resolve_dreaming(None, has_mcts, do_dream, surprise, 0.1, 0.05)
    assert list(is_dream_true) == list(is_dream_none)    # True traité comme None (normal)
