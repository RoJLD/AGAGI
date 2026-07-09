import numpy as np
import pytest

from tools.disjoint_heads_ab import torch, _make_teachers, N_HEADS
from tools.disjoint_heads_lr import _norm_weights, _train_flat_lr_perhead, _verdict_lr


def test_verdict_lr_closes():
    # 3/5 seeds >= 0.90 -> LR_CLOSES
    assert _verdict_lr([0.95, 0.92, 0.91, 0.5, 0.4]) == "LR_CLOSES"


def test_verdict_lr_interchangeable():
    # 3/5 seeds <= 0.79 -> LR_INTERCHANGEABLE
    assert _verdict_lr([0.70, 0.60, 0.75, 0.95, 0.92]) == "LR_INTERCHANGEABLE"


def test_verdict_lr_partial():
    # ni majorite >=0.90 ni majorite <=0.79 -> PARTIAL
    assert _verdict_lr([0.85, 0.88, 0.95, 0.60, 0.83]) == "PARTIAL"


def test_norm_weights_mean_one():
    w = _norm_weights(np.array([0.1, 2.0, 0.5]))
    assert w.shape == (N_HEADS,)
    assert abs(float(w.sum()) - N_HEADS) < 1e-9   # -> mean(w) == 1
    # plus la loss (EMA) est basse, plus le poids est haut
    assert w[0] > w[2] > w[1]


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_flat_lr_perhead_runs_and_returns_dict():
    # Garde contre une RuntimeError autograd in-place (forward unique + retain_graph + 3 step).
    teachers = _make_teachers()
    out = _train_flat_lr_perhead(2200, teachers, steps=10)
    assert set(out.keys()) == {"action", "value", "pred"}
    for k in out:
        assert np.isfinite(out[k])
        assert out[k] >= 0.0


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_lr_perhead_differs_from_loss_scaling():
    # Coeur de l'hypothese : moduler le lr != moduler la loss sous Adam par-tete.
    from tools.disjoint_heads_synergy import _train_flat_norm_perhead
    teachers = _make_teachers()
    lr_out = _train_flat_lr_perhead(2200, teachers, steps=50)
    syn_out = _train_flat_norm_perhead(2200, teachers, steps=50)
    assert (abs(lr_out["value"] - syn_out["value"]) > 1e-6
            or abs(lr_out["pred"] - syn_out["pred"]) > 1e-6)


from tools.disjoint_heads_lr import main_lr_check


def test_smoke_lr_returns_verdict():
    res = main_lr_check(K=2, base=2200, steps=30, _return=True)
    assert res["verdict"] in {"LR_CLOSES", "LR_INTERCHANGEABLE", "PARTIAL", "SKIPPED_NO_TORCH"}
    assert "per_seed" in res


@pytest.mark.skipif(torch is None, reason="PyTorch indisponible")
def test_lr_check_deterministic_two_passes():
    a = main_lr_check(K=2, base=2200, steps=50, _return=True)
    b = main_lr_check(K=2, base=2200, steps=50, _return=True)
    assert a["mean_recovery"] == b["mean_recovery"]
    assert [r["recovery"] for r in a["per_seed"]] == [r["recovery"] for r in b["per_seed"]]
