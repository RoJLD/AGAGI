"""
tools/arm_act_grad.py — Le #8 sur les ACTIVATIONS, évaluées par GRADIENT, sur une tâche DURE (EDR 069).

EDR 066 : sous mutation + tâche facile, tanh est optimal -> le #8 n'a rien à trouver. EDR 067 : le
gradient rend des tâches dures abordables. On donne enfin au #8 une vraie frontière : il propose des
activations, chacune **entraînée par BPTT** sur une mémoire à **LONG DÉLAI** (D grand -> gradient
évanescent, le régime où tanh souffre). Une activation au meilleur flux de gradient peut battre tanh.

Sûreté : sandbox EDR 035 (compile_activation). Dérivée de l'activation = numérique (marche pour tout f).
Usage : python -m tools.arm_act_grad   (LLM local + sandbox ; pas de DB)
"""
import json
import re

import numpy as np

from src.metaprog.llm_proposer_fn import local_llm_fn
from tools.arm_activation import compile_activation
from tools.grad_mem import _sigmoid

I_DIM, O_DIM = 8, 8


def run_bptt_act(W, K, D, bits, act, h=1e-4):
    """BPTT avec activation PLUGGABLE (dérivée numérique). -> (dW, accuracy)."""
    N = W.shape[0]
    B = bits.shape[0]
    I, O = I_DIM, O_DIM
    dt = _sigmoid(np.clip(np.diag(W), -10, 10))
    Wnd = W.copy()
    np.fill_diagonal(Wnd, 0.0)
    seq = [np.zeros((B, I))]
    seq[0][:, :K] = bits
    for _ in range(D):
        seq.append(np.zeros((B, I)))
    go = np.zeros((B, I))
    go[:, K] = 1.0
    seq.append(go)
    T = len(seq)
    H = np.zeros((B, N))
    cache = []
    for t in range(T):
        Hc = H.copy()
        Hc[:, :I] = seq[t]
        e = Hc @ Wnd
        a = act(e)
        H = (1.0 - dt) * Hc + dt * a
        cache.append((Hc, e))
    pred = H[:, N - O:N - O + K]
    acc = float(np.mean(np.sign(pred) == bits))
    dW = np.zeros((N, N))
    ddt_raw = np.zeros(N)
    dH = np.zeros((B, N))
    dH[:, N - O:N - O + K] += 2.0 * (pred - bits) / (B * K)
    for t in reversed(range(T)):
        Hc, e = cache[t]
        a = act(e)
        dHc = dH * (1.0 - dt)
        da = dH * dt
        ddt_raw += np.sum(dH * (a - Hc), axis=0)
        gprime = (act(e + h) - act(e - h)) / (2.0 * h)        # dérivée numérique
        de = da * gprime
        dW += Hc.T @ de
        dHc = dHc + de @ Wnd.T
        dH = np.zeros((B, N))
        dH[:, I:] = dHc[:, I:]
    np.fill_diagonal(dW, 0.0)
    dW[np.diag_indices(N)] = ddt_raw * dt * (1.0 - dt)
    return dW, acc


def train_act(act, K, D, N=19, epochs=600, batch=48, lr=0.02, seed=0):
    np.random.seed(seed)
    W = np.random.randn(N, N) * 0.3
    mW = np.zeros((N, N))
    vW = np.zeros((N, N))
    b1, b2, eps = 0.9, 0.999, 1e-8
    for ep in range(1, epochs + 1):
        bits = np.random.choice([-1.0, 1.0], size=(batch, K)).astype(np.float64)
        dW, _ = run_bptt_act(W, K, D, bits, act)
        mW = b1 * mW + (1 - b1) * dW
        vW = b2 * vW + (1 - b2) * dW * dW
        W -= lr * (mW / (1 - b1 ** ep)) / (np.sqrt(vW / (1 - b2 ** ep)) + eps)
    bits = np.random.choice([-1.0, 1.0], size=(256, K)).astype(np.float64)
    _, acc = run_bptt_act(W, K, D, bits, np.tanh if act is None else act)
    return acc


def build_prompt(context, K, D):
    past = context.get("recent", [])
    lines = [
        f"Reseau RECURRENT entraine par GRADIENT (BPTT) sur une memoire a LONG DELAI (K={K} bits, "
        f"delai={D} ticks). Le gradient traverse ~{D+2} couches -> GRADIENT EVANESCENT : tanh souffre.",
        "Propose UNE activation f(x) (numpy) qui ameliore le FLUX DE GRADIENT sur un long deroule",
        "(ex. moins saturante, pente preservee). Remplace tanh dans H=(1-dt)H+dt*f(exc).",
        "Activations deja essayees (accuracy ; tanh=baseline) :",
    ]
    for p in past:
        lines.append(f"  - {p['name']}: {p['score']}")
    lines += ["Contraintes : numpy/math uniquement, fonction pure f(x)->x.",
              'JSON SEUL : {"name":"...", "code":"import numpy as np\\ndef f(x):\\n    return ..."}']
    return "\n".join(lines)


def main(n_iters=6, seeds=(0, 1), K=6, D=10, llm=None):
    llm = llm or local_llm_fn()
    base = float(np.mean([train_act(np.tanh, K, D, seed=s) for s in seeds]))
    print(f"ARM-ACT-GRAD (#8 + gradient, tache DURE K={K} D={D}) : baseline tanh acc={base:.3f}")
    context = {"recent": [{"name": "tanh", "score": round(base, 3)}]}
    results = [("tanh", base)]
    for i in range(n_iters):
        try:
            resp = llm(build_prompt(context, K, D))
            d = json.loads(re.search(r"\{.*\}", resp, re.DOTALL).group(0))
            name, code = str(d.get("name", f"act{i}")), str(d.get("code", ""))
        except Exception as e:
            print(f"  iter {i}: illisible ({type(e).__name__})")
            continue
        fn, reason = compile_activation(code)
        if fn is None:
            print(f"  '{name}': REJETE ({reason})")
            context["recent"].append({"name": name, "score": f"rejete"})
            continue
        try:
            acc = float(np.mean([train_act(fn, K, D, seed=s) for s in seeds]))
        except Exception as e:
            print(f"  '{name}': crash ({type(e).__name__})")
            continue
        flag = "  <-- BAT tanh" if acc > base + 0.02 else ""
        print(f"  '{name}': acc={acc:.3f}{flag}")
        context["recent"].append({"name": name, "score": round(acc, 3)})
        results.append((name, acc))
    results.sort(key=lambda r: r[1], reverse=True)
    print("\n=== CLASSEMENT (accuracy, tache dure sous gradient) ===")
    for n, a in results:
        print(f"  {n:26s}: {a:.3f}")
    bn, ba = results[0]
    if bn != "tanh" and ba > base + 0.02:
        print(f"  -> le #8 a TROUVE mieux que tanh : '{bn}' (+{ba-base:.3f}) -- une vraie frontiere sous gradient !")
    else:
        print("  -> tanh reste le meilleur meme ici (ou regime trop dur/facile).")


if __name__ == "__main__":
    main()
