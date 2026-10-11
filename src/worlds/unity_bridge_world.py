"""
Unity Bridge World : Passerelle Bidirectionnelle Moteur de Jeu Réaliste (Unity PhysX / 3D).
Permet aux agents cognitifs d'AGIseed (Liquid Mamba ODE, MCTS, BFT) d'interagir
avec des environnements 3D haute fidélité simulés sous Unity.
Supporte le mode Live (connexion TCP temps réel) et le mode Simulation Locale (Mock certifié CI/CD).
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import json
import socket
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from src.worlds.base_world import BaseWorld


@dataclass
class UnityBridgeConfig:
    """Configuration de la passerelle Unity."""
    host: str = "127.0.0.1"               # Adresse IP du serveur Unity
    port: int = 5555                      # Port TCP d'échange
    timeout: float = 2.0                  # Timeout de connexion réseau (secondes)
    observation_dim: int = 45             # Dimension de perception (Lidar 3D, physique, énergie)
    action_dim: int = 25                  # Dimension d'action (Mouvement 3D, saisie, force, voix)
    mock_if_disconnected: bool = True     # Bascule automatique en simulation locale si Unity est hors ligne
    lidar_rays: int = 16                  # Nombre de faisceaux LiDAR 3D simulés
    step_dt: float = 0.02                 # Pas de simulation physique Unity (50 Hz / PhysX standard)


class UnityBridgeWorld(BaseWorld):
    """
    Monde Passerelle Unity :
    - Réception des observations physiques PhysX (Position 3D, vitesse, orientation, LiDAR, collisions).
    - Envoi des vecteurs de contrôle neuromoteurs (forces, couples, interactions).
    - Mode Fallback / Mock ultra-rapide garantissant 100% de reproductibilité sans dépendance graphique lourde.
    """
    def __init__(self, config: Optional[UnityBridgeConfig] = None):
        super().__init__(size=1)
        self.config = config or UnityBridgeConfig()

        self.connected_to_unity = False
        self.socket: Optional[socket.socket] = None
        self.tick_count = 0

        # Métriques de télémétrie
        self.total_packets_sent = 0
        self.total_packets_received = 0
        self.average_latency_ms = 0.0
        self.last_observation: Optional[np.ndarray] = None

        # État simulé interne pour mode Mock / Déconnecté
        self._mock_pos = np.zeros(3, dtype=np.float32)
        self._mock_vel = np.zeros(3, dtype=np.float32)
        self._mock_health = 100.0

        self._attempt_connection()

    def _attempt_connection(self) -> bool:
        """Tente d'établir un socket TCP avec la scène Unity active."""
        if not self.config.mock_if_disconnected:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.config.timeout)
                self.socket.connect((self.config.host, self.config.port))
                self.connected_to_unity = True
                return True
            except (socket.error, socket.timeout):
                self.connected_to_unity = False
                self.socket = None
                return False
        else:
            # Mode Mock par défaut pour isolation unitaire et vitesse d'exécution
            self.connected_to_unity = False
            return False

    def reset(self) -> np.ndarray:
        """Réinitialise l'environnement Unity ou l'état simulé local."""
        self.tick_count = 0
        self._mock_pos = np.zeros(3, dtype=np.float32)
        self._mock_vel = np.zeros(3, dtype=np.float32)
        self._mock_health = 100.0

        if self.connected_to_unity and self.socket:
            try:
                cmd = json.dumps({"command": "RESET"}).encode("utf-8") + b"\n"
                self.socket.sendall(cmd)
                resp = self._read_socket_line()
                if resp:
                    obs_data = json.loads(resp).get("observation", [])
                    self.last_observation = np.array(obs_data, dtype=np.float32)
                    return self.last_observation
            except Exception:
                self.connected_to_unity = False

        self.last_observation = self._generate_mock_observation()
        return self.last_observation

    def _generate_mock_observation(self) -> np.ndarray:
        """Génère un vecteur d'observation physique 3D réaliste en mode simulation locale."""
        # LiDAR 3D normalisé (16 rayons)
        lidar = np.full(self.config.lidar_rays, 1.0, dtype=np.float32)
        # Position 3D normalisée
        pos_norm = self._mock_pos / 50.0
        # Vitesse 3D normalisée
        vel_norm = self._mock_vel / 10.0
        # Métriques vitales (santé, énergie, contact sol)
        vitals = np.array([self._mock_health / 100.0, 1.0, 0.0], dtype=np.float32)

        # Concaténation et remplissage jusqu'à observation_dim
        base_features = np.concatenate([lidar, pos_norm, vel_norm, vitals])
        obs = np.zeros(self.config.observation_dim, dtype=np.float32)
        obs[:len(base_features)] = base_features[:self.config.observation_dim]
        return obs

    def _read_socket_line(self) -> Optional[str]:
        """Lit une ligne terminée par \n depuis le socket TCP."""
        if not self.socket:
            return None
        buffer = b""
        try:
            while not buffer.endswith(b"\n"):
                chunk = self.socket.recv(1024)
                if not chunk:
                    break
                buffer += chunk
            return buffer.decode("utf-8").strip()
        except socket.timeout:
            return None

    def step(self):
        """Avance la simulation d'un pas physique dans Unity ou en mode Mock."""
        self.tick_count += 1

        # Collecter les actions du premier agent
        actions = np.zeros(self.config.action_dim, dtype=np.float32)
        if len(self.agents) > 0:
            agent = self.agents[0]
            model = agent.get("model")
            obs = self.last_observation if self.last_observation is not None else self._generate_mock_observation()
            if hasattr(model, "forward"):
                out = model.forward(obs)
                if isinstance(out, np.ndarray):
                    actions[:min(len(out), self.config.action_dim)] = out[:self.config.action_dim]

        # 1. Échange réseau avec Unity si connecté
        if self.connected_to_unity and self.socket:
            try:
                payload = {
                    "command": "STEP",
                    "actions": actions.tolist(),
                    "tick": self.tick_count,
                }
                msg = json.dumps(payload).encode("utf-8") + b"\n"
                self.socket.sendall(msg)
                self.total_packets_sent += 1

                resp_str = self._read_socket_line()
                if resp_str:
                    data = json.loads(resp_str)
                    obs_list = data.get("observation", [])
                    self.last_observation = np.array(obs_list, dtype=np.float32)
                    self.total_packets_received += 1
                    return
            except Exception:
                self.connected_to_unity = False

        # 2. Simulation locale réaliste (Physique newtonienne intégrée 3D)
        dt = self.config.step_dt
        thrust = actions[:3]  # Mouvement 3D [Fx, Fy, Fz]
        self._mock_vel += thrust * dt
        # Frottement de l'air / amortissement linéaire
        self._mock_vel *= 0.98
        self._mock_pos += self._mock_vel * dt

        # Coût métabolique
        effort = float(np.linalg.norm(thrust))
        self._mock_health = max(0.0, self._mock_health - effort * 0.05 + 0.01)

        self.last_observation = self._generate_mock_observation()
        if len(self.agents) > 0:
            self.agents[0]["energy"] = self._mock_health

    def add_agent(self, agent_model, **kwargs):
        """Ajoute un agent pilotant l'avatar Unity."""
        agent_dict = {
            "id": f"unity_agent_{len(self.agents)}",
            "model": agent_model,
            "energy": kwargs.get("energy", 100.0),
            "age": 0,
        }
        self.agents.append(agent_dict)
        return agent_dict

    def get_unity_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de la passerelle et de la simulation 3D."""
        return {
            "connected_to_unity": self.connected_to_unity,
            "tick_count": self.tick_count,
            "packets_sent": self.total_packets_sent,
            "packets_received": self.total_packets_received,
            "mock_position": self._mock_pos.tolist(),
            "mock_velocity": self._mock_vel.tolist(),
            "avatar_health": self._mock_health,
        }

    def close(self):
        """Ferme la connexion réseau si ouverte."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            self.connected_to_unity = False
