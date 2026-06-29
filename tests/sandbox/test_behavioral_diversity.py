# tests/sandbox/test_behavioral_diversity.py
import pytest


@pytest.mark.slow
def test_behavioral_diversity_present_and_decomposed(monkeypatch):
    """Chaque ère rapporte behavioral_diversity + la décompo par descripteur, tous dans [0,1]."""
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
    assert len(res["per_era"]) == 2
    for row in res["per_era"]:
        for k in ("behavioral_diversity", "bdiv_preys", "bdiv_mammoth", "bdiv_spears", "bdiv_age"):
            assert k in row, f"clé manquante : {k}"
            assert 0.0 <= row[k] <= 1.0, f"{k}={row[k]} hors [0,1]"
    assert 0.0 <= res["per_era"][0]["median_competence"] <= 1.0
