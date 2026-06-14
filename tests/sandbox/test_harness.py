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


def test_rng_generator_isolated_from_global_seed():
    # Le Generator .rng doit être isolé du RNG global : perturber np.random ne change rien.
    a = SeedManager(7).rng.random()
    np.random.seed(0)
    b = SeedManager(7).rng.random()
    assert a == b


def test_seed_boundary_returns_effective_seed():
    assert SeedManager(100).seed_boundary(5) == 105


def test_seed_boundary_no_overflow_near_max():
    # base proche de 2**32 + i>0 ne doit PAS lever ValueError (modulo 2**32).
    s = SeedManager(2 ** 32 - 1).seed_boundary(3)
    assert 0 <= s < 2 ** 32


from src.seed_ai.harness import Harness


def test_harness_resolves_and_exposes_seed():
    with Harness(seed=1, name="t", with_db=False) as h:
        assert h.seed == 1
        assert h.db is None            # with_db=False -> pas de DB, pas de crash


def test_harness_seeds_boot_deterministically():
    with Harness(seed=99, name="t", with_db=False):
        a = np.random.rand()
    with Harness(seed=99, name="t", with_db=False):
        b = np.random.rand()
    assert a == b


def test_harness_none_seed_is_logged_int():
    with Harness(seed=None, name="t", with_db=False) as h:
        assert isinstance(h.seed, int) and 0 <= h.seed < 2 ** 32


def test_harness_with_db_false_never_starts_logger():
    with Harness(seed=1, name="t", with_db=False) as h:
        assert h._logger_started is False


def test_harness_exit_without_enter_is_safe():
    h = Harness(seed=1, name="t", with_db=False)
    h.__exit__(None, None, None)  # ne doit pas crasher


def test_eval_robust_is_reproducible():
    def fake_run_era(cfg, genomes):
        return None, {"score": float(np.random.rand())}
    s1 = Harness(seed=42, with_db=False).eval_robust(None, "g", fake_run_era, K=3, num_agents=1)
    s2 = Harness(seed=42, with_db=False).eval_robust(None, "g", fake_run_era, K=3, num_agents=1)
    assert s1 == s2


def test_eval_robust_pairs_conditions_on_seed():
    # Chaque ère re-seede sa frontière -> le 1er tirage ("monde initial") est identique pour
    # deux conditions au même seed, MÊME si elles consomment ensuite le flux differemment.
    worlds_a, worlds_b = [], []

    def run_era_a(cfg, genomes):
        worlds_a.append(float(np.random.rand()))  # monde
        np.random.rand()                          # condition A consomme
        return None, {"score": 0.0}

    def run_era_b(cfg, genomes):
        worlds_b.append(float(np.random.rand()))  # monde (même seed -> même valeur)
        np.random.rand(); np.random.rand()        # condition B consomme PLUS
        return None, {"score": 0.0}

    Harness(seed=7, with_db=False).eval_robust(None, "ga", run_era_a, K=3, num_agents=1)
    Harness(seed=7, with_db=False).eval_robust(None, "gb", run_era_b, K=3, num_agents=1)
    assert worlds_a == worlds_b   # mondes initiaux APPARIÉS


def test_save_writes_seed_and_commit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    h = Harness(seed=5, name="demo", with_db=False)
    path = h.save({"metric": 1.0})
    import json as _json
    with open(path, encoding="utf-8") as f:
        out = _json.load(f)
    assert out["seed"] == 5 and out["name"] == "demo" and "commit" in out
    assert out["data"]["metric"] == 1.0
