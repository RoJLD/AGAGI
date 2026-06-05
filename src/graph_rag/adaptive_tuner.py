"""
Adaptive Tuner — Lien entre le supervisor, KuzuDB et la simulation.
Reçoit les recommandations du supervisor et les injecte dans le monde.
"""
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AdaptiveConfig:
    """Configuration du tuner adaptatif."""
    def __init__(self):
        self.mutation_rate: float = 0.01
        self.crossover_rate: float = 0.5
        self.temperature: float = 1.0
        self.consensus_threshold: float = 0.5
        self.energy_reward_scale: float = 1.0
        self.social_bonus_scale: float = 1.0

class AdaptiveTuner:
    """
    Orchestre l'adaptation du monde selon les recommandations du supervisor.
    Commandement 4: Non-Bloquant (threading asynchrone).
    """
    def __init__(self, db_connection=None):
        self.db_conn = db_connection
        self.config = AdaptiveConfig()
        self.metrics_buffer = []
        self.feedback_enabled = True
        self._lock = threading.Lock()
        
    def ingest_frame_metrics(self, frame_summary: Dict[str, Any]):
        """Reçoit les métriques de chaque frame de simulation."""
        with self._lock:
            self.metrics_buffer.append({
                "timestamp": time.time(),
                "metrics": frame_summary
            })
            # Garder seulement les 100 derniers frames
            if len(self.metrics_buffer) > 100:
                self.metrics_buffer.pop(0)
                
    def compute_aggregated_score(self) -> Dict[str, float]:
        """Agrège les métriques sur la fenêtre glissante."""
        if not self.metrics_buffer:
            return {
                "avg_energy": 0.0,
                "energy_stability": 0.0,
                "social_density": 0.0,
                "genome_diversity": 0.0,
                "robustness": 0.0,
                "emergence": 0.0
            }
            
        with self._lock:
            energies = [m["metrics"].get("avg_energy", 0) for m in self.metrics_buffer]
            hp_values = [m["metrics"].get("avg_hp", 0) for m in self.metrics_buffer]
            social_densities = [m["metrics"].get("social_density", 0) for m in self.metrics_buffer]
            genome_diversities = [m["metrics"].get("genome_diversity", 0) for m in self.metrics_buffer]
            
        avg_energy = float(np.mean(energies)) if energies else 0.0
        energy_std = float(np.std(energies)) if len(energies) > 1 else 0.0
        energy_stability = 1.0 / (1.0 + energy_std)  # Stabilité = inverse de la variance
        
        social_density = float(np.mean(social_densities)) if social_densities else 0.0
        genome_diversity = float(np.mean(genome_diversities)) if genome_diversities else 0.0
        
        # Robustesse = stabilité énergétique + diversité génomique
        robustness = (energy_stability + genome_diversity) / 2.0
        
        # Émergeance = densité sociale + diversité génomique
        emergence = (social_density + genome_diversity) / 2.0
        
        return {
            "avg_energy": avg_energy,
            "energy_stability": energy_stability,
            "social_density": social_density,
            "genome_diversity": genome_diversity,
            "robustness": robustness,
            "emergence": emergence
        }
        
    def apply_supervisor_recommendation(self, recommendation: Dict[str, Any]):
        """Applique les recommandations du supervisor."""
        logger.info(f"Applying supervisor recommendation: {recommendation}")
        
        with self._lock:
            for key, value in recommendation.items():
                if hasattr(self.config, key):
                    old_val = getattr(self.config, key)
                    setattr(self.config, key, value)
                    logger.info(f"Tuned {key}: {old_val} -> {value}")
                    
    def log_to_kuzu(self, event_type: str, payload: Dict[str, Any]):
        """Enregistre les événements dans KuzuDB."""
        if self.db_conn is None:
            return
            
        try:
            # Format Cypher simplifié pour AGIseed
            if event_type == "FRAME_SUMMARY":
                # Pseudo: CREATE (f:FrameSummary {timestamp: ..., energy: ..., diversity: ...})
                pass
            elif event_type == "TUNING_CHANGE":
                # Pseudo: CREATE (t:TuningEvent {parameter: ..., old_value: ..., new_value: ...})
                pass
        except Exception as e:
            logger.error(f"Failed to log {event_type} to KuzuDB: {e}")
            
    def get_world_injection_config(self) -> Dict[str, Any]:
        """Retourne les paramètres à injecter dans le monde."""
        with self._lock:
            return {
                "mutation_rate": self.config.mutation_rate,
                "crossover_rate": self.config.crossover_rate,
                "temperature": self.config.temperature,
                "energy_reward_scale": self.config.energy_reward_scale,
                "social_bonus_scale": self.config.social_bonus_scale,
            }
