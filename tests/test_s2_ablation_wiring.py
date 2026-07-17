# tests/test_s2_ablation_wiring.py
"""Fast wiring test for run_ablation_map: no real world, fake run_condition -> lock era-pairing,
between arithmetic, and X_->PERCEPTION_ verdict mapping against silent regressions."""
import tools.s2_demand_ablation as mod
from tools.s2_demand_ablation import PerceptionAblatedMamba
from src.agents.baseline_models import ReflexBatchModel


def _fake_run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400, n_eras=12):
    # distingue les 3 conditions par batch_model_cls ; renvoie des survies contrôlées, n=12 ères
    if batch_model_cls is None:                       # intact
        return {"survival": [100.0] * 12, "era_survival": [100.0] * 12}
    if batch_model_cls is PerceptionAblatedMamba:      # ablated : effondrement 5x
        return {"survival": [20.0] * 12, "era_survival": [20.0] * 12}
    if batch_model_cls is ReflexBatchModel:            # réflexe (between)
        return {"survival": [10.0] * 12, "era_survival": [10.0] * 12}
    raise AssertionError(f"condition inattendue: {batch_model_cls}")


def test_run_ablation_map_wiring(monkeypatch):
    monkeypatch.setattr(mod, "run_condition", _fake_run_condition)
    monkeypatch.setattr(mod, "load_champion_genome", lambda: "FAKE_GENOME")
    m = mod.run_ablation_map(worlds=["stoneage"], seed=1, K=12, num_agents=3, max_ticks=10)
    r = m["stoneage"]
    assert r["within_ratio"] == 5.0            # 100/20 : within lit BIEN era_survival (pas pooled)
    assert r["between_ratio"] == 10.0          # 100/10 : between lit BIEN survival poolée / réflexe
    assert r["verdict"] == "PERCEPTION_DEMANDED"   # X_DEMANDED mappé -> PERCEPTION_DEMANDED
    assert r["n"] == 12
