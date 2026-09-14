"""P1.6 — l'APPRENANT in-world est un instrument : sa DOSE se compte, ses variantes se déclarent.

Contexte (backlog, bloc « 🧭 2026-09-14 », fait neuf n° 1) : les nuls « le crédit n'apprend pas à froid »
(S2-009 §crédit, S2-010, S2-011) ont été publiés SANS jamais compter combien de mises à jour l'apprenant
avait reçues — le TD(0) par tick n'est nommé par aucun record, et le panel a compté ≈ 48 mises à jour par
agent. `tools/learning_events.count_learning_events` est le compteur, en context manager posé sur le
backend torch et RESTAURÉ en `finally` ; ses deux flags de variante (`td_enabled`, `reward_scale`) et
l'override `lr` sont BIT-IDENTIQUES par défaut — c'est la première chose que ce fichier prouve.

Aucun monde n'est simulé ici : tout se joue sur une population torch de 3 agents, en quelques dizaines
de millisecondes. Les cas qui traversent le monde vivent dans `test_instrument_calibration.py`
(`run_learner_probe`, `learner_verdict`).
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("torch")

from src.agents.backend_torch import TorchPopulationModel  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402
from tools.cognitive_demand_inworld import _pinned_substrate  # noqa: E402
from tools.learning_events import count_learning_events  # noqa: E402

_B = 3
_ACT = [{"move": 0, "grab": 0, "rub": 0}] * _B
_REW = np.array([1.0, -1.0, 0.5], dtype=np.float32)


def _pop(seed=0, **kw):
    """Population torch de 3 agents FRAIS, déterministe (génomes tirés sous `seed`)."""
    np.random.seed(seed)
    agents = [MambaAgent() for _ in range(_B)]
    with _pinned_substrate():
        return TorchPopulationModel(agents, **kw)


def _obs(pop, seed=11):
    """Observation NON NULLE et déterministe : avec une obs nulle, H vaut 0 et le gradient sur W est
    exactement nul — l'update a lieu mais ne bouge rien (mesuré en écrivant ce fichier)."""
    return np.random.RandomState(seed).uniform(-1.0, 1.0, (pop.B, pop.I)).astype(np.float32)


def _drive(pop, n=3, rewards=_REW):
    """n ticks : forward puis learn (TD). Le premier learn d'une vie est DIFFÉRÉ (rend None)."""
    obs = _obs(pop)
    out = []
    for _ in range(n):
        pop.forward(obs)
        out.append(pop.learn(rewards, _ACT))
    return out


def _W(pop):
    return pop.W.detach().cpu().numpy().copy()


def test_counter_counts_td_and_episode_calls_and_restores_the_class():
    orig_learn, orig_ep = TorchPopulationModel.learn, TorchPopulationModel.learn_episode
    with count_learning_events() as ev:
        pop = _pop()
        rets = _drive(pop, n=3)
        obs = _obs(pop)
        pop.learn_episode([obs, obs], [_ACT, _ACT], np.ones(pop.B, dtype=np.float32))
    assert rets[0] is None and rets[1] is not None          # 1er learn différé, les suivants mettent à jour
    assert ev.td_calls == 3
    assert ev.td_updates == 2
    assert ev.episode_calls == 1
    assert TorchPopulationModel.learn is orig_learn          # restauré : le compteur ne survit pas au `with`
    assert TorchPopulationModel.learn_episode is orig_ep


def test_default_flags_are_bit_identical_to_the_bare_backend():
    bare = _pop(seed=7)
    _drive(bare, n=4)
    with count_learning_events() as ev:
        wrapped = _pop(seed=7)
        _drive(wrapped, n=4)
    assert np.array_equal(_W(bare), _W(wrapped)), "le compteur seul (scale 1.0, TD on) doit être un no-op EXACT"
    assert ev.td_updates == 3


def test_td_disabled_skips_every_update_and_says_why():
    with count_learning_events(td_enabled=False) as ev:
        pop = _pop(seed=3)
        w0 = _W(pop)
        rets = _drive(pop, n=3)
    assert all(r is None for r in rets)
    assert np.array_equal(w0, _W(pop)), "TD coupé : aucun poids ne bouge"
    assert ev.td_calls == 3 and ev.td_updates == 0
    assert ev.skips == {"td_disabled": 3}


def test_reward_scale_changes_the_update_and_is_published():
    ref = _pop(seed=5)
    _drive(ref, n=3)
    with count_learning_events(reward_scale=0.05) as ev:
        scaled = _pop(seed=5)
        _drive(scaled, n=3)
    assert not np.array_equal(_W(ref), _W(scaled)), "×0,05 doit produire une mise à jour DIFFÉRENTE"
    assert ev.summary()["reward_scale"] == 0.05
    assert ev.summary()["td_enabled"] is True


def test_lr_override_reaches_the_optimizer_and_is_restored():
    with count_learning_events(lr=0.004):
        pop = _pop(seed=1)
        assert pop.opt.param_groups[0]["lr"] == pytest.approx(0.004)
    pop2 = _pop(seed=1)
    assert pop2.opt.param_groups[0]["lr"] == pytest.approx(0.04), "hors du `with`, le défaut du backend"


def test_dW_accumulates_only_when_an_update_happens():
    with count_learning_events(td_enabled=False) as off:
        _drive(_pop(seed=2), n=3)
    with count_learning_events() as on:
        _drive(_pop(seed=2), n=3)
    assert off.dW_abs_sum == 0.0
    assert on.dW_abs_sum > 0.0


def test_restores_the_class_even_on_exception():
    orig_learn, orig_init = TorchPopulationModel.learn, TorchPopulationModel.__init__
    with pytest.raises(RuntimeError):
        with count_learning_events(lr=0.001):
            raise RuntimeError("boom")
    assert TorchPopulationModel.learn is orig_learn
    assert TorchPopulationModel.__init__ is orig_init


def test_episode_skip_reasons_emitted_by_the_world_are_counted():
    from src.worlds.world_1_stoneage import logger
    with count_learning_events() as ev:
        logger.emit("TORCH_EPISODE_SKIP", {"reason": "pop_desync", "tick": 8})
        logger.emit("TORCH_EPISODE_SKIP", {"reason": "id_missing", "tick": 16})
        logger.emit("TORCH_EPISODE_SKIP", {"reason": "id_missing", "tick": 24})
    assert ev.skips == {"pop_desync": 1, "id_missing": 2}


def test_summary_is_complete_and_serialisable():
    import json
    with count_learning_events(reward_scale=0.5, td_enabled=True, lr=0.01) as ev:
        _drive(_pop(seed=4), n=2)
    s = ev.summary()
    for k in ("td_calls", "td_updates", "episode_calls", "episode_updates", "skips", "dW_abs_sum",
              "reward_scale", "td_enabled", "lr"):
        assert k in s, k
    json.dumps(s)                                             # publiable tel quel dans un results/*.json
