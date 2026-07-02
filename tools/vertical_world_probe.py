"""Probe VERTICALITÉ : un champion évolué en 2D exploite-t-il l'affordance verticale quand
on active use_3d ? Compare 2 bras (2D/3D) sur une cohorte fixe de clones d'un champion HoF.
Métrique de DÉCISION = utilisation de Z dans le bras 3D (z-range + fraction Up/Down chez les
survivants) ; survie = interprétatif (le cube 3D est plus creux). Détecteur de POSITIF bon
marché avant tout investissement de visualisation 3D. Voir spec 2026-06-30-vertical-world-probe."""
import os
import sys
import json
import statistics
from typing import Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def classify_vertical_signal(z_range_3d: float, updown_frac_3d: float,
                             updown_floor: float = 0.25, margin: float = 1.2,
                             z_eps: float = 0.5,
                             survival_2d: Optional[float] = None,
                             survival_3d: Optional[float] = None) -> Dict:
    """PUR. Verdict d'utilisation de Z dans le bras 3D.
    Z_UTILISE si z_range_3d > z_eps ET updown_frac_3d > updown_floor*margin ; sinon Z_INERTE.
    updown_floor = 2/8 (Up+Down sur 8 actions argmax) ; margin = marge au-dessus du hasard ;
    z_eps = au moins une transition de couche. survival_ratio interprétatif (epsilon anti /0)."""
    threshold = updown_floor * margin
    z_used = z_range_3d > z_eps
    updown_used = updown_frac_3d > threshold
    verdict = "Z_UTILISE" if (z_used and updown_used) else "Z_INERTE"
    survival_ratio: Optional[float] = None
    if survival_2d is not None and survival_3d is not None:
        survival_ratio = survival_3d / max(survival_2d, 1e-6)
    return {"verdict": verdict, "z_range_3d": z_range_3d, "updown_frac_3d": updown_frac_3d,
            "threshold": threshold, "survival_ratio": survival_ratio}
