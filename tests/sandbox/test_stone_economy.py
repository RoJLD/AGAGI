"""Tests de l'économie de l'Âge de Pierre — monde exigeant (Step 2)."""
import math

import pytest

from src.environments.stone_economy import (
    prey_reward, weapon_damage, has_spear, can_craft_spear, anneal, approach_reward,
    is_craft_ingredient, state_signature, novelty_bonus,
)

# Physique réelle (config.py) : (weight, sharp, edible, friction, flammable)
ROCK = (1.0, 0.5, 0.0, 0.8, 0.0)
STICK = (0.5, 0.2, 0.0, 0.6, 1.0)
WOOD = (1.0, 0.5, 0.0, 0.6, 1.0)


def test_prey_reward_scales_with_difficulty():
    assert prey_reward(1.0) < prey_reward(3.0) < prey_reward(100.0)
    # Le Mammouth (hp 100) reste bien plus rentable qu'un petit gibier : gradient préservé.
    assert prey_reward(100.0) > 3 * prey_reward(1.0)


def test_small_prey_is_a_viable_meal():
    # Recalibrage C : un Lapin est un vrai repas (camp de base survivable),
    # mais loin du Mammouth -> on garde une raison de viser gros.
    assert 15.0 < prey_reward(1.0) < 40.0
    assert prey_reward(100.0) > 2.5 * prey_reward(1.0)


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


def test_state_signature_is_sorted_inventory():
    assert state_signature([]) == ()
    assert state_signature([{"type": "rock"}]) == ("rock",)
    # ordre indifferent -> meme signature (trie)
    assert state_signature([{"type": "stick"}, {"type": "rock"}]) == ("rock", "stick")
    assert state_signature([{"type": "rock"}, {"type": "stick"}]) == ("rock", "stick")
    assert state_signature(["Spear"]) == ("Spear",)


def test_novelty_bonus_decreases_with_frequency():
    # le precurseur du craft (vu 1 fois) recompense plus que l'inventaire vide (vu 1000 fois)
    assert novelty_bonus(1, 3.0) == pytest.approx(3.0)
    assert novelty_bonus(4, 3.0) == pytest.approx(1.5)
    assert novelty_bonus(1000, 3.0) < novelty_bonus(10, 3.0)
    assert novelty_bonus(0, 3.0) == 3.0  # garde-fou count=0


def test_is_craft_ingredient():
    assert is_craft_ingredient(ROCK)    # tranchant (sharp 0.5)
    assert is_craft_ingredient(STICK)   # manche (flammable 1.0)
    assert is_craft_ingredient(WOOD)
    assert not is_craft_ingredient((0.5, 0.0, 1.0, 0.1, 0.0))  # Fruit : ni l'un ni l'autre


def test_anneal_fades_over_eras():
    assert anneal(0, 30) == 1.0
    assert 0.9 < anneal(1, 30) < 1.0
    assert anneal(15, 30) == pytest.approx(0.5)
    assert anneal(30, 30) == 0.0
    assert anneal(40, 30) == 0.0          # clampe a 0, jamais negatif
    assert anneal(5, 0) == 0.0            # garde-fou n_eras=0


def test_approach_reward_only_when_closer_and_annealed():
    # se rapprocher (5 -> 3) tot dans le dev -> bonus ; lam=anneal(1,30)
    lam = anneal(1, 30)
    assert approach_reward(5.0, 3.0, eps=0.5, lam=lam) == pytest.approx(0.5 * lam)
    # s'eloigner ou stagner -> rien
    assert approach_reward(3.0, 5.0, eps=0.5, lam=lam) == 0.0
    assert approach_reward(4.0, 4.0, eps=0.5, lam=lam) == 0.0
    # une fois annele (lam=0), le scaffold a disparu meme en se rapprochant
    assert approach_reward(5.0, 3.0, eps=0.5, lam=0.0) == 0.0


def test_spear_recipe_does_not_collide_with_spark():
    # rock+rock : pas de lance, mais friction product 0.64 > 0.5 -> Spark (feu).
    assert not can_craft_spear(ROCK, ROCK)
    assert ROCK[3] * ROCK[3] > 0.5
    # rock+stick : lance, et friction product 0.48 < 0.5 -> pas de Spark. Séparés.
    assert can_craft_spear(ROCK, STICK)
    assert ROCK[3] * STICK[3] < 0.5
