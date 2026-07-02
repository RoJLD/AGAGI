import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.vertical_world_probe import classify_vertical_signal


def test_z_utilise_quand_range_et_updown_au_dessus_du_seuil():
    r = classify_vertical_signal(z_range_3d=2.0, updown_frac_3d=0.40)
    assert r["verdict"] == "Z_UTILISE"
    assert r["threshold"] == 0.25 * 1.2


def test_z_inerte_quand_range_nul():
    r = classify_vertical_signal(z_range_3d=0.0, updown_frac_3d=0.40)
    assert r["verdict"] == "Z_INERTE"


def test_z_inerte_quand_updown_sous_seuil():
    r = classify_vertical_signal(z_range_3d=2.0, updown_frac_3d=0.10)
    assert r["verdict"] == "Z_INERTE"


def test_survival_ratio_calcule_quand_fourni():
    r = classify_vertical_signal(2.0, 0.40, survival_2d=100.0, survival_3d=60.0)
    assert abs(r["survival_ratio"] - 0.6) < 1e-9


def test_survival_ratio_none_si_non_fourni():
    r = classify_vertical_signal(2.0, 0.40)
    assert r["survival_ratio"] is None


def test_survival_2d_zero_ne_divise_pas_par_zero():
    r = classify_vertical_signal(2.0, 0.40, survival_2d=0.0, survival_3d=5.0)
    assert r["survival_ratio"] > 0  # epsilon au dénominateur, pas d'exception
