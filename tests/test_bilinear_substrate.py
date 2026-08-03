import pytest

pytest.importorskip("torch")
import numpy as np
import torch

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel


def _pop(n=4, seed=0):
    np.random.seed(seed); torch.manual_seed(seed)
    return make_population([MambaAgent() for _ in range(n)], backend="torch")


def test_bilinear_off_is_bit_identical_reference():
    """BILINEAR=False (défaut) : _step == formule de référence (1-δ)H+δtanh(H·W_off), bit-à-bit."""
    assert TorchPopulationModel.BILINEAR is False   # défaut off
    m = _pop()
    assert m.U is None and m.V is None and m.W_bl is None
    H = torch.randn(m.B, m.N)
    obs = torch.randn(m.B, m.I)
    got = m._step(obs, H)
    # référence explicite
    Href = H.clone(); Href[:, :m.I] = obs
    diag = torch.diagonal(m.W, dim1=1, dim2=2)
    delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
    W_off = m.W * (1.0 - m._eye)
    exc = torch.bmm(Href.unsqueeze(1), W_off).squeeze(1)
    ref = (1.0 - delta) * Href + delta * torch.tanh(exc)
    assert torch.equal(got, ref), "BILINEAR=False doit être bit-identique à la référence"


def test_bilinear_on_creates_params_and_changes_step():
    """BILINEAR=True : params U/V/W_bl créés (bonnes formes), et _step diffère de la référence linéaire."""
    saved = TorchPopulationModel.BILINEAR
    TorchPopulationModel.BILINEAR = True
    try:
        m = _pop()
        r = TorchPopulationModel.BILINEAR_RANK
        assert m.U.shape == (m.B, m.N, r) and m.V.shape == (m.B, m.N, r) and m.W_bl.shape == (m.B, r, m.N)
        assert all(p.requires_grad for p in (m.U, m.V, m.W_bl))
        assert any(p is m.U for p in m.opt.param_groups[0]["params"])   # dans l'optimiseur par défaut
        H = torch.randn(m.B, m.N); obs = torch.randn(m.B, m.I)
        got = m._step(obs, H)
        Href = H.clone(); Href[:, :m.I] = obs
        diag = torch.diagonal(m.W, dim1=1, dim2=2); delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
        exc = torch.bmm(Href.unsqueeze(1), (m.W * (1.0 - m._eye))).squeeze(1)
        lin_ref = (1.0 - delta) * Href + delta * torch.tanh(exc)
        assert not torch.equal(got, lin_ref), "BILINEAR=True doit ajouter un terme (≠ linéaire)"
    finally:
        TorchPopulationModel.BILINEAR = saved
