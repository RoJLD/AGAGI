"""
tools/refgame_bio.py — Jeu référentiel sur le VRAI connectome de la biosphère (EDR 073).

EDR 072 : le jeu référentiel de population converge à 100% (MLP). On le porte sur le CONNECTOME RÉEL
de la biosphère, avec ses positions E/S exactes : apex à l'ENTRÉE 4 (on_apex_type), token aux SORTIES
19:23 (logits[19:23]). Le locuteur = le connectome (1 tick) ; l'auditeur = une tête de décode apprise.
Population, gradient (BPTT à travers le connectome + straight-through). Si ça converge fiablement,
l'architecture RÉELLE de l'agent apprend le langage par gradient -> pièce validée pour le câblage vivant.

Auto-contenu. Usage : python -m tools.refgame_bio
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import Genome

APEX_IN = 4              # on_apex_type : entrée 4 (world_1_stoneage ligne 477)
TOK_LO, TOK_HI = 19, 23  # token : logits[19:23] (world_1_stoneage ligne 969)
APEX_VALUES = [1.0, 0.5, -1.0]   # Mammouth, Ours, Leurre (valeurs réelles, ligne 340)
REFNAMES = ["Mammouth", "Ours", "Leurre"]


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def speak_fwd_bwd(W, I, O, N, apex_scalar, dtok=None):
    """Locuteur = connectome 1 tick. apex_scalar:(B,) -> token_logits:(B,V). Si dtok fourni: BPTT -> dW."""
    B = apex_scalar.shape[0]
    V = TOK_HI - TOK_LO
    dt = _sigmoid(np.clip(np.diag(W), -10, 10))
    Wnd = W.copy()
    np.fill_diagonal(Wnd, 0.0)
    obs = np.zeros((B, I))
    obs[:, APEX_IN] = apex_scalar
    Hc = np.zeros((B, N))
    Hc[:, :I] = obs
    e = Hc @ Wnd
    a = np.tanh(e)
    H = (1.0 - dt) * Hc + dt * a
    out = H[:, N - O:N]                              # bloc de sortie (O,)
    tok_logits = out[:, TOK_LO:TOK_HI]               # (B,V)
    if dtok is None:
        return tok_logits
    dH = np.zeros((B, N))
    dH[:, (N - O) + TOK_LO:(N - O) + TOK_HI] = dtok
    dHc = dH * (1.0 - dt)
    da = dH * dt
    de = da * (1.0 - a * a)
    dW = Hc.T @ de
    np.fill_diagonal(dW, 0.0)
    ddt = np.sum(dH * (a - Hc), axis=0) * dt * (1.0 - dt)
    dW[np.diag_indices(N)] = ddt
    return tok_logits, dW


def train_pop(seeds_pop, I, O, N, M=3, steps=4000, lr=0.01, seed=0):
    rng = np.random.RandomState(seed)
    V = TOK_HI - TOK_LO
    pop = [{"W": rng.randn(N, N) * 0.3, "Wd": rng.randn(V, M) * 0.4, "mW": None} for _ in range(seeds_pop)]
    apex = np.array(APEX_VALUES[:M])
    refs = np.arange(M)
    for t in range(1, steps + 1):
        si, li = rng.randint(seeds_pop), rng.randint(seeds_pop)
        S, L = pop[si], pop[li]
        tok_logits = speak_fwd_bwd(S["W"], I, O, N, apex)
        tok_soft = _softmax(tok_logits)
        tok_hard = np.eye(V)[np.argmax(tok_logits, axis=1)]
        plog = tok_hard @ L["Wd"]
        psoft = _softmax(plog)
        dplog = psoft.copy()
        dplog[np.arange(M), refs] -= 1.0
        dplog /= M
        L["Wd"] -= lr * (tok_hard.T @ dplog)         # tête de décode (auditeur)
        dtok_hard = dplog @ L["Wd"].T
        dtok = tok_soft * (dtok_hard - (dtok_hard * tok_soft).sum(1, keepdims=True))  # straight-through
        _, dW = speak_fwd_bwd(S["W"], I, O, N, apex, dtok=dtok)
        S["W"] -= lr * dW                            # connectome locuteur
    # eval : decode CROISÉ (auditeur j decode locuteur i)
    accs = []
    for i in range(seeds_pop):
        toks = np.argmax(speak_fwd_bwd(pop[i]["W"], I, O, N, apex), axis=1)
        msg = np.eye(V)[toks]
        for j in range(seeds_pop):
            accs.append(np.mean(np.argmax(msg @ pop[j]["Wd"], 1) == refs))
    return float(np.mean(accs))


def main(seeds=range(6), pop=6):
    cfg = WorldConfig()
    I, O = cfg.agent.num_inputs, cfg.agent.num_outputs
    N = max(I + O + 5, 172)
    print(f"JEU REFERENTIEL sur le VRAI connectome (I={I} O={O} N={N}) : apex@in{APEX_IN} -> token@out{TOK_LO}:{TOK_HI}")
    print(f"  referents = {REFNAMES} (valeurs {APEX_VALUES})")
    accs = []
    for s in seeds:
        a = train_pop(pop, I, O, N, seed=s)
        accs.append(a)
        print(f"  seed {s}: decode_croise = {a:.2f}")
    rate = np.mean([a > 0.9 for a in accs])
    print("\n=== VERDICT ===")
    print(f"  decode croise moyen = {np.mean(accs):.3f} ; convergence(>0.9) = {rate*100:.0f}% (biosphere mutation ~25%)")
    if np.mean(accs) > 0.9 and rate >= 0.8:
        print("  -> le VRAI connectome apprend un code referentiel apex PARTAGE et FIABLE par gradient.")
        print("     Architecture reelle validee -> pret pour le cablage dans la boucle vivante (decode head + pairing).")
    else:
        print("  -> convergence partielle sur le vrai connectome (l'entree scalaire unique complique).")


if __name__ == "__main__":
    main()
