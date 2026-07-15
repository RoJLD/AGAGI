"""TDD S2-003 — ladder de survie (permuted/noise/zero) au-dessus de S2-002. RED avant
implémentation de tools/s2_openloop_probe.py : la survie du champion est-elle indifférente à l'obs
(SURVIVAL_NEUTRAL) ou s'effondre-t-elle sous une ablation (SURVIVAL_SENSITIVE) ?"""
import numpy as np
from src.agents.mamba_agent import MambaBatchModel


def test_noise_obs_feeds_noise(monkeypatch):
    import tools.s2_openloop_probe as mod
    captured = {}

    def fake_parent_forward(self, batch_obs, env_surprise_batch=None):
        captured["obs"] = batch_obs
        return (np.zeros((batch_obs.shape[0], 2)), np.zeros(batch_obs.shape[0]))

    monkeypatch.setattr(MambaBatchModel, "forward", fake_parent_forward, raising=True)
    inst = object.__new__(mod.NoiseObsMamba)      # saute __init__ (pas d'agents)
    np.random.seed(3)
    obs = np.arange(10 * 4, dtype=np.float32).reshape(10, 4)
    before = obs.copy()
    inst.forward(obs)
    assert captured["obs"].shape == obs.shape
    assert not np.array_equal(captured["obs"], obs)     # remplacée par du bruit, pas l'obs d'origine
    assert np.array_equal(obs, before)                  # entrée d'origine INTACTE (pas de mutation)


def test_zero_obs_feeds_zeros(monkeypatch):
    import tools.s2_openloop_probe as mod
    captured = {}

    def fake_parent_forward(self, batch_obs, env_surprise_batch=None):
        captured["obs"] = batch_obs
        return (np.zeros((batch_obs.shape[0], 2)), np.zeros(batch_obs.shape[0]))

    monkeypatch.setattr(MambaBatchModel, "forward", fake_parent_forward, raising=True)
    inst = object.__new__(mod.ZeroObsMamba)        # saute __init__ (pas d'agents)
    obs = (np.arange(10 * 4, dtype=np.float32).reshape(10, 4) + 1.0)  # tout non-nul
    before = obs.copy()
    inst.forward(obs)
    assert captured["obs"].shape == obs.shape
    assert np.array_equal(captured["obs"], np.zeros_like(obs))
    assert np.array_equal(obs, before)              # entrée d'origine INTACTE (pas de mutation)


def test_ladder_wiring(monkeypatch):
    import tools.s2_openloop_probe as mod
    from tools.s2_demand_ablation import PerceptionAblatedMamba

    # cas 1 : les 3 barreaux sont PLATS -> verdict monde SURVIVAL_NEUTRAL
    def _fake_flat(world_cls, batch_model_cls, genome, seed, num_agents=12, max_ticks=200, n_eras=12):
        if batch_model_cls in (None, PerceptionAblatedMamba, mod.NoiseObsMamba, mod.ZeroObsMamba):
            return {"survival": [100.0] * 12, "era_survival": [100.0] * 12}
        raise AssertionError(f"condition inattendue: {batch_model_cls}")

    monkeypatch.setattr(mod, "run_condition", _fake_flat)
    monkeypatch.setattr(mod, "load_champion_genome", lambda: "FAKE_GENOME")
    out = mod.run_openloop_ladder(worlds=["soup"], seed=1, K=12, num_agents=3, max_ticks=10)
    r = out["soup"]
    assert r["intact_med"] == 100.0
    assert r["permuted"]["ratio"] == 1.0
    assert r["noise"]["ratio"] == 1.0
    assert r["zero"]["ratio"] == 1.0
    assert r["permuted"]["n"] == 12
    assert r["noise"]["n"] == 12
    assert r["zero"]["n"] == 12
    assert r["verdict"] == "SURVIVAL_NEUTRAL"

    # cas 2 : le barreau ZERO s'effondre (ratio 5.0 >= collapse_factor) -> SURVIVAL_SENSITIVE
    def _fake_zero_collapse(world_cls, batch_model_cls, genome, seed, num_agents=12, max_ticks=200, n_eras=12):
        if batch_model_cls is mod.ZeroObsMamba:
            return {"survival": [20.0] * 12, "era_survival": [20.0] * 12}
        if batch_model_cls in (None, PerceptionAblatedMamba, mod.NoiseObsMamba):
            return {"survival": [100.0] * 12, "era_survival": [100.0] * 12}
        raise AssertionError(f"condition inattendue: {batch_model_cls}")

    monkeypatch.setattr(mod, "run_condition", _fake_zero_collapse)
    out2 = mod.run_openloop_ladder(worlds=["soup"], seed=1, K=12, num_agents=3, max_ticks=10)
    r2 = out2["soup"]
    assert r2["zero"]["ratio"] == 5.0
    assert r2["permuted"]["ratio"] == 1.0
    assert r2["noise"]["ratio"] == 1.0
    assert r2["verdict"] == "SURVIVAL_SENSITIVE"
