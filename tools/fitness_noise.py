"""tools/fitness_noise.py — Le plateau de compétence (076) vient-il du BRUIT du signal de fitness ? (EDR 078)

EDR 077 : la mutation forge bien quand le signal est bon ; la biosphère evalue un genome sur 1 ere
(fitness ultra-bruitee ~ eval_B=1). On fait varier eval_B (nb d'episodes d'evaluation) et on mesure la
competence forgee. Si elle MONTE avec la proprete du signal -> le plateau est un probleme de MESURE,
pas de moteur. Usage : HEADLESS=1 python -m tools.fitness_noise
"""
import numpy as np
import tools.grad_compete as gc


def main(evals=(1, 2, 4, 8, 16, 64), seeds=range(3), gens=300):
    print(f"BRUIT DU SIGNAL DE FITNESS : competence forgee par la mutation selon eval_B (nb d'episodes).")
    print(f"  eval_B=1 ~ biosphere (1 ere bruitee) ; eval_B grand ~ signal propre. {len(seeds)} seeds, {gens} gens.")
    rows = []
    for eb in evals:
        comp = [gc.train_mutation(s, gens=gens, eval_B=eb, label=f"eval_B={eb:2d} seed {s+1}/{len(list(seeds))}")
                for s in seeds]
        rows.append((eb, float(np.mean(comp)), float(np.std(comp))))
    print("\n=== competence forgee vs proprete du signal ===")
    for eb, m, s in rows:
        bar = "#" * int(m * 3)
        print(f"  eval_B={eb:2d} : {m:5.2f} +/- {s:4.2f}  {bar}")
    lo, hi = rows[0][1], rows[-1][1]
    print("\n=== VERDICT ===")
    if hi > lo * 1.3:
        print(f"  -> la competence MONTE avec la proprete du signal ({lo:.1f} a eval_B=1 -> {hi:.1f} a eval_B={rows[-1][0]}).")
        print(f"     Le plateau de 076 est un probleme de MESURE (fitness bruitee), pas de moteur.")
        print(f"     Levier biosphere : EVALUER ROBUSTEMENT (plusieurs eres / episodes par genome).")
    else:
        print(f"  -> pas d'effet net du bruit ({lo:.1f} -> {hi:.1f}) : le plateau a une autre cause.")


if __name__ == "__main__":
    main()
