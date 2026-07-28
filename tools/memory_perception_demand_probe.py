"""AGI-Taxonomy — MESURE de l'arête « memory demands perception » sur un delayed-match-to-sample.

Mémoire = état récurrent APPRIS du MambaAgent, PORTÉ à travers les ticks (encode -> délai -> test).
Ablation d'ENTRÉE within-subject : à l'éval, on DÉRANGE le one-hot de l'indice au tick d'ENCODAGE
(derange_rows, in-distribution). Deux conditions : DELAYED (obs de test vide -> il faut la rétention) ->
l'ablation effondre ; PRESENT (obs de test = vue directe BRUITÉE de l'indice) -> l'ablation est inerte
(contrôle de demande = specificity_control). functional_aliasing="n/a" (ablation d'entrée, pas d'écriture
substrat -> pas de fuite à garder, cf. CALIB-ALIAS).

⚠️ Vérifié contre le code réel (`src/agents/backend_torch.py`), DIVERGENCE avec la transcription initiale :
`TorchPopulationModel.forward(x)` renvoie `(logits, 0)` — le 2e élément est un PLACEHOLDER entier, PAS
l'état — et `forward` met déjà à jour `self.H` EN INTERNE (`self.H = H_new.detach()`). Réassigner
`agent.H = state` casserait tout (H deviendrait l'entier 0 au tick suivant). `_forward_seq` NE réassigne
donc PAS l'état : un simple reset de `agent.H` à zéro en tête de séquence suffit, `forward` porte la
récurrence tick après tick tout seul (cf. `_forward_seq`, docstring). `learn_episode(obs_seq, actions_seq,
rewards, gate_last_only=True)` REJOUE lui-même toute la séquence depuis H=0 (tronqué, 1-pas par pas) —
il ne dépend PAS de `agent.H` externe ; `gate_last_only` ne pilote QUE l'application du gate de
conditionnement (désactivé ici, `CONDITION_GATE=False`), pas le crédit d'action — chaque tick contribue à
`total_logp`, d'où les actions neutres `{"move": 0}` aux ticks intermédiaires dans `_train_and_eval`.

Le nom run_*probe trippe le cliquet -> calibré (memory oracle/aléatoire) dans test_instrument_calibration.
Pur torch CPU, aucun bail. Usage : python tools/memory_perception_demand_probe.py
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


def _noisy_onehot(cues, K, I, n_agents, flip_p, rng):
    """Vue directe BRUITÉE de l'indice au TEST : avec proba flip_p, one-hot sur un référent ALÉATOIRE
    (garde la métrique PRESENT vivante, plafonnée à ~1-flip_p)."""
    shown = np.where(rng.random(n_agents) < flip_p, rng.randint(0, K, size=n_agents), cues)
    return _onehot(shown, K, I, n_agents)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _seq_inputs(cues, condition, ablate, K, I, n_agents, D, flip_p, rng):
    """Construit la séquence [encode, délai×D, test]. encode = one-hot indice (dérangé si ablate).
    délai = zéros. test = zéros (delayed) ou vue bruitée (present)."""
    enc_in = _onehot(cues, K, I, n_agents)
    if ablate:
        enc_in = derange_rows(enc_in, rng)             # ABLATION de la perception à l'ENCODAGE
    zeros = np.zeros((n_agents, I), dtype=np.float32)
    test_in = (zeros if condition == "delayed"
               else _noisy_onehot(cues, K, I, n_agents, flip_p, rng))
    return [enc_in] + [zeros for _ in range(D)] + [test_in], enc_in


def _forward_seq(agent, inputs):
    """Forward la séquence en PORTANT l'état récurrent. Renvoie les preds du DERNIER tick (le test).

    `TorchPopulationModel.forward` renvoie `(logits, 0)` — le 2e élément n'est PAS l'état, juste un
    placeholder entier — et met déjà à jour `agent.H` EN INTERNE à chaque appel (`self.H =
    H_new.detach()`). Un reset à zéro en tête de séquence suffit ; NE PAS réassigner `agent.H` depuis
    le retour de `forward` (ça écraserait la récurrence avec l'entier 0 au tick suivant)."""
    agent.H = _zeros_state(agent)
    preds = None
    for x in inputs:
        preds, _ = agent.forward(x)                    # forward() porte agent.H en interne
    return preds


def _zeros_state(agent):
    import torch
    return torch.zeros((_n_agents_of(agent), agent.N))


def _n_agents_of(agent):
    return agent.W.shape[0]


def _train_and_eval(seed, condition, episodes, n_agents, K, D, lr, flip_p, memory_mode, eval_batches=40):
    """Entraîne (learned) puis évalue perception d'encodage INTACTE vs DÉRANGÉE. Renvoie (acc_i, acc_a)."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = agent.I
        rng = np.random.RandomState(seed + 1)
        learned = memory_mode == "learned"
        if learned:
            agent.opt = torch.optim.Adam([agent.W], lr=lr)
            for _ in range(episodes):
                cues = rng.randint(0, K, size=n_agents)
                inputs, _enc = _seq_inputs(cues, condition, False, K, I, n_agents, D, flip_p, rng)
                preds = _forward_seq(agent, inputs)
                guess = _sample(preds, K, rng, n_agents)
                adv = (guess == cues).astype(np.float32)
                adv = adv - adv.mean()
                # crédit du DERNIER tick (le rappel) ; ticks intermédiaires = actions neutres
                acts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(inputs) - 1)]
                acts.append([{"move": int(g)} for g in guess])
                agent.learn_episode(inputs, acts, adv, gate_last_only=True)

        def _eval(ablate):
            hits = []
            for _ in range(eval_batches):
                cues = rng.randint(0, K, size=n_agents)
                inputs, enc_in = _seq_inputs(cues, condition, ablate, K, I, n_agents, D, flip_p, rng)
                if memory_mode == "oracle":
                    guess = enc_in[:, :K].argmax(axis=1)   # rétention PARFAITE de ce qui a été encodé
                elif memory_mode == "random":
                    guess = rng.randint(0, K, size=n_agents)
                else:
                    preds = _forward_seq(agent, inputs)
                    guess = np.asarray(preds)[:, :K].argmax(axis=1)
                hits.append((guess == cues).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval(False), _eval(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def run_memory_perception_demand_probe(seeds, episodes=800, n_agents=16, K=6, D=2, lr=0.05,
                                       flip_p=0.3, memory_mode="learned"):
    """Mesure « memory demands perception ». Par seed : DELAYED et PRESENT, chacun éval intact/ablé.
    DELAYED -> ablation_verdict (attendu X_DEMANDED) ; PRESENT -> inerte (specificity_control)."""
    di, da, pi, pa = [], [], [], []
    for s in seeds:
        d_i, d_a = _train_and_eval(s, "delayed", episodes, n_agents, K, D, lr, flip_p, memory_mode)
        p_i, p_a = _train_and_eval(s, "present", episodes, n_agents, K, D, lr, flip_p, memory_mode)
        di.append(d_i); da.append(d_a); pi.append(p_i); pa.append(p_a)

    floor = 1.0 / K
    delayed = ablation_verdict(di, da, intervention_verified=True, floor=floor, ceiling=1.0)
    present = ablation_verdict(pi, pa, intervention_verified=True, floor=floor, ceiling=1.0)
    present_med = float(np.median(pi))
    present_alive = floor + 0.05 < present_med < 0.9              # VIVANT (ni plancher ni plafond)
    specificity = "pass" if (present["verdict"] == "X_DECOY" and present_alive) else "fail"
    return {"delayed": delayed, "present": present, "present_alive": present_alive,
            "specificity_control": specificity, "functional_aliasing": "n/a", "n": len(seeds),
            "delayed_intact": di, "delayed_ablated": da, "present_intact": pi, "present_ablated": pa}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("MP_SEEDS", "12"))))
    ep = int(os.environ.get("MP_EPISODES", "800"))
    na = int(os.environ.get("MP_AGENTS", "16"))
    r = run_memory_perception_demand_probe(seeds, episodes=ep, n_agents=na)
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("delayed", "present", "specificity_control", "present_alive",
                               "functional_aliasing", "n")}, ensure_ascii=False, indent=2))
