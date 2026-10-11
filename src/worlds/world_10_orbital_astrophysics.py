"""
World 10 : Astro-Physique & Expansion Orbitale Multi-Gravitationnelle.
Modélise la mécanique orbitale newtonienne, l'attraction centrale mu,
le budget d'impulsion Delta-V, le transfert de Hohmann et le rendez-vous orbital.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from src.worlds.base_world import BaseWorld


@dataclass
class OrbitalConfig:
    """Configuration hyper-paramétrable pour le Monde 10 (Astro-Physique)."""
    mu_gravity: float = 100.0             # Paramètre gravitationnel standard G*M
    target_orbit_radius: float = 10.0     # Rayon de l'orbite cible (station ou astéroïde)
    dt: float = 0.05                      # Pas de temps d'intégration orbitale
    initial_propellant: float = 50.0      # Budget initial de Delta-V par vaisseau
    thrust_power: float = 2.0             # Accélération maximale du propulseur
    rendezvous_tolerance: float = 0.8     # Tolérance de distance pour valider le rendez-vous


class OrbitalAstrophysicsWorld(BaseWorld):
    """
    Monde 10 : Mécanique Spatiale & Navigation Orbitale.
    Les agents pilotent des sondes/vaisseaux dans un puits gravitationnel :
    - Équations différentielles de Kepler-Newton avec poussée continue ou impulsionnelle.
    - Transferts orbitaux (Hohmann, circularisation).
    - Amarrage avec station spatiale ou capture d'astéroïdes.
    - Rareté du carburant (Delta-V critique).
    """
    def __init__(self, config: Optional[OrbitalConfig] = None):
        super().__init__(size=1)
        self.config = config or OrbitalConfig()

        self.successful_rendezvous = 0
        self.crashed_ships = 0
        self.escaped_ships = 0
        self.total_delta_v_spent = 0.0

        # Position de la cible orbitale (station sur orbite circulaire à rayon R)
        self.target_angle = 0.0
        self.target_omega = np.sqrt(self.config.mu_gravity / (self.config.target_orbit_radius ** 3))

        self.reset()

    def reset(self):
        """Réinitialise l'environnement orbital."""
        self.tick_count = 0
        self.successful_rendezvous = 0
        self.crashed_ships = 0
        self.escaped_ships = 0
        self.total_delta_v_spent = 0.0
        self.target_angle = 0.0
        return self.get_target_state()

    def get_target_pos(self) -> np.ndarray:
        """Calcule la position cartésienne de la cible orbitale."""
        r = self.config.target_orbit_radius
        x = r * np.cos(self.target_angle)
        y = r * np.sin(self.target_angle)
        return np.array([x, y], dtype=np.float32)

    def get_target_state(self) -> np.ndarray:
        """Retourne l'état de la cible orbitale."""
        pos = self.get_target_pos()
        v_mag = np.sqrt(self.config.mu_gravity / self.config.target_orbit_radius)
        vel = np.array([-v_mag * np.sin(self.target_angle), v_mag * np.cos(self.target_angle)], dtype=np.float32)
        return np.concatenate([pos, vel])

    def step(self):
        """Avance l'intégration orbitale par intégrateur symplectique de Verlet."""
        self.tick_count += 1
        dt = self.config.dt

        # 1. Avancée de la cible orbitale
        self.target_angle += self.target_omega * dt
        target_pos = self.get_target_pos()

        # 2. Dynamique pour chaque agent/vaisseau
        for agent in self.agents:
            pos = agent["pos"]
            vel = agent["vel"]
            propellant = agent["propellant"]

            r_norm = float(np.linalg.norm(pos))

            # Contrôle de crash planétaire ou évasion infinie
            if r_norm < 1.0:
                self.crashed_ships += 1
                agent["energy"] = 0.0
                continue
            elif r_norm > self.config.target_orbit_radius * 3.0:
                self.escaped_ships += 1
                agent["energy"] = max(0.0, agent["energy"] - 10.0)
                continue

            # Décision de poussée de l'agent
            thrust = np.zeros(2, dtype=np.float32)
            model = agent.get("model")
            obs = np.concatenate([pos / 20.0, vel / 5.0, (target_pos - pos) / 10.0])

            if hasattr(model, "forward"):
                out = model.forward(obs)
                if isinstance(out, np.ndarray) and len(out) >= 2:
                    t_dir = out[:2]
                    t_norm = np.linalg.norm(t_dir)
                    if t_norm > 1e-4 and propellant > 0.0:
                        thrust = (t_dir / t_norm) * min(self.config.thrust_power, propellant)
                        agent["propellant"] -= float(np.linalg.norm(thrust)) * dt
                        self.total_delta_v_spent += float(np.linalg.norm(thrust)) * dt

            # Accélération gravitationnelle centrale : -mu / r^3 * r
            grav_acc = -(self.config.mu_gravity / (r_norm ** 3)) * pos
            total_acc = grav_acc + thrust

            # Intégration Euler-Cromer
            vel += total_acc * dt
            pos += vel * dt

            agent["pos"] = pos
            agent["vel"] = vel

            # Détection de rendez-vous avec la cible
            dist_to_target = float(np.linalg.norm(pos - target_pos))
            if dist_to_target <= self.config.rendezvous_tolerance:
                self.successful_rendezvous += 1
                agent["energy"] = min(100.0, agent["energy"] + 25.0)

    def add_agent(self, agent_model, **kwargs):
        """Place un vaisseau spatial sur orbite de départ."""
        r_init = kwargs.get("initial_radius", 5.0)
        angle_init = float(np.random.uniform(0, 2 * np.pi))
        pos = np.array([r_init * np.cos(angle_init), r_init * np.sin(angle_init)], dtype=np.float32)
        v_circ = np.sqrt(self.config.mu_gravity / r_init)
        vel = np.array([-v_circ * np.sin(angle_init), v_circ * np.cos(angle_init)], dtype=np.float32)

        agent_dict = {
            "id": f"ship_{len(self.agents)}",
            "model": agent_model,
            "pos": pos,
            "vel": vel,
            "propellant": float(kwargs.get("propellant", self.config.initial_propellant)),
            "energy": float(kwargs.get("energy", 80.0)),
            "age": 0,
        }
        self.agents.append(agent_dict)
        return agent_dict

    def get_orbital_metrics(self) -> Dict[str, Any]:
        """Retourne les statistiques de la campagne orbitale."""
        return {
            "successful_rendezvous": self.successful_rendezvous,
            "crashed_ships": self.crashed_ships,
            "escaped_ships": self.escaped_ships,
            "total_delta_v_spent": self.total_delta_v_spent,
        }
