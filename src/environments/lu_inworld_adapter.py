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
from src.metaprog.lu_algebra import LUCompositionalGrammar, LUAlgebraConfig
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
            self.encode_agent_latent(ag)

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

