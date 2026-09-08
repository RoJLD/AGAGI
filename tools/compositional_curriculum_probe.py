"""Un curriculum DYADE->ROTATION donne-t-il un code compositionnel ET partagé ? (Arc 4, LANG-004)

LANG-003 a révélé deux impasses sur la tâche 2-symboles :
- PAIRES FIGÉES -> code COMPOSITIONNEL (généralise zéro-shot) mais PRIVÉ (cross-partenaire = chance).
- ROTATION d'emblée -> NE CONVERGE PAS (goulot de consensus prohibitif à froid).

Hypothèse (parallèle au warm-start de la rétention, EDR-167/168/170) : le goulot est un DÉMARRAGE À FROID.
Un curriculum — phase 1 en paires figées (warm-start d'un code compositionnel), phase 2 en rotation (le
PARTAGER sans l'effondrer) — donnerait le meilleur des deux : compositionnel ET mutuellement intelligible.

Compare 3 conditions à BUDGET TOTAL APPARIÉ (W+E épisodes) :
- FIXED     : rotate=False, tout en paires figées.
- ROT_SCRATCH : rotate=True, tout en rotation (froid).
- CURRICULUM  : warmstart_fixed=W puis rotation E (dyade -> rotation).

Métriques : within/zeroshot (compositionnalité, cf. LANG-003) + topsim + cross_mi (intelligibilité mutuelle
croisée = partage, cf. LANG-002). Win = CURRICULUM compositionnel (zeroshot>>chance, topsim>0) ET partagé
(cross_mi eleve), là où FIXED est privé (cross_mi~0) et ROT_SCRATCH échoue (within~chance).

Usage : python tools/compositional_curriculum_probe.py  (env: CCP_W, CCP_E, CCP_SEEDS, CCP_A, CCP_V, CCP_AGENTS)
"""
import math
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main():
    import statistics
    from tools.compositional_language_probe import run_compositional
    from tools.experiment_preflight import assert_bar_separates_the_incapable

    W = int(os.environ.get("CCP_W", "4000"))
    E = int(os.environ.get("CCP_E", "4000"))
    seeds = list(range(int(os.environ.get("CCP_SEEDS", "2"))))
    A = int(os.environ.get("CCP_A", "3"))
    V = int(os.environ.get("CCP_V", "6"))
    M = int(os.environ.get("CCP_AGENTS", "8"))
    chance = 1.0 / A

    def _cell(rotate, warmstart, episodes):
        rows = [run_compositional(episodes=episodes, n_agents=M, A=A, V=V, seed=s, rotate=rotate,
                                  warmstart_fixed=warmstart) for s in seeds]
        def med(key):
            vals = [r[key] for r in rows if not (r[key] != r[key])]   # ignore NaN
            return statistics.median(vals) if vals else float("nan")
        out = {k: med(k) for k in ("within", "zeroshot", "topsim", "cross_mi")}
        # ⚠️ Le PLAFOND de l'incapable est un MAX sur les seeds, pas une médiane — et il vient du bras à
        # MESSAGE BROUILLÉ de `run_compositional` (mêmes agents entraînés, canal vide, éval seule).
        out["zeroshot_scrambled_max"] = max(r["zeroshot_scrambled"] for r in rows)
        return out

    conds = {
        "FIXED      ": _cell(False, 0, W + E),        # budget apparié : W+E en paires figées
        "ROT_SCRATCH": _cell(True, 0, W + E),         # W+E en rotation à froid
        "CURRICULUM ": _cell(True, W, E),             # W figées (warm-start) puis E rotation
    }

    print(f"A={A} V={V} chance={chance:.2f} M={M} W={W} E={E} seeds={len(seeds)}")
    for name, c in conds.items():
        print(f"{name} within={c['within']:.3f} zeroshot={c['zeroshot']:.3f} "
              f"topsim={c['topsim']:+.3f} cross_mi={c['cross_mi']:+.3f}")

    cur = conds["CURRICULUM "]
    fix = conds["FIXED      "]
    # ⚠️ P2.15 (2026-09-08) — `chance + 0.12` était posé à l'estime. Le plafond de l'incapable est
    # désormais MESURÉ dans le run : même récepteur ENTRAÎNÉ, même jeu tenu à l'écart, MESSAGE BROUILLÉ.
    # Il n'est pas égal au hasard — mesuré 0.281 contre 0.250 sur un contrôle à A=4 — et c'est
    # précisément ce qu'un seuil ancré sur `chance` ne pouvait pas voir.
    _scr = cur["zeroshot_scrambled_max"]
    # ⚠️ `n_eval` = nombre d'AGENTS, pas combos x agents. C'est DELIBERE et conservateur : l'erreur-type
    # en est SUR-estimee, donc la barre est plus HAUTE, donc plus dure a franchir. L'unite de replication
    # du depot est le seed, pas l'agent (les agents d'un seed partagent entrainement et tirages) ;
    # compter combos x agents comme independants serait le choix OPTIMISTE, celui qui abaisse la barre.
    bar_gen = _scr + math.sqrt(max(_scr * (1.0 - _scr), 0.0) / max(M, 1))
    assert_bar_separates_the_incapable(
        bar_gen, _scr,
        "zero-shot a MESSAGE BROUILLE du bras CURRICULUM : memes agents entraines, meme decodeur, meme "
        "jeu tenu a l'ecart, message remplace par des symboles aleatoires -- plafond d'un recepteur dont "
        "le canal ne transporte rien, MAX sur les seeds du MEME run",
        label="barre de generalisation zero-shot du curriculum")
    comp = cur["zeroshot"] > bar_gen and cur["topsim"] > 0.15        # compositionnel retenu
    shared = (cur["cross_mi"] == cur["cross_mi"]) and cur["cross_mi"] > 0.5   # partagé (non-NaN)
    fixed_private = (fix["cross_mi"] != fix["cross_mi"]) or fix["cross_mi"] < 0.3
    verdict = ("CURRICULUM_YIELDS_SHARED_COMPOSITIONAL" if comp and shared else
               "CURRICULUM_COMPOSITIONAL_NOT_SHARED" if comp else
               "CURRICULUM_FAILS_LIKE_SCRATCH")
    print(f"VERDICT={verdict} : CURRICULUM compositionnel={comp} (zeroshot {cur['zeroshot']:.3f} vs barre MESUREE {bar_gen:.3f} = brouillé {_scr:.3f} + 1 erreur-type) partagé={shared} "
          f"(cross_mi {cur['cross_mi']:+.2f}) ; FIXED privé={fixed_private} (cross_mi {fix['cross_mi']:+.2f})")


if __name__ == "__main__":
    main()
