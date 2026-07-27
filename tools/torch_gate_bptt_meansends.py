"""Gate + BPTT combinés sur means→ends IN-SUBSTRAT (EDR-147) — le build coordonné annoncé en EDR-146.

Question : le fil compositional // a montré qu'un GATE (readout de H_S2 -> biais sur le logit Y,
REINFORCE) + ANTI-SATURATION de la marginale P(Y) craque le binding (EDR-129/136-compo) MAIS sur un
substrat TRONQUÉ (leur forward détache H). Mon EDR-146 a montré que BPTT SEUL (crédit à travers le
temps, numpy-impossible) NE craque PAS le binding. Reste la conjonction : **BPTT apporte-t-il quelque
chose AU gate** ? BPTT façonne par gradient la mémoire S1 qui alimente le gate ; le gate route le
conditionnement. Design 2×2 propre, MÊME substrat torch, tout égal par ailleurs :

    {no-gate, gate} × {truncated (H détaché S1->S2), bptt (graphe récurrent retenu)}

Point clé du contraste : en `truncated`, H_S2 = step(obs_b, H_S1.detach()) — la VALEUR de H_S2 contient
toujours did_x (propagé en forward), seul le GRADIENT vers S1 est coupé. Le gate lit la valeur -> peut
conditionner (réplique 136). BPTT n'ajoute que la mise en forme par gradient de la mémoire S1. Donc :
  - gate × truncated  ~=  réplique EDR-136 (doit binder)
  - gate × bptt       =   la cellule NOUVELLE (BPTT aide-t-il le gate ?)
  - no-gate × {t,b}   =   réplique EDR-146 (ne binde pas)

Gate = biais additif sur le SEUL logit Y (via one-hot -> pas d'in-place sur le graphe). Anti-saturation
(EDR-136) = pénalité homéostatique antisat·mean(P(Y))² qui empêche l'effondrement always-Y (préserve le
gradient différentiel). Métrique de binding (EDR-128) : binding_gap = P(Y|X) − P(Y|¬X).

Usage : python tools/torch_gate_bptt_meansends.py   (env: TGB_EPOCHS, TGB_SEEDS, TGB_ANTISAT)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_cell(mode: str, use_gate: bool, epochs: int = 1000, n_agents: int = 128, seed: int = 0,
             target_x: int = 3, target_y: int = 5, lr: float = 0.05, antisat: float = 6.0):
    """Entraîne une cellule du 2×2 (mode ∈ {'bptt','truncated'}, use_gate ∈ {True,False}).

    Boucle manuelle sur pop._step (graphe retenu) pour insérer le gate DANS le graphe autograd :
    S1 -> échantillonne move1 (probs détachées) ; S2 -> logits_Y += gate_bias(H_S2) ; échantillonne
    move2 ; REINFORCE sur les 2 pas (retour épisodique + baseline) + anti-saturation. En `truncated`
    on détache H avant S2 (le crédit final ne remonte PAS la récurrence). Retourne binding_gap etc."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel

    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)
    agents = [MambaAgent() for _ in range(n_agents)]
    pop = TorchPopulationModel(agents, lr=lr)
    I, N, O = pop.I, pop.N, pop.O
    truncate = (mode == "truncated")

    # Gate : readout linéaire de H_S2 (N,) -> biais scalaire sur le logit Y (EDR-129-compo).
    w_gate = torch.zeros(N, requires_grad=True)
    b_gate = torch.zeros(1, requires_grad=True)
    params = [pop.W] + ([w_gate, b_gate] if use_gate else [])
    opt = torch.optim.Adam(params, lr=lr)

    obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)      # S1 (motif fixe)
    obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)      # S2 (n'encode pas did_x)
    obs_a_t = torch.tensor(obs_a)
    obs_b_t = torch.tensor(obs_b)
    idx = torch.arange(n_agents)
    onehot_y = torch.zeros(_MOVE)
    onehot_y[target_y] = 1.0

    hit_end = p_x = gap = 0.0
    for _ in range(epochs):
        H = torch.zeros((n_agents, N))
        # --- S1 : émettre X (graphe retenu) ---
        H = pop._step(obs_a_t, H)
        out1 = H[:, N - O:N]
        logits1 = out1[:, :_MOVE]
        move1 = np.array([rng.choice(_MOVE, p=p) for p in _softmax_np(logits1.detach().numpy())])
        did_x = (move1 == target_x)

        # --- S2 : émettre Y, gaté sur H_S2 ---
        if truncate:
            H = H.detach()                                        # coupe le crédit S2->S1
        H = pop._step(obs_b_t, H)
        out2 = H[:, N - O:N]
        base_logits2 = out2[:, :_MOVE]                           # politique de BASE (pré-gate)
        logits2 = base_logits2
        if use_gate:
            gate_bias = H @ w_gate + b_gate                       # (B,) readout de H_S2
            logits2 = logits2 + gate_bias.unsqueeze(1) * onehot_y  # biais sur le SEUL logit Y (one-hot)
        move2 = np.array([rng.choice(_MOVE, p=p) for p in _softmax_np(logits2.detach().numpy())])
        correct_y = (move2 == target_y)

        reward = np.where(correct_y & did_x, 1.0, -1.0).astype(np.float32)
        adv = torch.tensor(reward - reward.mean())               # baseline (variance REINFORCE)

        logp1 = torch.log_softmax(logits1, dim=1)[idx, torch.tensor(move1)]
        logp2 = torch.log_softmax(logits2, dim=1)[idx, torch.tensor(move2)]
        loss = -(adv * (logp1 + logp2)).mean()                   # REINFORCE, retour épisodique 2-pas
        if use_gate and antisat > 0:
            # anti-saturation de la politique de BASE (EDR-136) : garde la marginale Y de la BASE loin
            # de 1 (préserve le gradient différentiel) -> le gate soulève Y CONDITIONNELLEMENT, pas la base.
            base_p_y = torch.softmax(base_logits2, dim=1)[:, target_y].mean()
            loss = loss + antisat * base_p_y ** 2

        opt.zero_grad()
        loss.backward()
        opt.step()

        hit_end = float(np.mean(correct_y & did_x))
        p_x = float(np.mean(did_x))
        pyx = float(np.mean(correct_y[did_x])) if did_x.any() else 0.0
        pynx = float(np.mean(correct_y[~did_x])) if (~did_x).any() else 0.0
        gap = pyx - pynx
    return {"mode": mode, "gate": use_gate, "seed": int(seed),
            "hit_end": hit_end, "p_x": p_x, "binding_gap": gap}


def main():
    import statistics
    epochs = int(os.environ.get("TGB_EPOCHS", "1000"))
    seeds = list(range(int(os.environ.get("TGB_SEEDS", "3"))))
    antisat = float(os.environ.get("TGB_ANTISAT", "6.0"))
    cells = [("truncated", False), ("bptt", False), ("truncated", True), ("bptt", True)]
    out = {}
    for mode, gate in cells:
        rows = [run_cell(mode, gate, epochs=epochs, seed=s, antisat=antisat) for s in seeds]
        key = f"{'gate' if gate else 'nogate'}+{mode}"
        out[key] = rows
        med_gap = statistics.median(r["binding_gap"] for r in rows)
        med_hit = statistics.median(r["hit_end"] for r in rows)
        print(f"{key:16s} : binding_gap median={med_gap:+.3f} hit_end median={med_hit:.3f}  "
              f"per-seed gap={['%+.2f' % r['binding_gap'] for r in rows]}")

    g_bptt = statistics.median(r["binding_gap"] for r in out["gate+bptt"])
    g_trunc = statistics.median(r["binding_gap"] for r in out["gate+truncated"])
    n_bptt = statistics.median(r["binding_gap"] for r in out["nogate+bptt"])
    # Le gate craque-t-il (vs no-gate) ? BPTT ajoute-t-il, est-il neutre, ou DÉGRADE-t-il le gate ?
    gate_binds = g_trunc > 0.25 or g_bptt > 0.25
    if not gate_binds:
        bptt_effect = "GATE_DOES_NOT_BIND"
    elif g_bptt > g_trunc + 0.15:
        bptt_effect = "GATE_BINDS_BPTT_ADDS"
    elif g_bptt < g_trunc - 0.15:                    # BPTT casse le conditionnement que le gate établit
        bptt_effect = "GATE_BINDS_BPTT_DEGRADES"
    else:
        bptt_effect = "GATE_BINDS_BPTT_NEUTRAL"
    effect_txt = {"GATE_BINDS_BPTT_ADDS": "AJOUTE au", "GATE_BINDS_BPTT_DEGRADES": "DÉGRADE le",
                  "GATE_BINDS_BPTT_NEUTRAL": "neutre au", "GATE_DOES_NOT_BIND": "n/a"}[bptt_effect]
    print(f"VERDICT={bptt_effect} : gate+bptt={g_bptt:+.3f} gate+trunc={g_trunc:+.3f} "
          f"nogate+bptt={n_bptt:+.3f} -> gate {'CRAQUE' if gate_binds else 'ne craque pas'} "
          f"le binding ; BPTT {effect_txt} gate")
    return out


if __name__ == "__main__":
    main()
