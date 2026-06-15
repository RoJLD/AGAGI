import numpy as np
from tools import coevolve_use_long as cul
from tools.robust_eval import _load_champions
from src.seed_ai.mutation import MutationConfig


def test_sweet_cfg_is_long_substrate():
    cfg = cul._sweet_cfg()
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0


def test_measure_full_components_reproducible():
    cfg = cul._sweet_cfg()
    mc = MutationConfig(weight_init_std=2.0)
    champs = _load_champions()
    a = cul._measure_full(cfg, champs, mc, use_head=False, heads=None, num_agents=4, n=2, base=5)
    b = cul._measure_full(cfg, champs, mc, use_head=False, heads=None, num_agents=4, n=2, base=5)
    assert set(a) == {"kills", "nets", "survs"}
    assert len(a["kills"]) == 2 and len(a["nets"]) == 2 and len(a["survs"]) == 2
    assert a == b                                  # seedé -> reproductible (apparié)
