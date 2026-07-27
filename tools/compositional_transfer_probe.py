"""Un CURRICULUM de difficulté (facile->plein) bat-il le TABULA-RASA ? (CURR-001, proxy de transfer_ratio)

`tools/curriculum_transfer.py` (Dev #3) mesure ceci IN-WORLD (échelle de mondes) mais tourne la vraie
biosphère (KuzuDB partagée -> collision avec la session // in-world + lourd). Ici : PROXY standalone, même
question, sur l'axe DIFFICULTÉ DE TÂCHE du jeu compositionnel — non-collidant, ma méthode. Complète l'arc de
la loi warm-start/curriculum (montrée sur l'axe SOCIAL par LANG-004) : le curriculum aide-t-il aussi sur la
difficulté ? (prédiction : oui si le curriculum aide à échapper à l'équilibre partiel diagnostiqué LANG-005.)

Dims FIXES (A=4 toujours alloué ; seule la plage de valeurs échantillonnée change) :
- TABULA    : entraîne directement sur la tâche PLEINE (valeurs {0,1,2,3}) pendant E épisodes.
- CURRICULUM : phase 1 sur le sous-monde FACILE (valeurs {0,1,2}) E/2 ép, phase 2 PLEINE E/2 ép -> budget égal.
Mesure within (combos entraînés) + zeroshot (diagonale held-out) ; ratio = curriculum/tabula par seed.

Usage : python tools/compositional_transfer_probe.py  (env: CTP_EPISODES, CTP_SEEDS, CTP_A, CTP_EASY, CTP_V, CTP_AGENTS)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def compute_transfer(rows_tab, rows_cur, chance):
    """Par seed : ratio (curr-chance)/(tab-chance) sur within ET zeroshot. Renvoie médianes + verdict.
    PUR (testable sans torch)."""
    import statistics

    def ratio(cur, tab):
        return (cur - chance) / (tab - chance) if (tab - chance) > 1e-6 else float("nan")

    win_r = [ratio(c["within"], t["within"]) for t, c in zip(rows_tab, rows_cur)]
    zs_r = [ratio(c["zeroshot"], t["zeroshot"]) for t, c in zip(rows_tab, rows_cur)]
    win_r = [r for r in win_r if r == r]
    zs_r = [r for r in zs_r if r == r]
    med_win = statistics.median(win_r) if win_r else float("nan")
    med_zs = statistics.median(zs_r) if zs_r else float("nan")
    # le curriculum TRANSFÈRE si le ratio > 1 (au-dessus de la chance) sur within et/ou zeroshot
    if med_win > 1.08 or med_zs > 1.08:
        verdict = "CURRICULUM_TRANSFERS"
    elif med_win < 0.92 and med_zs < 0.92:
        verdict = "CURRICULUM_HURTS"
    else:
        verdict = "NEUTRAL"
    return {"ratio_within": med_win, "ratio_zeroshot": med_zs, "verdict": verdict}


def main():
    import statistics
    from tools.compositional_language_probe import run_compositional

    E = int(os.environ.get("CTP_EPISODES", "12000"))
    seeds = list(range(int(os.environ.get("CTP_SEEDS", "2"))))
    A = int(os.environ.get("CTP_A", "4"))
    easy = int(os.environ.get("CTP_EASY", "3"))                   # sous-monde facile = valeurs {0..easy-1}
    V = int(os.environ.get("CTP_V", "6"))
    M = int(os.environ.get("CTP_AGENTS", "8"))
    chance = 1.0 / A
    half = E // 2

    def tab(s):
        return run_compositional(episodes=E, n_agents=M, A=A, V=V, seed=s, rotate=False)

    def cur(s):
        return run_compositional(episodes=half, warmstart_easy=half, easy_values=easy,
                                 n_agents=M, A=A, V=V, seed=s, rotate=False)

    rows_tab = [tab(s) for s in seeds]
    rows_cur = [cur(s) for s in seeds]
    tw = statistics.median(r["within"] for r in rows_tab)
    tz = statistics.median(r["zeroshot"] for r in rows_tab)
    cw = statistics.median(r["within"] for r in rows_cur)
    cz = statistics.median(r["zeroshot"] for r in rows_cur)
    res = compute_transfer(rows_tab, rows_cur, chance)

    print(f"A={A} easy={easy} V={V} chance={chance:.2f} E={E} (curr={half}+{half}) M={M} seeds={len(seeds)}")
    print(f"TABULA     within={tw:.3f} zeroshot={tz:.3f}")
    print(f"CURRICULUM within={cw:.3f} zeroshot={cz:.3f}")
    print(f"VERDICT={res['verdict']} : ratio(curr/tab au-dessus chance) within={res['ratio_within']:.2f} "
          f"zeroshot={res['ratio_zeroshot']:.2f}")


if __name__ == "__main__":
    main()
