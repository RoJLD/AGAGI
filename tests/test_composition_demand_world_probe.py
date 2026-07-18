"""TDD C2 — la composition (chaîner un moyen non-récompensé vers une fin) est survival-porteuse SSI
corps insuffisant + chaîne ≥2 + énergie. Ablation = module de plan (identité du moyen → 0)."""
import numpy as np
from tools.composition_demand_world_probe import survive, probe


def test_sufficient_body_survives_without_plan():
    # réflexe corps suffisant (1.2>metab) : survit au cap même plan ablaté
    K = 5
    W = np.zeros((K, 2 * K)); b = np.zeros(K); b[0] = 10.0     # force a=0 (corps)
    s = survive(W, b, "ablated", body_gain=1.2, cog_gain=3.0, currency="energy", chain_len=2,
                K=K, rng=np.random.RandomState(1), ticks=200)
    assert s == 200


def test_recipe_insufficient_chain2_energy_is_composition_sensitive():
    # RECETTE : corps insuffisant + chaîne 2 (moyen requis) + énergie -> survie exige de composer
    r = probe(body_gain=0.5, cog_gain=3.0, currency="energy", chain_len=2, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_COMPOSITION_SENSITIVE"


def test_chain1_no_means_is_neutral():
    # chaîne 1 (fin directe, pas de moyen) : le plan est vide -> ablation inerte -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=3.0, currency="energy", chain_len=1, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_NEUTRAL"


def test_separate_currency_is_neutral():
    # devise séparée : composer ne paie pas la survie -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=20.0, currency="separate", chain_len=2, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_NEUTRAL"
