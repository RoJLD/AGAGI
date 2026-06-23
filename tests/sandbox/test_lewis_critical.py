import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from tools import lewis_critical as lc


def _apex_counts(env):
    by = {"Mammouth": 0, "Ours": 0, "Leurre": 0}
    for p in env.preys:
        t = p.get("type") if isinstance(p, dict) else getattr(p, "type", None)
        if t in by:
            by[t] += 1
    return by


def test_setup_critical_leurre_fraction():
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    lc._setup_critical(env, leurre_frac=0.5, n_apex=12)
    c = _apex_counts(env)
    assert c["Leurre"] == 6                       # 0.5 * 12
    assert c["Mammouth"] + c["Ours"] == 6         # le reste = positifs
    assert env.night_enabled is False             # hérité du correctif 086


def test_setup_critical_high_fraction():
    np.random.seed(0)
    env = Biosphere3D(WorldConfig())
    lc._setup_critical(env, leurre_frac=0.83, n_apex=12)
    c = _apex_counts(env)
    assert c["Leurre"] == 10                       # round(0.83*12)=10
    assert c["Mammouth"] + c["Ours"] == 2


def test_run_arm_reproducible():
    cfg = lc._sweet_cfg()
    g = lc._load_champions()[0]
    a = lc._run_arm(cfg, [g] * 4, 0.5, use_head=False, decode_act=False, scramble=False,
                    heads=None, world_seed=3, max_ticks=25)
    b = lc._run_arm(cfg, [g] * 4, 0.5, use_head=False, decode_act=False, scramble=False,
                    heads=None, world_seed=3, max_ticks=25)
    assert a["net"] == b["net"] and a["kills"] == b["kills"] and a["leurre_hits"] == b["leurre_hits"]
