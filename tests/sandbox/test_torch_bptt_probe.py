"""Test de la frontière BPTT (EDR-145) : torch résout la mémoire multi-pas que le 1-pas ne peut pas.
Pur (pas de biosphère). Skip propre si torch absent."""
import sys, os, inspect
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.torch_bptt_probe import train_copy_task


def test_bptt_solves_memory_task_truncated_does_not():
    # T=8 + distracteurs : BPTT façonne W à travers le temps (mémoire), le 1-pas (détaché) ne peut pas.
    acc_bptt = train_copy_task("bptt", T=8, epochs=300, seed=0)
    acc_trunc = train_copy_task("truncated", T=8, epochs=300, seed=0)
    assert acc_bptt > 0.85              # BPTT résout la mémoire à 8 pas
    assert acc_trunc < 0.80            # le crédit 1-pas (numpy/legacy) reste bien en-dessous
    assert acc_bptt - acc_trunc > 0.15  # écart net = la capacité débloquée par torch


def test_signature():
    p = inspect.signature(train_copy_task).parameters
    assert "mode" in p and "T" in p
