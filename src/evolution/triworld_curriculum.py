"""
src/evolution/triworld_curriculum.py — Orchestrateur du Curriculum Évolutif Tri-Mondes.
Pilote la phylogénèse continue d'une population d'agents à travers 3 époques successives :
1. Monde 1 (Âge de Pierre) : Survie élémentaire, chasse, feu.
2. Monde 2 (Âge Agricole) : Gestion du froid hivernal, greniers collectifs, synergie LU.
3. Monde 3 (Âge Industriel) : Extraction minérale, fusion au haut fourneau, métallurgie durable.

Respect des 12 Commandements AGIseed :
- 1. Flexible : Configurable via TriWorldCurriculumConfig.
- 2. Modulaire : Découplé des moteurs de monde.
- 3. Haute Performance : Évaluations vectorisées.
- 5. Transparent : Rapport structuré et auditable.
- 9. Stabilité Numérique : Bornes et moyennes protégées contre NaN.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_2_agricultural import AgriculturalWorld, AgriculturalConfig
from src.worlds.world_3_industrial import IndustrialWorld, IndustrialConfig
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig, Genome, apply_mutations


@dataclass
class TriWorldCurriculumConfig:
    """Paramétrage du curriculum inter-mondes."""
    pop_size: int = 8
    eras_per_world: int = 2
    max_ticks_per_era: int = 40
    mutation_rate: float = 0.05
    initial_energy: float = 50.0
    seed: int = 42
    isocaloric: bool = False


class TriWorldCurriculum:
    """Orchestre la transmission et l'adaptation de populations à travers les 3 Mondes."""

    def __init__(self, config: Optional[TriWorldCurriculumConfig] = None):
        self.config = config or TriWorldCurriculumConfig()
        np.random.seed(self.config.seed)
        self.mutation_cfg = MutationConfig(weight_mutate_rate=self.config.mutation_rate)
        self.history: List[Dict[str, Any]] = []

    def _init_population(self, num_inputs: int, num_outputs: int) -> List[MambaAgent]:
        """Initialise une population de départ."""
        pop = []
        for _ in range(self.config.pop_size):
            agent = MambaAgent(num_inputs=num_inputs, num_outputs=num_outputs, isocaloric=self.config.isocaloric)
            pop.append(agent)
        return pop

    def _evaluate_era(self, world_instance: Any, agents: List[MambaAgent]) -> Tuple[List[float], List[MambaAgent]]:
        """Évalue une population sur une ère dans un monde donné."""
        agent_entries = []
        for ag in agents:
            entry = world_instance.add_agent(ag, energy=self.config.initial_energy)
            agent_entries.append((ag, entry))

        for _ in range(self.config.max_ticks_per_era):
            world_instance.step()
            living = [e for _, e in agent_entries if e.get("energy", 0.0) > 0]
            if len(living) == 0:
                break

        # Scores de fitness basés sur l'énergie finale et l'activité
        scores = []
        for ag, entry in agent_entries:
            energy = max(0.0, float(entry.get("energy", 0.0)))
            inv_size = len(entry.get("inventory", []))
            score = energy + inv_size * 5.0
            scores.append(score)

        return scores, agents

    def run_stage(self, stage_name: str, world_factory, current_pop: List[MambaAgent]) -> Dict[str, Any]:
        """Fait évoluer la population sur un monde donné pendant N ères."""
        stage_history = []
        pop = current_pop

        for era in range(self.config.eras_per_world):
            world = world_factory()
            scores, evaluated_agents = self._evaluate_era(world, pop)

            # Tri par performance
            ranked_indices = np.argsort(scores)[::-1]
            best_idx = ranked_indices[0]
            best_score = float(scores[best_idx])
            mean_score = float(np.mean(scores))

            stage_history.append({
                "era": era + 1,
                "best_score": best_score,
                "mean_score": mean_score,
                "best_agent": evaluated_agents[best_idx],
            })

            # Sélection des meilleurs pour l'ère suivante
            survivors = [evaluated_agents[i] for i in ranked_indices[:max(2, len(pop) // 2)]]
            new_pop = []
            for s in survivors:
                new_pop.append(s)
            while len(new_pop) < self.config.pop_size:
                parent = survivors[np.random.randint(0, len(survivors))]
                child = MambaAgent(
                    num_inputs=parent.genome.num_inputs,
                    num_outputs=parent.genome.num_outputs,
                    num_nodes=parent.genome.num_nodes
                )
                child.genome.W = parent.genome.W.copy() + np.random.randn(*parent.genome.W.shape).astype(np.float32) * self.config.mutation_rate
                new_pop.append(child)
            pop = new_pop

        return {
            "stage_name": stage_name,
            "best_final_score": stage_history[-1]["best_score"],
            "mean_final_score": stage_history[-1]["mean_score"],
            "champion": stage_history[-1]["best_agent"],
            "surviving_pop": pop,
            "eras": stage_history
        }

    def run_full_curriculum(self) -> Dict[str, Any]:
        """Exécute la chaîne phylogénétique complète : Monde 1 -> Monde 2 -> Monde 3."""
        base_cfg = WorldConfig()
        initial_pop = self._init_population(base_cfg.agent.num_inputs, base_cfg.agent.num_outputs)

        # Étape 1 : Monde 1 (Âge de Pierre)
        stage_1 = self.run_stage(
            "StoneAge_World1",
            lambda: Biosphere3D(base_cfg),
            initial_pop
        )

        # Étape 2 : Monde 2 (Âge Agricole)
        agri_cfg = AgriculturalConfig(size=base_cfg.size, enable_granary=True)
        stage_2 = self.run_stage(
            "Agricultural_World2",
            lambda: AgriculturalWorld(agri_cfg),
            stage_1["surviving_pop"]
        )

        # Étape 3 : Monde 3 (Âge Industriel)
        indus_cfg = IndustrialConfig(size=base_cfg.size, enable_blast_furnace=True)
        stage_3 = self.run_stage(
            "Industrial_World3",
            lambda: IndustrialWorld(indus_cfg),
            stage_2["surviving_pop"]
        )

        # Calcul de l'efficacité de transfert phylogénétique
        scores = [stage_1["best_final_score"], stage_2["best_final_score"], stage_3["best_final_score"]]
        transfer_ratio = float(scores[2] / (scores[0] + 1e-6))

        curriculum_report = {
            "stages": [stage_1, stage_2, stage_3],
            "champions": {
                "stoneage": stage_1["champion"],
                "agricultural": stage_2["champion"],
                "industrial": stage_3["champion"],
            },
            "scores_progression": scores,
            "transfer_ratio": transfer_ratio,
            "status": "completed"
        }
        self.history.append(curriculum_report)
        return curriculum_report

    def persist_to_kuzudb(self, report: Dict[str, Any], db_path: Optional[str] = None, run_id: Optional[str] = None) -> str:
        """Persiste le run de curriculum dans KuzuDB (Commandement 5: Transparent & Auditable)."""
        import uuid
        from src.paths import kuzu_graph
        from src.graph_rag.experiment_tracker import ExperimentGraph
        from src.graph_rag.async_logger import logger as async_logger

        effective_db_path = db_path or kuzu_graph()
        actual_run_id = run_id or f"run_triworld_{uuid.uuid4().hex[:8]}"
        shared_db = async_logger.get_db()
        if shared_db is not None and (db_path is None or getattr(async_logger, "db_path", "") == effective_db_path):
            graph = ExperimentGraph(db=shared_db)
        else:
            graph = ExperimentGraph(db_path=effective_db_path)
        graph.log_phylogenetic_run(actual_run_id, report)
        return actual_run_id

