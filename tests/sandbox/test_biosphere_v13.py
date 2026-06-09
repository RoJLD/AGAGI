import numpy as np
import pytest
from unittest.mock import MagicMock
from src.environments.biosphere import Biosphere3D

def test_v13_item_generation():
    env = Biosphere3D(size=10)
    assert hasattr(env, "items"), "L'environnement doit avoir une liste 'items'."
    assert not hasattr(env, "balls"), "L'attribut 'balls' doit être supprimé."
    assert len(env.items) > 0, "Des items (rocks/sticks) doivent être générés dans l'environnement."
    
    # Vérification de la génération des arbres
    assert np.any(env.geometry == 4), "Il doit y avoir des troncs d'arbre (geo=4)."
    assert np.any(env.geometry == 5), "Il doit y avoir des feuilles (geo=5)."

def test_v13_observation_size():
    env = Biosphere3D(size=10)
    genome_mock = MagicMock()
    genome_mock.num_nodes = 50
    env.add_agent(genome_mock, x=5, y=5, z=5)
    agent = env.agents[0]
    
    # Ajout d'items simulés pour tester les dimensions
    agent["inventory"] = ["stick_short", "rock_small"]
    obs = env._get_agent_observation(agent)
    
    assert obs.shape == (1, 33), f"L'observation V13 doit avoir 33 entrées (obtenu: {obs.shape[1]})."

def test_v13_inventory_capacity():
    env = Biosphere3D(size=10)
    genome_mock = MagicMock()
    genome_mock.num_nodes = 50
    env.add_agent(genome_mock, x=5, y=5, z=5)
    agent = env.agents[0]
    
    assert isinstance(agent["inventory"], list), "L'inventaire doit être une liste (pouvant contenir plusieurs IDs d'items)."
