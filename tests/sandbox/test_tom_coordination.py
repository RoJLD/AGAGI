import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.tom_coordination import (
    _hunt_samples_from_state,
    _recruitment_signal,
    _verdict_coordination,
)


def test_hunt_samples_fresh_mammoth_only_near_agents():
    preys = [
        {"type": "Mammouth", "x": 5, "y": 5, "hp": 80.0},
        {"type": "Mammouth", "x": 0, "y": 0, "hp": 10.0},
        {"type": "Lapin", "x": 5, "y": 5, "hp": 1.0},
    ]
    agents = [
        {"x": 5, "y": 5},
        {"x": 5, "y": 6},
        {"x": 15, "y": 15},
        {"x": 0, "y": 0},
    ]
    samples = _hunt_samples_from_state(agents, preys, mammoth_hp=100.0)
    assert len(samples) == 2
    assert sorted(s["attacking"] for s in samples) == [False, True]
    assert all(s["others_near"] == 1 for s in samples)


def test_recruitment_signal_rates():
    samples = [
        {"attacking": True, "others_near": 2},
        {"attacking": False, "others_near": 1},
        {"attacking": True, "others_near": 0},
        {"attacking": False, "others_near": 0},
    ]
    sig = _recruitment_signal(samples)
    assert sig["n_with"] == 2 and sig["n_alone"] == 2
    assert sig["p_with"] == 0.5 and sig["p_alone"] == 0.5
    assert sig["delta"] == 0.0


def test_recruitment_signal_empty_buckets():
    sig = _recruitment_signal([{"attacking": True, "others_near": 3}])
    assert sig["p_alone"] == 0.0 and sig["n_alone"] == 0
    assert sig["p_with"] == 1.0 and sig["n_with"] == 1


def test_verdict_coordination_three_branches():
    assert _verdict_coordination({"delta": 0.15, "n_with": 30, "n_alone": 30}) == "COORDINATED"
    assert _verdict_coordination({"delta": 0.02, "n_with": 30, "n_alone": 30}) == "INDEPENDENT"
    assert _verdict_coordination({"delta": 0.15, "n_with": 5, "n_alone": 30}) == "INDETERMINE"
