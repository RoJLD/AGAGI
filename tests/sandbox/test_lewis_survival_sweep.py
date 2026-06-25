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


def test_main_apex_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_apex(levels=(12, 0), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_apex(levels=(12, 0), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [12, 0]
    assert set(a["table"][12]) == {"median", "famine", "combat", "mean_kills", "n"}
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"BARREAU TROUVE", "RUNG DEGENERE", "MUR INTRINSEQUE"}
    # le niveau N_APEX=0 ne peut produire aucun kill (aucun apex)
    assert a["table"][0]["mean_kills"] == 0


def test_cfg_sets_surprise_scale():
    assert lss._cfg(3, ttc_surprise_scale=0.0).ttc_surprise_scale == 0.0
    assert lss._cfg(3, ttc_surprise_scale=0.5).ttc_surprise_scale == 0.5
    assert lss._cfg(3).ttc_surprise_scale == 1.0          # defaut config preserve (retro-compat)


def test_verdict_surprise_three_branches():
    levels = (1.0, 0.5, 0.25, 0.0)
    ff0 = [0.0, 0.0, 0.0, 0.0]
    # un scale<1 franchit (0.25 et 0.0) -> tarif = surprise
    assert lss._verdict_surprise(levels, [10, 50, 130, 200], ff0) == "TARIF=SURPRISE"
    # aucun ne franchit + une surprise non-finie -> overflow racine
    assert lss._verdict_surprise(levels, [5, 5, 5, 5], [0.0, 0.0, 0.0, 0.3]) == "OVERFLOW=RACINE"
    # aucun ne franchit + surprises finies -> pas le brain_cost
    assert lss._verdict_surprise(levels, [5, 5, 5, 5], ff0) == "PAS LE BRAIN_COST"
    # frontiere : exactement au gate ne franchit pas (m > gate strict)
    assert lss._verdict_surprise(levels, [5, 5, 5, 120], ff0) == "PAS LE BRAIN_COST"


def test_measure_survival_collect_surprise():
    lss._disable_kuzu()
    cfg = lss._cfg(3, ttc_surprise_scale=1.0)
    a = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30, collect_surprise=True)
    a2 = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30, collect_surprise=True)
    assert set(a) == {"ticks", "famine", "combat", "kills", "surprise"}
    assert len(a["surprise"]) == 2                          # une entree par ere (2 seeds)
    assert set(a["surprise"][0]) == {"mean_abs_finite", "max_finite", "frac_nonfinite"}
    assert all(0.0 <= s["frac_nonfinite"] <= 1.0 for s in a["surprise"])
    assert a == a2                                          # seede -> reproductible
    # defaut (sans collect) -> contrat 093/094 preserve
    b = lss._measure_survival(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    assert set(b) == {"ticks", "famine", "combat", "kills"}


def test_main_surprise_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_surprise(levels=(1.0, 0.0), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_surprise(levels=(1.0, 0.0), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [1.0, 0.0]
    assert {"median", "famine", "combat", "mean_kills", "n",
            "mean_surprise", "frac_nonfinite"} <= set(a["table"][1.0])
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"TARIF=SURPRISE", "OVERFLOW=RACINE", "PAS LE BRAIN_COST"}


def test_cfg_sets_trace_flag():
    assert lss._cfg(3, trace_energy_sinks=True).trace_energy_sinks is True
    assert lss._cfg(3).trace_energy_sinks is False


def test_verdict_drain_four_branches():
    # action > 50% du net -> throw
    assert lss._verdict_drain({"brain": 1, "action": 12, "biologie": 2, "mouvement": 0, "net": 15}) == "TARIF=THROW"
    # biologie > 50% -> biologie
    assert lss._verdict_drain({"brain": 1, "action": 2, "biologie": 12, "mouvement": 0, "net": 15}) == "TARIF=BIOLOGIE"
    # brain > 50% -> brain
    assert lss._verdict_drain({"brain": 12, "action": 2, "biologie": 1, "mouvement": 0, "net": 15}) == "TARIF=BRAIN"
    # mouvement > 50% -> mouvement
    assert lss._verdict_drain({"brain": 1, "action": 2, "biologie": 1, "mouvement": 11, "net": 15}) == "TARIF=MOUVEMENT"
    # aucune > 50% -> diffus
    assert lss._verdict_drain({"brain": 5, "action": 6, "biologie": 4, "mouvement": 0, "net": 15}) == "DRAIN DIFFUS"
    # net <= 0 -> diffus (garde)
    assert lss._verdict_drain({"brain": 0, "action": 0, "biologie": 0, "mouvement": 0, "net": 0}) == "DRAIN DIFFUS"


def test_measure_drain_keys_and_reproducible():
    lss._disable_kuzu()
    cfg = lss._cfg(3, trace_energy_sinks=True)
    a = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    b = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    assert {"brain", "action", "biologie", "mouvement", "net", "n_agents"} <= set(a)  # EDR100: bio_* additive
    assert a["n_agents"] >= 1
    assert abs(a["net"] - (a["brain"] + a["action"] + a["biologie"] + a["mouvement"])) < 1e-6   # net = somme (telescopage)
    assert a == b                                                              # seede -> reproductible


def test_main_decompose_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    assert a["phases"] == b["phases"]                         # seede -> reproductible
    assert {"brain", "action", "biologie", "mouvement", "net", "n_agents"} <= set(a["phases"])  # EDR100: bio_* additive
    assert a["verdict"] in {"TARIF=THROW", "TARIF=BIOLOGIE", "TARIF=BRAIN", "TARIF=MOUVEMENT", "DRAIN DIFFUS"}


def test_verdict_bio_four_branches():
    base = {"bio_metab": 0, "bio_terrain": 0, "bio_carry": 0, "bio_autres": 0}
    assert lss._verdict_bio({**base, "bio_metab": 9, "bio_terrain": 1, "bio_carry": 1}) == "TARIF=METABOLISME"
    assert lss._verdict_bio({**base, "bio_terrain": 9, "bio_metab": 1, "bio_carry": 1}) == "TARIF=TERRAIN"
    assert lss._verdict_bio({**base, "bio_carry": 9, "bio_metab": 1, "bio_terrain": 1}) == "TARIF=CARRY"
    assert lss._verdict_bio({**base, "bio_metab": 4, "bio_terrain": 4, "bio_carry": 3}) == "DRAIN BIO DIFFUS"
    assert lss._verdict_bio(base) == "DRAIN BIO DIFFUS"        # bio_net <= 0 -> diffus


def test_measure_drain_has_bio_keys():
    lss._disable_kuzu()
    cfg = lss._cfg(3, trace_energy_sinks=True)
    a = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    a2 = lss._measure_drain(cfg, seeds=[7, 8], n_apex=0, num_agents=4, max_ticks=30)
    for k in ("bio_metab", "bio_terrain", "bio_carry", "bio_autres"):
        assert k in a
    # coherence agregat : somme des sous-postes ~ phase biologie
    assert abs((a["bio_metab"] + a["bio_terrain"] + a["bio_carry"] + a["bio_autres"]) - a["biologie"]) < 1e-6
    assert a == a2                                            # reproductible


def test_main_decompose_has_bio_verdict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_decompose(n_eval=2, R=1, seed=5, _return=True)
    assert a["phases"] == b["phases"]                         # reproductible
    assert "bio_verdict" in a
    assert a["bio_verdict"] in {"TARIF=METABOLISME", "TARIF=TERRAIN", "TARIF=CARRY", "DRAIN BIO DIFFUS"}
    for k in ("bio_metab", "bio_terrain", "bio_carry", "bio_autres"):
        assert k in a["phases"]


def test_cfg_sets_base_metabolism():
    assert lss._cfg(3, base_metabolism=0.05).base_metabolism == 0.05
    assert lss._cfg(3, base_metabolism=0.0).base_metabolism == 0.0
    assert lss._cfg(3).base_metabolism == lss.METAB          # defaut 0.25 (retro-compat)


def test_verdict_metab_three_branches():
    levels = (0.25, 0.1, 0.05, 0.025, 0.0)
    # un base_metabolism > 0 franchit (ici 0.05) -> rescale suffit
    assert lss._verdict_metab(levels, [10, 50, 130, 200, 260]) == "RESCALE SUFFIT"
    # franchit SEULEMENT a base_metabolism = 0 -> rescale extreme
    assert lss._verdict_metab(levels, [10, 20, 40, 90, 150]) == "RESCALE EXTREME"
    # aucun ne franchit -> pas le metabolisme seul
    assert lss._verdict_metab(levels, [5, 8, 10, 30, 60]) == "PAS LE METABOLISME SEUL"
    # frontiere : exactement au gate ne franchit pas (m > gate strict)
    assert lss._verdict_metab(levels, [5, 8, 10, 30, 120]) == "PAS LE METABOLISME SEUL"


def test_main_metab_runs_and_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = lss.main_metab(levels=(0.25, 0.0), n_eval=2, R=1, seed=5, _return=True)
    b = lss.main_metab(levels=(0.25, 0.0), n_eval=2, R=1, seed=5, _return=True)
    assert a["medians"] == b["medians"]                       # seede -> reproductible
    assert list(a["table"].keys()) == [0.25, 0.0]
    assert set(a["table"][0.25]) == {"median", "famine", "combat", "mean_kills", "n"}
    assert "p_one_sided" in a["jt"]
    assert a["verdict"] in {"RESCALE SUFFIT", "RESCALE EXTREME", "PAS LE METABOLISME SEUL"}
