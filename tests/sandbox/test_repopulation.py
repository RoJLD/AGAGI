"""Tests de la régénération de population (EDR 024)."""
import copy

import numpy as np

from src.seed_ai.repopulation import build_population


class _G:  # génome minimal : seul .W nous intéresse ici
    def __init__(self, w):
        self.W = w


def _mutate(g, cfg):
    child = copy.deepcopy(g)
    child.W = child.W + 0.01      # mutation factice non nulle
    return child


def test_no_inert_full_population():
    # Le bug réparé : plus AUCUN agent inerte (W=zéros) ; population pleine.
    champions = [_G(np.ones((6, 6)) * (i + 1)) for i in range(3)]
    pop = build_population(champions, 20, mut_config=None, mutate_fn=_mutate)
    assert len(pop) == 20
    assert all(np.any(g.W) for g in pop)        # zéro inerte


def test_elitism_champions_intact_first():
    champions = [_G(np.ones((4, 4)) * (i + 1)) for i in range(3)]
    pop = build_population(champions, 10, mut_config=None, mutate_fn=_mutate)
    for i in range(3):                           # les champions passent intacts en tête
        assert pop[i] is champions[i]
    assert len(pop) == 10


def test_children_descend_from_champions_roundrobin():
    # Les enfants sont des mutations des champions (valeurs proches d'un champion).
    champions = [_G(np.full((3, 3), 5.0)), _G(np.full((3, 3), 9.0))]
    pop = build_population(champions, 6, mut_config=None, mutate_fn=_mutate)
    for child in pop[2:]:                        # au-delà de l'élite
        base = child.W[0, 0] - 0.01             # on retire la mutation factice
        assert base in (5.0, 9.0)               # descend bien d'un champion


def test_heavy_fraction_uses_heavy_config():
    champions = [_G(np.ones((3, 3)))]
    seen = []
    def mut(g, cfg):
        seen.append(cfg)
        return _mutate(g, cfg)
    build_population(champions, 11, mut_config="std", mutate_fn=mut,
                     heavy_config="HEAVY", heavy_frac=0.3)
    # 1 champion + 10 enfants ; 30 % de 10 = 3 enfants en mutation forte.
    assert seen.count("HEAVY") == 3
    assert seen.count("std") == 7


def test_empty_champions_returns_empty():
    assert build_population([], 10, None, _mutate) == []
