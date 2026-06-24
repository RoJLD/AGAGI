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
