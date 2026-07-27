"""Le crédit épisodique permet-il la SPÉCIALISATION (choisir/s'engager sur UNE niche) ? — 3e proxy H-unif (EDR-165).

EDR-156/157 : le substrat développe un NOYAU de survie PARTAGÉ, pas de compétence spécialisée → verrou
de spécialisation. Le pari H-unif ([[torch-inworld-integration-plan]]) : spécialisation, binding (161) et
rétention (162) partagent le verrou de crédit conditionnel. 161 a couvert « compétence spécialisée vs
noyau générique » (composer vs FREE). Ici l'angle DISTINCT = choisir parmi PLUSIEURS chaînes et s'y
ENGAGER (spécialisation-comme-niche), + hétérogénéité de population émergente.

Monde 2 chaînes SYMÉTRIQUES : S1 CRAFT_A ou CRAFT_B ; S2 USE_A (paie SSI craft_A) ou USE_B (paie SSI
craft_B). Une chaîne CROISÉE (craft_A→use_B) ne paie pas → il faut s'ENGAGER sur une chaîne cohérente.
Requiert un gate MULTI-CIBLE (route vers use_A si did_A, use_B si did_B, appris depuis H) — capacité
EDR-165 ajoutée à `backend_torch` (additif, flag-gated). Compare ON (gate multi + learn_episode) vs OFF
(TD sans gate). STANDALONE.

Métriques : spec_depth = moyenne sur agents de max(comp_A_i, comp_B_i) (profondeur d'engagement sur la
meilleure chaîne) ; comp_total ; frac_A parmi spécialistes (hétérogénéité de population = division du
travail émergente depuis l'init).

Usage : python tools/craft_specialization_probe.py   (env: CSP_EPISODES, CSP_SEEDS)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8
CRAFT_A, CRAFT_B, USE_A, USE_B = 0, 1, 4, 5


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_spec(capability: bool, episodes: int = 800, n_agents: int = 128, seed: int = 0,
             r: float = 1.0, lr: float = 0.05, antisat: float = 6.0):
    """Entraîne une pop torch sur le monde 2-chaînes. capability=True : gate MULTI-CIBLE + learn_episode.
    False : TD sans gate. Renvoie spec_depth, comp_total, frac_A (hétérogénéité), le tout sur dernier quart."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
             TorchPopulationModel.GATE_TARGET, TorchPopulationModel.GATE_TARGETS)
    TorchPopulationModel.CONDITION_GATE = bool(capability)
    TorchPopulationModel.ANTISAT = antisat if capability else 0.0
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.GATE_TARGETS = [USE_A, USE_B] if capability else None
    try:
        pop = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        pop.opt = torch.optim.Adam(
            [p for p in [pop.W, pop.w_gate, pop.b_gate] if p is not None], lr=lr)
        rng = np.random.RandomState(seed + 1)
        I = pop.I
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)

        def _sample(preds):
            p = _softmax_np(np.asarray(preds)[:, :_MOVE])
            return np.array([rng.choice(_MOVE, p=pi) for pi in p])

        pop._gate_runtime = bool(capability)
        compA_hist, compB_hist = [], []
        for _ in range(episodes):
            pop.H = torch.zeros((n_agents, pop.N))
            preds1, _ = pop.forward(obs_a)
            move1 = _sample(preds1)
            did_a, did_b = (move1 == CRAFT_A), (move1 == CRAFT_B)
            act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
            preds2, _ = pop.forward(obs_b)
            move2 = _sample(preds2)
            act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
            comp_a = (move2 == USE_A) & did_a
            comp_b = (move2 == USE_B) & did_b
            energy = np.where(comp_a | comp_b, r, 0.0).astype(np.float32)
            if capability:
                pop.learn_episode([obs_a, obs_b], [act1, act2], energy - energy.mean(),
                                  gate_last_only=False)
            else:
                pop.learn(np.zeros(n_agents, np.float32), act1)
                pop.learn(energy, act2)
            compA_hist.append(comp_a)
            compB_hist.append(comp_b)

        q = max(1, episodes // 4)
        cA = np.stack(compA_hist[-q:]).mean(axis=0)              # (n_agents,) taux chaîne A par agent
        cB = np.stack(compB_hist[-q:]).mean(axis=0)
        best = np.maximum(cA, cB)
        spec_depth = float(best.mean())                          # profondeur d'engagement sur la meilleure chaîne
        specialists = best > 0.1                                 # agents ayant réellement une niche
        frac_a = float((cA[specialists] > cB[specialists]).mean()) if specialists.any() else float("nan")
        return {"capability": capability, "seed": int(seed), "spec_depth": spec_depth,
                "comp_total": float((cA + cB).mean()), "frac_specialists": float(specialists.mean()),
                "frac_A": frac_a}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
         TorchPopulationModel.GATE_TARGET, TorchPopulationModel.GATE_TARGETS) = saved


def main():
    import statistics
    episodes = int(os.environ.get("CSP_EPISODES", "800"))
    seeds = list(range(int(os.environ.get("CSP_SEEDS", "2"))))
    on = [run_spec(True, episodes=episodes, seed=s) for s in seeds]
    off = [run_spec(False, episodes=episodes, seed=s) for s in seeds]
    sd_on = statistics.median(x["spec_depth"] for x in on)
    sd_off = statistics.median(x["spec_depth"] for x in off)
    fa = [x["frac_A"] for x in on if x["frac_A"] == x["frac_A"]]   # filtre NaN
    print(f"ON  : spec_depth={sd_on:.3f} comp_total={statistics.median(x['comp_total'] for x in on):.3f} "
          f"frac_specialists={statistics.median(x['frac_specialists'] for x in on):.2f} "
          f"frac_A={statistics.median(fa):.2f}" if fa else f"ON  : spec_depth={sd_on:.3f}")
    print(f"OFF : spec_depth={sd_off:.3f} comp_total={statistics.median(x['comp_total'] for x in off):.3f} "
          f"frac_specialists={statistics.median(x['frac_specialists'] for x in off):.2f}")
    adv = sd_on - sd_off
    verdict = "CAPABILITY_ENABLES_SPECIALIZATION" if adv > 0.05 else "NO_SPECIALIZATION_ADVANTAGE"
    print(f"VERDICT={verdict} : spec_depth ON-OFF={adv:+.3f} -> la capacite "
          f"{'PERMET' if adv > 0.05 else 'ne permet PAS'} l'engagement sur une niche")


if __name__ == "__main__":
    main()
