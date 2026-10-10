"""
tests/test_lu_phase3_recursive_tom.py — Suite de tests unitaires pour LU Phase 3 :
- Récursion Grammaticale & Emboîtement de clauses (HRR unitaire, M1)
- Théorie de l'Esprit Latente (ToM) & Économie d'Information (M2)
- Consensus Délibératif Distribué au Coin du Feu (M3)
- Pont Symbolique-Neuronal Récursif et Archivage KuzuDB (M3)
"""

import pytest
import numpy as np
from pathlib import Path

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    cosine_similarity,
    circular_convolution,
    circular_correlation,
    bundle_vectors,
)
from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.agents.mamba_agent import MambaAgent


def test_recursive_hierarchical_clause_binding_and_unbinding():
    """
    Jalon M1 : Valide l'emboîtement récursif à 2 niveaux (Proposition dans Proposition).
    Z_outer = bind(S_out, P_out, Z_inner) où Z_inner = bind(S_in, P_in, T_in).
    Exige une fidélité de déliage cyclique >= 0.40 en profondeur 2.
    """
    dim = 64
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))
    
    # Éléments de la sous-clause interne (ex: "PREY FLEES SHELTER")
    rng = np.random.default_rng(101)
    s_in = rng.standard_normal(dim).astype(np.float32); s_in /= np.linalg.norm(s_in)
    p_in = rng.standard_normal(dim).astype(np.float32); p_in /= np.linalg.norm(p_in)
    t_in = rng.standard_normal(dim).astype(np.float32); t_in /= np.linalg.norm(t_in)
    
    inner_prop = grammar.compose(s_in, p_in, t_in)
    
    # Éléments de la clause externe enveloppante (ex: "SCOUT INFORMS [clause]")
    s_out = rng.standard_normal(dim).astype(np.float32); s_out /= np.linalg.norm(s_out)
    p_out = rng.standard_normal(dim).astype(np.float32); p_out /= np.linalg.norm(p_out)
    
    composite_message = grammar.compose_hierarchical(
        outer_subject=s_out,
        outer_predicate=p_out,
        inner_proposition=inner_prop
    )
    
    # Décomposition et extraction à 2 niveaux
    rec_s_out, rec_p_out, rec_inner = grammar.extract_hierarchical(composite_message)
    
    # 1. Vérification niveau externe (profondeur 1)
    sim_s_out = cosine_similarity(s_out, rec_s_out)
    sim_p_out = cosine_similarity(p_out, rec_p_out)
    sim_inner = cosine_similarity(inner_prop, rec_inner)
    
    assert sim_s_out >= 0.40, f"Échec rappel sujet externe: {sim_s_out:.3f}"
    assert sim_p_out >= 0.35, f"Échec rappel prédicat externe: {sim_p_out:.3f}"
    assert sim_inner >= 0.50, f"Échec rappel sous-clause interne: {sim_inner:.3f}"
    
    # 2. Décomposition de la sous-clause interne (profondeur 2)
    rec_s_in = grammar.extract_subject(rec_inner)
    rec_p_in = grammar.extract_predicate(rec_inner)
    rec_t_in = grammar.extract_target(rec_inner)
    
    sim_s_in = cosine_similarity(s_in, rec_s_in)
    sim_p_in = cosine_similarity(p_in, rec_p_in)
    sim_t_in = cosine_similarity(t_in, rec_t_in)
    
    mean_depth2_recall = (sim_s_in + sim_p_in + sim_t_in) / 3.0
    assert mean_depth2_recall >= 0.40, f"Rappel moyen profondeur 2 trop faible: {mean_depth2_recall:.3f} < 0.40"


def test_symbolic_bridge_recursive_compilation_and_decoding():
    """
    Jalons M1 & M3 : Valide la compilation descendante et la décompilation ascendante récursive.
    """
    bridge = LUSymbolicBridge(LUSymbolicBridgeConfig(dim=32, seed=42))
    
    # Directive récursive top-down : "SCOUT INFORMS" englobant "HUNTER HUNT PREY"
    outer = "SCOUT INFORMS"
    inner = "HUNTER HUNT PREY"
    
    token = bridge.compile_recursive_directive(outer, inner)
    assert token.shape == (32,)
    assert np.isclose(np.linalg.norm(token), 1.0, atol=1e-3)
    
    # Décompilation ascendante bottom-up
    decoded = bridge.decode_recursive_gigatoken(token)
    
    assert "outer_subject" in decoded
    assert "outer_predicate" in decoded
    assert "inner_clause" in decoded
    assert decoded["outer_subject"] == "SCOUT"
    assert decoded["outer_predicate"] == "INFORMS"
    assert decoded["inner_clause"]["subject"] == "HUNTER"
    assert decoded["inner_clause"]["predicate"] == "HUNT"
    assert decoded["inner_clause"]["target"] == "PREY"


def test_tom_latent_belief_updating_and_pragmatic_silence():
    """
    Jalon M2 : Valide la Theory of Mind (ToM) et l'économie métabolique de silence pragmatique.
    """
    world = Biosphere3D(WorldConfig(size=16))
    cfg = LUInWorldConfig(
        latent_dim=16,
        hear_radius=3,
        enable_tom=True,
        tom_redundancy_threshold=0.80,
        tom_silence_metabolic_saving=0.04
    )
    adapter = LUInWorldAdapter(world, cfg)
    
    rng = np.random.default_rng(77)
    intention = rng.standard_normal(16).astype(np.float32); intention /= np.linalg.norm(intention)
    
    # 1. Avant mise à jour : croyance vierge -> pas de silence
    prag_vec, is_silent = adapter.evaluate_tom_emission("ag_1", "ag_2", intention)
    assert not is_silent
    assert np.isclose(np.linalg.norm(prag_vec), 1.0, atol=1e-3)
    
    # 2. Mise à jour de la croyance : ag_1 sait que ag_2 a déjà le même vecteur intention
    adapter.update_peer_belief("ag_1", "ag_2", intention, alpha=1.0)
    
    # 3. Évaluation post-mise à jour : l'information est redondante (overlap = 1.0 >= 0.80) -> SILENCE pragmatique
    prag_vec2, is_silent2 = adapter.evaluate_tom_emission("ag_1", "ag_2", intention)
    assert is_silent2, "ToM aurait dû décider le silence pragmatique pour éviter le spam redondant"


def test_campfire_deliberation_consensus():
    """
    Jalon M3 : Valide le protocole délibératif distribué en multi-tours au coin du feu.
    """
    world = Biosphere3D(WorldConfig(size=16))
    cfg = LUInWorldConfig(
        latent_dim=16,
        enable_deliberation=True,
        deliberation_rounds=3,
        deliberation_consensus_threshold=0.60
    )
    adapter = LUInWorldAdapter(world, cfg)
    
    # 4 agents autour du feu avec des vecteurs d'intention initiaux
    agents = []
    rng = np.random.default_rng(99)
    for i in range(4):
        v = rng.standard_normal(16).astype(np.float32); v /= np.linalg.norm(v)
        agents.append({
            "id": f"agent_{i}",
            "role": "SCOUT" if i == 0 else "HUNTER",
            "lu_latent": v,
            "energy": 50.0
        })
    
    res = adapter.deliberate_at_campfire(agents, rounds=3)
    
    assert res["deliberated"] is True
    assert res["agreement"] >= 0.60
    assert res["consensus"].shape == (16,)
    assert adapter.deliberation_consensus_count == 1
    
    # Tous les agents ont adopté le consensus délibéré
    for ag in agents:
        assert "lu_deliberated_consensus" in ag
        assert np.allclose(ag["lu_deliberated_consensus"], res["consensus"], atol=1e-4)
