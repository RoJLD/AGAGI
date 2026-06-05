"""
Crafting system for AGIseed Biosphere.
Implements item definitions, registry, and combination logic (blueprints).

Version: V13
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass(frozen=True)
class ItemConfig:
    """Configuration and attributes of an item in the biosphere."""
    type: str
    poids: float
    porte_lance: float
    degats: float
    effect: str

# Base item registry
ITEM_REGISTRY: Dict[str, ItemConfig] = {
    "rock_small": ItemConfig(type="rock_small", poids=0.5, porte_lance=15.0, degats=1.0, effect="none"),
    "rock_medium": ItemConfig(type="rock_medium", poids=1.5, porte_lance=8.0, degats=2.5, effect="none"),
    "rock_large": ItemConfig(type="rock_large", poids=3.0, porte_lance=3.0, degats=5.0, effect="none"),
    "stick_short": ItemConfig(type="stick_short", poids=0.3, porte_lance=10.0, degats=0.5, effect="none"),
    "stick_long": ItemConfig(type="stick_long", poids=0.8, porte_lance=6.0, degats=1.5, effect="none"),
    "sharp_rock": ItemConfig(type="sharp_rock", poids=0.4, porte_lance=12.0, degats=2.0, effect="cut"),
    "sparks": ItemConfig(type="sparks", poids=0.0, porte_lance=0.0, degats=0.0, effect="fire"),
    "axe": ItemConfig(type="axe", poids=0.7, porte_lance=5.0, degats=4.0, effect="chop"),
    "spear": ItemConfig(type="spear", poids=1.0, porte_lance=20.0, degats=6.0, effect="pierce"),
    "bag_small": ItemConfig(type="bag_small", poids=0.6, porte_lance=2.0, degats=0.0, effect="storage_5"),
    "bag_medium": ItemConfig(type="bag_medium", poids=1.0, porte_lance=1.0, degats=0.0, effect="storage_7"),
    "bag_large": ItemConfig(type="bag_large", poids=1.5, porte_lance=0.5, degats=0.0, effect="storage_10"),
    "tree_log": ItemConfig(type="tree_log", poids=5.0, porte_lance=1.0, degats=10.0, effect="none"),
    "planks": ItemConfig(type="planks", poids=1.0, porte_lance=2.0, degats=1.0, effect="none"),
    "chest": ItemConfig(type="chest", poids=10.0, porte_lance=0.0, degats=0.0, effect="storage_20_immobile"),
    "lock": ItemConfig(type="lock", poids=0.2, porte_lance=5.0, degats=1.0, effect="lock_chest"),
}

# Blueprints mapping tuples of ingredients to a result item type
# (Keys will be pre-sorted dynamically to ensure order-independence)
_RAW_BLUEPRINTS: Dict[Tuple[str, ...], str] = {
    ("rock_small", "rock_small"): "sharp_rock",
    ("rock_small", "rock_medium"): "sparks",
    ("sharp_rock", "stick_short"): "axe",
    ("stick_short", "stick_short"): "bag_small",
    ("bag_small", "stick_long"): "bag_medium",
    ("bag_medium", "rock_small", "stick_long"): "bag_large",
    ("axe", "tree_log"): "planks",
    ("planks", "planks", "planks"): "chest",
    ("sharp_rock", "sharp_rock"): "lock",
    ("stick_long", "stick_long", "rock_medium"): "spear",
}

# Pre-sort blueprints keys to ensure order-independence
BLUEPRINTS: Dict[Tuple[str, ...], str] = {
    tuple(sorted(ingredients)): result
    for ingredients, result in _RAW_BLUEPRINTS.items()
}

def attempt_combine(inventory_items: List[str]) -> Optional[str]:
    """
    Attempts to combine a list of items into a new item based on blueprints.
    
    Args:
        inventory_items: List of item types (e.g., ["rock_small", "rock_medium"])
        
    Returns:
        The resulting item type if a blueprint matches, else None.
    """
    if not inventory_items:
        return None
        
    sorted_items = tuple(sorted(inventory_items))
    return BLUEPRINTS.get(sorted_items)
