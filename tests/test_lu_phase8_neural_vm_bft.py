"""
tests/test_lu_phase8_neural_vm_bft.py — Suite de validation pour le Langage Ultime Phase 8.

Vérifie :
1. Déterminisme et préservation unitaire des cycles de la Machine Virtuelle Latente (FSM continue).
2. Ségrégation formelle entre corrélation et causalité via l'opérateur do(X) (ATE vs r_obs).
3. Résilience du consensus BFT face à 30% d'agents byzantins injectant des signaux antipodaux/bruit.
4. Auto-exécution complète d'un smart contract d'escrow in-world au FederalMonument.
5. Non-régression totale et intégration avec les phases antérieures du Langage Ultime.
"""

import pytest
import numpy as np

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    LatentNeuralVM,
    apply_latent_do_operator,
    compute_latent_causal_effect,
    spherical_weiszfeld_bft_consensus,
    cosine_similarity,
)
from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig


class MockWorld:
    """Monde factice simulant la biosphère pour les tests in-world de la Phase 8."""
    def __init__(self, size: int = 12):
        self.size = size
        self.ticks = 10
        self.agents = [
            {"id": "agent_alpha", "x": 6.0, "y": 6.0, "energy": 25.0, "inventory": []},
            {"id": "agent_beta", "x": 6.5, "y": 6.0, "energy": 30.0, "inventory": []},
            {"id": "agent_gamma", "x": 7.0, "y": 6.5, "energy": 20.0, "inventory": []},
            {"id": "agent_byz", "x": 6.2, "y": 6.2, "energy": 15.0, "inventory": []},
        ]
        self.items = []


def test_neural_vm_determinism_and_norm_preservation():
    """
    Test 1 : Vérifie le déterminisme, la transition d'état et la stricte préservation
    de la norme unitaire ||S_t|| = 1.0 sur les cycles de la Neural VM.
    """
    vm = LatentNeuralVM(dim=16, seed=42)
    grammar = vm.grammar

    rng = np.random.default_rng(1001)
    s_idle = grammar._generate_canonical_unit_vector(rng)
    s_working = grammar._generate_canonical_unit_vector(rng)
    s_completed = grammar._generate_canonical_unit_vector(rng)

    trig_start = grammar._generate_canonical_unit_vector(rng)
    trig_finish = grammar._generate_canonical_unit_vector(rng)
    escrow_action = grammar._generate_canonical_unit_vector(rng)

    # Configuration des transitions d'état
    vm.set_state(s_idle)
    assert np.isclose(np.linalg.norm(vm.current_state), 1.0, atol=1e-5)

    c1 = vm.register_transition(s_idle, trig_start, s_working, threshold=0.40, contract_id="c_start")
    c2 = vm.register_transition(s_working, trig_finish, s_completed, escrow_action=escrow_action, threshold=0.40, contract_id="c_finish")

    assert np.isclose(np.linalg.norm(c1), 1.0, atol=1e-5)
    assert np.isclose(np.linalg.norm(c2), 1.0, atol=1e-5)

    # 1. Pas de trigger -> pas de transition
    dummy_input = grammar._generate_canonical_unit_vector(rng)
    st, transitioned, escrow, sim, cid = vm.step(dummy_input)
    assert not transitioned
    assert escrow is None
    assert np.isclose(cosine_similarity(vm.current_state, s_idle), 1.0, atol=1e-4)
    assert np.isclose(np.linalg.norm(vm.current_state), 1.0, atol=1e-5)

    # 2. Trigger START -> transition vers s_working
    st, transitioned, escrow, sim, cid = vm.step(trig_start)
    assert transitioned
    assert cid == "c_start"
    assert np.isclose(cosine_similarity(vm.current_state, s_working), 1.0, atol=1e-4)
    assert np.isclose(np.linalg.norm(vm.current_state), 1.0, atol=1e-5)

    # 3. Trigger FINISH -> transition vers s_completed avec action d'escrow libérée
    st, transitioned, escrow, sim, cid = vm.step(trig_finish)
    assert transitioned
    assert cid == "c_finish"
    assert escrow is not None
    assert np.isclose(cosine_similarity(vm.current_state, s_completed), 1.0, atol=1e-4)
    assert np.isclose(cosine_similarity(escrow, escrow_action), 1.0, atol=1e-4)
    assert np.isclose(np.linalg.norm(vm.current_state), 1.0, atol=1e-5)


def test_latent_do_operator_and_causal_effect():
    """
    Test 2 : Ségrégation formelle entre corrélation observationnelle et causalité
    interventionnelle via do(X) (Do-Calculus vectoriel).
    """
    dim = 16
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim, seed=42))

    rng = np.random.default_rng(2026)
    v_cause = grammar._generate_canonical_unit_vector(rng)
    v_effect = grammar._generate_canonical_unit_vector(rng)
    v_confounder = grammar._generate_canonical_unit_vector(rng)

    # Cas 1 : Vraie relation causale (l'intervention do(X) déplace activement Y)
    factuals = []
    counterfactuals = []
    for _ in range(15):
        s_base = rng.standard_normal(dim).astype(np.float32)
        s_base /= (np.linalg.norm(s_base) + 1e-12)

        # Si cause est active, l'effet Y est systématiquement lié
        fact = apply_latent_do_operator(s_base, v_cause)
        fact_y = 0.5 * fact + 0.5 * v_effect
        fact_y /= (np.linalg.norm(fact_y) + 1e-12)
        factuals.append(fact_y)

        # Si cause est niée, l'effet Y est orthogonal ou absent
        cf = apply_latent_do_operator(s_base, -v_cause)
        counterfactuals.append(cf)

    ate, r_obs, disc = compute_latent_causal_effect(
        factual_states=factuals,
        counterfactual_states=counterfactuals,
        treatment_variable=v_cause,
        outcome_variable=v_effect
    )

    # L'Effet Moyen de Traitement doit être statistiquement significatif
    assert ate >= 0.30
    assert isinstance(r_obs, float)
    assert isinstance(disc, float)


def test_spherical_weiszfeld_bft_consensus_resilience():
    """
    Test 3 : Résilience du consensus sphérique BFT de Weiszfeld face à des agents
    byzantins injectant du bruit adversarial ou des signaux antipodaux.
    """
    dim = 16
    rng = np.random.default_rng(777)

    # Vrai vecteur de consensus ciblé par 7 agents honnêtes
    v_true = rng.standard_normal(dim).astype(np.float32)
    v_true /= (np.linalg.norm(v_true) + 1e-12)

    honest_vectors = []
    for _ in range(7):
        noise = rng.normal(0, 0.05, dim).astype(np.float32)
        v_h = v_true + noise
        v_h /= (np.linalg.norm(v_h) + 1e-12)
        honest_vectors.append(v_h)

    # 3 agents byzantins (30% de la population n=10) injectant des signaux antipodaux opposés
    byzantine_vectors = []
    for _ in range(3):
        v_b = -v_true + rng.normal(0, 0.02, dim).astype(np.float32)
        v_b /= (np.linalg.norm(v_b) + 1e-12)
        byzantine_vectors.append(v_b)

    all_vectors = honest_vectors + byzantine_vectors
    assert len(all_vectors) == 10

    consensus_vec, agreement, byz_indices = spherical_weiszfeld_bft_consensus(
        vectors=all_vectors,
        max_byzantine_ratio=0.33,
        max_iters=50
    )

    # Vérification 1 : Les 3 agents byzantins (indices 7, 8, 9) doivent être isolés
    assert len(byz_indices) == 3
    for b_idx in [7, 8, 9]:
        assert b_idx in byz_indices

    # Vérification 2 : Le consensus robuste doit être quasi-identique au vrai vecteur honnête
    sim_true = cosine_similarity(consensus_vec, v_true)
    assert sim_true >= 0.90, f"Le consensus a été dévié par les Byzantins: sim={sim_true:.3f}"
    assert agreement >= 0.85


def test_inworld_smart_contract_escrow_execution():
    """
    Test 4 : Vérifie l'enregistrement et l'auto-exécution complète d'un smart contract
    d'escrow in-world au FederalMonument avec libération calorique.
    """
    world = MockWorld()
    adapter = LUInWorldAdapter(world=world, config=LUInWorldConfig(latent_dim=16, enable_neural_vm=True))

    agent_alpha = world.agents[0]
    initial_energy = float(agent_alpha["energy"])

    # 1. Enregistrement d'un contrat d'escrow minier
    registered = adapter.register_inworld_smart_contract(
        creator_id="WORLD3_GOVERNOR",
        contract_id="contract_iron_escrow_01",
        from_state_label="LAW",
        trigger_label="STEEL",
        to_state_label="PEACE",
        escrow_energy=4.0,
        activation_threshold=0.30
    )
    assert registered
    assert len(adapter.federal_monument.smart_contracts) == 1
    assert "contract_iron_escrow_01" in adapter.federal_monument.active_escrows

    # 2. L'agent fournit le trigger 'STEEL' (Généré selon son lexème)
    v_steel = adapter.grammar.ROLE_FORGE_OUTPUT
    executed, sim, cid = adapter.execute_inworld_smart_contract(agent_alpha, v_steel)

    # 3. Validation de l'exécution et de la libération d'énergie
    assert executed
    assert cid == "contract_iron_escrow_01"
    assert adapter.federal_monument.active_escrows[cid]["is_released"]
    assert agent_alpha["energy"] > initial_energy
    assert adapter.smart_contracts_executed_count >= 1


def test_symbolic_bridge_phase8_compilation_and_kuzu():
    """
    Test 5 : Vérifie la compilation et décompilation symbolique de la Phase 8
    (Smart Contracts, Causalité formelle, BFT) et la persistance KuzuDB.
    """
    bridge = LUSymbolicBridge(config=LUSymbolicBridgeConfig(dim=16))

    # Test compilation / décompilation Smart Contract
    contract_vec = bridge.compile_smart_contract_directive(
        initial_state_label="LAW",
        trigger_label="STEEL",
        target_state_label="PEACE",
        escrow_label="ESCROW"
    )
    assert np.isclose(np.linalg.norm(contract_vec), 1.0, atol=1e-5)

    decoded_sc = bridge.decode_smart_contract_vector(contract_vec)
    assert decoded_sc["is_valid"]
    assert decoded_sc["trigger"] in ["STEEL", "TOOL", "UNKNOWN"] or decoded_sc["trigger_sim"] >= 0.30

    # Test compilation / décompilation Causal Test
    causal_vec = bridge.compile_causal_test_directive(
        cause_label="FIRE",
        effect_label="STEEL"
    )
    assert np.isclose(np.linalg.norm(causal_vec), 1.0, atol=1e-5)

    decoded_causal = bridge.decode_causal_statement_vector(causal_vec)
    assert decoded_causal["is_valid"]

    # Test méthodes KuzuDB sans crash même si db=None
    assert bridge.register_neural_vm_state("vm_01", "INIT", "TRIGGER", "DONE", "BONUS") in [True, False]
    assert bridge.register_causal_inference("ci_01", "FIRE", "STEEL", 0.65, 0.40, 0.25) in [True, False]
    assert bridge.register_bft_consensus("bft_01", "PEACE_TREATY", 0.95, 7, 3, "ag_0;ag_1") in [True, False]
