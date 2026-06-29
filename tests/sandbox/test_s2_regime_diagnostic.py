# tests/sandbox/test_s2_regime_diagnostic.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tools.s2_regime_diagnostic import regime_diagnostic_verdict, REGIMES


def _cell(survival, era_survival=None, censored=0.0):
    return {"survival": list(survival),
            "era_survival": list(era_survival if era_survival is not None else survival),
            "life_score": list(survival), "era_life": list(survival),
            "censored_frac": censored}


def _sep_regime(champ_age, base_age, n=8, censored=0.0, max_ticks=400):
    """Régime où le champion DOMINE le baseline : n ères appariées toutes positives + pools disjoints."""
    return {"champion": _cell([champ_age] * n, censored=censored),
            "reflex_naive": _cell([base_age] * n),
            "random_action": _cell([base_age] * n)}


def _equal_regime(age, n=8, censored=0.0):
    """Régime où champion ≈ baselines (aucune séparation)."""
    return {"champion": _cell([age] * n, censored=censored),
            "reflex_naive": _cell([age] * n),
            "random_action": _cell([age] * n)}


def test_sous_puissance_when_champion_beats_at_default():
    cells = {"defaut": _sep_regime(300, 50), "sweet": _sep_regime(300, 50)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "SOUS_PUISSANCE"
    assert v["regime_recommande"] == "defaut"
    assert v["per_regime"]["defaut"]["beats"] is True


def test_confond_plancher_when_default_floored_but_sweet_separates():
    # défaut : tous au plancher (20 << 0.5*400) et égaux -> non survivable, pas de séparation
    # sweet : champion 300 (survivable) domine baseline 50, lift = 300/20 = 15 >= 1.5
    cells = {"defaut": _equal_regime(20), "sweet": _sep_regime(300, 50)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "CONFOND_PLANCHER"
    assert v["regime_recommande"] == "sweet"
    assert v["per_regime"]["defaut"]["survivable"] is False
    assert v["per_regime"]["sweet"]["survivable"] is True


def test_n_exige_pas_reel_when_sweet_survivable_but_no_separation():
    # sweet survivable (300 >= 200) ET champion ≈ dummy -> finding réel
    cells = {"defaut": _equal_regime(20), "sweet": _equal_regime(300)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "N_EXIGE_PAS_REEL"
    assert v["regime_recommande"] is None


def test_ambigu_when_no_regime_survivable_and_no_separation():
    cells = {"defaut": _equal_regime(20), "sweet": _equal_regime(30)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["verdict"] == "AMBIGU"
    assert v["regime_recommande"] is None


def test_survivable_via_censored_fraction():
    # médiane basse (100 < 200) MAIS 30% censurés -> survivable par CENSORED_SURV ; champ ≈ dummy
    cells = {"defaut": _equal_regime(20),
             "sweet": {"champion": _cell([100] * 8, censored=0.30),
                       "reflex_naive": _cell([100] * 8), "random_action": _cell([100] * 8)}}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["per_regime"]["sweet"]["survivable"] is True
    assert v["verdict"] == "N_EXIGE_PAS_REEL"


def test_thresholds_and_regimes_reported():
    cells = {"defaut": _equal_regime(20), "sweet": _equal_regime(30)}
    v = regime_diagnostic_verdict(cells, max_ticks=400)
    assert v["thresholds"]["CLIFF_THRESH"] == 0.33
    assert REGIMES["sweet"] == (0.25, 3.0)
