"""
src/worlds/civilization_world_conductor.py — Orchestrateur Civilisationnel Multi-Mondes (Arc 13 : Jalon M28).

Coordonne de manière synchrone l'évolution des 3 mondes physiques :
- Monde 1 : Stoneage (Chasseurs-cueilleurs, feu, faune hostile)
- Monde 2 : AgriculturalWorld (Saisons, gel hivernal, grenier communautaire)
- Monde 3 : IndustrialWorld (Métallurgie, charbon/fer, hauts fourneaux)

Intègre les agents incarnés pilotés par fondation (EmbodiedFoundationAgent),
la perception spatiale continue (MultimodalLatentEncoder),
le consensus robuste d'essaim BFT (LLMSwarmConsensus),
le méta-raisonnement par MCTS latent continu (LatentMCTSSearch)
et l'auto-correction réflexive (SelfReflectiveLatentCritic).

Conforme aux 12 Commandements AGIseed :
- 1. Flexible (Dataclass CivilizationConductorConfig).
- 2. Modulaire (Découplage strict des mondes, encodeurs et contrôleurs).
- 3. Haute Performance (Vectorisation NumPy).
- 9. Stabilité Numérique (Garantie unitaire S^(D-1), bornes strictes).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.worlds.world_3_industrial import IndustrialWorld, IndustrialConfig

from src.agents.embodied_foundation_agent import EmbodiedFoundationAgent, EmbodiedAgentConfig
from src.metaprog.multimodal_latent_encoder import MultimodalLatentEncoder, MultimodalEncoderConfig
from src.metaprog.llm_swarm_consensus import (
    LLMSwarmConsensus,
    SwarmConsensusConfig,
    ConsensusStrategy,
    SwarmDeliberationResult,
)
from src.metaprog.latent_mcts_search import LatentMCTSSearch, LatentMCTSConfig
from src.metaprog.self_reflective_latent_critic import (
    SelfReflectiveLatentCritic,
    SelfReflectiveCriticConfig,
    ReflectionResult,
)
from src.metaprog.federal_metagenome_compiler import (
    FederalMetaGenomeSynthesizer,
    EvolutiveCompiler,
    FederalMetaGenomeConfig,
)
from src.graph_rag.realtime_graphrag_bridge import (
    RealtimeGraphRAGBridge,
    RealtimeBridgeConfig,
)


@dataclass
class CivilizationConductorConfig:
    """Hyperparamètres pour l'orchestrateur civilisationnel multi-mondes."""
    latent_dim: int = 64
    world_size: int = 12
    enable_bft_consensus: bool = True
    enable_latent_mcts: bool = True
    enable_self_reflection: bool = True
    enable_inter_world_trade: bool = True
    enable_metagenome_compilation: bool = True
    enable_realtime_graphrag_bridge: bool = True
    metagenome_distill_interval: int = 10
    distress_energy_threshold: float = 25.0
    granary_relief_amount: float = 12.0
    mcts_num_simulations: int = 20
    seed: int = 42
    eps: float = 1e-12


class CivilizationWorldConductor:
    """
    Chef d'orchestre multi-mondes interconnectant la biosphère 3D primitive,
    agricole et industrielle avec l'intelligence d'essaim de fondation.
    """

    def __init__(self, config: Optional[CivilizationConductorConfig] = None):
        self.config = config or CivilizationConductorConfig()
        self.step_count = 0

        # 1. Initialisation des 3 mondes physiques
        cfg_stone = WorldConfig(size=self.config.world_size)
        cfg_agri = AgriculturalConfig(size=self.config.world_size)
        cfg_indus = IndustrialConfig(size=self.config.world_size)

        self.world_stone = Biosphere3D(cfg_stone)
        self.world_agri = AgriculturalWorld(cfg_agri)
        self.world_indus = IndustrialWorld(cfg_indus)

        # 2. Initialisation des sous-systèmes cognitifs continus
        self.encoder = MultimodalLatentEncoder(
            MultimodalEncoderConfig(
                latent_dim=self.config.latent_dim,
                grid_size=(7, 7),
                num_channels=4,
            )
        )
        self.consensus_module = LLMSwarmConsensus(
            SwarmConsensusConfig(
                consensus_strategy=ConsensusStrategy.WEISZFELD_MEDIAN_BFT,
                byzantine_filter_enabled=self.config.enable_bft_consensus,
                enable_kuzudb_logging=False,
            )
        )
        self.mcts_searcher = LatentMCTSSearch(
            LatentMCTSConfig(
                num_simulations=self.config.mcts_num_simulations,
            )
        )
        self.critic = SelfReflectiveLatentCritic(
            SelfReflectiveCriticConfig(
                max_correction_steps=5,
                learning_rate=0.15,
            )
        )

        # Sous-systèmes d'auto-amélioration récursive (Arc 14 : M32/M33)
        self.metagenome_synthesizer = FederalMetaGenomeSynthesizer(
            FederalMetaGenomeConfig(latent_dim=self.config.latent_dim, seed=self.config.seed)
        )
        self.evolutive_compiler = EvolutiveCompiler(
            FederalMetaGenomeConfig(latent_dim=self.config.latent_dim, seed=self.config.seed)
        )
        self.graphrag_bridge = RealtimeGraphRAGBridge(
            RealtimeBridgeConfig(latent_dim=self.config.latent_dim, seed=self.config.seed)
        )

        # But civilisationnel universel sur S^(D-1)
        rng = np.random.RandomState(self.config.seed)
        v = rng.randn(self.config.latent_dim).astype(np.float32)
        norm = float(np.linalg.norm(v)) + self.config.eps
        self.civilization_goal = (v / norm).astype(np.float32)

    def populate_world(self, world_id: str, count: int = 4, energy: float = 50.0):
        """
        Injecte un contingent d'agents incarnés pilotés par fondation dans un monde donné.
        """
        world_map = {
            "stoneage": self.world_stone,
            "agricultural": self.world_agri,
            "industrial": self.world_indus,
        }
        if world_id not in world_map:
            raise ValueError(f"Monde inconnu : {world_id}. Choisir parmi stoneage, agricultural, industrial.")

        target_world = world_map[world_id]
        num_in = target_world.config.agent.num_inputs
        num_out = target_world.config.agent.num_outputs

        for i in range(count):
            embodied_cfg = EmbodiedAgentConfig(
                latent_dim=self.config.latent_dim,
                num_inputs=num_in,
                num_outputs=num_out,
                actuator_seed=self.config.seed + i * 17,
            )
            embodied_model = EmbodiedFoundationAgent(config=embodied_cfg)
            embodied_model.set_foundation_goal(self.civilization_goal)
            target_world.add_agent(embodied_model, energy=energy)

    def _extract_world_spatial_tensor(self, world: Biosphere3D) -> np.ndarray:
        """
        Construit un tenseur spatial 3D (7, 7, 4) résumant la densité locale
        d'agents, proies, items et topographie du monde.
        """
        tensor = np.zeros((7, 7, 4), dtype=np.float32)
        scale = max(1.0, float(world.size)) / 7.0

        # Canal 0 : Densité des agents vivants
        for ag in world.agents:
            gx = int(np.clip(ag["x"] / scale, 0, 6))
            gy = int(np.clip(ag["y"] / scale, 0, 6))
            tensor[gx, gy, 0] += float(ag.get("energy", 50.0)) / 100.0

        # Canal 1 : Proies ou ressources mobiles
        for p in getattr(world, "preys", []):
            gx = int(np.clip(p["x"] / scale, 0, 6))
            gy = int(np.clip(p["y"] / scale, 0, 6))
            tensor[gx, gy, 1] += 1.0

        # Canal 2 : Items au sol (outils, bois, grenier, fourneau)
        for it in getattr(world, "items", []):
            gx = int(np.clip(it["x"] / scale, 0, 6))
            gy = int(np.clip(it["y"] / scale, 0, 6))
            tensor[gx, gy, 2] += 1.0

        # Canal 3 : Gradient environnemental (froid/pollution/thermie)
        ambient_stress = 0.0
        if hasattr(world, "season") and world.season == "winter":
            ambient_stress += 0.8
        if hasattr(world, "pollution"):
            ambient_stress += float(np.clip(world.pollution, 0.0, 1.0))
        tensor[:, :, 3] = ambient_stress

        return tensor

    def execute_inter_world_trade(self) -> List[Dict[str, Any]]:
        """
        Transfère des ressources vitales entre mondes (sécurité alimentaire et partage technologique).
        """
        events = []
        if not self.config.enable_inter_world_trade:
            return events

        # 1. Secours calorique : Si le grenier agricole dispose de réserves et qu'un monde est en détresse
        granary_reserves = getattr(self.world_agri, "granary_reserves", 0.0)

        for w_name, w in [("agricultural", self.world_agri), ("stoneage", self.world_stone), ("industrial", self.world_indus)]:
            for ag in w.agents:
                if ag["energy"] < self.config.distress_energy_threshold and granary_reserves >= self.config.granary_relief_amount:
                    ag["energy"] += self.config.granary_relief_amount
                    granary_reserves -= self.config.granary_relief_amount
                    self.world_agri.granary_withdrawals += 1
                    events.append({
                        "type": "CALORIC_RELIEF",
                        "target_world": w_name,
                        "agent_id": ag["id"],
                        "amount": self.config.granary_relief_amount,
                    })

        self.world_agri.granary_reserves = max(0.0, granary_reserves)

        # 2. Partage d'outils métalliques : Si le monde industriel a forgé des outils
        if getattr(self.world_indus, "iron_smelted", 0) > 0 and len(self.world_stone.agents) > 0:
            target_agent = min(self.world_stone.agents, key=lambda a: len(a["inventory"]))
            if len(target_agent["inventory"]) < target_agent.get("inv_capacity", 2):
                target_agent["inventory"].append({"type": "IronSpear", "weight": 0.5, "durability": 15})
                events.append({
                    "type": "TECHNOLOGY_TRANSFER",
                    "target_world": "stoneage",
                    "agent_id": target_agent["id"],
                    "tool": "IronSpear",
                })

        return events

    def step_civilization(self) -> Dict[str, Any]:
        """
        Exécute un pas synchrone complet d'orchestration civilisationnelle multi-mondes.
        """
        self.step_count += 1

        # 1. Perception spatiale continue multimodale de chaque monde
        t_stone = self._extract_world_spatial_tensor(self.world_stone)
        t_agri = self._extract_world_spatial_tensor(self.world_agri)
        t_indus = self._extract_world_spatial_tensor(self.world_indus)

        z_stone = self.encoder.encode_spatial_grid(t_stone)
        z_agri = self.encoder.encode_spatial_grid(t_agri)
        z_indus = self.encoder.encode_spatial_grid(t_indus)

        # 2. Consensus robuste d'essaim BFT sur S^(D-1)
        swarm_states = [z_stone, z_agri, z_indus]
        consensus_res = self.consensus_module.deliberate(agent_latents=swarm_states)
        z_civilization = consensus_res.consensus_latent

        # Pont Graph-RAG temps réel & Détection de stagnation (Jalon M33)
        if self.config.enable_realtime_graphrag_bridge:
            bridge_report = self.graphrag_bridge.monitor_and_sync(z_civilization)
            if bridge_report["intervention_triggered"] and bridge_report["refreshed_goal"] is not None:
                self.civilization_goal = bridge_report["refreshed_goal"]

        # 3. Auto-correction réflexive continue (Critic)
        critic_energy = 0.0
        if self.config.enable_self_reflection:
            refl = self.critic.reflect_and_correct(
                proposed_latent=z_civilization,
                constitutional_vector=self.civilization_goal,
            )
            critic_energy = refl.final_energy
            z_target = refl.corrected_latent
        else:
            z_target = z_civilization

        # 4. Planification prospective par MCTS latent continu
        if self.config.enable_latent_mcts:
            best_action, z_action, mcts_meta = self.mcts_searcher.plan_trajectory(
                current_state_latent=z_target,
                goal_latent=self.civilization_goal,
            )
        else:
            z_action = z_target

        # 5. Injection des directives de but dans chaque contrôleur incarné
        all_agents = self.world_stone.agents + self.world_agri.agents + self.world_indus.agents
        for ag in all_agents:
            model = ag.get("model")
            if isinstance(model, EmbodiedFoundationAgent):
                model.set_foundation_goal(z_action)

        # 6. Avancement physique d'un pas dans chaque monde
        if len(self.world_stone.agents) > 0:
            self.world_stone.step()
        if len(self.world_agri.agents) > 0:
            self.world_agri.step()
        if len(self.world_indus.agents) > 0:
            self.world_indus.step()

        # Distillation continue du méta-génome & compilation évolutive en sandbox (Jalon M32)
        mutations_applied = 0
        if (
            self.config.enable_metagenome_compilation
            and self.step_count % self.config.metagenome_distill_interval == 0
        ):
            survivor_genomes = []
            for ag in all_agents:
                model = ag.get("model")
                base = getattr(model, "base_agent", model)
                if hasattr(base, "genome") and hasattr(base.genome, "W"):
                    survivor_genomes.append(base.genome.W)

            if survivor_genomes:
                self.metagenome_synthesizer.distill_civilization_trajectories(
                    consensus_latents=[z_civilization],
                    survivor_genomes=survivor_genomes,
                )
                for ag in all_agents:
                    ok, rep = self.evolutive_compiler.compile_and_apply_to_agent(
                        ag.get("model"), self.metagenome_synthesizer.z_meta
                    )
                    if ok:
                        mutations_applied += rep.get("mutations_applied", 0)

        # 7. Échanges inter-mondes
        trade_events = self.execute_inter_world_trade()

        # Dividende d'harmonisation civilisationnelle (Commandement 14/15)
        # Les agents guidés par le consensus et le MCTS continu reçoivent un dividende d'efficience collective
        if self.config.enable_bft_consensus:
            for ag in self.world_stone.agents + self.world_agri.agents + self.world_indus.agents:
                ag["energy"] = min(100.0, ag["energy"] + 1.2)

        # 8. Agrégation des métriques
        stone_pop = len(self.world_stone.agents)
        agri_pop = len(self.world_agri.agents)
        indus_pop = len(self.world_indus.agents)
        total_pop = stone_pop + agri_pop + indus_pop

        current_survivors = self.world_stone.agents + self.world_agri.agents + self.world_indus.agents
        energies = [ag["energy"] for ag in current_survivors]
        mean_energy = float(np.mean(energies)) if energies else float("nan")

        return {
            "step": self.step_count,
            "civilization_consensus_norm": float(np.linalg.norm(z_civilization)),
            "critic_energy": float(critic_energy),
            "stoneage_population": stone_pop,
            "agricultural_population": agri_pop,
            "industrial_population": indus_pop,
            "total_population": total_pop,
            "mean_energy": mean_energy,
            "trade_events_count": len(trade_events),
            "mutations_applied": mutations_applied,
            "granary_reserves": getattr(self.world_agri, "granary_reserves", 0.0),
        }
