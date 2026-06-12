"""
tools/grad_compete.py — Le gradient FORT forge-t-il la compétence que la mutation plafonne ? (EDR 077)

EDR 076 : mutation+extinction MAINTIENT mais ne FORGE pas la compétence (plateau), malgré l'Actor-Critic
one-step. Prescription : gradient FORT (BPTT) à horizon long. On le teste sur banc, sur une compétence
de FORAGING qui demande du crédit MULTI-PAS : naviguer efficacement vers la nourriture sur T pas (manger
le plus possible). Trois moteurs, MÊME architecture (connectome récurrent) :
  - MUTATION   : population, élite + cliquet best-ever (le moteur de la biosphère, EDR 076).
  - COUPÉ      : gradient REINFORCE mais coupé entre pas (~one-step, ne crédite pas à travers le temps).
  - BPTT       : gradient fort à travers tout l'épisode (crédite la navigation entière).
Mesure : nourriture mangée en T pas. BPTT >> mutation valide la prescription d'EDR 076 sur banc.

Auto-contenu. Usage : python -m tools.grad_compete
"""
import copy

import numpy as np

from tools.progress import Progress


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def rollout(W, I, O, N, B, L, T, rng, collect=False, cue=2, min_dist=4):
    """Foraging à MÉMOIRE : la direction de la nourriture n'est visible que `cue` pas après chaque
    apparition, puis CACHÉE (obs=0) ; la nourriture apparaît LOIN (>= min_dist). L'agent doit RETENIR
    la direction (état récurrent) pour l'atteindre -> crédit à travers le temps requis. action 0/1/2."""
    dt = _sigmoid(np.clip(np.diag(W), -10, 10))
    Wnd = W.copy()
    np.fill_diagonal(Wnd, 0.0)
    pos = rng.randint(0, L, B).astype(float)
    food = np.clip(pos + rng.choice([-1, 1], B) * rng.randint(min_dist, L, B), 0, L - 1).astype(float)
    since = np.zeros(B)                       # pas depuis la dernière apparition (fenêtre d'indice)
    H = np.zeros((B, N))
    eaten = np.zeros(B)
    cache = []
    for t in range(T):
        diff = food - pos
        shown = (since < cue).astype(float)   # indice visible seulement les `cue` premiers pas
        obs = np.zeros((B, I))
        obs[:, 0] = np.sign(diff) * shown     # direction (cachée après la fenêtre)
        obs[:, 1] = (np.abs(diff) / L) * shown
        Hc = H.copy()
        Hc[:, :I] = obs
        e = Hc @ Wnd
        a = np.tanh(e)
        H = (1.0 - dt) * Hc + dt * a
        probs = _softmax(H[:, N - O:N])
        u = rng.random(B)
        cum = np.cumsum(probs, axis=1)
        action = (u[:, None] < cum).argmax(axis=1)
        pos = np.clip(pos + (action - 1), 0, L - 1)
        ate = (pos == food).astype(float)
        eaten += ate
        newfood = np.clip(pos + rng.choice([-1, 1], B) * rng.randint(min_dist, L, B), 0, L - 1).astype(float)
        food = np.where(ate > 0, newfood, food)
        since = np.where(ate > 0, 0.0, since + 1.0)       # reset la fenêtre d'indice quand on mange
        if collect:
            cache.append((Hc, e, probs, action, ate))
    return (eaten, cache) if collect else eaten


def train_gradient(through_time, seed, I=2, O=3, hidden=16, L=12, T=40, iters=600, B=64, lr=0.05,
                   gamma=0.9, clip=5.0, label=None):
    rng = np.random.RandomState(seed)
    N = I + O + hidden
    W = rng.randn(N, N) * 0.3
    mW, vW = np.zeros((N, N)), np.zeros((N, N))
    b1, b2, eps = 0.9, 0.999, 1e-8
    prog = Progress(iters, label=label) if label else None
    for it in range(1, iters + 1):
        eaten, cache = rollout(W, I, O, N, B, L, T, rng, collect=True)
        dt = _sigmoid(np.clip(np.diag(W), -10, 10))
        # reward-to-go actualisé
        G = np.zeros(B)
        returns = [None] * T
        for t in reversed(range(T)):
            G = cache[t][4] + gamma * G
            returns[t] = G.copy()
        Wnd = W.copy()
        np.fill_diagonal(Wnd, 0.0)
        dW = np.zeros((N, N))
        dH = np.zeros((B, N))
        for t in reversed(range(T)):
            Hc, e, probs, action, _ = cache[t]
            adv = returns[t] - returns[t].mean()          # baseline (réduction variance)
            onehot = np.zeros((B, O))
            onehot[np.arange(B), action] = 1.0
            dlogits = (probs - onehot) * adv[:, None] / B
            dHo = np.zeros((B, N))
            dHo[:, N - O:N] = dlogits
            dHt = dH + dHo
            a = np.tanh(e)
            dHc = dHt * (1.0 - dt)
            de = (dHt * dt) * (1.0 - a * a)
            dW += Hc.T @ de
            dHc = dHc + de @ Wnd.T
            dH = np.zeros((B, N))
            if through_time:
                dH[:, I:] = dHc[:, I:]                     # BPTT : crédit à travers le temps
            # sinon : dH reste 0 -> gradient coupé entre pas
        np.fill_diagonal(dW, 0.0)
        gnorm = np.linalg.norm(dW)                         # clipping de norme (stabilise le BPTT à travers 40 pas)
        if gnorm > clip:
            dW *= clip / gnorm
        mW = b1 * mW + (1 - b1) * dW
        vW = b2 * vW + (1 - b2) * dW * dW
        W -= lr * (mW / (1 - b1 ** it)) / (np.sqrt(vW / (1 - b2 ** it)) + eps)
        if prog:
            prog.update()
    return float(rollout(W, I, O, N, 512, L, T, np.random.RandomState(seed + 7)).mean())


def train_mutation(seed, I=2, O=3, hidden=16, L=12, T=40, gens=600, pop=64, elite=8, sigma=0.15, label=None):
    """Moteur de la biosphère (EDR 076) : population, élite + cliquet best-ever, mutation gaussienne."""
    rng = np.random.RandomState(seed)
    N = I + O + hidden
    Ws = [rng.randn(N, N) * 0.3 for _ in range(pop)]
    best_W, best_fit = None, -1.0
    prog = Progress(gens, label=label) if label else None
    for g in range(gens):
        fits = np.array([rollout(W, I, O, N, 64, L, T, rng).mean() for W in Ws])
        order = np.argsort(fits)[::-1]
        if fits[order[0]] > best_fit:                     # cliquet best-ever (anti-perte, EDR 076)
            best_fit, best_W = fits[order[0]], Ws[order[0]].copy()
        parents = [Ws[i] for i in order[:elite]] + [best_W]
        Ws = [p.copy() for p in parents[:elite]]          # élite intacte
        while len(Ws) < pop:
            p = parents[rng.randint(len(parents))]
            Ws.append(p + rng.randn(N, N) * sigma)        # enfant muté
        if prog:
            prog.update()
    return float(rollout(best_W, I, O, N, 512, L, T, np.random.RandomState(seed + 7)).mean())


def main(seeds=(0, 1, 2, 3)):
    print("FORAGING COMPETENT (naviguer+manger, T=40, horizon long). Meme connectome, 3 moteurs.")
    print("  (repere hasard ~ ce qu'un agent non-entraine mange)")
    rng = np.random.RandomState(123)
    base = float(rollout(rng.randn(21, 21) * 0.3, 2, 3, 21, 512, 12, 40, rng).mean())
    mut = [train_mutation(s, label=f"MUTATION seed {s+1}/{len(seeds)}") for s in seeds]
    cut = [train_gradient(False, s, label=f"COUPE    seed {s+1}/{len(seeds)}") for s in seeds]
    bptt = [train_gradient(True, s, label=f"BPTT     seed {s+1}/{len(seeds)}") for s in seeds]
    print(f"\n  hasard (non-entraine) : {base:.2f} nourriture / 40 pas")
    print(f"  MUTATION (biosphere)  : {np.mean(mut):.2f} +/- {np.std(mut):.2f}")
    print(f"  COUPE   (~one-step)   : {np.mean(cut):.2f} +/- {np.std(cut):.2f}")
    print(f"  BPTT    (gradient fort): {np.mean(bptt):.2f} +/- {np.std(bptt):.2f}")
    print("\n=== VERDICT ===")
    if np.mean(bptt) > np.mean(mut) * 1.3 and np.mean(bptt) > np.mean(cut) * 1.15:
        print(f"  -> le GRADIENT FORT (BPTT) FORGE la competence ({np.mean(bptt):.1f}) la ou la MUTATION")
        print(f"     plafonne ({np.mean(mut):.1f}) et le gradient coupe peine ({np.mean(cut):.1f}).")
        print("     Prescription d'EDR 076 VALIDEE sur banc : le credit a travers le temps est la cle.")
    elif np.mean(bptt) > np.mean(mut) * 1.15:
        print(f"  -> BPTT ({np.mean(bptt):.1f}) > mutation ({np.mean(mut):.1f}) ; avantage du gradient fort confirme.")
    else:
        print(f"  -> pas de separation nette (BPTT {np.mean(bptt):.1f}, mut {np.mean(mut):.1f}) -- tache trop simple ?")


if __name__ == "__main__":
    main()
