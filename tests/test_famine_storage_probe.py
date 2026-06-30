import numpy as np
from tools.famine_storage_probe import count_reserves, measure_genome, evolve_in_famine, compute_emergence_verdict
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.environments.config import WorldConfig
from src.seed_ai.mutation import Genome


def test_count_reserves_counts_fruits_and_masked():
    agent = {"inventory": [
        {"type": "Fruit", "weight": 0.5},
        {"type": "_FruitReserve", "weight": 0.5},
        {"type": "Spear", "weight": 1.0},
        "not_a_dict",
    ]}
    assert count_reserves(agent) == 2


def test_measure_genome_returns_survival_and_fruits():
    # un génome frais (petit run) ; on vérifie la FORME du retour, pas une valeur précise.
    genomes, _ = init_primordial_soup(num_agents=2, config=WorldConfig())
    g = genomes[0]
    out = measure_genome(g, seed=1, cache_enabled=True, num_agents=4, max_ticks=40,
                         cycle_abundance=10, cycle_famine=10)
    assert set(out) == {"median_survival", "fruits_at_transition"}
    assert out["median_survival"] >= 0.0
    assert out["fruits_at_transition"] >= 0.0


def test_evolve_in_famine_returns_genome():
    # smoke minimal : 2 ères, peu d'agents/ticks -> renvoie un Genome aux bonnes dims.
    g = evolve_in_famine(seed=3, eras=2, num_agents=4, max_ticks=30,
                         cycle_abundance=10, cycle_famine=10)
    assert isinstance(g, Genome)
    # Dimensions canoniques de la base main (num_inputs=59, num_outputs=108 via MambaAgent defaut)
    assert g.num_inputs == 59 and g.num_outputs == 108


def test_evolve_in_famine_deterministic():
    # même seed -> même champion (W identique). Repro (verrou Dev #3).
    g1 = evolve_in_famine(seed=5, eras=2, num_agents=4, max_ticks=30,
                          cycle_abundance=10, cycle_famine=10)
    g2 = evolve_in_famine(seed=5, eras=2, num_agents=4, max_ticks=30,
                          cycle_abundance=10, cycle_famine=10)
    assert np.array_equal(g1.W, g2.W)


def test_verdict_emerge_when_famine_delta_dominates():
    # l'évolué dépend du cache (gros delta), le stoneage non (delta ~0) -> EMERGE
    df = [40.0, 35.0, 50.0, 45.0, 38.0, 42.0, 47.0, 39.0]
    ds = [2.0, 1.0, 3.0, 0.0, 1.0, 2.0, 1.0, 0.0]
    v = compute_emergence_verdict(df, ds)
    assert v["verdict"] == "EMERGE"
    assert v["n"] == 8 and v["n_favorable"] == 8
    assert v["sign_p"] < 0.05


def test_verdict_n_emerge_pas_when_deltas_match():
    # aucun avantage cache spécifique à l'évolué -> N_EMERGE_PAS (finding substrat)
    df = [3.0, 2.0, 1.0, 4.0, 2.0, 3.0, 1.0, 2.0]
    ds = [2.0, 3.0, 2.0, 1.0, 3.0, 2.0, 2.0, 1.0]
    v = compute_emergence_verdict(df, ds)
    assert v["verdict"] == "N_EMERGE_PAS"


def test_verdict_empty():
    v = compute_emergence_verdict([], [])
    assert v["verdict"] == "N_EMERGE_PAS" and v["n"] == 0
