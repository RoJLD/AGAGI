"""
tests/test_lu_compositional_and_multihop.py — Validation LU Phase 2.
Vérifie :
1. Algèbre compositionnelle (Binding / Unbinding HRR, similarité cosinus > 0.85).
2. Décomposition de phrases vectorielles structurées.
3. Propagation multi-hop et consensus acoustique.
4. Pont symbolique KuzuDB / LangGraph.
"""

import pytest
import numpy as np

from src.metaprog.lu_algebra import (
    LUAlgebraConfig,
    LUCompositionalGrammar,
    circular_convolution,
    circular_correlation,
    bundle_vectors,
    cosine_similarity,
)


def test_circular_convolution_and_correlation_fidelity():
    """Valide que circular_correlation(circular_convolution(A, B), A) ~= B."""
    rng = np.random.default_rng(123)
    dim = 64
    a = rng.normal(0, 1, dim).astype(np.float32)
    a /= np.linalg.norm(a)

    b = rng.normal(0, 1, dim).astype(np.float32)
    b /= np.linalg.norm(b)

    # Binding
    c = circular_convolution(a, b)
    assert c.shape == (dim,)
    assert np.isclose(np.linalg.norm(c), 1.0, atol=1e-3)

    # Le vecteur lié est quasi-orthogonal à ses opérandes (propriété HRR fondamentale)
    assert abs(cosine_similarity(c, a)) < 0.40
    assert abs(cosine_similarity(c, b)) < 0.40

    # Dé-binding : recouvrir b depuis c et a
    b_recovered = circular_correlation(c, a)
    sim = cosine_similarity(b_recovered, b)
    assert sim > 0.90, f"La fidélité de dé-binding HRR doit dépasser 0.90 (obtenu: {sim:.4f})"


def test_compositional_grammar_message_structuring():
    """Valide l'extraction de rôles (Sujet, Prédicat, Cible) depuis une phrase composite."""
    cfg = LUAlgebraConfig(dim=64, seed=42)
    grammar = LUCompositionalGrammar(cfg)
    rng = np.random.default_rng(999)

    # Lexèmes
    concept_hunter = rng.normal(0, 1, 64).astype(np.float32)
    concept_hunter /= np.linalg.norm(concept_hunter)

    concept_gather = rng.normal(0, 1, 64).astype(np.float32)
    concept_gather /= np.linalg.norm(concept_gather)

    concept_fruit = rng.normal(0, 1, 64).astype(np.float32)
    concept_fruit /= np.linalg.norm(concept_fruit)

    # Message composé : "HUNTER GATHER FRUIT"
    msg = grammar.compose(
        subject=concept_hunter,
        predicate=concept_gather,
        target=concept_fruit,
    )
    assert msg.shape == (64,)
    assert np.isclose(np.linalg.norm(msg), 1.0, atol=1e-3)

    # Extraction des rôles
    recovered_subj = grammar.extract_subject(msg)
    recovered_pred = grammar.extract_predicate(msg)
    recovered_tgt = grammar.extract_target(msg)

    sim_subj = cosine_similarity(recovered_subj, concept_hunter)
    sim_pred = cosine_similarity(recovered_pred, concept_gather)
    sim_tgt = cosine_similarity(recovered_tgt, concept_fruit)

    # Dans un bundle à 3 composantes, les signaux émergent au-dessus du bruit aléatoire
    assert sim_subj > 0.25, f"Signal sujet attendu saillant: {sim_subj}"
    assert sim_pred > 0.25, f"Signal prédicat attendu saillant: {sim_pred}"
    assert sim_tgt > 0.15, f"Signal cible attendu saillant: {sim_tgt}"

    # Contraste : un concept non présent donne une similarité moyenne quasi-nulle
    random_sims = [
        abs(cosine_similarity(recovered_subj, rng.normal(0, 1, 64)))
        for _ in range(10)
    ]
    mean_noise = float(np.mean(random_sims))
    assert mean_noise < 0.15
    assert sim_subj > mean_noise * 2.0


def test_multi_hop_acoustic_relay_inworld():
    """Valide que la propagation acoustique multi-hop transmet l'alerte à un agent hors de vue directe."""
    from src.environments.config import WorldConfig
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
    from src.agents.mamba_agent import MambaAgent

    world = Biosphere3D(WorldConfig(size=20))
    adapter = LUInWorldAdapter(world, LUInWorldConfig(
        hear_radius=3,
        enable_multi_hop=True,
        relay_decay=0.8,
        pack_coordination=True,
        alignment_threshold=-1.0,
        warmstart_spectral=True
    ))

    # Trois agents en chaîne : A(2, 2) -> B(4, 2) [dist=2 <= 3] -> C(6, 2) [dist=2 <= 3, mais dist(A, C)=4 > 3]
    agent_a = world.add_agent(MambaAgent(), x=2, y=2, energy=80.0)
    agent_b = world.add_agent(MambaAgent(), x=4, y=2, energy=80.0)
    agent_c = world.add_agent(MambaAgent(), x=6, y=2, energy=80.0)

    # Proie proche de A (x=0, y=2) pour créer un fort biais directionnel saillant (dx = -0.2)
    world.preys.append({"x": 0, "y": 2, "hp": 1.0, "type": "Mammouth"})

    # Step de communication continue
    metrics = adapter.step()

    # B a reçu directement de A
    assert "lu_steer_bias" in agent_b
    # C doit avoir reçu le relais acoustique multi-hop depuis B (alors que dist(A, C)=4 > hear_radius=3)
    assert agent_c.get("lu_multi_hop_relayed", False) is True
    assert "lu_steer_bias" in agent_c
    assert metrics["multi_hop_relays"] >= 1


def test_symbolic_bridge_top_down_and_bottom_up():
    """Valide la compilation descendante d'une consigne et le décodage ascendant (Jalon M3)."""
    from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig

    cfg = LUSymbolicBridgeConfig(dim=64, similarity_match_threshold=0.20, seed=42)
    bridge = LUSymbolicBridge(cfg)

    # 1. Compilation descendante : "HUNTER HUNT PREY" -> Gigatoken composite
    token = bridge.compile_directive_to_gigatoken("HUNTER HUNT PREY")
    assert token.shape == (64,)
    assert np.isclose(np.linalg.norm(token), 1.0, atol=1e-3)

    # 2. Décompilation ascendante
    decoded = bridge.decode_gigatoken_to_symbolic(token)
    assert decoded["subject"] == "HUNTER"
    assert decoded["predicate"] == "HUNT"
    assert decoded["target"] == "PREY"
    assert decoded["scores"]["subject_sim"] > 0.20
    assert decoded["scores"]["predicate_sim"] > 0.20

    # 3. Enregistrement d'un lexème émergent
    new_vec = np.random.randn(64).astype(np.float32)
    lex_id = bridge.register_emergent_lexeme("NEW_TOOL", "TARGET", new_vec)
    assert "NEW_TOOL" in bridge.lexicon
    assert bridge.lexicon["NEW_TOOL"]["category"] == "TARGET"

