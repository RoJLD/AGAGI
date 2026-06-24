"""Sonde d'intervention causale du dreaming (Phase 2). Le dreaming CAUSE-t-il un meilleur sort, ou
corrèle-t-il à la détresse (EDR 093/094) ? Force l'acte + la profondeur du rêve via le hook gated
MambaBatchModel.FORCE_DREAM ; balaye {off,1,4,8} -> courbe dose-réponse de la survie.
Spec : docs/superpowers/specs/2026-06-24-Dream-Causal-Intervention-design.md. Diagnostic causal."""
import os
import sys
import logging
import statistics
from typing import List, Dict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.curriculum_transfer import _sign_test_p


def _paired_ratios(arm: List[float], off: List[float]) -> List[float]:
    m = min(len(arm), len(off))
    return [arm[i] / max(off[i], 1e-6) for i in range(m)]


def dose_response_verdict(per_arm: Dict, eps: float = 0.02) -> Dict:
    """Verdict ancré sur le bras le plus profond (max K) vs off, apparié par seed. Renvoie aussi la
    courbe dose-réponse complète (ratio apparié médian de chaque bras-K vs off)."""
    off = per_arm.get("off", [])
    ks = sorted(k for k in per_arm if k != "off")
    if not off or not ks:
        return {"ratio": 1.0, "sign_p": 1.0, "n_favorable": 0, "n": 0,
                "verdict": "NEUTRE", "ratios_par_K": {}}
    ratios_par_K = {}
    for k in ks:
        pr = _paired_ratios(per_arm[k], off)
        ratios_par_K[str(k)] = float(statistics.median(pr)) if pr else 1.0
    pr = _paired_ratios(per_arm[ks[-1]], off)            # bras le plus profond
    ratio = float(statistics.median(pr)) if pr else 1.0
    effective = [r for r in pr if r != 1.0]
    sign_p = _sign_test_p(sum(1 for r in effective if r > 1.0), len(effective))
    n_fav = sum(1 for r in pr if r > 1.0)
    if ratio > 1.0 + eps and sign_p < 0.1:
        verdict = "CAUSE_BENEFIQUE"
    elif ratio < 1.0 - eps and sign_p < 0.1:
        verdict = "CAUSE_NUISIBLE"
    else:
        verdict = "NEUTRE"
    return {"ratio": ratio, "sign_p": sign_p, "n_favorable": n_fav, "n": len(pr),
            "verdict": verdict, "ratios_par_K": ratios_par_K}
