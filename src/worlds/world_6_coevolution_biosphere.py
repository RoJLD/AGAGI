"""
World 6 : L'Écosystème Co-Évolutif Proies/Prédateurs Adaptatifs.
Hérite de Biosphere3D avec proies apprenantes/réactives, dynamique de fuite (Boids),
course aux armements biologique (Arms Race), toxicité et camouflage sélectif.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


@dataclass
class CoevolutionConfig(WorldConfig):
    """Configuration hyper-paramétrable pour le Monde 6 (Co-Évolution)."""
    prey_base_speed: float = 1.0           # Distance de fuite des proies par tick
    prey_evasion_radius: float = 6.0       # Rayon de détection des prédateurs par les proies
    enable_prey_adaptation: bool = True    # Adaptation dynamique de la vitesse des proies
    adaptation_rate: float = 0.05          # Vitesse d'accélération de l'Arms Race
    toxic_prey_ratio: float = 0.2          # Ratio de proies vénéneuses (exige discrimination)
    toxicity_damage: float = 25.0          # Dégât subi en cas d'ingestion de proie toxique
    camouflage_prob: float = 0.25          # Probabilité qu'une proie ait un camouflage lidar


class CoevolutionBiosphereWorld(Biosphere3D):
    """
    Monde 6 : Écosystème Co-Évolutif.
    Introduit une pression adaptative bidirectionnelle (Red Queen Dynamics) :
    - Évasion active : Les proies détectent les agents et fuient selon un vecteur inverse de menace.
    - Toxicité sélective : 20% des proies sont vénéneuses (exige discrimination par les prédateurs).
    - Camouflage dynamique : Proies difficiles à détecter par le lidar classique.
    - Course aux armements (Arms Race) : Si la prédation est forte, les proies accélèrent.
    """
    def __init__(self, config: Optional[CoevolutionConfig] = None):
        cfg = config or CoevolutionConfig()
        super().__init__(cfg)
        self.coevo_config = cfg

        # Dynamiques de co-évolution
        self.current_prey_speed = cfg.prey_base_speed
        self.prey_kills = 0
        self.toxic_kills = 0
        self.successful_evasions = 0
        self.arms_race_generation = 1

        # Enrichissement des proies avec attributs co-évolutifs
        self._init_adaptive_preys()

    def _init_adaptive_preys(self) -> None:
        """Attribue la toxicité et le camouflage aux proies du monde."""
        for p in self.preys:
            p["is_toxic"] = bool(np.random.rand() < self.coevo_config.toxic_prey_ratio)
            p["is_camouflaged"] = bool(np.random.rand() < self.coevo_config.camouflage_prob)

    def step(self):
        """Avance la simulation en intégrant la dynamique réactive des proies."""
        # 1. Comportement de fuite des proies face aux agents
        if self.agents and self.preys:
            agents_coords = np.array([[float(a["x"]), float(a["y"])] for a in self.agents])

            for p in self.preys:
                p_coord = np.array([float(p["x"]), float(p["y"])])
                dists = np.linalg.norm(agents_coords - p_coord, axis=1)
                closest_idx = int(np.argmin(dists))
                min_dist = float(dists[closest_idx])

                # Si un prédateur est dans le rayon de fuite
                if min_dist < self.coevo_config.prey_evasion_radius:
                    threat_dir = p_coord - agents_coords[closest_idx]
                    norm = float(np.linalg.norm(threat_dir))
                    if norm > 1e-4:
                        step_vec = (threat_dir / norm) * self.current_prey_speed
                        # Mise à jour position de fuite avec rebond aux limites
                        new_x = int(np.clip(round(p["x"] + step_vec[0]), 0, self.size - 1))
                        new_y = int(np.clip(round(p["y"] + step_vec[1]), 0, self.size - 1))
                        p["x"] = new_x
                        p["y"] = new_y
                        self.successful_evasions += 1

        # 2. Exécution du step standard Biosphere3D
        super().step()

        # 3. Vérification des captures toxiques
        for a in self.agents:
            if a.get("last_catch_toxic", False):
                a["energy"] = max(0.0, a["energy"] - self.coevo_config.toxicity_damage)
                self.toxic_kills += 1
                a["last_catch_toxic"] = False

        # 4. Arms Race périodique : les proies accélèrent si trop peuplées ou trop chassées
        if self.ticks % 50 == 0 and self.coevo_config.enable_prey_adaptation:
            if len(self.preys) < 4:
                self.current_prey_speed = min(3.0, self.current_prey_speed * (1.0 + self.coevo_config.adaptation_rate))
                self.arms_race_generation += 1
                self._spawn_preys()
                self._init_adaptive_preys()

    def get_coevolution_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de la course aux armements."""
        return {
            "current_prey_speed": self.current_prey_speed,
            "arms_race_generation": self.arms_race_generation,
            "successful_evasions": self.successful_evasions,
            "toxic_kills": self.toxic_kills,
            "active_preys_count": len(self.preys),
        }
