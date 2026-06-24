"""Sonde funnel autel/outil (barreau 0 de l'EDR 014). Au sweet spot sur stoneage : l'autel est-il
structurellement mort (altars_solved jamais >0) et où les agents décrochent-ils dans le pathway outil
(craft -> usage mammouth) ? Observationnel, pure-lecture des champs d'agent (vivants+morts, EDR 092).
Spec : docs/superpowers/specs/2026-06-24-Altar-Tool-Funnel-Probe-design.md."""
import os
import sys
import logging
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.AltarToolFunnel")


def _frac(agents: List[Dict], key: str) -> float:
    """Fraction des agents avec champ `key` >= 1 (rare-event-aware). Liste vide -> 0.0."""
    if not agents:
        return 0.0
    return sum(1 for a in agents if a.get(key, 0) >= 1) / len(agents)


def _seed_summary(agents: List[Dict]) -> Dict:
    return {"n": len(agents),
            "frac_hunt": _frac(agents, "preys_eaten"),
            "frac_craft": _frac(agents, "spears_crafted"),
            "frac_apex": _frac(agents, "mammoth_kills"),
            "total_spears": sum(a.get("spears_crafted", 0) for a in agents),
            "total_mammoth_kills": sum(a.get("mammoth_kills", 0) for a in agents),
            "altars_solved_max": max((a.get("altars_solved", 0) for a in agents), default=0)}


def funnel_verdict(per_seed_agents: Dict, eps: float = 0.02) -> Dict:
    """Verdicts décomposés (autel + funnel outil) sur TOUS les agents poolés, fractions (pas médianes).
    Le verdict funnel localise le 1er étage qui s'effondre sous eps. par_seed = courbe complète."""
    all_agents = [a for agents in per_seed_agents.values() for a in agents]
    frac_hunt = _frac(all_agents, "preys_eaten")
    frac_craft = _frac(all_agents, "spears_crafted")
    frac_apex = _frac(all_agents, "mammoth_kills")
    altars_solved_max = max((a.get("altars_solved", 0) for a in all_agents), default=0)
    verdict_autel = "AUTEL_MORT" if altars_solved_max == 0 else "AUTEL_VIVANT"
    if frac_craft < eps:
        verdict_funnel = "GAP_ACQUISITION"
    elif frac_apex < eps:
        verdict_funnel = "GAP_USAGE"
    else:
        verdict_funnel = "PATHWAY_VIVANT"
    return {"verdict_autel": verdict_autel, "verdict_funnel": verdict_funnel,
            "frac_hunt": frac_hunt, "frac_craft": frac_craft, "frac_apex": frac_apex,
            "total_spears": sum(a.get("spears_crafted", 0) for a in all_agents),
            "total_mammoth_kills": sum(a.get("mammoth_kills", 0) for a in all_agents),
            "altars_solved_max": altars_solved_max, "n_agents": len(all_agents),
            "par_seed": {str(s): _seed_summary(agents) for s, agents in per_seed_agents.items()}}
