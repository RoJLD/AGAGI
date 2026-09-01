"""add_node decale-t-il le bloc d'ENTREE, et un lecteur y survit-il ?"""
import numpy as np
from tools.jobs.run import hold

with hold("kuzu", owner="probe-addnode", ttl_s=1800):
    import tools.evo_cognitive_objective as M
    import src.seed_ai.mutation as MUT
    from src.seed_ai.mutation import apply_mutations, MutationConfig, Genome

    # 1) FREQUENCE : add_node insere-t-il a j < num_inputs, et a i >= j ?
    orig = MUT.add_node
    stat = {"calls": 0, "j_lt_inputs": 0, "i_ge_j": 0}
    def spy(g, cfg):
        W = g.W; nz = np.nonzero(W)
        if len(nz[0]):
            k = np.random.RandomState(0)  # juste pour ne pas consommer le RNG global ici
        stat["calls"] += 1
        before_I = g.num_inputs
        # on re-implemente le tirage pour l'observer, puis on delegue
        nzi, nzj = np.nonzero(g.W)
        if len(nzi) == 0:
            return orig(g, cfg)
        # NOTE : on ne peut pas connaitre le tirage interne sans le refaire ; on inspecte APRES
        n_before = g.num_nodes
        orig(g, cfg)
        return None
    # inspection directe du code plutot que du tirage : on instrumente en rejouant la logique
    def observe(g):
        nzi, nzj = np.nonzero(g.W)
        if len(nzi) == 0: return None
        idx = np.random.randint(len(nzi))
        return int(nzi[idx]), int(nzj[idx])

    np.random.seed(0)
    g = M._fresh_soup(1, M._cfg(), 0.4)[0]
    I0 = g.num_inputs
    n_j_lt_I = n_i_ge_j = 0
    TRIALS = 3000
    for _ in range(TRIALS):
        r = observe(g)
        if r is None: continue
        i, j = r
        if j < I0: n_j_lt_I += 1
        if i >= j: n_i_ge_j += 1
    print(f"  sur {TRIALS} tirages d'arete (i,j) du meme genome :")
    print(f"    j < num_inputs ({I0})  : {100*n_j_lt_I/TRIALS:5.1f} %   -> insertion DANS le bloc d'entree")
    print(f"    i >= j                 : {100*n_i_ge_j/TRIALS:5.1f} %   -> new_W[i,j] cible le MAUVAIS noeud")

    # 2) EFFET : un LECTEUR cable survit-il a des add_node ?
    I, O, N = 59, 108, 172
    SIG = M.SIG_COLS[0]
    def reader():
        W = np.zeros((N, N), dtype=np.float32); np.fill_diagonal(W, 10.0)
        W[SIG, N - O + M.THROW_IDX] = 3.0
        return Genome(W, I, O)
    mc = MutationConfig(); mc.add_node_rate = 1.0; mc.weight_mutate_rate = 0.0
    mc.add_connection_rate = 0.0; mc.prune_rate = 0.0; mc.meso_skip_rate = 0.0; mc.meso_gate_rate = 0.0
    print(f"\n  saillance d'un LECTEUR cable apres k add_node (rien d'autre ne mute) :")
    for k in (0, 1, 3, 10):
        np.random.seed(7)
        g = reader()
        for _ in range(k):
            g = apply_mutations(g, mc)
        sal = M.measure_decision_saliency(g, 500, channel=SIG, out_idx=M.THROW_IDX,
                                          num_agents=8, ticks=30, tasks=(1,))
        print(f"    k={k:>2} add_node : N={g.num_nodes:>3} num_inputs={g.num_inputs:>3} -> saillance={sal:.3f}")
