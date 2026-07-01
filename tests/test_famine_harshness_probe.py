"""Tests de la sonde de dureté famine (tools/famine_harshness_probe.py) — durcir-la-famine (EDR-130).

Le classifieur de régime est PUR (testable sans biosphère) : il tranche « le stockage est-il
load-bearing ? » à partir de la survie buffer-seul (cache OFF) vs oracle-storer (réserve injectée)."""
from tools.famine_harshness_probe import classify_storage_regime


def test_regime_storage_required_quand_oracle_domine_le_buffer():
    # oracle 223 vs buffer 96 = ratio 2.3 >= 1.5 -> le monde EXIGE le stockage
    r = classify_storage_regime(buffer_survival=96.0, oracle_survival=223.0, min_ratio=1.5)
    assert r["verdict"] == "STORAGE_REQUIRED"
    assert round(r["ratio"], 2) == round(223.0 / 96.0, 2)


def test_regime_storage_redundant_quand_oracle_proche_du_buffer():
    # oracle 122 vs buffer 107 = ratio 1.14 < 1.5 -> buffer suffit, stockage redondant (cas EDR-126)
    r = classify_storage_regime(buffer_survival=107.0, oracle_survival=122.0, min_ratio=1.5)
    assert r["verdict"] == "STORAGE_REDUNDANT"


def test_regime_buffer_zero_ne_divise_pas_par_zero():
    r = classify_storage_regime(buffer_survival=0.0, oracle_survival=50.0, min_ratio=1.5)
    assert r["verdict"] == "STORAGE_REQUIRED"
    import math
    assert math.isfinite(r["ratio"])
