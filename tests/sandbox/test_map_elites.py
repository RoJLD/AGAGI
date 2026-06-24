import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np
from src.seed_ai.map_elites import descriptor, MapElitesArchive


class _G:
    def __init__(self, n):
        self.num_nodes = n


def test_descriptor_bins():
    assert descriptor(172, {"mammoth_kills": 1}) == (1, 3)
    assert descriptor(150, {}) == (0, 0)
    assert descriptor(400, {})[0] == 7          # size clampé haut
    assert descriptor(172, {"preys_eaten": 2}) == (1, 1)
    assert descriptor(172, {"spears_crafted": 1}) == (1, 2)
    assert descriptor(100, {})[0] == 0          # size clampé bas


def test_upsert_keeps_max_per_cell():
    a = MapElitesArchive()
    assert a.upsert(10.0, _G(172), {"preys_eaten": 1}) is True
    assert a.upsert(5.0, _G(172), {"preys_eaten": 1}) is False   # même cellule, plus bas
    assert a.best_score() == 10.0
    assert a.upsert(20.0, _G(172), {"preys_eaten": 1}) is True   # plus haut -> remplace
    assert a.best_score() == 20.0
    assert a.coverage() == 1


def test_distinct_cells_coexist():
    a = MapElitesArchive()
    a.upsert(10.0, _G(172), {"preys_eaten": 1})    # (1,1)
    a.upsert(8.0, _G(172), {"mammoth_kills": 1})   # (1,3)
    a.upsert(7.0, _G(220), {"preys_eaten": 1})     # (4,1)
    assert a.coverage() == 3


def test_sample_and_empty():
    a = MapElitesArchive()
    assert a.sample(3) == []
    a.upsert(10.0, _G(172), {"preys_eaten": 1})
    a.upsert(9.0, _G(200), {"mammoth_kills": 1})
    np.random.seed(0)
    s = a.sample(4)
    assert len(s) == 4
    assert all(hasattr(g, "num_nodes") for g in s)


def test_config_use_map_elites_default_false():
    from src.environments.config import WorldConfig
    assert WorldConfig().use_map_elites is False
