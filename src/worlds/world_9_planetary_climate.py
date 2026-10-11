"""
World 9 : Climat Global & Rétroactions Planétaires Non-Linéaires.
Modélise le cycle du carbone atmosphérique, la rétroaction d'albédo glaciaire,
l'acidification océanique, les catastrophes météorologiques et la tragédie des biens communs.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional

from src.worlds.base_world import BaseWorld


@dataclass
class PlanetaryClimateConfig:
    """Configuration hyper-paramétrable pour le Monde 9 (Climat Planétaire)."""
    initial_co2_ppm: float = 280.0         # Niveau de CO2 préindustriel
    climate_sensitivity: float = 3.0       # Hausse de température (°C) par doublement de CO2
    carbon_sink_capacity: float = 0.5      # Taux d'absorption naturelle par tick (océan + forêts)
    ice_albedo_threshold: float = 2.0      # Seuil d'anomalie thermique (°C) déclenchant la fonte d'albédo
    extreme_weather_prob_base: float = 0.05 # Probabilité de base d'événements climatiques extrêmes
    disaster_energy_damage: float = 20.0   # Dégât énergétique infligé par tempête/sécheresse
    reforestation_cost: float = 5.0        # Coût énergétique par action de reboisement
    reforestation_sink_boost: float = 0.2  # Puits de carbone additionnel par forêt restaurée


class PlanetaryClimateWorld(BaseWorld):
    """
    Monde 9 : Climat Planétaire Couplé.
    Les agents font face aux rétroactions écologiques globales de leurs actions :
    - Émissions de carbone : Liées à l'activité productive et industrielle.
    - Échauffement radiatif : T_anom = S * ln(CO2 / 280) / ln(2).
    - Rétroaction d'albédo : La fonte glaciaire accélère l'absorption thermique.
    - Déclenchement d'événements extrêmes non-linéaires en cas de dépassement de seuil.
    - Gouvernance et capture de carbone : Sauvegarde de la planète par action concertée.
    """
    def __init__(self, config: Optional[PlanetaryClimateConfig] = None):
        super().__init__(size=1)
        self.config = config or PlanetaryClimateConfig()

        # Variables d'état planétaire
        self.co2_ppm: float = self.config.initial_co2_ppm
        self.temp_anomaly: float = 0.0
        self.ice_sheet_fraction: float = 1.0  # 1.0 = couverture complète, 0.0 = fonte totale
        self.forest_coverage: float = 1.0
        self.extreme_events_count: int = 0
        self.carbon_captured: float = 0.0
        self.total_emissions: float = 0.0

        self.reset()

    def reset(self):
        """Réinitialise les conditions climatiques planétaires."""
        self.tick_count = 0
        self.co2_ppm = self.config.initial_co2_ppm
        self.temp_anomaly = 0.0
        self.ice_sheet_fraction = 1.0
        self.forest_coverage = 1.0
        self.extreme_events_count = 0
        self.carbon_captured = 0.0
        self.total_emissions = 0.0
        return self.get_climate_state()

    def get_climate_state(self) -> np.ndarray:
        """Retourne l'état climatique sous forme de vecteur normalisé."""
        norm_co2 = (self.co2_ppm - 280.0) / 500.0
        state = np.array([
            norm_co2,
            self.temp_anomaly / 5.0,
            self.ice_sheet_fraction,
            self.forest_coverage,
        ], dtype=np.float32)
        return state

    def step(self):
        """Avance la dynamique climatique d'un cycle avec rétroactions non-linéaires."""
        self.tick_count += 1

        # 1. Émissions anthropiques des agents & Actions d'atténuation
        tick_emissions = 0.0
        for agent in self.agents:
            model = agent.get("model")
            action = 0  # 0: Activité standard, 1: Reboisement/Capture
            if hasattr(model, "forward"):
                out = model.forward(self.get_climate_state())
                if isinstance(out, np.ndarray) and len(out) > 0:
                    action = int(np.argmax(out))

            if action == 1 and agent["energy"] >= self.config.reforestation_cost:
                # Action de capture / reboisement
                agent["energy"] -= self.config.reforestation_cost
                self.carbon_captured += 0.8
                self.forest_coverage = min(1.5, self.forest_coverage + 0.01)
            else:
                # Activité standard émettrice
                tick_emissions += 0.4
                agent["energy"] = min(100.0, agent["energy"] + 2.0)  # Gain énergétique de subsistance

        self.total_emissions += tick_emissions

        # 2. Bilan du cycle du carbone
        sink = (self.config.carbon_sink_capacity * self.forest_coverage) + self.carbon_captured * 0.1
        net_carbon_flux = tick_emissions - sink
        self.co2_ppm = float(max(200.0, self.co2_ppm + net_carbon_flux * 0.5))

        # 3. Calcul de la température globale (Forçage radiatif logarithmique)
        ratio = max(0.5, self.co2_ppm / self.config.initial_co2_ppm)
        self.temp_anomaly = float(self.config.climate_sensitivity * (np.log(ratio) / np.log(2.0)))

        # Rétroaction de fonte d'albédo glaciaire si réchauffement
        if self.temp_anomaly > self.config.ice_albedo_threshold:
            self.ice_sheet_fraction = max(0.0, self.ice_sheet_fraction - 0.02 * (self.temp_anomaly - self.config.ice_albedo_threshold))
            # L'albédo réduit amplifie la température
            self.temp_anomaly += (1.0 - self.ice_sheet_fraction) * 0.5

        # 4. Événements climatiques extrêmes stochastiques
        event_prob = self.config.extreme_weather_prob_base * (1.0 + max(0.0, self.temp_anomaly) ** 1.5)
        if np.random.rand() < min(0.8, event_prob):
            self.extreme_events_count += 1
            # Les agents subissent des dégâts météorologiques
            for agent in self.agents:
                agent["energy"] = max(0.0, agent["energy"] - self.config.disaster_energy_damage)

    def add_agent(self, agent_model, **kwargs):
        """Ajoute un agent participant à l'équilibre planétaire."""
        agent_dict = {
            "id": f"clim_agent_{len(self.agents)}",
            "model": agent_model,
            "energy": kwargs.get("energy", 70.0),
            "age": 0,
        }
        self.agents.append(agent_dict)
        return agent_dict

    def get_planetary_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques planétaires et climatiques."""
        return {
            "co2_ppm": self.co2_ppm,
            "temp_anomaly": self.temp_anomaly,
            "ice_sheet_fraction": self.ice_sheet_fraction,
            "forest_coverage": self.forest_coverage,
            "extreme_events_count": self.extreme_events_count,
            "total_emissions": self.total_emissions,
            "carbon_captured": self.carbon_captured,
        }
