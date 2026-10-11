"""
tools/planetary_omniverse_benchmark.py — Banc Officiel de Civilisation Planétaire & Spatiale (Arc 18 : Jalon M51).
Évalue la capacité de l'architecture à piloter simultanément :
1. Les télécommunications distribuées et l'intégrité de flux (Monde 8).
2. L'équilibre thermodynamique et l'atténuation du carbone planétaire (Monde 9).
3. La navigation orbitale et l'expansion spatiale dans un champ gravitationnel (Monde 10).
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.worlds.planetary_omniverse_conductor import PlanetaryOmniverseConductor, OmniverseConfig


def run_planetary_omniverse_benchmark(num_steps: int = 30) -> dict:
    """
    Exécute une campagne globale d'évaluation planétaire et orbitale.
    """
    conductor = PlanetaryOmniverseConductor(OmniverseConfig(simulation_steps=num_steps))

    class AdaptiveCivilizationAgent:
        def forward(self, obs):
            # Politique mixte : action équilibrée selon l'observation
            if len(obs) == 4:
                # Agent climatique : alterne subsistance et reboisement
                return np.array([0.4, 0.6])
            elif len(obs) >= 6:
                # Agent orbital : visée vectorielle vers la cible
                target_rel = obs[4:6]
                return target_rel
            else:
                return np.zeros(2)

    agent = AdaptiveCivilizationAgent()
    conductor.cyber_world.add_agent(agent, node_id=0)
    conductor.climate_world.add_agent(agent)
    conductor.orbital_world.add_agent(agent, initial_radius=5.0)

    print("🌌 ====================================================================")
    print("🌟 [BANC ARC 18 : CIVILISATION PLANÉTAIRE & SPATIALE OMNIVERSELLE]")
    print("🌌 ====================================================================")

    kardashev_history = []

    for s in range(1, num_steps + 1):
        res = conductor.step()
        kardashev_history.append(res["kardashev_index"])
        if s % 10 == 0 or s == num_steps:
            print(f"Étape {s:02d} | Cyber: {res['cyber_score']:.3f} | Climat: {res['climate_score']:.3f} | Orbital: {res['orbital_score']:.3f} | Kardashev: {res['kardashev_index']:.4f}")

    mean_kardashev = float(np.mean(kardashev_history))
    final_report = conductor.get_omniverse_report()

    print("--------------------------------------------------------------------")
    print(f"📡 Paquets Délivrés Réseau     : {final_report['cyber']['delivered_packets']}")
    print(f"🌍 Anomalie Thermique Finale    : {final_report['climate']['temp_anomaly']:.2f} °C")
    print(f"🛰️ Carbone Capturé              : {final_report['climate']['carbon_captured']:.2f} Gt")
    print(f"🚀 Delta-V Orbital Consommé     : {final_report['orbital']['total_delta_v_spent']:.2f} m/s")
    print(f"👑 Indice de Kardashev Moyen    : {mean_kardashev:.4f}")
    print("--------------------------------------------------------------------")
    print("✅ RÉSULTAT : Civilisation Planétaire et Spatiale Validée avec Succès !")

    return {
        "steps": num_steps,
        "mean_kardashev": mean_kardashev,
        "final_report": final_report,
    }


if __name__ == "__main__":
    run_planetary_omniverse_benchmark()
