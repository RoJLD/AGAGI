"""Tests du banc gate+BPTT means→ends (EDR-147). Pur (pas de biosphère). Skip si torch absent."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
pytest.importorskip("torch")

from tools.torch_gate_bptt_meansends import run_cell


def test_run_cell_smoke_all_four():
    # les 4 cellules du 2×2 tournent et renvoient les métriques de binding.
    for mode in ("truncated", "bptt"):
        for gate in (False, True):
            r = run_cell(mode, gate, epochs=20, n_agents=16, seed=0, antisat=6.0)
            assert set(r) >= {"hit_end", "p_x", "binding_gap", "gate", "mode"}
            assert r["mode"] == mode and r["gate"] is gate
            assert -1.0 <= r["binding_gap"] <= 1.0


def test_gate_updates_when_enabled():
    # avec gate, l'entraînement doit produire un binding_gap != celui du no-gate au même seed
    # (le gate modifie la dynamique) -> smoke de non-dégénérescence.
    r_gate = run_cell("truncated", True, epochs=60, n_agents=32, seed=1, antisat=6.0)
    r_none = run_cell("truncated", False, epochs=60, n_agents=32, seed=1, antisat=6.0)
    assert r_gate["binding_gap"] != r_none["binding_gap"]


def test_antisat_zero_is_accepted():
    # antisat=0 (pas de pénalité) est un régime valide (contrôle).
    r = run_cell("bptt", True, epochs=20, n_agents=16, seed=0, antisat=0.0)
    assert "binding_gap" in r
