"""
tests/test_autotelic_curriculum_benchmark.py — Validation du banc de curriculum autotélique.
"""
import pytest
from tools.autotelic_curriculum_benchmark import run_autotelic_curriculum_benchmark


def test_autotelic_benchmark_execution():
    res = run_autotelic_curriculum_benchmark(num_cycles=4)
    assert res["cycles"] == 4
    assert res["scalings_count"] >= 1
    assert res["final_complexity"] >= 2
    assert res["mean_competence"] > 0.6
