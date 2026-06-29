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


def load_champion_genome():
    """Proxy paresseux vers tools.s2_demand.load_champion_genome — patchable par monkeypatch en CI."""
    from tools.s2_demand import load_champion_genome as _fn
    return _fn()


def _make_config(base_metabolism, forage_payoff):
    """WorldConfig au régime voulu (base_metabolism, forage_payoff) ; reste = défauts."""
    from src.environments.config import WorldConfig
    return WorldConfig(base_metabolism=base_metabolism, forage_payoff=forage_payoff)


# Agents du diagnostic. fresh_genome=True -> agents frais ; batch_model_cls=None -> moteur normal (champion).
def _agents():
    from src.agents.baseline_models import RandomActionBatchModel, ReflexBatchModel
    return {
        "champion":      {"batch_model_cls": None,                   "fresh_genome": False},
        "reflex_naive":  {"batch_model_cls": ReflexBatchModel,       "fresh_genome": True},
        "random_action": {"batch_model_cls": RandomActionBatchModel, "fresh_genome": True},
    }


AGENTS = ("champion", "reflex_naive", "random_action")


def run_diagnostic(seed=2026, K=8, num_agents=20, max_ticks=400):
    """Grille 2 régimes × 3 agents sur stoneage -> cells[regime][agent] = dict run_condition."""
    from tools.s2_demand import run_condition
    from src.worlds.world_1_stoneage import Biosphere3D
    champion = load_champion_genome()
    agents = _agents()
    cells = {}
    for regime, (bm, fp) in REGIMES.items():
        cfg = _make_config(bm, fp)
        rc = {}
        for name in AGENTS:
            spec = agents[name]
            genome = None if spec["fresh_genome"] else champion
            rc[name] = run_condition(Biosphere3D, spec["batch_model_cls"], genome, seed,
                                     num_agents=num_agents, max_ticks=max_ticks, n_eras=K, config=cfg)
        cells[regime] = rc
    return cells


_ACTION = {
    "SOUS_PUISSANCE":   "le VOID n'était que du bruit -> lancer le S2 confirmatoire AU DÉFAUT (pré-reg tel quel).",
    "CONFOND_PLANCHER": "effet plancher au régime dur -> lancer le S2 confirmatoire AU SWEET-SPOT (addendum daté à la pré-reg).",
    "N_EXIGE_PAS_REEL": "le monde n'exige PAS l'intelligence même survivable -> finding fort (formaliser via S2 confirmatoire).",
    "AMBIGU":           "inconclusif (aucun régime survivable, ou cas contradictoire) -> re-powerer / élargir les régimes.",
}


def _print_table(report):
    print(f"\n=== S2 — Diagnostic de régime (seed={report['seed']}, commit={report['commit']}, K={report['K']}) ===")
    for regime, r in report["per_regime"].items():
        print(f"  {regime:7s} : survivable={str(r['survivable']):5s} | médiane_champ={r['champ_median']:6.1f} "
              f"| censuré={r['censored_frac']*100:3.0f}% | vs {r['strongest_baseline']:13s} "
              f"p={r['p']:.3f} Cliff δ={r['cliff']:+.2f} bat={r['beats']}")
    print(f"  -> VERDICT : {report['verdict']} (lift sweet/défaut={report['lift']:.2f})")
    print(f"  -> {_ACTION.get(report['verdict'], '')}")
    if report["regime_recommande"]:
        print(f"  -> régime recommandé pour le S2 confirmatoire : {report['regime_recommande']}")


def run_diagnostic_main(seed=2026, K=8, num_agents=20, max_ticks=400, with_db=False):
    """Orchestre le diagnostic, sauve le report (results/s2_regime_diagnostic_<seed>.json), imprime."""
    from src.seed_ai.harness import Harness, _git_short_commit
    with Harness(seed=seed, name="s2_regime_diagnostic", with_db=with_db) as h:
        cells = run_diagnostic(seed=seed, K=K, num_agents=num_agents, max_ticks=max_ticks)
        v = regime_diagnostic_verdict(cells, max_ticks=max_ticks)
        report = {"seed": seed, "commit": _git_short_commit(), "K": K, **v}
        h.save(report)
    _print_table(report)
    return report


if __name__ == "__main__":
    run_diagnostic_main(seed=int(os.getenv("EXPERIMENT_SEED", "2026")))
