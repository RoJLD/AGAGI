"""Harnais d'évaluation puissant (EDR 052) : distingue signal et bruit."""
from src.seed_ai.eval_harness import powered_eval, verdict, rank, is_robust_winner


def _const(value_map):
    # run_seed_fn déterministe : renvoie une valeur par (condition, seed) depuis un dict.
    def fn(cfg, seed):
        return value_map[cfg][seed]
    return fn


def test_powered_eval_aggregates():
    vals = {"A": {0: 1.0, 1: 2.0, 2: 3.0}}
    res = powered_eval({"A": "A"}, _const(vals), seeds=(0, 1, 2))
    assert abs(res["A"]["mean"] - 2.0) < 1e-9
    assert res["A"]["n"] == 3 and res["A"]["std"] > 0


def test_verdict_flags_clear_difference_significant():
    # A nettement > B, faible variance -> significatif.
    vals = {"A": {0: 0.90, 1: 0.95, 2: 0.92}, "B": {0: 0.10, 1: 0.12, 2: 0.08}}
    res = powered_eval({"A": "A", "B": "B"}, _const(vals), seeds=(0, 1, 2))
    v = verdict("A", "B", res)
    assert v["significant"] and v["winner"] == "A"


def test_verdict_flags_noise_as_non_significant():
    # Moyennes proches, variance large, intervalles qui se chevauchent -> bruit.
    vals = {"A": {0: 0.10, 1: 0.90, 2: 0.30}, "B": {0: 0.80, 1: 0.15, 2: 0.50}}
    res = powered_eval({"A": "A", "B": "B"}, _const(vals), seeds=(0, 1, 2))
    v = verdict("A", "B", res)
    assert not v["significant"] and v["winner"] is None


def test_is_robust_winner():
    clear = {"win": {0: 1.0, 1: 1.1, 2: 0.9}, "lose": {0: 0.0, 1: 0.1, 2: -0.1}}
    res = powered_eval({"win": "win", "lose": "lose"}, _const(clear), seeds=(0, 1, 2))
    name, v = is_robust_winner(res)
    assert name == "win"
    # Bruit : pas de gagnant robuste.
    noisy = {"x": {0: 0.5, 1: 0.1, 2: 0.9}, "y": {0: 0.4, 1: 0.6, 2: 0.2}}
    res2 = powered_eval({"x": "x", "y": "y"}, _const(noisy), seeds=(0, 1, 2))
    name2, _ = is_robust_winner(res2)
    assert name2 is None


def test_rank_orders_by_mean():
    vals = {"hi": {0: 0.9}, "mid": {0: 0.5}, "lo": {0: 0.1}}
    res = powered_eval({"hi": "hi", "mid": "mid", "lo": "lo"}, _const(vals), seeds=(0,))
    assert [n for n, _, _ in rank(res)] == ["hi", "mid", "lo"]
