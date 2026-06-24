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


def test_measure_survival_keys_and_reproducible():
    lss._disable_kuzu()
    cfg = lss._cfg(3)
    a = lss._measure_survival(cfg, seeds=[7, 8], num_agents=4, max_ticks=30)
    b = lss._measure_survival(cfg, seeds=[7, 8], num_agents=4, max_ticks=30)
    assert set(a) == {"ticks", "famine", "combat", "kills"}
    assert len(a["kills"]) == 2                       # un kills moyen par ere (2 seeds)
    assert len(a["ticks"]) >= 8                        # >= num_agents par ere, pool inclut les morts
    assert all(0 <= t <= 30 for t in a["ticks"])       # ages bornes par max_ticks
    assert a == b                                      # seede -> reproductible
    assert a["famine"] + a["combat"] <= len(a["ticks"])


def test_main_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main(levels=(3, 48), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main(levels=(3, 48), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [3, 48]
    assert set(a["table"][3]) == {"median", "famine", "combat", "mean_kills", "n"}
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"BARREAU TROUVE", "BARREAU TROP CHER", "PAS DE RUNG"}


def test_verdict_apex_three_branches():
    levels = (12, 9, 6, 3, 0)
    # survie franchie a un N_APEX > 0 (ici 6 et 3) -> barreau trouve
    assert lss._verdict_apex(levels, [10, 20, 130, 200, 260]) == "BARREAU TROUVE"
    # survie franchie SEULEMENT a N_APEX = 0 -> rung degenere
    assert lss._verdict_apex(levels, [10, 20, 40, 90, 150]) == "RUNG DEGENERE"
    # aucun niveau ne franchit (meme 0) -> mur intrinseque
    assert lss._verdict_apex(levels, [5, 8, 10, 30, 60]) == "MUR INTRINSEQUE"
    # frontiere : exactement au gate ne franchit pas (m > gate strict)
    assert lss._verdict_apex(levels, [5, 8, 10, 30, 120]) == "MUR INTRINSEQUE"


def test_measure_survival_n_apex_wired_and_reproducible():
    lss._disable_kuzu()
    cfg = lss._cfg(3)
    a = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    a2 = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    assert set(a) == {"ticks", "famine", "combat", "kills"}
    assert a == a2                              # seede -> reproductible
    # n_apex=0 -> AUCUN apex instancie -> impossible de tuer un Mammouth -> kills tous nuls.
    # Assertion science-independante (ne depend PAS de l'issue de survie) : prouve le cablage de n_apex.
    assert sum(a["kills"]) == 0
