import numpy as np
from tools.lewis_survival_sweep import (
    _p_reach_of_pool, _verdict_evolve_nav, _evolve_nav_gen, _cfg, _reproduce,
    _report_evolve_nav, main_evolve_nav,
)
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent


def test_p_reach_of_pool_fraction():
    pool = [{"_forage_min_dist": 0.0}, {"_forage_min_dist": 3.0},
            {"_forage_min_dist": 0.0}, {"_forage_min_dist": 9999.0}]
    assert _p_reach_of_pool(pool) == 0.5   # 2 sur 4 atteignent (md<=0)


def test_p_reach_of_pool_absent_key_is_unreached():
    pool = [{}, {"_forage_min_dist": 0.0}]   # cle absente -> defaut 9999 -> non atteint
    assert _p_reach_of_pool(pool) == 0.5


def test_p_reach_of_pool_empty():
    assert _p_reach_of_pool([]) == 0.0


def test_verdict_evolve_nav_evolue():
    # premieres ~0.18, dernieres ~0.40 -> delta 0.22 >= 0.15
    traj = [0.18, 0.17, 0.19, 0.18, 0.20] + [0.30, 0.35, 0.38, 0.40, 0.42]
    assert _verdict_evolve_nav(traj) == "NAVIGATION EVOLUE"


def test_verdict_evolve_nav_bloque():
    # plat ~0.18 partout -> delta ~0
    traj = [0.18, 0.17, 0.19, 0.18, 0.20] + [0.19, 0.18, 0.20, 0.17, 0.19]
    assert _verdict_evolve_nav(traj) == "SUBSTRAT BLOQUE"


def test_verdict_evolve_nav_boundary():
    # first median=0.20, last median=0.35 -> delta 0.15 (>= 0.15 -> EVOLUE)
    traj = [0.20] * 5 + [0.35] * 5
    assert _verdict_evolve_nav(traj) == "NAVIGATION EVOLUE"


def test_verdict_evolve_nav_empty():
    assert _verdict_evolve_nav([]) == "SUBSTRAT BLOQUE"


def test_evolve_nav_gen_smoke():
    seed_at(107, 0)
    cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
    mc = MutationConfig(weight_init_std=2.0)
    genomes = _reproduce([MambaAgent().genome for _ in range(3)], 6, mc)
    scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=15)
    assert 0.0 <= p_reach <= 1.0
    assert isinstance(scored, list) and len(scored) >= 1
    s0, g0 = scored[0]
    assert isinstance(s0, float)
    assert g0 is not None
    assert set(stats) == {"ticks", "eaten", "p_reach"}
    assert np.isfinite(stats["ticks"]) and stats["p_reach"] == p_reach


class _FakeHarness:
    """Capture h.save sans DB."""
    def __init__(self):
        self.saved = None

    def save(self, d):
        self.saved = d


def test_report_evolve_nav_verdict_and_save():
    traj = [0.18, 0.17, 0.19, 0.18, 0.20, 0.30, 0.35, 0.38, 0.40, 0.42]
    stats = [{"ticks": 20, "eaten": 3, "p_reach": p} for p in traj]
    h = _FakeHarness()
    out = _report_evolve_nav(h, traj, stats, 10, 24, 80, _return=True)
    assert out["verdict"] == "NAVIGATION EVOLUE"
    assert h.saved is not None and h.saved["verdict"] == "NAVIGATION EVOLUE"
    assert h.saved["traj"] == traj


def test_main_evolve_nav_smoke():
    out = main_evolve_nav(generations=2, num_agents=6, max_ticks=12, seed=107, _return=True)
    assert "verdict" in out
    assert len(out["traj"]) == 2
    assert out["verdict"] in ("NAVIGATION EVOLUE", "SUBSTRAT BLOQUE")
