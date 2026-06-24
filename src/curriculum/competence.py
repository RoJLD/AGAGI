"""
Fonctions de compétence par monde (EDR 008 §KPI).

Transforment les stats brutes d'une ère (liste de dicts par agent, telle que
produite par base_world.run_era) en un scalaire de **compétence** dans [0, 1].
C'est le "bulletin de notes" qui pilote la graduation du CurriculumRunner.

Convention : agréger par la MÉDIANE (robuste aux outliers / génies isolés),
normaliser par une référence propre au monde, clamper dans [0, 1].
"""
from typing import List, Dict, Callable
import numpy as np


def _median_norm(values: List[float], ref: float) -> float:
    """Médiane des valeurs, normalisée par `ref`, clampée dans [0, 1]."""
    if not values or ref <= 0:
        return 0.0
    return float(np.clip(np.median(values) / ref, 0.0, 1.0))


# --- Monde 0 : Soup (exemple de référence, déjà implémenté) -----------------

AGE_REF = 200.0  # une ère = 200 ticks par défaut (base_world.run_era)


def soup_competence(agent_stats: List[Dict]) -> float:
    """
    Monde 0 (Soup) — stade sensorimoteur. Maîtrise = homéostasie : survivre
    longtemps. On prend la médiane des âges, normalisée par la durée d'une ère.
    Un score proche de 1 => la population tient toute l'ère sans s'éteindre.
    """
    ages = [a.get("age", 0) for a in agent_stats]
    return _median_norm(ages, AGE_REF)


# --- Monde 1 : Stoneage (À TOI) ---------------------------------------------

# Refs/poids à choisir par toi. Stats dispo par agent : age, energy,
# preys_eaten, altars_solved, total_dreams, total_reflexes.
PREY_REF = 5.0    # suggestion de point de départ — ajuste selon tes runs
ALTAR_REF = 3.0


def stoneage_competence(agent_stats: List[Dict]) -> float:
    """
    Monde 1 (Stoneage) — stade causalité/outil. Maîtrise = chasse + usage
    d'outils/puzzles.

    Choix retenus (à ajuster librement) :
      - Normalisation : médiane / réf, clampée — robuste aux génies isolés.
      - Pondération : l'outil/puzzle (`altars_solved`), plus "cognitif", pèse 0.6
        contre 0.4 pour la chasse (`preys_eaten`) — on récompense davantage le
        signe d'intelligence que le signe de survie brute.
    """
    hunt = _median_norm([a.get("preys_eaten", 0) for a in agent_stats], PREY_REF)
    tools = _median_norm([a.get("altars_solved", 0) for a in agent_stats], ALTAR_REF)
    return float(np.clip(0.4 * hunt + 0.6 * tools, 0.0, 1.0))


# --- Mondes 2/3/Gym : implémentations PROVISOIRES -----------------------------
# Les vrais KPI (stock, social_density, chaînes d'outils) ne sont pas tous dans
# les stats par-agent collectées aujourd'hui. En attendant, on dérive des proxys
# robustes des stats disponibles (age, energy, preys_eaten, altars_solved,
# total_dreams). À raffiner monde par monde, comme stoneage_competence (cf. EDR 008).

DREAM_REF = 3.0     # profondeur de planification (proxy MCTS)
GYM_ALTAR_REF = 5.0


def agricultural_competence(agent_stats: List[Dict]) -> float:
    """Monde 2 — planification / gratification différée. PROVISOIRE :
    horizon de planification (total_dreams) + persistance (age)."""
    horizon = _median_norm([a.get("total_dreams", 0) for a in agent_stats], DREAM_REF)
    persist = _median_norm([a.get("age", 0) for a in agent_stats], AGE_REF)
    return float(np.clip(0.5 * horizon + 0.5 * persist, 0.0, 1.0))


def industrial_competence(agent_stats: List[Dict]) -> float:
    """Monde 3 — composition / abstraction. PROVISOIRE :
    composition d'outils (altars_solved) + persistance (age)."""
    compose = _median_norm([a.get("altars_solved", 0) for a in agent_stats], ALTAR_REF)
    persist = _median_norm([a.get("age", 0) for a in agent_stats], AGE_REF)
    return float(np.clip(0.6 * compose + 0.4 * persist, 0.0, 1.0))


def gym_competence(agent_stats: List[Dict]) -> float:
    """Gym — opérations formelles. PROVISOIRE : résolution de puzzles (altars_solved)."""
    return _median_norm([a.get("altars_solved", 0) for a in agent_stats], GYM_ALTAR_REF)


# --- Métrique de SURVIE (transfert re-métricisé, EDR 085/090) ----------------
# Le signal d'autel/outil est nul tant que le goulot d'exploration (EDR 014) tient ->
# `*_competence` (pondérées altars 0.6) restent au plancher. Pour mesurer le TRANSFERT sur une
# dimension où le monde discrimine RÉELLEMENT la compétence, on agrège la SURVIE (âge), qui a un
# gradient au sweet spot énergie (champion 163-227 vs frais 44, EDR 085). Indépendant du monde.

def survival_competence(agent_stats: List[Dict]) -> float:
    """Compétence = survie : médiane des âges / AGE_REF, clampée (cf. soup_competence). Robuste
    aux génies isolés (convention médiane). À utiliser AU SWEET SPOT énergie (sinon plancher létal)."""
    return _median_norm([a.get("age", 0) for a in agent_stats], AGE_REF)


# --- Registre : world_type -> competence_fn ---------------------------------

COMPETENCE_REGISTRY: Dict[str, Callable[[List[Dict]], float]] = {
    "soup": soup_competence,
    "stoneage": stoneage_competence,
    "agricultural": agricultural_competence,
    "industrial": industrial_competence,
    "gym": gym_competence,
}


def competence_for(world_type: str) -> Callable[[List[Dict]], float]:
    """Renvoie la fonction de compétence d'un monde (KeyError si inconnu)."""
    return COMPETENCE_REGISTRY[world_type]
