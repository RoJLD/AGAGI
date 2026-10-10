"""
tests/test_lu_phase6_writing_arithmetic_science.py — Validation du Langage Ultime (LU Phase 6).

Piliers validés :
1. Algèbre d'Arithmétique Vectorielle FPE : Z(a) ⊛ Z(b) = Z(a+b), ratio stœchiométrique.
2. Inscriptions Stigmargiques & Substrats Physiques : InscriptionStone, SlateTablet, demi-vie géologique.
3. Académie Scientifique & Transmission Épigénétique : Prior boost intergénérationnel.
4. Comptabilité de Marché sur Tablettes : Auditabilité des dettes et créances.
"""

import pytest
import numpy as np
from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    encode_fractional_power_number,
    decode_fractional_power_number,
    decay_inscription_geological,
    validate_recipe_ratio,
    cosine_similarity,
    circular_convolution,
)
from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
    InscriptionStone,
    SlateTablet,
)


class MockWorld:
    """Mock minimal de Biosphere3D pour valider la communication in-world."""
    def __init__(self, num_agents: int = 6):
        self.tick = 1
        self.size = 16
        self.iron_smelted = 0
        self.metal_tools_crafted = 0
        self.agents = []
        for i in range(num_agents):
            self.agents.append({
                "id": f"ag_{i}",
                "x": 8.0 + (i % 2) * 1.0,
                "y": 8.0 + (i // 2) * 1.0,
                "energy": 25.0,
                "age": 5,
                "inventory": [],
            })


def test_fpe_arithmetic_binding_and_addition():
    """
    Vérifie la propriété d'addition spectrale FPE :
    Z_num(a) ⊛ Z_num(b) = Z_num(a + b).
    """
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=16, seed=42))

    z0 = grammar.encode_number(0.0)
    z1 = grammar.encode_number(1.0)
    z2 = grammar.encode_number(2.0)
    z3 = grammar.encode_number(3.0)
    z5 = grammar.encode_number(5.0)

    # 1. Neutralité de 0 : z0 ⊛ z2 ≈ z2
    conv_0_2 = circular_convolution(z0, z2)
    sim_0_2 = float(cosine_similarity(conv_0_2, z2))
    assert sim_0_2 > 0.98, f"Identité FPE échouée : sim={sim_0_2}"

    # 2. Addition par convolution : z2 ⊛ z3 ≈ z5
    conv_2_3 = circular_convolution(z2, z3)
    sim_add = float(cosine_similarity(conv_2_3, z5))
    assert sim_add > 0.95, f"Addition FPE 2+3=5 échouée : sim={sim_add}"

    # 3. Décodage du nombre 5
    best_k, conf = grammar.decode_number(conv_2_3, max_n=10)
    assert best_k == 5, f"Décodage nombre attendu 5, obtenu {best_k} (conf={conf})"
    assert conf > 0.95


def test_quantified_item_and_recipe_ratio():
    """
    Vérifie la liaison item-quantité et la validation d'une recette ou équation stœchiométrique.
    Ex: 3 Wood + 1 Ore -> 1 IronPickaxe.
    """
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=16, seed=42))

    rng_w = np.random.default_rng(101)
    v_wood = grammar._generate_canonical_unit_vector(rng_w)

    rng_o = np.random.default_rng(202)
    v_ore = grammar._generate_canonical_unit_vector(rng_o)

    rng_p = np.random.default_rng(303)
    v_pickaxe = grammar._generate_canonical_unit_vector(rng_p)

    # Liaison quantité : 3 Wood
    quant_wood = grammar.encode_quantified_item(3.0, v_wood)
    decoded_q, q_conf = grammar.extract_quantified_item(quant_wood, v_wood, max_n=5)
    assert decoded_q == 3, f"Quantité attendue 3, obtenue {decoded_q}"
    assert q_conf > 0.85

    # Composition de recette complète
    recipe = grammar.compose_recipe_ratio(
        inputs=[(3.0, v_wood), (1.0, v_ore)],
        outputs=[(1.0, v_pickaxe)]
    )

    # Validation d'une proposition conforme
    in_offer = grammar.encode_quantified_item(3.0, v_wood)
    out_demand = grammar.encode_quantified_item(1.0, v_pickaxe)

    agreed, score = validate_recipe_ratio(recipe, in_offer, out_demand, grammar, threshold=0.25)
    assert agreed, f"Recette valide rejetée : score={score}"


def test_stigmergy_inscription_stele_and_geological_decay():
    """
    Vérifie la gravure d'une inscription sur stèle, son décodage sémantique
    et sa résistance à la lente érosion géologique.
    """
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=16, seed=42))

    rng_t = np.random.default_rng(404)
    v_topic = grammar._generate_canonical_unit_vector(rng_t)

    rng_c = np.random.default_rng(505)
    v_content = grammar._generate_canonical_unit_vector(rng_c)

    inscription = grammar.compose_inscription(v_topic, v_content)

    # Extraction exacte
    rec_topic = grammar.extract_inscription_topic(inscription)
    rec_content = grammar.extract_inscription_content(inscription)

    sim_t = float(cosine_similarity(rec_topic, v_topic))
    sim_c = float(cosine_similarity(rec_content, v_content))
    assert sim_t > 0.40, f"Extraction topic échouée : {sim_t}"
    assert sim_c > 0.40, f"Extraction content échouée : {sim_c}"

    # Érosion géologique sur 200 ticks
    eroded = inscription.copy()
    for _ in range(200):
        eroded = decay_inscription_geological(eroded, noise_std=1e-4)

    sim_eroded = float(cosine_similarity(eroded, inscription))
    assert sim_eroded > 0.90, f"Stèle effacée trop rapidement par érosion : {sim_eroded}"


def test_inworld_stele_reading_and_epigenetic_transmission():
    """
    Vérifie l'Académie Scientifique in-world :
    Un agent nouveau-né lisant la stèle reçoit un boost calorique et un conditionnement de prior.
    """
    world = MockWorld(num_agents=4)
    adapter = LUInWorldAdapter(world, LUInWorldConfig(latent_dim=16, enable_writing=True))

    assert "stele_metallurgy_academy" in adapter.steles
    assert "stele_geology_map" in adapter.steles

    apprentice = world.agents[0]
    apprentice["x"] = 8.0
    apprentice["y"] = 8.0
    apprentice["age"] = 2
    apprentice["energy"] = 15.0

    stele = adapter.read_nearest_stele(apprentice, max_radius=3.0)
    assert stele is not None
    assert stele.id == "stele_metallurgy_academy"
    assert stele.read_count >= 1

    # Vérification de l'effet épigénétique
    assert apprentice.get("lu_prior_boosted") is True
    assert apprentice["energy"] >= 20.0, f"Boost calorique manquant : {apprentice['energy']}"
    assert adapter.epigenetic_boosts_count >= 1


def test_market_accounting_ledger_on_slate_tablets():
    """
    Vérifie la tenue du grand livre de comptes sur tablettes lors des échanges au marché.
    """
    world = MockWorld(num_agents=2)
    adapter = LUInWorldAdapter(world, LUInWorldConfig(latent_dim=16, enable_writing=True, enable_arithmetic=True))

    ag_a = world.agents[0]
    ag_b = world.agents[1]

    trade_record = {
        "party_a": ag_a["id"],
        "party_b": ag_b["id"],
        "give_a": "FOOD",
        "give_b": "TOOL",
        "agreement_score": 0.85,
    }

    adapter.record_market_transaction_to_ledger(trade_record)

    tab_a_id = f"market_ledger_{ag_a['id']}"
    tab_b_id = f"market_ledger_{ag_b['id']}"

    assert tab_a_id in adapter.tablets
    assert tab_b_id in adapter.tablets

    entries_a = adapter.tablets[tab_a_id].balance_entries
    assert len(entries_a) >= 1
    assert entries_a[0]["role"] == "CREDIT"
    assert entries_a[0]["partner"] == ag_b["id"]
