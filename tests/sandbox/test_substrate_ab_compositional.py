# tests/sandbox/test_substrate_ab_compositional.py
import pytest

from tools.substrate_ab_compositional import compositional_reward


def test_compositional_reward_truth_table():
    """Récompense étape 2 = +1 SSI (Y correct ET X fait en S1), −1 sinon (les 4 cas)."""
    assert compositional_reward(move2=4, target_y=4, did_x=True) == 1.0    # X✓ Y✓
    assert compositional_reward(move2=4, target_y=4, did_x=False) == -1.0  # X✗ Y✓ : Y seul ne paie pas
    assert compositional_reward(move2=2, target_y=4, did_x=True) == -1.0   # X✓ Y✗
    assert compositional_reward(move2=2, target_y=4, did_x=False) == -1.0  # X✗ Y✗


@pytest.mark.slow
def test_compositional_ab_smoke():
    """Le banc A/B tourne pour les deux backends et renvoie un verdict structuré."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare
    res = compare(seeds=(0,), trials=30, n_agents=4)
    assert res["verdict"] in {"GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for k in ("legacy_delta", "torch_delta", "diff"):
        assert k in row
