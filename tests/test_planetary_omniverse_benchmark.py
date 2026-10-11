"""
tests/test_planetary_omniverse_benchmark.py — Validation du banc planétaire omniversel.
"""
import pytest
from tools.planetary_omniverse_benchmark import run_planetary_omniverse_benchmark


def test_planetary_omniverse_benchmark_execution():
    res = run_planetary_omniverse_benchmark(num_steps=15)
    assert res["steps"] == 15
    assert res["mean_kardashev"] > 0.3
    assert "final_report" in res
