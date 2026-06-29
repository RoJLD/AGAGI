import numpy as np
from tools.lewis_survival_sweep import _p_reach_of_pool, _verdict_evolve_nav


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
