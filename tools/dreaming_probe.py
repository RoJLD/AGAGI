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
