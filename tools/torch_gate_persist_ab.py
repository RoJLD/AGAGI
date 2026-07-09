"""A/B PERSIST vs RESET du gate au rebuild du pop (cran 2, prerequis EDR-163). Le gate porte le binding
means->ends (EDR-158/159) mais est population-partage, PAS dans le genome -> perdu au rebuild sur
mortalite. Ce banc teste si le porter (inherit_gate) maintient le CAPABILITY_PAYS d'EDR-161 a travers
les rebuilds. Reutilise le monde 2-pas craft->USE de compositional_world_probe (EDR-161).

Usage : python tools/torch_gate_persist_ab.py   (env: TGP_SEEDS, TGP_EPISODES, TGP_REBUILD_EVERY, TGP_DEMAND)
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
from src.agents.backend_torch import TorchPopulationModel
from tools.compositional_world_probe import _energy, _softmax_np, CRAFT, USE, _MOVE
from tools.substrate_ab import compute_ab_verdict


def inherit_gate(new_pop, old_pop) -> bool:
    """Porte le gate appris (w_gate/b_gate) de old_pop vers new_pop a travers un rebuild. Le gate est
    population-partage, hors genome -> perdu au rebuild sauf carry-over explicite. No-op (False) si un
    gate est absent ou si les dimensions different. N'affecte PAS W (survit via genome)."""
    if getattr(new_pop, "w_gate", None) is None or getattr(old_pop, "w_gate", None) is None:
        return False
    if new_pop.w_gate.shape != old_pop.w_gate.shape or new_pop.b_gate.shape != old_pop.b_gate.shape:
        return False
    with torch.no_grad():
        new_pop.w_gate.data.copy_(old_pop.w_gate.data)
        new_pop.b_gate.data.copy_(old_pop.b_gate.data)
    return True


def _new_gated_pop(agents, lr):
    """Construit un pop torch gate-ON depuis des agents (W relu de leur genome) + opt Adam."""
    pop = make_population(agents, backend="torch")
    pop.opt = torch.optim.Adam([p for p in [pop.W, pop.w_gate, pop.b_gate] if p is not None], lr=lr)
    pop._gate_runtime = True
    return pop


def run_arm(persist, demand=1.0, episodes=800, rebuild_every=200, n_agents=64,
            seed=0, lr=0.05, antisat=6.0):
    """Pop torch PERSISTANT sur le monde 2-pas craft->USE (EDR-161) avec rebuilds tous les
    `rebuild_every` episodes. Au rebuild : nouveau pop depuis les MEMES agents (W survit via genome) ;
    persist=True -> inherit_gate (le gate survit), persist=False -> gate neuf (bug actuel). Renvoie le
    comp_rate du dernier quart. Isole PERSIST vs RESET (1 variable = le sort du gate au rebuild)."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
             TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.ANTISAT = antisat
    TorchPopulationModel.GATE_TARGET = USE
    try:
        agents = [MambaAgent() for _ in range(n_agents)]
        pop = _new_gated_pop(agents, lr)
        rng = np.random.RandomState(seed + 1)
        I = pop.I
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)

        def _sample(preds):
            p = _softmax_np(np.asarray(preds)[:, :_MOVE])
            return np.array([rng.choice(_MOVE, p=pi) for pi in p])

        comp_hist, n_rebuilds = [], 0
        for ep in range(episodes):
            if ep > 0 and ep % rebuild_every == 0:
                old = pop
                pop = _new_gated_pop(agents, lr)          # W survit (genome) ; gate neuf
                if persist:
                    inherit_gate(pop, old)                # ... sauf carry-over explicite
                n_rebuilds += 1
            pop.H = torch.zeros((n_agents, pop.N))
            preds1, _ = pop.forward(obs_a)
            move1 = _sample(preds1)
            did_x = (move1 == CRAFT)
            act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
            preds2, _ = pop.forward(obs_b)
            move2 = _sample(preds2)
            act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
            energy = np.array([_energy(int(move2[i]), bool(did_x[i]), demand)
                               for i in range(n_agents)], dtype=np.float32)
            pop.learn_episode([obs_a, obs_b], [act1, act2], energy - energy.mean(),
                              gate_last_only=False)
            comp_hist.append((move2 == USE) & did_x)
        q = max(1, episodes // 4)
        comp_rate = float(np.mean(np.concatenate(comp_hist[-q:])))
        return {"persist": bool(persist), "demand": float(demand), "seed": int(seed),
                "comp_rate": comp_rate, "n_rebuilds": n_rebuilds}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
         TorchPopulationModel.GATE_TARGET) = saved


def compare(seeds=(0, 1, 2, 3), demand=1.0, episodes=800, rebuild_every=200, n_agents=64):
    """A/B apparie PERSIST vs RESET par seed -> verdict (diff = comp_rate persist - reset)."""
    rows = []
    for s in seeds:
        p = run_arm(True, demand, episodes, rebuild_every, n_agents, seed=s)
        r = run_arm(False, demand, episodes, rebuild_every, n_agents, seed=s)
        rows.append({"seed": s, "persist": p["comp_rate"], "reset": r["comp_rate"],
                     "diff": p["comp_rate"] - r["comp_rate"], "n_rebuilds": p["n_rebuilds"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TGP_SEEDS", "0,1,2,3").split(","))
    episodes = int(os.environ.get("TGP_EPISODES", "800"))
    rebuild_every = int(os.environ.get("TGP_REBUILD_EVERY", "200"))
    demand = float(os.environ.get("TGP_DEMAND", "1.0"))
    out = compare(seeds=seeds, demand=demand, episodes=episodes, rebuild_every=rebuild_every)
    for r in out["rows"]:
        print(f"seed={r['seed']} persist={r['persist']:.3f} reset={r['reset']:.3f} "
              f"diff={r['diff']:+.3f} (rebuilds={r['n_rebuilds']})")
    print("VERDICT:", out["verdict"])
