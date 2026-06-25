# tests/sandbox/test_diversity_dose_probe.py
import pytest


@pytest.mark.slow
def test_mixture_mode_runs_population_exact_and_decomposes(monkeypatch):
    """Le mode mixture (f=0.5) construit N agents, tourne (reproduction stoneage→row[n]≥N), sort la décompo apex/lance."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    monkeypatch.setenv("CT_CLONE_FRAC", "0.5")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.target_competence_probe import run_probe
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_probe("stoneage", k=1, num_agents=20, max_ticks=80, shared_db=db, mode="mixture")
    finally:
        async_logger.stop()
    assert res["mode"] == "mixture" and res["per_era"]
    row = res["per_era"][0]
    # Garde-fou compte : population initialisée = N (≥ car le monde peut reproduire en cours de sim).
    assert row["n"] >= 20
    assert "frac_apex" in row and "frac_tool" in row
    assert "total_mammoth" in row and "total_spears" in row
    assert 0.0 <= res["median_competence"] <= 1.0
