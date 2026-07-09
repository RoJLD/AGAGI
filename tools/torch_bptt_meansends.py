"""BPTT fenêtré sur means→ends IN-SUBSTRAT (EDR-146) — le vrai test de valeur de torch.

Tâche means→ends (= celle du fil compositional //, mais mécanisme DIFFÉRENT = complémentaire) :
S1 émettre X (récompense différée 0), S2 émettre Y récompensé SSI X fait en S1. `obs_b` n'encode PAS
did_x -> l'agent doit le MÉMORISER par la récurrence, PUIS conditionner Y sur lui = binding.

On oppose deux régimes d'apprentissage du MÊME substrat torch (`TorchPopulationModel`) :
  - **bptt**      : crédit rétropropagé À TRAVERS la récurrence S2->S1 (graphe retenu). Numpy ne peut pas.
  - **truncated** : H détaché entre S1 et S2 (= ce que forward/learn/legacy font). Crédit 1-pas.

Métrique de binding (EDR-128) : binding_gap = P(Y|X) − P(Y|¬X). >0 = conditionnement (means→ends) ;
≈0 = l'agent monte des marginales sans binder. Hypothèse : BPTT ouvre le gap, tronqué non.

Usage : python tools/torch_bptt_meansends.py   (env: TBM_EPOCHS, TBM_SEEDS)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8


def _softmax(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_meansends(mode: str, epochs: int = 600, n_agents: int = 128, seed: int = 0,
                  target_x: int = 3, target_y: int = 5, lr: float = 0.05):
    """Entraîne le substrat torch sur means→ends en régime `mode` ('bptt'|'truncated').
    Retourne les métriques finales (hit_end, p_x, binding_gap = P(Y|X)−P(Y|¬X))."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel

    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)
    agents = [MambaAgent() for _ in range(n_agents)]
    pop = TorchPopulationModel(agents, lr=lr)
    pop.opt = torch.optim.Adam([pop.W], lr=lr)     # Adam pour REINFORCE (SGD trop lent/bruité)
    I, N = pop.I, pop.N
    obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)   # S1 (motif fixe)
    obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)   # S2 (motif distinct ; n'encode pas did_x)
    truncate = (mode == "truncated")

    hit_end = p_x = gap = 0.0
    for _ in range(epochs):
        pop.H = torch.zeros((n_agents, N))                     # épisode frais
        logits1, _ = pop.forward(obs_a)
        move1 = np.array([rng.choice(_MOVE, p=p) for p in _softmax(np.asarray(logits1)[:, :_MOVE])])
        logits2, _ = pop.forward(obs_b)
        move2 = np.array([rng.choice(_MOVE, p=p) for p in _softmax(np.asarray(logits2)[:, :_MOVE])])

        did_x = (move1 == target_x)
        correct_y = (move2 == target_y)
        reward = np.where(correct_y & did_x, 1.0, -1.0).astype(np.float32)
        adv = reward - reward.mean()                           # baseline (réduit la variance REINFORCE)

        acts = [[{"move": int(m)} for m in move1], [{"move": int(m)} for m in move2]]
        pop.learn_episode_bptt([obs_a, obs_b], acts, adv, truncate=truncate)

        hit_end = float(np.mean(correct_y & did_x))
        p_x = float(np.mean(did_x))
        pyx = float(np.mean(correct_y[did_x])) if did_x.any() else 0.0
        pynx = float(np.mean(correct_y[~did_x])) if (~did_x).any() else 0.0
        gap = pyx - pynx
    return {"mode": mode, "hit_end": hit_end, "p_x": p_x, "binding_gap": gap}


def main():
    import statistics
    epochs = int(os.environ.get("TBM_EPOCHS", "1000"))   # <1000 = sous-entraîné (hit_end ~ chance)
    seeds = list(range(int(os.environ.get("TBM_SEEDS", "3"))))
    out = {}
    for mode in ("bptt", "truncated"):
        rows = [run_meansends(mode, epochs=epochs, seed=s) for s in seeds]
        out[mode] = rows
        med_gap = statistics.median(r["binding_gap"] for r in rows)
        med_hit = statistics.median(r["hit_end"] for r in rows)
        print(f"{mode:9s} : binding_gap median={med_gap:+.3f} hit_end median={med_hit:.3f}  "
              f"per-seed gap={['%+.2f' % r['binding_gap'] for r in rows]}")
    gb = statistics.median(r["binding_gap"] for r in out["bptt"])
    gt = statistics.median(r["binding_gap"] for r in out["truncated"])
    verdict = "BPTT_BINDE" if (gb > 0.25 and gb > gt + 0.15) else ("PARTIEL" if gb > gt + 0.10 else "NEUTRE")
    print(f"VERDICT={verdict} : binding_gap bptt={gb:+.3f} vs truncated={gt:+.3f} "
          f"-> le crédit à travers le temps (numpy-impossible) {'OUVRE' if verdict!='NEUTRE' else 'n_ouvre pas'} le means→ends")
    return out


if __name__ == "__main__":
    main()
