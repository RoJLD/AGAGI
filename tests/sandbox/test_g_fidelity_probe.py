import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from tools.g_fidelity_probe import (
    transition_error, fidelity_verdict,
    collect_ratios, run_probe,
    collect_ratios_env, run_probe_env,
    _GRID_L, _N_MOVES, _OBS_DIM, _obs_bench,
)


def test_transition_error_perfect_g_beats_baseline():
    H_prev = np.array([0.0, 0.0], dtype=np.float32)
    H_next = np.array([1.0, 0.0], dtype=np.float32)
    g_delta = np.array([1.0, 0.0], dtype=np.float32)        # g prédit exactement le changement
    g_err, base_err = transition_error(H_prev, g_delta, H_next)
    assert np.isclose(g_err, 0.0)                            # prédiction parfaite
    assert base_err > 0.0                                    # baseline se trompe
    assert g_err < base_err


def test_transition_error_zero_g_equals_baseline():
    H_prev = np.array([0.0, 0.0], dtype=np.float32)
    H_next = np.array([1.0, 0.0], dtype=np.float32)
    g_delta = np.zeros(2, dtype=np.float32)                  # g=0 -> identique à la baseline
    g_err, base_err = transition_error(H_prev, g_delta, H_next)
    assert np.isclose(g_err, base_err)


def test_fidelity_verdict_faithful():
    out = fidelity_verdict([0.3, 0.4, 0.2, 0.5, 0.35])       # g bat nettement la baseline
    assert out["verdict"] == "G_FIDELE"
    assert out["n_favorable"] == 5 and out["n"] == 5


def test_fidelity_verdict_useless():
    out = fidelity_verdict([1.3, 1.2, 1.5, 1.1])
    assert out["verdict"] == "G_INUTILE"


def test_fidelity_verdict_neutral_and_no_nan():
    out = fidelity_verdict([1.0, 1.0])                        # égalités -> NEUTRE, pas de NaN
    assert out["verdict"] == "NEUTRE"
    assert np.isfinite(out["sign_p"])


def test_collect_ratios_returns_finite_positive():
    ratios, action_abs = collect_ratios(seed=0, warmup=20, measure=20)
    assert len(ratios) > 0
    assert all(np.isfinite(r) and r >= 0.0 for r in ratios)


def test_run_probe_structure():
    out = run_probe(seeds=[0, 1], warmup=20, measure=20)
    assert set(["median_ratio", "n_favorable", "n", "sign_p", "verdict"]).issubset(out)
    assert out["verdict"] in ("G_FIDELE", "G_INUTILE", "NEUTRE")


def test_collect_ratios_all_actions_exercised():
    """Vérifie que les 8 actions sont toutes exercées : chaque G[a] doit avoir des mesures."""
    from src.agents.mamba_agent import MambaBatchModel
    n_actions = MambaBatchModel.PLAN_A
    _, action_abs = collect_ratios(seed=0, warmup=20, measure=n_actions * 4)
    for a_idx in range(n_actions):
        assert len(action_abs[a_idx]) > 0, f"Action {a_idx} non exercée"
        assert all(np.isfinite(v) for v in action_abs[a_idx]), f"mean|G[{a_idx}]| non fini"


def test_collect_ratios_nontrivial_transitions():
    """Avec obs variables σ=0.3, les transitions latentes doivent dépasser le seuil base_err>0.01."""
    ratios, _ = collect_ratios(seed=1, warmup=10, measure=50)
    # Au moins quelques transitions doivent être mesurées (base_err > 0.01)
    assert len(ratios) > 0, "Aucune transition non-triviale mesurée avec obs variables"


# ===== Tests env-based (collect_ratios_env / run_probe_env) =====

def test_obs_bench_shape_and_onehot():
    """_obs_bench produit un vecteur de dimension correcte et valide."""
    o = _obs_bench(3, 5)
    assert o.shape == (_OBS_DIM,)
    assert o[3] == 1.0               # one-hot position
    assert o[_GRID_L + 5] == 1.0    # one-hot danger
    assert o.sum() == 2.0
    o2 = _obs_bench(0, None)
    assert o2.sum() == 1.0           # pas de danger


def test_collect_ratios_env_returns_finite_positive():
    """collect_ratios_env retourne des ratios finis et positifs (env réel)."""
    ratios, action_abs = collect_ratios_env(seed=0, warmup=20, measure=30)
    assert len(ratios) > 0, "Aucune transition mesurée dans l'env réel"
    assert all(np.isfinite(r) and r >= 0.0 for r in ratios), "Ratios non-finis ou négatifs"
    for a_idx in range(_N_MOVES):
        assert len(action_abs[a_idx]) > 0, f"Action {a_idx} non exercée dans l'env"


def test_collect_ratios_env_all_moves_covered():
    """Les 3 moves sont tous exercés (round-robin) et ont des mean|G[a]| finis."""
    ratios, action_abs = collect_ratios_env(seed=2, warmup=10, measure=_N_MOVES * 5)
    for a_idx in range(_N_MOVES):
        assert len(action_abs[a_idx]) > 0, f"Move {a_idx} jamais joué"
        assert all(np.isfinite(v) for v in action_abs[a_idx]), f"mean|G[{a_idx}]| non fini"


def test_collect_ratios_env_obs_vary_with_position():
    """Sanity check : la grille produit des obs différentes selon la position (couplage réel)."""
    o_left = _obs_bench(0, None)
    o_mid = _obs_bench(_GRID_L // 2, None)
    o_right = _obs_bench(_GRID_L - 1, None)
    assert not np.allclose(o_left, o_mid), "Obs identiques pour positions différentes"
    assert not np.allclose(o_mid, o_right), "Obs identiques pour positions différentes"


def test_run_probe_env_structure():
    """run_probe_env retourne un dict avec les clés de fidelity_verdict + mean_G_abs_by_action."""
    out = run_probe_env(seeds=[0, 1], warmup=20, measure=20)
    required = {"median_ratio", "n_favorable", "n", "sign_p", "verdict", "mean_G_abs_by_action"}
    assert required.issubset(out), f"Clés manquantes : {required - set(out)}"
    assert out["verdict"] in ("G_FIDELE", "G_INUTILE", "NEUTRE")
    g_abs = out["mean_G_abs_by_action"]
    for a_idx in range(_N_MOVES):
        assert a_idx in g_abs, f"Action {a_idx} absente de mean_G_abs_by_action"
        assert np.isfinite(g_abs[a_idx])


def test_run_probe_stoneage_returns_verdict():
    from tools.g_fidelity_probe import run_probe_stoneage
    result = run_probe_stoneage([0], warmup=5, measure=5, num_agents=4)
    assert "verdict" in result
    assert result["n"] >= 0
