import numpy as np
from tools.famine_storage_probe import count_reserves, measure_genome
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from src.environments.config import WorldConfig


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
