"""
Autotelic Curriculum Conductor : Orchestrateur de Co-Évolution Mondes-Modèles.
Permet aux agents d'évoluer et de se complexifier au fur et à mesure que le monde
lui-même s'élève en difficulté dès qu'un seuil de maîtrise (Top) est atteint.
Inspiré des dynamiques POET (Paired Open-Ended Trailblazer) et PAIRED.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional

from src.worlds.base_world import BaseWorld
from src.worlds.world_5_economic_market import EconomicMarketWorld, EconomicConfig
from src.worlds.world_6_coevolution_biosphere import CoevolutionBiosphereWorld, CoevolutionConfig
from src.worlds.world_7_symbolic_reasoning import SymbolicReasoningWorld, SymbolicConfig


@dataclass
class AutotelicConfig:
    """Configuration du Curriculum Autotélique."""
    mastery_threshold: float = 0.80     # Seuil de compétence pour déclencher la complexification
    min_eras_before_scaling: int = 2     # Nombre minimal d'ères à observer
    difficulty_multiplier: float = 1.25  # Facteur d'élévation de complexité du monde
    max_complexity_level: int = 10       # Niveau plafond de complexité


class AutotelicCurriculumConductor:
    """
    Orchestrateur Autotélique :
    - Évalue en continu la performance des agents sur les dimensions :
      1. Survie & Écologie (Monde 1, 6)
      2. Coordination Économique (Monde 5)
      3. Rigueur Déductive & Symbolique (Monde 7)
    - Dès que les agents atteignent le sommet (Score >= mastery_threshold),
      le monde s'auto-complexifie (rareté des ressources, réactivité des proies, profondeur des théorèmes).
    - Favorise la co-évolution conjointe du modèle et de son environnement.
    """
    def __init__(self, config: Optional[AutotelicConfig] = None):
        self.config = config or AutotelicConfig()
        self.current_tier = 1
        self.complexity_level = 1
        self.consecutive_mastery_count = 0
        self.history_records: List[Dict[str, Any]] = []

        # Instanciation modulaire des environnements du curriculum
        self.world_econ = EconomicMarketWorld(EconomicConfig())
        self.world_coevo = CoevolutionBiosphereWorld(CoevolutionConfig())
        self.world_symb = SymbolicReasoningWorld(SymbolicConfig())

    def evaluate_competence(self, metrics: Dict[str, Any]) -> float:
        """
        Calcule un indice composite normalisé de compétence [0, 1].
        """
        econ_score = float(np.clip(metrics.get("econ_volume", 0.0) / 20.0, 0.0, 1.0))
        survival_score = float(np.clip(metrics.get("survival_rate", 0.5), 0.0, 1.0))
        logic_score = float(np.clip(metrics.get("symbolic_acc", 0.5), 0.0, 1.0))

        composite_score = 0.35 * survival_score + 0.35 * econ_score + 0.30 * logic_score
        return float(composite_score)

    def trigger_world_coevolution_scaling(self) -> Dict[str, Any]:
        """
        Élève la complexité des mondes lorsque les modèles sont au top de leur niveau.
        """
        self.complexity_level = min(
            self.config.max_complexity_level,
            self.complexity_level + 1
        )
        mult = self.config.difficulty_multiplier

        # 1. Complexification du Monde Économique (Élasticité et rareté accrues)
        self.world_econ.econ_config.elasticity *= mult
        self.world_econ.econ_config.base_food_price *= mult

        # 2. Complexification de l'Écosystème (Course aux armements, proies plus véloces)
        self.world_coevo.coevo_config.prey_base_speed *= mult
        self.world_coevo.coevo_config.prey_evasion_radius *= mult

        # 3. Complexification Symbolique (Tolérance réduite, théorèmes plus denses)
        self.world_symb.config.tolerance_eps /= mult

        scaling_event = {
            "new_complexity_level": self.complexity_level,
            "scaling_applied": True,
            "difficulty_multiplier": mult,
        }
        return scaling_event

    def step_curriculum_cycle(self, observed_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute un cycle de diagnostic et d'ajustement du curriculum.
        """
        competence = self.evaluate_competence(observed_metrics)
        is_top_level = competence >= self.config.mastery_threshold

        scaling_info = {"scaling_applied": False}

        if is_top_level:
            self.consecutive_mastery_count += 1
            if self.consecutive_mastery_count >= self.config.min_eras_before_scaling:
                scaling_info = self.trigger_world_coevolution_scaling()
                self.consecutive_mastery_count = 0  # Réinitialisation après élévation
        else:
            self.consecutive_mastery_count = max(0, self.consecutive_mastery_count - 1)

        record = {
            "tier": self.current_tier,
            "complexity_level": self.complexity_level,
            "competence": competence,
            "is_top_level": is_top_level,
            "scaling_info": scaling_info,
        }
        self.history_records.append(record)
        return record
