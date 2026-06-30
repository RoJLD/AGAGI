# tests/sandbox/test_substrate_ab_compositional.py
import pytest
import numpy as np

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


from tools.substrate_ab_compositional import _init_factor, _build_agents


def test_init_factor_anchor_is_one():
    """À num_nodes=172 (hidden=5), le facteur normalisé == 1.0 → normalized ≡ prod (dédup ancrage)."""
    assert _init_factor(172, "normalized") == 1.0
    assert _init_factor(172, "prod") == 1.0


def test_init_factor_normalized_formula():
    """Facteur normalisé = sqrt(171/(N-1)) ; prod toujours 1.0 quelle que soit la taille."""
    assert _init_factor(267, "normalized") == pytest.approx(np.sqrt(171.0 / 266.0))
    assert _init_factor(187, "normalized") == pytest.approx(np.sqrt(171.0 / 186.0))
    assert _init_factor(267, "prod") == 1.0


def test_build_agents_size_mapping():
    """num_nodes contrôle la taille ; I/O restent fixes (59/108) ; hidden = num_nodes-167."""
    agents = _build_agents(3, 187, "prod")
    assert len(agents) == 3
    for a in agents:
        assert a.genome.num_nodes == 187
        assert a.genome.num_inputs == 59
        assert a.genome.num_outputs == 108


def test_build_agents_normalized_scales_W():
    """init normalisé multiplie W par sqrt(171/(N-1)) ; prod laisse W intact (même seed)."""
    np.random.seed(7)
    prod = _build_agents(2, 267, "prod")
    np.random.seed(7)
    norm = _build_agents(2, 267, "normalized")
    factor = np.sqrt(171.0 / 266.0)
    for p, q in zip(prod, norm):
        assert np.allclose(q.genome.W, p.genome.W * factor, atol=1e-5)


@pytest.mark.slow
def test_sweep_smoke():
    """sweep renvoie une cellule par (hidden,init) avec verdict structuré + courbe non vide."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep
    res = sweep(hiddens=(5, 20), inits=("prod",), seeds=(0,), trials=20, n_agents=4)
    assert res["cells"] and len(res["cells"]) == 2
    for c in res["cells"]:
        assert c["verdict"] in {"GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE"}
        assert c["hidden"] in (5, 20) and c["init"] == "prod"
        assert c["per_seed"] and len(c["per_seed"]) == 1
    assert len(res["curve"]["legacy"]) == 2 and len(res["curve"]["torch"]) == 2
    assert all("median_hit_end" in p for p in res["curve"]["torch"])
