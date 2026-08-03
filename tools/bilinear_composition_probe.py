"""Calibration : le terme BILINÉAIRE du substrat débloque-t-il la composition (q+key)%K ?

Étalon connu (finding LANG-MEMORY, `tools/language_memory_demand_probe.py`) : le substrat PLAIN est NUL
sur (q+key)%K (médianes 0.15-0.33 sur un large balayage d'hyperparamètres/méthodes de crédit, floor=1/K).
On entraîne la MÊME tâche avec `TorchPopulationModel.BILINEAR` off puis on, et on compare : `unlocked`
ssi plain reste nul (<= 1/K+0.15) ET bilinéaire apprend (> 1/K+0.15). Contrôle NO-OP : task='recall'
(pur-rappel, one-shot key->key, que le plain apprend déjà) doit ENCORE marcher en bilinéaire (pas de
régression du canal que le substrat maîtrisait avant l'ajout du terme). Le nom `run_*probe` trippe le
cliquet -> calibré dans `tests/sandbox/test_instrument_calibration.py`. Pur torch CPU, aucun bail.

⚠️ Vérifié contre le code réel (`src/agents/backend_torch.py`, Task 1 `7747b1e`) :
- `TorchPopulationModel.BILINEAR`/`BILINEAR_RANK` sont des flags de CLASSE lus au constructeur
  (`make_population` doit être appelé APRÈS les avoir positionnés) ; `agent.U`/`agent.V`/`agent.W_bl`
  ne sont créés (non-None) QUE si `BILINEAR=True` au moment du `__init__`.
- `forward(x) -> (logits, 0)` : le 2e élément est un PLACEHOLDER entier, PAS l'état — `forward` met déjà
  à jour `self.H` EN INTERNE. Ne PAS réassigner `agent.H` depuis ce retour.
- `learn_episode(obs_seq, actions_seq, rewards, gate_last_only=True)` rejoue depuis un H LOCAL tronqué
  (indépendant de `agent.H` externe) et backprop via `self._step`, qui inclut le terme bilinéaire quand
  `BILINEAR=True` et `self.W_bl is not None` — le gradient REMONTE jusqu'à U/V/W_bl (vérifié : leurs
  valeurs changent après un `learn_episode`, cf. smoke/calibration).
- REINFORCE crédite le GUESS ÉCHANTILLONNÉ (pas la cible), motif déjà calibré dans les sondes sœurs
  (`language_memory_demand_probe.py`, `memory_perception_demand_probe.py`) — l'avantage centré
  `(guess==tgt)-mean` pousse la probabilité du guess RÉEL vers le haut/bas selon qu'il a marché.

Usage : python tools/bilinear_composition_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np


def _slot(idx, K, offset, I, n):
    m = np.zeros((n, I), dtype=np.float32)
    m[np.arange(n), offset + (idx % K)] = 1.0
    return m


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, K, rng, n):
    p = _softmax(np.asarray(preds)[:, :K])
    return np.array([rng.choice(K, p=pi) for pi in p])


def _train_eval_one(seed, bilinear, task, episodes, n_agents, K, lr, rank, eval_batches=40):
    """Entraîne la tâche (composition (q+key)%K OU recall=key) avec BILINEAR on/off ; renvoie l'accuracy éval."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.BILINEAR = bool(bilinear)
    TorchPopulationModel.BILINEAR_RANK = int(rank)
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        params = [agent.W]
        if bilinear:
            params += [agent.U, agent.V, agent.W_bl]           # inclure les params bilinéaires
        agent.opt = torch.optim.Adam(params, lr=lr)

        def _target(key, q):
            return (q + key) % K if task == "composition" else key   # recall = key seul (no-op)

        for _ in range(episodes):
            key = rng.randint(0, K, size=n_agents)
            q = rng.randint(0, K, size=n_agents)
            enc = _slot(key, K, 0, I, n_agents)
            use = _slot(q, K, K, I, n_agents) if task == "composition" else np.zeros((n_agents, I), np.float32)
            seq = [enc, use]                                   # encode(key) puis usage(query) ; 1 pas de portage
            agent.H = torch.zeros((n_agents, agent.N))
            logits = None
            for x in seq:
                logits, _ = agent.forward(x)
            guess = _sample(logits, K, rng, n_agents)
            tgt = _target(key, q)
            adv = (guess == tgt).astype(np.float32)
            adv = adv - adv.mean()
            acts = [[{"move": 0} for _ in range(n_agents)], [{"move": int(g)} for g in guess]]
            agent.learn_episode(seq, acts, adv, gate_last_only=True)

        hits = []
        for _ in range(eval_batches):
            key = rng.randint(0, K, size=n_agents)
            q = rng.randint(0, K, size=n_agents)
            enc = _slot(key, K, 0, I, n_agents)
            use = _slot(q, K, K, I, n_agents) if task == "composition" else np.zeros((n_agents, I), np.float32)
            agent.H = torch.zeros((n_agents, agent.N))
            logits = None
            for x in (enc, use):
                logits, _ = agent.forward(x)
            g = np.asarray(logits)[:, :K].argmax(axis=1)
            hits.append((g == _target(key, q)).astype(np.float32))
        return float(np.mean(np.concatenate(hits)))
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK) = saved


def run_bilinear_composition_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02, rank=16, task="composition"):
    """Compare le substrat PLAIN vs BILINÉAIRE sur la tâche. `unlocked` ssi plain nul (<= 1/K+0.15)
    ET bilinéaire apprend (> 1/K+0.15)."""
    plain, bil = [], []
    for s in seeds:
        plain.append(_train_eval_one(s, False, task, episodes, n_agents, K, lr, rank))
        bil.append(_train_eval_one(s, True, task, episodes, n_agents, K, lr, rank))
    bar = 1.0 / K + 0.15
    pm, bm = float(np.median(plain)), float(np.median(bil))
    unlocked = (pm <= bar) and (bm > bar)
    return {"plain_median": pm, "bilinear_median": bm, "unlocked": unlocked,
            "per_seed": {"plain": plain, "bilinear": bil}, "task": task, "n": len(seeds)}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("BL_SEEDS", "12"))))
    r = run_bilinear_composition_probe(seeds, episodes=int(os.environ.get("BL_EPISODES", "1500")))
    print(json.dumps({k: v for k, v in r.items() if k != "per_seed"}, ensure_ascii=False, indent=2))
