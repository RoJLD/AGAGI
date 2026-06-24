# tests/sandbox/test_metabolic_cost_sweep.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.metabolic_cost_sweep import _sign_test_p, compute_sweep_verdict


def test_sign_test_p_bounds():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1     # tous favorables sur 5 -> significatif
    assert _sign_test_p(2, 4) == 1.0    # 2/4 -> bilatéral = 1.0


def test_verdict_efficace():
    per_coef = [{"coef": 0.01,
                 "eff_ratios": [1.2, 1.3, 1.15],   # efficacité en hausse
                 "surv_ratios": [0.98, 1.0, 0.95]}] # survie OK
    out = compute_sweep_verdict(per_coef)["per_coef"][0]
    assert out["verdict"] == "EFFICACE"
    assert out["median_eff"] > 1.05


def test_verdict_nuit_on_collapse():
    per_coef = [{"coef": 0.05,
                 "eff_ratios": [1.5, 1.6, 1.4],    # efficacité haute MAIS...
                 "surv_ratios": [0.5, 0.4, 0.6]}]  # survie effondrée
    out = compute_sweep_verdict(per_coef)["per_coef"][0]
    assert out["collapsed"] is True
    assert out["verdict"] == "NUIT"


def test_verdict_neutre():
    per_coef = [{"coef": 0.001,
                 "eff_ratios": [1.0, 0.99, 1.01],
                 "surv_ratios": [1.0, 1.0, 1.0]}]
    assert compute_sweep_verdict(per_coef)["per_coef"][0]["verdict"] == "NEUTRE"


def test_verdict_empty():
    assert compute_sweep_verdict([])["per_coef"] == []
