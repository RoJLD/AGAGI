"""
src/seed_ai/referential_head.py — Tête référentielle DÉDIÉE pour l'agent (EDR 074).

EDR 073 : le connectome 1-tick est un substrat trop faible pour le langage référentiel (~0.5). EDR
072 : le jeu de population par gradient (MLP avec couche cachée) converge à 100 %. Solution : donner à
l'agent une **tête dédiée** (apex_onehot -> hidden -> token), co-entraînée par le jeu de population,
qui produit le token quand l'agent perçoit un apex. Branchée dans Biosphere3D -> langage FIABLE dans
l'agent vivant (vs 25 % loterie mutation).
"""
import numpy as np


def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def new_head(M=3, V=4, H=12, rng=None):
    """Tête : locuteur (apex_onehot M -> hidden H -> token V) + décodeur d'entraînement (token -> apex)."""
    rng = rng or np.random.RandomState()
    sc = 0.5
    return {"Ws1": rng.randn(M, H) * sc, "bs1": np.zeros(H),
            "Ws2": rng.randn(H, V) * sc, "bs2": np.zeros(V),
            "Wd": rng.randn(V, M) * sc, "M": M, "V": V}


def speak_logits(head, apex_oh):
    h = np.tanh(apex_oh @ head["Ws1"] + head["bs1"])
    return h @ head["Ws2"] + head["bs2"]


def speak_token(head, apex_idx):
    """apex_idx (0..M-1) -> token idx (0..V-1). Le token que l'agent émet pour cet apex."""
    oh = np.zeros((1, head["M"]))
    oh[0, apex_idx] = 1.0
    return int(np.argmax(speak_logits(head, oh)[0]))


def train_population(heads, steps=5000, lr=0.02, seed=0):
    """Co-entraîne une POPULATION de têtes par le jeu référentiel (072) : paires aléatoires, gradient,
    straight-through -> convention PARTAGÉE et fiable (vs loterie mutation). Modifie les têtes en place."""
    rng = np.random.RandomState(seed)
    M, V = heads[0]["M"], heads[0]["V"]
    ref = np.eye(M)
    tgt = np.arange(M)
    for _ in range(steps):
        si, li = rng.randint(len(heads)), rng.randint(len(heads))
        S, L = heads[si], heads[li]
        hs = np.tanh(ref @ S["Ws1"] + S["bs1"])
        slog = hs @ S["Ws2"] + S["bs2"]
        msoft = _softmax(slog)
        mhard = np.eye(V)[np.argmax(slog, axis=1)]
        plog = mhard @ L["Wd"]
        psoft = _softmax(plog)
        dplog = psoft.copy()
        dplog[np.arange(M), tgt] -= 1.0
        dplog /= M
        L["Wd"] -= lr * (mhard.T @ dplog)                  # décodeur (auditeur)
        dmsg = dplog @ L["Wd"].T
        dslog = msoft * (dmsg - (dmsg * msoft).sum(1, keepdims=True))   # straight-through
        dhs = dslog @ S["Ws2"].T
        dzs = dhs * (1 - hs * hs)
        S["Ws2"] -= lr * (hs.T @ dslog)
        S["bs2"] -= lr * dslog.sum(0)
        S["Ws1"] -= lr * (ref.T @ dzs)
        S["bs1"] -= lr * dzs.sum(0)
    return heads


def cross_decode_accuracy(heads):
    """Decode CROISÉ : tout décodeur décode-t-il tout locuteur ? (1.0 = convention partagée parfaite)."""
    M, V = heads[0]["M"], heads[0]["V"]
    ref = np.eye(M)
    tgt = np.arange(M)
    accs = []
    for S in heads:
        toks = np.argmax(speak_logits(S, ref), axis=1)
        msg = np.eye(V)[toks]
        for L in heads:
            accs.append(np.mean(np.argmax(msg @ L["Wd"], 1) == tgt))
    return float(np.mean(accs))
