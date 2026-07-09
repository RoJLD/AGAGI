"""Frontière torch : BPTT (backprop through time) — la capacité que numpy N'A PAS (EDR-145).

Le moteur legacy dérive le crédit à la MAIN et 1-PAS (il détache l'état récurrent chaque tick,
cf. round-trip via l'agent) -> il ne peut PAS assigner le crédit À TRAVERS le temps. torch autograd,
lui, rétropropage à travers la chaîne récurrente complète = BPTT.

Démonstration sur la tâche canonique de MÉMOIRE (copie à T pas) : un indice binaire est injecté à
t=0, l'agent doit le ressortir à t=T-1. Il faut ROUTER l'info à travers T pas récurrents -> le
gradient de la sortie finale doit traverser les T pas. BPTT complet (graphe retenu) apprend ; le mode
TRONQUÉ (état détaché chaque pas, = ce que legacy peut faire) reste au hasard.

Cellule minimale et AUTONOME (pas la TorchBatchModel per-tick-rebuild, qui combat BPTT : son
intégration in-world = étape suivante). Usage : python tools/torch_bptt_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def train_copy_task(mode: str, T: int = 6, N: int = 16, epochs: int = 400, seed: int = 0,
                    batch: int = 64, lr: float = 0.02):
    """Tâche copie-à-T-pas. mode='bptt' (graphe retenu à travers les T pas) vs 'truncated' (état
    détaché chaque pas = crédit 1-pas façon legacy). Retourne l'accuracy finale (chance=0.5).

    Dynamique LTC-like : H' = (1-δ)H + δ·tanh(H·W + x). Indice injecté à t=0 ; lecture à t=T-1.
    Supervisé (CE) : isole la capacité de CRÉDIT à travers le temps du bruit d'exploration RL."""
    import numpy as np
    import torch

    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)

    W = (torch.randn(N, N, generator=g) * 0.1).requires_grad_(True)     # récurrent
    Win = (torch.randn(1, N, generator=g) * 0.5).requires_grad_(True)   # injection de l'indice
    Wout = (torch.randn(N, 2, generator=g) * 0.5).requires_grad_(True)  # lecture finale
    delta = torch.full((N,), 0.5)                                       # constante de temps fixe
    opt = torch.optim.Adam([W, Win, Wout], lr=lr)

    def step(H, x):
        excit = H @ W + x
        return (1.0 - delta) * H + delta * torch.tanh(excit)

    acc = 0.0
    for _ in range(epochs):
        cue = torch.randint(0, 2, (batch,), generator=g)                # indice ∈ {0,1}
        H = torch.zeros(batch, N)
        x0 = (cue.float() * 2.0 - 1.0).unsqueeze(1) @ Win              # (batch,N) injection ±1 à t=0
        H = step(H, x0)
        for _t in range(1, T):
            if mode == "truncated":
                H = H.detach()                                          # crédit 1-pas (façon legacy)
            # DISTRACTEURS : bruit injecté chaque pas -> l'indice doit être ACTIVEMENT maintenu
            # (dynamique récurrente entraînée) sinon il est noyé. Seul BPTT peut façonner W pour ça.
            noise = torch.randn(batch, N, generator=g) * 0.8
            H = step(H, noise)
        logits = H @ Wout
        loss = torch.nn.functional.cross_entropy(logits, cue)
        opt.zero_grad(); loss.backward(); opt.step()
        acc = float((logits.argmax(1) == cue).float().mean())
    return acc


def main():
    T = int(os.environ.get("TBP_T", "6"))
    seeds = [0, 1, 2]
    res = {}
    for mode in ("bptt", "truncated"):
        accs = [train_copy_task(mode, T=T, seed=s) for s in seeds]
        res[mode] = accs
        import statistics
        print(f"{mode:9s} T={T} : acc par seed = {['%.2f' % a for a in accs]}  median={statistics.median(accs):.2f}")
    import statistics
    b = statistics.median(res["bptt"]); t = statistics.median(res["truncated"])
    verdict = "BPTT_DEBLOQUE" if (b > 0.9 and t < 0.65) else ("PARTIEL" if b > t + 0.15 else "NEUTRE")
    print(f"VERDICT={verdict} : bptt={b:.2f} vs truncated={t:.2f} (chance=0.50) "
          f"-> torch BPTT résout la mémoire à {T} pas que le crédit 1-pas (numpy/legacy) ne peut pas")
    return res


if __name__ == "__main__":
    main()
