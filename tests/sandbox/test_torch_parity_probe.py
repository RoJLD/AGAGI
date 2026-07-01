"""Tests du probe de parité torch↔legacy (EDR-141, item 2). Pur (pas de biosphère)."""
import sys, os, inspect
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import numpy as np, pytest
pytest.importorskip("torch")

from tools.torch_parity_probe import per_tick_divergence
from src.agents.mamba_agent import MambaAgent


def _genome():
    return MambaAgent().genome


def test_per_step_parity_is_exact_at_t0():
    # t=0 (depuis H=0 identique) : legacy-core et torch-swish calculent la MÊME chose.
    d = per_tick_divergence(_genome(), ticks=3)
    assert d[0] < 1e-4


def test_masking_off_gives_bit_parity_every_tick():
    # neutraliser le masque d'attention d'entrée de legacy -> parité à CHAQUE tick (le résidu = ce masque).
    d = per_tick_divergence(_genome(), ticks=8, force_legacy_mask_ones=True)
    assert max(d) < 1e-4


def test_signature():
    p = inspect.signature(per_tick_divergence).parameters
    assert "genome" in p and "force_legacy_mask_ones" in p
