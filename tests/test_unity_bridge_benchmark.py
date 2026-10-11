"""
tests/test_unity_bridge_benchmark.py — Validation du banc de la passerelle Unity 3D.
"""
import pytest
from tools.unity_bridge_benchmark import run_unity_bridge_benchmark


def test_unity_bridge_benchmark_execution():
    res = run_unity_bridge_benchmark(num_steps=20)
    assert res["steps"] == 20
    assert res["fps"] > 10.0
    assert "final_metrics" in res
