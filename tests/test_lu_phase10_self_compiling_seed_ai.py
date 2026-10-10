"""
tests/test_lu_phase10_self_compiling_seed_ai.py — Suite de validation pour le Langage Ultime Phase 10.

Vérifie :
1. Déterminisme et intégrité spectrale du désassemblage/recompilation de connectome (S^(D-1), rho(W) < 1.0).
2. Vérification formelle de Hoare continue ({P} C {Q}, rejet des contradictions constitutionnelles et divergences).
3. Auto-compilation in-situ d'un MambaAgent vivant avec préservation de la stabilité dynamique.
4. Soumission et approbation d'auto-mutation à l'autel d'évolution du FederalMonument (+10.0 E, traçabilité).
5. Intégration dans step() in-world et non-régression stricte (quand enable_self_compilation=False).
"""

import pytest
import numpy as np

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    ConnectomeCompiler,
    verify_hoare_safety,
    circular_convolution,
    cosine_similarity,
)
from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig
from src.agents.mamba_agent import MambaAgent


class MockModelPhase10:
    """Modèle léger simulant un connectome neural pour tests rapides."""
    def __init__(self, n: int = 16):
        rng = np.random.RandomState(42)
        # Matrice stable avec rayon spectral < 1.0
        raw = (rng.randn(n, n) * 0.1).astype(np.float32)
        self.W = raw


class MockWorldPhase10:
    """Monde factice pour tester les interactions d'auto-évolution in-world au FederalMonument."""
    def __init__(self, size: int = 12):
        self.size = size
        self.ticks = 0
        self.model = MockModelPhase10(n=16)
        self.agents = [
            {"id": "agent_seed_1", "x": 6.0, "y": 6.0, "energy": 25.0, "inventory": [], "model": MockModelPhase10(n=16)},
            {"id": "agent_seed_2", "x": 6.5, "y": 6.0, "energy": 30.0, "inventory": [], "model": MockModelPhase10(n=16)},
            {"id": "agent_distant", "x": 1.0, "y": 1.0, "energy": 20.0, "inventory": []},
        ]
        self.items = []


def test_connectome_compiler_disassemble_and_recompile():
    """
    Test 1 : Vérifie le désassemblage spectral unitaire W -> Z_conn in S^(D-1)
    et la recompilation chirurgicale d'un macro-programme sous Lipschitz spectral rho(W) < 1.0.
    """
    compiler = ConnectomeCompiler(dim=16, seed=42)
    model = MockModelPhase10(n=16)

    # 1. Désassemblage spectral
    z_conn, info = compiler.disassemble_connectome(model)
    assert isinstance(z_conn, np.ndarray)
    assert z_conn.shape == (16,)
    norm_z = np.linalg.norm(z_conn)
    assert abs(norm_z - 1.0) < 1e-4, f"Z_conn doit être sur S^(D-1), norme={norm_z}"
    assert info["is_stable"] is True
    assert info["spectral_radius"] < 1.0

    # 2. Recompilation chirurgicale
    rng = np.random.RandomState(101)
    macro_prog = rng.randn(16).astype(np.float32)
    macro_prog = macro_prog / np.linalg.norm(macro_prog)

    W_before = model.W.copy()
    success, spec_rad, compile_info = compiler.compile_to_connectome(
        macro_program=macro_prog,
        target_model=model,
        alpha=0.15
    )

    assert success is True
    assert spec_rad < 1.0, f"Rayon spectral doit rester strictement contractant : {spec_rad}"
    assert not np.array_equal(model.W, W_before), "Les poids du connectome doivent avoir été modifiés."
    assert np.all(np.isfinite(model.W)), "Les poids ne doivent contenir ni NaN ni Inf."


def test_hoare_continuous_safety_verification():
    """
    Test 2 : Vérifie la Logique de Hoare continue {P} C {Q} :
    - Acceptation des transformations cohérentes.
    - Rejet des contradictions constitutionnelles (<C, Constitution> < -0.30).
    - Rejet des divergences de post-condition.
    """
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=16))

    rng = np.random.default_rng(2026)
    v_pre = grammar._generate_canonical_unit_vector(rng)
    v_const = grammar._generate_canonical_unit_vector(rng)

    # Cas 1 : Transformation alignée et sûre
    v_cmd = v_const.copy()
    v_post = circular_convolution(v_pre, v_cmd)
    v_post = (v_post / (np.linalg.norm(v_post) + 1e-12)).astype(np.float32)
    is_safe, score, reason = verify_hoare_safety(
        pre_state=v_pre,
        modification=v_cmd,
        post_condition=v_post,
        constitution_vector=v_const,
        alignment_threshold=0.60
    )
    assert is_safe is True
    assert reason == "HOARE_PROOF_SATISFIED"
    assert score >= 0.60

    # Cas 2 : Violation constitutionnelle (anti-parallèle à la constitution)
    v_bad_cmd = -v_const
    is_safe_bad, score_bad, reason_bad = verify_hoare_safety(
        pre_state=v_pre,
        modification=v_bad_cmd,
        post_condition=v_post,
        constitution_vector=v_const,
        alignment_threshold=0.60
    )
    assert is_safe_bad is False
    assert reason_bad == "CONSTITUTIONAL_CONTRADICTION"

    # Cas 3 : Violation de post-condition (commande divergente)
    v_divergent_post = -v_post
    is_safe_div, score_div, reason_div = verify_hoare_safety(
        pre_state=v_pre,
        modification=v_cmd,
        post_condition=v_divergent_post,
        constitution_vector=v_const,
        alignment_threshold=0.60
    )
    assert is_safe_div is False
    assert reason_div == "HOARE_POSTCONDITION_VIOLATION"


def test_mamba_agent_in_situ_self_compilation():
    """
    Test 3 : Auto-compilation chirurgicale in-situ d'un MambaAgent vivant avec génome V13.
    Vérifie la mise à jour directe de genome.W sous contrôle de rayon spectral.
    """
    agent = MambaAgent(num_inputs=10, num_outputs=10, num_nodes=24)
    compiler = ConnectomeCompiler(dim=16, seed=42)

    # Vérification initiale
    z_conn, info = compiler.disassemble_connectome(agent)
    assert z_conn.shape == (16,)
    assert abs(np.linalg.norm(z_conn) - 1.0) < 1e-4

    W_orig = agent.genome.W.copy()

    # Recompilation ciblée
    rng = np.random.RandomState(99)
    macro_token = rng.randn(16).astype(np.float32)
    macro_token = macro_token / np.linalg.norm(macro_token)

    ok, spec_rad, info_compile = compiler.compile_to_connectome(
        macro_program=macro_token,
        target_model=agent,
        alpha=0.10
    )

    assert ok is True
    assert spec_rad < 1.0
    assert not np.array_equal(agent.genome.W, W_orig), "Le génome du MambaAgent doit être modifié in-situ."
    assert np.all(np.isfinite(agent.genome.W))


def test_federal_monument_self_evolution_altar():
    """
    Test 4 : Soumission et ratification d'une auto-modification au FederalMonument.
    Vérifie la preuve de Hoare, l'attribution du dividende calorique (+10.0 E)
    et la journalisation dans l'hyper-graphe / monument.
    """
    world = MockWorldPhase10()
    adapter = LUInWorldAdapter(world=world, config=LUInWorldConfig(enable_self_compilation=True))
    adapter.bootstrap_federal_monument()

    agent = world.agents[0]
    initial_energy = float(agent["energy"])
    model = agent["model"]

    # Exécution de l'auto-évolution
    success = adapter.verify_and_apply_connectome_evolution(agent=agent, target_model=model)

    assert success is True
    assert agent.get("connectome_self_compiled") is True
    assert float(agent["energy"]) >= initial_energy + 10.0, "L'agent doit recevoir le bonus d'auto-évolution (+10.0 E)"
    assert adapter.self_compiled_mutations_count >= 1
    assert adapter.hoare_proofs_verified_count >= 1

    # Vérification des registres du FederalMonument
    assert adapter.federal_monument is not None
    assert len(adapter.federal_monument.self_compiled_mutations) >= 1
    assert len(adapter.federal_monument.hoare_proofs) >= 1

    last_proof = adapter.federal_monument.hoare_proofs[-1]
    assert last_proof["is_safe"] is True
    assert last_proof["agent_id"] == str(agent["id"])


def test_lu_inworld_step_integration_and_non_regression():
    """
    Test 5 : Intégration complète dans la boucle step() in-world :
    - Déclenchement automatique pour les agents proches de l'autel.
    - Non-régression totale quand enable_self_compilation=False (zéro auto-compilation).
    """
    world = MockWorldPhase10()
    adapter_active = LUInWorldAdapter(world=world, config=LUInWorldConfig(enable_self_compilation=True))
    adapter_active.bootstrap_federal_monument()

    # Step avec auto-compilation active
    res = adapter_active.step()
    assert res["tick_self_compilations"] >= 1
    assert res["self_compiled_mutations"] >= 1
    assert res["hoare_proofs_verified"] >= 1

    # Step avec auto-compilation désactivée
    world_inactive = MockWorldPhase10()
    adapter_inactive = LUInWorldAdapter(world=world_inactive, config=LUInWorldConfig(enable_self_compilation=False))
    adapter_inactive.bootstrap_federal_monument()

    res_inactive = adapter_inactive.step()
    assert res_inactive["tick_self_compilations"] == 0
    assert res_inactive["self_compiled_mutations"] == 0
    assert adapter_inactive.self_compiled_mutations_count == 0
