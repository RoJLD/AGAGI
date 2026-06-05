"""
Unit tests for Projectiles Physics (V12/V13 ARC 2)
[Commandment 7] Test-Driven Metaprogramming Sandbox Validation
"""
import numpy as np
import pytest
from src.environments.projectiles import ProjectilePhysics, ProjectileConfig

def test_calculate_throw_scalar():
    """Test scalar projectile throw logic."""
    physics = ProjectilePhysics()
    portee, cost = physics.calculate_throw(agent_energy=50.0, item_weight=2.0)
    
    # Expected range: int((10 / 2) * (1 + 50/100)) = int(5 * 1.5) = 7
    assert portee == 7
    # Expected cost: 2.0 * 2.0 = 4.0
    assert cost == 4.0

def test_calculate_damage_scalar():
    """Test scalar damage/stun tick logic."""
    physics = ProjectilePhysics()
    stun = physics.calculate_damage(item_weight=2.0, distance_traveled=3.0, max_range=7.0)
    
    # Speed: max(0.1, (7-3)/7) = max(0.1, 4/7) = 0.5714
    # Stun: int(2.0 * 0.5714 * 10) = int(11.428) = 11
    assert stun == 11

def test_vectorized_throw_and_damage():
    """
    [Commandment 3] Validate that the operations support vectorized 
    arrays natively without loops.
    """
    physics = ProjectilePhysics()
    
    # Simulate a Swarm of 3 agents throwing items
    energies = np.array([50.0, 100.0, 0.0])
    weights = np.array([2.0, 1.0, 5.0])
    
    ranges, costs = physics.calculate_throw(energies, weights)
    
    # Validate Ranges: 
    # 1: (10/2) * 1.5 = 7
    # 2: (10/1) * 2.0 = 20
    # 3: (10/5) * 1.0 = 2
    np.testing.assert_array_equal(ranges, np.array([7, 20, 2]))
    np.testing.assert_array_equal(costs, np.array([4.0, 2.0, 10.0]))
    
    # Validate Damage Vectors
    distances = np.array([3.0, 19.0, 2.0])
    stuns = physics.calculate_damage(weights, distances, ranges)
    
    # Stuns:
    # 1: 2.0 * ((7-3)/7) * 10 = 11
    # 2: 1.0 * max(0.1, 1/20) * 10 = 1.0 * 0.1 * 10 = 1
    # 3: 5.0 * max(0.1, 0/2) * 10 = 5.0 * 0.1 * 10 = 5
    np.testing.assert_array_equal(stuns, np.array([11, 1, 5]))
