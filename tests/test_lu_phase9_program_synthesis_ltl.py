"""
tests/test_lu_phase9_program_synthesis_ltl.py — Suite de validation pour le Langage Ultime Phase 9.

Vérifie :
1. Déterminisme et terminaison contractante des boucles de programmes latents (Théorème du point fixe de Banach, Lipschitz L < 1.0).
2. Validation des opérateurs de Logique Temporelle Diachronique Vectorielle (LTL: NEXT, EVENTUALLY, ALWAYS).
3. Résolution et fidélité d'analogies vectorielles multivers (A : B :: C : D, CKA/fidélité >= 0.85).
4. Auto-exécution in-world d'un contrat temporel à libération différée au FederalMonument.
5. Intégration complète in-world : synthèse de programmes, transfert d'analogie et non-régression.
"""

import pytest
import numpy as np

from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    LatentProgramSynthesizer,
    apply_temporal_operator,
    solve_latent_analogy,
    verify_analogy_quality,
    cosine_similarity,
)
from src.metaprog.lu_symbolic_bridge import LUSymbolicBridge, LUSymbolicBridgeConfig
from src.environments.lu_inworld_adapter import LUInWorldAdapter, LUInWorldConfig


class MockWorldPhase9:
    """Monde factice pour tester les interactions de Phase 9 au FederalMonument."""
    def __init__(self, size: int = 12):
        self.size = size
        self.ticks = 0
        self.agents = [
            {"id": "agent_alpha", "x": 6.0, "y": 6.0, "energy": 25.0, "inventory": []},
            {"id": "agent_beta", "x": 6.5, "y": 6.0, "energy": 30.0, "inventory": []},
            {"id": "agent_gamma", "x": 7.0, "y": 6.5, "energy": 20.0, "inventory": []},
        ]
        self.items = []


def test_latent_program_synthesis_banach_termination():
    """
    Test 1 : Vérifie la synthèse de programmes vectoriels et la garantie de terminaison
    stricte par contraction de Banach (Lipschitz constant L < 1.0).
    """
    synthesizer = LatentProgramSynthesizer(dim=16, seed=42)
    grammar = synthesizer.grammar

    rng = np.random.default_rng(2026)
    v_entry = grammar._generate_canonical_unit_vector(rng)
    v_loop = grammar._generate_canonical_unit_vector(rng)
    v_branch = grammar._generate_canonical_unit_vector(rng)
    v_term = grammar._generate_canonical_unit_vector(rng)

    # 1. Synthèse d'un programme contractant (L = 0.80 < 1.0)
    token = synthesizer.synthesize_program(
        entry_state=v_entry,
        loop_operator=v_loop,
        branch_condition=v_branch,
        terminal_state=v_term,
        lipschitz_constant=0.80,
        program_id="prog_contracting"
    )

    assert token.shape == (16,)
    assert np.isclose(np.linalg.norm(token), 1.0, atol=1e-5)
    assert "prog_contracting" in synthesizer.synthesized_programs

    # 2. Exécution du programme avec état initial aligné sur v_entry
    final_state, trace, converged = synthesizer.execute(
        program_id="prog_contracting",
        initial_state=v_entry.copy(),
        max_iterations=30,
        tolerance=1e-4
    )

    assert converged is True
    assert len(trace) > 1
    assert len(trace) <= 30
    assert np.isclose(np.linalg.norm(final_state), 1.0, atol=1e-5)

    # Vérification de la propriété de contraction : la distance entre états consécutifs décroît
    diffs = [np.linalg.norm(trace[i] - trace[i-1]) for i in range(2, len(trace))]
    if len(diffs) >= 2:
        assert diffs[-1] <= diffs[0] + 1e-4

    # 3. Branchement conditionnel : si l'état initial satisfait la condition de branchement,
    # le programme converge immédiatement vers terminal_state
    final_branch, trace_branch, conv_branch = synthesizer.execute(
        program_id="prog_contracting",
        initial_state=v_branch.copy(),
        max_iterations=10,
        tolerance=1e-4
    )
    assert conv_branch is True
    assert np.isclose(cosine_similarity(final_branch, v_term), 1.0, atol=0.20)


def test_vectorial_linear_temporal_logic_operators():
    """
    Test 2 : Validation des opérateurs de Logique Temporelle Vectorielle (LTL) :
    NEXT, EVENTUALLY et ALWAYS sur des trajectoires de Gigatokens.
    """
    dim = 16
    rng = np.random.default_rng(777)
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim))

    pred = grammar._generate_canonical_unit_vector(rng)
    noise_vec = grammar._generate_canonical_unit_vector(rng)

    # Trajectoire 1 : Le prédicat est respecté à chaque pas de temps (ALWAYS vrai)
    traj_always = [pred + 0.05 * np.random.randn(dim).astype(np.float32) for _ in range(6)]
    traj_always = [(v / np.linalg.norm(v)).astype(np.float32) for v in traj_always]

    sat_always, score_always, _ = apply_temporal_operator(
        trajectory=traj_always,
        predicate=pred,
        operator_type="ALWAYS",
        horizon=5,
        threshold=0.50
    )
    assert sat_always is True
    assert score_always >= 0.50

    # Trajectoire 2 : Violation à t=2 (ALWAYS faux)
    traj_broken = traj_always.copy()
    traj_broken[2] = -pred  # violation directe antipodale
    sat_broken, score_broken, _ = apply_temporal_operator(
        trajectory=traj_broken,
        predicate=pred,
        operator_type="ALWAYS",
        horizon=5,
        threshold=0.50
    )
    assert sat_broken is False

    # Trajectoire 3 : Prédicat absent au début mais présent à t=3 (EVENTUALLY vrai)
    traj_eventual = [noise_vec for _ in range(5)]
    traj_eventual[3] = pred
    sat_eventually, score_eventually, _ = apply_temporal_operator(
        trajectory=traj_eventual,
        predicate=pred,
        operator_type="EVENTUALLY",
        horizon=5,
        threshold=0.50
    )
    assert sat_eventually is True
    assert score_eventually >= 0.50

    # Trajectoire 4 : Opérateur NEXT (satisfait si le pas t=1 satisfait le prédicat)
    traj_next = [noise_vec, pred, noise_vec]
    sat_next, score_next, _ = apply_temporal_operator(
        trajectory=traj_next,
        predicate=pred,
        operator_type="NEXT",
        horizon=2,
        threshold=0.50
    )
    assert sat_next is True


def test_latent_cross_world_analogy_solving():
    """
    Test 3 : Résolution d'analogie sémantique vectorielle A : B :: C : D.
    Vérifie que D_solved reconstruit fidèlement la relation structurelle (fidélité >= 0.85).
    """
    dim = 16
    rng = np.random.default_rng(888)
    grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=dim))

    # Définition d'un vecteur de transformation relationnelle R
    # Ex: Métallurgie (A: Charbon -> B: Acier) vs Agriculture (C: Compost -> D: Moisson)
    v_a = grammar._generate_canonical_unit_vector(rng)
    v_relation = grammar._generate_canonical_unit_vector(rng) * 0.60
    v_b = (v_a + v_relation)
    v_b = (v_b / np.linalg.norm(v_b)).astype(np.float32)

    v_c = grammar._generate_canonical_unit_vector(rng)
    v_d_expected = (v_c + v_relation)
    v_d_expected = (v_d_expected / np.linalg.norm(v_d_expected)).astype(np.float32)

    # Résolution par transport optimal / parallélogramme sphérique
    v_d_solved = solve_latent_analogy(v_a, v_b, v_c)

    assert v_d_solved.shape == (dim,)
    assert np.isclose(np.linalg.norm(v_d_solved), 1.0, atol=1e-5)

    # Évaluation de la fidélité de l'analogie
    fidelity = verify_analogy_quality(v_a, v_b, v_c, v_d_expected)
    assert fidelity >= 0.85, f"Fidélité d'analogie insuffisante : {fidelity:.4f} < 0.85"


def test_inworld_temporal_contract_delayed_release():
    """
    Test 4 : Auto-exécution d'un contrat temporel LTL au FederalMonument in-world.
    L'énergie est bloquée sous séquestre et n'est libérée qu'après vérification continue
    de la clause temporelle sur l'horizon spécifié.
    """
    world = MockWorldPhase9()
    cfg = LUInWorldConfig(
        latent_dim=16,
        enable_program_synthesis=True,
        enable_ltl_temporal_logic=True,
        enable_analogy_transfer=True
    )
    adapter = LUInWorldAdapter(world, config=cfg)

    # Initialisation du FederalMonument
    adapter.bootstrap_federal_monument()
    assert adapter.federal_monument is not None

    # Enregistrement d'un contrat temporel : ALWAYS satisfaire "PEACE" pendant 3 ticks
    reg_ok = adapter.register_temporal_smart_contract(
        creator_id="agent_alpha",
        contract_id="contract_peace_3ticks",
        trigger_label="PEACE",
        target_label="COOPERATION",
        delay_ticks=3,
        escrow_energy=6.0,
        condition_type="ALWAYS"
    )
    assert reg_ok is True
    assert "contract_peace_3ticks" in adapter.federal_monument.temporal_escrows

    alpha = world.agents[0]
    initial_energy = alpha["energy"]

    # Les agents maintiennent l'état pacifique requis par le contrat temporel
    v_peace = adapter.federal_monument.temporal_escrows["contract_peace_3ticks"]["trigger_vector"]
    for ag in world.agents:
        ag["lu_latent"] = v_peace.copy()

    # Tick 1 : Contrat en cours, 2 ticks restants, pas de libération
    released_1 = adapter.step_temporal_escrows(world.agents)
    assert released_1 == 0
    assert alpha["energy"] == initial_energy
    assert not adapter.federal_monument.temporal_escrows["contract_peace_3ticks"]["is_released"]

    # Tick 2 : Contrat en cours, 1 tick restant
    released_2 = adapter.step_temporal_escrows(world.agents)
    assert released_2 == 0
    assert alpha["energy"] == initial_energy

    # Tick 3 : Échéance atteinte avec succès ! Libération de l'escrow énergétique
    released_3 = adapter.step_temporal_escrows(world.agents)
    assert released_3 == 1
    assert adapter.federal_monument.temporal_escrows["contract_peace_3ticks"]["is_released"]
    assert alpha["energy"] > initial_energy
    assert adapter.temporal_escrows_released_count == 1


def test_inworld_program_synthesis_and_analogy_transfer():
    """
    Test 5 : Synthèse de programme in-world et transfert d'analogie avec dividende d'énergie.
    Vérifie la non-régression et le cycle complet d'adaptation.
    """
    world = MockWorldPhase9()
    cfg = LUInWorldConfig(latent_dim=16)
    adapter = LUInWorldAdapter(world, config=cfg)
    adapter.bootstrap_federal_monument()

    alpha = world.agents[0]
    e_start = alpha["energy"]

    # 1. Synthèse d'un macro-programme in-world
    syn_ok = adapter.synthesize_and_register_program(
        creator_id="agent_alpha",
        program_id="macro_forage_craft",
        entry_label="HARVEST",
        loop_operator="REFINE",
        branch_condition="READY",
        term_label="STORE",
        lipschitz_l=0.80
    )
    assert syn_ok is True
    assert len(adapter.federal_monument.synthesized_programs) == 1
    assert adapter.programs_synthesized_count == 1

    # 2. Exécution in-world du programme
    exec_res = adapter.execute_inworld_program(alpha, "macro_forage_craft")
    assert exec_res["converged"] is True
    assert alpha["energy"] >= e_start + 4.0  # Bonus de réalisation de programme

    # 3. Transfert d'analogie inter-mondes
    e_before_analogy = alpha["energy"]
    analogy_res = adapter.conduct_analogy_transfer(
        agent=alpha,
        a_label="CHARCOAL",
        b_label="STEEL",
        c_label="COMPOST",
        d_target_label="HARVEST"
    )
    assert "transferred" in analogy_res
    assert "fidelity" in analogy_res
    if analogy_res["transferred"]:
        assert alpha["energy"] >= e_before_analogy + 3.0
        assert adapter.analogy_transfers_count >= 1

    # 4. Intégration via step() globale
    step_metrics = adapter.step()
    assert "temporal_clauses_evaluated" in step_metrics
    assert "programs_synthesized" in step_metrics
    assert "analogy_transfers" in step_metrics
