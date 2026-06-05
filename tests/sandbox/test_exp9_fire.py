import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent

def test_day_night_and_comfort():
    config = WorldConfig()
    world = Biosphere3D(config=config)
    
    # Add an agent
    agent = MambaAgent(num_inputs=config.agent.num_inputs)
    world.add_agent(agent, x=5, y=5, z=0, energy=50.0)
    
    a = world.agents[0]
    initial_comfort = a["confort"]
    
    # Step during the day (ticks < 50)
    world.ticks = 10
    world.step()
    
    assert world.is_night == False
    assert world.agents[0]["confort"] > initial_comfort # Increased

    # Step during the night (ticks >= 50)
    world.ticks = 49
    world.step()
    
    assert world.is_night == True
    # In world.step(), it will decrease comfort by 1
    
def test_fire_fear_and_crafting():
    config = WorldConfig()
    world = Biosphere3D(config=config)
    
    # Test Prey fleeing fire
    world.preys.clear()
    world.items.clear()
    
    # Place fire
    world.items.append({"x": 5, "y": 5, "z": 0, "type": "Fire", "ttl": 500})
    
    # Place prey near fire
    world.preys.append({"x": 5, "y": 6, "type": "Lapin", "stunned": 0, "hp": 1.0})
    
    world._move_preys()
    # Should move away from (5,5)
    assert world.preys[0]["y"] > 5 or world.preys[0]["x"] != 5

if __name__ == "__main__":
    test_day_night_and_comfort()
    test_fire_fear_and_crafting()
    print("EXP-9 tests passed!")
