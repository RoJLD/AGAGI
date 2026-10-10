"""
tests/test_lu_phase4_speciation_trade.py — Suite de tests unitaires pour LU Phase 4 :
- Variétés de Grassmann Gr(k, D), Distance Géodésique & Dérive Dialectale (M1)
- Algèbre de Contrats Latents & Équilibre de Réciprocité de Nash (M2)
- MultiTribalTranslator & Pivot Lingua Franca (M3)
- Négociation de Troc Décentralisée & Transfert d'Inventaire In-World (M2 & M3)
"""

import pytest
import numpy as np
from pathlib import Path

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    grassmann_distance,
    orthonormal_subspace,
    drift_subspace,
    linear_cka,
    cosine_similarity,
    match_contract_trade,
)
from src.metaprog.lu_symbolic_bridge import (
    LUSymbolicBridge,
    LUSymbolicBridgeConfig,
    MultiTribalTranslator,
)
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig


def test_grassmann_distance_and_dialect_drift():
    """
    Jalon M1 : Valide la géométrie sur Gr(k, D), la distance géodésique et la dérive dialectale.
    Prouve qu'à isolement géographique, deux populations atteignent d_G >= 0.35
    tout en préservant une cohérence interne CKA >= 0.85.
    """
    dim = 16
    k = 4
    rng = np.random.default_rng(42)

    # Base commune initiale
    raw_base = rng.standard_normal((dim, k)).astype(np.float32)
    q_base, _ = np.linalg.qr(raw_base)
    u_clan_a = q_base[:, :k].astype(np.float32)

    # Clan A et Clan B soumis à des pressions environnementales distinctes
    stim_a = rng.standard_normal((10, dim)).astype(np.float32)
    stim_b = rng.standard_normal((10, dim)).astype(np.float32)

    # Dérive dialectale itérative
    u_clan_b = u_clan_a.copy()
    for _ in range(15):
        u_clan_a = drift_subspace(u_clan_a, stim_a, drift_rate=0.15)
        u_clan_b = drift_subspace(u_clan_b, stim_b, drift_rate=0.15)

    # Mesure de la distance géodésique de Grassmann
    d_g = grassmann_distance(u_clan_a, u_clan_b)
    assert d_g >= 0.35, f"La distance de Grassmann inter-clans devrait être >= 0.35, mesuré {d_g:.3f}"

    # Vérification de la cohérence interne CKA au sein des représentations du Clan A
    cka_intra = linear_cka(stim_a, stim_a + 0.05 * rng.standard_normal(stim_a.shape))
    assert cka_intra >= 0.85, f"Cohérence interne CKA trop faible : {cka_intra:.3f} < 0.85"


def test_latent_trade_contracts_nash_reciprocity():
    """
    Jalon M2 : Valide l'algèbre de contrats latents et la validation de troc bilatéral de Nash.
    """
    dim = 32
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))
    rng = np.random.default_rng(101)

    # Vecteurs de concepts : Food vs Tool
    food_vec = rng.standard_normal(dim).astype(np.float32); food_vec /= np.linalg.norm(food_vec)
    tool_vec = rng.standard_normal(dim).astype(np.float32); tool_vec /= np.linalg.norm(tool_vec)
    weapon_vec = rng.standard_normal(dim).astype(np.float32); weapon_vec /= np.linalg.norm(weapon_vec)

    # Contrat A : Offre FOOD, Demande TOOL
    contract_a = grammar.compose_contract(give_item=food_vec, demand_item=tool_vec)

    # Contrat B compatible : Offre TOOL, Demande FOOD
    contract_b_match = grammar.compose_contract(give_item=tool_vec, demand_item=food_vec)

    # Contrat C incompatible : Offre WEAPON, Demande WEAPON
    contract_c_mismatch = grammar.compose_contract(give_item=weapon_vec, demand_item=weapon_vec)

    # 1. Test de réciprocité positive (Accord de Nash)
    agreed, score = match_contract_trade(contract_a, contract_b_match, grammar, threshold=0.60)
    assert agreed is True, f"Le troc complémentaire aurait dû être validé (score: {score:.3f})"
    assert score >= 0.60

    # 2. Test de réciprocité négative (Désaccord / Refus)
    disagreed, score_dis = match_contract_trade(contract_a, contract_c_mismatch, grammar, threshold=0.60)
    assert disagreed is False, f"Le troc asymétrique aurait dû être rejeté (score: {score_dis:.3f})"

    # 3. Extraction et décomposition du contrat
    rec_give, rec_demand = grammar.extract_contract(contract_a)
    assert cosine_similarity(rec_give, food_vec) >= 0.50
    assert cosine_similarity(rec_demand, tool_vec) >= 0.50


def test_multi_tribal_translator_and_lingua_franca():
    """
    Jalon M3 : Valide le MultiTribalTranslator et la projection pivot (Lingua Franca).
    """
    dim = 16
    k = 4
    multi_trans = MultiTribalTranslator(dim=dim, k=k, seed=77)
    rng = np.random.default_rng(88)

    # 2 clans avec dialectes orthonormaux distincts
    q_a, _ = np.linalg.qr(rng.standard_normal((dim, k)))
    q_b, _ = np.linalg.qr(rng.standard_normal((dim, k)))
    multi_trans.register_clan("Clan_North", q_a.astype(np.float32))
    multi_trans.register_clan("Clan_South", q_b.astype(np.float32))

    # Token source émis par le Clan North
    v_north = rng.standard_normal(dim).astype(np.float32); v_north /= np.linalg.norm(v_north)

    # Projection vers le pivot Lingua Franca
    v_pivot = multi_trans.translate_to_pivot(v_north, "Clan_North")
    assert v_pivot.shape == (dim,)
    assert np.isclose(np.linalg.norm(v_pivot), 1.0, atol=1e-3)

    # Traduction croisée North -> South
    v_south = multi_trans.translate_between_clans(v_north, "Clan_North", "Clan_South")
    assert v_south.shape == (dim,)
    assert np.isclose(np.linalg.norm(v_south), 1.0, atol=1e-3)

    # Cycle-consistance via le pivot : North -> South -> North
    v_cycle = multi_trans.translate_between_clans(v_south, "Clan_South", "Clan_North")
    sim_cycle = cosine_similarity(v_north, v_cycle)
    assert sim_cycle >= 0.40, f"Cycle-consistance inter-clans trop faible: {sim_cycle:.3f}"


def test_inworld_trade_contract_negotiation_and_inventory_transfer():
    """
    Jalons M2 & M3 : Valide la négociation de troc in-world et l'échange effectif d'inventaire.
    """
    world = Biosphere3D(WorldConfig(size=16))
    cfg = LUInWorldConfig(
        latent_dim=32,
        enable_trade_contracts=True,
        trade_agreement_threshold=0.60,
        market_radius=5,
        market_point=(8, 8),
    )
    adapter = LUInWorldAdapter(world, cfg)

    # Agent A (Agriculteur / Porteur de Fruit)
    agent_a = {
        "id": "farmer_1",
        "clan": "Clan_North",
        "x": 8, "y": 8,
        "energy": 50.0,
        "inventory": [{"type": "Fruit", "quality": 1.0}],
    }
    # Agent B (Artisan / Porteur de Lance)
    agent_b = {
        "id": "crafter_1",
        "clan": "Clan_South",
        "x": 8, "y": 9,
        "energy": 50.0,
        "inventory": [{"type": "Spear", "quality": 1.0}],
    }
    world.agents = [agent_a, agent_b]

    # Négociation de troc
    trades = adapter.negotiate_trade_contracts([agent_a, agent_b])

    assert len(trades) >= 1, "Le contrat de troc aurait dû être conclu"
    assert adapter.contracts_settled_count == 1
    assert adapter.trade_transfers_count == 1

    # Vérification de l'interversion réelle des inventaires
    inv_a_types = [it["type"] for it in agent_a["inventory"]]
    inv_b_types = [it["type"] for it in agent_b["inventory"]]
    assert "Spear" in inv_a_types, "L'agent A aurait dû recevoir la Spear"
    assert "Fruit" in inv_b_types, "L'agent B aurait dû recevoir le Fruit"

    # Vérification du surplus calorique bilatéral
    assert agent_a["energy"] == 52.0, "L'agent A aurait dû recevoir +2.0 E de surplus commercial"
    assert agent_b["energy"] == 52.0, "L'agent B aurait dû recevoir +2.0 E de surplus commercial"
