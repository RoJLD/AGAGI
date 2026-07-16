"""Tests du bras lr-par-tete (T2/M1) : verdict pur + smoke torch."""
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.disjoint_heads_v4 import _verdict_v4, main_v4_check
from tools.disjoint_heads_ab import torch


def test_verdict_lr_recovers_majority():
    assert _verdict_v4([0.8, 0.75, 0.6, 0.9, 0.55]) == "LR_RECOVERS"


def test_verdict_lr_insufficient_majority():
    assert _verdict_v4([0.1, 0.05, 0.2, 0.15, 0.0]) == "LR_INSUFFICIENT"


def test_verdict_lr_partial_when_mixed():
    # ni >=0.50 majorite ni <=0.20 majorite (0.35/0.4/0.45 au milieu)
    assert _verdict_v4([0.35, 0.40, 0.45, 0.30, 0.42]) == "LR_PARTIAL"


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_smoke_runs_and_reports_three_knobs():
    res = main_v4_check(K=1, base=2200, steps=20, _return=True)
    assert res["verdict"] in {"LR_RECOVERS", "LR_INSUFFICIENT", "LR_PARTIAL"}
    assert set(res["means"]) == {"norm", "perhead", "lr"}
    assert len(res["per_seed"]) == 1
    r = res["per_seed"][0]
    assert {"rec_norm", "rec_perhead", "rec_lr"} <= set(r)
