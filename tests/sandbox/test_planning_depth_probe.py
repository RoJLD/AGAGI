"""Tests de la profondeur de planning × fidélité (PLAN-003, G4). Pur numpy."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tools.planning_depth_probe import run_depth


def test_run_depth_smoke_keys():
    r = run_depth(d=6, K=3, exec_steps=3, n_test=40, depths=(1, 2), noise=0.1, seed=0, n_fit=1500)
    assert set(r["models"]) == {"perfect", "bilinear", "bilinear_noisy", "linear"}
    for kind in r["models"]:
        for k in (1, 2):
            assert 0.0 <= r["models"][kind][k] <= 1.0


def test_depth_helps_faithful_model():
    # avec un modèle fidèle (bilinéaire), planifier plus profond aide (meilleur k > depth-1).
    r = run_depth(d=8, K=4, exec_steps=5, n_test=100, depths=(1, 3), noise=0.15, seed=1)
    bi = r["models"]["bilinear"]
    assert bi[3] > bi[1] + 0.05


def test_bad_model_stuck_at_all_depths():
    # un modèle inadéquat (linéaire sur dynamique action-conditionnée) reste bas à toute profondeur.
    r = run_depth(d=8, K=4, exec_steps=5, n_test=100, depths=(1, 2, 3, 4), noise=0.15, seed=2)
    lin = r["models"]["linear"]
    assert max(lin.values()) < 0.55           # jamais loin de la chance, quelle que soit la profondeur


def test_fidelity_gates_depth_gain():
    # le gain de profondeur du modèle fidèle dépasse celui du modèle inadéquat.
    r = run_depth(d=8, K=4, exec_steps=5, n_test=100, depths=(1, 2, 3, 4), noise=0.15, seed=3)
    gain_bi = max(r["models"]["bilinear"].values()) - r["models"]["bilinear"][1]
    gain_lin = max(r["models"]["linear"].values()) - r["models"]["linear"][1]
    assert gain_bi > gain_lin
