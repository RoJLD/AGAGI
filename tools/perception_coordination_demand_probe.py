"""SP-2 — MESURE de l'arête « coordination demande perception » sur le jeu référentiel de Lewis.

Ablation d'ENTRÉE within-subject : à l'éval, on DÉRANGE le one-hot cible du sender (derange_rows,
in-distribution). Deux conditions : COORD (le receiver ne lit que le signal) -> l'ablation effondre ;
NO-COORD (le receiver a une vue directe BRUITÉE de la cible -> métrique vivante) -> l'ablation est inerte
(contrôle de demande = specificity_control). `functional_aliasing = "n/a"` : une ablation d'entrée n'écrit
rien dans le substrat, aucune fuite à garder (cf. CALIB-ALIAS).

Le nom `run_*probe` trippe le cliquet -> calibré (sender oracle/aléatoire) dans test_instrument_calibration.
Pur torch CPU, aucun bail. Usage : python tools/perception_coordination_demand_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.demand_marker import ablation_verdict
from tools.s2_demand_ablation import derange_rows


def _onehot(idx, size, I, n_agents):
    m = np.zeros((n_agents, I), dtype=np.float32)
    m[np.arange(n_agents), idx % size] = 1.0
    return m


def _noisy_onehot(targets, K, I, n_agents, flip_p, rng):
    """Vue directe BRUITÉE de la cible : avec proba flip_p, one-hot sur un référent ALÉATOIRE (garde la
    métrique NO-COORD vivante, plafonnée à ~1-flip_p)."""
    shown = np.where(rng.random(n_agents) < flip_p, rng.randint(0, K, size=n_agents), targets)
    return _onehot(shown, K, I, n_agents)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _signal_from(s_in, sender, sender_mode, V, rng, n_agents):
    """Signal émis à partir de ce que le sender PERÇOIT (s_in, éventuellement dérangé). oracle/random =
    contrôles de calibration ; learned = sender torch."""
    if sender_mode == "oracle":
        return (np.asarray(s_in).argmax(axis=1) % V)          # émet l'index perçu
    if sender_mode == "random":
        return rng.randint(0, V, size=n_agents)               # décorrélé de la perception
    import torch
    sender.H = torch.zeros((n_agents, sender.N))
    preds_s, _ = sender.forward(s_in)
    return _sample(preds_s, V, rng, n_agents)


def _full_params(pop):
    """P2.27 — l'optimiseur doit couvrir le substrat COMPLET. `[pop.W]` seul laissait `U/V/W_bl`
    GELÉS à leur init : le terme bilinéaire n'aurait jamais appris, et la sonde aurait rendu un nul
    qui ne mesure que l'initialisation. Sans BILINEAR ils valent `None` et la liste se réduit à
    `[pop.W]` — bit-identique au comportement d'avant."""
    return [pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None]


def _train_and_eval(seed, no_coord, episodes, n_agents, K, V, lr, flip_p, sender_mode,
                    eval_batches=40, bilinear=False):
    """Entraîne (learned) puis évalue perception INTACTE vs DÉRANGÉE. Renvoie (acc_intact, acc_ablated)."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    # P2.27 — le substrat est ÉPINGLÉ, pas hérité de l'ambiant : `TorchPopulationModel.BILINEAR` est
    # un attribut de CLASSE lu par `__init__` (`backend_torch.py:111`) et `_step` (`:128`). Non posé,
    # une autre sonde du même processus pouvait faire mesurer un AUTRE substrat à celle-ci, sans trace.
    # ⚠️ Défaut `False` (substrat `plain`) parce que **cette sonde a GRAVÉ l'arête
    # `language→perception`** : changer le défaut invaliderait silencieusement des chiffres publiés.
    # Posé AVANT `make_population` — `U/V/W_bl` ne sont créés qu'à la CONSTRUCTION.
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.BILINEAR = bool(bilinear)
    try:
        sender = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        receiver = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = sender.I
        rng = np.random.RandomState(seed + 1)
        learned = sender_mode == "learned"
        if learned:
            sender.opt = torch.optim.Adam(_full_params(sender), lr=lr)
        receiver.opt = torch.optim.Adam(_full_params(receiver), lr=lr)

        for _ in range(episodes):
            targets = rng.randint(0, K, size=n_agents)
            s_in = _onehot(targets, K, I, n_agents)
            signal = _signal_from(s_in, sender, sender_mode, V, rng, n_agents)
            recv_in = (_noisy_onehot(targets, K, I, n_agents, flip_p, rng) if no_coord
                       else _onehot(signal, V, I, n_agents))
            receiver.H = torch.zeros((n_agents, receiver.N))
            preds_r, _ = receiver.forward(recv_in)
            guess = _sample(preds_r, K, rng, n_agents)
            adv = (guess == targets).astype(np.float32)
            adv = adv - adv.mean()
            if learned:
                sender.learn_episode([s_in], [[{"move": int(x)} for x in signal]], adv, gate_last_only=False)
            receiver.learn_episode([recv_in], [[{"move": int(x)} for x in guess]], adv, gate_last_only=False)

        def _eval(ablate):
            hits = []
            for _ in range(eval_batches):
                targets = rng.randint(0, K, size=n_agents)
                s_in = _onehot(targets, K, I, n_agents)
                if ablate:
                    s_in = derange_rows(s_in, rng)             # ABLATION de la perception du sender
                signal = _signal_from(s_in, sender, sender_mode, V, rng, n_agents)
                recv_in = (_noisy_onehot(targets, K, I, n_agents, flip_p, rng) if no_coord
                           else _onehot(signal, V, I, n_agents))
                receiver.H = torch.zeros((n_agents, receiver.N))
                pr, _ = receiver.forward(recv_in)
                guess = np.asarray(pr)[:, :K].argmax(axis=1)
                hits.append((guess == targets).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval(False), _eval(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR) = saved


def run_perception_coordination_demand_probe(seeds, episodes=1000, n_agents=32, K=6, V=8, lr=0.05,
                                             flip_p=0.3, sender_mode="learned", bilinear=False):
    """Mesure « coordination demande perception ». Par seed : COORD et NO-COORD, chacun éval intact/ablé.
    COORD -> ablation_verdict (attendu X_DEMANDED) ; NO-COORD -> inerte (specificity_control).

    `bilinear` (défaut `False`, cf. `_train_and_eval`) : le substrat mesuré est ÉPINGLÉ et RENDU
    LISIBLE dans `substrate` — sans quoi le résultat n'est pas identifiable a posteriori (P2.27)."""
    ci, ca, ni, na = [], [], [], []
    for s in seeds:
        c_i, c_a = _train_and_eval(s, False, episodes, n_agents, K, V, lr, flip_p, sender_mode,
                                   bilinear=bilinear)
        n_i, n_a = _train_and_eval(s, True, episodes, n_agents, K, V, lr, flip_p, sender_mode,
                                   bilinear=bilinear)
        ci.append(c_i); ca.append(c_a); ni.append(n_i); na.append(n_a)

    floor = 1.0 / K
    coord = ablation_verdict(ci, ca, intervention_verified=True, floor=floor, ceiling=1.0)
    nocoord = ablation_verdict(ni, na, intervention_verified=True, floor=floor, ceiling=1.0)
    nocoord_med = float(np.median(ni))
    nocoord_alive = floor + 0.05 < nocoord_med < 0.9              # VIVANT (ni plancher ni plafond)
    specificity = "pass" if (nocoord["verdict"] == "X_DECOY" and nocoord_alive) else "fail"
    return {"coord": coord, "nocoord": nocoord, "nocoord_alive": nocoord_alive,
            "specificity_control": specificity, "functional_aliasing": "n/a", "n": len(seeds),
            "substrate": {"BILINEAR": bool(bilinear), "CONDITION_GATE": False},   # P2.27
            "coord_intact": ci, "coord_ablated": ca, "nocoord_intact": ni, "nocoord_ablated": na}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("SP2_SEEDS", "12"))))
    ep = int(os.environ.get("SP2_EPISODES", "1000"))
    na = int(os.environ.get("SP2_AGENTS", "32"))
    r = run_perception_coordination_demand_probe(seeds, episodes=ep, n_agents=na)
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("coord", "nocoord", "specificity_control", "nocoord_alive",
                               "functional_aliasing", "n")}, ensure_ascii=False, indent=2))
