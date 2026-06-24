"""Sonde de Dreaming (barreau 0, attaque du goulot d'exploration EDR 014, approche A).
L'organe MCTS (+0.5 drain) est-il (Q1) survivable au sweet spot vs létal, et (Q2) payant quand
présent ? Spec : docs/superpowers/specs/2026-06-23-Dreaming-Organ-Revival-design.md.
Diagnostic SEUL : observe, ne répare pas le moteur."""
import os
import sys
import logging
import statistics
from typing import List, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.curriculum.competence import survival_competence
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.harness import SeedManager, Harness
from src.graph_rag.async_logger import logger as async_logger
from src.agents.mamba_agent import MambaAgent
from main_biosphere import init_primordial_soup
from main_curriculum import _prepare_world, _acquire_shared_db

log = logging.getLogger("AGIseed.DreamingProbe")


def _has_organ(agent: Dict) -> bool:
    """True si l'agent porte l'organe MCTS (organ_genes[0]). Robuste aux champs manquants."""
    model = agent.get("model")
    genome = getattr(model, "genome", None)
    og = getattr(genome, "organ_genes", None)
    return bool(og is not None and len(og) > 0 and og[0])


def organ_prevalence(agents: List[Dict]) -> float:
    """Fraction des agents portant l'organe MCTS. Liste vide -> 0.0."""
    if not agents:
        return 0.0
    return sum(1 for a in agents if _has_organ(a)) / len(agents)


def q2_split(stats: List[Dict]) -> Dict:
    """Sépare les agents par rêve (total_dreams>0) et compare leur compétence-survie.
    Groupe vide -> compétence 0.0 (convention survival_competence)."""
    dreamers = [s for s in stats if s.get("total_dreams", 0) > 0]
    nondreamers = [s for s in stats if s.get("total_dreams", 0) == 0]
    c_d = survival_competence(dreamers)
    c_n = survival_competence(nondreamers)
    return {"dreamers_competence": c_d, "nondreamers_competence": c_n,
            "delta": c_d - c_n, "n_dreamers": len(dreamers), "n_nondreamers": len(nondreamers)}


def dreaming_verdict(delta_prev_sweet: float, delta_prev_lethal: float,
                     q2a_delta: float, q2b_ratio: float,
                     surv_eps: float = 0.05, pay_eps: float = 0.02) -> str:
    """Gate 4-cas. SURVIT = organe toléré au sweet spot (Δprev > -eps) ET moins purgé qu'au létal
    (pression nette > 0). PAYE = bénéfice intra-pop (q2a_delta > pay_eps) OU population on>off
    (q2b_ratio > 1+pay_eps)."""
    survives = (delta_prev_sweet > -surv_eps) and ((delta_prev_sweet - delta_prev_lethal) > 0)
    pays = (q2a_delta > pay_eps) or (q2b_ratio > 1.0 + pay_eps)
    if survives and pays:
        return "SURVIT_ET_PAYE"
    if survives and not pays:
        return "SURVIT_PAS_PAYE"
    if (not survives) and pays:
        return "PAYE_PAS_SURVIT"
    return "MORT"


def _set_organ(genome, on: bool) -> None:
    """Force organ_genes[0] (MCTS) sur un génome LOCAL. Préserve les autres organes."""
    og = np.array(genome.organ_genes, dtype=bool) if getattr(genome, "organ_genes", None) is not None \
        else np.array([False, False], dtype=bool)
    og[0] = bool(on)
    genome.organ_genes = og


def run_era_organ(target: str, seed: int, organ_fraction: float, metab: float, payoff: float,
                  num_agents: int, max_ticks: int, shared_db) -> List[Dict]:
    """UNE ère sur `target`, avec une fraction `organ_fraction` de la population portant l'organe
    MCTS (les `int(organ_fraction*num_agents)` premiers). Renvoie par agent vivant à la fin :
    {age, total_dreams, has_organ}. Déterministe (memory_retriever neutralisé)."""
    SeedManager(seed).seed_boundary(0)
    config = WorldConfig()
    config.base_metabolism = metab
    config.forage_payoff = payoff
    env = _prepare_world(target, config, deterministic=True)

    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    n_on = int(round(organ_fraction * len(genomes)))
    for i, g in enumerate(genomes):
        _set_organ(g, i < n_on)
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=50.0)

    env.current_era = 1
    t = 0
    while len(env.agents) > 0 and t < max_ticks:
        env.step()
        t += 1

    survivors = list(env.agents)        # vivants à la fin -> signal de mortalité différentielle (Q1)
    out = [{"age": a.get("age", 0), "total_dreams": a.get("total_dreams", 0),
            "has_organ": _has_organ(a)} for a in survivors]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out
