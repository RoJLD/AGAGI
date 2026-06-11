"""
tools/refgame_pop.py — Jeu référentiel de POPULATION par gradient (EDR 072).

EDR 070 : le gradient fait converger un jeu référentiel à 2 agents. La biosphère a le vrai défi :
une POPULATION entière doit partager UNE convention (avec mutation = loterie 25 %, EDR 053). Test :
N agents, chacun locuteur ET auditeur, entraînés par gradient à communiquer avec des partenaires
ALÉATOIRES. Le gradient force-t-il une convention PARTAGÉE par toute la population, fiablement ?
Référents = types d'apex (biosphère). Auto-contenu. Usage : python -m tools.refgame_pop
"""
import numpy as np

REFERENTS = ["Mammouth", "Leurre", "Ours", "Sanglier"]      # référents de la biosphère


def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def _new_agent(M, V, H, rng):
    sc = 0.4
    return {  # locuteur (M->H->V) + auditeur (V->H->M)
        "Ws1": rng.randn(M, H) * sc, "bs1": np.zeros(H),
        "Ws2": rng.randn(H, V) * sc, "bs2": np.zeros(V),
        "Wl1": rng.randn(V, H) * sc, "bl1": np.zeros(H),
        "Wl2": rng.randn(H, M) * sc, "bl2": np.zeros(M),
        "_adam": None,
    }


def _speak(ag, ref):
    hs = np.tanh(ref @ ag["Ws1"] + ag["bs1"])
    slog = hs @ ag["Ws2"] + ag["bs2"]
    return hs, slog, _softmax(slog)


def _listen(ag, msg):
    hl = np.tanh(msg @ ag["Wl1"] + ag["bl1"])
    plog = hl @ ag["Wl2"] + ag["bl2"]
    return hl, plog, _softmax(plog)


def _adam_step(ag, grads, lr, t, b1=0.9, b2=0.999, eps=1e-8):
    if ag["_adam"] is None:
        ag["_adam"] = {}
    for k, g in grads.items():
        if k not in ag["_adam"]:                            # un agent joue locuteur ET auditeur
            ag["_adam"][k] = [np.zeros_like(ag[k]), np.zeros_like(ag[k])]
        m, v = ag["_adam"][k]
        m[:] = b1 * m + (1 - b1) * g
        v[:] = b2 * v + (1 - b2) * g * g
        ag[k] -= lr * (m / (1 - b1 ** t)) / (np.sqrt(v / (1 - b2 ** t)) + eps)


def train_pop(M, V, H, N, seed, steps=4000, lr=0.02):
    rng = np.random.RandomState(seed)
    pop = [_new_agent(M, V, H, rng) for _ in range(N)]
    ref = np.eye(M)
    tgt = np.arange(M)
    for t in range(1, steps + 1):
        si, li = rng.randint(N), rng.randint(N)            # paire ALÉATOIRE (locuteur, auditeur)
        S, L = pop[si], pop[li]
        hs, slog, msoft = _speak(S, ref)
        mhard = np.eye(V)[np.argmax(slog, axis=1)]         # symbole discret (straight-through)
        hl, plog, psoft = _listen(L, mhard)
        # --- backward (auditeur) ---
        dplog = psoft.copy()
        dplog[np.arange(M), tgt] -= 1.0
        dplog /= M
        gL = {"Wl2": hl.T @ dplog, "bl2": dplog.sum(0)}
        dhl = dplog @ L["Wl2"].T
        dzl = dhl * (1 - hl * hl)
        gL["Wl1"] = mhard.T @ dzl
        gL["bl1"] = dzl.sum(0)
        dmsg = dzl @ L["Wl1"].T
        # --- backward (locuteur, straight-through) ---
        dslog = msoft * (dmsg - (dmsg * msoft).sum(1, keepdims=True))
        gS = {"Ws2": hs.T @ dslog, "bs2": dslog.sum(0)}
        dhs = dslog @ S["Ws2"].T
        dzs = dhs * (1 - hs * hs)
        gS["Ws1"] = ref.T @ dzs
        gS["bs1"] = dzs.sum(0)
        _adam_step(L, gL, lr, t)
        _adam_step(S, gS, lr, t)
    # --- eval : decode CROISÉ (auditeur j decode locuteur i) sur toutes les paires ---
    accs = []
    for i in range(N):
        _, slog_i, _ = _speak(pop[i], ref)
        toks = np.argmax(slog_i, axis=1)
        msg = np.eye(V)[toks]
        for j in range(N):
            _, plog_j, _ = _listen(pop[j], msg)
            accs.append(np.mean(np.argmax(plog_j, 1) == tgt))
    return float(np.mean(accs))


def main(seeds=range(8), M=4, V=6, H=16, N=6):
    print(f"JEU REFERENTIEL de POPULATION par gradient : {N} agents, {M} referents, {V} tokens.")
    print(f"  referents = {REFERENTS[:M]} ; decode CROISE (n'importe quel auditeur decode n'importe quel locuteur)")
    accs = []
    for s in seeds:
        a = train_pop(M, V, H, N, s)
        accs.append(a)
        print(f"  seed {s}: decode_croise_population = {a:.2f}")
    rate = np.mean([a > 0.9 for a in accs])
    print("\n=== VERDICT ===")
    print(f"  decode croise moyen = {np.mean(accs):.3f} ; taux convergence(>0.9) = {rate*100:.0f}%")
    print(f"  (repere biosphere sous MUTATION : convention ~25%, loterie -- EDR 053)")
    if np.mean(accs) > 0.9 and rate >= 0.8:
        print("  -> CONVENTION PARTAGEE par toute la population, FIABLEMENT. Le gradient resout la")
        print("     coordination multi-agent du langage -- le mecanisme a cabler dans Biosphere3D.")
    elif np.mean(accs) > 0.7:
        print("  -> convergence partielle de population (gradient aide nettement vs loterie mutation).")
    else:
        print("  -> la coordination de population resiste meme sous gradient (a regler).")


if __name__ == "__main__":
    main()
