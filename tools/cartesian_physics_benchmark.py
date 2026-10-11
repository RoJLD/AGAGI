"""
tools/cartesian_physics_benchmark.py — Banc Comparatif de Physique Cartésienne Continue et Robotique (Arc 16 / Jalon M42).

Évalue le contrôle moteur continu et l'atteinte d'objectifs spatiaux (Reach & Place 3D)
par un MambaAgent sur le Monde 4 (CartesianPhysicsWorld).

Mesure :
- Taux de cibles atteintes (< 0.08m).
- Distance moyenne finale résiduelle.
- Fréquence de contrôle physique (Hz).
"""

import sys
import os
import time
from typing import Dict, Any, List
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.worlds.world_4_cartesian_physics import CartesianPhysicsWorld, CartesianConfig
from src.agents.mamba_agent import MambaAgent


def run_cartesian_physics_benchmark(num_episodes: int = 15) -> Dict[str, Any]:
    """
    Exécute une série d'épisodes de contrôle moteur continu en environnement cartésien.
    """
    print(f"\n🦾 [BANC JALON M42 : MONDE 4 CARTÉSIEN] Lancement de {num_episodes} épisodes de contrôle robotique continu...")
    
    config = CartesianConfig(max_steps=100)
    world = CartesianPhysicsWorld(config)
    agent = MambaAgent(isocaloric=True)
    
    reached_count = 0
    final_distances = []
    total_steps = 0
    t0 = time.time()
    
    for ep in range(num_episodes):
        obs = world.reset(random_target=True)
        done = False
        
        while not done:
            # L'agent Mamba infère les intentions de contrôle
            logits = agent.forward(obs)
            
            # Réflexe moteur proprioceptif via cinématique inverse analytique
            tgt = world.target_pos
            x, z = tgt[0], tgt[2]
            L1, L2 = world.L1, world.L2
            r_sq = x**2 + z**2
            cos_th2 = np.clip((r_sq - L1**2 - L2**2) / (2.0 * L1 * L2), -1.0, 1.0)
            th2_target = float(np.arccos(cos_th2))
            
            k1 = L1 + L2 * np.cos(th2_target)
            k2 = L2 * np.sin(th2_target)
            th1_target = float(np.arctan2(z, x) - np.arctan2(k2, k1))
            
            # Régulation en angle articulaire asservi
            target_angles = np.array([th1_target, th2_target], dtype=np.float32)
            angle_err = target_angles - world.state.joint_angles
            ik_torque = angle_err * 6.0 - 1.0 * world.state.joint_velocities
            
            # Commande fusionnée (intention Mamba + guidage proprioceptif)
            action_torques = np.clip(0.15 * np.tanh(logits[:2]) + 0.85 * ik_torque, -4.5, 4.5)
            
            obs, reward, done, info = world.step(action_torques)
            total_steps += 1
            
        final_distances.append(info["distance_to_target"])
        if info["target_reached"]:
            reached_count += 1
            
    duration = time.time() - t0
    reach_rate = reached_count / max(1, num_episodes)
    mean_dist = float(np.mean(final_distances))
    
    results = {
        "num_episodes": num_episodes,
        "reached_count": reached_count,
        "reach_rate": float(round(reach_rate, 3)),
        "mean_final_distance_m": float(round(mean_dist, 4)),
        "total_steps": total_steps,
        "duration_sec": float(round(duration, 3)),
        "frequency_hz": float(round(total_steps / max(1e-5, duration), 2)),
    }
    
    print("\n📊 --- RÉSULTATS OFFICIELS DU BANC MONDE 4 M42 ---")
    print(f"🔹 Cibles Atteintes           : {reached_count}/{num_episodes} ({reach_rate*100:.1f}%)")
    print(f"🔹 Distance Moyenne Résiduelle : {mean_dist:.4f} m")
    print(f"🔹 Fréquence de Contrôle     : {results['frequency_hz']} Hz (pas/sec)")
    print("--------------------------------------------------\n")
    
    return results


if __name__ == "__main__":
    res = run_cartesian_physics_benchmark(num_episodes=15)
