"""TDD B2 — la mémoire n'est survival-porteuse que si corps insuffisant ET rappel différé ET énergie."""
import numpy as np
from tools.memory_demand_world_probe import survive, probe


def test_sufficient_body_survives_without_memory():
    # réflexe corps suffisant (1.2>metab) : survit au cap même mémoire ablatée
    K = 5
    W = np.zeros((K, 2 * K)); b = np.zeros(K); b[0] = 10.0     # force a=0 (réflexe corps)
    s = survive(W, b, "ablated", body_gain=1.2, cog_gain=5.0, currency="energy", recall="delayed",
                K=K, rng=np.random.RandomState(1), ticks=200)
    assert s == 200


def test_recipe_insufficient_delayed_energy_is_memory_sensitive():
    # RECETTE : corps insuffisant + rappel DIFFÉRÉ + énergie -> survie exige la mémoire -> ablation effondre
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", recall="delayed", K=5, seed=2,
              n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_MEMORY_SENSITIVE"
    assert r["mem_weight"] > 0.05                              # la politique PÈSE la mémoire


def test_present_recall_is_neutral():
    # rappel PRÉSENT (l'obs montre l'action correcte) : la mémoire est inutile -> ablation inerte -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", recall="present", K=5, seed=2,
              n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_NEUTRAL"


def test_separate_currency_is_neutral():
    # devise séparée : réussir le rappel ne paie pas la survie -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=20.0, currency="separate", recall="delayed", K=5, seed=2,
              n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_NEUTRAL"
