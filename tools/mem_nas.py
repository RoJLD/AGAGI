"""
tools/mem_nas.py — Tâche-mémoire DÉDIÉE pour le NAS (EDR 064).

EDR 062 : le foraging ne sature pas le connectome -> NAS bloqué faute de demande. On sort du foraging
et on crée un BANC COGNITIF PUR : rappel parallèle de K bits après un délai (la mémoire vit dans les
nœuds cachés ; `add_node` en ajoute). Auto-contenu : Genome + recurrent_forward + apply_mutations (ni
DB ni Biosphere). Spéciation par taille (protection, EDR 060) + add_node.

A/B (dims FIXES I=O=8 -> A/B propre sur la croissance) : K=1 (mémoire triviale) vs K=6 (sature les ~3
nœuds cachés initiaux). La demande de mémoire fait-elle ENFIN grandir l'architecture sélectionnée ?

Usage : python -m tools.mem_nas   (rapide, pas de DB)
"""
import copy

import numpy as np

from src.seed_ai.rl_evolution import recurrent_forward
from src.seed_ai.mutation import Genome, apply_mutations, MutationConfig
from src.seed_ai.eval_harness import verdict

I_DIM, O_DIM = 8, 8          # slots fixes (>= K max) -> genomes comparables entre conditions


def fresh_genome(N):
    W = (np.random.randn(N, N) * 0.4).astype(np.float32)
    return Genome(W, I_DIM, O_DIM)


def eval_genome(genome, K, D, trials=24):
    """Rappel parallèle : encode K bits -> délai D -> recall. Accuracy moyenne (chance=0.5)."""
    N = genome.num_nodes
    Hh = np.zeros((1, 5, N), dtype=np.float32)
    Hp = np.zeros((1, N), dtype=np.float32)
    accs = []
    for _ in range(trials):
        bits = np.random.choice([-1.0, 1.0], size=K).astype(np.float32)
        H = np.zeros((1, N), dtype=np.float32)
        obs = np.zeros((1, I_DIM), dtype=np.float32)
        obs[0, :K] = bits                                       # encode
        _, H, _, _, _ = recurrent_forward(genome, obs, H, Hh, Hp)
        for _ in range(D):                                      # délai (entrées nulles)
            _, H, _, _, _ = recurrent_forward(genome, np.zeros((1, I_DIM), dtype=np.float32), H, Hh, Hp)
        go = np.zeros((1, I_DIM), dtype=np.float32)
        go[0, K] = 1.0                                          # signal "recall"
        preds, H, _, _, _ = recurrent_forward(genome, go, H, Hh, Hp)
        recalled = np.sign(preds[0, :K])
        accs.append(float(np.mean(recalled == bits)))
    return float(np.mean(accs))


def _select(pop, scores, n_elite, speciate):
    order = list(np.argsort(scores)[::-1])
    if not speciate:
        return [pop[i] for i in order[:n_elite]]
    seen, reserved = set(), []                                  # niche par taille (protège l'innovation)
    for i in order:
        n = pop[i].num_nodes
        if n not in seen:
            seen.add(n)
            reserved.append(i)
    rest = [i for i in order if i not in set(reserved)]
    keep = (reserved + rest)[:n_elite]
    return [pop[i] for i in keep]


def evolve(K, D, seed, generations=30, pop=24, hidden0=3, speciate=True, add_node_rate=0.5):
    np.random.seed(seed)
    mc = MutationConfig()
    mc.add_node_rate = add_node_rate
    N0 = I_DIM + O_DIM + hidden0
    genomes = [fresh_genome(N0) for _ in range(pop)]
    n_elite = max(2, pop // 4)
    best_acc = 0.0
    for _ in range(generations):
        scores = [eval_genome(g, K, D) for g in genomes]
        best_acc = max(best_acc, max(scores))
        elite = _select(genomes, scores, n_elite, speciate)
        children = []
        while len(children) < pop - len(elite):
            parent = elite[np.random.randint(len(elite))]
            child = apply_mutations(parent, mc)     # clone interne -> renvoie le mutant
            children.append(child)
        genomes = elite + children
    final_nodes = float(np.mean([g.num_nodes for g in genomes]))
    return final_nodes, best_acc


def _stats(vals):
    a = np.array(vals, dtype=float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1)) if len(a) > 1 else 0.0,
            "vals": [float(v) for v in vals], "n": len(a)}


def main(seeds=range(5)):
    seeds = list(seeds)
    print("MEM-NAS (banc cognitif dedie) : K=1 (trivial) vs K=6 (sature la memoire). Speciation ON.")
    hard_n, hard_a, easy_n, easy_a = [], [], [], []
    for s in seeds:
        hn, ha = evolve(K=6, D=3, seed=s)
        en, ea = evolve(K=1, D=3, seed=s)
        hard_n.append(hn); hard_a.append(ha); easy_n.append(en); easy_a.append(ea)
        print(f"  seed {s}: K6 nodes={hn:.1f} acc={ha:.2f} | K1 nodes={en:.1f} acc={ea:.2f}")

    res = {"K6": _stats(hard_n), "K1": _stats(easy_n)}
    v = verdict("K6", "K1", res, t_thresh=2.0)
    print("\n=== VERDICT (croissance d'architecture) ===")
    print(f"  K1 (trivial) : nodes={res['K1']['mean']:.2f}+/-{res['K1']['std']:.2f} | acc={np.mean(easy_a):.2f}")
    print(f"  K6 (memoire) : nodes={res['K6']['mean']:.2f}+/-{res['K6']['std']:.2f} | acc={np.mean(hard_a):.2f}")
    print(f"  {v['summary']}")
    if v["significant"] and v["winner"] == "K6":
        print("  -> la DEMANDE DE MEMOIRE fait grandir l'architecture : le NAS marche sur une tache dediee !")
    elif res["K6"]["mean"] > res["K1"]["mean"] + 0.5:
        print("  -> tendance a la croissance sous demande memoire (a confirmer en puissance).")
    else:
        print("  -> pas de croissance differenciee : meme une tache memoire dediee ne selectionne pas la taille")
        print("     (ou la neuro-evolution n'apprend pas la tache -- voir acc vs 0.5).")


if __name__ == "__main__":
    main()
