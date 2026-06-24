# tests/sandbox/test_map_elites_compare.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from tools.map_elites_compare import _qd_label, run_lineage_hof, run_lineage_qd, compare


def test_qd_label_mapping():
    assert _qd_label("TRANSFERE") == "QD_GAGNE"
    assert _qd_label("NUIT") == "QD_PERD"
    assert _qd_label("NEUTRE") == "NEUTRE"


def _fake_pool_runner(cfg, genomes, max_ticks):
    # score déterministe qui varie par génome (taille) -> reproductibilité testable.
    pool = [(40.0 + float(g.num_nodes % 20), g,
             {"num_nodes": g.num_nodes, "preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 0})
            for g in genomes]
    best = max(p[0] for p in pool)
    return pool, {"score": best, "ticks": 200.0}


def test_arms_run_and_reproducible():
    a = run_lineage_hof(0, eras=3, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    b = run_lineage_hof(0, eras=3, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    assert a == b                                   # apparié reproductible
    c_qd, cov = run_lineage_qd(0, eras=3, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    assert isinstance(c_qd, float) and cov >= 1     # archive peuplée


def test_compare_structure_and_verdict():
    out = compare(seeds=[0, 1], eras=2, num_agents=6, max_ticks=50, run_era_fn=_fake_pool_runner)
    assert "per_seed" in out and "verdict" in out and out["config"]["seeds"] == [0, 1]
    assert out["verdict"] in ("QD_GAGNE", "QD_PERD", "NEUTRE")
    assert all("ratio" in p and "C_hof" in p and "C_qd" in p for p in out["per_seed"])


import pytest
@pytest.mark.skipif(os.environ.get("MEC_SMOKE") != "1", reason="smoke lourd — set MEC_SMOKE=1")
def test_compare_smoke_real():
    from src.graph_rag.async_logger import logger as async_logger
    async_logger.start()
    try:
        out = compare(seeds=[0], eras=2, num_agents=6, max_ticks=30)
    finally:
        async_logger.stop()
    assert out["verdict"] in ("QD_GAGNE", "QD_PERD", "NEUTRE")
    assert out["per_seed"][0]["coverage"] >= 1
