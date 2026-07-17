"""Tests du payoff de la mémoire (MEM-001, 4e modalité de l'instrument within-subject). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.memory_payoff_probe import run, _memory, _obs_at_probe
import numpy as np


def test_ablation_collapses_only_when_recall_demanded():
    # WITHIN : ablater la mémoire effondre le rappel dans DEMAND, pas dans MEMORYLESS.
    r = run(K=6, delay=5, lam=0.85, seed=0)
    dem = r["MEMORY-DEMAND"]
    mless = r["MEMORYLESS"]
    assert dem["acc_ablated"] < dem["acc_true"] * 0.6
    assert mless["acc_ablated"] > mless["acc_true"] * 0.9


def test_memory_read_only_when_it_pays():
    # corroborant : poids sur la mémoire >0 en DEMAND, ~0 en MEMORYLESS (readout l'ignore si superflue).
    r = run(K=6, delay=5, lam=0.85, seed=1)
    assert r["MEMORY-DEMAND"]["mem_w"] > 0.3
    assert r["MEMORYLESS"]["mem_w"] < 0.15


def test_memoryless_has_empty_memory():
    # en memoryless, l'indice n'entre jamais dans la mémoire du passé -> m = 0.
    assert np.allclose(_memory(cue=2, demanding=False, delay=5, lam=0.85, K=6), 0.0)
    # en demanding, la mémoire retient la direction de l'indice (non nulle).
    m = _memory(cue=2, demanding=True, delay=5, lam=0.85, K=6)
    assert m[2] > 0 and int(np.argmax(m)) == 2


def test_probe_obs_hidden_iff_demanding():
    assert np.allclose(_obs_at_probe(3, demanding=True, K=6), 0.0)      # caché -> il faut la mémoire
    assert _obs_at_probe(3, demanding=False, K=6)[3] == 1.0            # visible -> obs courante suffit
