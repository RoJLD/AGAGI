import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from tools.g_fidelity_probe import transition_error, fidelity_verdict


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


from tools.g_fidelity_probe import collect_ratios, run_probe


def test_collect_ratios_returns_finite_positive():
    ratios = collect_ratios(seed=0, warmup=20, measure=20)
    assert len(ratios) > 0
    assert all(np.isfinite(r) and r >= 0.0 for r in ratios)


def test_run_probe_structure():
    out = run_probe(seeds=[0, 1], warmup=20, measure=20)
    assert set(["median_ratio", "n_favorable", "n", "sign_p", "verdict"]).issubset(out)
    assert out["verdict"] in ("G_FIDELE", "G_INUTILE", "NEUTRE")
