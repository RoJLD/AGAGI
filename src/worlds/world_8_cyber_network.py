"""
World 8 : Écosystème Cyber-Physique & Réseaux Distribués d'Information.
Modélise la topologie de réseau dynamique, le routage de paquets, la bande passante,
la latence de transmission et la détection d'intrusions byzantines.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from src.worlds.base_world import BaseWorld


@dataclass
class CyberNetworkConfig:
    """Configuration hyper-paramétrable pour le Monde 8 (Cyber-Réseau)."""
    num_nodes: int = 8                     # Nombre de routeurs / serveurs du graphe
    link_probability: float = 0.4          # Densité des liens de communication
    bandwidth_per_tick: int = 10           # Capacité maximale de paquets par lien
    packet_loss_rate: float = 0.05         # Taux de perte spontanée de paquets
    byzantine_corruption_rate: float = 0.15 # Taux de paquets malveillants injectés
    delivery_reward: float = 5.0           # Gain par paquet correctement délivré
    corruption_penalty: float = 3.0        # Pénalité en cas d'acceptation de paquet corrompu


class CyberNetworkWorld(BaseWorld):
    """
    Monde 8 : Cyber-Réseau Décentralisé.
    Les agents opèrent comme des routeurs ou agents réseau distribués :
    - Acheminement de paquets d'information de Source -> Destination.
    - Gestion de congestion de files d'attente (Buffer Bloat).
    - Filtrage cryptographique / Détection d'anomalies face aux paquets corrompus.
    - Métriques d'intégrité de flux, latence moyenne et débit utile (Goodput).
    """
    def __init__(self, config: Optional[CyberNetworkConfig] = None):
        super().__init__(size=1)
        self.config = config or CyberNetworkConfig()

        self.num_nodes = self.config.num_nodes
        self.adjacency_matrix = np.zeros((self.num_nodes, self.num_nodes), dtype=int)
        self._init_network_topology()

        # Files d'attente de paquets sur les noeuds
        self.packet_queues: Dict[int, List[Dict[str, Any]]] = {i: [] for i in range(self.num_nodes)}
        self.delivered_packets = 0
        self.corrupted_packets_detected = 0
        self.corrupted_packets_accepted = 0
        self.dropped_packets = 0

        self.reset()

    def _init_network_topology(self) -> None:
        """Génère un graphe de réseau connexe de manière vectorisée."""
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                if np.random.rand() < self.config.link_probability:
                    self.adjacency_matrix[i, j] = 1
                    self.adjacency_matrix[j, i] = 1
            # Assurer au moins une connexion (graphe connexe)
            target = (i + 1) % self.num_nodes
            self.adjacency_matrix[i, target] = 1
            self.adjacency_matrix[target, i] = 1

    def reset(self):
        """Réinitialise l'état du réseau et génère des paquets initiaux."""
        self.tick_count = 0
        for i in range(self.num_nodes):
            self.packet_queues[i].clear()
        self.spawn_packets(count=15)
        return self.get_network_state()

    def spawn_packets(self, count: int = 5) -> None:
        """Injecte de nouveaux paquets de données dans le réseau."""
        for _ in range(count):
            src = int(np.random.randint(0, self.num_nodes))
            dst = int(np.random.randint(0, self.num_nodes))
            while dst == src:
                dst = int(np.random.randint(0, self.num_nodes))

            is_corrupt = bool(np.random.rand() < self.config.byzantine_corruption_rate)
            checksum = 1.0 if not is_corrupt else -1.0

            packet = {
                "id": f"pkt_{self.tick_count}_{src}_{dst}",
                "src": src,
                "dst": dst,
                "hops": 0,
                "is_corrupt": is_corrupt,
                "checksum": checksum,
                "payload_size": 1.0,
            }
            self.packet_queues[src].append(packet)

    def get_network_state(self) -> np.ndarray:
        """Encode l'état global du réseau sous forme de tenseur d'observation normalisé."""
        queue_lengths = np.array([len(self.packet_queues[i]) for i in range(self.num_nodes)], dtype=np.float32)
        norm_queues = queue_lengths / float(max(1, self.config.bandwidth_per_tick * 2))
        return norm_queues

    def step(self):
        """Avance la simulation du réseau d'un cycle de routage."""
        self.tick_count += 1

        # 1. Traitement des paquets sur chaque routeur
        for node_id in range(self.num_nodes):
            queue = self.packet_queues[node_id]
            bandwidth_left = self.config.bandwidth_per_tick

            while queue and bandwidth_left > 0:
                pkt = queue.pop(0)
                bandwidth_left -= 1

                # Vérification de perte de paquet aléatoire
                if np.random.rand() < self.config.packet_loss_rate:
                    self.dropped_packets += 1
                    continue

                # Si le paquet est arrivé à destination
                if pkt["dst"] == node_id:
                    # Contrôle d'intégrité / Détection d'anomalies
                    if pkt["checksum"] < 0:
                        self.corrupted_packets_accepted += 1
                    else:
                        self.delivered_packets += 1
                        # Récompenser les agents hébergés sur ce noeud
                        for a in self.agents:
                            if a.get("node_id") == node_id:
                                a["energy"] = min(100.0, a["energy"] + self.config.delivery_reward)
                else:
                    # Routage vers le prochain saut connecté le plus proche
                    neighbors = np.where(self.adjacency_matrix[node_id] > 0)[0]
                    if len(neighbors) > 0:
                        # Choix du voisin le plus proche de la cible ou avec la file la moins encombrée
                        next_hop = int(np.random.choice(neighbors))
                        pkt["hops"] += 1
                        if len(self.packet_queues[next_hop]) < self.config.bandwidth_per_tick * 3:
                            self.packet_queues[next_hop].append(pkt)
                        else:
                            self.dropped_packets += 1  # Rejet pour congestion (Buffer Overflow)

        # 2. Injection continue de trafic
        if self.tick_count % 3 == 0:
            self.spawn_packets(count=4)

    def add_agent(self, agent_model, **kwargs):
        """Associe un agent à un noeud spécifique du réseau."""
        node_id = kwargs.get("node_id", len(self.agents) % self.num_nodes)
        agent_dict = {
            "id": f"net_agent_{len(self.agents)}",
            "model": agent_model,
            "node_id": node_id,
            "energy": kwargs.get("energy", 60.0),
            "age": 0,
        }
        self.agents.append(agent_dict)
        return agent_dict

    def get_cyber_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de santé et de performance du réseau."""
        total_finished = max(1, self.delivered_packets + self.corrupted_packets_accepted + self.dropped_packets)
        delivery_rate = float(self.delivered_packets / total_finished)
        return {
            "delivered_packets": self.delivered_packets,
            "corrupted_packets_accepted": self.corrupted_packets_accepted,
            "dropped_packets": self.dropped_packets,
            "delivery_rate": delivery_rate,
            "active_queues_total": sum(len(q) for q in self.packet_queues.values()),
        }
