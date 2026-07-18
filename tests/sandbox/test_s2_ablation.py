import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent
from src.agents.ablation_models import ObsAblatedMambaBatchModel


class _RecordingInner:
    """Stub du MambaBatchModel interne : enregistre l'obs reçue, renvoie des sorties factices."""
    def __init__(self):
        self.seen = None
    def forward(self, batch_obs, env_surprise_batch=None):
        self.seen = np.asarray(batch_obs).copy()
        B = batch_obs.shape[0]
        return np.zeros((B, 2), dtype=np.float32), np.zeros(B, dtype=np.float32)
    def compute_policy_gradient(self, *a, **k):
        self.grad_called = True
        return


def test_ablation_shuffles_rows_decorrelates():
    agents = [MambaAgent() for _ in range(8)]
    w = ObsAblatedMambaBatchModel(agents)
    w._inner = _RecordingInner()                         # intercepte l'obs vue par le champion
    obs = (np.arange(8)[:, None] * np.ones((1, 3))).astype(np.float64)   # ligne i = [i,i,i] distinctes
    non_identity = False
    for _ in range(5):
        np.random.seed(1 + _)
        w.forward(obs)
        seen = w._inner.seen
        assert seen.shape == obs.shape
        assert sorted(seen[:, 0].tolist()) == sorted(obs[:, 0].tolist())   # PERMUTATION (mêmes lignes)
        if not np.array_equal(seen, obs):
            non_identity = True
    assert non_identity                                  # le shuffle décorrèle bien (pas un no-op)


def test_ablation_determinism():
    agents = [MambaAgent() for _ in range(6)]
    obs = (np.arange(6)[:, None] * np.ones((1, 3))).astype(np.float64)
    w1 = ObsAblatedMambaBatchModel(agents); w1._inner = _RecordingInner()
    w2 = ObsAblatedMambaBatchModel(agents); w2._inner = _RecordingInner()
    np.random.seed(42); w1.forward(obs); s1 = w1._inner.seen
    np.random.seed(42); w2.forward(obs); s2 = w2._inner.seen
    assert np.array_equal(s1, s2)


def test_ablation_empty_batch():
    w = ObsAblatedMambaBatchModel([])
    w._inner = _RecordingInner()
    logits, comp = w.forward(np.zeros((0, 3), dtype=np.float64))
    assert logits.shape[0] == 0 and comp.shape[0] == 0


def test_ablation_delegates_grad():
    agents = [MambaAgent() for _ in range(4)]
    w = ObsAblatedMambaBatchModel(agents); w._inner = _RecordingInner()
    w.compute_policy_gradient(np.zeros(4))
    assert getattr(w._inner, "grad_called", False)


from src.seed_ai.s2_stats import verdict_within_subject


def _cond(center, n=12, spread=4.0):
    """Condition synthétique : survie centrée sur `center` (era = n médianes, pooled = 4n individus)."""
    era = list(np.linspace(center - spread, center + spread, n))
    pooled = list(np.linspace(center - spread, center + spread, 4 * n))
    return {"survival": pooled, "era_survival": era}


def test_within_verdict_causal_full():
    # champion (45) >> ablaté (15) ; ablaté ~ random (15) -> perception explique TOUT -> CAUSAL-FULL
    r = verdict_within_subject(_cond(45), _cond(15), _cond(15))
    assert r["verdict"] == "CAUSAL-FULL"
    assert r["is_causal"] and r["edge_fully_perceptual"]


def test_within_verdict_causal_partiel():
    # champion (45) >> ablaté (25) ; ablaté (25) >> random (10) -> perception explique une PART -> PARTIEL
    r = verdict_within_subject(_cond(45), _cond(25), _cond(10))
    assert r["verdict"] == "CAUSAL-PARTIEL"
    assert r["is_causal"] and not r["edge_fully_perceptual"]


def test_within_verdict_non_causal():
    # champion (45) ~ ablaté (44) -> ablater la perception NE nuit PAS -> NON-CAUSAL
    r = verdict_within_subject(_cond(45), _cond(44), _cond(10))
    assert r["verdict"] == "NON-CAUSAL"
    assert not r["is_causal"]


def test_within_verdict_causal_critique():
    # champion (45) >> ablaté (8) ; ablaté (8) PIRE que random (15) -> perception essentielle -> CAUSAL-CRITIQUE
    r = verdict_within_subject(_cond(45), _cond(8), _cond(15))
    assert r["verdict"] == "CAUSAL-CRITIQUE"
    assert r["is_causal"]


from tools.s2_demand import CONDITIONS as S2_CONDITIONS, _within_block


def test_condition_registered():
    assert "champion_obs_ablated" in S2_CONDITIONS
    spec = S2_CONDITIONS["champion_obs_ablated"]
    assert spec["fresh_genome"] is False              # MÊME génome champion
    assert spec["batch_model_cls"] is ObsAblatedMambaBatchModel


def test_within_block_from_conds():
    # _within_block extrait champion / champion_obs_ablated / random_action et rend le verdict
    conds = {"champion": _cond(45), "champion_obs_ablated": _cond(15), "random_action": _cond(15)}
    r = _within_block(conds)
    assert r["verdict"] in {"CAUSAL-FULL", "CAUSAL-PARTIEL", "CAUSAL-CRITIQUE", "NON-CAUSAL"}
    assert r["verdict"] == "CAUSAL-FULL"
