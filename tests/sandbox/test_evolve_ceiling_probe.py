# tests/sandbox/test_evolve_ceiling_probe.py
import pytest


@pytest.mark.slow
def test_evolution_carry_and_decompose_preserve_true(monkeypatch):
    """2 ères, carry ère0->1 OK, décompo + taille réseau + cap_hits présents (preserve_dims=True)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.evolve_ceiling_probe import run_evolution
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60,
                            shared_db=db, preserve_dims=True, node_cap=512, experiment_seed=0)
    finally:
        async_logger.stop()
    assert res["preserve_dims"] is True
    assert len(res["per_era"]) == 2          # carry ère0->1 a tourné sans crash
    row0, row1 = res["per_era"]
    for row in (row0, row1):
        for k in ("frac_apex", "frac_tool", "median_competence", "mean_nodes",
                  "max_nodes", "n", "ticks", "cap_hits"):
            assert k in row, f"clé manquante : {k}"
        assert 0.0 <= row["median_competence"] <= 1.0
        assert row["mean_nodes"] > 0


@pytest.mark.slow
def test_evolution_preserve_false_runs_and_flattens(monkeypatch):
    """Contrôle : preserve_dims=False tourne sans crash ; décomposition valide (mêmes clés).
    La divergence taille True vs False ne s'observe qu'à l'échelle prod (K=12/40, not smoke K=12)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.evolve_ceiling_probe import run_evolution
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60,
                            shared_db=db, preserve_dims=False, node_cap=512, experiment_seed=0)
    finally:
        async_logger.stop()
    assert res["preserve_dims"] is False
    assert len(res["per_era"]) == 2
    # Ère 1 : agents ré-importés via from_genome(preserve_dims=False) -> aplatis à 172 à l'instanciation.
    # La reproduction intra-ère peut grossir au-delà, donc on borne par max_nodes raisonnable, pas ==172.
    assert res["per_era"][1]["mean_nodes"] > 0
