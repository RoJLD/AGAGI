# tests/sandbox/test_live_harvest.py
import pytest


@pytest.mark.slow
def test_probe_outputs_live_decomposition(monkeypatch):
    """Après câblage : run_probe sur stoneage expose la décompo apex/lance dans per_era
    (preuve que mammoth_kills/spears_crafted sont récoltés ET rapportés)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.target_competence_probe import run_probe
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_probe("stoneage", k=1, num_agents=30, max_ticks=120, shared_db=db, mode="tabula")
    finally:
        async_logger.stop()
    assert res["per_era"], "aucune ère"
    row = res["per_era"][0]
    assert "frac_apex" in row and "frac_tool" in row
    assert "total_mammoth" in row and "total_spears" in row
    assert 0.0 <= res["median_competence"] <= 1.0
