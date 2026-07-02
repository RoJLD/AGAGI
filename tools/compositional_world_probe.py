"""Le binding LIVRÉ (EDR-158/159) PAIE-t-il quand un monde EXIGE la composition ? (EDR-161)

Fil torch 158/159 : le substrat prod a maintenant une capacité de binding means→ends (gate additif +
`learn_episode` à crédit épisodique). Question de VALEUR (motif S2/EDR-130 appliqué à la composition) :
cette capacité laisse-t-elle un agent EXPLOITER un monde qui demande la composition, là où le substrat
plain (learn TD, sans gate — EDR-148) ne le peut pas ? EDR-130 avait montré que le substrat plain ne
répond PAS à la demande (le stockage n'émerge pas même quand le monde l'exige) ; ici on teste si la
capacité binding renverse ça POUR la composition.

Monde « craft→consomme » (2 pas), standalone (ne touche AUCUN code monde partagé) :
- S1 (obs_craft) : l'agent agit ; did_x = (move == CRAFT).
- S2 (obs_use)   : l'agent CHOISIT — USE (paie SSI craft fait = composition 2-pas) ou FREE (nourriture
  1-pas, sans composition).
- Énergie = d·comp + (1−d)·free, avec comp = +1 si (USE & did_x) sinon −1 si USE sinon 0 ; free = +1 si
  FREE sinon 0. Le LEVIER DE DEMANDE d ∈ [0,1] : d=0 la composition est inutile (FREE suffit),
  d=1 la composition est la SEULE source d'énergie.

On compare, sur un sweep de d, la capacité ON (gate additif task-agnostique + learn_episode) vs OFF
(pop.learn TD 1-pas, sans gate). Métrique = énergie moyenne/épisode (PAYOFF) sur le dernier quart.
Prédiction : l'avantage (ON − OFF) CROÎT avec d (à d élevé seul le bindeur collecte l'énergie).

Usage : python tools/compositional_world_probe.py   (env: CWP_EPISODES, CWP_SEEDS, CWP_DEMANDS)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8
CRAFT, FREE, USE = 0, 2, 4       # indices d'action (< _MOVE)


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _energy(move2, did_x, d):
    """Énergie/épisode. Coût de FAIM constant (l'abstention COÛTE → force l'engagement, pas
    d'échappatoire à 0 comme dans la v1 qui empêchait le binding de bootstrapper). FREE (1-pas) vaut
    (1−d) : abondant à faible demande, nul à demande max. Composer (craft@S1 + USE@S2) vaut (0.5+d) :
    toujours décent, meilleur à demande élevée. USE-sans-craft = coût DOUX (juste la faim, pas de
    pénalité dure) → n'écrase pas l'exploration de USE avant que le craft soit fiable."""
    hunger = -0.3
    if move2 == FREE:
        return hunger + (1.0 - d)              # nourriture libre, sans composition
    if move2 == USE and did_x:
        return hunger + (0.5 + d)              # composition réussie (2-pas)
    return hunger                              # abstention / USE-sans-craft / autre : juste la faim


def run_world(capability: bool, demand: float, episodes: int = 800, n_agents: int = 128,
              seed: int = 0, lr: float = 0.05, antisat: float = 6.0):
    """Entraîne une pop torch sur le monde craft→consomme à un niveau de demande donné.
    capability=True : gate additif task-agnostique + learn_episode (crédit épisodique, EDR-158/159).
    capability=False : pop.learn TD(0) 1-pas sans gate (substrat plain, EDR-148).
    Renvoie payoff (énergie moy/épisode, dernier quart), comp_rate (taux de composition réussie)."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
             TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = bool(capability)
    TorchPopulationModel.ANTISAT = antisat if capability else 0.0
    TorchPopulationModel.GATE_TARGET = USE if capability else None    # le gate route l'action « ends »
    try:
        pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        pop.opt = torch.optim.Adam(
            [p for p in [pop.W, pop.w_gate, pop.b_gate] if p is not None], lr=lr)
        rng = np.random.RandomState(seed + 1)
        I = pop.I
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)     # S1 craft
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)     # S2 use/free (n'encode pas did_x)
        zeros = np.zeros(n_agents, dtype=np.float32)

        def _sample(preds):
            p = _softmax_np(np.asarray(preds)[:, :_MOVE])
            return np.array([rng.choice(_MOVE, p=pi) for pi in p])

        # capacité ON = gate task-agnostique UNIFORME (self-scope depuis H, EDR-159) : actif à tous les
        # forwards. OFF = pas de gate (w_gate None). _gate_runtime = capability suffit.
        pop._gate_runtime = bool(capability)
        e_hist, comp_hist = [], []
        for _ in range(episodes):
            pop.H = torch.zeros((n_agents, pop.N))
            preds1, _ = pop.forward(obs_a)
            move1 = _sample(preds1)
            did_x = (move1 == CRAFT)
            act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
            if not capability:
                pop.learn(zeros, act1)                              # TD : update différé S1
            preds2, _ = pop.forward(obs_b)
            move2 = _sample(preds2)
            act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
            energy = np.array([_energy(int(move2[i]), bool(did_x[i]), demand)
                               for i in range(n_agents)], dtype=np.float32)
            if capability:
                pop.learn_episode([obs_a, obs_b], [act1, act2], energy - energy.mean(),
                                  gate_last_only=False)             # crédit épisodique, task-agnostique
            else:
                pop.learn(energy, act2)                             # TD : update différé S2
            e_hist.append(energy)
            comp_hist.append((move2 == USE) & did_x)

        q = max(1, episodes // 4)
        payoff = float(np.mean(np.concatenate(e_hist[-q:])))
        comp_rate = float(np.mean(np.concatenate(comp_hist[-q:])))
        return {"capability": capability, "demand": demand, "seed": int(seed),
                "payoff": payoff, "comp_rate": comp_rate}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
         TorchPopulationModel.GATE_TARGET) = saved


def main():
    import statistics
    episodes = int(os.environ.get("CWP_EPISODES", "800"))
    seeds = list(range(int(os.environ.get("CWP_SEEDS", "3"))))
    demands = [float(x) for x in os.environ.get("CWP_DEMANDS", "0.0,0.5,1.0").split(",")]
    adv = {}
    for d in demands:
        on = [run_world(True, d, episodes=episodes, seed=s) for s in seeds]
        off = [run_world(False, d, episodes=episodes, seed=s) for s in seeds]
        p_on = statistics.median(r["payoff"] for r in on)
        p_off = statistics.median(r["payoff"] for r in off)
        c_on = statistics.median(r["comp_rate"] for r in on)
        c_off = statistics.median(r["comp_rate"] for r in off)
        adv[d] = p_on - p_off
        print(f"demand={d:.2f} : payoff ON={p_on:+.3f} OFF={p_off:+.3f} adv={p_on-p_off:+.3f} | "
              f"comp_rate ON={c_on:.2f} OFF={c_off:.2f}")
    hi, lo = max(demands), min(demands)
    scales = adv[hi] > adv[lo] + 0.05 and adv[hi] > 0.05
    verdict = "CAPABILITY_PAYS_UNDER_COMPOSITION_DEMAND" if scales else "CAPABILITY_NO_PAYOFF"
    print(f"VERDICT={verdict} : adv(d={hi})={adv[hi]:+.3f} vs adv(d={lo})={adv[lo]:+.3f} -> "
          f"l'avantage de la capacité {'CROÎT' if scales else 'ne croît PAS'} avec la demande")


if __name__ == "__main__":
    main()
