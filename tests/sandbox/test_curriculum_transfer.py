# tests/sandbox/test_curriculum_transfer.py
from tools.curriculum_transfer import compute_transfer_verdict, _sign_test_p


def test_sign_test_p_extremes():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1          # tous du même côté -> significatif
    assert _sign_test_p(3, 6) == 1.0         # 50/50 -> p=1
    assert 0.0 <= _sign_test_p(4, 5) <= 1.0


def test_verdict_transfere_when_ratios_above_one():
    v = compute_transfer_verdict([1.5, 1.4, 1.6, 1.3, 1.5])
    assert v["verdict"] == "TRANSFERE"
    assert v["n_favorable"] == 5 and v["n"] == 5
    assert v["median_ratio"] > 1.0


def test_verdict_nuit_when_ratios_below_one():
    v = compute_transfer_verdict([0.5, 0.6, 0.4, 0.5])
    assert v["verdict"] == "NUIT"


def test_verdict_neutre_in_band_or_mixed():
    assert compute_transfer_verdict([1.01, 0.99, 1.02, 0.98])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["sign_p"] == 1.0
