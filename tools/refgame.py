"""
tools/refgame.py — Jeu référentiel entraîné par GRADIENT : le langage sous gradient (EDR 070, #4).

EDR 053 : sous MUTATION, la convention référentielle émerge dans ~25 % des runs (loterie). Hypothèse
(journée 067-069) : comme le NAS, c'était un problème de RECHERCHE (mutation), pas fondamental. Test :
un locuteur encode un référent (1-hot) en SYMBOLE discret, un auditeur le décode ; les deux entraînés
ENSEMBLE par gradient. Goulot symbolique discret via straight-through (forward=argmax, backward=softmax).

Question : sous gradient, la convergence vers un code partagé est-elle FIABLE (≫ 25 % des seeds) ?
Auto-contenu (pas de DB). Usage : python -m tools.refgame
"""
import numpy as np


def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def run_refgame(M=8, V=8, H=16, epochs=1500, lr=0.02, seed=0):
    """Entraîne locuteur+auditeur par gradient. -> (accuracy_decode, MI(token;referent) normalisee)."""
    rng = np.random.RandomState(seed)
    sc = 0.4
    P = {  # locuteur (M->H->V) + auditeur (V->H->M)
        "Ws1": rng.randn(M, H) * sc, "bs1": np.zeros(H),
        "Ws2": rng.randn(H, V) * sc, "bs2": np.zeros(V),
        "Wl1": rng.randn(V, H) * sc, "bl1": np.zeros(H),
        "Wl2": rng.randn(H, M) * sc, "bl2": np.zeros(M),
    }
    adam = {k: [np.zeros_like(v), np.zeros_like(v)] for k, v in P.items()}
    b1, b2, eps = 0.9, 0.999, 1e-8
    ref = np.eye(M)
    tgt = np.arange(M)
    for ep in range(1, epochs + 1):
        # --- forward ---
        hs = np.tanh(ref @ P["Ws1"] + P["bs1"])
        slog = hs @ P["Ws2"] + P["bs2"]
        msoft = _softmax(slog)
        mhard = np.eye(V)[np.argmax(slog, axis=1)]          # symbole discret (straight-through)
        hl = np.tanh(mhard @ P["Wl1"] + P["bl1"])
        plog = hl @ P["Wl2"] + P["bl2"]
        psoft = _softmax(plog)
        # --- backward ---
        dplog = psoft.copy()
        dplog[np.arange(M), tgt] -= 1.0
        dplog /= M
        g = {}
        g["Wl2"] = hl.T @ dplog
        g["bl2"] = dplog.sum(0)
        dhl = dplog @ P["Wl2"].T
        dzl = dhl * (1 - hl * hl)
        g["Wl1"] = mhard.T @ dzl
        g["bl1"] = dzl.sum(0)
        dmsg = dzl @ P["Wl1"].T
        dslog = msoft * (dmsg - (dmsg * msoft).sum(1, keepdims=True))   # straight-through (jac softmax)
        g["Ws2"] = hs.T @ dslog
        g["bs2"] = dslog.sum(0)
        dhs = dslog @ P["Ws2"].T
        dzs = dhs * (1 - hs * hs)
        g["Ws1"] = ref.T @ dzs
        g["bs1"] = dzs.sum(0)
        for k in P:
            m, v = adam[k]
            m[:] = b1 * m + (1 - b1) * g[k]
            v[:] = b2 * v + (1 - b2) * g[k] * g[k]
            P[k] -= lr * (m / (1 - b1 ** ep)) / (np.sqrt(v / (1 - b2 ** ep)) + eps)
    # --- eval ---
    hs = np.tanh(ref @ P["Ws1"] + P["bs1"])
    tokens = np.argmax(hs @ P["Ws2"] + P["bs2"], axis=1)
    hl = np.tanh(np.eye(V)[tokens] @ P["Wl1"] + P["bl1"])
    pred = np.argmax(hl @ P["Wl2"] + P["bl2"], axis=1)
    acc = float(np.mean(pred == tgt))
    inj = len(set(tokens.tolist())) / M                     # injectivite du code (1.0 = bijectif)
    return acc, inj


def main(seeds=range(10), M=8, V=8):
    print(f"JEU REFERENTIEL sous GRADIENT : {M} referents, {V} tokens, {len(list(seeds))} seeds.")
    accs, injs = [], []
    for s in seeds:
        a, inj = run_refgame(M=M, V=V, seed=s)
        accs.append(a)
        injs.append(inj)
        print(f"  seed {s}: decode_acc={a:.2f}  code_injectif={inj:.2f}")
    rate = np.mean([a > 0.95 for a in accs])
    print("\n=== VERDICT ===")
    print(f"  decode moyen = {np.mean(accs):.3f} ; taux de convergence (acc>0.95) = {rate*100:.0f}%")
    print(f"  (repere : sous MUTATION, emergence ~25% -- loterie, EDR 053)")
    if rate >= 0.8:
        print("  -> le GRADIENT CRACK le langage : convergence FIABLE vers un code partage (vs loterie mutation).")
        print("     Le mur du langage etait, comme le NAS, un probleme de RECHERCHE -- pas fondamental.")
    elif rate > 0.4:
        print("  -> convergence amelioree mais pas totale (gradient aide, sans garantir).")
    else:
        print("  -> pas de convergence fiable meme sous gradient (le langage resiste plus profondement).")


if __name__ == "__main__":
    main()
