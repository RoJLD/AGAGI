"""Gate de conditionnement sur action BINAIRE (cran 2, Brique A). Le gate livre (EDR-159/165) biaise une
politique CATEGORIELLE (8 moves) ; l'action "ends" biosphere = throw (logit 8, BINAIRE). Ce harnais teste
en ISOLATION si un readout de H apprend a conditionner throw sur did_craft sous credit episodique, avant
tout cablage biosphere. Monde 2-pas binaire ; ne touche NI backend_torch NI la biosphere.

Usage : python tools/torch_binary_gate_probe.py   (env: TBG_SEEDS, TBG_EPISODES, TBG_AGENTS)
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
from tools.substrate_ab import compute_ab_verdict


def _energy_binary(throw, did_craft, hunger=-0.3):
    """Energie/episode du monde 2-pas binaire. +1 SSI composition (throw ET craft) ; faim sinon
    (throw-sans-craft, craft-sans-throw, abstention) -> l'abstention COUTE, force l'engagement."""
    return 1.0 if (throw and did_craft) else hunger


def _binding_gap(throws, did_crafts):
    """Instrument de binding direct (EDR-126) : P(throw|did_craft) - P(throw|¬did_craft). >0 = throw
    conditionne sur le craft ; ~0 = throw independant du craft (pas de binding)."""
    throws = np.asarray(throws, dtype=np.float32)
    dc = np.asarray(did_crafts, dtype=bool)
    p_given = float(throws[dc].mean()) if dc.any() else 0.0
    p_notgiven = float(throws[~dc].mean()) if (~dc).any() else 0.0
    return p_given - p_notgiven


def run_arm(gate_on, episodes=800, n_agents=64, seed=0, lr=0.05, antisat=6.0, shuffle_label=False):
    """Entraine une tete throw BINAIRE sur le monde 2-pas. gate_on=True : logit_throw = H·w_throw + b
    (conditionne sur H -> peut decoder did_craft) ; gate_on=False : logit_throw = b seul (marginal, pas
    de lecture de H -> ne peut pas conditionner). Credit episodique REINFORCE binaire + anti-saturation
    (penalise P(throw) -> empeche le collapse always-throw). W gele (H detache) : isole la tete throw.
    shuffle_label=True (revue finale C1/I1) : CONTROLE anti-memorisation -- did_craft est permute par une
    permutation FIXE (seedee, constante sur tous les episodes) avant de calculer l'energie ET le
    binding_gap. Le label garde le meme taux de base mais est decorrele du vrai contexte : un gap_ON
    eleve sous ce controle prouverait que le readout memorise n'importe quel label fixe (confond), pas
    qu'il conditionne sur le VRAI craft.
    Renvoie binding_gap (dernier quart) + comp_rate + throw_rate."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
    N, I = pop.N, pop.I
    w_throw = torch.zeros(N, requires_grad=True)
    b_throw = torch.zeros(1, requires_grad=True)
    params = [w_throw, b_throw] if gate_on else [b_throw]
    opt = torch.optim.Adam(params, lr=lr)
    rng = np.random.RandomState(seed + 1)
    obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
    obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
    perm = np.random.RandomState(seed + 7).permutation(n_agents) if shuffle_label else None

    throw_hist, craft_hist = [], []
    for _ in range(episodes):
        pop.H = torch.zeros((n_agents, pop.N))
        with torch.no_grad():
            p1, _ = pop.forward(obs_a)
        move1 = _softmax_np(np.asarray(p1)[:, :_MOVE]).argmax(1)
        did_craft = (move1 == CRAFT)
        if shuffle_label:
            did_craft = did_craft[perm]                        # label fixe mais FAUX (meme perm/episode)
        with torch.no_grad():
            pop.forward(obs_b)                                  # met a jour pop.H (S2)
        H_S2 = pop.H.detach()                                   # W gele : gradient seulement via w_throw
        if gate_on:
            z = H_S2 @ w_throw + b_throw                        # conditionne sur H
        else:
            z = b_throw.expand(n_agents)                       # marginal (aucune lecture de H)
        pthrow = torch.sigmoid(torch.clamp(z, -10.0, 10.0))
        throw = (pthrow.detach() > torch.rand(n_agents)).float()
        energy = np.array([_energy_binary(bool(throw[i]), bool(did_craft[i]))
                           for i in range(n_agents)], dtype=np.float32)
        ret = torch.tensor(energy - energy.mean())             # retour episodique baseline
        logp = throw * torch.log(pthrow + 1e-6) + (1 - throw) * torch.log(1 - pthrow + 1e-6)
        loss = -(ret * logp).mean() + antisat * pthrow.mean() ** 2   # REINFORCE + anti-saturation
        opt.zero_grad()
        loss.backward()
        opt.step()
        throw_hist.append(throw.detach().numpy())
        craft_hist.append(did_craft.copy())

    q = max(1, episodes // 4)
    th = np.concatenate(throw_hist[-q:])
    cr = np.concatenate(craft_hist[-q:])
    return {"gate_on": bool(gate_on), "seed": int(seed),
            "binding_gap": _binding_gap(th, cr),
            "comp_rate": float(np.mean(th * cr)),
            "throw_rate": float(np.mean(th))}


def compare(seeds=(0, 1, 2, 3), episodes=800, n_agents=64):
    """A/B apparie gate-binaire ON vs OFF vs SHUFFLE par seed -> verdict (diff = binding_gap ON - OFF).
    Le VRAI test de binding est diff_vs_shuffle (ON vrai vs ON avec label permute fixe) : si le readout
    memorise n'importe quel label fixe (confond, revue finale C1/I1), gap_ON ~= gap_shuffle et
    diff_vs_shuffle ~= 0 malgre un diff (ON vs OFF) positif."""
    rows = []
    for s in seeds:
        on = run_arm(True, episodes=episodes, n_agents=n_agents, seed=s)
        off = run_arm(False, episodes=episodes, n_agents=n_agents, seed=s)
        shuf = run_arm(True, shuffle_label=True, episodes=episodes, n_agents=n_agents, seed=s)
        rows.append({"seed": s, "on": on["binding_gap"], "off": off["binding_gap"],
                     "shuffle": shuf["binding_gap"], "on_comp": on["comp_rate"],
                     "diff": on["binding_gap"] - off["binding_gap"],
                     "diff_vs_shuffle": on["binding_gap"] - shuf["binding_gap"]})
    verdict_vs_shuffle = compute_ab_verdict([{"diff": r["diff_vs_shuffle"]} for r in rows], band=0.02)
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02),
            "verdict_vs_shuffle": verdict_vs_shuffle}


if __name__ == "__main__":
    seeds = tuple(int(x) for x in os.environ.get("TBG_SEEDS", "0,1,2,3").split(","))
    episodes = int(os.environ.get("TBG_EPISODES", "800"))
    agents = int(os.environ.get("TBG_AGENTS", "64"))
    out = compare(seeds=seeds, episodes=episodes, n_agents=agents)
    for r in out["rows"]:
        print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_OFF={r['off']:+.3f} "
              f"gap_shuffle={r['shuffle']:+.3f} diff={r['diff']:+.3f} "
              f"diff_vs_shuffle={r['diff_vs_shuffle']:+.3f} (comp_ON={r['on_comp']:.3f})")
    print("VERDICT:", out["verdict"])
    print("VERDICT_VS_SHUFFLE:", out["verdict_vs_shuffle"])
    _label = {"GRADIENT_GAGNE": "GATE_BINAIRE_BINDE", "HEBBIEN_GAGNE": "OFF_BINDE_PLUS", "NEUTRE": "NEUTRE"}
    print("INTERPRETATION:", _label.get(out["verdict"]["verdict"], out["verdict"]["verdict"]))
    _vvs = out["verdict_vs_shuffle"]["verdict"]
    if _vvs == "NEUTRE":
        print("CONFOND_MEMORISATION: gap(vrai) ~= gap(shuffle) -> le binding n'est PAS isole du label-fixe")
    elif _vvs == "HEBBIEN_GAGNE":
        print("CONFOND_MEMORISATION: gap(vrai) <= gap(shuffle) -> le label FAUX bind AUTANT OU PLUS "
              "que le vrai contexte -> le binding n'est PAS isole du label-fixe (confond confirme)")
    else:
        print("INTERPRETATION_VS_SHUFFLE: gap(vrai) domine gap(shuffle) -> binding partiellement "
              "isole du label-fixe (residu du confond a verifier)")
