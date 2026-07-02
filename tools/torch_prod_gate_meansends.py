"""Validation PROD de la recette gate+anti-saturation (EDR-148) — la recette 129/136/147 binde-t-elle
à travers le VRAI chemin de production ?

EDR-147 a montré, dans une boucle REINFORCE custom, que gate+anti-saturation craque le binding
means→ends (BPTT le dégrade). Question de MIGRATION restée ouverte : la recette tient-elle dans le
chemin PROD réel — `make_population(backend="torch")` + `pop.forward`/`pop.learn` (Actor-Critic TD(0)
à crédit DIFFÉRÉ d'un tick, PAS REINFORCE) — celui qu'utilise le banc compositional // ? Et le gate
sait-il conditionner sur H SEUL (appliqué uniformément par le substrat task-agnostique), sans la
béquille « gate câblé à S2 » du banc 147 ?

On compare, tâche means→ends identique (run_compositional du fil //), le chemin prod avec gate OFF vs
ON (via les flags de classe CONDITION_GATE/ANTISAT/GATE_TARGET). Métrique de binding directe (EDR-128) :
binding_gap = P(Y|X) − P(Y|¬X), poolée sur (agent × épisode) du dernier quart.

Usage : python tools/torch_prod_gate_meansends.py   (env: TPG_EPISODES, TPG_SEEDS, TPG_ANTISAT)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8


def _compo_reward(move2, target_y, did_x):
    return 1.0 if (move2 == target_y and did_x) else -1.0


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_prod(use_gate: bool, episodes: int = 1000, n_agents: int = 128, seed: int = 0,
             target_x: int = 0, target_y: int = 4, lr: float = 0.05, antisat: float = 6.0,
             stochastic: bool = False, gate_s2_only: bool = False, credit: str = "td",
             gate_uniform: bool = False, gate_mult: bool = False):
    """Entraîne une pop torch sur means→ends via le CHEMIN PROD (forward + crédit), gate ON/OFF.
    `credit` : 'td' = `pop.learn` Actor-Critic TD(0) différé 1-pas (défaut prod, EDR-148 : ne binde pas) ;
    'episodic' = `pop.learn_episode` (retour épisodique + gate + anti-sat, EDR-158 : le véhicule qui
    PORTE le binding). `stochastic` : échantillonne (exploration) vs argmax. `gate_s2_only` : gate OFF au
    forward de S1 (anti-contamination, EDR-148). Renvoie binding_gap poolé sur le dernier quart."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    # Flags de classe (restaurés en fin — isolation intra-process). GATE_TARGET = l'action "ends".
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
             TorchPopulationModel.GATE_TARGET, TorchPopulationModel.GATE_MULT)
    TorchPopulationModel.CONDITION_GATE = bool(use_gate)
    TorchPopulationModel.ANTISAT = antisat if use_gate else 0.0
    TorchPopulationModel.GATE_TARGET = target_y if use_gate else None
    TorchPopulationModel.GATE_MULT = bool(gate_mult)              # EDR-160 : gate multiplicatif sigmoïde
    try:
        agents = [MambaAgent() for _ in range(n_agents)]
        pop = make_population(agents, backend="torch")
        pop.opt = torch.optim.Adam(
            [p for p in [pop.W, pop.w_gate, pop.b_gate] if p is not None], lr=lr)
        rng = np.random.RandomState(seed + 1)
        I = pop.I
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)   # S1 (motif fixe)
        obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)   # S2 (n'encode pas did_x)
        zeros = np.zeros(n_agents, dtype=np.float32)

        def _pick(preds):
            logits = np.asarray(preds)[:, :_MOVE]
            if stochastic:
                p = _softmax_np(logits)
                return np.array([rng.choice(_MOVE, p=pi) for pi in p])
            return logits.argmax(axis=1)

        episodic = (credit == "episodic")
        did_hist, cor_hist = [], []
        for _ in range(episodes):
            pop.H = torch.zeros((n_agents, pop.N))                  # épisode frais
            # gate OFF au forward de S1 si scoping ; gate_uniform (EDR-159 : self-scope depuis H) ⇒ ON partout
            pop._gate_runtime = gate_uniform or not (gate_s2_only or episodic)
            preds1, _ = pop.forward(obs_a)                          # S1 : émettre X (récompense différée)
            move1 = _pick(preds1)
            did_x = (move1 == target_x)
            act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
            if not episodic:
                pop.learn(zeros, act1)                             # crédit TD : update différé de S1
            pop._gate_runtime = True                               # gate ON au forward de S2
            preds2, _ = pop.forward(obs_b)                          # S2 : émettre Y (payé SSI X)
            move2 = _pick(preds2)
            correct_y = (move2 == target_y)
            reward2 = np.array([_compo_reward(int(move2[i]), target_y, bool(did_x[i]))
                                for i in range(n_agents)], dtype=np.float32)
            act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
            if episodic:                                           # crédit ÉPISODIQUE : retour 2-pas
                adv = reward2 - reward2.mean()                     # baseline (variance REINFORCE)
                # gate_uniform ⇒ gate à TOUS les pas (self-scope depuis H) ; sinon scopé au dernier (ends)
                pop.learn_episode([obs_a, obs_b], [act1, act2], adv, gate_last_only=not gate_uniform)
            else:
                pop.learn(reward2, act2)                           # crédit TD : update différé de S2
            did_hist.append(did_x)
            cor_hist.append(correct_y)

        q = max(1, episodes // 4)
        did = np.concatenate(did_hist[-q:])                        # pool (agent × épisode) du dernier quart
        cor = np.concatenate(cor_hist[-q:])
        pyx = float(np.mean(cor[did])) if did.any() else 0.0
        pynx = float(np.mean(cor[~did])) if (~did).any() else 0.0
        return {"gate": use_gate, "seed": int(seed), "hit_end": float(np.mean(cor & did)),
                "p_x": float(np.mean(did)), "binding_gap": pyx - pynx}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT,
         TorchPopulationModel.GATE_TARGET, TorchPopulationModel.GATE_MULT) = saved


def main():
    import statistics
    episodes = int(os.environ.get("TPG_EPISODES", "1000"))
    seeds = list(range(int(os.environ.get("TPG_SEEDS", "3"))))
    antisat = float(os.environ.get("TPG_ANTISAT", "6.0"))
    out = {}
    for use_gate in (False, True):
        rows = [run_prod(use_gate, episodes=episodes, seed=s, antisat=antisat) for s in seeds]
        key = "gate" if use_gate else "nogate"
        out[key] = rows
        med_gap = statistics.median(r["binding_gap"] for r in rows)
        med_hit = statistics.median(r["hit_end"] for r in rows)
        print(f"{key:7s} : binding_gap median={med_gap:+.3f} hit_end median={med_hit:.3f}  "
              f"per-seed gap={['%+.2f' % r['binding_gap'] for r in rows]}")
    g = statistics.median(r["binding_gap"] for r in out["gate"])
    n = statistics.median(r["binding_gap"] for r in out["nogate"])
    verdict = ("GATE_BINDS_IN_PROD" if (g > 0.25 and g > n + 0.15) else
               "GATE_PARTIAL_IN_PROD" if g > n + 0.10 else "GATE_DOES_NOT_BIND_IN_PROD")
    print(f"VERDICT={verdict} : gate={g:+.3f} vs nogate={n:+.3f} -> la recette "
          f"{'TIENT' if verdict=='GATE_BINDS_IN_PROD' else 'ne tient pas nettement'} dans le chemin prod")
    return out


if __name__ == "__main__":
    main()
