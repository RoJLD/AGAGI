import numpy as np
from typing import Dict, Tuple, Union

class DynamicPhysicsRegistry:
    """
    V17 Dynamic Physics Registry.
    Provides dynamically resolved physical properties (weight, sharpness, edibility, friction, flammability)
    for emergent crafted or generated items, avoiding hard-coded tables.
    """
    
    def __init__(self, initial_physics: Dict[str, Tuple[float, float, float, float, float]] = None):
        self._registry = {
            "meat": (0.5, 0.0, 1.0, 0.1, 0.0),
            "spear": (2.0, 1.0, 0.0, 0.5, 0.5),
            "rock": (1.0, 0.5, 0.0, 0.8, 0.0),
            "stick": (0.5, 0.2, 0.0, 0.6, 1.0),
            "wood": (1.0, 0.5, 0.0, 0.6, 1.0),
            "spark": (0.0, 0.0, 0.0, 0.0, 0.0),
            "fire": (0.0, 0.0, 0.0, 0.0, 0.0),
            "fruit": (0.5, 0.0, 1.0, 0.1, 0.0),
            "seed": (0.1, 0.0, 0.1, 0.1, 0.0)
        }
        if initial_physics:
            for k, v in initial_physics.items():
                self._registry[k.lower()] = v
                
    def get_properties(self, item_name: str) -> Tuple[float, float, float, float, float]:
        """
        Retrieves the 5-tuple of properties for an item.
        If unknown, estimates using sub-word composition (e.g. 'heavy_rock' -> rock).
        """
        if not isinstance(item_name, str):
            item_name = str(item_name)
            
        key = item_name.lower().strip()
        if key in self._registry:
            return self._registry[key]
            
        # Composite matching (e.g. "stone_spear" -> match "spear")
        for ref_key, ref_val in self._registry.items():
            if ref_key in key:
                # Sub-string match found! We adapt the properties.
                # If it's a composite, let's adjust weight slightly if it starts with "heavy_" or similar.
                weight, sharp, food, friction, flam = ref_val
                if "heavy" in key:
                    weight *= 1.5
                elif "light" in key or "small" in key:
                    weight *= 0.5
                
                # Cache the resolved value
                self._registry[key] = (weight, sharp, food, friction, flam)
                return self._registry[key]
                
        # Default fallback (neutral properties)
        fallback = (0.5, 0.0, 0.0, 0.5, 0.2)
        self._registry[key] = fallback
        return fallback

    def register_item(self, item_name: str, properties: Tuple[float, float, float, float, float]):
        """Allows LLM operator or simulator to register new emergent physical properties."""
        self._registry[item_name.lower().strip()] = properties
