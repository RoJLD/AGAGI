import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.map_elites import MapElitesArchive
from tools.qd_tier_rescue import _tier_coverage, _verdict_qd_rescue


def test_tier_coverage_counts_cells_per_tier():
    arch = MapElitesArchive()
    arch.cells = {
        (0, 0): (1.0, object(), {}),
        (1, 1): (1.0, object(), {}),
        (2, 2): (1.0, object(), {}),
        (3, 2): (1.0, object(), {}),
        (4, 3): (1.0, object(), {}),
    }
    assert _tier_coverage(arch) == {"cells_tier0": 1, "cells_tier1": 1, "cells_tier2": 2, "cells_tier3": 1}


def test_tier_coverage_empty_archive():
    assert _tier_coverage(MapElitesArchive()) == {"cells_tier0": 0, "cells_tier1": 0, "cells_tier2": 0, "cells_tier3": 0}


def test_verdict_qd_rescue_confirme():
    assert _verdict_qd_rescue({"frac_craft": 0.01}, {"frac_craft": 0.15}) == "QD_RESCUE_CRAFT CONFIRME"


def test_verdict_qd_rescue_neutre():
    assert _verdict_qd_rescue({"frac_craft": 0.01}, {"frac_craft": 0.05}) == "QD_NEUTRE"


def test_verdict_qd_rescue_nuit():
    assert _verdict_qd_rescue({"frac_craft": 0.20}, {"frac_craft": 0.05}) == "QD_NUIT"


def test_verdict_qd_rescue_lift_but_still_floored_is_neutre():
    assert _verdict_qd_rescue({"frac_craft": 0.01}, {"frac_craft": 0.10}) == "QD_NEUTRE"
