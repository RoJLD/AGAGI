import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.anticipation_bench import run_bench, compare


def test_run_bench_returns_survival():
    out = run_bench(plan_bias=0.0, seeds=[0, 1], steps=40)
    assert "survival_mean" in out and 0.0 <= out["survival_mean"] <= 1.0
    assert len(out["per_seed"]) == 2


def test_compare_structure():
    out = compare(seeds=[0, 1, 2])
    assert set(["verdict", "median_ratio", "sign_p", "n_favorable", "n"]).issubset(out)
    assert out["verdict"] in ("PLAN_GAGNE", "PLAN_PERD", "NEUTRE")
