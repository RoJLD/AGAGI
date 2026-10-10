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
)
from src.metaprog.lu_symbolic_bridge import MultiTribalTranslator
from src.graph_rag.async_logger import logger


ROLE_SCOUT = "SCOUT"
ROLE_CRAFTER = "CRAFTER"
ROLE_HUNTER = "HUNTER"
ALL_ROLES = [ROLE_SCOUT, ROLE_HUNTER, ROLE_CRAFTER]


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
        self.neutral_reference_vector: np.ndarray = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)

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

        is_consensus = mean_sim >= self.config.deliberation_consensus_threshold
        if is_consensus:
            self.deliberation_consensus_count += 1
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

        return settled_consortiums

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

