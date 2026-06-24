"""Sonde de signature de détresse du dreaming (Phase 1-A, corrélationnel). Les rêves se concentrent-
ils chez les agents proches de la mort ? Spec : docs/superpowers/specs/2026-06-24-Dream-Distress-
Signature-design.md. ORIENTANT, pas définitif (la Phase 2 causale tranche). Diagnostic seul."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def dream_rate(agent: Dict) -> float:
    """Taux de rêve ajusté à l'exposition : total_dreams / max(age, 1) (age 0 -> dénominateur 1)."""
    return agent.get("total_dreams", 0) / max(agent.get("age", 0), 1)
