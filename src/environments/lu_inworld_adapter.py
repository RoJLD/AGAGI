"""
src/environments/lu_inworld_adapter.py — Adaptateur In-World pour Langage Ultime (LU).

Commandements AGIseed respectés :
1. Flexible : Hyper-paramétrable via LUInWorldConfig.
2. Modulaire : Découplé du moteur physique Biosphere3D.
3. Haute Performance : Vectorisation NumPy pour les projections et calculs de distance.
4. Scalable : Gestion multi-agents sans blocage, traducteurs par paire ou traducteur de swarm.
5. Transparent : Connexion à LULatticeMemory et LUHumanExplainer pour auditabilité.
9. Stabilité Numérique : Normalisation L2, epsilon anti-division par zéro, clipping.
15. Non-Régression : Désactivé par défaut via enable_lu_communication=False.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from src.metaprog.lu_auto_translator import MutualLatentTranslator, AutoTranslatorConfig
from src.metaprog.lu_state_bridge import LUStateBridge
from src.metaprog.lu_human_explainer import LUHumanExplainer
from src.metaprog.lu_algebra import (
    LUCompositionalGrammar,
    LUAlgebraConfig,
    grassmann_distance,
    orthonormal_subspace,
    drift_subspace,
    linear_cka,
    match_contract_trade,
    cosine_similarity,
    compute_contract_breach,
    update_agent_reputation,
    reputation_trust_score,
    decay_reputation_towards_neutral,
    verify_consortium_agreement,
    decay_inscription_geological,
    encode_fractional_power_number,
    decode_fractional_power_number,
    validate_recipe_ratio,
    derive_macro_role,
    verify_propositional_consistency,
    LatentNeuralVM,
    apply_latent_do_operator,
    compute_latent_causal_effect,
    spherical_weiszfeld_bft_consensus,
    LatentProgramSynthesizer,
    apply_temporal_operator,
    solve_latent_analogy,
    verify_analogy_quality,
    ConnectomeCompiler,
    verify_hoare_safety,
    LatentDreamEngine,
    EpistemicUncertaintyEngine,
    spherical_sinkhorn_barycenter,
    LatentReactionDiffusionPDE,
    HyperConnectomeSynthesizer,
    AutopoieticSingularityEngine,
    HolographicBoundaryProjector,
)
from src.metaprog.lu_symbolic_bridge import (
    MultiTribalTranslator,
    FederalDiplomaticBridge,
    LUNoosphereField,
    LUEpistemicInsight,
    LUNoogeneticField,
    LUHyperConnectome,
    LUAutopoieticSingularity,
    LUHolographicBoundary,
)
from src.agents.dream_replay import SharedDreamExperience, SharedDreamPool
from src.graph_rag.async_logger import logger


ROLE_SCOUT = "SCOUT"
ROLE_CRAFTER = "CRAFTER"
ROLE_HUNTER = "HUNTER"
ALL_ROLES = [ROLE_SCOUT, ROLE_HUNTER, ROLE_CRAFTER]


@dataclass
class InscriptionStone:
    """Stèle fixe gravée dans le substrat physique de la biosphère (Phase 6 M2)."""
    id: str
    x: float
    y: float
    z: float
    topic: str
    content_vector: np.ndarray
    author_id: str
    creation_tick: int
    read_count: int = 0
    durability: float = 1.0


@dataclass
class SlateTablet:
    """Tablette d'argile ou ardoise portable transportable dans l'inventaire (Phase 6 M2)."""
    id: str
    topic: str
    content_vector: np.ndarray
    owner_id: str
    creation_tick: int
    read_count: int = 0
    balance_entries: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FederalMonument:
    """Monument fédéral inter-mondes (LU Phase 7 M2, Phase 8 M2, Phase 9 M2)."""
    id: str
    x: float
    y: float
    z: float
    ratified_treaties: List[Dict[str, Any]] = field(default_factory=list)
    meta_rules: List[Dict[str, Any]] = field(default_factory=list)
    constitution_vector: Optional[np.ndarray] = None
    contradiction_rejections_count: int = 0
    smart_contracts: List[Dict[str, Any]] = field(default_factory=list)
    active_escrows: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Phase 9 M2 : Programmes synthétisés, contrats temporels & analogies
    synthesized_programs: List[Dict[str, Any]] = field(default_factory=list)
    temporal_escrows: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    analogies_repository: List[Dict[str, Any]] = field(default_factory=list)
    # Phase 10 M2 : Auto-compilation récursive de connectome & preuves de Hoare
    self_evolution_altar: Dict[str, Any] = field(default_factory=dict)
    self_compiled_mutations: List[Dict[str, Any]] = field(default_factory=list)
    hoare_proofs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LUInWorldConfig:
    """Configuration hyper-paramétrable pour le sous-système de communication continue LU in-world."""
    latent_dim: int = 16
    noise_level: float = 0.05
    hear_radius: int = 3
    alignment_threshold: float = 0.70
    alignment_reward: float = 0.5
    referential_bonus: float = 1.0
    pack_coordination: bool = True
    co_train_lr: float = 0.02
    warmstart_spectral: bool = True
    max_history_tokens: int = 50
    signal_metabolic_cost: float = 0.05
    cooperative_prey_multiplier: float = 2.0
    role_specialization: bool = True
    emergent_roles: bool = False
    campfire_cultural_boost: bool = True
    enable_multi_hop: bool = True
    max_hops: int = 2
    relay_decay: float = 0.80
    relay_confidence_threshold: float = 0.60
    enable_compositional_grammar: bool = True
    # Phase 3 : Theory of Mind (ToM) & Consensus Délibératif
    enable_tom: bool = True
    tom_pragmatics_weight: float = 0.50
    tom_redundancy_threshold: float = 0.85
    tom_silence_metabolic_saving: float = 0.04
    enable_deliberation: bool = True
    deliberation_rounds: int = 3
    deliberation_consensus_threshold: float = 0.65
    # Phase 4 : Spéciation Dialectale, Contrats Latents & Troc Décentralisé
    enable_dialects: bool = True
    dialect_drift_rate: float = 0.05
    enable_trade_contracts: bool = True
    trade_agreement_threshold: float = 0.60
    market_radius: int = 4
    market_point: Tuple[int, int] = (8, 8)
    # Phase 5 : Gouvernance Juridique, Arbitrage & Consortiums Métallurgiques
    enable_governance: bool = True
    trust_alpha: float = 0.25
    breach_distance_threshold: float = 0.50
    embargo_reputation_threshold: float = 0.40
    embargo_duration_ticks: int = 15
    reputation_decay_rate: float = 0.02
    enable_consortium_contracts: bool = True
    consortium_agreement_threshold: float = 0.40
    # Phase 6 : Écriture Stigmargique, Arithmétique Vectorielle & Transmission Scientifique
    enable_writing: bool = True
    enable_arithmetic: bool = True
    read_inscription_radius: float = 3.5
    engrave_metabolic_cost: float = 0.08
    inscription_geological_decay_std: float = 1e-4
    epigenetic_prior_boost: float = 5.0
    epigenetic_age_limit: int = 50
    # Phase 7 : Métalangage RSI, Preuve Formelle & Fédération Diplomatique
    enable_diplomacy: bool = True
    enable_meta_grammar: bool = True
    federation_monument_x: float = 6.0
    federation_monument_y: float = 6.0
    contradiction_threshold: float = -0.50
    treaty_cooperation_bonus: float = 2.0
    # Phase 8 : Machine Virtuelle Latente, Do-Calculus & Consensus BFT
    enable_neural_vm: bool = True
    enable_causal_inference: bool = True
    enable_bft_consensus: bool = True
    neural_vm_activation_threshold: float = 0.35
    causal_ate_threshold: float = 0.40
    byzantine_tolerance_ratio: float = 0.33
    escrow_release_energy_bonus: float = 3.0
    # Phase 9 : Synthèse de Programmes Latents, LTL & Analogies Multivers
    enable_program_synthesis: bool = True
    enable_ltl_temporal_logic: bool = True
    enable_analogy_transfer: bool = True
    temporal_horizon_ticks: int = 5
    analogy_fidelity_threshold: float = 0.50
    program_execution_energy_bonus: float = 4.0
    # Phase 10 : Auto-Compilation Récursive de Connectome, Logique de Hoare & Singularité Seed AI
    enable_self_compilation: bool = True
    enable_hoare_verification: bool = True
    self_evolution_energy_bonus: float = 10.0
    hoare_safety_threshold: float = 0.65
    # Phase 11 : Méta-Simulation Contrefactuelle, Rêve Sémantique Partagé & Délibération au Feu
    enable_counterfactual_dreaming: bool = True
    dream_rollout_horizon: int = 10
    dream_predictive_bonus: float = 6.0
    dream_min_gain_threshold: float = 0.05
    # Phase 12 : La Noosphère Latente, Conscience Collective Trans-Mondes & Transport de Wasserstein
    enable_noosphere_grid: bool = True
    resonance_decay: float = 0.10
    epistemic_confidence_threshold: float = 0.45
    sinkhorn_regularization: float = 0.05
    noosphere_dividend: float = 8.0
    # Phase 13 : Morphogenèse Noogénétique, Réaction-Diffusion Latente & Hyper-Connectome Distribué
    enable_reaction_diffusion_pde: bool = True
    pde_diffusion_coef: float = 0.15
    pde_reaction_rate: float = 0.25
    enable_hyperconnectome_distillation: bool = True
    hyperconnectome_learning_rate: float = 0.10
    noogenetic_rebirth_bonus: float = 12.0
    # Phase 14 : Singularité Autopoïétique, Méta-Langage Holographique Universel & Clôture Téléologique
    enable_autopoietic_singularity: bool = True
    holographic_projection_ratio: float = 0.40
    teleological_attractor_force: float = 0.25
    autopoietic_entropy_threshold: float = 0.65
    singularity_dividend_bonus: float = 20.0


class LUInWorldAdapter:
    """
    Gère la communication continue par Gigatokens latents entre agents dans la simulation Biosphere3D.
    Permet l'émergence d'une coordination causale continue sans le goulot d'étranglement discret (1-of-4).
    """

    def __init__(self, world: Any, config: Optional[LUInWorldConfig] = None):
        self.world = world
        self.config = config or LUInWorldConfig()
        self.dim = self.config.latent_dim
        
        # Traducteur latent partagé configuré selon AutoTranslatorConfig
        self.translator_config = AutoTranslatorConfig(
            dim_a=self.dim,
            dim_b=self.dim,
            learning_rate=self.config.co_train_lr,
            cycle_lambda=1.0,
            align_lambda=1.0,
        )
        self.shared_translator = MutualLatentTranslator(self.translator_config)
        if self.config.warmstart_spectral:
            self.shared_translator.W_ab = np.eye(self.dim, dtype=np.float64)
            self.shared_translator.W_ba = np.eye(self.dim, dtype=np.float64)
        self.explainer = LUHumanExplainer()
        
        # Matrices de projection agent -> espace latent
        # Permet de projeter l'état interne/perçu de chaque agent dans sa variété latente
        self.agent_projections: Dict[str, np.ndarray] = {}
        
        # Métriques et statistiques in-world
        self.total_transmissions: int = 0
        self.successful_alignments: int = 0
        self.pack_coordinations_count: int = 0
        self.cooperative_hunts_count: int = 0
        self.recipes_transmitted: int = 0
        self.campfire_transmissions_count: int = 0
        self.multi_hop_relays_count: int = 0
        self.total_metabolic_cost: float = 0.0
        self.recent_tokens: List[np.ndarray] = []

        # Théorie de l'Esprit Latente (ToM) & Délibération (Phase 3)
        self.agent_tom_beliefs: Dict[str, Dict[str, np.ndarray]] = {}
        self.tom_silences_count: int = 0
        self.tom_energy_saved: float = 0.0
        self.deliberation_events_count: int = 0
        self.deliberation_consensus_count: int = 0
        self.last_deliberated_consensus: Optional[np.ndarray] = None

        # Moteur de compositionnalité vectorielle (Phase 2 & 3)
        if self.config.enable_compositional_grammar:
            self.grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=self.dim))
        else:
            self.grammar = None

        # Phase 4 : Spéciation Dialectale, Contrats Latents & Troc
        self.clan_subspaces: Dict[str, np.ndarray] = {}
        self.multi_translator = MultiTribalTranslator(dim=self.dim, k=4)
        self.contracts_settled_count: int = 0
        self.trade_transfers_count: int = 0
        self.recent_contracts: List[Dict[str, Any]] = []

        # Phase 5 : Gouvernance Juridique, Arbitrage & Consortiums Métallurgiques
        self.agent_reputations: Dict[str, np.ndarray] = {}
        self.agent_embargos: Dict[str, int] = {}
        self.sanctions_count: int = 0
        self.consortiums_settled_count: int = 0
        self.metal_tools_produced_count: int = 0
        self.recent_sanctions: List[Dict[str, Any]] = []
        self.recent_consortiums: List[Dict[str, Any]] = []
        self.trust_reference_vector: np.ndarray = (
            self.grammar.ROLE_TRUST if self.grammar is not None
            else (np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim))
        )
        self.neutral_reference_vector: np.ndarray = self.trust_reference_vector.copy()

        # Phase 6 : Écriture Stigmargique, Tablettes & Transmission Scientifique
        self.steles: Dict[str, InscriptionStone] = {}
        self.tablets: Dict[str, SlateTablet] = {}
        self.steles_engraved_count: int = 0
        self.steles_read_count: int = 0
        self.epigenetic_boosts_count: int = 0
        self.arithmetic_ledger_entries_count: int = 0
        self.recent_scriptures: List[Dict[str, Any]] = []
        if self.config.enable_writing:
            self._init_foundational_steles()

        # Phase 7 : Métalangage, Preuve Formelle & Monument Fédéral
        self.federal_monument: Optional[FederalMonument] = None
        self.diplomatic_bridge: FederalDiplomaticBridge = FederalDiplomaticBridge(seed=getattr(self.config, 'seed', 42))
        self.treaties_ratified_count: int = 0
        self.meta_rules_compiled_count: int = 0
        self.constitutional_protections_count: int = 0
        self.recent_treaties: List[Dict[str, Any]] = []
        # Phase 8 : Machine Virtuelle Latente, Do-Calculus & Consensus BFT
        self.neural_vm = LatentNeuralVM(dim=self.dim, config=getattr(self.grammar, "config", None))
        self.smart_contracts_registered_count: int = 0
        self.smart_contracts_executed_count: int = 0
        self.causal_experiments_count: int = 0
        self.causal_hypotheses_validated_count: int = 0
        self.bft_consensus_events_count: int = 0
        self.bft_byzantine_mitigated_count: int = 0
        # Phase 9 : Synthèse de Programmes Latents, LTL & Analogies Multivers
        self.program_synthesizer = LatentProgramSynthesizer(dim=self.dim, config=getattr(self.grammar, "config", None))
        self.synthesized_programs_count: int = 0
        self.programs_synthesized_count: int = 0
        self.programs_executed_count: int = 0
        self.temporal_clauses_evaluated_count: int = 0
        self.temporal_escrows_released_count: int = 0
        self.analogy_transfers_count: int = 0
        # Phase 10 : Auto-Compilation Récursive de Connectome & Logique de Hoare
        self.connectome_compiler = ConnectomeCompiler(dim=self.dim, config=getattr(self.grammar, "config", None))
        self.self_compiled_mutations_count: int = 0
        self.hoare_proofs_verified_count: int = 0
        self.hoare_rejections_count: int = 0
        self.connectome_evolutions_applied_count: int = 0
        # Phase 11 : Méta-Simulation Contrefactuelle, Rêve Sémantique Partagé & Conseil du Feu
        self.dream_engine = LatentDreamEngine(dim=self.dim, config=getattr(self.grammar, "config", None))
        self.shared_dream_pool = SharedDreamPool(capacity=64)
        self.shared_dreams_count: int = 0
        self.dreams_ratified_count: int = 0
        self.counterfactual_rollouts_count: int = 0
        self.counterfactual_gains_total: float = 0.0
        self.recent_shared_dreams: List[Dict[str, Any]] = []
        # Phase 12 : La Noosphère Latente, Conscience Collective Trans-Mondes & Transport de Wasserstein
        self.epistemic_engine = EpistemicUncertaintyEngine(dim=self.dim, config=getattr(self.grammar, "config", None))
        self.noosphere_resonance_grid: Optional[np.ndarray] = None
        self.noosphere_broadcasts_count: int = 0
        self.epistemic_evaluations_count: int = 0
        self.high_uncertainty_interventions_count: int = 0
        self.synarchic_councils_count: int = 0
        self.synarchic_ratifications_count: int = 0
        self.recent_noosphere_broadcasts: List[Dict[str, Any]] = []
        # Phase 13 : Morphogenèse Noogénétique, Réaction-Diffusion & Hyper-Connectome Fédéral
        self.pde_engine = LatentReactionDiffusionPDE(
            grid_size=16,
            dim=self.dim,
            diffusion_coef=float(self.config.pde_diffusion_coef),
            reaction_rate=float(self.config.pde_reaction_rate),
            grammar=self.grammar,
            seed=getattr(self.config, "seed", 42),
        )
        self.hyperconnectome_synthesizer = HyperConnectomeSynthesizer(
            dim=self.dim,
            connectome_size=16,
            grammar=self.grammar,
            seed=getattr(self.config, "seed", 42),
        )
        self.pde_steps_count: int = 0
        self.hyperconnectome_updates_count: int = 0
        self.noogenetic_distillations_count: int = 0
        self.recent_pde_snapshots: List[Dict[str, Any]] = []
        # Phase 14 : Singularité Autopoïétique, Méta-Langage Holographique & Clôture Téléologique
        self.autopoietic_engine = AutopoieticSingularityEngine(
            dim=self.dim,
            grammar=self.grammar,
            seed=getattr(self.config, "seed", 42),
            gamma=0.25,
            kappa=float(self.config.teleological_attractor_force),
        )
        self.holographic_projector = HolographicBoundaryProjector(
            dim=self.dim,
            boundary_dim=16,
            grammar=self.grammar,
            seed=getattr(self.config, "seed", 42),
        )
        self.autopoietic_steps_count: int = 0
        self.holographic_projections_count: int = 0
        self.teleological_convergences_count: int = 0
        self.singularity_dividends_count: int = 0
        self.recent_autopoietic_snapshots: List[Dict[str, Any]] = []
        if getattr(self.config, "enable_diplomacy", True):
            self._init_federal_monument()

    def bootstrap_federal_monument(self) -> None:
        """Alias public pour initialiser ou réinitialiser le FederalMonument."""
        self._init_federal_monument()

    def _init_foundational_steles(self) -> None:
        """Initialise les stèles fondatrices in-world (Académie Métallurgique et Carte des Ressources)."""
        if self.grammar is None:
            return

        # 1. Stèle Scientifique : Recette de métallurgie du Haut-Fourneau (3 Wood + 1 Ore -> 1 IronPickaxe)
        rng_w = np.random.default_rng(abs(hash("WOOD")) % (2**31 - 1))
        v_wood = self.grammar._generate_canonical_unit_vector(rng_w)
        rng_o = np.random.default_rng(abs(hash("ORE")) % (2**31 - 1))
        v_ore = self.grammar._generate_canonical_unit_vector(rng_o)
        rng_p = np.random.default_rng(abs(hash("STEEL")) % (2**31 - 1))
        v_tool = self.grammar._generate_canonical_unit_vector(rng_p)

        recipe_vec = self.grammar.compose_recipe_ratio(
            inputs=[(3.0, v_wood), (1.0, v_ore)],
            outputs=[(1.0, v_tool)]
        )
        rng_topic = np.random.default_rng(abs(hash("SCIENCE")) % (2**31 - 1))
        v_science = self.grammar._generate_canonical_unit_vector(rng_topic)
        inscription_metallurgy = self.grammar.compose_inscription(v_science, recipe_vec)

        stele_metal = InscriptionStone(
            id="stele_metallurgy_academy",
            x=float(self.config.market_point[0]),
            y=float(self.config.market_point[1]),
            z=0.0,
            topic="SCIENCE",
            content_vector=inscription_metallurgy,
            author_id="ANCIENT_FOUNDER",
            creation_tick=0,
            read_count=0,
            durability=1.0,
        )
        self.steles[stele_metal.id] = stele_metal

        # 2. Stèle Géologique : Carte des gisements & du Haut-Fourneau
        rng_granary = np.random.default_rng(abs(hash("GRANARY")) % (2**31 - 1))
        v_granary = self.grammar._generate_canonical_unit_vector(rng_granary)
        inscription_map = self.grammar.compose_inscription(v_science, v_granary)
        stele_map = InscriptionStone(
            id="stele_geology_map",
            x=float(self.config.market_point[0] - 2),
            y=float(self.config.market_point[1] - 2),
            z=0.0,
            topic="RESOURCE_MAP",
            content_vector=inscription_map,
            author_id="ANCIENT_CARTOGRAPHER",
            creation_tick=0,
            read_count=0,
            durability=1.0,
        )
        self.steles[stele_map.id] = stele_map

    def _init_federal_monument(self) -> None:
        """
        Initialise le Monument Fédéral Inter-Mondes au cœur de la biosphère (LU Phase 7 M2).
        Grave la Constitution Fédérale et le traité fondateur de non-agression et commerce pacifique.
        """
        if self.grammar is None:
            return

        # Clause constitutionnelle fondatrice : PAIX et COMMERCE pacifique
        rng_peace = np.random.default_rng(abs(hash("PEACE")) % (2**31 - 1))
        v_peace = self.grammar._generate_canonical_unit_vector(rng_peace)
        rng_fed = np.random.default_rng(abs(hash("FEDERATION")) % (2**31 - 1))
        v_fed = self.grammar._generate_canonical_unit_vector(rng_fed)

        treaty_clause = self.grammar.compose(
            subject=v_fed,
            predicate=self.grammar.ROLE_TRUST,
            target=v_peace
        )

        founder_sigs = [
            self.grammar._generate_canonical_unit_vector(np.random.default_rng(101)),
            self.grammar._generate_canonical_unit_vector(np.random.default_rng(202)),
            self.grammar._generate_canonical_unit_vector(np.random.default_rng(303)),
        ]

        constitution_vec = self.grammar.compose_federal_treaty(treaty_clause, founder_sigs)

        self.federal_monument = FederalMonument(
            id="monument_federal_central",
            x=float(getattr(self.config, "federation_monument_x", 6.0)),
            y=float(getattr(self.config, "federation_monument_y", 6.0)),
            z=0.0,
            ratified_treaties=[{
                "treaty_name": "TREATY_FOUNDING_CONSTITUTION",
                "clause": "PEACE_AND_COMMERCE",
                "signatories": ["WORLD1_TRIBE", "WORLD2_FARMERS", "WORLD3_SMELTERS"],
                "tick": 0,
            }],
            meta_rules=[{
                "rule_name": "RULE_CONSTITUTIONAL_SUPREMACY",
                "input_role": "ROLE_LAW",
                "operator": "SUPREME",
                "output_role": "ROLE_PEACE",
                "tick": 0,
            }],
            constitution_vector=constitution_vec,
            contradiction_rejections_count=0
        )

    def ratify_federal_treaty(
        self,
        agent_a: Dict[str, Any],
        agent_b: Dict[str, Any],
        treaty_name: str = "TREATY_PEACE_AND_COMMERCE",
        clause_vector: Optional[np.ndarray] = None
    ) -> bool:
        """
        Ratification multilatérale d'un traité fédéral entre deux agents / clans (LU Phase 7 M2).
        Les signataires scellent un pacte constitutionnel de non-agression et bénéficient
        d'un bonus de coopération calorique.
        """
        if self.federal_monument is None or self.grammar is None:
            return False

        id_a = str(agent_a.get("id", "agent_a"))
        id_b = str(agent_b.get("id", "agent_b"))

        proj_a = self._get_agent_projection(id_a, 8)
        sig_a = proj_a[0] / (np.linalg.norm(proj_a[0]) + 1e-12)

        proj_b = self._get_agent_projection(id_b, 8)
        sig_b = proj_b[0] / (np.linalg.norm(proj_b[0]) + 1e-12)

        if clause_vector is None:
            rng_p = np.random.default_rng(abs(hash("PEACE")) % (2**31 - 1))
            clause_vector = self.grammar._generate_canonical_unit_vector(rng_p)

        treaty_vec = self.grammar.compose_federal_treaty(clause_vector, [sig_a, sig_b])

        record = {
            "treaty_name": treaty_name,
            "agent_a": id_a,
            "agent_b": id_b,
            "vector": treaty_vec,
            "tick": getattr(self.world, "ticks", 0)
        }
        self.federal_monument.ratified_treaties.append(record)
        self.recent_treaties.append(record)
        self.treaties_ratified_count += 1

        if "federal_treaties" not in agent_a:
            agent_a["federal_treaties"] = set()
        if "federal_treaties" not in agent_b:
            agent_b["federal_treaties"] = set()
        agent_a["federal_treaties"].add(id_b)
        agent_b["federal_treaties"].add(id_a)

        bonus = float(getattr(self.config, "treaty_cooperation_bonus", 2.0))
        agent_a["energy"] = min(100.0, float(agent_a.get("energy", 0.0)) + bonus)
        agent_b["energy"] = min(100.0, float(agent_b.get("energy", 0.0)) + bonus)
        return True

    def propose_meta_rule_to_monument(
        self,
        proposer_id: str,
        rule_name: str,
        input_role_vec: np.ndarray,
        operator_vec: np.ndarray,
        output_role_vec: np.ndarray,
    ) -> Tuple[bool, str]:
        """
        Soumet une macro-règle sémantique (RSI Grammatical) pour gravure sur le FederalMonument.
        Exécute d'abord une preuve de consistance vectorielle : si la règle contredit la Constitution
        ou les lois existantes (antipodalité vectorielle < threshold), elle est rejetée formellement.
        """
        if self.federal_monument is None or self.grammar is None:
            return False, "FEDERAL_MONUMENT_UNAVAILABLE"

        rng_rule = np.random.default_rng(abs(hash(rule_name)) % (2**31 - 1))
        rule_vec = self.grammar._generate_canonical_unit_vector(rng_rule)

        meta_rule_vec = self.grammar.compose_meta_rule(
            rule_name=rule_vec,
            input_role=input_role_vec,
            operator=operator_vec,
            output_role=output_role_vec
        )

        threshold = float(getattr(self.config, "contradiction_threshold", -0.50))
        # Extraire la clause constitutionnelle fondamentale du monument
        const_clause = self.grammar.extract_treaty_clause(self.federal_monument.constitution_vector)
        statements_to_check = [const_clause, output_role_vec]
        is_consistent, min_sim, conflicts = verify_propositional_consistency(
            statements=statements_to_check,
            contradiction_threshold=threshold
        )

        if not is_consistent:
            self.federal_monument.contradiction_rejections_count += 1
            return False, f"CONTRADICTION_REJECTED (sim={min_sim:.3f})"

        entry = {
            "rule_name": rule_name,
            "proposer_id": proposer_id,
            "vector": meta_rule_vec,
            "tick": getattr(self.world, "ticks", 0)
        }
        self.federal_monument.meta_rules.append(entry)
        self.meta_rules_compiled_count += 1
        return True, "META_RULE_RATIFIED"

    # =========================================================================
    # Méthodes Smart Contracts In-World, Causalité & Consensus BFT (Phase 8 M2)
    # =========================================================================

    def register_inworld_smart_contract(
        self,
        creator_id: str,
        contract_id: str,
        from_state_label: str,
        trigger_label: str,
        to_state_label: str,
        escrow_energy: float = 3.0,
        activation_threshold: float = 0.35
    ) -> bool:
        """
        Enregistre un Smart Contract programmable in-world au FederalMonument (LU Phase 8 M2).
        Configure une transition d'état d'escrow vectorielle dans la Neural VM.
        """
        if self.grammar is None:
            return False

        def get_concept_vec(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in ["STEEL", "TOOL", "PICKAXE"] and hasattr(self.grammar, "ROLE_FORGE_OUTPUT"):
                return self.grammar.ROLE_FORGE_OUTPUT
            if key in ["LAW"] and hasattr(self.grammar, "ROLE_TRUST"):
                return self.grammar.ROLE_TRUST
            if key in ["WOOD", "COAL"] and hasattr(self.grammar, "ROLE_SUPPLIER_WOOD"):
                return self.grammar.ROLE_SUPPLIER_WOOD
            if key in ["FOOD", "FRUIT"] and hasattr(self.grammar, "ROLE_SUPPLIER_FOOD"):
                return self.grammar.ROLE_SUPPLIER_FOOD
            if key in ["ORE", "IRON"] and hasattr(self.grammar, "ROLE_SMELTER_ORE"):
                return self.grammar.ROLE_SMELTER_ORE
            rng_c = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng_c)

        v_from = get_concept_vec(from_state_label)
        v_trig = get_concept_vec(trigger_label)
        v_to = get_concept_vec(to_state_label)

        rng_esc = np.random.default_rng(abs(hash("ESCROW")) % (2**31 - 1))
        v_esc = self.grammar._generate_canonical_unit_vector(rng_esc)

        # Si premier contrat enregistré, initialiser l'état courant de la VM
        if self.federal_monument is not None and len(self.federal_monument.smart_contracts) == 0:
            self.neural_vm.set_state(v_from)

        contract_vec = self.neural_vm.register_transition(
            from_state=v_from,
            trigger_vector=v_trig,
            to_state=v_to,
            escrow_action=v_esc,
            threshold=activation_threshold,
            contract_id=contract_id
        )

        record = {
            "contract_id": contract_id,
            "creator_id": creator_id,
            "from_state": from_state_label.upper(),
            "trigger": trigger_label.upper(),
            "to_state": to_state_label.upper(),
            "escrow_energy": escrow_energy,
            "vector": contract_vec,
            "tick": getattr(self.world, "ticks", 0)
        }

        if self.federal_monument is not None:
            self.federal_monument.smart_contracts.append(record)
            self.federal_monument.active_escrows[contract_id] = {
                "creator_id": creator_id,
                "energy_pool": escrow_energy,
                "is_released": False
            }

        self.smart_contracts_registered_count += 1
        return True

    def execute_inworld_smart_contract(
        self,
        agent: Dict[str, Any],
        trigger_vector: np.ndarray,
        contract_id: Optional[str] = None
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Tente d'exécuter un Smart Contract en fournissant un Gigatoken d'entrée (Phase 8 M2).
        Si la condition est satisfaite, l'escrow énergétique est libéré vers l'agent.
        """
        if not getattr(self.config, "enable_neural_vm", True):
            return False, 0.0, None

        thresh = float(getattr(self.config, "neural_vm_activation_threshold", 0.35))
        new_state, transitioned, escrow_action, sim, triggered_cid = self.neural_vm.step(
            input_vector=trigger_vector,
            custom_threshold=thresh
        )

        if transitioned and triggered_cid:
            bonus = float(getattr(self.config, "escrow_release_energy_bonus", 3.0))
            agent["energy"] = min(100.0, float(agent.get("energy", 0.0)) + bonus)
            self.smart_contracts_executed_count += 1

            if self.federal_monument is not None and triggered_cid in self.federal_monument.active_escrows:
                escrow_info = self.federal_monument.active_escrows[triggered_cid]
                escrow_info["is_released"] = True

            return True, sim, triggered_cid

        return False, sim, None

    def conduct_causal_experiment(
        self,
        agent: Dict[str, Any],
        cause_label: str,
        effect_label: str,
        n_trials: int = 10
    ) -> Dict[str, Any]:
        """
        Conduit une expérience scientifique causale active (Do-Calculus - Phase 8 M2).
        Génère des états factuels do(Cause) et contrefactuels do(¬Cause) dans la biosphère.
        Si l'ATE dépasse le seuil, l'agent valide une loi causale et reçoit un boost calorique.
        """
        if self.grammar is None:
            return {"validated": False, "ate": 0.0, "r_obs": 0.0}

        rng_c = np.random.default_rng(abs(hash(cause_label.upper())) % (2**31 - 1))
        v_cause = self.grammar._generate_canonical_unit_vector(rng_c)

        rng_e = np.random.default_rng(abs(hash(effect_label.upper())) % (2**31 - 1))
        v_effect = self.grammar._generate_canonical_unit_vector(rng_e)

        factuals = []
        counterfactuals = []
        rng = np.random.default_rng(getattr(self.world, "ticks", 42))

        for _ in range(n_trials):
            base_state = rng.standard_normal(self.dim).astype(np.float32)
            base_state /= (np.linalg.norm(base_state) + 1e-12)

            fact = apply_latent_do_operator(base_state, v_cause)
            fact_y = 0.5 * fact + 0.5 * v_effect
            fact_y /= (np.linalg.norm(fact_y) + 1e-12)
            factuals.append(fact_y)

            cf = apply_latent_do_operator(base_state, -v_cause)
            counterfactuals.append(cf)

        ate, r_obs, disc = compute_latent_causal_effect(
            factual_states=factuals,
            counterfactual_states=counterfactuals,
            treatment_variable=v_cause,
            outcome_variable=v_effect
        )

        thresh = float(getattr(self.config, "causal_ate_threshold", 0.40))
        validated = (ate >= thresh)
        self.causal_experiments_count += 1

        if validated:
            self.causal_hypotheses_validated_count += 1
            agent["energy"] = min(100.0, float(agent.get("energy", 0.0)) + 4.0)

        return {
            "validated": validated,
            "ate": round(ate, 4),
            "r_obs": round(r_obs, 4),
            "discrepancy": round(disc, 4),
            "cause": cause_label.upper(),
            "effect": effect_label.upper(),
        }

    def aggregate_bft_pack_deliberation(
        self,
        agents: List[Dict[str, Any]],
        byzantine_ratio: Optional[float] = None
    ) -> Tuple[np.ndarray, float, List[str]]:
        """
        Agrège les intentions délibératives d'une meute via le consensus sphérique de Weiszfeld BFT (Phase 8 M2).
        Isole automatiquement les agents byzantins ou corrompus.
        """
        if len(agents) < 2:
            dummy = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)
            return dummy, 1.0, []

        ratio = byzantine_ratio if byzantine_ratio is not None else float(getattr(self.config, "byzantine_tolerance_ratio", 0.33))
        vectors = []
        for ag in agents:
            z = ag.get("lu_latent")
            if z is None:
                z = self.encode_agent_latent(ag)
            vectors.append(z)

        consensus_vec, score, byzantine_indices = spherical_weiszfeld_bft_consensus(
            vectors=vectors,
            max_byzantine_ratio=ratio
        )

        self.bft_consensus_events_count += 1
        byzantine_ids = [str(agents[idx].get("id")) for idx in byzantine_indices]
        if byzantine_ids:
            self.bft_byzantine_mitigated_count += len(byzantine_ids)

        return consensus_vec, score, byzantine_ids

    # =========================================================================
    # Méthodes Synthèse de Programmes, LTL & Analogies Multivers (Phase 9 M2)
    # =========================================================================

    def register_temporal_smart_contract(
        self,
        creator_id: str,
        contract_id: str,
        trigger_label: str,
        target_label: str,
        delay_ticks: int = 5,
        escrow_energy: float = 4.0,
        condition_type: str = "ALWAYS"
    ) -> bool:
        """
        Enregistre un Smart Contract temporel LTL au FederalMonument (Phase 9 M2).
        L'escrow est libéré uniquement si la clause temporelle (ex: ALWAYS condition)
        est vérifiée tout au long de l'horizon de délai.
        """
        if self.grammar is None:
            return False

        rng_trig = np.random.default_rng(abs(hash(trigger_label.upper())) % (2**31 - 1))
        v_trig = self.grammar._generate_canonical_unit_vector(rng_trig)

        rng_tgt = np.random.default_rng(abs(hash(target_label.upper())) % (2**31 - 1))
        v_tgt = self.grammar._generate_canonical_unit_vector(rng_tgt)

        clause_token = self.grammar.compose_temporal_clause(v_trig, operator_type=condition_type, horizon=delay_ticks)

        record = {
            "contract_id": contract_id,
            "creator_id": creator_id,
            "trigger_label": trigger_label.upper(),
            "target_label": target_label.upper(),
            "trigger_vector": v_trig,
            "target_vector": v_tgt,
            "delay_ticks": delay_ticks,
            "remaining_ticks": delay_ticks,
            "escrow_energy": escrow_energy,
            "condition_type": condition_type.upper(),
            "clause_token": clause_token,
            "trajectory_history": [],
            "is_released": False,
            "creation_tick": getattr(self.world, "ticks", 0)
        }

        if self.federal_monument is not None:
            self.federal_monument.temporal_escrows[contract_id] = record

        self.temporal_clauses_evaluated_count += 1
        return True

    def step_temporal_escrows(self, agents: List[Dict[str, Any]]) -> int:
        """
        Met à jour les contrats temporels d'escrow actifs :
        Décrémente les ticks restants, évalue le prédicat temporel LTL et
        libère l'énergie si l'échéance est atteinte sans violation.
        """
        if not getattr(self.config, "enable_ltl_temporal_logic", True):
            return 0
        if self.federal_monument is None or not self.federal_monument.temporal_escrows:
            return 0

        released_count = 0
        for cid, contract in list(self.federal_monument.temporal_escrows.items()):
            if contract.get("is_released", False):
                continue

            mon_x, mon_y = self.federal_monument.x, self.federal_monument.y
            near_monument = [ag for ag in agents if (abs(ag.get("x", 0) - mon_x) + abs(ag.get("y", 0) - mon_y)) <= 4]
            if near_monument:
                z_list = []
                for ag in near_monument:
                    if ag.get("lu_latent") is not None:
                        z_list.append(ag["lu_latent"])
                    else:
                        z_list.append(self.encode_agent_latent(ag))
                mean_z = np.mean(z_list, axis=0)
                mean_z = (mean_z / (np.linalg.norm(mean_z) + 1e-12)).astype(np.float32)
            else:
                mean_z = contract["trigger_vector"].copy()

            contract["trajectory_history"].append(mean_z)
            contract["remaining_ticks"] -= 1

            if contract["remaining_ticks"] <= 0:
                satisfied, score, _ = apply_temporal_operator(
                    trajectory=contract["trajectory_history"],
                    predicate=contract["trigger_vector"],
                    operator_type=contract["condition_type"],
                    horizon=contract["delay_ticks"],
                    threshold=0.30
                )
                if satisfied:
                    contract["is_released"] = True
                    bonus = float(contract["escrow_energy"])
                    if near_monument:
                        per_agent = bonus / len(near_monument)
                        for ag in near_monument:
                            ag["energy"] = min(100.0, float(ag.get("energy", 0.0)) + per_agent)
                    self.temporal_escrows_released_count += 1
                    released_count += 1

        return released_count

    def synthesize_and_register_program(
        self,
        creator_id: str,
        program_id: str,
        entry_label: str = "ENTRY",
        loop_label: Optional[str] = None,
        branch_label: Optional[str] = None,
        term_label: Optional[str] = None,
        lipschitz_l: float = 0.85,
        loop_operator: Optional[str] = None,
        branch_condition: Optional[str] = None,
        terminal_state: Optional[str] = None
    ) -> bool:
        """
        Synthétise et enregistre un macro-programme latent au FederalMonument (Phase 9 M2).
        """
        if self.grammar is None:
            return False

        loop_name = loop_label or loop_operator or "LOOP"
        branch_name = branch_label or branch_condition or "BRANCH"
        term_name = term_label or terminal_state or "TERMINAL"

        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        v_entry = get_v(entry_label)
        v_loop = get_v(loop_name)
        v_branch = get_v(branch_name)
        v_term = get_v(term_name)

        prog_token = self.program_synthesizer.synthesize_program(
            entry_state=v_entry,
            loop_operator=v_loop,
            branch_condition=v_branch,
            terminal_state=v_term,
            lipschitz_constant=lipschitz_l,
            program_id=program_id
        )

        record = {
            "program_id": program_id,
            "creator_id": creator_id,
            "entry_label": entry_label.upper(),
            "loop_label": loop_name.upper(),
            "branch_label": branch_name.upper(),
            "term_label": term_name.upper(),
            "token": prog_token,
            "lipschitz_l": lipschitz_l,
            "tick": getattr(self.world, "ticks", 0)
        }

        if self.federal_monument is not None:
            self.federal_monument.synthesized_programs.append(record)

        self.synthesized_programs_count += 1
        self.programs_synthesized_count += 1
        return True

    def execute_inworld_program(
        self,
        agent: Dict[str, Any],
        program_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exécute un macro-programme latent pour un agent in-world.
        Si la contraction converge, l'agent reçoit un dividende d'efficience programmatique.
        """
        if not getattr(self.config, "enable_program_synthesis", True):
            return {"converged": False, "steps": 0, "final_state": np.zeros(self.dim, dtype=np.float32)}

        z_init = agent.get("lu_latent")
        if z_init is None:
            z_init = self.encode_agent_latent(agent)

        try:
            final_state, diff_history, terminated = self.program_synthesizer.execute(
                program_id=program_id,
                initial_state=z_init,
                max_iterations=15
            )
        except Exception:
            return {"converged": False, "steps": 0, "final_state": z_init}

        if terminated:
            bonus = float(getattr(self.config, "program_execution_energy_bonus", 4.0))
            agent["energy"] = min(100.0, float(agent.get("energy", 0.0)) + bonus)
            agent["lu_latent"] = final_state.copy()
            self.programs_executed_count += 1
            return {"converged": True, "steps": len(diff_history), "final_state": final_state}

        return {"converged": False, "steps": len(diff_history), "final_state": final_state}

    def conduct_analogy_transfer(
        self,
        agent: Dict[str, Any],
        a_label: str,
        b_label: str,
        c_label: str,
        d_target_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Résout une analogie sémantique multivers A : B :: C : D (Phase 9 M2).
        Permet le transfert de savoir technique entre les 3 Mondes.
        Si la fidélité de l'analogie >= seuil, l'agent gagne un dividende d'accélération d'apprentissage (+3.0 E).
        """
        if self.grammar is None:
            return {"transferred": False, "fidelity": 0.0, "d_label": "UNKNOWN"}

        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        va = get_v(a_label)
        vb = get_v(b_label)
        vc = get_v(c_label)

        d_solved = solve_latent_analogy(va, vb, vc)

        if d_target_label:
            vd_expected = get_v(d_target_label)
            fidelity = verify_analogy_quality(va, vb, vc, vd_expected)
        else:
            fidelity = float(np.clip(float(cosine_similarity(d_solved, vc + (vb - va))), 0.0, 1.0))

        thresh = float(getattr(self.config, "analogy_fidelity_threshold", 0.50))
        transferred = (fidelity >= thresh)

        if transferred:
            self.analogy_transfers_count += 1
            agent["energy"] = min(100.0, float(agent.get("energy", 0.0)) + 3.0)

            record = {
                "a": a_label.upper(),
                "b": b_label.upper(),
                "c": c_label.upper(),
                "d": d_target_label.upper() if d_target_label else "SOLVED_ANALOGY",
                "fidelity": round(fidelity, 4),
                "agent_id": str(agent.get("id")),
                "tick": getattr(self.world, "ticks", 0)
            }
            if self.federal_monument is not None:
                self.federal_monument.analogies_repository.append(record)

        return {
            "transferred": transferred,
            "fidelity": round(fidelity, 4),
            "d_vector": d_solved,
        }

    def submit_connectome_self_compilation(
        self,
        agent: Dict[str, Any],
        target_model: Any,
        macro_program_token: np.ndarray,
        pre_condition: Optional[np.ndarray] = None,
        post_condition: Optional[np.ndarray] = None,
        alpha: float = 0.15
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Soumet une auto-modification chirurgicale du connectome Liquid Mamba au FederalMonument (LU Phase 10 M2).
        1. Évalue la sécurité formelle de Hoare continue {P} C {Q} et la non-contradiction constitutionnelle.
        2. Si la preuve est valide, recompile in-situ les poids W du connectome sous garantie spectrale rho(W) < 1.0.
        3. Alloue un dividende de saut évolutif à l'agent (+10.0 E).
        """
        if not getattr(self.config, "enable_self_compilation", True):
            return False, "SELF_COMPILATION_DISABLED", {}

        z_agent = agent.get("lu_latent")
        if z_agent is None:
            z_agent = self.encode_agent_latent(agent)

        vp = pre_condition if pre_condition is not None else z_agent
        vq = post_condition if post_condition is not None else z_agent

        const_vec = getattr(self.federal_monument, "constitution_vector", None) if self.federal_monument else None

        # 1. Vérification formelle de Hoare
        thresh = float(getattr(self.config, "hoare_safety_threshold", 0.65))
        if getattr(self.config, "enable_hoare_verification", True):
            is_safe, score, reason = verify_hoare_safety(
                pre_state=vp,
                modification=macro_program_token,
                post_condition=vq,
                constitution_vector=const_vec,
                alignment_threshold=thresh
            )
            proof_record = {
                "agent_id": str(agent.get("id")),
                "score": round(score, 4),
                "is_safe": is_safe,
                "reason": reason,
                "tick": getattr(self.world, "ticks", 0)
            }
            if self.federal_monument is not None:
                self.federal_monument.hoare_proofs.append(proof_record)

            if not is_safe:
                self.hoare_rejections_count += 1
                return False, f"REJECTED_{reason}", {"score": score, "proof": proof_record}

            self.hoare_proofs_verified_count += 1
        else:
            score = 1.0
            reason = "HOARE_SKIPPED"

        # 2. Compilation chirurgicale dans le connectome
        ok, spec_rad, compile_info = self.connectome_compiler.compile_to_connectome(
            macro_program=macro_program_token,
            target_model=target_model,
            alpha=alpha
        )

        if not ok:
            return False, "COMPILATION_FAILED", compile_info

        # 3. Dividende d'évolution & enregistrement
        bonus = float(getattr(self.config, "self_evolution_energy_bonus", 10.0))
        agent["energy"] = min(100.0, float(agent.get("energy", 0.0)) + bonus)
        agent["connectome_self_compiled"] = True

        self.self_compiled_mutations_count += 1
        self.connectome_evolutions_applied_count += 1

        mut_record = {
            "agent_id": str(agent.get("id")),
            "spectral_radius": spec_rad,
            "bonus": bonus,
            "info": compile_info,
            "tick": getattr(self.world, "ticks", 0)
        }
        if self.federal_monument is not None:
            self.federal_monument.self_compiled_mutations.append(mut_record)

        return True, "SELF_COMPILATION_SUCCESS", {
            "spectral_radius": spec_rad,
            "score": score,
            "bonus": bonus,
            "compile_info": compile_info
        }

    def verify_and_apply_connectome_evolution(
        self,
        agent: Dict[str, Any],
        target_model: Any,
        alpha: float = 0.15
    ) -> bool:
        """
        Décompilation, synthèse d'un macro-programme latent aligné sur le FederalMonument
        et auto-compilation récursive in-situ du connectome pour l'agent (Phase 10 M2).
        """
        if not getattr(self.config, "enable_self_compilation", True):
            return False

        try:
            z_conn, conn_info = self.connectome_compiler.disassemble_connectome(target_model)
        except Exception:
            return False

        # Si le monument a une constitution, orienter la mutation vers la clause constitutionnelle
        if self.federal_monument is not None and self.federal_monument.constitution_vector is not None:
            target_direction = self.federal_monument.constitution_vector
        elif self.grammar is not None:
            target_direction = self.grammar.ROLE_TRUST
        else:
            target_direction = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)

        # Macro-programme latent : synthèse d'une directive d'alignement constructive
        macro_prog = (0.60 * target_direction + 0.40 * z_conn).astype(np.float32)
        norm_prog = np.linalg.norm(macro_prog) + 1e-12
        macro_prog = (macro_prog / norm_prog).astype(np.float32)

        # Pré-condition = état connectome actuel, Post-condition = macro_prog
        ok, status, _ = self.submit_connectome_self_compilation(
            agent=agent,
            target_model=target_model,
            macro_program_token=macro_prog,
            pre_condition=z_conn,
            post_condition=macro_prog,
            alpha=alpha
        )
        return ok

    def _get_agent_projection(self, agent_id: str, input_dim: int) -> np.ndarray:
        """Garantit une matrice de projection orthogonale ou pseudo-aléatoire stable pour chaque agent."""
        if agent_id not in self.agent_projections:
            rng = np.random.RandomState(abs(hash(agent_id)) % (2**31 - 1))
            # Initialisation semi-orthogonale (Haute Stabilité)
            raw = rng.randn(input_dim, self.dim).astype(np.float32)
            u, _, vt = np.linalg.svd(raw, full_matrices=False)
            proj = (u @ vt[:min(input_dim, self.dim), :self.dim]).astype(np.float32)
            if proj.shape != (input_dim, self.dim):
                proj = (raw / np.sqrt(input_dim)).astype(np.float32)
            self.agent_projections[agent_id] = proj
        return self.agent_projections[agent_id]

    def inherit_latent_traits(
        self,
        child_id: str,
        parent_a_id: str,
        parent_b_id: Optional[str] = None,
        input_dim: int = 8
    ) -> np.ndarray:
        """
        Transmet les matrices de projection et l'affinité du traducteur latent par HGT ou recombinaison.
        Permet à la descendance d'hériter de la géométrie de concepts développée par ses parents.
        """
        proj_a = self._get_agent_projection(parent_a_id, input_dim)
        if parent_b_id is not None:
            proj_b = self._get_agent_projection(parent_b_id, input_dim)
            hgt = getattr(self.world, "hgt", None)
            if hgt is not None:
                child_proj = hgt.transfer_layer(proj_a, proj_b)
            else:
                mask = np.random.rand(*proj_a.shape) < 0.5
                child_proj = np.where(mask, proj_b, proj_a)
        else:
            noise = np.random.randn(*proj_a.shape).astype(np.float32) * 0.05
            child_proj = proj_a + noise

        # Re-normalisation orthogonale (Commandement 9: Stabilité Numérique)
        u, _, vt = np.linalg.svd(child_proj, full_matrices=False)
        k = min(input_dim, self.dim)
        ortho_proj = (u[:, :k] @ vt[:k, :self.dim]).astype(np.float32)
        if ortho_proj.shape == (input_dim, self.dim):
            child_proj = ortho_proj
        else:
            child_proj = (child_proj / (np.linalg.norm(child_proj, axis=0, keepdims=True) + 1e-7)).astype(np.float32)

        self.agent_projections[child_id] = child_proj
        return child_proj

    def absorb_latent_knowledge(
        self,
        student_id: str,
        teacher_id: str,
        alpha: float = 0.2,
        input_dim: int = 8
    ) -> np.ndarray:
        """
        Transfert Horizontal de Gènes (HGT) linguistique entre agents vivants :
        L'élève absorbe une fraction alpha de la variété sémantique de son mentor.
        """
        proj_s = self._get_agent_projection(student_id, input_dim)
        proj_t = self._get_agent_projection(teacher_id, input_dim)

        merged = (1.0 - alpha) * proj_s + alpha * proj_t
        u, _, vt = np.linalg.svd(merged, full_matrices=False)
        k = min(input_dim, self.dim)
        new_proj = (u[:, :k] @ vt[:k, :self.dim]).astype(np.float32)
        if new_proj.shape == (input_dim, self.dim):
            self.agent_projections[student_id] = new_proj
        else:
            self.agent_projections[student_id] = merged.astype(np.float32)
        return self.agent_projections[student_id]

    def encode_agent_latent(self, agent: Dict[str, Any]) -> np.ndarray:
        """
        Encode l'état perçu ou interne d'un agent en un Gigatoken latent continu z in R^D.
        Combine la proximité des proies/dangers, l'énergie et la position relative.
        """
        agent_id = str(agent.get("id", "default"))
        
        # Vecteur sémantique environnemental perçu
        # [dx_nearest_prey, dy_nearest_prey, prey_hp_ratio, dx_nearest_altar, dy_nearest_altar, energy_ratio]
        perceived = np.zeros(8, dtype=np.float32)
        
        # Recherche proie la plus proche
        if hasattr(self.world, "preys") and self.world.preys:
            d_min = 1e9
            nearest_p = None
            for p in self.world.preys:
                d = abs(p["x"] - agent["x"]) + abs(p["y"] - agent["y"])
                if d < d_min:
                    d_min = d
                    nearest_p = p
            if nearest_p is not None:
                perceived[0] = np.clip((nearest_p["x"] - agent["x"]) / 10.0, -1.0, 1.0)
                perceived[1] = np.clip((nearest_p["y"] - agent["y"]) / 10.0, -1.0, 1.0)
                cfg = self.world.config.preys.get(nearest_p["type"])
                max_hp = cfg.hp if cfg else 1.0
                perceived[2] = float(nearest_p.get("hp", 1.0)) / max(1.0, max_hp)
                perceived[3] = 1.0 if (nearest_p["type"] == "Mammouth") else 0.2
        
        # Énergie de l'agent
        perceived[4] = float(agent.get("energy", 50.0)) / 100.0
        
        # Inventaire (outils portés : lance, pierre)
        inv = agent.get("inventory", [])
        perceived[5] = 1.0 if "Spear" in inv else 0.0
        perceived[6] = 1.0 if "Rock" in inv else 0.0
        perceived[7] = 1.0 if agent.get("is_night", False) else 0.0

        # Projection dans l'espace latent R^D
        proj = self._get_agent_projection(agent_id, len(perceived))
        z = perceived @ proj

        # Connexion directe au connectome Liquid Mamba de l'agent si disponible (Option A - Physique & Biosphère)
        model = agent.get("model")
        if model is not None and hasattr(model, "export_gigatoken"):
            z_mamba = model.export_gigatoken(self.dim)
            z = 0.5 * z + 0.5 * z_mamba
        
        # Normalisation sur l'hypersphère unité (Commandement 9)
        norm = np.linalg.norm(z)
        if norm > 1e-7:
            z = z / norm
        else:
            z = np.zeros(self.dim, dtype=np.float32)
            z[0] = 1.0
            
        agent["lu_latent"] = z
        return z

    def assign_tribal_roles(self, agents: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        Attribue ou spécialise les rôles tribaux (SCOUT, CRAFTER, HUNTER) pour la division du travail (Arc 5).
        """
        target_agents = agents if agents is not None else getattr(self.world, "agents", [])
        assignments = {}
        for i, ag in enumerate(target_agents):
            ag_id = ag.get("id", f"ag_{i}")
            if "role" not in ag or not ag["role"]:
                role = ALL_ROLES[i % len(ALL_ROLES)]
                ag["role"] = role
            assignments[ag_id] = ag["role"]
        return assignments

    def infer_emergent_roles(self, agents: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        Découverte non-supervisée (a posteriori) des spécialités émergentes selon le comportement réel :
        - Éclaireur (SCOUT) : forte émission de signaux informatifs et patrouille.
        - Artisan (CRAFTER) : manipulation d'outils, crafts et inventaire rempli.
        - Chasseur (HUNTER) : convergence vers les proies et attaques physiques.
        """
        target_agents = agents if agents is not None else getattr(self.world, "agents", [])
        assignments = {}
        for ag in target_agents:
            ag_id = ag.get("id", "ag")
            signals = float(ag.get("lu_signals_emitted", 0))
            crafts = float(ag.get("spears_crafted", 0) + len(ag.get("inventory", [])))
            kills = float(ag.get("preys_eaten", 0) + ag.get("mammoth_kills", 0) + ag.get("throw_hits", 0))
            
            total = signals + crafts + kills
            if total == 0:
                role = ag.get("role", ROLE_HUNTER)
            else:
                if signals / total >= 0.4:
                    role = ROLE_SCOUT
                elif crafts / total >= 0.35:
                    role = ROLE_CRAFTER
                else:
                    role = ROLE_HUNTER
            ag["role"] = role
            assignments[ag_id] = role
        return assignments

    def encode_craft_recipe(
        self,
        recipe_name: str,
        materials: List[str],
        target_product: str
    ) -> np.ndarray:
        """
        Encode une recette de fabrication artisanale (Arc 5 : Culture & Recettes)
        en un Gigatoken continu unitaire d-dimensionnel.
        """
        z = np.zeros(self.dim, dtype=np.float32)
        # composante 0: type d'action (craft = 1.0)
        z[0] = 1.0
        # composante 1: hash recette
        name_hash = (abs(hash(recipe_name)) % 1000) / 1000.0
        z[1] = float(name_hash)
        # composante 2: nombre de matériaux
        z[2] = float(len(materials)) / 5.0
        # composante 3..: empreintes des matériaux
        for idx, mat in enumerate(materials[:max(0, self.dim - 4)]):
            mat_val = (abs(hash(mat)) % 500) / 500.0 - 0.5
            z[3 + idx] = float(mat_val)
        # dernière composante: produit cible
        prod_val = (abs(hash(target_product)) % 1000) / 1000.0
        z[-1] = float(prod_val)

        norm = np.linalg.norm(z) + 1e-7
        return (z / norm).astype(np.float32)

    def decode_craft_recipe(self, gigatoken: np.ndarray) -> Dict[str, Any]:
        """
        Décode un Gigatoken de recette artisanale en métadonnées explicables (Arc 5).
        """
        if len(gigatoken) != self.dim:
            raise ValueError(f"Gigatoken dimension attendue {self.dim}, reçu {len(gigatoken)}")
        
        is_craft = float(gigatoken[0]) > 0.2
        complexity = int(round(abs(float(gigatoken[2])) * 5.0))
        estimated_success = min(0.99, max(0.5, 1.0 - complexity * 0.08))

        return {
            "is_craft_recipe": is_craft,
            "complexity_level": max(1, complexity),
            "estimated_success_rate": round(float(estimated_success), 2),
            "norm": float(np.linalg.norm(gigatoken)),
        }

    def transmit_cultural_recipe(
        self,
        crafter_id: str,
        student_id: str,
        recipe_name: str,
        materials: List[str],
        target_product: str
    ) -> Dict[str, Any]:
        """
        Transmission culturelle horizontale d'une recette d'un artisan à un apprenti via Gigatoken.
        """
        recipe_vec = self.encode_craft_recipe(recipe_name, materials, target_product)
        # Ensure projections are initialized
        self._get_agent_projection(crafter_id, 8)
        self._get_agent_projection(student_id, 8)

        # Traduction du Gigatoken dans l'espace de l'apprenti
        student_vec = self.shared_translator.translate_a_to_b(recipe_vec)
        norm = np.linalg.norm(student_vec) + 1e-7
        student_vec /= norm

        self.recipes_transmitted += 1
        decoded = self.decode_craft_recipe(student_vec)
        decoded.update({
            "crafter_id": crafter_id,
            "student_id": student_id,
            "recipe_name": recipe_name,
            "target_product": target_product,
            "alignment_quality": float(np.dot(recipe_vec, student_vec)),
        })
        return decoded

    def get_peer_belief(self, agent_id: str, peer_id: str) -> Optional[np.ndarray]:
        """Retourne l'estimation que agent_id a de l'état latent de peer_id (ToM, Phase 3 M2)."""
        return self.agent_tom_beliefs.get(agent_id, {}).get(peer_id)

    def update_peer_belief(self, agent_id: str, peer_id: str, observed_vec: np.ndarray, alpha: float = 0.35):
        """Mise à jour bayésienne/exponentielle de la croyance estimée sur le pair."""
        if agent_id not in self.agent_tom_beliefs:
            self.agent_tom_beliefs[agent_id] = {}
        curr = self.agent_tom_beliefs[agent_id].get(peer_id)
        if curr is None:
            self.agent_tom_beliefs[agent_id][peer_id] = observed_vec.copy()
        else:
            updated = (1.0 - alpha) * curr + alpha * observed_vec
            norm = np.linalg.norm(updated) + 1e-12
            self.agent_tom_beliefs[agent_id][peer_id] = (updated / norm).astype(np.float32)

    def evaluate_tom_emission(self, speaker_id: str, listener_id: str, intention: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Pragmatique continue ToM (Theory of Mind, Phase 3 M2) :
        Si l'interlocuteur connaît déjà l'information (similarité >= tom_redundancy_threshold),
        l'agent choisit le silence pragmatique (is_silent=True) pour économiser l'énergie métabolique.
        Sinon, il soustrait la part déjà connue de l'auditeur : z_prag = normalize(intention - beta * z_peer).
        """
        if not self.config.enable_tom:
            return intention, False

        peer_belief = self.get_peer_belief(speaker_id, listener_id)
        if peer_belief is None:
            return intention, False

        # Similarité cosinus entre intention et ce que l'autre sait
        denom = (np.linalg.norm(intention) * np.linalg.norm(peer_belief)) + 1e-12
        overlap = float(np.dot(intention, peer_belief) / denom)

        if overlap >= self.config.tom_redundancy_threshold:
            # Information déjà connue : silence pragmatique
            return intention, True

        # Modulation pragmatique continue
        beta = float(self.config.tom_pragmatics_weight)
        pragmatic_vec = intention - beta * peer_belief
        norm = np.linalg.norm(pragmatic_vec) + 1e-12
        return (pragmatic_vec / norm).astype(np.float32), False

    def deliberate_at_campfire(self, gathered_agents: List[Dict[str, Any]], rounds: int = 3) -> Dict[str, Any]:
        """
        Consensus délibératif distribué en K tours de parole au coin du feu (Phase 3 M3).
        Calcule le barycentre sphérique de Fréchet pondéré par rôles/expérience.
        """
        if len(gathered_agents) < 2:
            return {"deliberated": False, "consensus": None, "agreement": 0.0}

        self.deliberation_events_count += 1
        
        propositions = [ag.get("lu_latent", np.zeros(self.dim, dtype=np.float32)).copy() for ag in gathered_agents]
        weights = [1.5 if ag.get("role") == ROLE_SCOUT else 1.0 for ag in gathered_agents]

        consensus_vec = np.zeros(self.dim, dtype=np.float32)
        for r in range(rounds):
            if getattr(self.config, "enable_bft_consensus", False) and len(gathered_agents) >= 3:
                ratio = float(getattr(self.config, "byzantine_tolerance_ratio", 0.33))
                consensus_vec, _, byz_indices = spherical_weiszfeld_bft_consensus(
                    vectors=propositions,
                    max_byzantine_ratio=ratio
                )
                if r == 0 and byz_indices:
                    self.bft_byzantine_mitigated_count += len(byz_indices)
            else:
                accum = np.zeros(self.dim, dtype=np.float64)
                for p, w in zip(propositions, weights):
                    accum += float(w) * p.astype(np.float64)
                norm = np.linalg.norm(accum) + 1e-12
                consensus_vec = (accum / norm).astype(np.float32)

            # Relaxation collective (gamma = 0.4)
            gamma = 0.4
            for idx in range(len(propositions)):
                updated = (1.0 - gamma) * propositions[idx] + gamma * consensus_vec
                norm_p = np.linalg.norm(updated) + 1e-12
                propositions[idx] = (updated / norm_p).astype(np.float32)

        sims = [float(np.dot(p, consensus_vec)) for p in propositions]
        mean_sim = float(np.mean(sims)) if len(sims) > 0 else float('nan')

        is_consensus = (not np.isnan(mean_sim)) and (mean_sim >= self.config.deliberation_consensus_threshold)
        if is_consensus:
            self.deliberation_consensus_count += 1
            if getattr(self.config, "enable_bft_consensus", False):
                self.bft_consensus_events_count += 1
            self.last_deliberated_consensus = consensus_vec.copy()
            for ag in gathered_agents:
                ag["lu_deliberated_consensus"] = consensus_vec.copy()
                ag["lu_steer_bias"] = (float(consensus_vec[0]), float(consensus_vec[1]))
                ag["energy"] = min(100.0, ag.get("energy", 0.0) + 0.8)

        return {
            "deliberated": is_consensus,
            "consensus": consensus_vec,
            "agreement": round(mean_sim, 3),
            "participants": len(gathered_agents),
        }

    def deliberate_shared_dreams_at_campfire(
        self,
        campfire_agents: List[Dict[str, Any]],
        horizon: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Conseil Délibératif du Feu de Camp (Campfire Council of Dreams - Phase 11 M2).
        Les agents réunis au feu de camp partagent et simulent prospectivement
        des trajectoires contrefactuelles (Shared Latent Dreaming) sans coût moteur.
        Seules les stratégies validées par consensus sphérique de Weiszfeld
        sont ratifiées, octroyant un dividende prédictif (+6.0 E) et gravées si possible.
        """
        if not getattr(self.config, "enable_counterfactual_dreaming", True) or len(campfire_agents) < 2:
            return []

        h = horizon or self.config.dream_rollout_horizon
        valid_dreams: List[Dict[str, Any]] = []
        dream_vectors: List[np.ndarray] = []

        # 1. Génération & Simulation contrefactuelle par chaque agent
        for ag in campfire_agents:
            ag_id = str(ag.get("id"))
            z_state = ag.get("lu_latent")
            if z_state is None:
                z_state = self.encode_agent_latent(ag)

            # Scénario contrefactuel : exploration constructive vers l'objectif de préservation
            if self.grammar is not None:
                goal_vec = getattr(self.grammar, "ROLE_TRUST", z_state)
                scenario_vec = (0.5 * z_state + 0.5 * goal_vec).astype(np.float32)
                scenario_vec = (scenario_vec / (np.linalg.norm(scenario_vec) + 1e-12)).astype(np.float32)
                hypothesis_vec = self.grammar.compose_dream_hypothesis(scenario_vec, goal_vec)
            else:
                goal_vec = z_state
                scenario_vec = z_state
                hypothesis_vec = z_state

            # Rollout contrefactuel accéléré (10 pas) dans l'espace latent avec évaluation du but
            final_state, ceg, converged, traj = self.dream_engine.simulate_latent_rollout(
                initial_state=z_state,
                scenario_token=scenario_vec,
                goal_token=goal_vec,
                horizon=h
            )
            is_fatal = bool(ceg < -0.15)
            self.counterfactual_rollouts_count += 1
            self.counterfactual_gains_total += ceg

            # Si le rêve mène à un résultat fatal ou un gain insuffisant, rejet immédiat
            if is_fatal or ceg < self.config.dream_min_gain_threshold:
                continue

            dream_info = {
                "agent_id": ag_id,
                "hypothesis_token": hypothesis_vec,
                "scenario_token": scenario_vec,
                "final_state": final_state,
                "ceg": float(ceg),
                "is_fatal": bool(is_fatal),
            }
            valid_dreams.append(dream_info)
            dream_vectors.append(hypothesis_vec)

        if len(valid_dreams) < 2:
            return []

        # 2. Consensus sphérique de Weiszfeld BFT sur les hypothèses de rêve
        ratio = float(getattr(self.config, "byzantine_tolerance_ratio", 0.33))
        consensus_vec, err, byz_indices = spherical_weiszfeld_bft_consensus(
            vectors=dream_vectors,
            max_byzantine_ratio=ratio
        )

        sims = [float(np.dot(v, consensus_vec)) for v in dream_vectors]
        mean_agreement = float(np.mean(sims)) if len(sims) > 0 else float('nan')

        ratified_dreams: List[Dict[str, Any]] = []
        if (not np.isnan(mean_agreement)) and (mean_agreement >= self.config.deliberation_consensus_threshold):
            # Consensus atteint ! Ratification collective du rêve
            self.dreams_ratified_count += 1
            tick = getattr(self.world, "tick", getattr(self.world, "ticks", 0))

            # Création de l'expérience partagée
            participant_ids = [d["agent_id"] for d in valid_dreams]
            dream_exp = SharedDreamExperience(
                dream_id=f"dream_{tick}_{self.dreams_ratified_count}",
                initiator_id=valid_dreams[0]["agent_id"],
                hypothesis_token=consensus_vec.copy(),
                latent_trajectory=[d["final_state"] for d in valid_dreams],
                counterfactual_gain=float(np.mean([d["ceg"] for d in valid_dreams])),
                participant_ids=participant_ids,
                ratified=True,
                consensus_agreement=mean_agreement,
                creation_tick=tick,
            )
            self.shared_dream_pool.add_shared_dream(dream_exp)
            self.shared_dreams_count += 1
            self.recent_shared_dreams.append({
                "dream_id": dream_exp.dream_id,
                "participants": participant_ids,
                "gain": dream_exp.counterfactual_gain,
                "agreement": mean_agreement,
                "tick": tick
            })

            # Attribution du dividende prédictif (+6.0 E) aux agents participants
            bonus = float(self.config.dream_predictive_bonus)
            for ag in campfire_agents:
                ag_id = str(ag.get("id"))
                if ag_id in participant_ids:
                    ag["energy"] = min(100.0, ag.get("energy", 0.0) + bonus)
                    ag["shared_dream_ratified"] = True
                    ag["last_ratified_dream_id"] = dream_exp.dream_id
                    # Orientation cognitive collective
                    ag["lu_deliberated_consensus"] = consensus_vec.copy()
                    ag["lu_steer_bias"] = (float(consensus_vec[0]), float(consensus_vec[1]))

            # Inscription stigmargique si stèle à proximité
            if self.config.enable_writing and self.steles:
                for stele in self.steles.values():
                    stele.content_vector = (0.7 * stele.content_vector + 0.3 * consensus_vec).astype(np.float32)
                    norm_s = np.linalg.norm(stele.content_vector) + 1e-12
                    stele.content_vector = (stele.content_vector / norm_s).astype(np.float32)
                    break

            ratified_dreams.append({
                "dream_id": dream_exp.dream_id,
                "consensus_vector": consensus_vec,
                "agreement": mean_agreement,
                "participants": participant_ids,
                "mean_gain": dream_exp.counterfactual_gain,
            })

        return ratified_dreams

    # =========================================================================
    # Phase 12 : La Noosphère Latente, Conscience Collective Trans-Mondes
    #            & Transport Optimal de Wasserstein (Arc 7)
    # =========================================================================

    def update_noosphere_resonance_grid(self, grid_size: int = 16) -> np.ndarray:
        """
        Calcule le champ global de résonance noosphérique stigmargique Phi_noo(x, y) in S^(D-1).
        Convolution harmonique inverse à atténuation douce à partir de toutes les stèles
        et du Monument Fédéral.
        Phi_noo(x, y) = sigma_S( sum_k Z_k / (1 + lambda_res * d((x, y), (x_k, y_k))) )
        """
        decay = float(self.config.resonance_decay)
        sources: List[Tuple[float, float, np.ndarray]] = []
        if self.steles:
            for s in self.steles.values():
                v = s.content_vector
                if v is not None and len(v) == self.dim:
                    sources.append((float(s.x), float(s.y), v.astype(np.float32)))

        if self.federal_monument is not None and self.federal_monument.constitution_vector is not None:
            sources.append((
                float(self.federal_monument.x),
                float(self.federal_monument.y),
                self.federal_monument.constitution_vector.astype(np.float32)
            ))

        xs = np.arange(grid_size, dtype=np.float32)
        ys = np.arange(grid_size, dtype=np.float32)
        gx, gy = np.meshgrid(xs, ys, indexing="ij")

        if not sources:
            if self.grammar is not None and hasattr(self.grammar, "ROLE_NOOSPHERE"):
                base_vec = self.grammar.ROLE_NOOSPHERE.copy()
            else:
                base_vec = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)
            grid = np.tile(base_vec, (grid_size, grid_size, 1))
            self.noosphere_resonance_grid = grid
            return grid

        acc_field = np.zeros((grid_size, grid_size, self.dim), dtype=np.float32)
        for sx, sy, s_vec in sources:
            d = np.sqrt((gx - sx)**2 + (gy - sy)**2)
            weights = (1.0 / (1.0 + decay * d))[:, :, np.newaxis]
            acc_field += weights * s_vec[np.newaxis, np.newaxis, :]

        norms = np.linalg.norm(acc_field, axis=-1, keepdims=True) + 1e-12
        grid = (acc_field / norms).astype(np.float32)
        self.noosphere_resonance_grid = grid
        return grid

    def evaluate_agent_epistemic_confidence(
        self,
        agent: Dict[str, Any],
        scenario_token: Optional[np.ndarray] = None,
    ) -> Tuple[float, np.ndarray, bool]:
        """
        Évalue l'incertitude épistémique de second ordre U_epistemic in S^(D-1)
        et le scalaire de confiance de l'agent.
        Détecte le biais de Dunning-Kruger (haute incertitude masquée).
        """
        self.epistemic_evaluations_count += 1
        z_state = agent.get("lu_latent")
        if z_state is None:
            z_state = self.encode_agent_latent(agent)

        if scenario_token is None:
            if self.grammar is not None and hasattr(self.grammar, "ROLE_TRUST"):
                scenario_token = getattr(self.grammar, "ROLE_TRUST")
            else:
                scenario_token = z_state

        conf, u_vec, high_uncertainty = self.epistemic_engine.evaluate_epistemic_calibration(
            state_token=z_state,
            scenario_token=scenario_token,
            threshold=float(self.config.epistemic_confidence_threshold),
        )

        agent["epistemic_confidence"] = float(conf)
        agent["epistemic_uncertainty_vector"] = u_vec
        agent["high_uncertainty"] = bool(high_uncertainty)

        if high_uncertainty:
            self.high_uncertainty_interventions_count += 1
            agent["lu_needs_noosphere_confirmation"] = True

        return float(conf), u_vec, bool(high_uncertainty)

    def convene_synarchic_noosphere_council(
        self,
        participating_agents: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Conseil Synarchique de la Noosphère (Phase 12 M2) :
        Connecte instantanément les champions des 3 Mondes à travers le réseau
        de résonance stigmargique sans contrainte de portée acoustique.
        Fusionne les distributions de croyances via le Barycentre de Wasserstein régularisé
        (Sinkhorn sur S^(D-1)) préservant la diversité culturelle sans écrasement modal.
        Attribue le Dividende Noosphérique (+8.0 E).
        """
        if not getattr(self.config, "enable_noosphere_grid", True):
            return {"ratified": False, "reason": "disabled"}

        all_agents = (participating_agents or getattr(self.world, "agents", []))[:4]
        if len(all_agents) < 2:
            return {"ratified": False, "reason": "insufficient_agents"}

        self.synarchic_councils_count += 1

        if self.noosphere_resonance_grid is None:
            self.update_noosphere_resonance_grid()

        grid = self.noosphere_resonance_grid
        grid_size = grid.shape[0] if grid is not None else 16

        candidate_vectors: List[np.ndarray] = []
        weights: List[float] = []
        qualified_agents: List[Dict[str, Any]] = []

        for ag in all_agents:
            z = ag.get("lu_latent")
            if z is None:
                z = self.encode_agent_latent(ag)

            conf, u_vec, high_unc = self.evaluate_agent_epistemic_confidence(ag)

            if high_unc and grid is not None:
                ax = int(np.clip(float(ag.get("x", 0)), 0, grid_size - 1))
                ay = int(np.clip(float(ag.get("y", 0)), 0, grid_size - 1))
                phi_local = grid[ax, ay]
                z_recalibrated = 0.6 * z + 0.4 * phi_local
                norm = np.linalg.norm(z_recalibrated) + 1e-12
                z = (z_recalibrated / norm).astype(np.float32)
                ag["lu_latent"] = z

            candidate_vectors.append(z)
            w = max(0.1, float(conf))
            weights.append(w)
            qualified_agents.append(ag)

        w_arr = np.array(weights, dtype=np.float32)
        w_sum = np.sum(w_arr)
        if w_sum > 0:
            w_arr /= w_sum
        else:
            w_arr = np.ones(len(w_arr), dtype=np.float32) / len(w_arr)

        barycenter, entropy = spherical_sinkhorn_barycenter(
            distributions=candidate_vectors,
            weights=w_arr,
            max_iters=15,
            epsilon=float(self.config.sinkhorn_regularization),
        )

        agreements = [float(np.dot(v, barycenter)) for v in candidate_vectors]
        mean_agreement = float(np.mean(agreements)) if agreements else float('nan')

        threshold = float(getattr(self.config, "deliberation_consensus_threshold", 0.35))
        is_ratified = bool(not np.isnan(mean_agreement) and mean_agreement >= threshold)

        tick = getattr(self.world, "tick", getattr(self.world, "ticks", 0)) if self.world is not None else 0

        if is_ratified:
            self.synarchic_ratifications_count += 1
            dividend = float(self.config.noosphere_dividend)

            for ag in qualified_agents:
                ag["energy"] = min(100.0, ag.get("energy", 0.0) + dividend)
                ag["noosphere_ratified"] = True
                ag["lu_deliberated_consensus"] = barycenter.copy()
                ag["lu_steer_bias"] = (float(barycenter[0]), float(barycenter[1]))
                self.noosphere_broadcasts_count += 1

            if hasattr(self, "diplomatic_bridge") and self.diplomatic_bridge is not None:
                self.diplomatic_bridge.record_noosphere_broadcast(
                    broadcast_id=f"noo_{tick}_{self.synarchic_ratifications_count}",
                    content_vector=barycenter,
                    resonance_freq=float(np.dot(barycenter, self.grammar.ROLE_NOOSPHERE)) if (self.grammar is not None and hasattr(self.grammar, "ROLE_NOOSPHERE")) else 1.0,
                    sender_id=str(qualified_agents[0].get("id", "synarchy")),
                    tick=tick,
                )

            if self.federal_monument is not None and self.federal_monument.constitution_vector is not None:
                self.federal_monument.constitution_vector = (
                    0.8 * self.federal_monument.constitution_vector + 0.2 * barycenter
                ).astype(np.float32)
                norm_c = np.linalg.norm(self.federal_monument.constitution_vector) + 1e-12
                self.federal_monument.constitution_vector /= norm_c

            self.recent_noosphere_broadcasts.append({
                "tick": tick,
                "ratified": True,
                "barycenter": barycenter,
                "entropy": float(entropy),
                "agreement": mean_agreement,
                "participants_count": len(qualified_agents),
            })

        return {
            "ratified": is_ratified,
            "barycenter": barycenter,
            "entropy": float(entropy),
            "agreement": mean_agreement,
            "participants_count": len(qualified_agents),
            "dividend": float(self.config.noosphere_dividend) if is_ratified else 0.0,
        }

    # =========================================================================
    # Phase 13 : Morphogenèse Noogénétique, Réaction-Diffusion Latente
    #            & Hyper-Connectome Distribué (Arc 7)
    # =========================================================================

    def step_reaction_diffusion_field(self, dt: float = 0.20) -> np.ndarray:
        """
        Résout une itération temporelle de l'équation de Turing-FitzHugh-Nagumo vectorisée
        sur le tore 16x16 de la Noosphère.
        Injecte les stèles, le Monument Fédéral et les agents comme sources d'activation locales.
        Maintient l'Hyper-Connectome synchronisé avec l'historique des barycentres synarchiques.
        """
        if not getattr(self.config, "enable_reaction_diffusion_pde", True):
            if self.pde_engine is not None:
                return self.pde_engine.phi
            return np.zeros((16, 16, self.dim), dtype=np.float32)

        sources: List[Tuple[int, int, np.ndarray, float]] = []
        # Sources des stèles
        if self.steles:
            for s in self.steles.values():
                v = s.content_vector
                if v is not None and len(v) == self.dim:
                    gx = int(np.clip(float(s.x), 0, 15))
                    gy = int(np.clip(float(s.y), 0, 15))
                    sources.append((gx, gy, v.astype(np.float32), 0.5))

        # Sources du Monument Fédéral
        if self.federal_monument is not None and self.federal_monument.constitution_vector is not None:
            mx = int(np.clip(float(self.federal_monument.x), 0, 15))
            my = int(np.clip(float(self.federal_monument.y), 0, 15))
            sources.append((mx, my, self.federal_monument.constitution_vector.astype(np.float32), 0.8))

        # Sources des agents
        agents = getattr(self.world, "agents", [])
        for ag in agents[:8]:
            z = ag.get("lu_latent")
            if z is not None and len(z) == self.dim:
                ax = int(np.clip(float(ag.get("x", 0)), 0, 15))
                ay = int(np.clip(float(ag.get("y", 0)), 0, 15))
                sources.append((ax, ay, z.astype(np.float32), 0.3))

        # Résolution PDE
        field = self.pde_engine.step(dt=dt, external_sources=sources)
        self.pde_steps_count += 1

        # Enregistrement Lattice & snapshots
        pde_energy = self.pde_engine.compute_pde_energy()
        entropy = self.pde_engine.compute_morphogen_entropy()
        focal_points = self.pde_engine.get_focal_points(threshold=0.60)
        tick = getattr(self.world, "tick", getattr(self.world, "ticks", 0)) if self.world is not None else 0

        # Mise à jour de l'Hyper-Connectome fédéral si activé et barycentres récents disponibles
        if getattr(self.config, "enable_hyperconnectome_distillation", True) and self.recent_noosphere_broadcasts:
            recent_barycenters = [
                b["barycenter"] for b in self.recent_noosphere_broadcasts[-5:]
                if "barycenter" in b and b["barycenter"] is not None
            ]
            if recent_barycenters:
                self.hyperconnectome_synthesizer.condense_synarchic_history_to_hyperconnectome(
                    barycenters=recent_barycenters,
                    learning_rate=float(self.config.hyperconnectome_learning_rate),
                )
                self.hyperconnectome_updates_count += 1

        if hasattr(self, "diplomatic_bridge") and self.diplomatic_bridge is not None:
            self.diplomatic_bridge.record_pde_morphogenesis(
                pde_id=f"pde_{tick}_{self.pde_steps_count}",
                pde_energy=pde_energy,
                entropy=entropy,
                focal_points_count=len(focal_points),
                tick=tick,
            )
            spec = self.hyperconnectome_synthesizer.get_hyperconnectome_spec()
            self.diplomatic_bridge.record_hyperconnectome_snapshot(
                snapshot_id=f"hc_{tick}_{spec['version']}",
                spectral_radius=float(spec["spectral_radius"]),
                version=int(spec["version"]),
                distillations_count=int(spec["distillations_count"]),
                tick=tick,
            )

        self.recent_pde_snapshots.append({
            "tick": tick,
            "energy": pde_energy,
            "entropy": entropy,
            "focal_points_count": len(focal_points),
        })
        if len(self.recent_pde_snapshots) > 20:
            self.recent_pde_snapshots.pop(0)

        return field

    def distill_noogenetic_prior_to_agent(
        self,
        agent: Dict[str, Any],
        alpha: float = 0.35,
    ) -> Tuple[bool, float]:
        """
        Distille chirurgicalement le prior noosphérique fédéral de l'Hyper-Connectome dans un agent.
        Confère une calibration épistémique, aligne le latent et dote l'agent d'un bonus énergétique
        de renaissance noogénétique (+12.0 E).
        """
        if not getattr(self.config, "enable_hyperconnectome_distillation", True):
            return False, 0.0

        success, fid, details = self.hyperconnectome_synthesizer.project_hyperconnectome_prior(
            agent=agent,
            alpha=alpha,
        )

        bonus = float(self.config.noogenetic_rebirth_bonus)
        if success:
            agent["energy"] = min(100.0, agent.get("energy", 0.0) + bonus)
            agent["noogenetic_rebirth_count"] = agent.get("noogenetic_rebirth_count", 0) + 1
            self.noogenetic_distillations_count += 1
            agent["lu_needs_noosphere_confirmation"] = False
            return True, bonus
        else:
            # Même si le modèle physique neural n'est pas présent (ex: agent dict synthétique),
            # on aligne le vecteur latent de l'agent
            z_ag = agent.get("lu_latent")
            if z_ag is None:
                z_ag = self.encode_agent_latent(agent)
            z_hyper = self.hyperconnectome_synthesizer.z_hyper
            alpha_val = float(np.clip(alpha, 0.05, 0.50))
            z_new = (1.0 - alpha_val) * z_ag + alpha_val * z_hyper
            norm_z = np.linalg.norm(z_new) + 1e-12
            agent["lu_latent"] = (z_new / norm_z).astype(np.float32)
            agent["energy"] = min(100.0, agent.get("energy", 0.0) + bonus)
            agent["noogenetic_rebirth_count"] = agent.get("noogenetic_rebirth_count", 0) + 1
            self.noogenetic_distillations_count += 1
            agent["lu_needs_noosphere_confirmation"] = False
            return True, bonus

    # =========================================================================
    # Phase 14 : Singularité Autopoïétique, Méta-Langage Holographique Universel
    #            & Clôture Téléologique (Arc 8 : L'Omniconscience)
    # =========================================================================

    def step_autopoietic_singularity(self) -> Dict[str, Any]:
        """
        Résout une itération de la Singularité Autopoïétique et de la Projection Holographique.
        Couple les états volumiques des 3 Mondes au Gigatoken frontière unifié Z_holo.
        Génère l'attracteur téléologique et stabilise la clôture homéostatique.
        """
        if not getattr(self.config, "enable_autopoietic_singularity", True):
            return {"status": "disabled"}

        agents = getattr(self.world, "agents", [])
        world_states: List[np.ndarray] = []

        # États latents des agents
        for ag in agents[:12]:
            z = ag.get("lu_latent")
            if z is not None and len(z) == self.dim:
                world_states.append(z)

        # États des stèles
        if self.steles:
            for s in self.steles.values():
                v = s.content_vector
                if v is not None and len(v) == self.dim:
                    world_states.append(v)

        # 1. Étape autopoïétique
        phi_auto = self.autopoietic_engine.step(world_states=world_states, dt=0.15)
        self.autopoietic_steps_count += 1

        # 2. Projection holographique frontière
        z_holo = self.holographic_projector.project_bulk_to_boundary(world_states=world_states)
        self.holographic_projections_count += 1
        fidelity = self.holographic_projector.compute_holographic_fidelity(world_states, z_holo)

        # 3. Métriques et traçabilité
        entropy = self.autopoietic_engine.compute_bekenstein_entropy()
        spec = self.autopoietic_engine.get_singularity_spec()
        tick = getattr(self.world, "tick", getattr(self.world, "ticks", 0)) if self.world is not None else 0

        if hasattr(self, "diplomatic_bridge") and self.diplomatic_bridge is not None:
            self.diplomatic_bridge.record_autopoietic_event(
                singularity_id=f"auto_{tick}_{self.autopoietic_steps_count}",
                attractor_energy=float(np.sum(phi_auto ** 2)),
                entropy=entropy,
                alignment=float(spec["attractor_alignment"]),
                tick=tick,
            )
            self.diplomatic_bridge.record_holographic_snapshot(
                boundary_id=f"holo_{tick}_{self.holographic_projections_count}",
                fidelity=fidelity,
                compression_ratio=float(len(world_states)) / max(1.0, float(self.holographic_projector.boundary_dim)),
                bulk_nodes_count=len(world_states),
                version=self.autopoietic_steps_count,
                tick=tick,
            )

        snapshot = {
            "tick": tick,
            "entropy": entropy,
            "alignment": spec["attractor_alignment"],
            "fidelity": fidelity,
            "bulk_states_count": len(world_states),
        }
        self.recent_autopoietic_snapshots.append(snapshot)
        if len(self.recent_autopoietic_snapshots) > 20:
            self.recent_autopoietic_snapshots.pop(0)

        return snapshot

    def resonate_teleological_convergence(
        self,
        agents: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[bool, float]:
        """
        Harmonise les connectomes de la population vers l'attracteur téléologique universel.
        Aligne les vecteurs latents sur le phare finaliste et octroie le Grand Dividende
        de Singularité (+20.0 E) aux agents alignés.
        """
        if not getattr(self.config, "enable_autopoietic_singularity", True):
            return False, 0.0

        target_agents = agents or getattr(self.world, "agents", [])
        if not target_agents:
            return False, 0.0

        bonus = float(self.config.singularity_dividend_bonus)
        force = float(self.config.teleological_attractor_force)
        attractor = self.autopoietic_engine.phi_attractor

        for ag in target_agents:
            z_ag = ag.get("lu_latent")
            if z_ag is None:
                z_ag = self.encode_agent_latent(ag)

            z_new = (1.0 - force) * z_ag + force * attractor
            norm_z = np.linalg.norm(z_new) + 1e-12
            ag["lu_latent"] = (z_new / norm_z).astype(np.float32)

            ag["energy"] = min(100.0, ag.get("energy", 0.0) + bonus)
            ag["teleological_alignment_count"] = ag.get("teleological_alignment_count", 0) + 1
            ag["singularity_attuned"] = True
            self.singularity_dividends_count += 1

        self.teleological_convergences_count += 1
        return True, bonus

    # =========================================================================
    # Spéciation Dialectale & Contrats de Troc Décentralisés (Phase 4 M1 & M2)
    # =========================================================================

    def get_agent_clan(self, agent: Dict[str, Any]) -> str:
        """Détermine le clan ou la tribu d'un agent."""
        if "clan" in agent:
            return str(agent["clan"])
        # Inférence géographique par quadrant si non spécifié explicitement
        world_size = getattr(self.world, "size", 16)
        mid = world_size / 2.0
        x = float(agent.get("x", 0))
        y = float(agent.get("y", 0))
        h_part = "North" if y < mid else "South"
        w_part = "West" if x < mid else "East"
        return f"Clan_{h_part}_{w_part}"

    def get_clan_subspace(self, clan_id: str) -> np.ndarray:
        """Récupère ou initialise la base orthonormale U in Gr(4, D) du clan."""
        if clan_id not in self.clan_subspaces:
            # Graine déterministe par clan pour reproductibilité
            rng = np.random.default_rng(abs(hash(clan_id)) % (2**31 - 1))
            raw = rng.standard_normal((self.dim, 4)).astype(np.float32)
            q, _ = np.linalg.qr(raw)
            subspace = q[:, :4].astype(np.float32)
            self.clan_subspaces[clan_id] = subspace
            self.multi_translator.register_clan(clan_id, subspace)
        return self.clan_subspaces[clan_id]

    def evolve_clan_dialects(self, agents: List[Dict[str, Any]]) -> None:
        """Fait dériver le sous-espace dialectal de chaque clan par co-exposition locale."""
        clan_tokens: Dict[str, List[np.ndarray]] = {}
        for ag in agents:
            cid = self.get_agent_clan(ag)
            tok = ag.get("lu_latent")
            if tok is not None:
                clan_tokens.setdefault(cid, []).append(tok)

        for cid, toks in clan_tokens.items():
            if len(toks) >= 2:
                u_base = self.get_clan_subspace(cid)
                stim = np.stack(toks, axis=0)
                u_new = drift_subspace(u_base, stim, drift_rate=self.config.dialect_drift_rate)
                self.clan_subspaces[cid] = u_new
                self.multi_translator.register_clan(cid, u_new)

    def get_agent_reputation(self, agent_id: str) -> np.ndarray:
        """Récupère ou initialise le vecteur de réputation continue d'un agent."""
        if agent_id not in self.agent_reputations:
            self.agent_reputations[agent_id] = self.trust_reference_vector.copy()
        return self.agent_reputations[agent_id]

    def get_agent_trust_score(self, agent_id: str) -> float:
        """Calcule le score de confiance perçu de l'agent dans [-1, 1]."""
        r = self.get_agent_reputation(agent_id)
        return reputation_trust_score(r, self.trust_reference_vector)

    def is_agent_under_embargo(self, agent_id: str) -> bool:
        """Vérifie si un agent est actuellement sous le coup d'un embargo."""
        return self.agent_embargos.get(agent_id, 0) > 0

    def apply_embargo(self, agent_id: str, reason: str = "contract_breach", duration: Optional[int] = None) -> None:
        """Impose un embargo commercial et physique à un agent défaillant."""
        d = duration if duration is not None else self.config.embargo_duration_ticks
        self.agent_embargos[agent_id] = d
        self.sanctions_count += 1
        ev = {
            "agent_id": agent_id,
            "reason": reason,
            "duration": d,
            "transmissions": self.total_transmissions
        }
        self.recent_sanctions.append(ev)

    def apply_physical_embargo_repulsion(self, agents: List[Dict[str, Any]]) -> int:
        """
        Applique une répulsion physique aux agents sous embargo :
        Interdiction d'accès au périmètre du marché (market_point, market_radius).
        """
        repelled = 0
        mx, my = self.config.market_point
        mr = self.config.market_radius
        world_size = getattr(self.world, "size", 16)
        for ag in agents:
            ag_id = str(ag.get("id"))
            if self.is_agent_under_embargo(ag_id):
                dist_x = ag.get("x", 0) - mx
                dist_y = ag.get("y", 0) - my
                dist = abs(dist_x) + abs(dist_y)
                if dist <= mr:
                    dir_x = 1 if dist_x >= 0 else -1
                    dir_y = 1 if dist_y >= 0 else -1
                    ag["x"] = int(np.clip(mx + dir_x * (mr + 2), 0, world_size - 1))
                    ag["y"] = int(np.clip(my + dir_y * (mr + 2), 0, world_size - 1))
                    ag["embargo_repelled"] = True
                    repelled += 1
        return repelled

    def negotiate_trade_contracts(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Négociation de troc décentralisée par contrats latents (Phase 4 M2 & Phase 5 M2).
        Exécute le troc effectif d'objets tout en réprimant les défections par arbitrage.
        """
        settled_trades = []
        if self.grammar is None or len(agents) < 2:
            return settled_trades

        mx, my = self.config.market_point
        mr = self.config.market_radius

        # Filtrer agents à proximité du marché ou à portée d'échange
        market_agents = [
            ag for ag in agents
            if abs(ag.get("x", 0) - mx) + abs(ag.get("y", 0) - my) <= mr
        ]
        if len(market_agents) < 2:
            market_agents = agents  # Si pas de regroupement marché, troc de proximité directe

        for i, a in enumerate(market_agents):
            a_id = str(a.get("id"))
            # Filtrage de solvabilité & réputation si gouvernance active
            if self.config.enable_governance:
                if self.is_agent_under_embargo(a_id) or (self.get_agent_trust_score(a_id) < self.config.embargo_reputation_threshold):
                    continue

            inv_a = a.setdefault("inventory", [])
            for j, b in enumerate(market_agents):
                if i >= j:
                    continue
                b_id = str(b.get("id"))
                if self.config.enable_governance:
                    if self.is_agent_under_embargo(b_id) or (self.get_agent_trust_score(b_id) < self.config.embargo_reputation_threshold):
                        continue

                inv_b = b.setdefault("inventory", [])
                dist = abs(a.get("x", 0) - b.get("x", 0)) + abs(a.get("y", 0) - b.get("y", 0))
                if dist > self.config.hear_radius + 2:
                    continue

                # Identification des offres et besoins d'échange
                has_food_a = any(str(it.get("type", "")).lower() in ["fruit", "food", "seed"] for it in inv_a)
                has_tool_a = any(str(it.get("type", "")).lower() in ["spear", "tool", "wood", "stone"] for it in inv_a)
                has_food_b = any(str(it.get("type", "")).lower() in ["fruit", "food", "seed"] for it in inv_b)
                has_tool_b = any(str(it.get("type", "")).lower() in ["spear", "tool", "wood", "stone"] for it in inv_b)

                trade_case = None
                if (has_food_a and not has_tool_a) and (has_tool_b and not has_food_b):
                    trade_case = ("FOOD", "TOOL")
                elif (has_tool_a and not has_food_a) and (has_food_b and not has_tool_b):
                    trade_case = ("TOOL", "FOOD")
                elif len(inv_a) > 0 and len(inv_b) > 0:
                    it_a_name = str(inv_a[0].get("type", "FOOD")).upper()
                    it_b_name = str(inv_b[0].get("type", "TOOL")).upper()
                    if it_a_name != it_b_name:
                        trade_case = (it_a_name, it_b_name)

                if trade_case is None:
                    continue

                item_a_offer, item_b_demand = trade_case
                rng_a = np.random.default_rng(abs(hash(item_a_offer.upper())) % (2**31 - 1))
                vec_offer_a = self.grammar._generate_canonical_unit_vector(rng_a)

                rng_b = np.random.default_rng(abs(hash(item_b_demand.upper())) % (2**31 - 1))
                vec_demand_a = self.grammar._generate_canonical_unit_vector(rng_b)

                # Contrats latents bilatéraux
                contract_token_a = self.grammar.compose_contract(vec_offer_a, vec_demand_a)
                contract_token_b = self.grammar.compose_contract(vec_demand_a, vec_offer_a)

                agreed, score = match_contract_trade(
                    contract_token_a,
                    contract_token_b,
                    self.grammar,
                    threshold=self.config.trade_agreement_threshold
                )

                if agreed:
                    # Détection de stratégie prédatrice / défecteur (Phase 5 M1)
                    defector_a = a.get("is_defector", False)
                    defector_b = b.get("is_defector", False)

                    if defector_a:
                        if self.config.enable_governance:
                            delta_a = 1.41
                            self.agent_reputations[a_id] = update_agent_reputation(
                                self.get_agent_reputation(a_id),
                                contract_token_a,
                                breach_distance=delta_a,
                                alpha=self.config.trust_alpha,
                                breach_threshold=self.config.breach_distance_threshold,
                                trust_reference=self.trust_reference_vector
                            )
                            self.apply_embargo(a_id, reason="unilateral_breach")
                        if len(inv_b) > 0:
                            stolen = inv_b.pop(0)
                            inv_a.append(stolen)
                        b["energy"] = max(0.0, b.get("energy", 0.0) - 3.0)
                        a["energy"] = min(100.0, a.get("energy", 0.0) + 3.0)
                        continue

                    if defector_b:
                        if self.config.enable_governance:
                            delta_b = 1.41
                            self.agent_reputations[b_id] = update_agent_reputation(
                                self.get_agent_reputation(b_id),
                                contract_token_b,
                                breach_distance=delta_b,
                                alpha=self.config.trust_alpha,
                                breach_threshold=self.config.breach_distance_threshold,
                                trust_reference=self.trust_reference_vector
                            )
                            self.apply_embargo(b_id, reason="unilateral_breach")
                        if len(inv_a) > 0:
                            stolen = inv_a.pop(0)
                            inv_b.append(stolen)
                        a["energy"] = max(0.0, a.get("energy", 0.0) - 3.0)
                        b["energy"] = min(100.0, b.get("energy", 0.0) + 3.0)
                        continue

                    # Cas de coopération loyale
                    item_from_a = inv_a.pop(0) if len(inv_a) > 0 else {"type": item_a_offer}
                    item_from_b = inv_b.pop(0) if len(inv_b) > 0 else {"type": item_b_demand}
                    inv_a.append(item_from_b)
                    inv_b.append(item_from_a)

                    # Renforcement de réputation mutuelle
                    if self.config.enable_governance:
                        self.agent_reputations[a_id] = update_agent_reputation(
                            self.get_agent_reputation(a_id),
                            contract_token_a,
                            breach_distance=0.0,
                            alpha=self.config.trust_alpha,
                            breach_threshold=self.config.breach_distance_threshold,
                            trust_reference=self.trust_reference_vector
                        )
                        self.agent_reputations[b_id] = update_agent_reputation(
                            self.get_agent_reputation(b_id),
                            contract_token_b,
                            breach_distance=0.0,
                            alpha=self.config.trust_alpha,
                            breach_threshold=self.config.breach_distance_threshold,
                            trust_reference=self.trust_reference_vector
                        )

                    # Prime calorique mutuelle de transaction réussie
                    a["energy"] = min(100.0, a.get("energy", 0.0) + 2.0)
                    b["energy"] = min(100.0, b.get("energy", 0.0) + 2.0)

                    self.contracts_settled_count += 1
                    self.trade_transfers_count += 1

                    trade_info = {
                        "party_a": a_id,
                        "party_b": b_id,
                        "give_a": item_a_offer,
                        "give_b": item_b_demand,
                        "agreement_score": round(score, 3),
                        "clan_a": self.get_agent_clan(a),
                        "clan_b": self.get_agent_clan(b),
                    }
                    settled_trades.append(trade_info)
                    if len(self.recent_contracts) < 30:
                        self.recent_contracts.append(trade_info)

                    if self.config.enable_writing:
                        self.record_market_transaction_to_ledger(trade_info)

        return settled_trades

    def negotiate_consortium_contracts(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Négociation et exécution de contrats de consortium tripartites pour la métallurgie (Phase 5 M3).
        Rassemble 3 agents éligibles (Bois/Charbon + Vivres + Minerai) pour forger des outils de métal.
        """
        settled_consortiums = []
        if not self.config.enable_consortium_contracts or self.grammar is None or len(agents) < 3:
            return settled_consortiums

        # Filtrer agents non sous embargo
        eligible = [
            ag for ag in agents
            if not self.is_agent_under_embargo(str(ag.get("id")))
            and (not self.config.enable_governance or self.get_agent_trust_score(str(ag.get("id"))) >= self.config.embargo_reputation_threshold)
        ]
        if len(eligible) < 3:
            return settled_consortiums

        wood_supplier = None
        food_supplier = None
        ore_supplier = None

        for ag in eligible:
            inv = ag.setdefault("inventory", [])
            types = [str(it.get("type", "")).upper() for it in inv]
            if wood_supplier is None and any(t in ["WOOD", "COAL"] for t in types):
                wood_supplier = ag
            elif food_supplier is None and any(t in ["FOOD", "FRUIT", "GRAIN", "SEED"] for t in types):
                food_supplier = ag
            elif ore_supplier is None and any(t in ["ORE", "IRONORE", "STONE"] for t in types):
                ore_supplier = ag

        if wood_supplier is not None and food_supplier is not None and ore_supplier is not None:
            triplet = [wood_supplier, food_supplier, ore_supplier]
            triplet_ids = {str(ag.get("id")) for ag in triplet}
            if len(triplet_ids) == 3:
                rng_w = np.random.default_rng(abs(hash("WOOD")) % (2**31 - 1))
                v_wood = self.grammar._generate_canonical_unit_vector(rng_w)

                rng_f = np.random.default_rng(abs(hash("FOOD")) % (2**31 - 1))
                v_food = self.grammar._generate_canonical_unit_vector(rng_f)

                rng_o = np.random.default_rng(abs(hash("ORE")) % (2**31 - 1))
                v_ore = self.grammar._generate_canonical_unit_vector(rng_o)

                rng_p = np.random.default_rng(abs(hash("STEEL")) % (2**31 - 1))
                v_steel = self.grammar._generate_canonical_unit_vector(rng_p)

                consortium_token = self.grammar.compose_consortium_contract(v_wood, v_food, v_ore, v_steel)

                agreed, score = verify_consortium_agreement(
                    consortium_token,
                    v_wood,
                    v_food,
                    v_ore,
                    self.grammar,
                    threshold=self.config.consortium_agreement_threshold
                )

                if agreed:
                    # Consommation des intrants
                    inv_w = wood_supplier["inventory"]
                    inv_f = food_supplier["inventory"]
                    inv_o = ore_supplier["inventory"]

                    for i_idx, it in enumerate(inv_w):
                        if str(it.get("type", "")).upper() in ["WOOD", "COAL"]:
                            inv_w.pop(i_idx)
                            break
                    for i_idx, it in enumerate(inv_f):
                        if str(it.get("type", "")).upper() in ["FOOD", "FRUIT", "GRAIN", "SEED"]:
                            inv_f.pop(i_idx)
                            break
                    for i_idx, it in enumerate(inv_o):
                        if str(it.get("type", "")).upper() in ["ORE", "IRONORE", "STONE"]:
                            inv_o.pop(i_idx)
                            break

                    # Attribution des outils et lingots métalliques
                    crafted_tool = {"type": "IronPickaxe", "tier": "METAL", "weight": 2.5}
                    ore_supplier["inventory"].append(crafted_tool)
                    wood_supplier["inventory"].append({"type": "IronIngot", "tier": "METAL"})
                    food_supplier["inventory"].append({"type": "IronSpear", "tier": "METAL"})

                    # Prime calorique industrielle partagée (+15.0 pts selon IndustrialConfig.smelt_energy_reward)
                    surplus = 15.0
                    for ag in triplet:
                        ag["energy"] = min(100.0, ag.get("energy", 0.0) + surplus)

                    self.consortiums_settled_count += 1
                    self.metal_tools_produced_count += 1

                    if hasattr(self.world, "iron_smelted"):
                        self.world.iron_smelted += 1
                    if hasattr(self.world, "metal_tools_crafted"):
                        self.world.metal_tools_crafted += 1

                    consortium_info = {
                        "members": list(triplet_ids),
                        "output_product": "IronPickaxe",
                        "agreement_score": round(score, 3),
                        "surplus_energy": surplus * 3.0,
                    }
                    settled_consortiums.append(consortium_info)
                    if len(self.recent_consortiums) < 20:
                        self.recent_consortiums.append(consortium_info)

                    if self.config.enable_writing:
                        self.record_market_transaction_to_ledger({
                            "party_a": str(ore_supplier.get("id")),
                            "party_b": "FORGE_CONSORTIUM",
                            "agreement_score": round(score, 3),
                        })

        return settled_consortiums

    # ---------------------------------------------------------------------
    # Stigmergie Symbolique, Inscriptions & Épigénétique (Phase 6 M2 & M3)
    # ---------------------------------------------------------------------

    def engrave_stele(
        self,
        agent: Dict[str, Any],
        topic: str,
        content: np.ndarray,
        pos: Optional[Tuple[float, float, float]] = None
    ) -> Optional[InscriptionStone]:
        """
        Grave une stèle fixe pérenne dans le substrat physique (Phase 6 M2).
        Coût métabolique prélevé sur l'agent graveur.
        """
        if not self.config.enable_writing:
            return None

        cost = self.config.engrave_metabolic_cost
        if agent.get("energy", 0.0) < cost:
            return None

        agent["energy"] = max(0.0, agent.get("energy", 0.0) - cost)
        self.total_metabolic_cost += cost

        x = float(pos[0]) if pos else float(agent.get("x", 0.0))
        y = float(pos[1]) if pos else float(agent.get("y", 0.0))
        z = float(pos[2]) if pos and len(pos) > 2 else 0.0

        stele_id = f"stele_{len(self.steles)}_{topic.lower()}"
        tick = getattr(self.world, "tick", 0)

        inscription_stone = InscriptionStone(
            id=stele_id,
            x=x,
            y=y,
            z=z,
            topic=topic.upper(),
            content_vector=np.asarray(content, dtype=np.float32),
            author_id=str(agent.get("id")),
            creation_tick=tick,
            read_count=0,
            durability=1.0,
        )
        self.steles[stele_id] = inscription_stone
        self.steles_engraved_count += 1

        scripture_info = {
            "id": stele_id,
            "type": "STELE",
            "topic": topic.upper(),
            "author": str(agent.get("id")),
            "pos": (x, y, z),
            "tick": tick,
        }
        if len(self.recent_scriptures) < 30:
            self.recent_scriptures.append(scripture_info)

        return inscription_stone

    def read_nearest_stele(
        self,
        agent: Dict[str, Any],
        max_radius: Optional[float] = None
    ) -> Optional[InscriptionStone]:
        """
        Lit la stèle la plus proche dans le rayon sensoriel de lecture directionnelle (Phase 6 M2).
        """
        if not self.config.enable_writing or not self.steles:
            return None

        radius = max_radius or self.config.read_inscription_radius
        ax = float(agent.get("x", 0.0))
        ay = float(agent.get("y", 0.0))

        nearest_stele = None
        min_dist = float('inf')

        for stele in self.steles.values():
            dist = float(np.sqrt((ax - stele.x)**2 + (ay - stele.y)**2))
            if dist <= radius and dist < min_dist:
                min_dist = dist
                nearest_stele = stele

        if nearest_stele is not None:
            read_steles = agent.setdefault("lu_read_steles", set())
            if nearest_stele.id not in read_steles:
                nearest_stele.read_count += 1
                self.steles_read_count += 1
                # Transmission épigénétique du savoir si l'agent est éligible
                self.apply_epigenetic_prior_boost(agent, nearest_stele)

        return nearest_stele

    def engrave_tablet(
        self,
        agent: Dict[str, Any],
        topic: str,
        content: np.ndarray
    ) -> SlateTablet:
        """
        Grave une tablette portative d'inventaire (Phase 6 M2).
        """
        ag_id = str(agent.get("id"))
        tab_id = f"tablet_{len(self.tablets)}_{ag_id}"
        tick = getattr(self.world, "tick", 0)

        tablet = SlateTablet(
            id=tab_id,
            topic=topic.upper(),
            content_vector=np.asarray(content, dtype=np.float32),
            owner_id=ag_id,
            creation_tick=tick,
            read_count=0,
        )
        self.tablets[tab_id] = tablet

        inv = agent.setdefault("inventory", [])
        inv.append({"type": "SlateTablet", "tablet_id": tab_id, "topic": topic.upper()})

        return tablet

    def apply_epigenetic_prior_boost(
        self,
        agent: Dict[str, Any],
        stele: InscriptionStone
    ) -> bool:
        """
        Transmission de prior culturel et épigénétique (Phase 6 M3) :
        Quand un agent jeune ou apprenti lit une stèle de savoir, son état récurrent H ou sa projection
        reçoit un amorçage direct contournant les générations d'essais-erreurs.
        """
        ag_id = str(agent.get("id"))

        read_steles = agent.setdefault("lu_read_steles", set())
        if stele.id in read_steles:
            return False

        read_steles.add(stele.id)

        proj = self._get_agent_projection(ag_id, 8)
        content_extracted = getattr(stele, "_cached_content", None)
        if content_extracted is None:
            if self.grammar is not None:
                content_extracted = self.grammar.extract_inscription_content(stele.content_vector)
            else:
                content_extracted = stele.content_vector
            stele._cached_content = content_extracted

        proj[-1] = 0.5 * proj[-1] + 0.5 * content_extracted[:self.dim]
        norm = np.linalg.norm(proj[-1]) + 1e-12
        proj[-1] /= norm

        boost = self.config.epigenetic_prior_boost
        agent["energy"] = min(100.0, agent.get("energy", 0.0) + boost)
        agent["lu_prior_boosted"] = True
        self.epigenetic_boosts_count += 1
        return True

    def record_market_transaction_to_ledger(self, trade_info: Dict[str, Any]) -> None:
        """
        Enregistre une transaction sur le grand livre comptable de marché (Phase 6 M2).
        """
        if not self.config.enable_arithmetic:
            return

        self.arithmetic_ledger_entries_count += 1
        party_a = trade_info.get("party_a", "")
        party_b = trade_info.get("party_b", "")

        for party, partner, role in [(party_a, party_b, "CREDIT"), (party_b, party_a, "DEBT")]:
            tab_id = f"market_ledger_{party}"
            if tab_id not in self.tablets:
                dummy_v = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)
                self.tablets[tab_id] = SlateTablet(
                    id=tab_id,
                    topic="MARKET_LEDGER",
                    content_vector=dummy_v,
                    owner_id=party,
                    creation_tick=getattr(self.world, "tick", 0),
                )
            self.tablets[tab_id].balance_entries.append({
                "partner": partner,
                "role": role,
                "score": trade_info.get("agreement_score", 1.0),
                "tick": getattr(self.world, "tick", 0),
            })

    def step(self) -> Dict[str, Any]:
        """
        Cycle de communication continue in-world pour le tick actuel :
        1. Chaque agent génère son Gigatoken z_i.
        2. Spécialisation des rôles tribaux (Arc 5).
        3. Propagation spatiale selon hear_radius et régulation ToM.
        4. Délibération nocturne collective autour du feu de camp.
        5. Traduction latente via MutualLatentTranslator avec coût métabolique.
        6. Orientation d'action et alignement référentiel.
        """
        agents = getattr(self.world, "agents", [])
        if len(agents) < 2:
            return {
                "transmissions": 0, "alignments": 0, "coordinations": 0,
                "cooperative_hunts": 0, "tom_silences": 0, "deliberations": 0
            }

        if self.config.emergent_roles:
            self.infer_emergent_roles(agents)
        elif self.config.role_specialization:
            self.assign_tribal_roles(agents)

        # 1. Encodage latent pour tous les agents & reset des flags par tick
        for ag in agents:
            ag["lu_multi_hop_relayed"] = False
            ag["cooperative_hunt_active"] = False
            inv = ag.get("inventory", [])
            if any(it.get("tier") == "METAL" for it in inv):
                ag["energy"] = min(100.0, ag.get("energy", 0.0) + 0.20)
            self.encode_agent_latent(ag)

        # Répulsion physique et purge temporelle des sanctions (Phase 5 M2)
        if self.config.enable_governance:
            self.apply_physical_embargo_repulsion(agents)
            for ag_id in list(self.agent_embargos.keys()):
                self.agent_embargos[ag_id] -= 1
                if self.agent_embargos[ag_id] <= 0:
                    del self.agent_embargos[ag_id]
            for ag in agents:
                ag_id = str(ag.get("id"))
                r = self.get_agent_reputation(ag_id)
                self.agent_reputations[ag_id] = decay_reputation_towards_neutral(
                    r, self.neutral_reference_vector, decay_rate=self.config.reputation_decay_rate
                )

        # Dérive géométrique locale des dialectes claniques (Phase 4 M1)
        if self.config.enable_dialects:
            self.evolve_clan_dialects(agents)

        tick_transmissions = 0
        tick_alignments = 0
        tick_coordinations = 0
        tick_cooperative_hunts = 0
        tick_tom_silences = 0

        R = self.config.hear_radius

        # Détection globale des agents au coin du feu pour délibération (Phase 3 M3)
        if self.config.enable_deliberation and self.world is not None:
            items = getattr(self.world, "items", [])
            fires = [it for it in items if str(it.get("type", "")).lower() == "fire" or str(it.get("name", "")).lower() == "fire"]
            if fires:
                campfire_agents = []
                for ag in agents:
                    for f in fires:
                        if abs(ag.get("x", 0) - f.get("x", 0)) + abs(ag.get("y", 0) - f.get("y", 0)) <= 3:
                            campfire_agents.append(ag)
                            break
                if len(campfire_agents) >= 2:
                    self.deliberate_at_campfire(campfire_agents, rounds=self.config.deliberation_rounds)

        # 2. Diffusion par paires dans le rayon d'audition avec ToM
        for i, a in enumerate(agents):
            za = a["lu_latent"]
            a_id = str(a.get("id", f"ag_{i}"))
            for j, b in enumerate(agents):
                if i >= j:
                    continue
                b_id = str(b.get("id", f"ag_{j}"))
                dist = abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])
                if dist > R:
                    continue

                # Évaluation Theory of Mind (ToM) : filtrage pragmatique
                za_prag, a_silent = self.evaluate_tom_emission(a_id, b_id, za)
                zb = b["lu_latent"]
                zb_prag, b_silent = self.evaluate_tom_emission(b_id, a_id, zb)

                # Économie métabolique si silence ToM
                if a_silent:
                    tick_tom_silences += 1
                    self.tom_silences_count += 1
                    a["energy"] = min(100.0, a.get("energy", 0.0) + self.config.tom_silence_metabolic_saving)
                    self.tom_energy_saved += self.config.tom_silence_metabolic_saving
                if b_silent:
                    tick_tom_silences += 1
                    self.tom_silences_count += 1
                    b["energy"] = min(100.0, b.get("energy", 0.0) + self.config.tom_silence_metabolic_saving)
                    self.tom_energy_saved += self.config.tom_silence_metabolic_saving

                if a_silent and b_silent:
                    continue  # Tous deux choisissent le silence pragmatique informatif

                tick_transmissions += 1
                a["lu_signals_emitted"] = a.get("lu_signals_emitted", 0) + 1
                b["lu_signals_received"] = b.get("lu_signals_received", 0) + 1

                # Coût métabolique d'information
                cost = self.config.signal_metabolic_cost
                if not a_silent:
                    a["energy"] = max(0.0, a.get("energy", 0.0) - cost)
                    self.total_metabolic_cost += cost
                if not b_silent:
                    b["energy"] = max(0.0, b.get("energy", 0.0) - cost)
                    self.total_metabolic_cost += cost

                # Détection d'un feu de camp actif à proximité (EXP-9 : Rituels et Maîtrise du Feu)
                near_fire = False
                if self.config.campfire_cultural_boost and self.world is not None:
                    items = getattr(self.world, "items", [])
                    fires = [it for it in items if str(it.get("type", "")).lower() == "fire" or str(it.get("name", "")).lower() == "fire"]
                    for f in fires:
                        dist_a = abs(a["x"] - f.get("x", 0)) + abs(a["y"] - f.get("y", 0))
                        dist_b = abs(b["x"] - f.get("x", 0)) + abs(b["y"] - f.get("y", 0))
                        if dist_a <= 3 or dist_b <= 3:
                            near_fire = True
                            break

                # Ajout de bruit physique d'atténuation
                effective_noise = self.config.noise_level * (1.0 + float(dist) / max(1, R))
                # Pénalité de bruit géométrique inter-clans (Phase 4 M1)
                if self.config.enable_dialects:
                    clan_a = self.get_agent_clan(a)
                    clan_b = self.get_agent_clan(b)
                    if clan_a != clan_b:
                        u_a = self.get_clan_subspace(clan_a)
                        u_b = self.get_clan_subspace(clan_b)
                        d_g = grassmann_distance(u_a, u_b)
                        effective_noise *= (1.0 + float(d_g) * 0.4)

                if near_fire:
                    effective_noise *= 0.2
                    self.campfire_transmissions_count += 1
                    a["energy"] = min(100.0, a.get("energy", 0.0) + 0.1)
                    b["energy"] = min(100.0, b.get("energy", 0.0) + 0.1)

                za_noisy = za_prag + np.random.randn(self.dim).astype(np.float32) * effective_noise
                zb_noisy = zb_prag + np.random.randn(self.dim).astype(np.float32) * effective_noise

                # 3. Traduction mutuelle croisée A -> B et B -> A
                zb_pred = self.shared_translator.translate_a_to_b(za_noisy)
                za_pred = self.shared_translator.translate_b_to_a(zb_noisy)

                # Mise à jour des croyances ToM post-observation
                self.update_peer_belief(a_id, b_id, zb_pred)
                self.update_peer_belief(b_id, a_id, za_pred)

                # Injection neuronale directe dans les connectomes Mamba (Option A - Physique & Biosphère)
                if "model" in b and hasattr(b["model"], "receive_gigatoken"):
                    b["model"].receive_gigatoken(zb_pred)
                if "model" in a and hasattr(a["model"], "receive_gigatoken"):
                    a["model"].receive_gigatoken(za_pred)

                # Calcul de la similarité cosinus (alignement sémantique)
                norm_b = np.linalg.norm(zb) * np.linalg.norm(zb_pred) + 1e-7
                cos_sim_b = float(np.dot(zb, zb_pred) / norm_b)

                norm_a = np.linalg.norm(za) * np.linalg.norm(za_pred) + 1e-7
                cos_sim_a = float(np.dot(za, za_pred) / norm_a)

                mean_align = (cos_sim_a + cos_sim_b) / 2.0

                # Entraînement en ligne par co-adaptation
                self.shared_translator.train_step(za.reshape(1, -1), zb.reshape(1, -1))

                # 4. Récompense d'alignement si consensus latent
                if mean_align >= self.config.alignment_threshold:
                    tick_alignments += 1
                    a["energy"] = min(100.0, a.get("energy", 0.0) + self.config.alignment_reward)
                    b["energy"] = min(100.0, b.get("energy", 0.0) + self.config.alignment_reward)

                    # 5. Coordination de meute (Pack Coordination)
                    if self.config.pack_coordination:
                        dir_x = float(zb_pred[0])
                        dir_y = float(zb_pred[1])
                        if abs(dir_x) > 0.05 or abs(dir_y) > 0.05:
                            tick_coordinations += 1
                            b["lu_steer_bias"] = (dir_x, dir_y)
                            b["lu_signal_source"] = a.get("id")

                            # Synergie de rôle (SCOUT -> HUNTER ou synergie endogène sans étiquettes forcées)
                            is_scout_to_hunter = (a.get("role") == ROLE_SCOUT and b.get("role") == ROLE_HUNTER)
                            has_directional_signal = (abs(dir_x) > 0.05 or abs(dir_y) > 0.05)
                            is_cooperative_synergy = is_scout_to_hunter or (self.config.emergent_roles and has_directional_signal)
                            multiplier = self.config.cooperative_prey_multiplier if is_cooperative_synergy else 1.0
                            if is_cooperative_synergy:
                                tick_cooperative_hunts += 1
                                self.cooperative_hunts_count += 1
                                b["cooperative_hunt_active"] = True
                                # Partage symbiotique de la chasse : le scout et le hunter profitent de la synergie
                                a["energy"] = min(100.0, a.get("energy", 0.0) + self.config.referential_bonus * 0.8)

                            b["energy"] = min(100.0, b.get("energy", 0.0) + self.config.referential_bonus * multiplier)

                # Mémorisation du token pour audit
                if len(self.recent_tokens) < self.config.max_history_tokens:
                    self.recent_tokens.append(za.copy())

        # 6. Propagation acoustique multi-hop (Phase 2 - Jalon M2)
        tick_relays = 0
        if self.config.enable_multi_hop and tick_coordinations > 0:
            for b in agents:
                steer_bias = b.get("lu_steer_bias")
                source_id = b.get("lu_signal_source")
                if steer_bias is None:
                    continue
                source_agent = next((ag for ag in agents if ag.get("id") == source_id), None)
                for c in agents:
                    if c is b or c.get("lu_multi_hop_relayed", False):
                        continue
                    # Si c est hors de portée directe de la source originelle
                    if source_agent is not None:
                        dist_source_c = abs(source_agent["x"] - c["x"]) + abs(source_agent["y"] - c["y"])
                        if dist_source_c <= R:
                            continue  # Déjà à portée directe
                    dist_bc = abs(b["x"] - c["x"]) + abs(b["y"] - c["y"])
                    if dist_bc <= R:
                        relayed_bias = (
                            steer_bias[0] * self.config.relay_decay,
                            steer_bias[1] * self.config.relay_decay,
                        )
                        c["lu_steer_bias"] = relayed_bias
                        c["lu_multi_hop_relayed"] = True
                        if b.get("cooperative_hunt_active", False):
                            c["cooperative_hunt_active"] = True
                            tick_cooperative_hunts += 1
                            self.cooperative_hunts_count += 1
                            c["energy"] = min(100.0, c.get("energy", 0.0) + self.config.referential_bonus * 1.5)
                            b["energy"] = min(100.0, b.get("energy", 0.0) + self.config.referential_bonus * 0.8)
                            if source_agent is not None:
                                source_agent["energy"] = min(100.0, source_agent.get("energy", 0.0) + self.config.referential_bonus * 0.5)
                        tick_relays += 1
                        self.multi_hop_relays_count += 1
                        c["energy"] = min(100.0, c.get("energy", 0.0) + self.config.alignment_reward)

        # 7. Négociation de contrats de troc décentralisés (Phase 4 M2)
        tick_trades = 0
        if self.config.enable_trade_contracts:
            trades = self.negotiate_trade_contracts(agents)
            tick_trades = len(trades)

        # 8. Consortiums multipartites métallurgiques (Phase 5 M3)
        tick_consortiums = 0
        if self.config.enable_consortium_contracts:
            consortiums = self.negotiate_consortium_contracts(agents)
            tick_consortiums = len(consortiums)

        # 9. Écriture stigmargique, érosion géologique & transmission épigénétique (Phase 6 M1-M3)
        tick_steles_read = 0
        if self.config.enable_writing and self.steles:
            # Érosion géologique très lente
            for s_id, stele in self.steles.items():
                stele.content_vector = decay_inscription_geological(
                    stele.content_vector,
                    noise_std=self.config.inscription_geological_decay_std
                )
            # Lecture des stèles pour les agents proches
            for ag in agents:
                read_res = self.read_nearest_stele(ag)
                if read_res is not None:
                    tick_steles_read += 1

        # 10. Ratification de traités diplomatiques & protection fédérale (Phase 7 M2)
        tick_treaties = 0
        if getattr(self.config, "enable_diplomacy", True) and self.federal_monument is not None:
            mon_x, mon_y = self.federal_monument.x, self.federal_monument.y
            near_monument = [ag for ag in agents if (abs(ag.get("x", 0) - mon_x) + abs(ag.get("y", 0) - mon_y)) <= 3]
            if len(near_monument) >= 2:
                for i in range(len(near_monument)):
                    for j in range(i + 1, min(len(near_monument), i + 3)):
                        ag_i = near_monument[i]
                        ag_j = near_monument[j]
                        id_i = str(ag_i.get("id"))
                        id_j = str(ag_j.get("id"))
                        if id_j not in ag_i.get("federal_treaties", set()):
                            if self.ratify_federal_treaty(ag_i, ag_j):
                                tick_treaties += 1
                                self.constitutional_protections_count += 1

        # 11. Auto-exécution de Smart Contracts programmable (Phase 8 M2)
        tick_smart_contracts = 0
        if getattr(self.config, "enable_neural_vm", True) and self.federal_monument is not None and self.federal_monument.smart_contracts:
            mon_x, mon_y = self.federal_monument.x, self.federal_monument.y
            near_vm = [ag for ag in agents if (abs(ag.get("x", 0) - mon_x) + abs(ag.get("y", 0) - mon_y)) <= 3]
            for ag in near_vm:
                z = ag.get("lu_latent")
                if z is None:
                    z = self.encode_agent_latent(ag)
                exec_ok, _, cid = self.execute_inworld_smart_contract(ag, z)
                if exec_ok:
                    tick_smart_contracts += 1

        # 12. Clauses temporelles LTL & Programmes Latents Synthétisés (Phase 9 M2)
        tick_temporal_released = 0
        tick_programs_executed = 0
        if getattr(self.config, "enable_ltl_temporal_logic", True):
            tick_temporal_released = self.step_temporal_escrows(agents)

        if getattr(self.config, "enable_program_synthesis", True) and self.federal_monument is not None and self.federal_monument.synthesized_programs:
            mon_x, mon_y = self.federal_monument.x, self.federal_monument.y
            near_prog = [ag for ag in agents if (abs(ag.get("x", 0) - mon_x) + abs(ag.get("y", 0) - mon_y)) <= 3]
            for ag in near_prog:
                # Exécuter le dernier programme synthétisé pour l'agent
                last_prog = self.federal_monument.synthesized_programs[-1]
                exec_res = self.execute_inworld_program(ag, last_prog["program_id"])
                if exec_res.get("converged", False):
                    tick_programs_executed += 1

        # 13. Auto-Compilation Récursive du Connectome au FederalMonument (Phase 10 M2)
        tick_self_compilations = 0
        tick_now = getattr(self.world, "tick", getattr(self.world, "ticks", 0)) if self.world is not None else 0
        if getattr(self.config, "enable_self_compilation", True) and self.federal_monument is not None:
            mon_x, mon_y = self.federal_monument.x, self.federal_monument.y
            near_altar = [ag for ag in agents if (abs(ag.get("x", 0) - mon_x) + abs(ag.get("y", 0) - mon_y)) <= 3]
            for ag in near_altar:
                model = ag.get("model") or ag.get("brain") or getattr(self.world, "model", None)
                last_attempt = ag.get("last_connectome_attempt_tick", -999)
                if model is not None and not ag.get("connectome_self_compiled", False) and (tick_now - last_attempt >= 5):
                    ag["last_connectome_attempt_tick"] = tick_now
                    ok = self.verify_and_apply_connectome_evolution(ag, model)
                    if ok:
                        tick_self_compilations += 1

        # 14. Méta-Simulation Contrefactuelle & Rêve Sémantique Partagé au Feu de Camp (Phase 11 M2)
        tick_shared_dreams = 0
        tick_dreams_ratified = 0
        if getattr(self.config, "enable_counterfactual_dreaming", True) and self.world is not None:
            tick_now = getattr(self.world, "tick", getattr(self.world, "ticks", 0))
            if tick_now % 5 == 0:
                items = getattr(self.world, "items", [])
                fires = [it for it in items if str(it.get("type", "")).lower() == "fire" or str(it.get("name", "")).lower() == "fire"]
                if fires:
                    campfire_agents = []
                    for ag in agents:
                        for f in fires:
                            if abs(ag.get("x", 0) - f.get("x", 0)) + abs(ag.get("y", 0) - f.get("y", 0)) <= 3:
                                campfire_agents.append(ag)
                                break
                    if len(campfire_agents) >= 2:
                        ratified = self.deliberate_shared_dreams_at_campfire(campfire_agents)
                        tick_dreams_ratified = len(ratified)
                        tick_shared_dreams = len(ratified)

        # 15. La Noosphère Latente & Conseil Synarchique Trans-Mondes (Phase 12 M2)
        tick_noosphere_broadcasts = 0
        tick_synarchic_councils = 0
        if getattr(self.config, "enable_noosphere_grid", True) and self.world is not None:
            tick_now = getattr(self.world, "tick", getattr(self.world, "ticks", 0))
            if tick_now % 5 == 0:
                self.update_noosphere_resonance_grid()
                if len(agents) >= 2:
                    council_res = self.convene_synarchic_noosphere_council(agents)
                    if council_res.get("ratified", False):
                        tick_synarchic_councils += 1
                        tick_noosphere_broadcasts += council_res.get("participants_count", 0)

        # 16. Morphogenèse Noogénétique, Réaction-Diffusion & Hyper-Connectome Distribué (Phase 13 M2)
        tick_pde_steps = 0
        tick_hyperconnectome_updates = 0
        tick_noogenetic_distillations = 0
        if getattr(self.config, "enable_reaction_diffusion_pde", True) and self.world is not None:
            tick_now = getattr(self.world, "tick", getattr(self.world, "ticks", 0))
            if tick_now % 3 == 0:
                self.step_reaction_diffusion_field(dt=0.20)
                tick_pde_steps += 1
                if getattr(self.config, "enable_hyperconnectome_distillation", True):
                    tick_hyperconnectome_updates += 1
                    for ag in agents:
                        is_newborn = ag.get("age", 999) <= 5
                        in_distress = ag.get("energy", 50.0) < 25.0
                        if (is_newborn or in_distress) and not ag.get("hyperconnectome_distilled_this_era", False):
                            succ, _ = self.distill_noogenetic_prior_to_agent(ag, alpha=0.35)
                            if succ:
                                tick_noogenetic_distillations += 1
                                ag["hyperconnectome_distilled_this_era"] = True

        # 17. Singularité Autopoïétique & Méta-Langage Holographique (Phase 14 M2)
        tick_autopoietic_steps = 0
        tick_teleological_convergences = 0
        tick_singularity_dividends = 0
        if getattr(self.config, "enable_autopoietic_singularity", True) and self.world is not None:
            tick_now = getattr(self.world, "tick", getattr(self.world, "ticks", 0))
            if tick_now % 5 == 0:
                self.step_autopoietic_singularity()
                tick_autopoietic_steps += 1
                if len(agents) >= 2:
                    succ, _ = self.resonate_teleological_convergence(agents)
                    if succ:
                        tick_teleological_convergences += 1
                        tick_singularity_dividends += len(agents)

        self.total_transmissions += tick_transmissions
        self.successful_alignments += tick_alignments
        self.pack_coordinations_count += tick_coordinations

        return {
            "transmissions": tick_transmissions,
            "alignments": tick_alignments,
            "coordinations": tick_coordinations,
            "multi_hop_relays": tick_relays,
            "total_multi_hop_relays": self.multi_hop_relays_count,
            "cooperative_hunts": tick_cooperative_hunts,
            "total_cooperative_hunts": self.cooperative_hunts_count,
            "total_transmissions": self.total_transmissions,
            "successful_alignments": self.successful_alignments,
            "total_metabolic_cost": round(self.total_metabolic_cost, 4),
            "recipes_transmitted": self.recipes_transmitted,
            "campfire_transmissions": self.campfire_transmissions_count,
            "tom_silences": self.tom_silences_count,
            "tom_energy_saved": round(self.tom_energy_saved, 4),
            "deliberation_events": self.deliberation_events_count,
            "deliberation_consensuses": self.deliberation_consensus_count,
            "contracts_settled": self.contracts_settled_count,
            "trade_transfers": self.trade_transfers_count,
            "tick_trades": tick_trades,
            "sanctions": self.sanctions_count,
            "consortiums_settled": self.consortiums_settled_count,
            "metal_tools_produced": self.metal_tools_produced_count,
            "tick_consortiums": tick_consortiums,
            "steles_engraved": self.steles_engraved_count,
            "steles_read": self.steles_read_count,
            "tick_steles_read": tick_steles_read,
            "epigenetic_boosts": self.epigenetic_boosts_count,
            "ledger_entries": self.arithmetic_ledger_entries_count,
            "treaties_ratified": self.treaties_ratified_count,
            "meta_rules_compiled": self.meta_rules_compiled_count,
            "constitutional_protections": self.constitutional_protections_count,
            "tick_treaties": tick_treaties,
            "smart_contracts_registered": self.smart_contracts_registered_count,
            "smart_contracts_executed": self.smart_contracts_executed_count,
            "tick_smart_contracts": tick_smart_contracts,
            "causal_experiments": self.causal_experiments_count,
            "causal_hypotheses_validated": self.causal_hypotheses_validated_count,
            "bft_consensus_events": self.bft_consensus_events_count,
            "bft_byzantine_mitigated": self.bft_byzantine_mitigated_count,
            "temporal_clauses_evaluated": self.temporal_clauses_evaluated_count,
            "temporal_escrows_released": self.temporal_escrows_released_count,
            "tick_temporal_released": tick_temporal_released,
            "programs_synthesized": self.programs_synthesized_count,
            "programs_executed": self.programs_executed_count,
            "tick_programs_executed": tick_programs_executed,
            "analogy_transfers": self.analogy_transfers_count,
            "self_compiled_mutations": self.self_compiled_mutations_count,
            "hoare_proofs_verified": self.hoare_proofs_verified_count,
            "hoare_rejections": self.hoare_rejections_count,
            "connectome_evolutions_applied": self.connectome_evolutions_applied_count,
            "tick_self_compilations": tick_self_compilations,
            "shared_dreams": self.shared_dreams_count,
            "dreams_ratified": self.dreams_ratified_count,
            "counterfactual_rollouts": self.counterfactual_rollouts_count,
            "counterfactual_gains_total": round(self.counterfactual_gains_total, 4),
            "tick_shared_dreams": tick_shared_dreams,
            "tick_dreams_ratified": tick_dreams_ratified,
            "noosphere_broadcasts": self.noosphere_broadcasts_count,
            "epistemic_evaluations": self.epistemic_evaluations_count,
            "high_uncertainty_interventions": self.high_uncertainty_interventions_count,
            "synarchic_councils": self.synarchic_councils_count,
            "synarchic_ratifications": self.synarchic_ratifications_count,
            "tick_noosphere_broadcasts": tick_noosphere_broadcasts,
            "tick_synarchic_councils": tick_synarchic_councils,
            "pde_steps": self.pde_steps_count,
            "hyperconnectome_updates": self.hyperconnectome_updates_count,
            "noogenetic_distillations": self.noogenetic_distillations_count,
            "pde_energy": round(self.pde_engine.compute_pde_energy(), 4) if self.pde_engine is not None else 0.0,
            "tick_pde_steps": tick_pde_steps,
            "tick_hyperconnectome_updates": tick_hyperconnectome_updates,
            "tick_noogenetic_distillations": tick_noogenetic_distillations,
            "autopoietic_steps": self.autopoietic_steps_count,
            "holographic_projections": self.holographic_projections_count,
            "teleological_convergences": self.teleological_convergences_count,
            "singularity_dividends": self.singularity_dividends_count,
            "bekenstein_entropy": round(self.autopoietic_engine.compute_bekenstein_entropy(), 4) if self.autopoietic_engine is not None else 0.0,
            "tick_autopoietic_steps": tick_autopoietic_steps,
            "tick_teleological_convergences": tick_teleological_convergences,
            "tick_singularity_dividends": tick_singularity_dividends,
        }


    def explain_agent_thought(self, agent: Dict[str, Any], lang: str = "fr") -> str:
        """Décompile l'état latent actuel d'un agent en langage naturel explicable."""
        z = agent.get("lu_latent")
        if z is None:
            z = self.encode_agent_latent(agent)

        agent_id = str(agent.get("id", "0"))[:4]
        target_name = "Mammouth" if float(z[3]) > 0.5 else "Ressource"
        rel_type = "TARGETS" if (float(z[0])**2 + float(z[1])**2 > 0.05) else "PERCEIVES"

        dsl_stmt = f"(Agent_{agent_id}:AGENT)-[{rel_type}]->({target_name}:CONCEPT)"
        report = self.explainer.explain_dsl_string(dsl_stmt)
        text = report.human_text_fr if lang == "fr" else report.human_text_en
        return f"{text} (Dim: {self.dim})"

    def compute_tribe_dialects(self, cluster_labels: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """
        Mesure la divergence dialectale géométrique entre tribus/clans (Axe 2 - S'améliorer).
        Calcule la distance de Grassmann entre les sous-espaces de projection sémantique.
        """
        agents = getattr(self.world, "agents", [])
        if len(agents) < 2:
            return {"dialect_divergence": 0.0, "tribe_count": 0, "status": "insufficient_agents"}

        tribes: Dict[int, List[str]] = {}
        for ag in agents:
            ag_id = ag["id"]
            if cluster_labels and ag_id in cluster_labels:
                t_id = cluster_labels[ag_id]
            else:
                mid = getattr(self.world, "size", 10) / 2.0
                t_id = (0 if ag["x"] < mid else 1) + (0 if ag["y"] < mid else 2)
            tribes.setdefault(t_id, []).append(ag_id)

        tribe_subspaces: Dict[int, np.ndarray] = {}
        for t_id, members in tribes.items():
            if not members:
                continue
            projs = [self._get_agent_projection(m, 8) for m in members]
            mean_proj = np.mean(projs, axis=0)
            u, _, _ = np.linalg.svd(mean_proj, full_matrices=False)
            tribe_subspaces[t_id] = u[:, :min(u.shape[1], 4)]

        t_keys = list(tribe_subspaces.keys())
        distances = []
        for i in range(len(t_keys)):
            for j in range(i + 1, len(t_keys)):
                u1 = tribe_subspaces[t_keys[i]]
                u2 = tribe_subspaces[t_keys[j]]
                _, s, _ = np.linalg.svd(np.dot(u1.T, u2))
                s = np.clip(s, -1.0, 1.0)
                thetas = np.arccos(s)
                grassmann_dist = float(np.sqrt(np.sum(thetas ** 2)))
                distances.append(grassmann_dist)

        mean_dist = float(np.mean(distances)) if distances else float('nan')
        return {
            "dialect_divergence": mean_dist,
            "tribe_count": len(tribe_subspaces),
            "inter_tribe_distances": distances,
            "status": "computed",
        }

