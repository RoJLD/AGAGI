# tests/sandbox/test_diverse_selection.py
import pytest


@pytest.mark.slow
def test_diverse_selection_runs_and_reports_diversity(monkeypatch):
    """select='diverse' (tournoi) tourne 2 ères, le carry tournoi ère0->1 ne crashe pas,
    et chaque ère rapporte genome_diversity (garde-fou mécanisme)."""
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
                            shared_db=db, preserve_dims=True, node_cap=512,
                            experiment_seed=0, select="diverse", n_carry=6,
                            tournament_size=3, pop_cap=40)
    finally:
        async_logger.stop()
    assert res["select"] == "diverse"
    assert res["n_carry"] == 6 and res["pop_cap"] == 40
    assert len(res["per_era"]) == 2
    for row in res["per_era"]:
        assert "genome_diversity" in row
        assert row["genome_diversity"] >= 0.0
    assert 0.0 <= res["per_era"][0]["median_competence"] <= 1.0


@pytest.mark.slow
def test_elitist_default_unchanged_with_diversity_metric(monkeypatch):
    """Le défaut select='elitist' tourne (carry top-3 EDR105) et rapporte aussi genome_diversity."""
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
    assert res["select"] == "elitist"        # défaut non-régressif
    assert res["pop_cap"] is None
    assert res["n_carry"] == 12
    assert "genome_diversity" in res["per_era"][0]
