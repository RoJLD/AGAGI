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


def test_normalized_anchor_equals_prod_factor():
    """À l'ancrage (num_nodes=172, hidden=5), normalized et prod ont le MÊME facteur (1.0)
    → c'est l'invariant qui déclenche la déduplication dans sweep (pas de cellule en double)."""
    assert _init_factor(172, "normalized") == _init_factor(172, "prod") == 1.0
    # Hors ancrage, les facteurs DIVERGENT (pas de dédup) :
    assert _init_factor(187, "normalized") != _init_factor(187, "prod")


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


def test_decode_auc_separable_signal():
    """Sur un signal linéairement séparable, l'AUC du décodeur ≈ 1."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    rng = np.random.RandomState(0)
    y = np.array([0, 1] * 60)                          # 120 samples, 2 classes équilibrées
    X = rng.randn(120, 4) + y[:, None] * 6.0           # signal fort corrélé à y
    auc = _decode_auc(X, y, min_per_class=8, seed=0)
    assert auc is not None and auc > 0.9


def test_decode_auc_pure_noise():
    """Sur du bruit indépendant de y, l'AUC ≈ 0.5 (pas de signal décodable)."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    rng = np.random.RandomState(1)
    y = np.array([0, 1] * 60)
    X = rng.randn(120, 4)                               # aucun lien avec y
    auc = _decode_auc(X, y, min_per_class=8, seed=0)
    assert auc is not None and 0.35 <= auc <= 0.65


def test_decode_auc_missing_class_returns_none():
    """Si une classe manque (ou < min_per_class), renvoie None (agent non qualifiant)."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    X = np.random.RandomState(2).randn(40, 4)
    y_one_class = np.zeros(40, dtype=int)              # une seule classe
    assert _decode_auc(X, y_one_class, min_per_class=8, seed=0) is None
    y_too_few = np.array([1] * 3 + [0] * 37)           # classe 1 < min_per_class
    assert _decode_auc(X, y_too_few, min_per_class=8, seed=0) is None


def test_read_state_legacy_shape():
    """_read_state(legacy) renvoie l'état récurrent batché (B, N) après un forward."""
    import numpy as np
    from src.agents.backend import make_population
    from tools.substrate_ab_compositional import _build_agents, _read_state
    np.random.seed(0)
    agents = _build_agents(4, 172, "prod")
    pop = make_population(agents, backend="legacy")
    obs = (np.random.RandomState(1).randn(4, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
    pop.forward(obs)
    st = _read_state(pop, "legacy")
    assert st.shape == (4, 172)


@pytest.mark.slow
def test_read_state_torch_shape():
    """_read_state(torch) renvoie pop.H sous forme numpy (B, N)."""
    pytest.importorskip("torch")
    import numpy as np
    from src.agents.backend import make_population
    from tools.substrate_ab_compositional import _build_agents, _read_state
    np.random.seed(0)
    agents = _build_agents(4, 172, "prod")
    pop = make_population(agents, backend="torch")
    obs = (np.random.RandomState(1).randn(4, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
    pop.forward(obs)
    st = _read_state(pop, "torch")
    assert st.shape == (4, 172)


@pytest.mark.slow
def test_memory_probe_smoke():
    """memory_probe renvoie un dict structuré ; le contrôle permutation est dans la bande chance (≈0.5)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import memory_probe
    res = memory_probe(seeds=(0,), n_agents=8, trials=60)
    assert res["verdict"] in {"MEMORY_PRESENT", "MEMORY_ABSENT", "ASYMÉTRIQUE"}
    assert "control_valid" in res
    assert res["cells"]
    for c in res["cells"]:
        assert c["backend"] in {"legacy", "torch"}
        for k in ("n_qualifying", "base_rate", "median_auc_s2", "median_auc_pre", "median_delta",
                  "median_auc_shuffled"):
            assert k in c
        # Le contrôle permutation (labels mélangés sur H_S2) est la vraie baseline chance :
        # H_pre est confondu (causalement amont de did_x) et ne constitue PAS un contrôle fiable.
        if c["median_auc_shuffled"] is not None:
            assert 0.3 <= c["median_auc_shuffled"] <= 0.7   # contrôle permutation dans la bande chance


def test_warmup_reward_rule():
    """Phase A (warmup) : reward = +1 si l'action == target_x (did_x), sinon −1. Pur."""
    from tools.substrate_ab_compositional import _warmup_reward
    assert _warmup_reward(move1=0, target_x=0) == 1.0
    assert _warmup_reward(move1=3, target_x=0) == -1.0
    assert _warmup_reward(move1=4, target_x=4) == 1.0


@pytest.mark.slow
def test_run_curriculum_warmup0_is_compositional():
    """warmup_trials=0 → phase A vide → run_curriculum exécute la phase B seule (plancher compo)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum
    r = run_curriculum("legacy", seed=0, warmup_trials=0, compo_trials=40, n_agents=4)
    # warmup vide → did_x de warmup non défini/neutre ; les clés existent et hit ∈ [0,1]
    for k in ("warmup_didx_end", "hit_start", "hit_end", "compo_didx_end", "delta"):
        assert k in r
    assert 0.0 <= r["hit_end"] <= 1.0


@pytest.mark.slow
def test_compare_curriculum_smoke():
    """compare_curriculum renvoie un verdict curriculum structuré + per_seed avec les trajectoires."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare_curriculum
    res = compare_curriculum(seeds=(0,), warmup_trials=40, compo_trials=40, n_agents=4)
    assert res["verdict_curriculum"] in {"DISCOVERY", "CREDIT", "WARMUP_FAILED", "AMBIGU"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for k in ("legacy", "torch"):
        for kk in ("warmup_didx_end", "hit_end", "compo_didx_end"):
            assert kk in row[k]
