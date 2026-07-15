"""EDR-178 : robustesse aux régimes de la structure de facteurs du binding in-world.

Rejoue le factoriel 2^4 (compare_factorial, EDR-177) dans 3 régimes et compare les 4 effets
principaux : la structure trouvée par EDR-177 (no_consume dominant, F2/F4 inertes) est-elle
invariante au régime, ou F2 (weightless) émerge-t-il sous survie contrainte / F4
(conditional_credit) sous payoff rare ? Régimes létal/rare = valeurs de DÉPART, calibrées à
l'exécution. Non-biaisé (penalty=0) hérité de compare_factorial.

Usage : python tools/factorial_regime_sweep.py
  (env : FRS_SEEDS, FRS_TICKS, FRS_WARMUP, FRS_AGENTS, FRS_REGIMES=neutralise,letal,rare)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.torch_throw_gate_inworld_ab import compare_factorial, _factorial_effects

# Régimes : mêmes 16 cellules 2^4, seuls les knobs de régime changent. Valeurs CALIBRÉES (sonde
# survie+kills, 3 tours) : le drain-throw plafonne la survie, donc « létal » = tampon d'énergie
# RÉDUIT (night=True exterminait la cohorte, écarté) ; « rare » = proies rares + fourrage/énergie
# soutenus (sinon famine : la proie est cible ET nourriture, et les throws sans kill drainent).
REGIMES = {
    "neutralise": dict(night=False, energy=250.0, base_metabolism=0.05, forage_payoff=3.0, prey_sparse=15, prey_dense=300),
    "letal":      dict(night=False, energy=150.0, base_metabolism=0.05, forage_payoff=3.0, prey_sparse=15, prey_dense=300),
    "rare":       dict(night=False, energy=800.0, base_metabolism=0.05, forage_payoff=6.0, prey_sparse=3,  prey_dense=6),
}

_FACTORS = ("no_consume", "weightless", "dense", "conditional_credit")


def run_sweep(regimes, seeds=(0, 1, 2, 3), ticks=120, warmup=30, n_agents=30):
    """Pour chaque régime nommé (dict de knobs), lance compare_factorial + _factorial_effects.
    Retourne {nom: {"cells": [...], "effects": {...}}}."""
    out = {}
    for name, rk in regimes.items():
        cells = compare_factorial(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=n_agents, **rk)
        out[name] = {"cells": cells, "effects": _factorial_effects(cells)}
    return out


def _regime_main_effects_table(regime_effects):
    """Pivote {nom: effects (de _factorial_effects)} en {facteur: {nom: effet_principal}}."""
    return {f: {name: eff["main"][f] for name, eff in regime_effects.items()} for f in _FACTORS}


def _cell0(cells):
    """La cellule tout-propre (T,T,T,T)."""
    return next(c for c in cells if c["no_consume"] and c["weightless"]
                and c["dense"] and c["conditional_credit"])


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    seeds = tuple(int(x) for x in os.environ.get("FRS_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("FRS_TICKS", "120"))
    warmup = int(os.environ.get("FRS_WARMUP", "30"))
    agents = int(os.environ.get("FRS_AGENTS", "30"))
    names = os.environ.get("FRS_REGIMES", "neutralise,letal,rare").split(",")
    regimes = {n: REGIMES[n] for n in names if n in REGIMES}

    out = run_sweep(regimes, seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents)
    effects = {n: res["effects"] for n, res in out.items()}
    tbl = _regime_main_effects_table(effects)

    cols = list(regimes)
    print("EFFETS PRINCIPAUX (diff propre - confond) par regime :")
    print(f"  {'facteur':22s} " + " ".join(f"{c:>12s}" for c in cols))
    for f in _FACTORS:
        print(f"  {f:22s} " + " ".join(f"{tbl[f][c]:+12.3f}" for c in cols))

    _lab = {"GRADIENT_GAGNE": "BINDE", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PLAT"}
    print("\nCELLULE-0 (tout-propre) par regime :")
    for n in cols:
        c0 = _cell0(out[n]["cells"])
        v = c0["verdict"]
        pos = v["verdict"] == "GRADIENT_GAGNE"
        if pos and len(seeds) >= 12:
            concl = "BINDE (K>=12)"
        elif pos:
            concl = f"BINDING_APPARENT n={len(seeds)}<12 NON-CONCLUANT"
        else:
            concl = _lab.get(v["verdict"], "?")
        print(f"  {n:12s} diff={c0['median_diff']:+.3f} kills={c0['median_kills']:.0f} "
              f"-> {v['verdict']} ({concl}) sign_p={v.get('sign_p')}")
