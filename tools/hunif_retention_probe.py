"""Le crédit épisodique RACHÈTE-t-il la RÉTENTION du craft (EDR-127) ? — 2e proxy du pari H-unif (EDR-162).

EDR-127 : le craft est ATTEINT mais NON RETENU (l'agent ne re-crafte pas en cohorte fixe) → verrou =
rétention, pas substrat/sélection. Le pari H-unif ([[torch-inworld-integration-plan]]) : rétention,
binding (161) et spécialisation partagent le MÊME verrou de crédit conditionnel. EDR-161 a montré que le
crédit épisodique PAIE sous demande de composition ; ici on teste l'axe RÉTENTION, distinct :

Mécanisme : une action CRAFT coûte −c IMMÉDIATEMENT (S1) et n'est payée (+r) qu'au CONSUME DIFFÉRÉ (S2,
SSI craft fait). Le TD 1-pas voit le craft comme une perte immédiate → l'abandonne (décroissance =
rétention échoue). Le crédit épisodique voit le retour NET (r−c>0) → le retient. Nouvelle mesure vs 161
= TRAJECTOIRE (craft_rate début vs fin) + sweep du COÛT c (rétention plus dure quand c monte).

Compare capacité ON (gate additif task-agnostique + `learn_episode`, EDR-159) vs OFF (`learn` TD 1-pas,
EDR-148). STANDALONE (ne touche AUCUN code monde partagé).

Usage : python tools/hunif_retention_probe.py   (env: CRP_EPISODES, CRP_SEEDS, CRP_COSTS, CRP_R)
(Renommé de craft_retention_probe pour éviter la collision de chemin avec le banc craft in-world de main.)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8
CRAFT, CONSUME = 0, 4       # indices d'action (< _MOVE)


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_retention(capability: bool, cost: float, r: float = 1.0, episodes: int = 800,
                  n_agents: int = 128, seed: int = 0, lr: float = 0.05, antisat: float = 6.0,
                  warmstart_episodes: int = 0):
    """Entraîne une pop torch sur le jeu craft(coûteux, différé)→consomme. capability=True : gate +
    learn_episode (crédit épisodique). False : learn TD 1-pas. `warmstart_episodes` : phase préalable à
    coût 0 (bâtit le bassin haut-craft, EDR-167 test d'hystérésis) AVANT la phase mesurée au coût `cost`.
    Renvoie craft_rate EARLY/LATE (rétention), comp_rate LATE, payoff LATE."""
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
    TorchPopulationModel.GATE_TARGET = CONSUME if capability else None
    try:
        pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        pop.opt = torch.optim.Adam(
            [p for p in [pop.W, pop.w_gate, pop.b_gate] if p is not None], lr=lr)
        rng = np.random.RandomState(seed + 1)
        I = pop.I
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)     # S1 (craft)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)     # S2 (consume)

        def _sample(preds):
            p = _softmax_np(np.asarray(preds)[:, :_MOVE])
            return np.array([rng.choice(_MOVE, p=pi) for pi in p])

        pop._gate_runtime = bool(capability)                         # gate uniforme (self-scope, EDR-159)
        craft_hist, comp_hist, e_hist = [], [], []

        def _episode(ep_cost, record):
            pop.H = torch.zeros((n_agents, pop.N))
            preds1, _ = pop.forward(obs_a)
            move1 = _sample(preds1)
            crafted = (move1 == CRAFT)
            act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
            r1 = np.where(crafted, -ep_cost, 0.0).astype(np.float32)  # COÛT immédiat du craft (S1)
            if not capability:
                pop.learn(r1, act1)                                  # TD : le coût du craft est vu à S1
            preds2, _ = pop.forward(obs_b)
            move2 = _sample(preds2)
            act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
            consumed = (move2 == CONSUME) & crafted
            r2 = np.where(consumed, r, 0.0).astype(np.float32)        # bénéfice DIFFÉRÉ (S2, SSI craft)
            energy = r1 + r2
            if capability:
                pop.learn_episode([obs_a, obs_b], [act1, act2], energy - energy.mean(),
                                  gate_last_only=False)
            else:
                pop.learn(r2, act2)
            if record:
                craft_hist.append(crafted)
                comp_hist.append(consumed)
                e_hist.append(energy)

        for _ in range(warmstart_episodes):                          # bassin haut à coût 0 (non enregistré)
            _episode(0.0, record=False)
        for _ in range(episodes):                                    # phase mesurée au coût `cost`
            _episode(cost, record=True)

        q = max(1, episodes // 4)
        craft_early = float(np.mean(np.concatenate(craft_hist[:q])))
        craft_late = float(np.mean(np.concatenate(craft_hist[-q:])))
        return {"capability": capability, "cost": cost, "seed": int(seed),
                "craft_early": craft_early, "craft_late": craft_late,
                "comp_late": float(np.mean(np.concatenate(comp_hist[-q:]))),
                "payoff_late": float(np.mean(np.concatenate(e_hist[-q:])))}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
         TorchPopulationModel.GATE_TARGET) = saved


def main():
    import statistics
    episodes = int(os.environ.get("CRP_EPISODES", "800"))
    seeds = list(range(int(os.environ.get("CRP_SEEDS", "2"))))
    costs = [float(x) for x in os.environ.get("CRP_COSTS", "0.0,0.3,0.6").split(",")]
    r = float(os.environ.get("CRP_R", "1.0"))
    adv = {}
    for c in costs:
        on = [run_retention(True, c, r=r, episodes=episodes, seed=s) for s in seeds]
        off = [run_retention(False, c, r=r, episodes=episodes, seed=s) for s in seeds]
        cl_on = statistics.median(x["craft_late"] for x in on)
        cl_off = statistics.median(x["craft_late"] for x in off)
        cmp_on = statistics.median(x["comp_late"] for x in on)
        cmp_off = statistics.median(x["comp_late"] for x in off)
        adv[c] = cl_on - cl_off
        print(f"cost={c:.2f} : craft_late ON={cl_on:.2f} OFF={cl_off:.2f} adv={cl_on-cl_off:+.2f} | "
              f"comp_late ON={cmp_on:.2f} OFF={cmp_off:.2f}")
    hi, lo = max(costs), min(costs)
    scales = adv[hi] > adv[lo] + 0.05 and adv[hi] > 0.05
    verdict = "EPISODIC_CREDIT_RETAINS_CRAFT" if scales else "NO_RETENTION_ADVANTAGE"
    print(f"VERDICT={verdict} : adv(c={hi})={adv[hi]:+.2f} vs adv(c={lo})={adv[lo]:+.2f} -> "
          f"l'avantage de rétention {'CROÎT' if scales else 'ne croît PAS'} avec le coût du craft")


if __name__ == "__main__":
    main()
