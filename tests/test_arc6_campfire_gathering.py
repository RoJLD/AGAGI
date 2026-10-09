import pytest
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import World1StoneAge
from src.agents.mamba_agent import MambaAgent

def test_campfire_night_gathering_and_osmosis():
    cfg = WorldConfig()
    cfg.grid_size = 10
    cfg.prey_mode = "NONE"
    cfg.item_physics = {}
    world = World1StoneAge(cfg)
    world.benchmark_mode = True  # cohorte stable sans repro non contrôlée
    
    # Placer un feu au centre
    fire_pos = (5, 5)
    world.items.append({
        "type": "Fire",
        "id": "campfire_alpha",
        "x": 5,
        "y": 5,
        "ttl": 20
    })
    
    # Créer 2 agents près du feu
    m1 = MambaAgent(num_inputs=cfg.agent.num_inputs)
    m2 = MambaAgent(num_inputs=cfg.agent.num_inputs)
    # Assurer que les connectomes W diffèrent initialement
    m2.genome.W += 0.5
    
    a1 = world.add_agent(m1, x=5, y=5, energy=80.0)
    a2 = world.add_agent(m2, x=5, y=5, energy=40.0) # a2 est moins énergétique => élève
    
    # Agent témoin loin du feu (dans le froid nocturne)
    m_ctrl = MambaAgent(num_inputs=cfg.agent.num_inputs)
    a_ctrl = world.add_agent(m_ctrl, x=0, y=0, energy=80.0)
    
    a1["confort"] = 20.0
    a2["confort"] = 20.0
    a_ctrl["confort"] = 20.0
    
    # Forcer la nuit via le cycle circadien (ticks >= 50)
    world.ticks = 50
    world.training_mode = False
    
    # Capturer le génome de départ de a2
    w_before = np.copy(a2["model"].genome.W)
    
    # Effectuer un step
    world.step()
    
    # 1. Vérifier le confort thermique relatif la nuit (près du feu vs dans le froid)
    assert a1["confort"] >= a_ctrl["confort"], "L'agent près du feu doit avoir un meilleur confort que dans le froid"
    
    # 2. Vérifier que le rassemblement est compté
    assert world.campfire_gatherings >= 1, "Le rassemblement nocturne au feu doit être comptabilisé"
    
    # 3. Vérifier la transmission culturelle HGT (mentorat)
    assert world.campfire_transfers >= 1, "L'aîné doit transmettre des connaissances à l'élève près du feu"
    assert not np.allclose(w_before, a2["model"].genome.W), "Les poids du modèle élève doivent avoir évolué par osmose HGT"

def test_campfire_ttl_decay():
    cfg = WorldConfig()
    cfg.grid_size = 6
    cfg.prey_mode = "NONE"
    world = World1StoneAge(cfg)
    
    # Ajouter au moins un agent pour que le cycle step() avance
    m = MambaAgent(num_inputs=cfg.agent.num_inputs)
    world.add_agent(m, x=0, y=0, energy=50.0)
    
    world.items.append({
        "type": "Fire",
        "id": "fire_temp",
        "x": 2,
        "y": 2,
        "ttl": 1
    })
    
    assert any(it.get("type") == "Fire" for it in world.items)
    world.step()
    # Après 1 step avec ttl=1, le feu doit être éteint
    fires = [it for it in world.items if it.get("type") == "Fire"]
    assert len(fires) == 0, "Le feu doit s'éteindre quand son TTL expire"
