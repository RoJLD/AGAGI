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
