"""
tests/test_lu_phase7_metagrammar_diplomacy.py — Suite de Tests pour LU Phase 7.
Valide :
1. Dérivation de macro-rôles d'ordre supérieur (RSI Grammatical).
2. Détection géométrique de contradiction vectorielle (Preuve formelle).
3. Pont diplomatique inter-connectomes asymétrique (D_A != D_B) et CKA.
4. Substrat in-world FederalMonument, ratification et rejet de contradiction.
5. Persistance Graph-RAG KuzuDB (LUMetaGrammar, LUProofCheck, LUFederalTreaty).
Conforme aux 12 Commandements AGIseed (3. NumPy vectorisé, 5. Traçabilité KuzuDB, 7. Test-Driven, 9. Stabilité).
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    derive_macro_role,
    verify_propositional_consistency,
    cosine_similarity,
    circular_convolution,
    circular_correlation,
)
from src.metaprog.lu_symbolic_bridge import (
    LUSymbolicBridge,
    LUSymbolicBridgeConfig,
    FederalDiplomaticBridge,
)
from src.environments.lu_inworld_adapter import (
    LUInWorldAdapter,
    LUInWorldConfig,
    FederalMonument,
)
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.graph_rag.database import KuzuDatabase, DatabaseConfig


def test_derive_macro_role_preserves_unit_spectrum():
    """
    Test 1 : Vérifie que la dérivation d'un macro-rôle unitaire via derive_macro_role
    génère un foncteur à spectre de Fourier plat |F(R)| = 1 sur S^{D-1}.
    """
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))
    role_a = grammar.ROLE_SUBJECT
    role_b = grammar.ROLE_TARGET

    macro_role = derive_macro_role(role_a, role_b)

    # 1. Vérification de la norme L2 sur S^{D-1}
    norm = float(np.linalg.norm(macro_role))
    assert abs(norm - 1.0) < 1e-4

    # 2. Vérification du spectre unitaire plat
    spectrum = np.abs(np.fft.fft(macro_role))
    expected_val = spectrum[0]
    # Toutes les composantes fréquentielles doivent avoir la même amplitude unitaire
    assert np.allclose(spectrum, expected_val, atol=1e-3)

    # 3. Déconvolution de test : binding d'un concept X avec le macro-rôle
    x = grammar._generate_canonical_unit_vector(np.random.default_rng(99))
    bound = circular_convolution(macro_role, x)
    unbound = circular_correlation(bound, macro_role)
    sim = float(cosine_similarity(unbound, x))
    assert sim >= 0.85


def test_propositional_consistency_detects_contradictions():
    """
    Test 2 : Vérifie que verify_propositional_consistency valide un corpus cohérent
    et détecte infailliblement une antipodalité vectorielle (P et ~P).
    """
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=123))

    # Cas A : Propositions cohérentes (mutuellement orthogonales ou corrélées positivement)
    p1 = grammar._generate_canonical_unit_vector(np.random.default_rng(1))
    p2 = grammar._generate_canonical_unit_vector(np.random.default_rng(2))
    p3 = grammar._generate_canonical_unit_vector(np.random.default_rng(3))

    is_consistent, min_sim, conflicts = verify_propositional_consistency(
        statements=[p1, p2, p3],
        contradiction_threshold=-0.50
    )
    assert is_consistent is True
    assert len(conflicts) == 0

    # Cas B : Introduction d'une proposition contradictoire (négation vectorielle)
    p_contra = -p1 + np.random.normal(0.0, 0.05, size=dim).astype(np.float32)
    p_contra /= np.linalg.norm(p_contra)

    is_consistent_b, min_sim_b, conflicts_b = verify_propositional_consistency(
        statements=[p1, p2, p_contra],
        contradiction_threshold=-0.50
    )
    assert is_consistent_b is False
    assert len(conflicts_b) >= 1
    assert min_sim_b < -0.50
    # Le conflit doit pointer sur (0, 2)
    conflict_pairs = [(c[0], c[1]) for c in conflicts_b]
    assert (0, 2) in conflict_pairs


def test_federal_diplomatic_bridge_asymmetric_cka():
    """
    Test 3 : Vérifie que FederalDiplomaticBridge projette entre connectomes asymétriques
    (D_A=16, D_B=32) et maintient un alignement CKA élevé.
    """
    bridge = FederalDiplomaticBridge(seed=42)
    n_samples = 20
    rng = np.random.default_rng(42)

    vecs_a = rng.normal(0, 1.0, size=(n_samples, 16)).astype(np.float32)
    vecs_a /= np.linalg.norm(vecs_a, axis=-1, keepdims=True)

    # Projection vers D_B = 32
    projected_b = np.array([bridge.project(v, 32) for v in vecs_a])
    assert projected_b.shape == (n_samples, 32)
    for v in projected_b:
        assert abs(np.linalg.norm(v) - 1.0) < 1e-4

    # Calcul CKA linéaire entre l'espace A et l'espace projeté B
    cka_score = bridge.compute_asymmetric_alignment_cka(vecs_a, projected_b)
    # L'isométrie partielle SVD doit préserver au moins 0.85 de CKA
    assert cka_score >= 0.85


def test_federal_monument_inworld_and_treaty_ratification():
    """
    Test 4 : Vérifie l'initialisation du FederalMonument in-world, le rejet d'une règle
    contradictoire et la ratification d'un traité de paix avec bonus calorique.
    """
    world_cfg = WorldConfig(size=12)
    world = Biosphere3D(world_cfg)
    lu_cfg = LUInWorldConfig(
        latent_dim=16,
        enable_diplomacy=True,
        enable_meta_grammar=True,
        federation_monument_x=6.0,
        federation_monument_y=6.0,
        treaty_cooperation_bonus=3.0,
    )
    adapter = LUInWorldAdapter(world, lu_cfg)

    # 1. Présence du Monument
    assert adapter.federal_monument is not None
    assert adapter.federal_monument.id == "monument_federal_central"
    assert len(adapter.federal_monument.ratified_treaties) >= 1

    # 2. Test du rejet de contradiction sur le monument
    grammar = adapter.grammar
    const_clause = grammar.extract_treaty_clause(adapter.federal_monument.constitution_vector)
    # Création d'une proposition antipodale violant la constitution
    anti_const = -const_clause + np.random.normal(0.0, 0.05, size=lu_cfg.latent_dim).astype(np.float32)
    anti_const /= np.linalg.norm(anti_const)

    accepted, msg = adapter.propose_meta_rule_to_monument(
        proposer_id="REBEL_AGENT",
        rule_name="WAR_RULE",
        input_role_vec=grammar.ROLE_META_SUBJECT,
        operator_vec=grammar.ROLE_META_OPERATOR,
        output_role_vec=anti_const
    )
    assert accepted is False
    assert "CONTRADICTION_REJECTED" in msg
    assert adapter.federal_monument.contradiction_rejections_count >= 1

    # 3. Ratification de traité entre deux agents citoyens
    agent_a = {"id": "agent_alpha", "x": 6, "y": 6, "energy": 50.0}
    agent_b = {"id": "agent_beta", "x": 6, "y": 7, "energy": 50.0}

    success = adapter.ratify_federal_treaty(agent_a, agent_b, treaty_name="TREATY_MUTUAL_AID")
    assert success is True
    assert adapter.treaties_ratified_count >= 1
    # Bonus calorique appliqué
    assert agent_a["energy"] == 53.0
    assert agent_b["energy"] == 53.0
    assert "agent_beta" in agent_a["federal_treaties"]
    assert "agent_alpha" in agent_b["federal_treaties"]


def test_kuzudb_metagrammar_and_treaty_persistence():
    """
    Test 5 : Vérifie l'enregistrement et l'auditabilité dans KuzuDB des métarègles,
    des contrôles de consistance et des traités fédéraux.
    """
    temp_dir = tempfile.mkdtemp()
    db_path = str(Path(temp_dir) / "kuzu_phase7_test")
    try:
        db = KuzuDatabase(DatabaseConfig(db_path=db_path))
        bridge_cfg = LUSymbolicBridgeConfig(dim=16, db_path=db_path)
        bridge = LUSymbolicBridge(bridge_cfg, db=db)

        # 1. Enregistrement LUMetaGrammar
        ok_rule = bridge.register_meta_grammar_rule(
            rule_id="meta_rule_001",
            rule_name="CONSTITUTIONAL_SUPREMACY",
            input_role="ROLE_LAW",
            operator="DERIVES",
            output_role="ROLE_PEACE"
        )
        assert ok_rule is True

        # 2. Enregistrement LUProofCheck
        ok_proof = bridge.register_proof_check(
            check_id="proof_001",
            theorem_id="meta_rule_001",
            is_consistent=True,
            min_similarity=0.25,
            conflict_count=0
        )
        assert ok_proof is True

        # 3. Enregistrement LUFederalTreaty
        ok_treaty = bridge.register_federal_treaty(
            treaty_id="treaty_fed_001",
            treaty_name="PAN_WORLD_CONSTITUTION",
            clause_summary="Interdiction de predation et marche commun",
            signatories=["WORLD_1", "WORLD_2", "WORLD_3"]
        )
        assert ok_treaty is True

        # 4. Vérification de lecture Cypher
        res_rule = db.execute_cypher("MATCH (r:LUMetaGrammar) RETURN count(r) AS c")
        assert res_rule[0][0] == 1

        res_proof = db.execute_cypher("MATCH (p:LUProofCheck) RETURN count(p) AS c")
        assert res_proof[0][0] == 1

        res_treaty = db.execute_cypher("MATCH (t:LUFederalTreaty) RETURN count(t) AS c")
        assert res_treaty[0][0] == 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
