"""Tests du probe de parité torch↔legacy (EDR-141, item 2). Pur (pas de biosphère)."""
import sys, os, inspect
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np, pytest
pytest.importorskip("torch")

from tools.torch_parity_probe import per_tick_divergence
from src.agents.mamba_agent import MambaAgent


def _genome():
    return MambaAgent().genome


def test_bit_parity_every_tick_after_mask_port():
    # EDR-144 : torch réplique le masque d'attention d'entrée -> parité BIT-À-BIT à CHAQUE tick.
    d = per_tick_divergence(_genome(), ticks=8)
    assert max(d) < 1e-4


def test_forcing_legacy_mask_off_breaks_parity():
    # neutraliser SEULEMENT le masque de legacy (torch garde le sien) -> divergence
    # = preuve que le masque d'attention d'entrée est bien load-bearing dans la parité.
    d = per_tick_divergence(_genome(), ticks=8, force_legacy_mask_ones=True)
    assert max(d) > 1e-3


def test_signature():
    p = inspect.signature(per_tick_divergence).parameters
    assert "genome" in p and "force_legacy_mask_ones" in p
