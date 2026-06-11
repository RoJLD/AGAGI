"""
tools/grad_forage.py — Gradient (BPTT) en RL : 1er pas vers le gradient dans l'agent vivant (EDR 071).

EDR 067-070 : le gradient débloque tout, mais en SUPERVISÉ (banc mémoire). L'agent vivant est RL
(récompense, actions). On valide ici le pont : **REINFORCE à travers le temps (BPTT)** sur une tâche
foraging-MÉMOIRE — l'agent voit un indice (gauche/droite) au pas 0, puis caché ; il doit le RETENIR
(état récurrent) et naviguer vers le bon bout. C'est ce que l'Actor-Critic one-step (EDR 020) ne peut
pas faire (créditer une décision mémoire prise 8 pas plus tôt).

Compare : BPTT (gradient à travers tout l'épisode) vs ONE-STEP (gradient coupé à chaque pas). La
mémoire-RL n'est apprenable QUE par BPTT. Auto-contenu. Usage : python -m tools.grad_forage
"""
import numpy as np


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def episode(W, I, O, N, B, K, L, through_time, rng):
    """Déroule B épisodes batchés ; renvoie dW (REINFORCE) et le taux de succès."""
    dt = _sigmoid(np.clip(np.diag(W), -10, 10))
    Wnd = W.copy()
    np.fill_diagonal(Wnd, 0.0)
    cue = rng.choice([-1.0, 1.0], size=B)                 # bon bout (gauche/droite), montré au pas 0
    pos = np.zeros(B)
    H = np.zeros((B, N))
    cache = []
    for t in range(K):
        obs = np.zeros((B, I))
        obs[:, 0] = cue if t == 0 else 0.0                # indice TRANSITOIRE (pas 0 seulement)
        obs[:, 1] = pos / L
        Hc = H.copy()
        Hc[:, :I] = obs
        e = Hc @ Wnd
        a = np.tanh(e)
        H = (1.0 - dt) * Hc + dt * a
        logits = H[:, N - O:N]                            # 2 logits d'action (lus sur les sorties)
        probs = _softmax(logits)
        act = (rng.random(B) < probs[:, 1]).astype(int)   # 0 -> gauche, 1 -> droite
        pos = np.clip(pos + (2 * act - 1), -L, L)
        cache.append((Hc, e, probs, act))
    reward = cue * pos / L                                # +1 si au bon bout, -1 au mauvais
    success = float(np.mean(np.sign(pos) == cue))
    adv = reward - reward.mean()                          # baseline (réduction de variance)

    dW = np.zeros((N, N))
    dH = np.zeros((B, N))
    for t in reversed(range(K)):
        Hc, e, probs, act = cache[t]
        onehot = np.zeros((B, O))
        onehot[np.arange(B), act] = 1.0
        dlogits = (probs - onehot) * adv[:, None] / B     # grad REINFORCE de -logprob*adv
        dHo = np.zeros((B, N))
        dHo[:, N - O:N] = dlogits
        dHt = dH + dHo
        a = np.tanh(e)
        dHc = dHt * (1.0 - dt)
        da = dHt * dt
        de = da * (1.0 - a * a)
        dW += Hc.T @ de
        dHc = dHc + de @ Wnd.T
        if through_time:
            dH = np.zeros((B, N))
            dH[:, I:] = dHc[:, I:]                         # BPTT : le gradient remonte dans le temps
        else:
            dH = np.zeros((B, N))                          # ONE-STEP : gradient coupe entre pas
    return dW, success


def train(through_time, seed, I=2, O=2, hidden=14, K=8, L=5, episodes=1500, B=64, lr=0.05):
    rng = np.random.RandomState(seed)
    N = I + O + hidden
    W = rng.randn(N, N) * 0.3
    mW = np.zeros((N, N))
    vW = np.zeros((N, N))
    b1, b2, eps = 0.9, 0.999, 1e-8
    succ = 0.0
    for ep in range(1, episodes + 1):
        dW, s = episode(W, I, O, N, B, K, L, through_time, rng)
        succ = 0.98 * succ + 0.02 * s if ep > 1 else s
        mW = b1 * mW + (1 - b1) * dW
        vW = b2 * vW + (1 - b2) * dW * dW
        W -= lr * (mW / (1 - b1 ** ep)) / (np.sqrt(vW / (1 - b2 ** ep)) + eps)
    # eval
    rng2 = np.random.RandomState(seed + 999)
    _, s = episode(W, I, O, N, 512, K, L, True, rng2)
    return s


def main(seeds=(0, 1, 2, 3)):
    print("FORAGING-MEMOIRE en RL : indice transitoire (pas 0) -> retenir -> naviguer. (hasard=0.5)")
    bptt = [train(True, s) for s in seeds]
    one = [train(False, s) for s in seeds]
    print(f"  BPTT (gradient a travers le temps) : succes = {np.mean(bptt):.3f} +/- {np.std(bptt):.3f}")
    print(f"  ONE-STEP (gradient coupe)          : succes = {np.mean(one):.3f} +/- {np.std(one):.3f}")
    print("\n=== VERDICT ===")
    if np.mean(bptt) > 0.85 and np.mean(bptt) > np.mean(one) + 0.15:
        print(f"  -> le BPTT-RL APPREND la memoire-foraging ({np.mean(bptt):.2f}) la ou le one-step rame ({np.mean(one):.2f}).")
        print("     Le gradient a travers le temps marche en RL : pont banc->biosphere VALIDE.")
    elif np.mean(bptt) > 0.85:
        print(f"  -> BPTT-RL apprend ({np.mean(bptt):.2f}) ; le one-step aussi ({np.mean(one):.2f}) -- tache peu memoire.")
    else:
        print(f"  -> BPTT-RL n'apprend pas nettement ({np.mean(bptt):.2f}) -- a deboguer/regler.")


if __name__ == "__main__":
    main()
