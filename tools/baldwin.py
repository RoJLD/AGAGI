"""
tools/baldwin.py — Gradient DANS l'agent + évolution = effet Baldwin (EDR 068).

EDR 067 : le gradient (BPTT) débloque l'apprentissage (la mutation seule plafonnait). On l'intègre
comme l'apprentissage de l'AGENT (chaque agent apprend par gradient dans sa "vie"), et on combine
avec l'évolution = **Baldwin** : l'évolution sélectionne non l'agent fini, mais l'agent *apprenable*
(init qui atteint une bonne perf en PEU de pas de gradient). Darwinien : les poids appris NE
s'héritent PAS (on fait évoluer l'INIT, évaluée après apprentissage).

Test (vie courte = peu de pas -> l'init compte) : init aléatoire+vie vs Baldwin(init évoluée)+vie vs
mutation pure (EDR 064 ~0.78) vs gradient long (EDR 067 ~1.0). Auto-contenu (pas de DB).

Usage : python -m tools.baldwin
"""
import numpy as np

from tools.grad_mem import run_bptt

I_DIM, O_DIM = 8, 8


def life_train(W, K, D, steps, lr=0.08, batch=32):
    """Une VIE : `steps` pas de gradient (SGD+momentum) depuis W. -> (accuracy_finale, W_appris)."""
    W = W.copy()
    vel = np.zeros_like(W)
    for _ in range(steps):
        bits = np.random.choice([-1.0, 1.0], size=(batch, K)).astype(np.float64)
        _, dW, _ = run_bptt(W, I_DIM, O_DIM, K, D, bits)
        vel = 0.9 * vel - lr * dW
        W += vel
    bits = np.random.choice([-1.0, 1.0], size=(256, K)).astype(np.float64)
    _, _, acc = run_bptt(W, I_DIM, O_DIM, K, D, bits)
    return acc, W


def baldwin_evolve(K, D, life_steps, seed, generations=18, pop=20, N=19):
    """Évolue l'INIT W (Darwinien) ; fitness = perf APRÈS `life_steps` pas de gradient."""
    np.random.seed(seed)
    pop_W = [np.random.randn(N, N) * 0.3 for _ in range(pop)]
    n_elite = max(2, pop // 4)
    best = 0.0
    for _ in range(generations):
        fit = [life_train(W, K, D, life_steps)[0] for W in pop_W]      # apprend, puis évalue
        best = max(best, max(fit))
        order = list(np.argsort(fit)[::-1])
        elite = [pop_W[i] for i in order[:n_elite]]
        children = []
        while len(children) < pop - len(elite):
            parent = elite[np.random.randint(len(elite))]
            children.append(parent + np.random.randn(N, N) * 0.15)     # mutation de l'INIT seulement
        pop_W = elite + children
    # perf finale : meilleure init évoluée, ré-évaluée après une vie
    fit = [life_train(W, K, D, life_steps)[0] for W in pop_W]
    return max(fit)


def main(seeds=(0, 1, 2), K=6, D=3, life_steps=20):
    print(f"BALDWIN (gradient dans l'agent + evolution) : K={K}, vie={life_steps} pas de gradient.")
    rand = np.mean([life_train(np.random.RandomState(s).randn(19, 19) * 0.3, K, D, life_steps)[0] for s in seeds])
    bald = np.mean([baldwin_evolve(K, D, life_steps, s) for s in seeds])
    print(f"  init ALEATOIRE + vie ({life_steps} pas)     : acc = {rand:.3f}")
    print(f"  BALDWIN (init evoluee) + vie ({life_steps} pas): acc = {bald:.3f}")
    print(f"  (reperes : mutation pure ~0.78 [064] ; gradient long ~1.00 [067])")
    print("\n=== VERDICT ===")
    if bald > rand + 0.05:
        print(f"  -> EFFET BALDWIN : l'evolution facon des inits APPRENABLES (+{bald-rand:.3f} vs aleatoire).")
        print("     L'evolution (globale) prepare le terrain que le gradient (local) exploite vite.")
    else:
        print("  -> pas d'avantage Baldwin net a cette echelle (la vie courte suffit peut-etre deja).")


if __name__ == "__main__":
    main()
