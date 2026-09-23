"""P4.13 (a) — `delta_distribution` (src/agents/mamba_agent.py) et son runner HoF (tools/delta_distribution_hof.py)
confrontés à des réponses CONNUES : diagonale nulle -> 0,5 exact (no-op) ; W_jj = ±10 et au-delà -> clip ;
monotonie ; nan COMPTÉ et exclu, jamais avalé ; aucune diagonale finie -> None, pas 0 ; agrégation à génomes
absents -> None. Aucun HoF lu ici."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agents.mamba_agent import DELTA_GELE, DELTA_INSTANTANE, delta_distribution  # noqa: E402
from tools.delta_distribution_hof import agrege  # noqa: E402


def _W(diag):
    W = np.random.RandomState(0).randn(len(diag), len(diag)) * 0.3     # hors-diagonale QUELCONQUE : ignorée
    np.fill_diagonal(W, diag)
    return W


def test_zero_diagonal_gives_exactly_one_half_everywhere():
    d = delta_distribution(_W([0.0] * 7))
    assert d == {"n": 7, "n_non_fini": 0, "min": 0.5, "mediane": 0.5, "max": 0.5, "part_gele": 0.0,
                 "part_instantane": 0.0, "part_diag_nulle": 1.0}


def test_prediction_matches_the_forward_formula_and_the_clip_at_ten():
    d = delta_distribution(_W([10.0, -10.0, 100.0, -100.0, 2.0]))
    s10 = 1.0 / (1.0 + np.exp(-10.0))
    assert d["max"] == pytest.approx(s10) and d["min"] == pytest.approx(1.0 - s10)     # 100 est clippé à 10
    assert d["part_instantane"] == pytest.approx(2 / 5) and d["part_gele"] == pytest.approx(2 / 5)
    assert d["part_diag_nulle"] == 0.0 and d["mediane"] == pytest.approx(1.0 / (1.0 + np.exp(-2.0)))
    assert DELTA_GELE < 0.5 < DELTA_INSTANTANE                                        # bornes publiées, pas un verdict


def test_monotone_in_the_diagonal():
    lo, hi = delta_distribution(_W([-1.0] * 4)), delta_distribution(_W([1.0] * 4))
    assert lo["mediane"] < 0.5 < hi["mediane"]


def test_non_finite_diagonal_entries_are_counted_and_excluded_never_swallowed():
    d = delta_distribution(_W([0.0, np.nan, np.inf, 0.0]))
    assert d["n"] == 4 and d["n_non_fini"] == 2 and d["mediane"] == 0.5 and d["part_diag_nulle"] == 1.0


def test_all_non_finite_gives_None_statistics_not_zero():
    d = delta_distribution(_W([np.nan, np.nan]))
    assert d["n_non_fini"] == 2 and d["mediane"] is None and d["part_gele"] is None


def test_accepts_a_genome_like_object_and_refuses_a_non_square_matrix():
    class G:
        W = _W([0.0, 3.0])
    assert delta_distribution(G())["n"] == 2
    with pytest.raises(ValueError):
        delta_distribution(np.zeros((2, 3)))


def test_aggregate_over_no_genome_is_None_not_zero_and_counts_genomes_without_statistics():
    vide = agrege({})
    assert vide["n_genomes"] == 0 and vide["mediane_mediane_des_genomes"] is None
    g = {"a": delta_distribution(_W([0.0] * 3)), "b": delta_distribution(_W([np.nan] * 3))}
    ag = agrege(g)
    assert ag == {"n_genomes": 2, "n_sans_stat": 1, "n_non_fini_total": 3, "min_mediane_des_genomes": 0.5,
                  "mediane_mediane_des_genomes": 0.5, "max_mediane_des_genomes": 0.5, "part_gele_mediane_des_genomes": 0.0,
                  "part_instantane_mediane_des_genomes": 0.0, "part_diag_nulle_mediane_des_genomes": 1.0}
