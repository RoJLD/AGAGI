"""UN add_node detruit-il vraiment un lecteur ? Robustesse + mecanisme."""
import numpy as np
from tools.jobs.run import hold

with hold("kuzu", owner="probe-fragile", ttl_s=1800):
    import tools.evo_cognitive_objective as M
    from src.seed_ai.mutation import add_node, MutationConfig, Genome

    I, O, N = 59, 108, 172
    SIG = M.SIG_COLS[0]
    def reader():
        W = np.zeros((N, N), dtype=np.float32); np.fill_diagonal(W, 10.0)
        W[SIG, N - O + M.THROW_IDX] = 3.0
        return Genome(W, I, O)

    cfg = MutationConfig()
    print("  10 seeds : UN SEUL add_node applique a un lecteur cable (rien d'autre)")
    kept_edge = lost_sal = 0
    for s in range(10):
        np.random.seed(100 + s)
        g = reader().clone()
        add_node(g, cfg)
        Nn, On = g.num_nodes, g.num_outputs
        j_throw = Nn - On + M.THROW_IDX
        edge = float(g.W[SIG, j_throw])
        diag_out = float(g.W[j_throw, j_throw])
        sal = M.measure_decision_saliency(g, 900 + s, channel=SIG, out_idx=M.THROW_IDX,
                                          num_agents=6, ticks=20, tasks=(1,))
        if edge != 0.0: kept_edge += 1
        if sal < 0.5: lost_sal += 1
        if s < 5:
            print(f"    seed {s}: N={Nn} arete[SIG->throw]={edge:+.2f} diag_sortie={diag_out:+.2f} sal={sal:.3f}")
    print(f"    -> arete encore presente : {kept_edge}/10 | saillance PERDUE : {lost_sal}/10")

    # MECANISME : l'insertion decale-t-elle le bloc de SORTIE ?
    np.random.seed(100)
    g = reader().clone()
    before = {c: float(g.W[SIG, N - O + c]) for c in (M.THROW_IDX,)}
    add_node(g, cfg)
    Nn, On = g.num_nodes, g.num_outputs
    print(f"\n  MECANISME : N {N}->{Nn}, bloc de sortie commence a {N-O} -> {Nn-On}")
    row = g.W[SIG]
    nz = np.nonzero(row)[0]
    print(f"    l'arete du signal pointe maintenant vers la colonne {nz.tolist()} "
          f"(attendu {Nn-On+M.THROW_IDX} pour rester 'throw')")
    print(f"    diagonale du noeud INSERE : cherche un noeud a diag 0 dans le chemin")
    zeros = [k for k in range(Nn) if g.W[k, k] == 0.0]
    print(f"    noeuds SANS reflexe (diag=0) : {zeros[:6]}{'...' if len(zeros)>6 else ''} ({len(zeros)} au total)")
