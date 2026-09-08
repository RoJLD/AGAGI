# tests/sandbox/test_metabolic_cost_sweep.py
import sys, os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.metabolic_cost_sweep import _sign_test_p, compute_sweep_verdict


def test_sign_test_p_bounds():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1     # tous favorables sur 5 -> significatif
    assert _sign_test_p(2, 4) == 1.0    # 2/4 -> bilatéral = 1.0


def test_verdict_efficace():
    # ⚠️ n=8, PAS 3. Le correctif E14 du 2026-09-01 a ajouté `sign_p < 0.05` à cette branche ; à n=3
    # `sign_p` vaut 0.25 AU MIEUX, donc EFFICACE était devenu INATTEIGNABLE et ce test rouge depuis.
    # C'est la classe E14 elle-même — une garde exécutable jamais rétro-appliquée à ses propres tests.
    per_coef = [{"coef": 0.01,
                 "eff_ratios": [1.2, 1.3, 1.15, 1.25, 1.1, 1.35, 1.18, 1.22],   # efficacité en hausse
                 "surv_ratios": [0.98, 1.0, 0.95, 0.99, 1.0, 0.97, 0.98, 1.0]}]  # survie OK
    out = compute_sweep_verdict(per_coef)["per_coef"][0]
    assert out["verdict"] == "EFFICACE"
    assert out["median_eff"] > 1.05
    assert out["sign_p"] < 0.05, "la puissance est la CONDITION du verdict, pas un detail"


def test_verdict_EFFICACE_est_INATTEIGNABLE_sous_le_plancher_de_puissance():
    """Le plancher, GRAVÉ. La MÊME dose (tous les ratios favorables, médiane identique) sur 3 seeds ne
    peut PAS rendre EFFICACE : `sign_p` vaut 0.25 par construction. Sans ce cas, la prochaine garde
    ajoutée re-cassera les fixtures en silence — c'est exactement ce qui vient de se produire."""
    petit = [{"coef": 0.01, "eff_ratios": [1.2, 1.3, 1.15], "surv_ratios": [0.98, 1.0, 0.95]}]
    out = compute_sweep_verdict(petit)["per_coef"][0]
    assert out["median_eff"] > 1.05 and out["n_favorable"] == 3      # la DOSE est là
    assert out["sign_p"] == 0.25                                     # la PUISSANCE ne l'est pas
    assert out["verdict"] == "NEUTRE"


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
    # 8 seeds et non 2 : sous le plancher de puissance (`sign_p < 0.05`) le verdict
    # EFFICACE est inatteignable quelle que soit la dose -- cf. le cas dédié ci-dessus.
    out = run_sweep(seeds=[0, 1, 2, 3, 4, 5, 6, 7], coefs=[0.0, 0.01], eras=2,
                    num_agents=6, max_ticks=50, run_era_fn=_fake_run_era_fn)
    assert "per_coef" in out and "per_lineage" in out
    coef_entry = [c for c in out["per_coef"] if abs(c["coef"] - 0.01) < 1e-9][0]
    assert coef_entry["verdict"] == "EFFICACE"        # efficacité ↑, survie constante


def _fake_kwta_runner(cfg, genomes, max_ticks):
    # plus on sparsifie (keep bas), plus mean_active baisse ; competence/survie constants.
    keep = getattr(cfg, "kwta_keep_frac", 1.0)
    metrics = {"ticks": 200.0, "score": 50.0, "mean_active": max(1.0, 150.0 * keep)}
    scored = [(50.0, _FakeGenome()) for _ in range(5)]
    return scored, metrics


def test_run_sweep_generalized_param_and_baseline():
    out = run_sweep(seeds=[0, 1, 2, 3, 4, 5, 6, 7], coefs=[1.0, 0.5], eras=2,
                    num_agents=6, max_ticks=50, run_era_fn=_fake_kwta_runner,
                    param="kwta_keep_frac", baseline=1.0)   # 8 seeds : cf. plancher
    assert out["config"]["param"] == "kwta_keep_frac"
    assert out["config"]["baseline"] == 1.0
    entry = [c for c in out["per_coef"] if abs(c["coef"] - 0.5) < 1e-9][0]
    # keep=0.5 -> mean_active moitie -> efficiency (competence/mean_active) ~ x2 -> EFFICACE
    assert entry["verdict"] == "EFFICACE"


def test_run_sweep_backward_compat_d1():
    # sans param/baseline : comportement D1 inchange (param=metabolic_cost_coef, baseline=0.0)
    out = run_sweep(seeds=[0], coefs=[0.01], eras=2, num_agents=6, max_ticks=50,
                    run_era_fn=_fake_run_era_fn)
    assert out["config"]["param"] == "metabolic_cost_coef"
    assert out["config"]["baseline"] == 0.0
    assert any(abs(c["coef"] - 0.01) < 1e-9 for c in out["per_coef"])


def test_seed_num_nodes_enriches_hidden_layer():
    # NAS substrat : seed_num_nodes contrôle la taille du connectome de graine -> vraie couche cachée.
    captured = {}

    def _cap_runner(cfg, genomes, max_ticks):
        captured["mean_nodes"] = float(np.mean([g.num_nodes for g in genomes]))
        return [(50.0, genomes[0])], {"ticks": 100.0, "score": 50.0, "mean_active": 10.0}

    run_lineage(0, 0.0, eras=1, num_agents=6, max_ticks=10, run_era_fn=_cap_runner, seed_num_nodes=240)
    big = captured["mean_nodes"]
    run_lineage(0, 0.0, eras=1, num_agents=6, max_ticks=10, run_era_fn=_cap_runner)
    default = captured["mean_nodes"]
    assert big >= 235        # ~240 noeuds (petite croissance add_node tolérée)
    assert default <= 180    # défaut bare ~172
    assert big > default


@pytest.mark.skipif(os.environ.get("MCS_SMOKE") != "1",
                    reason="smoke lourd (vraie biosphère) — set MCS_SMOKE=1 pour lancer")
def test_run_era_metab_smoke():
    from tools.metabolic_cost_sweep import run_era_metab, _make_cfg
    from src.agents.mamba_agent import MambaAgent
    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        cfg = _make_cfg(0.0)
        genomes = [MambaAgent().genome for _ in range(6)]
        scored, m = run_era_metab(cfg, genomes, max_ticks=30)
        assert m["mean_active"] >= 0.0
        assert m["ticks"] >= 1
        assert isinstance(scored, list)
    finally:
        async_logger.stop()
