"""
CurriculumRunner — Axe ontogénétique (cf. docs/EDR/008_Developmental_Curriculum.md).

Enchaîne les worlds par portes de maîtrise (mastery gates) au lieu de tourner
30 ères dans un monde fixe. Le champion d'un monde maîtrisé est promu dans le
monde suivant via le mécanisme d'import existant
(init_primordial_soup(import_agent_id=...)).

Découplage volontaire (testabilité, Commandement 4) : le runner ne connaît PAS
les worlds ni KuzuDB. Il reçoit un callback `run_era_fn` qui exécute UNE ère
dans un monde donné et renvoie un EraResult. L'intégration concrète dans
main_biosphere.py injecte ce callback.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict
import logging

import numpy as np

from src.seed_ai.live_progress import emit_progress

logger = logging.getLogger("AGIseed.Curriculum")


@dataclass
class EraResult:
    """Ce que run_era_fn doit renvoyer pour une ère."""
    competence: float                        # compétence agrégée du monde, 0..1
    champion_agent_id: Optional[str] = None  # id[:8] du champion à promouvoir
    raw_stats: Dict = field(default_factory=dict)


@dataclass
class WorldStage:
    """Un barreau de l'échelle développementale."""
    world_type: str   # "soup" | "stoneage" | "agricultural" | "industrial" | "gym"
    name: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.world_type


@dataclass
class GraduationConfig:
    """Paramètres de la porte de maîtrise (EDR 008). Variables d'expérience."""
    window: int = 5            # W : taille de la fenêtre glissante
    eps_plateau: float = 0.01  # pente OLS max (par ère) pour déclarer un plateau
    c_floor: float = 0.6       # plancher anti-plateau-bas
    patience: int = 2          # K : ères consécutives remplissant la condition
    max_eras: int = 30         # garde-temps : promotion forcée


def plateau_slope(history: List[float], window: int) -> float:
    """Pente OLS de la compétence sur la fenêtre glissante (unité : par ère)."""
    ys = np.asarray(history[-window:], dtype=float)
    if len(ys) < 2:
        return float("inf")  # pas assez de points -> jamais un plateau
    xs = np.arange(len(ys), dtype=float)
    return float(np.polyfit(xs, ys, 1)[0])


def has_graduated(history: List[float], cfg: GraduationConfig) -> bool:
    """
    La population diplôme-t-elle du monde courant ? (EDR 008)

    PLATEAU  : |pente OLS sur W ères| < eps_plateau   (la compétence a cessé de monter)
    PLANCHER : médiane des W dernières compétences >= c_floor  (anti-plateau-bas)

    La PATIENCE K (ères consécutives) est gérée par le runner, pas ici : cette
    fonction est un prédicat pur sur l'historique, donc trivialement testable.
    """
    if len(history) < cfg.window:
        return False
    recent = history[-cfg.window:]
    plateau = abs(plateau_slope(history, cfg.window)) < cfg.eps_plateau
    floor = float(np.median(recent)) >= cfg.c_floor
    return plateau and floor


class CurriculumRunner:
    """Orchestre la traversée des mondes par maîtrise (EDR 008)."""

    def __init__(
        self,
        stages: List[WorldStage],
        run_era_fn: Callable[[str, Optional[str], int], EraResult],
        grad_cfg: Optional[GraduationConfig] = None,
        keep_memory: bool = False,
    ):
        if not stages:
            raise ValueError("Le curriculum a besoin d'au moins un WorldStage.")
        self.stages = stages
        self.run_era_fn = run_era_fn
        self.cfg = grad_cfg or GraduationConfig()
        self.keep_memory = keep_memory
        self.transcript: List[Dict] = []  # journal développemental (une entrée/monde)

    def run(self) -> List[Dict]:
        """
        Traverse tous les stages. Renvoie le transcript développemental :
        une entrée par monde (ères tenues, compétence finale, champion promu,
        ancêtre hérité). C'est la trace observable de la "2e échelle de temps".
        """
        carried_agent_id: Optional[str] = None  # le "relicat" transféré de monde en monde

        for depth, stage in enumerate(self.stages):
            history: List[float] = []
            streak = 0           # compteur de patience K
            champion: Optional[str] = None
            graduated = False
            era = 0

            while era < self.cfg.max_eras:
                era += 1
                result = self.run_era_fn(
                    stage.world_type,
                    carried_agent_id,
                    1 if self.keep_memory else 0,
                )
                history.append(result.competence)
                emit_progress({
                    "run": stage.name,
                    "generation": era,
                    "fitness": result.competence,
                    "accuracy": None,
                    "size": None,
                })
                if result.champion_agent_id:
                    champion = result.champion_agent_id

                if has_graduated(history, self.cfg):
                    streak += 1
                    if streak >= self.cfg.patience:
                        graduated = True
                        logger.info(
                            "🎓 Graduation %s à l'ère %d (C=%.3f)",
                            stage.name, era, history[-1],
                        )
                        break
                else:
                    streak = 0

            if not graduated:
                logger.info(
                    "⏱️ Garde-temps atteint pour %s (%d ères, C=%.3f)",
                    stage.name, era, history[-1] if history else 0.0,
                )

            self.transcript.append({
                "depth": depth,
                "world": stage.name,
                "eras": era,
                "final_competence": history[-1] if history else 0.0,
                "graduated": graduated,
                "champion_promoted": champion,
                "inherited_from": carried_agent_id,
            })

            # Promotion : le champion devient le relicat transféré au monde suivant.
            carried_agent_id = champion

        return self.transcript
