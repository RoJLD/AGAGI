# tests/sandbox/test_lewis_survival_sweep.py
import numpy as np
import pytest
from tools import lewis_survival_sweep as lss


def test_cfg_sets_payoff_metab_cap():
    cfg = lss._cfg(12)
    assert cfg.forage_payoff == 12.0
    assert cfg.base_metabolism == 0.25
    assert cfg.max_population == 150


def test_verdict_three_branches():
    levels = (3, 6, 12, 24, 48)
    # franchit le gate des le niveau 12 (<=24) -> barreau trouve
    assert lss._verdict(levels, [10, 50, 130, 200, 260]) == "BARREAU TROUVE"
    # ne franchit qu'a 48 (x16) -> trop cher
    assert lss._verdict(levels, [10, 20, 40, 90, 150]) == "BARREAU TROP CHER"
    # ne franchit jamais -> pas de rung
    assert lss._verdict(levels, [5, 8, 10, 30, 60]) == "PAS DE RUNG"
    # franchit des le 1er niveau accessible (24) -> trouve
    assert lss._verdict(levels, [10, 20, 100, 121, 130]) == "BARREAU TROUVE"
