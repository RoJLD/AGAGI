"""tools/s2_regime_diagnostic.py — Diagnostic de régime S2 (outillage EXPLORATOIRE).
Tranche pourquoi le champion HoF ≈ dummy au benchmark S2 : sous-puissance (H1), effet plancher de
régime énergétique (H2), ou n'exige-pas-réel (H3). Grille 2 régimes × 3 agents sur stoneage, K ères
appariées. Recommande le régime où lancer le S2 confirmatoire. N'amende PAS la pré-reg S2.
Spec : docs/superpowers/specs/2026-06-29-s2-regime-diagnostic-design.md
Usage : python tools/s2_regime_diagnostic.py   (EXPERIMENT_SEED=2026 par défaut)"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.s2_stats import cliffs_delta, wilcoxon_signed_rank, ALPHA, CLIFF_THRESH

# Régimes énergétiques (base_metabolism, forage_payoff). 'defaut' = prod/historique ; 'sweet' = EDR085.
REGIMES = {"defaut": (1.0, 1.0), "sweet": (0.25, 3.0)}

# Seuils DIAGNOSTIC (exploratoires, ajustables) — distincts des seuils confirmatoires pré-enregistrés.
SURV_FLOOR_FRAC = 0.5     # médiane d'âge >= 50% de max_ticks -> régime survivable (absolu)
CENSORED_SURV = 0.25      # OU >= 25% censurés (survivants à max_ticks) -> survivable
LIFT_RATIO = 1.5          # sweet relève la survie >= 1.5x le défaut -> "sort du plancher"


def _beats(champ, base):
    """Le champion BAT le baseline : p<ALPHA (Wilcoxon signé apparié sur era_survival) ET
    Cliff δ >= CLIFF_THRESH (sur les individus poolés). Renvoie {p, cliff, beats}."""
    ce = np.asarray(champ["era_survival"], dtype=float)
    be = np.asarray(base["era_survival"], dtype=float)
    m = min(ce.size, be.size)
    _w, p = wilcoxon_signed_rank(ce[:m] - be[:m])
    cliff = cliffs_delta(champ["survival"], base["survival"])
    return {"p": float(p), "cliff": float(cliff), "beats": bool(p < ALPHA and cliff >= CLIFF_THRESH)}


def _strongest_baseline(regime_cells):
    """Baseline (hors 'champion') à plus haute survie médiane = le plus dur à battre."""
    keys = [k for k in regime_cells if k != "champion"]
    return max(keys, key=lambda k: float(np.median(regime_cells[k]["survival"]))
               if regime_cells[k]["survival"] else 0.0)


def _median(cell):
    return float(np.median(cell["survival"])) if cell["survival"] else 0.0


def _survivable(champ, max_ticks):
    """Régime survivable : médiane d'âge du champion >= SURV_FLOOR_FRAC*max_ticks OU censuré >= CENSORED_SURV."""
    return bool(_median(champ) >= SURV_FLOOR_FRAC * max_ticks
                or float(champ.get("censored_frac", 0.0)) >= CENSORED_SURV)


def regime_diagnostic_verdict(cells, max_ticks=400):
    """Verdict du diagnostic à partir de `cells[regime][agent]` (dicts run_condition). Table §C de la spec.
    Ordre : (1) champion bat au défaut -> SOUS_PUISSANCE ; sinon (2a) défaut au plancher + sweet survivable
    (lift) + champion bat au sweet -> CONFOND_PLANCHER ; (2b) sweet survivable + champion ne bat pas ->
    N_EXIGE_PAS_REEL ; (2c) sinon -> AMBIGU."""
    per = {}
    for regime, rc in cells.items():
        sb = _strongest_baseline(rc)
        cmp = _beats(rc["champion"], rc[sb])
        per[regime] = {"strongest_baseline": sb, "p": cmp["p"], "cliff": cmp["cliff"],
                       "beats": cmp["beats"], "survivable": _survivable(rc["champion"], max_ticks),
                       "champ_median": _median(rc["champion"]),
                       "censored_frac": float(rc["champion"].get("censored_frac", 0.0))}
    md, ms = per.get("defaut", {}), per.get("sweet", {})
    md_med, ms_med = md.get("champ_median", 0.0), ms.get("champ_median", 0.0)
    lift = (ms_med / md_med) if md_med > 0 else (float("inf") if ms_med > 0 else 1.0)

    if md.get("beats"):
        verdict, reco = "SOUS_PUISSANCE", "defaut"
    elif (not md.get("survivable")) and ms.get("survivable") and lift >= LIFT_RATIO and ms.get("beats"):
        verdict, reco = "CONFOND_PLANCHER", "sweet"
    elif ms.get("survivable") and not ms.get("beats"):
        verdict, reco = "N_EXIGE_PAS_REEL", None
    else:
        verdict, reco = "AMBIGU", None

    return {"verdict": verdict, "regime_recommande": reco, "lift": float(lift), "per_regime": per,
            "thresholds": {"ALPHA": ALPHA, "CLIFF_THRESH": CLIFF_THRESH,
                           "SURV_FLOOR_FRAC": SURV_FLOOR_FRAC, "CENSORED_SURV": CENSORED_SURV,
                           "LIFT_RATIO": LIFT_RATIO}}
