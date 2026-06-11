"""
tools/grad_mem.py — Apprentissage par GRADIENT (BPTT) du connectome récurrent (EDR 067).

EDR 064 : la mutation seule ne sait pas exploiter la capacité (croissance = bloat ; K=6 plafonne à
~0.78). Hypothèse : le GRADIENT (BPTT) débloque. On l'implémente à la main (numpy) sur le banc mémoire
(rappel de K bits), et on teste : (1) le gradient résout-il K=6 bien mieux que la mutation ? (2) la
CAPACITÉ (nœuds cachés) paie-t-elle ENFIN sous gradient ? (la question NAS, EDR 064).

Dynamique (= recurrent_forward) : H = (1-dt)*Hc + dt*tanh(Hc @ Wnd), dt=sigmoid(diag(W)), entrées
clampées (Hc[:, :I]=obs). Auto-contenu (pas de DB). Usage : python -m tools.grad_mem
"""
import numpy as np


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def run_bptt(W, I, O, K, D, bits):
    """Forward déroulé + BPTT. bits:(B,K). -> (loss, dW, accuracy)."""
    N = W.shape[0]
    B = bits.shape[0]
    dt = _sigmoid(np.clip(np.diag(W), -10, 10))      # (N,)
    Wnd = W.copy()
    np.fill_diagonal(Wnd, 0.0)

    seq = [np.zeros((B, I))]
    seq[0][:, :K] = bits                             # encode
    for _ in range(D):
        seq.append(np.zeros((B, I)))                 # délai
    go = np.zeros((B, I))
    go[:, K] = 1.0
    seq.append(go)                                   # recall
    T = len(seq)

    H = np.zeros((B, N))
    cache = []
    for t in range(T):
        Hc = H.copy()
        Hc[:, :I] = seq[t]                           # clamp d'entrée
        a = np.tanh(Hc @ Wnd)
        H = (1.0 - dt) * Hc + dt * a
        cache.append((Hc, a))

    pred = H[:, N - O:N - O + K]                      # (B,K)
    loss = float(np.mean((pred - bits) ** 2))
    acc = float(np.mean(np.sign(pred) == bits))

    dW = np.zeros((N, N))
    ddt_raw = np.zeros(N)
    dH = np.zeros((B, N))
    dH[:, N - O:N - O + K] += 2.0 * (pred - bits) / (B * K)
    for t in reversed(range(T)):
        Hc, a = cache[t]
        dHc = dH * (1.0 - dt)
        da = dH * dt
        ddt_raw += np.sum(dH * (a - Hc), axis=0)     # dL/ddt (avant deriv. sigmoid)
        de = da * (1.0 - a * a)                       # tanh'
        dW += Hc.T @ de                               # e = Hc @ Wnd
        dHc = dHc + de @ Wnd.T
        dH = np.zeros((B, N))
        dH[:, I:] = dHc[:, I:]                         # le clamp coupe le gradient vers les entrées
    np.fill_diagonal(dW, 0.0)                          # Wnd diagonale fixée à 0
    dW[np.diag_indices(N)] = ddt_raw * dt * (1.0 - dt)  # diag(W) -> dt via sigmoid'
    return loss, dW, acc


def train(N, I=8, O=8, K=6, D=3, epochs=700, batch=64, lr=0.02, seed=0):
    np.random.seed(seed)
    W = np.random.randn(N, N) * 0.3
    mW = np.zeros((N, N))
    vW = np.zeros((N, N))
    b1, b2, eps = 0.9, 0.999, 1e-8
    for ep in range(1, epochs + 1):
        bits = np.random.choice([-1.0, 1.0], size=(batch, K)).astype(np.float64)
        _, dW, _ = run_bptt(W, I, O, K, D, bits)
        mW = b1 * mW + (1 - b1) * dW
        vW = b2 * vW + (1 - b2) * dW * dW
        W -= lr * (mW / (1 - b1 ** ep)) / (np.sqrt(vW / (1 - b2 ** ep)) + eps)
    bits = np.random.choice([-1.0, 1.0], size=(512, K)).astype(np.float64)
    _, _, acc = run_bptt(W, I, O, K, D, bits)
    return acc


def main(seeds=(0, 1, 2)):
    print("GRADIENT (BPTT) sur le banc memoire. (mutation : K=6 plafonne a ~0.78, EDR 064)")
    print("\n=== 1. Le gradient resout-il la tache ? (K, N=19 = 3 caches) ===")
    for K in (2, 4, 6):
        accs = [train(N=19, K=K, seed=s) for s in seeds]
        print(f"  K={K} : acc gradient = {np.mean(accs):.3f} +/- {np.std(accs):.3f}")

    print("\n=== 2. La CAPACITE paie-t-elle sous gradient ? (K=8 dur, I=O=12, N croissant) ===")
    for hidden in (1, 8, 16):
        N = 12 + 12 + hidden
        accs = [train(N=N, I=12, O=12, K=8, seed=s) for s in seeds]
        print(f"  hidden={hidden:2d} (N={N}) : acc K=8 = {np.mean(accs):.3f} +/- {np.std(accs):.3f}")

    print("\n=== VERDICT ===")
    g6 = np.mean([train(N=19, K=6, seed=s) for s in seeds])
    print(f"  K=6 : gradient={g6:.3f} vs mutation~0.78 -> {'GRADIENT DEBLOQUE LA TACHE' if g6 > 0.90 else 'pas mieux'}")
    a_lo = np.mean([train(N=25, I=12, O=12, K=8, seed=s) for s in seeds])
    a_hi = np.mean([train(N=40, I=12, O=12, K=8, seed=s) for s in seeds])
    print(f"  K=8 : N=25 {a_lo:.3f} -> N=40 {a_hi:.3f} -> capacite {'PAIE sous gradient' if a_hi > a_lo + 0.03 else 'non-bindante (les sorties stockent deja les bits)'}")
    if g6 > 0.90 and a_hi > a_lo + 0.03:
        print("  -> EDR 064 confirme : la MUTATION etait le goulot ; le gradient debloque tache ET capacite.")


if __name__ == "__main__":
    main()
