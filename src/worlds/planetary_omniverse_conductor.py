"""
Planetary Omniverse Conductor : Orchestrateur de Civilisation Planétaire & Spatiale.
Relie de manière unifiée le Cyber-Réseau (Monde 8), le Climat Planétaire (Monde 9)
et l'Expansion Orbitale (Monde 10) pour mesurer la maturité civilisationnelle de l'AGI.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional

from src.worlds.world_8_cyber_network import CyberNetworkWorld, CyberNetworkConfig
from src.worlds.world_9_planetary_climate import PlanetaryClimateWorld, PlanetaryClimateConfig
from src.worlds.world_10_orbital_astrophysics import OrbitalAstrophysicsWorld, OrbitalConfig


@dataclass
class OmniverseConfig:
    """Configuration du Métamonde Planétaire Omniversel."""
    simulation_steps: int = 50           # Nombre d'itérations par ère planétaire
    target_kardashev_threshold: float = 0.85 # Seuil de maturité de Type I


class PlanetaryOmniverseConductor:
    """
    Conducteur Planétaire Omniversel :
    Supervise la synergie entre :
    1. Télécommunications & Données (Cyber-Réseau)
    2. Homéostasie Planétaire (Climat & Résilience)
    3. Conquête Spatiale (Mécanique Orbitale & Ressources Extra-Terrestres)
    """
    def __init__(self, config: Optional[OmniverseConfig] = None):
        self.config = config or OmniverseConfig()

        self.cyber_world = CyberNetworkWorld(CyberNetworkConfig())
        self.climate_world = PlanetaryClimateWorld(PlanetaryClimateConfig())
        self.orbital_world = OrbitalAstrophysicsWorld(OrbitalConfig())

        self.kardashev_index = 0.0
        self.history: List[Dict[str, Any]] = []

    def step(self):
        """Avance synchronisée des 3 dimensions planétaires."""
        # 1. Propagation des flux de communication
        self.cyber_world.step()

        # 2. Évolution du climat et bilan carbone
        self.climate_world.step()

        # 3. Trajectoires et navigation orbitale
        self.orbital_world.step()

        # Calcul de l'Indice Kardashev Synthétique K_score
        c_metrics = self.cyber_world.get_cyber_metrics()
        clim_metrics = self.climate_world.get_planetary_metrics()
        orb_metrics = self.orbital_world.get_orbital_metrics()

        cyber_score = float(c_metrics["delivery_rate"])
        # Score climatique : pénalisé si température anormale élevée
        climate_score = float(np.clip(1.0 - (clim_metrics["temp_anomaly"] / 5.0), 0.1, 1.0))
        # Score orbital : basé sur la survie et le rendez-vous
        total_ships = max(1, len(self.orbital_world.agents))
        orbital_score = float(np.clip((orb_metrics["successful_rendezvous"] + 1.0) / (total_ships + 1.0), 0.1, 1.0))

        # Moyenne géométrique
        self.kardashev_index = float((cyber_score * climate_score * orbital_score) ** (1.0 / 3.0))

        step_record = {
            "tick": self.cyber_world.tick_count,
            "cyber_score": cyber_score,
            "climate_score": climate_score,
            "orbital_score": orbital_score,
            "kardashev_index": self.kardashev_index,
        }
        self.history.append(step_record)
        return step_record

    def get_omniverse_report(self) -> Dict[str, Any]:
        """Retourne le bilan consolidé de la civilisation planétaire."""
        return {
            "kardashev_index": self.kardashev_index,
            "cyber": self.cyber_world.get_cyber_metrics(),
            "climate": self.climate_world.get_planetary_metrics(),
            "orbital": self.orbital_world.get_orbital_metrics(),
        }
