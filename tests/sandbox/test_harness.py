# tests/sandbox/test_harness.py
import numpy as np
from src.seed_ai.harness import SeedManager


def test_resolve_returns_given_int():
    assert SeedManager.resolve(123) == 123


def test_resolve_draws_valid_int_when_none():
    s = SeedManager.resolve(None)
    assert isinstance(s, int) and 0 <= s < 2 ** 32


def test_seed_boundary_is_reproducible():
    SeedManager(42).seed_boundary(0)
    a = np.random.rand()
    SeedManager(42).seed_boundary(0)
    b = np.random.rand()
    assert a == b


def test_seed_boundary_independent_across_eras():
    sm = SeedManager(100)
    sm.seed_boundary(0)
    a = np.random.rand()
    sm.seed_boundary(1)
    b = np.random.rand()
    assert a != b


def test_rng_generator_is_seeded():
    assert SeedManager(7).rng.random() == SeedManager(7).rng.random()
