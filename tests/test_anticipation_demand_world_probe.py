"""TDD C1 — l'anticipation (application d'un forward-model) est survival-porteuse SSI corps insuffisant +
dynamique non-triviale (shift≠0) + énergie. Ablation = module M→identité."""
import numpy as np
from tools.anticipation_demand_world_probe import survive, probe, _model_matrix, _shifted


def test_model_matrix_implements_shift():
    K, shift = 5, 1
    M = _model_matrix(shift, K)
    for s in range(1, K):
        o = np.zeros(K); o[s] = 1.0
        assert int(np.argmax(M @ o)) == _shifted(s, shift, K)   # M applique la dynamique
    assert M[0, 0] == 1.0                                        # identité sur le corps


def test_recipe_insufficient_dynamic_energy_is_anticipation_sensitive():
    # RECETTE : corps insuffisant + shift=1 (futur) + énergie -> survie exige le modèle -> ablation effondre
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", shift=1, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_ANTICIPATION_SENSITIVE"


def test_static_dynamics_is_neutral():
    # shift=0 (nourriture statique) : le réactif (identité) suffit -> ablation du module inerte -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", shift=0, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_NEUTRAL"


def test_separate_currency_is_neutral():
    # devise séparée : anticiper ne paie pas la survie -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=20.0, currency="separate", shift=1, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_NEUTRAL"
