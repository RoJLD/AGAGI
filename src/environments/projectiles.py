"""
Projectiles Physics Module (V12/V13 ARC 2)
Handles the physics, energy costs, and impact calculations of thrown objects.
Follows AGIseed principles: Vectorized with NumPy, configurable, type-hinted.
"""

from dataclasses import dataclass
import numpy as np
from typing import Tuple, Union

@dataclass
class ProjectileConfig:
    """
    Hyperparameters for projectile physics.
    [Commandment 1] Avoids hard-coding and allows injecting configs.
    """
    base_range: float = 10.0
    energy_cost_multiplier: float = 2.0
    base_damage_multiplier: float = 10.0
    min_impact_speed: float = 0.1

class ProjectilePhysics:
    """
    Physics engine for thrown items like rocks or worms (ARC 2).
    [Commandment 3] Supports both scalar and vectorized NumPy operations 
    to prevent slow `for` loops during Swarm evaluations.
    """
    def __init__(self, config: ProjectileConfig = None):
        self.config = config or ProjectileConfig()

    def calculate_throw(
        self, 
        agent_energy: Union[float, np.ndarray], 
        item_weight: Union[float, np.ndarray]
    ) -> Tuple[Union[int, np.ndarray], Union[float, np.ndarray]]:
        """
        Calculates the maximum range and energy cost of throwing an item.
        
        Args:
            agent_energy: Current energy of the throwing agent(s).
            item_weight: Weight of the item(s) being thrown.
            
        Returns:
            Tuple containing (range_in_cells, energy_cost).
        """
        # Range = (base_range / weight) * (1.0 + agent_energy / 100.0)
        raw_range = (self.config.base_range / item_weight) * (1.0 + agent_energy / 100.0)
        
        # Support for vectorization
        if isinstance(raw_range, np.ndarray):
            portee = np.floor(raw_range).astype(int)
        else:
            portee = int(raw_range)
            
        cost = item_weight * self.config.energy_cost_multiplier
        return portee, cost

    def calculate_damage(
        self, 
        item_weight: Union[float, np.ndarray], 
        distance_traveled: Union[float, np.ndarray], 
        max_range: Union[float, np.ndarray]
    ) -> Union[int, np.ndarray]:
        """
        Calculates the damage (stun ticks) dealt by a projectile upon impact.
        
        Args:
            item_weight: Weight of the thrown item.
            distance_traveled: Distance the item has traveled before impact.
            max_range: The maximum range of the throw.
            
        Returns:
            Damage in terms of stun ticks (int or array of ints).
        """
        # Avoid division by zero if max_range is somehow 0
        safe_max_range = np.maximum(max_range, 1e-5) if isinstance(max_range, np.ndarray) else max(max_range, 1e-5)
        
        # Impact speed linearly decreases with distance
        ratio = (safe_max_range - distance_traveled) / safe_max_range
        
        if isinstance(ratio, np.ndarray):
            impact_speed = np.clip(ratio, self.config.min_impact_speed, None)
        else:
            impact_speed = max(self.config.min_impact_speed, ratio)
            
        # Stun calculation
        raw_stun = item_weight * impact_speed * self.config.base_damage_multiplier
        
        if isinstance(raw_stun, np.ndarray):
            return np.floor(raw_stun).astype(int)
        else:
            return int(raw_stun)
