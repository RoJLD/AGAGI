"""P2.56 (b), troisième fournée — trois instruments MUETS reçoivent une injection à dose connue, 0 monde :

* `tools/transfer_ratio.py::measure` — le maillon `_eras_to_master` est remplacé (curriculum 5 ères, contrôle 10 ères →
  ratio 2,0 ; égaux → 1,0 ; un bras invalide est IGNORÉ et compté ; aucun bras valide → `None`, jamais un nombre) ;
  le journal KuzuDB est neutralisé.
* `tools/s2_fallback_rate_probe.py::measured_floor` — `survive` et `life_seeds` rendent des vies CONNUES (vie = seed + 5) :
  la médiane et les 24 vies publiées sont prédites exactement, et la politique corps-seul est bien celle de `K`.
* `tools/warmstart_evolution_inworld.py::probe_genome_free_channels` — la trajectoire-oracle et la sonde de canaux
  libres sont injectées : la population torch construite porte `num_agents` clones du génome à lr = 0 (le génome n'est
  PAS entraîné par la sonde), et une trajectoire vide rend `None` (absence, pas un résultat).

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

import tools.transfer_ratio as T  # noqa: E402
import tools.s2_fallback_rate_probe as S  # noqa: E402
import tools.warmstart_evolution_inworld as W  # noqa: E402


class _NoLogger:
    def start(self):
        pass

    def stop(self):
        pass


# ---- transfer_ratio.measure ---------------------------------------------------------------------------------------
def test_transfer_ratio_reads_a_known_dose_and_ignores_an_invalid_run_without_inventing(monkeypatch):
    monkeypatch.setattr(T, "async_logger", _NoLogger())
    calls = []

    def _eras(ladder, keep_memory, grad_cfg, **kw):
        calls.append((tuple(ladder), keep_memory))
        return (5, True) if len(ladder) == 2 else (10, True)
    monkeypatch.setattr(T, "_eras_to_master", _eras)
    assert T.measure("stoneage", "agricultural", repeats=2) == pytest.approx(2.0)
    assert calls == [(("stoneage", "agricultural"), True), (("agricultural",), False)] * 2
    assert all(kp is False for lad, kp in calls if len(lad) == 1), "le contrôle tabula rasa n'hérite pas"
    monkeypatch.setattr(T, "_eras_to_master", lambda ladder, km, g, **kw: (7, True))
    assert T.measure("a", "b", repeats=1) == pytest.approx(1.0)                   # égaux : ratio 1, NEUTRE
    monkeypatch.setattr(T, "_eras_to_master", lambda ladder, km, g, **kw: (None, None))
    assert T.measure("a", "b", repeats=3) is None, "aucun bras valide : pas de ratio fabriqué"
    with pytest.raises(ValueError):
        T.measure("a", "b", repeats=0)


def test_transfer_ratio_keeps_only_the_valid_repeats_in_the_mean(monkeypatch):
    monkeypatch.setattr(T, "async_logger", _NoLogger())
    state = {"i": 0}

    def _eras(ladder, keep_memory, grad_cfg, **kw):
        if len(ladder) == 2:
            state["i"] += 1
            return (None, None) if state["i"] == 1 else (4, True)          # 1er run invalide, puis 4 ères
        return (8, True)
    monkeypatch.setattr(T, "_eras_to_master", _eras)
    assert T.measure("a", "b", repeats=3) == pytest.approx(2.0)                   # 8/4 sur les 2 runs valides


# ---- s2_fallback_rate_probe.measured_floor ------------------------------------------------------------------------
def test_measured_floor_publishes_the_median_and_ALL_lives_from_known_seeds(monkeypatch):
    cell = {"K": 4, "body_gain": 1.0, "cog_gain": 0.0, "currency": "e", "ticks": 30}
    seen = {}
    monkeypatch.setattr(S, "body_only_policy", lambda K: seen.setdefault("K", K) and ("W0", "b0") or ("W0", "b0"))
    monkeypatch.setattr(S, "life_seeds", lambda seed, n_eval=24: list(range(seed, seed + n_eval)))

    def _survive(W0, b0, mode, body_gain, cog_gain, currency, K, rng, ticks):
        assert (W0, b0, mode, K, ticks) == ("W0", "b0", "true", 4, 30)
        return int(rng.get_state()[1][0]) + 5                                  # vie = seed + 5 (MT19937 : key[0] = seed)
    monkeypatch.setattr(S, "survive", _survive)
    med, lives = S.measured_floor(cell, seed=100, n_eval=5)
    assert lives == [105, 106, 107, 108, 109] and med == 107.0 and seen["K"] == 4
    with pytest.raises(ValueError):
        S.measured_floor(cell, seed=100, n_eval=0)


# ---- warmstart_evolution_inworld.probe_genome_free_channels -------------------------------------------------------
def test_probe_genome_free_channels_builds_frozen_clones_and_forwards_the_oracle_trajectory(monkeypatch):
    pytest.importorskip("torch")
    from src.agents.backend_torch import TorchPopulationModel
    from src.agents.mamba_agent import MambaAgent
    genome = MambaAgent().genome
    seen = {}
    monkeypatch.setattr(W, "_collect_oracle_trajectory", lambda seed, n, t, m, c: (["o0"], ["t0"]))

    def _probe(pop, obs_seq, tgt_seq):
        seen.update(B=pop.B, lr=pop.lr, cls=type(pop).__name__, obs=obs_seq, tgt=tgt_seq,
                    same_W=all(np.array_equal(a.genome.W, genome.W) for a in pop.agents))
        return {"marker": 42}
    monkeypatch.setattr(W, "_probe_free_channels", _probe)
    out = W.probe_genome_free_channels(genome, seed=1, num_agents=3, max_ticks=5)
    assert out == {"marker": 42}
    assert seen["B"] == 3 and seen["lr"] == 0.0 and seen["cls"] == TorchPopulationModel.__name__ and seen["same_W"]
    assert seen["obs"] == ["o0"] and seen["tgt"] == ["t0"]
    monkeypatch.setattr(W, "_collect_oracle_trajectory", lambda seed, n, t, m, c: ([], []))
    assert W.probe_genome_free_channels(genome, seed=1, num_agents=3, max_ticks=5) is None   # absence, pas un résultat
    with pytest.raises(ValueError):
        W.probe_genome_free_channels(genome, num_agents=0)
