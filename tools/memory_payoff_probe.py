"""La MÉMOIRE paie-t-elle ? (4ᵉ modalité de l'instrument within-subject, MEM-001)

L'audit mémoire du projet ([[memory-architecture-audit]]) : la mémoire PEUT payer en isolation (BPTT) mais NE
PAIE PAS in-world car les tâches n'EXIGENT pas de rappel. On teste ça causalement avec l'instrument
within-subject ([[within-subject-demand-marker]]).

BPTT est numpy-impossible ; on contourne comme l'archi réelle (état H_prev porté + readout dessus) : la MÉMOIRE
est un SUBSTRAT FIXE (intégrateur à fuite qui retient les obs passées), seul le READOUT feedforward s'apprend
(softmax GD). Tâche de rappel différé : un indice (cue) apparaît, puis on sonde l'agent après un délai.
- MEMORY-DEMANDING : l'indice est CACHÉ au moment de la sonde → répondre EXIGE de l'avoir mémorisé.
- MEMORYLESS (trivial) : l'indice est VISIBLE à la sonde → répondre ne demande pas de mémoire.

Ablation within-subject = décorréler la mémoire portée (l'intégrateur d'un indice ALÉATOIRE). Si le succès
s'effondre → la mémoire est causalement porteuse. Corroborant : poids du readout sur l'entrée mémoire.

Usage : python tools/memory_payoff_probe.py   (env: MEM_SEEDS, MEM_K, MEM_DELAY, MEM_LAMBDA)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _memory(cue, demanding, delay, lam, K):
    """Mémoire = intégrateur à fuite FIXE (m ← λ·m + obs) sur le PASSÉ SEUL (ticks 0..delay-1, hors tick de
    sonde). DEMANDING : l'indice n'est vu qu'au tick 0 → m = λ^(delay-1)·onehot(cue) (retient la direction).
    MEMORYLESS : l'indice n'apparaît qu'à la SONDE (jamais dans le passé) → m = 0 (aucune info dans la mémoire)."""
    m = np.zeros(K)
    for t in range(delay):                         # passé seulement (le tick de sonde est traité séparément)
        obs = np.zeros(K)
        if demanding and t == 0:                   # demanding : indice au tick 0 puis caché
            obs[cue] = 1.0
        m = lam * m + obs
    return m


def _obs_at_probe(cue, demanding, K):
    """Observation courante à la sonde : indice CACHÉ (demanding → 0, il faut la mémoire) ou VISIBLE
    (memoryless → onehot, l'obs courante suffit et la mémoire ne porte rien)."""
    o = np.zeros(K)
    if not demanding:
        o[cue] = 1.0
    return o


def _feat(obs_cur, m):
    return np.concatenate([obs_cur, m])            # [observation courante ⊕ mémoire portée]


def _fit_readout(demanding, delay, lam, K, lr=0.5, epochs=600, decay=1e-3):
    """Readout softmax (feedforward) ajusté à prédire l'indice depuis [obs courante ⊕ mémoire]. Weight-decay :
    les poids inutiles retombent à 0 (le readout ne pèse la mémoire que si elle est nécessaire)."""
    F = np.array([_feat(_obs_at_probe(c, demanding, K), _memory(c, demanding, delay, lam, K)) for c in range(K)])
    targets = np.arange(K)
    onehot = np.eye(K)[targets]
    W = np.zeros((K, 2 * K))
    for _ in range(epochs):
        Z = F @ W.T
        Z -= Z.max(axis=1, keepdims=True)
        P = np.exp(Z)
        P /= P.sum(axis=1, keepdims=True)
        W -= lr * ((P - onehot).T @ F / len(F) + decay * W)
    return W


def _accuracy(W, demanding, delay, lam, K, mem_mode, seed, n=2000):
    """Précision de rappel. mem_mode : 'true' (mémoire du vrai indice) / 'random' (ablation : mémoire d'un
    indice ALÉATOIRE, décorrélée)."""
    rng = np.random.RandomState(seed + 700)
    ok = []
    for _ in range(n):
        c = rng.randint(K)
        m_cue = c if mem_mode == "true" else rng.randint(K)
        f = _feat(_obs_at_probe(c, demanding, K), _memory(m_cue, demanding, delay, lam, K))
        ok.append(1.0 if int(np.argmax(W @ f)) == c else 0.0)
    return float(np.mean(ok))


def run(K, delay, lam, seed):
    out = {}
    for demanding, name in ((True, "MEMORY-DEMAND"), (False, "MEMORYLESS")):
        W = _fit_readout(demanding, delay, lam, K)
        acc_t = _accuracy(W, demanding, delay, lam, K, "true", seed)
        acc_a = _accuracy(W, demanding, delay, lam, K, "random", seed)
        mem_w = float(np.mean(np.abs(W[:, K:])))    # poids du readout sur l'entrée mémoire
        out[name] = {"acc_true": acc_t, "acc_ablated": acc_a, "mem_w": mem_w}
    return out


def main():
    import statistics
    seeds = list(range(int(os.environ.get("MEM_SEEDS", "8"))))
    K = int(os.environ.get("MEM_K", "6"))
    delay = int(os.environ.get("MEM_DELAY", "5"))
    lam = float(os.environ.get("MEM_LAMBDA", "0.85"))
    chance = 1.0 / K
    runs = [run(K, delay, lam, s) for s in seeds]

    print(f"K={K} delay={delay} λ={lam} chance={chance:.2f} seeds={len(seeds)} (rappel différé)")
    print(f"{'monde':16s} {'mém.vraie':>9s} {'mém.ablée':>9s} {'poids_mém':>9s} | {'PAIE(×)':>8s}")
    summ = {}
    for name in ("MEMORY-DEMAND", "MEMORYLESS"):
        at = statistics.median(r[name]["acc_true"] for r in runs)
        aa = statistics.median(r[name]["acc_ablated"] for r in runs)
        mw = statistics.median(r[name]["mem_w"] for r in runs)
        pays = at / max(aa, 1e-9)
        summ[name] = (pays, mw)
        print(f"{name:16s} {at:9.2f} {aa:9.2f} {mw:9.3f} | {pays:7.1f}x")

    pays_dem, mw_dem = summ["MEMORY-DEMAND"]
    pays_mless, mw_mless = summ["MEMORYLESS"]
    correct = pays_dem > 1.5 and pays_mless < 1.3 and mw_dem > 0.3 and mw_mless < 0.15
    verdict = ("MEMORY_PAYS_IFF_TASK_DEMANDS_DELAYED_RECALL" if correct else "MEMORY_PAYOFF_UNCLEAR")
    print(f"VERDICT={verdict} : ablation mémoire → demand {pays_dem:.1f}x (PAIE) / memoryless {pays_mless:.1f}x "
          f"(ne paie pas) ; poids_mém demand {mw_dem:.2f} vs memoryless {mw_mless:.2f} (mémoire lue SSI elle "
          f"paie) → la mémoire paie causalement SSI la tâche exige un rappel différé (valide l'audit : "
          f"in-world elle ne paie pas car les tâches n'exigent pas de rappel)")


if __name__ == "__main__":
    main()
