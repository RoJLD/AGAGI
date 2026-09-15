"""`tools/learner_calibration.summarize` (P1.6) et sa tolérance aux cellules NON MESURÉES (P3.4).

Mesuré le 2026-09-15 (seed 2030, bras `natural` du legacy) : l'apprenant DIVERGE (NaN dans les logits) et
la cohorte ne prend plus AUCUNE décision ; `run_learner_probe` refuse de fabriquer un taux. Le runner publie
la cellule avec sa raison (`learning=None`), et `summarize` doit : la compter dans `n`, la publier dans
`non_mesures`, ne jamais l'avaler dans la médiane, et la garder au DÉNOMINATEUR du test des signes.
Aucun monde n'est simulé ici.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.learner_calibration import summarize  # noqa: E402


def _cell(first, last, upd=100):
    return {"hit_first": first, "hit_last": last,
            "learning": {"td_updates": upd, "episode_updates": 10, "dW_abs_sum": 5.0}}


def _arms(natural_2028=None):
    seeds = ("2026", "2027", "2028")
    nat = {"2026": _cell(0.20, 0.50), "2027": _cell(0.20, 0.45),
           "2028": natural_2028 if natural_2028 is not None else _cell(0.20, 0.48)}
    return {
        "oracle": {"per_seed": {s: _cell(1.0, 1.0, 0) for s in seeds}},
        "lr0_reference": {"per_seed": {s: _cell(0.12, 0.12, 0) for s in seeds}},
        "natural": {"per_seed": nat},
        "lr_low": {"per_seed": {s: _cell(0.20, 0.40) for s in seeds}},
    }


def test_summarize_all_cells_measured_reads_LEARNS_with_full_sign_count():
    out = summarize(_arms(), learner_arms=("natural", "lr_low"))
    assert out["medians"]["natural"]["n"] == 3 and out["medians"]["natural"]["non_mesures"] == 0
    v = out["verdicts"]["natural"]
    assert v["verdict"] == "LEARNER_LEARNS" and v["seeds_above_reference"] == "3/3" and v["seeds_non_mesures"] == 0


def test_summarize_keeps_an_UNMEASURED_cell_in_n_and_in_the_sign_denominator_never_in_the_median():
    non_mesure = {"hit_first": None, "hit_last": None, "learning": None,
                  "erreur": "bloc SANS aucune decision -- aucun taux n'est fabrique"}
    out = summarize(_arms(natural_2028=non_mesure), learner_arms=("natural", "lr_low"))
    m = out["medians"]["natural"]
    assert m["n"] == 3 and m["non_mesures"] == 1
    assert m["hit_last"] == 0.475                      # médiane des DEUX cellules mesurées (0.50, 0.45)
    v = out["verdicts"]["natural"]
    assert v["seeds_above_reference"] == "2/3"         # le seed divergent n'est PAS « au-dessus »
    assert v["seeds_non_mesures"] == 1
