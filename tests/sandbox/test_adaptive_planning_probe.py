"""Tests de la profondeur de planning adaptative (PLAN-004, G4). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.adaptive_planning_probe import depth_from_fidelity, run_adaptive


def test_policy_monotone_in_fidelity():
    # plus le modèle est fidèle (MSE bas), plus la profondeur choisie est grande.
    deep = depth_from_fidelity(0.005, 4)
    mid = depth_from_fidelity(0.05, 4)
    shallow = depth_from_fidelity(0.20, 4)
    assert deep >= mid >= shallow
    assert deep == 4 and shallow == 1


def test_policy_within_bounds():
    for mse in (0.0, 0.01, 0.03, 0.08, 0.15, 0.5):
        k = depth_from_fidelity(mse, 4)
        assert 1 <= k <= 4


def test_adaptive_matches_max_success_cheaper():
    r = run_adaptive(d=8, K=4, exec_steps=5, n_test=100, depth_max=4, seed=0)
    ada_s = sum(row["adaptive"][0] for row in r["rows"])
    hi_s = sum(row["fixedmax"][0] for row in r["rows"])
    ada_c = sum(row["adaptive"][1] for row in r["rows"])
    hi_c = sum(row["fixedmax"][1] for row in r["rows"])
    assert ada_s >= hi_s - 0.15          # succès agrégé ~= fixe-max (à la tolérance de bruit près)
    assert ada_c < hi_c * 0.6            # nettement moins de calcul


def test_bad_model_gets_shallow_depth():
    # sur le régime linéaire (mauvais modèle), la profondeur adaptative doit être faible.
    r = run_adaptive(d=8, K=4, exec_steps=4, n_test=80, depth_max=4, seed=1)
    lin = next(row for row in r["rows"] if row["kind"] == "linear")
    assert lin["depth_ada"] <= 2
