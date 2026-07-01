"""tools/tom_coordination.py — ToM comportementale : la chasse coop est-elle COORDONNEE ? (P4 audit memoire, #2).

Tranche le caveat #2 d'EDR 132 (decode latent = contexte partage vs modelisation). Mecanique (EDR 028) :
attaquer = etre sur la cellule d'une proie (world_1_stoneage:692) ; le mammouth (hp 100) meurt des degats
cumules du pack. Question : parmi les agents proches d'un mammouth FRAIS, la proba d'attaquer est-elle plus
haute quand d'AUTRES agents sont proches (recrutement) ou inchangee (convergence fortuite) ?

Tooling pur READ-ONLY (pas de src/ modifie ; competence_profile/map_elites_compare importes).
Usage : MEC_PRESERVE_DIMS=1 python -m tools.tom_coordination
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, PRESERVE_DIMS
from tools.competence_profile import _evolve_champions


def _manhattan(a, m):
    return abs(a["x"] - m["x"]) + abs(a["y"] - m["y"])


def _hunt_samples_from_state(agents, preys, mammoth_hp):
    """Pour chaque mammouth FRAIS (hp >= 0.5*mammoth_hp), pour chaque agent a distance Manhattan <= 2 :
    {attacking: dist==0, others_near: nb d'AUTRES agents a <= 2 du mammouth}."""
    samples = []
    thresh = 0.5 * mammoth_hp
    for m in preys:
        if m.get("type") != "Mammouth" or m.get("hp", 0.0) < thresh:
            continue
        near = [a for a in agents if _manhattan(a, m) <= 2]
        for a in near:
            samples.append({"attacking": _manhattan(a, m) == 0, "others_near": len(near) - 1})
    return samples


def _recruitment_signal(samples):
    """p_with = P(attaque | others_near>=1), p_alone = P(attaque | others_near==0), delta = with - alone."""
    with_ = [s for s in samples if s["others_near"] >= 1]
    alone = [s for s in samples if s["others_near"] == 0]

    def _rate(xs):
        return float(np.mean([1.0 if s["attacking"] else 0.0 for s in xs])) if xs else 0.0

    p_with, p_alone = _rate(with_), _rate(alone)
    return {"p_with": p_with, "p_alone": p_alone, "delta": p_with - p_alone,
            "n_with": len(with_), "n_alone": len(alone)}


def _verdict_coordination(sig):
    """INDETERMINE si trop peu d'obs ; COORDINATED si delta >= 0.10 (recrutement) ; sinon INDEPENDENT."""
    if sig["n_with"] < 20 or sig["n_alone"] < 20:
        return "INDETERMINE"
    if sig["delta"] >= 0.10:
        return "COORDINATED"
    return "INDEPENDENT"
