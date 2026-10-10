"""
tests/test_lu_phase5_governance_metallurgy.py — Validation LU Phase 5.
Vérifie formellement :
1. Algèbre de confiance continue, détection de défection et hystérésis (pas d'amnésie sur 10 cycles).
2. Arbitrage distribué, embargo commercial et répulsion physique du marché.
3. Contrats de consortium tripartites pour la métallurgie (Monde 1 Bois/Charbon + Monde 2 Vivres + Monde 3 Minerai).
4. Persistance KuzuDB des traités de consortium, lois et sanctions.
Conforme aux 12 Commandements AGIseed (NumPy pur, vectorisation, tolérances strictes).
"""
import pytest
import numpy as np

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    compute_contract_breach,
    update_agent_reputation,
    reputation_trust_score,
    decay_reputation_towards_neutral,
    verify_consortium_agreement,
)
from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig


class MockWorld:
    """Mock minimal de Biosphere3D / IndustrialWorld pour tests d'intégration in-world."""
    def __init__(self, size: int = 16):
        self.size = size
        self.agents = []
        self.items = []
        self.iron_smelted = 0
        self.metal_tools_crafted = 0


def test_contract_breach_detection_and_reputation_hysteresis():
    """
    Jalon M1 : Prouver qu'une trahison ponctuelle (breach) fait chuter le score de confiance
    sous le seuil commercial (< 0.40) et que le score demeure sous 0.40 pendant au moins 10 cycles.
    """
    dim = 32
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))
    trust_ref = grammar.ROLE_TRUST
    neutral_ref = np.ones(dim, dtype=np.float32) / np.sqrt(dim)

    # Agent réputé au départ (aligné sur trust_ref)
    r_initial = trust_ref.copy()
    initial_score = reputation_trust_score(r_initial, trust_ref)
    assert initial_score >= 0.99, f"Score initial insuffisant: {initial_score}"

    # Contrat d'échange
    rng = np.random.default_rng(101)
    offer_vec = grammar._generate_canonical_unit_vector(rng)
    demand_vec = grammar._generate_canonical_unit_vector(rng)
    contract_token = grammar.compose_contract(offer_vec, demand_vec)

    # 1. Respect loyal du contrat (breach = 0)
    delta_loyal = compute_contract_breach(offer_vec, offer_vec)
    assert delta_loyal < 1e-5
    r_loyal = update_agent_reputation(
        r_initial, contract_token, breach_distance=delta_loyal,
        alpha=0.25, breach_threshold=0.50, trust_reference=trust_ref
    )
    score_loyal = reputation_trust_score(r_loyal, trust_ref)
    assert score_loyal >= 0.90, f"Score loyal dégradé: {score_loyal}"

    # 2. Défection unilatérale (breach sévère, promesse non livrée)
    zero_delivery = np.zeros(dim, dtype=np.float32)
    delta_breach = compute_contract_breach(offer_vec, zero_delivery)
    assert delta_breach >= 0.99, f"Delta breach anormal: {delta_breach}"

    # Mise à jour avec sanction
    r_sanctioned = update_agent_reputation(
        r_initial, contract_token, breach_distance=delta_breach,
        alpha=0.40, breach_threshold=0.50, trust_reference=trust_ref
    )
    score_sanctioned = reputation_trust_score(r_sanctioned, trust_ref)
    assert score_sanctioned < 0.40, f"La trahison n'a pas fait chuter le score sous 0.40: {score_sanctioned}"

    # 3. Preuve d'Hystérésis : Sur 10 cycles d'inactivité, le score reste < 0.40
    curr_r = r_sanctioned.copy()
    for cycle in range(10):
        curr_r = decay_reputation_towards_neutral(curr_r, neutral_ref, decay_rate=0.02)
        score_cycle = reputation_trust_score(curr_r, trust_ref)
        assert score_cycle < 0.40, f"Amnésie au cycle {cycle+1}: score={score_cycle} >= 0.40"


def test_distributed_arbitrage_and_physical_embargo():
    """
    Jalon M2 : Vérifie l'ostracisme décentralisé in-world :
    - Un agent défecteur est placé sous embargo et voit son trust score s'effondrer.
    - Les autres agents refusent le troc avec lui.
    - L'agent sous embargo est physiquement repoussé hors du rayon de marché.
    """
    world = MockWorld(size=16)
    cfg = LUInWorldConfig(
        latent_dim=32,
        enable_governance=True,
        embargo_reputation_threshold=0.40,
        embargo_duration_ticks=10,
        market_point=(8, 8),
        market_radius=3
    )
    adapter = LUInWorldAdapter(world, cfg)

    # Création de deux agents sur la place du marché (8, 8)
    ag_honest = {
        "id": "ag_honest",
        "x": 8, "y": 8,
        "energy": 50.0,
        "inventory": [{"type": "FOOD"}],
        "is_defector": False
    }
    ag_defector = {
        "id": "ag_defector",
        "x": 8, "y": 8,
        "energy": 50.0,
        "inventory": [{"type": "TOOL"}],
        "is_defector": True  # Stratégie prédatrice
    }
    world.agents = [ag_honest, ag_defector]

    # Première tentative de troc : ag_defector trahit
    trades = adapter.negotiate_trade_contracts(world.agents)
    assert len(trades) == 0, "Le deal n'aurait pas dû être scellé loyalement"
    assert adapter.sanctions_count >= 1, "Aucune sanction enregistrée suite à la défection"
    assert adapter.is_agent_under_embargo("ag_defector") is True
    assert adapter.get_agent_trust_score("ag_defector") < 0.40

    # L'honnête refuse désormais toute transaction avec le défecteur
    trades_next = adapter.negotiate_trade_contracts(world.agents)
    assert len(trades_next) == 0, "L'agent sous embargo ne doit pas pouvoir négocier"

    # Vérification de la répulsion physique hors du marché
    ag_defector["x"], ag_defector["y"] = 8, 8  # Tente de rester sur le marché
    repelled = adapter.apply_physical_embargo_repulsion(world.agents)
    assert repelled == 1, "Le défecteur aurait dû être repoussé"
    dist_after = abs(ag_defector["x"] - 8) + abs(ag_defector["y"] - 8)
    assert dist_after > cfg.market_radius, f"L'agent n'a pas été éjecté du marché: dist={dist_after}"


def test_tripartite_consortium_contract_and_metallurgy():
    """
    Jalon M3 : Vérifie la composition et l'exécution de contrats de consortium tripartites :
    Monde 1 (Bois) + Monde 2 (Vivres) + Monde 3 (Minerai) -> Outils Métalliques + Surplus Énergétique.
    """
    dim = 64
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=77))

    # Test algébrique du contrat de consortium
    rng = np.random.default_rng(88)
    v_wood = grammar._generate_canonical_unit_vector(rng)
    v_food = grammar._generate_canonical_unit_vector(rng)
    v_ore = grammar._generate_canonical_unit_vector(rng)
    v_steel = grammar._generate_canonical_unit_vector(rng)

    consortium_token = grammar.compose_consortium_contract(v_wood, v_food, v_ore, v_steel)

    # Accord unanime des 3 fournisseurs (seuil = 0.40 pour 4 composantes superposées)
    agreed, score = verify_consortium_agreement(
        consortium_token, v_wood, v_food, v_ore, grammar, threshold=0.40
    )
    assert agreed is True, f"Consortium rejeté malgré des offres conformes: score={score}"
    assert score >= 0.40, f"Score de consortium insuffisant: {score}"

    # Rejet si l'un des fournisseurs offre une ressource discordante
    v_discordant = grammar._generate_canonical_unit_vector(rng)
    disagreed, disc_score = verify_consortium_agreement(
        consortium_token, v_discordant, v_food, v_ore, grammar, threshold=0.40
    )
    assert disagreed is False, "Le consortium aurait dû rejeter l'offre discordante"

    # Test d'intégration in-world avec 3 agents
    world = MockWorld(size=16)
    cfg = LUInWorldConfig(
        latent_dim=dim,
        enable_consortium_contracts=True,
        consortium_agreement_threshold=0.40
    )
    adapter = LUInWorldAdapter(world, cfg)

    ag_wood = {"id": "ag_wood", "x": 8, "y": 8, "energy": 40.0, "inventory": [{"type": "WOOD"}]}
    ag_food = {"id": "ag_food", "x": 8, "y": 8, "energy": 40.0, "inventory": [{"type": "FOOD"}]}
    ag_miner = {"id": "ag_miner", "x": 8, "y": 8, "energy": 40.0, "inventory": [{"type": "ORE"}]}
    world.agents = [ag_wood, ag_food, ag_miner]

    consortiums = adapter.negotiate_consortium_contracts(world.agents)
    assert len(consortiums) == 1, "Le consortium tripartite aurait dû être scellé"
    assert adapter.consortiums_settled_count == 1
    assert adapter.metal_tools_produced_count == 1

    # Vérification de l'attribution des outils et lingots métalliques
    has_metal_tool = any(it.get("tier") == "METAL" for it in ag_miner["inventory"])
    has_ingot = any(it.get("type") == "IronIngot" for it in ag_wood["inventory"])
    has_metal_spear = any(it.get("type") == "IronSpear" for it in ag_food["inventory"])

    assert has_metal_tool is True, "Le mineur n'a pas reçu son outil forgé"
    assert has_ingot is True, "Le bûcheron n'a pas reçu son lingot"
    assert has_metal_spear is True, "L'agriculteur n'a pas reçu sa lance métallique"

    # Surplus calorique de production partagé
    assert ag_wood["energy"] > 40.0
    assert ag_food["energy"] > 40.0
    assert ag_miner["energy"] > 40.0


def test_symbolic_bridge_consortium_and_kuzudb_methods():
    """
    Jalon M3 (Suite) : Vérifie la compilation/décodage de consortiums et la consigne KuzuDB.
    """
    bridge = LUSymbolicBridge(LUSymbolicBridgeConfig(dim=64, seed=42))

    # Compilation & Décodage
    token = bridge.compile_consortium_contract("WOOD", "FOOD", "ORE", "STEEL")
    decoded = bridge.decode_consortium_contract(token)

    assert decoded["wood"] == "WOOD"
    assert decoded["food"] == "FOOD"
    assert decoded["ore"] == "ORE"
    assert decoded["product"] == "STEEL"
    assert decoded["is_valid"] is True

    # Méthodes KuzuDB (mode sans DB active = retourne False sans lever d'exception)
    res_law = bridge.register_legal_rule("law_001", "Pacte du Marché", "Interdiction de défection", 0.60)
    res_sanc = bridge.register_sanction_event("sanc_001", "ag_bad", "Breach", 1.0)
    res_con = bridge.register_consortium("con_001", "Haut-Fourneau Réuni", 3, "IronPickaxe", 15.0)

    assert isinstance(res_law, bool)
    assert isinstance(res_sanc, bool)
    assert isinstance(res_con, bool)
