import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.map_elites import MapElitesArchive
from tools.qd_tier_rescue import (
    _tier_coverage,
    _verdict_qd_rescue,
    _evolve_qd_champions,
    main_qd_tier_rescue,
    _report_qd_rescue,
)


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


def test_evolve_qd_champions_populates_craft_cell_with_fake_runner():
    def _g(nodes):
        return types.SimpleNamespace(num_nodes=nodes)

    def fake_runner(cfg, genomes, max_ticks):
        pool = [
            (10.0, _g(160), {"num_nodes": 160, "preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 0}),
            (50.0, _g(200), {"num_nodes": 200, "preys_eaten": 2, "spears_crafted": 3, "mammoth_kills": 0}),
        ]
        return pool, {"score": 50.0, "ticks": 10.0}

    champs, archive = _evolve_qd_champions(seed=99260, eras=2, num_agents=6, max_ticks=10, run_era_fn=fake_runner)
    assert archive.coverage() > 0
    assert _tier_coverage(archive)["cells_tier2"] >= 1
    assert isinstance(champs, list)


def test_smoke_main_qd_tier_rescue_returns_verdict():
    res = main_qd_tier_rescue(R=1, eras=2, num_agents=10, max_ticks=80, seed=99260, _return=True)
    assert res["verdict"] in {"QD_RESCUE_CRAFT CONFIRME", "QD_NEUTRE", "QD_NUIT"}
    assert "d_craft" in res
    assert len(res["per_seed"]) == 1
    assert set(res["per_seed"][0].keys()) >= {"seed", "hof", "qd", "coverage"}


def test_report_qd_rescue_per_seed_sign_and_craft_share():
    class _FakeH:
        def save(self, d):
            self.saved = d

    per_seed = [
        {"seed": 1, "hof": {"frac_forage": 0.6, "frac_craft": 0.01, "frac_apex": 0.16, "n": 30},
         "qd": {"frac_forage": 0.6, "frac_craft": 0.40, "frac_apex": 0.16, "n": 30},
         "coverage": {"cells_tier0": 2, "cells_tier1": 3, "cells_tier2": 1, "cells_tier3": 1}},
        {"seed": 2, "hof": {"frac_forage": 0.6, "frac_craft": 0.01, "frac_apex": 0.16, "n": 30},
         "qd": {"frac_forage": 0.6, "frac_craft": 0.00, "frac_apex": 0.16, "n": 30},
         "coverage": {"cells_tier0": 2, "cells_tier1": 3, "cells_tier2": 0, "cells_tier3": 1}},
        {"seed": 3, "hof": {"frac_forage": 0.6, "frac_craft": 0.01, "frac_apex": 0.16, "n": 30},
         "qd": {"frac_forage": 0.6, "frac_craft": 0.00, "frac_apex": 0.16, "n": 30},
         "coverage": {"cells_tier0": 2, "cells_tier1": 3, "cells_tier2": 0, "cells_tier3": 1}},
    ]
    res = _report_qd_rescue(_FakeH(), per_seed, R=3, _return=True)
    # moyenne qd craft = 0.1333, d = 0.1233 -> le verdict GELE (sur moyenne) est CONFIRME
    assert res["verdict"] == "QD_RESCUE_CRAFT CONFIRME"
    # mais un SEUL seed le porte (I1) :
    assert res["n_confirme_seeds"] == 1
    # borne haute sample (C1) : mean(cells_tier2)=1/3 / mean(coverage_tot)=19/3 ~ 0.0526
    assert 0.04 < res["craft_cell_share"] < 0.06
