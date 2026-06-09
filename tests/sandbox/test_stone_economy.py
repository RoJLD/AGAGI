"""Tests de l'économie de l'Âge de Pierre — monde exigeant (Step 2)."""
import math

from src.environments.stone_economy import (
    prey_reward, weapon_damage, has_spear, can_craft_spear,
)

# Physique réelle (config.py) : (weight, sharp, edible, friction, flammable)
ROCK = (1.0, 0.5, 0.0, 0.8, 0.0)
STICK = (0.5, 0.2, 0.0, 0.6, 1.0)
WOOD = (1.0, 0.5, 0.0, 0.6, 1.0)


def test_prey_reward_scales_with_difficulty():
    assert prey_reward(1.0) < prey_reward(3.0) < prey_reward(100.0)
    # Le Mammouth (hp 100) doit valoir bien plus qu'un Lapin (hp 1).
    assert prey_reward(100.0) > 8 * prey_reward(1.0)


def test_small_prey_only_subsists():
    # Un Lapin (~7) couvre quelques ticks de drain (~1-2/tick), pas l'abondance.
    assert 5.0 < prey_reward(1.0) < 12.0


def test_weapon_damage_makes_mammoth_winnable_only_with_spear():
    assert weapon_damage(False) == 10.0
    assert weapon_damage(True) >= 50.0
    # Mammouth 100 HP : injouable à mains nues (>=10 coups, riposte mortelle),
    # faisable à la lance (<=2 coups).
    assert math.ceil(100.0 / weapon_damage(False)) >= 10
    assert math.ceil(100.0 / weapon_damage(True)) <= 2


def test_has_spear_detects_dict_and_str_items():
    assert has_spear([{"type": "Spear", "weight": 2.0}])
    assert has_spear(["Spear"])
    assert not has_spear([{"type": "rock"}, {"type": "stick"}])
    assert not has_spear([])


def test_can_craft_spear_requires_edge_and_haft():
    assert can_craft_spear(ROCK, STICK)     # tranchant (rock) + manche (stick)
    assert can_craft_spear(STICK, ROCK)     # ordre indifférent
    assert can_craft_spear(ROCK, WOOD)      # bois aussi flammable
    assert not can_craft_spear(ROCK, ROCK)  # deux rochers : pas de manche (flammable 0)
    assert not can_craft_spear(STICK, STICK)  # deux sticks : pas assez tranchant (0.2)


def test_spear_recipe_does_not_collide_with_spark():
    # rock+rock : pas de lance, mais friction product 0.64 > 0.5 -> Spark (feu).
    assert not can_craft_spear(ROCK, ROCK)
    assert ROCK[3] * ROCK[3] > 0.5
    # rock+stick : lance, et friction product 0.48 < 0.5 -> pas de Spark. Séparés.
    assert can_craft_spear(ROCK, STICK)
    assert ROCK[3] * STICK[3] < 0.5
