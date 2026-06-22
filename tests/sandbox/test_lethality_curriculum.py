# tests/sandbox/test_lethality_curriculum.py
import numpy as np
import pytest
from tools import lethality_curriculum as lc


def test_lethal_cfg_is_sweet_spot():
    cfg = lc._lethal_cfg()
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0


def test_survival_competence_bounds_and_median():
    assert lc._survival_competence([], max_ticks=300) == 0.0          # vide -> 0
    assert lc._survival_competence([150], max_ticks=300) == 0.5       # médiane normalisée
    assert lc._survival_competence([600], max_ticks=300) == 1.0       # clip haut
    assert lc._survival_competence([60, 120, 300], max_ticks=300) == pytest.approx(120 / 300)


def test_verdict_three_branches():
    # gate échoué (survie <= 120) -> négatif profond, peu importe les stats
    assert lc._verdict(90.0, wilcoxon_p=0.01, med=5.0, lo=2.0) == "NEGATIF PROFOND"
    # gate ok + effet significatif positif -> casse le bootstrap
    assert lc._verdict(150.0, wilcoxon_p=0.01, med=5.0, lo=2.0) == "CASSE LE BOOTSTRAP"
    # gate ok mais effet non significatif / IC traverse 0 -> pas le goulot
    assert lc._verdict(150.0, wilcoxon_p=0.20, med=1.0, lo=-1.0) == "PAS LE GOULOT"
    assert lc._verdict(150.0, wilcoxon_p=0.01, med=-1.0, lo=-3.0) == "PAS LE GOULOT"


def test_run_era_clean_keys_and_reproducible():
    cfg = lc._lethal_cfg()
    seed_from = __import__("src.seed_ai.harness", fromlist=["seed_at"]).seed_at
    champs = lc._load_champions()
    seed_from(7, 0)
    g = lc._reproduce(champs, 4, lc.MutationConfig(weight_init_std=2.0))
    seed_from(7, 0)
    a = lc._run_era_clean(cfg, g, leurre_frac=0.5, max_ticks=20)
    seed_from(7, 0)
    b = lc._run_era_clean(cfg, g, leurre_frac=0.5, max_ticks=20)
    assert set(a) == {"ticks", "kills", "leurre_hits", "survivors", "scored"}
    assert a["ticks"] == b["ticks"] and a["kills"] == b["kills"]      # seedé -> reproductible
    assert a["leurre_hits"] == b["leurre_hits"]
    assert len(a["scored"]) <= 5 and a["ticks"] <= 20


def test_coevolve_at_shape_and_caps():
    cfg = lc._lethal_cfg()
    mc = lc.MutationConfig(weight_init_std=2.0)
    gcfg = lc.GraduationConfig(window=2, eps_plateau=0.02, c_floor=0.0, patience=1, max_eras=3)
    start = lc._load_champions()
    genomes, eras, history, graduated = lc._coevolve_at(
        cfg, mc, leurre_frac=0.5, start_genomes=start, grad_cfg=gcfg,
        base=1234, num_agents=4, max_ticks=20,
    )
    assert 1 <= eras <= 3                       # borné par max_eras
    assert len(history) == eras                 # une compétence par ère tenue
    assert len(genomes) == 5                    # top-5 portés
    assert all(0.0 <= c <= 1.0 for c in history)
    # reproductible
    g2, e2, h2, _ = lc._coevolve_at(cfg, mc, 0.5, start, gcfg, 1234, 4, 20)
    assert e2 == eras and h2 == history
