import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_famine import FamineWorld, FOOD_VALUE, SPOIL_RATE, MIN_FOOD_VALUE


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
    # Deux bras : famine permanente + nuit désactivée pour isoler le pur signal de stockage.
    # Le stockeur porte 8 fruits avec coûts RÉELS :
    #   (1) portage : 8 fruits × 0.5 kg × 0.5 drain/kg/tick = 2.0/tick supplémentaire
    #   (2) péremption : valeur FOOD_VALUE décroît de SPOIL_RATE/tick depuis le stockage
    # Le phénotype est normalisé à drain=1.0 (phenotype_energy_drain forcé) pour isoler le
    # signal de stockage d'un génome aléatoire pathologique (drain typique ~14 avec inv élevée).
    # Résultats mesurés sur base main (num_inputs=59) : sans cache ≈26 ticks, avec 8 fruits ≈36 ticks,
    # delta ≈10 > 5. PROUVE la distinctness HONNÊTE : le coût de portage est réel (+2/tick), la valeur
    # effective décroît avec l'âge, mais l'avantage de pouvoir consommer pendant la famine
    # l'emporte sur le coût.
    def survival(with_cache):
        np.random.seed(42)
        w = FamineWorld(WorldConfig())
        if hasattr(w, "memory_retriever"):
            w.memory_retriever.stop()
        # Nuit désactivée : isole la pression de pénurie cyclique (pas de thermodynamique
        # nocturne) pour un scénario de stockage pur. FamineWorld hérite la nuit mais
        # ce test la coupe pour mesurer uniquement le delta stockage. Les EDR vérifieront
        # l'interaction nuit+stockage.
        w.night_enabled = False
        w.cycle_abundance, w.cycle_famine = 0, 500   # famine pure (pas de regen)
        w.add_agent(_fresh_model(w), energy=60.0)
        a = w.agents[0]
        # Normaliser le phénotype : isole le signal stockage d'un génome aléatoire
        # dont drain ≈14 (inv_capacity ~67 × 0.1) rendrait les deux bras identiquement courts.
        a["model"].phenotype_energy_drain = 1.0
        if with_cache:
            for _ in range(8):
                a["inventory"].append({"type": "Fruit", "weight": 0.5})
        t = 0
        while w.agents and t < 500:
            w.step(); t += 1
        return t
    t_cache = survival(with_cache=True)
    t_nocache = survival(with_cache=False)
    # Le stockeur doit survivre plus longtemps que le non-stockeur (delta > 5 ticks).
    # Coûts réels : portage +2.0/tick, péremption, mais 8 recharges lors de la disette.
    # Seuil conservatif (> 5) calibré sur base main num_inputs=59 (delta mesuré ≈ 10).
    assert t_cache > t_nocache + 5, (
        f"Distinctness échouée : stockeur={t_cache} ticks, non-stockeur={t_nocache} ticks, "
        f"delta={t_cache - t_nocache} (attendu >5)"
    )


def test_famine_wired_into_factories():
    from main_curriculum import WORLD_FACTORY, DEFAULT_LADDER
    from tools.s2_demand import WORLDS as S2_WORLDS
    from src.worlds.world_famine import FamineWorld
    assert WORLD_FACTORY["famine"] is FamineWorld
    assert S2_WORLDS["famine"] is FamineWorld
    # non-régression
    assert DEFAULT_LADDER == ["stoneage", "agricultural", "industrial"]
    assert "stoneage" in WORLD_FACTORY


def test_famine_io_compat_with_champion_agent():
    from src.environments.config import WorldConfig
    from src.worlds.world_famine import FamineWorld
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.add_agent(_fresh_model(w), energy=80.0)
    w.step()   # ne crashe pas : obs/action hérités de stoneage
    assert True


def test_cache_enabled_false_disables_auto_consume():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cache_enabled = False
    w.cycle_abundance, w.cycle_famine = 0, 100   # famine permanente
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["inventory"].append({"type": "Fruit", "weight": 0.5})
    e0 = a["energy"]
    w.step()
    # cache OFF : le fruit n'est PAS consommé par le cache -> reste STOCKÉ. Robuste à la mort de
    # l'agent (drain RNG) : s'il survit, le fruit est démasqué ("Fruit") ; s'il meurt mid-step, il
    # reste masqué ("_FruitReserve", la boucle de démasquage n'itère que les vivants). Dans les deux
    # cas il n'est PAS consommé (cache OFF) -> toujours présent comme réserve.
    assert any(it.get("type") in ("Fruit", "_FruitReserve") for it in a["inventory"])
    assert a["energy"] <= e0    # aucune remontée d'énergie (cache off : drain seul, pas de FOOD_VALUE)


def test_cache_enabled_default_true_consumes():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    assert w.cache_enabled is True   # défaut non-régressif
    w.cycle_abundance, w.cycle_famine = 0, 100
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["inventory"].append({"type": "Fruit", "weight": 0.5})
    e0 = a["energy"]
    w.step()
    # cache ON (défaut) : fruit consommé, énergie remontée (comportement EDR-118)
    assert all(it.get("type") != "Fruit" for it in a["inventory"])
    assert a["energy"] > e0 - 5.0


def test_energy_bank_withdraws_from_reserve_in_famine():
    np.random.seed(42)
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cache_enabled = True
    w.cycle_abundance, w.cycle_famine = 0, 100   # famine permanente
    w.add_agent(_fresh_model(w), energy=10.0)    # affame (< starve_threshold 25)
    a = w.agents[0]
    a["reserve"] = 50.0
    r0 = a["reserve"]
    w.step()
    assert a.get("reserve", 0.0) < r0   # retrait de la reserve en famine quand affame


def test_energy_bank_no_withdraw_when_cache_off():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cache_enabled = False
    w.cycle_abundance, w.cycle_famine = 0, 100
    w.add_agent(_fresh_model(w), energy=10.0)
    a = w.agents[0]
    a["reserve"] = 50.0
    r0 = a["reserve"]
    w.step()
    assert a.get("reserve", 0.0) == r0   # cache OFF : aucun retrait (banque desactivee)


def test_energy_bank_stores_surplus_in_abundance():
    w = FamineWorld(WorldConfig())
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.cache_enabled = True
    w.cycle_abundance, w.cycle_famine = 100, 0   # abondance permanente
    w.add_agent(_fresh_model(w), energy=100.0)   # surplus > BANK_THRESHOLD 90
    a = w.agents[0]
    a["model"].phenotype_energy_drain = 0.0      # isole l'effet banque
    w.step()
    assert a.get("reserve", 0.0) > 0   # le surplus est banque en abondance
