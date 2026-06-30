import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_famine import FamineWorld, FOOD_VALUE


def _world(deterministic=True):
    w = Biosphere3D(WorldConfig())
    # neutralise la mémoire ambiante (repro) si présente
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    return w


def _fresh_model(world):
    from src.agents.mamba_agent import MambaAgent
    m = MambaAgent()
    return m


def test_food_regen_scale_default_is_one():
    w = _world()
    assert w.food_regen_scale == 1.0


def test_food_regen_scale_zero_freezes_food_spawn():
    w = _world()
    w.food_regen_scale = 0.0
    # force les arbres fruitiers à vouloir spawner ce tick
    for td in w.tree_data:
        if td.get("is_fruit"):
            td["cooldown"] = 0
    n_items_before = len(w.items)
    n_preys_before = len(w.preys)
    w.step()
    # aucune nouvelle nourriture (fruits) ; les proies ne regénèrent pas
    assert len(w.items) <= n_items_before
    assert len(w.preys) <= n_preys_before


def test_famine_phase_schedule():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cycle_abundance, w.cycle_famine = 5, 3
    # ticks 0..4 = abondance ; 5..7 = famine ; 8 = abondance
    phases = []
    for _ in range(9):
        phases.append(w.is_famine())
        w.ticks += 1
    assert phases == [False, False, False, False, False, True, True, True, False]


def test_famine_sets_food_regen_scale_zero():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cycle_abundance, w.cycle_famine = 2, 2
    w.ticks = 2          # entre en famine
    w.step()
    assert w.food_regen_scale == 0.0


def test_auto_consume_from_cache_when_starving():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cycle_abundance, w.cycle_famine = 0, 100   # famine permanente
    # un agent affamé portant un fruit en réserve
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["inventory"].append({"type": "Fruit", "weight": 0.5})
    e0 = a["energy"]
    w.step()
    # l'agent a auto-consommé son fruit -> énergie remontée (malgré le drain), cache vidé
    assert all(it.get("type") != "Fruit" for it in a["inventory"])
    assert a["energy"] > e0 - 5.0   # le gain FOOD_VALUE domine le drain du tick


def test_distinctness_non_storer_dies_storer_survives_famine():
    # Deux mondes identiques, famine longue. Le non-stockeur (cache vide) meurt ;
    # le stockeur (cache plein) survit nettement plus longtemps. PROUVE la distinctness.
    def survival(with_cache):
        w = FamineWorld(WorldConfig())
        if hasattr(w, "memory_retriever"):
            w.memory_retriever.stop()
        w.cycle_abundance, w.cycle_famine = 0, 300   # famine pure (pas de regen)
        w.add_agent(_fresh_model(w), energy=60.0)
        a = w.agents[0]
        if with_cache:
            for _ in range(10):
                a["inventory"].append({"type": "Fruit", "weight": 0.5})
        t = 0
        while w.agents and t < 300:
            w.step(); t += 1
        return t
    assert survival(with_cache=True) > survival(with_cache=False) + 20
