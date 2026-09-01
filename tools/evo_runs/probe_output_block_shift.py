"""L'insertion d'add_node DECALE-t-elle la semantique du bloc de SORTIE ?

EVO-021 attribuait la destruction d'un lecteur a la diagonale nulle du noeud insere. EVO-022 a REFUTE ce
mecanisme par intervention (heriter la diagonale ne change rien : 13/20 dans les deux bras). Un chiffre
trahit la vraie cause : la destruction est de ~65 %, or le lecteur n'a QU'UNE arete parmi ~173 entrees
non nulles -- add_node ne peut la scinder que dans ~0.6 % des cas.

Hypothese testee ici : add_node n'ajuste jamais num_outputs, donc une insertion DANS le bloc de sortie
decale l'indice de chaque sortie. L'arete cablee survit mais ne pilote plus la meme decision.
"""
import numpy as np
import tools.evo_cognitive_objective as M
from src.seed_ai.mutation import add_node, MutationConfig, Genome

I, O, N = 59, 108, 172
SIG = M.SIG_COLS[0]
J0 = N - O + M.THROW_IDX          # colonne du noeud `throw` AVANT toute insertion


def wired_reader():
    W = np.zeros((N, N), dtype=np.float32)
    np.fill_diagonal(W, 10.0)
    W[SIG, J0] = 3.0
    return Genome(W, I, O)


def main():
    cfg = MutationConfig()
    apres_j0 = intact_recalc = intact_absolu = ligne_glissee = 0
    TRIALS = 200
    for s in range(TRIALS):
        np.random.seed(1000 + s)
        g = wired_reader().clone()
        add_node(g, cfg)
        Nn, On = g.num_nodes, g.num_outputs
        j_recalc = Nn - On + M.THROW_IDX          # ou l'on CROIT que throw se trouve
        nz = np.nonzero(g.W[SIG])[0]
        # ligne VIDE = l'insertion a eu lieu a j <= SIG, la ligne du signal a GLISSE en SIG+1
        if len(nz) == 0:
            ligne_glissee += 1
            apres_j0 += 1
            continue
        col = int(nz[-1])                          # ou l'arete du signal pointe REELLEMENT
        if col == j_recalc:
            intact_recalc += 1
        if col == J0:
            intact_absolu += 1
        if col != j_recalc:
            apres_j0 += 1
    print(f"  {TRIALS} insertions sur un lecteur cable :")
    print(f"    l'arete pointe encore vers l'indice RECALCULE (N-O+8) : {intact_recalc}/{TRIALS} "
          f"({100*intact_recalc/TRIALS:.0f} %)")
    print(f"    l'arete pointe encore vers l'indice d'ORIGINE ({J0})   : {intact_absolu}/{TRIALS} "
          f"({100*intact_absolu/TRIALS:.0f} %)")
    print(f"    DESALIGNEE (l'arete survit mais ne pilote plus throw) : {apres_j0}/{TRIALS} "
          f"({100*apres_j0/TRIALS:.0f} %)")
    print(f"      dont ligne d'ENTREE glissee (insertion a j <= {SIG}) : {ligne_glissee}/{TRIALS} "
          f"({100*ligne_glissee/TRIALS:.0f} %)")
    print("\n  -> si le taux de desalignement approche le taux de destruction mesure en EVO-021 (~65 %),")
    print("     la cause est le DECALAGE DU BLOC DE SORTIE, pas la diagonale du noeud insere.")


if __name__ == "__main__":
    main()
