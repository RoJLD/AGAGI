"""Gate binaire, test HELD-OUT sans confond (cran 2, Brique B1). EDR-169 a montre que le harnais binaire
a obs FIXES confond binding et memorisation. Ici : obs VARIABLES par episode + S1 stochastique + did_craft
encode dans obs_b[:,0] (simule le spear-en-inventaire) + HELD-OUT (readout gele, obs fraiches). Le vrai
verdict = gap_heldout(ON) vs gap_heldout(SHUFFLE label de recompense). Ne touche NI backend_torch NI la
biosphere. Reutilise le monde/energie de torch_binary_gate_probe (DRY).

Usage : python tools/torch_binary_gate_heldout_probe.py   (env: TBH_SEEDS, TBH_TRAIN, TBH_TEST, TBH_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import torch

from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from tools.compositional_world_probe import _softmax_np, CRAFT, _MOVE
from tools.torch_binary_gate_probe import _energy_binary, _binding_gap
from tools.substrate_ab import compute_ab_verdict


def run_arm(shuffle_reward=False, train_ep=1200, test_ep=100, n_agents=128, seed=0,
            lr=0.05, antisat=6.0, signal_amp=3.0):
    """Monde 2-pas a obs VARIABLES. S1 stochastique -> did_craft ; obs_b[:,0]=did*signal_amp (contexte
    dans l'etat). TRAIN : readout w_throw/b_throw entraine par REINFORCE binaire + anti-sat ; le label de
    RECOMPENSE est le vrai did_craft (ON) ou une PERMUTATION FIXE (shuffle_reward -> decorrele du contexte).
    HELD-OUT : readout gele, obs FRAICHES, binding_gap mesure sur le VRAI did_craft. W gele (H detache).
    ON -> la recompense suit le contexte -> gap eleve ; SHUFFLE -> gap ~0 (rien a apprendre de generalisant)."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
    N, I = pop.N, pop.I
    w_throw = torch.zeros(N, requires_grad=True)
    b_throw = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w_throw, b_throw], lr=lr)
    rng = np.random.RandomState(seed + 1)
    perm = np.random.RandomState(seed + 7).permutation(n_agents)   # permutation FIXE du label de recompense

    def _episode(update):
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        pop.H = torch.zeros((n_agents, pop.N))
        with torch.no_grad():
            p1, _ = pop.forward(obs_a)
        probs = _softmax_np(np.asarray(p1)[:, :_MOVE])
        move1 = np.array([rng.choice(_MOVE, p=pi) for pi in probs])   # S1 STOCHASTIQUE
        did_craft = (move1 == CRAFT)
        obs_b[:, 0] = did_craft.astype(np.float32) * signal_amp        # contexte dans l'obs
        with torch.no_grad():
            pop.forward(obs_b)
        H_S2 = pop.H.detach()
        z = H_S2 @ w_throw + b_throw
        pthrow = torch.sigmoid(torch.clamp(z, -10.0, 10.0))
        throw = (pthrow.detach() > torch.rand(n_agents)).float()
        reward_label = did_craft[perm] if shuffle_reward else did_craft   # SHUFFLE = recompense decorrelee
        energy = np.array([_energy_binary(bool(throw[i]), bool(reward_label[i]))
                           for i in range(n_agents)], dtype=np.float32)
        if update:
            ret = torch.tensor(energy - energy.mean())
            logp = throw * torch.log(pthrow + 1e-6) + (1 - throw) * torch.log(1 - pthrow + 1e-6)
            loss = -(ret * logp).mean() + antisat * pthrow.mean() ** 2
            opt.zero_grad()
            loss.backward()
            opt.step()
        return throw.detach().numpy(), did_craft            # gap TOUJOURS sur le VRAI did_craft

    for _ in range(train_ep):
        _episode(update=True)
    th, cr = [], []
    for _ in range(test_ep):                                # HELD-OUT : readout gele, obs fraiches
        t, d = _episode(update=False)
        th.append(t)
        cr.append(d)
    th = np.concatenate(th)
    cr = np.concatenate(cr)
    return {"shuffle_reward": bool(shuffle_reward), "seed": int(seed),
            "binding_gap_heldout": _binding_gap(th, cr),
            "comp_rate_heldout": float(np.mean(th * cr)),
            "throw_rate_heldout": float(np.mean(th))}
