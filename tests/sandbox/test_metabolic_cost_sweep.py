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


import numpy as np
from tools.metabolic_cost_sweep import run_lineage, run_sweep


class _FakeGenome:
    def clone(self):
        return _FakeGenome()


def _fake_run_era_fn(cfg, genomes, max_ticks):
    # Déterministe : plus le coef est haut, plus mean_active baisse (cerveaux sparses sélectionnés)
    # et plus l'efficacité monte ; survie quasi constante. competence fixe.
    coef = getattr(cfg, "metabolic_cost_coef", 0.0)
    mean_active = max(1.0, 100.0 - coef * 2000.0)   # coef=0 ->100 ; 0.01 ->80
    metrics = {"ticks": 200.0, "score": 50.0, "mean_active": mean_active}
    scored = [(50.0, _FakeGenome()) for _ in range(5)]
    return scored, metrics


def test_run_lineage_efficiency_rises_with_coef():
    base = run_lineage(seed=0, coef=0.0, eras=3, num_agents=6, max_ticks=50,
                       run_era_fn=_fake_run_era_fn)
    hi = run_lineage(seed=0, coef=0.01, eras=3, num_agents=6, max_ticks=50,
                     run_era_fn=_fake_run_era_fn)
    assert hi["efficiency"] > base["efficiency"]      # moins de noeuds actifs -> efficacité ↑
    assert hi["mean_active"] < base["mean_active"]


def test_run_lineage_paired_reproducible():
    a = run_lineage(seed=7, coef=0.005, eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    b = run_lineage(seed=7, coef=0.005, eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    assert a["efficiency"] == b["efficiency"]


def test_run_sweep_structure_and_verdict():
    out = run_sweep(seeds=[0, 1], coefs=[0.0, 0.01], eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    assert "per_coef" in out and "per_lineage" in out
    coef_entry = [c for c in out["per_coef"] if abs(c["coef"] - 0.01) < 1e-9][0]
    assert coef_entry["verdict"] == "EFFICACE"        # efficacité ↑, survie constante
