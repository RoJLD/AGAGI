"""EDR-178 : robustesse aux régimes de la structure de facteurs du binding in-world.

Rejoue le factoriel 2^4 (compare_factorial, EDR-177) dans 3 régimes et compare les 4 effets
principaux : la structure trouvée par EDR-177 (no_consume dominant, F2/F4 inertes) est-elle
invariante au régime, ou F2 (weightless) émerge-t-il sous survie contrainte / F4
(conditional_credit) sous payoff rare ? Régimes létal/rare = valeurs de DÉPART, calibrées à
l'exécution. Non-biaisé (penalty=0) hérité de compare_factorial.

Usage : python tools/factorial_regime_sweep.py
  (env : FRS_SEEDS, FRS_TICKS, FRS_WARMUP, FRS_AGENTS, FRS_REGIMES=neutralise,letal,rare)

⚠️ PORTAGE (2026-09-15, P2.60). Écrit le 2026-07-15 sur `chantier/factorial-regime-sweep` (tag
`keep/edr-177-178-factorial-regime-sweep`), porté dans HEAD par FUSION 3-voies avec le BANC qu'il pilote
(`compare_factorial` + les trois leviers du monde F1/F2/F4 `torch_throw_no_consume` /
`torch_throw_weightless` / `torch_throw_conditional_credit`, dans `tools/torch_throw_gate_inworld_ab.py`
et `src/worlds/world_1_stoneage.py` -- `git merge-tree` sans conflit, les gardes E14 et les défauts de
seeds de HEAD conservés). Au portage :
  * `_factorial_effects` (couche d'agrégation du plan 2^4) a UNE définition, celle du banc, importée
    ici -- corrigée porte 14 : un pool VIDE rend `nan`, pas `0.0` (le tag fabriquait un effet nul là
    où aucun niveau n'était mesuré) ;
  * `run_sweep` est un ORCHESTRATEUR : il accepte l'INJECTION (`compare_fn`, `effects_fn`) et est
    calibré à dose connue sans simuler (`tests/sandbox/test_edr177_178_calibration.py`), avec une
    garde d'arguments EN TÊTE (E14 rétro-appliquée, même forme que les `compare_*` du banc) ;
  * le verdict de cellule-0 (garde de puissance n >= 12) sort du bloc `__main__` vers une fonction
    PURE, `_cell0_verdict`, pour être calibrable -- et un NUL sous le plancher de puissance y est
    dit NON-CONCLUANT (un nul mesuré à n=4 n'est pas un nul, cf. `peut_conclure` de
    `compute_ab_verdict`).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.torch_throw_gate_inworld_ab import compare_factorial, _factorial_effects  # noqa: E402

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

# Garde-fou power-evaporation (EDR-177 §Confirmation, [[power-evaporation-guardrail]]) : pas de
# verdict POSITIF sous n=12 ; et un NUL sous ce plancher n'est pas un nul mesuré.
_N_MIN_VERDICT = 12
_LABELS = {"GRADIENT_GAGNE": "BINDE", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PLAT"}


def run_sweep(regimes, seeds=(0, 1, 2, 3, 4), ticks=120, warmup=30, n_agents=30,
              compare_fn=None, effects_fn=None):
    """Pour chaque régime nommé (dict de knobs), lance compare_factorial + _factorial_effects.
    Retourne {nom: {"cells": [...], "effects": {...}}}.
    `compare_fn` / `effects_fn` : INJECTION (calibration à dose connue, aucun monde construit) ; par
    défaut le banc EDR-177 (`compare_factorial`) et sa `_factorial_effects`.
    Défaut `seeds` relevé à 5 (2026-09-15) pour la même raison que les `compare_*` de HEAD (P2.49) :
    `compute_ab_verdict` exige `sign_p < 0.1`, donc n >= 5 pour qu'un positif soit seulement POSSIBLE."""
    # GARDE D'ARGUMENTS, EN TÊTE (E14 rétro-appliquée). Un argument degenere est une erreur d'APPEL,
    # pas un fait sur le monde : sans elle, un dict de régimes vide rend {} et un horizon nul rend
    # des cellules vides que l'aval lit comme des MESURES. Posée AVANT tout appel au banc.
    if not regimes or not list(seeds) or int(ticks) <= 0 or int(n_agents) <= 0 or int(warmup) >= int(ticks):
        raise ValueError(
            f"run_sweep : argument degenere (regimes={list(regimes or ())}, seeds={list(seeds)}, ticks={ticks}, "
            f"warmup={warmup}, n_agents={n_agents}) -- aucune mesure possible ; ne pas confondre avec une "
            "mesure nulle OBSERVÉE.")
    compare = compare_fn if compare_fn is not None else compare_factorial
    effects = effects_fn if effects_fn is not None else _factorial_effects
    out = {}
    for name, rk in regimes.items():
        cells = compare(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=n_agents, **rk)
        out[name] = {"cells": cells, "effects": effects(cells)}
    return out


def _regime_main_effects_table(regime_effects):
    """Pivote {nom: effects (de _factorial_effects)} en {facteur: {nom: effet_principal}}."""
    return {f: {name: eff["main"][f] for name, eff in regime_effects.items()} for f in _FACTORS}


def _cell0(cells):
    """La cellule tout-propre (T,T,T,T). Lève si elle manque : une carte sans cellule-0 n'a pas de test
    décisif, et `next()` nu aurait laissé fuir une StopIteration."""
    c0 = next((c for c in cells if c["no_consume"] and c["weightless"]
               and c["dense"] and c["conditional_credit"]), None)
    if c0 is None:
        raise ValueError("factorial_regime_sweep : cellule-0 (tout-propre) ABSENTE de la carte -- pas de test décisif.")
    return c0


def _cell0_verdict(c0, n_seeds):
    """Verdict de la cellule tout-propre sous garde de puissance (PUR). `c0` = cellule de
    `compare_factorial` (porte `verdict` de `compute_ab_verdict`), `n_seeds` = K du dispositif.
    Étiquettes : GRADIENT_GAGNE -> BINDE, HEBBIEN_GAGNE -> SHUFFLE_BINDE_PLUS, NEUTRE -> PLAT ;
    sous n < 12, TOUT verdict est marqué NON-CONCLUANT (un positif comme un nul : cf. `peut_conclure`).
    Lève sur étiquette hors vocabulaire, verdict absent ou n degenere -- jamais « ? »."""
    if int(n_seeds) <= 0:
        raise ValueError(f"_cell0_verdict : n_seeds degenere ({n_seeds}).")
    v = (c0.get("verdict") or {}).get("verdict") if isinstance(c0, dict) else None
    if v not in _LABELS:
        raise ValueError(f"_cell0_verdict : étiquette de verdict inconnue ou absente ({v!r}) -- "
                         f"vocabulaire {sorted(_LABELS)}.")
    powered = int(n_seeds) >= _N_MIN_VERDICT
    label = _LABELS[v]
    if powered:
        conclusion = label
    else:
        conclusion = f"{label} n={int(n_seeds)}<{_N_MIN_VERDICT} NON-CONCLUANT"
    return {"verdict": v, "conclusion": conclusion, "powered": powered, "n_seeds": int(n_seeds),
            "median_diff": c0.get("median_diff"), "sign_p": c0["verdict"].get("sign_p"),
            "median_kills": c0.get("median_kills")}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    seeds = tuple(int(x) for x in os.environ.get("FRS_SEEDS", "0,1,2,3,4").split(","))
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

    print("\nCELLULE-0 (tout-propre) par regime :")
    for n in cols:
        c0 = _cell0(out[n]["cells"])
        v = _cell0_verdict(c0, len(seeds))
        print(f"  {n:12s} diff={c0['median_diff']:+.3f} kills={c0['median_kills']:.0f} "
              f"-> {v['verdict']} ({v['conclusion']}) sign_p={v.get('sign_p')}")
