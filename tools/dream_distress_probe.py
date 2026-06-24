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

from tools.curriculum_transfer import _sign_test_p


def dream_rate(agent: Dict) -> float:
    """Taux de rêve ajusté à l'exposition : total_dreams / max(age, 1) (age 0 -> dénominateur 1)."""
    return agent.get("total_dreams", 0) / max(agent.get("age", 0), 1)


def distress_split(stats: List[Dict], age_floor: int = 10) -> Dict:
    """Filtre age >= age_floor (écarte l'artefact petit-âge), split par âge médian, compare le taux
    de rêve médian des court-vivants vs long-vivants. delta = rate_short - rate_long (>0 = détresse)."""
    kept = [s for s in stats if s.get("age", 0) >= age_floor]
    if not kept:
        return {"rate_short": 0.0, "rate_long": 0.0, "delta": 0.0, "n_short": 0, "n_long": 0}
    med_age = statistics.median([s["age"] for s in kept])
    short = [s for s in kept if s["age"] < med_age]
    long = [s for s in kept if s["age"] >= med_age]
    r_short = float(statistics.median([dream_rate(s) for s in short])) if short else 0.0
    r_long = float(statistics.median([dream_rate(s) for s in long])) if long else 0.0
    return {"rate_short": r_short, "rate_long": r_long, "delta": r_short - r_long,
            "n_short": len(short), "n_long": len(long)}


def distress_verdict(deltas: List[float], delta_eps: float = 0.0) -> Dict:
    """Agrège les delta par seed. DETRESSE = court-vivants rêvent plus (median > eps ET sign_p<0.15) ;
    BENEFIQUE = long-vivants rêvent plus (median < -eps ET sign_p<0.15) ; NEUTRE sinon. sign_p calculé
    sur les deltas EFFECTIFS (≠0) -> évite k>n (pattern compute_transfer_verdict)."""
    if not deltas:
        return {"median_delta": 0.0, "n_favorable": 0, "sign_p": 1.0, "verdict": "NEUTRE"}
    med = float(statistics.median(deltas))
    n_fav = sum(1 for d in deltas if d > 0.0)
    effective = [d for d in deltas if d != 0.0]
    sign_p = _sign_test_p(sum(1 for d in effective if d > 0.0), len(effective))
    if med > delta_eps and sign_p < 0.15:
        verdict = "DETRESSE"
    elif med < -delta_eps and sign_p < 0.15:
        verdict = "BENEFIQUE"
    else:
        verdict = "NEUTRE"
    return {"median_delta": med, "n_favorable": n_fav, "sign_p": sign_p, "verdict": verdict}
