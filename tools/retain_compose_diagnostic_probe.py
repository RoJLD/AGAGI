"""Diagnostic : le mur retain+compose est-il la RÉTENTION apprise (H1) ou la lecture d'un état porté (H2) ?

3 conditions bilinéaire (BILINEAR=True) + supervisé (cross-entropy via _step direct, grad) sur (q+key)%K :
 same_tick : key+q CO-PRÉSENTS en entrée (baseline, connu ~0.93) ;
 oracle    : key injecté PAR FIAT dans des nœuds d'ÉTAT (mem_slots), q en entrée -> rétention PARFAITE ;
 learned   : 2 pas encode(key)->use(q), rétention APPRISE (~0.18 à `lr=0.02` SEULEMENT -> voir ⚠️ E19).
oracle APPREND -> gap = rétention apprise (H1) ; oracle ÉCHOUE (same_tick OK) -> gap = lecture d'état (H2).
Calibré : same_tick (positif, le bilinéaire compose) + oracle_decorrelated (négatif, key aléatoire ->
plancher) + learned (contre-exemple GELÉ de la bascule de `lr`, ajouté le 2026-09-01).
Pur torch CPU, aucun bail. Usage : python tools/retain_compose_diagnostic_probe.py

⚠️⚠️ E19 — TOUT VERDICT ISSU DE CETTE SONDE DOIT ÊTRE REJOUÉ À `lr=0.002` AVANT D'ÊTRE ÉCRIT.
Le défaut `lr=0.02` (:101) est CONSERVÉ tel quel — le changer ré-écrirait silencieusement le passé et
invaliderait les chiffres cités dans les cas de calibration — mais il PRODUIT un faux nul sur `learned` :
- `n_agents` n'est PAS un minibatch. Chaque agent porte ses PROPRES `W/U/V/W_bl`
  (`src/agents/backend_torch.py:85-86` et `:113-115`), donc la `F.cross_entropy` sur les 16 lignes (:86)
  donne à CHAQUE jeu de paramètres exactement 1 exemple par pas -> **batch effectif = 1** sous Adam (:80).
- `same_tick` (:51-52) et `oracle` (:53-58) sont des problèmes à UN SEUL `_step`, bien conditionnés : ils
  TOLÈRENT ce pas. `learned` (:59-61) enchaîne DEUX `_step` avec BPTT et DIVERGE. Le réglage avait été
  validé implicitement sur les conditions faciles, puis appliqué à la condition testée.
- MESURÉ n=12, episodes=600, seule variable changée = `lr` : lr=0.02 -> same_tick 0.969 / oracle 0.971 /
  learned **0.173** (verdict `RETENTION`) ; lr=0.002 -> 0.937 / 0.945 / learned **0.923** (verdict
  `INCONCLUSIVE`). Séparation par-seed TOTALE (0.897 > 0.192, **0/144**) ; l'écart learned↔oracle passe de
  0.798 à 0.022. Le verdict rendu par `run_retain_compose_diagnostic_probe` (:110-119) est donc une
  fonction du RÉGLAGE autant que du substrat.
- Le verdict `RETENTION` bâti sur ce défaut a été RETIRÉ : record `EDR-RETAIN-COMPOSE` (rétracté),
  remplacé par `EDR-RETAIN-COMPOSE-LR`. Garde de pré-vol :
  `tools/experiment_preflight.py::assert_verdict_invariant_to_optimizer` (raisonne sur l'ÉCART AU BRAS DE
  RÉFÉRENCE, jamais sur une barre absolue). Contre-exemple gelé :
  `tests/sandbox/test_instrument_calibration.py::test_retain_compose_learned_verdict_is_an_lr_artifact`.
- ⚠️ La barre `bar = 1/K + 0.15` (:108) est elle-même MAL PLACÉE : elle est 0.072 SOUS le plafond
  structurel du substrat plain (0.3889, forme close — mesure d'UNE passe, NON RÉPLIQUÉE). Ne pas la
  traiter comme une frontière de capacité.

⚠️ Vérifié contre le code réel (`src/agents/backend_torch.py`, `src/agents/mamba_agent.py`,
`src/agents/backend.py`) au moment de l'implémentation — aucun écart avec le brief :
- `TorchPopulationModel._step(obs_t, H_in) -> H_new` est bien grad-enabled (PAS de `torch.no_grad()`
  interne) ; `forward` (lui, `no_grad`) n'est PAS utilisé ici, `_step` est appelé DIRECT — seul moyen
  d'obtenir un graphe autograd traversant l'injection d'état de la condition `oracle`.
- Dims par défaut de `MambaAgent()` : I=59, N=172, O=108. `_mem_start(N=172, O=108, K)` = 70 pour K=6 ;
  mem_slots = [70:76], STRICTEMENT après la fenêtre de readout [N-O:N-O+K] = [64:70] (aucun chevauchement)
  et ≥ I=59 (non écrasés par `H[:, :I] = obs_t` dans `_step`).
- `agent.opt` existe déjà après `make_population` (SGD sur `[W]` ou `[W,U,V,W_bl]` créé par `__init__`) ;
  on le REMPLACE par un Adam incluant explicitement les params bilinéaires, comme le fait le probe frère
  `tools/bilinear_composition_probe.py`.
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


def _mem_start(N, O, K):
    ms = (N - O) + K                     # après les K nœuds de readout, dans l'état non-readout
    assert ms + K <= N, f"mem_slots débordent (N={N},O={O},K={K}) — placer ailleurs"
    return ms


def _cond_logits(agent, key, q, condition, K, I, N, O, n, rng_dec):
    """Un forward grad-enabled (via _step DIRECT, pas agent.forward qui est no_grad) selon la condition.
    Renvoie les logits (n, K) au pas RÉPONSE."""
    import torch
    H = torch.zeros((n, N))
    if condition == "same_tick":
        obs = _slot(key, K, 0, I, n) + _slot(q, K, K, I, n)          # key@[0:K] + q@[K:2K]
        H = agent._step(torch.tensor(obs), H)
    elif condition in ("oracle", "oracle_decorrelated"):
        held = key if condition == "oracle" else rng_dec.randint(0, K, size=n)  # vrai vs aléatoire
        ms = _mem_start(N, O, K)
        H = H.clone()
        H[np.arange(n), ms + (held % K)] = 1.0                       # key injecté en état (mem_slots)
        H = agent._step(torch.tensor(_slot(q, K, K, I, n)), H)       # q en entrée
    else:                                                            # learned (2 pas, BPTT)
        H = agent._step(torch.tensor(_slot(key, K, 0, I, n)), H)     # encode(key)
        H = agent._step(torch.tensor(_slot(q, K, K, I, n)), H)       # use(q)
    return H[:, N - O:N][:, :K]


def _train_eval_condition(seed, condition, episodes, n_agents, K, lr, eval_batches=40):
    import torch
    import torch.nn.functional as F
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel as TPM

    np.random.seed(seed); torch.manual_seed(seed)
    saved = (TPM.CONDITION_GATE, TPM.GATE_TARGET, TPM.BILINEAR, TPM.BILINEAR_RANK)
    TPM.CONDITION_GATE = False; TPM.GATE_TARGET = None
    TPM.BILINEAR = True; TPM.BILINEAR_RANK = 16
    try:
        agent = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I, N, O = agent.I, agent.N, agent.O
        rng = np.random.RandomState(seed + 1); rng_dec = np.random.RandomState(seed + 7)
        agent.opt = torch.optim.Adam([agent.W, agent.U, agent.V, agent.W_bl], lr=lr)

        for _ in range(episodes):
            key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
            logits = _cond_logits(agent, key, q, condition, K, I, N, O, n_agents, rng_dec)
            tgt = torch.tensor(((q + key) % K).astype(np.int64))
            loss = F.cross_entropy(logits, tgt)
            agent.opt.zero_grad(); loss.backward(); agent.opt.step()

        hits = []
        with torch.no_grad():
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
                logits = _cond_logits(agent, key, q, condition, K, I, N, O, n_agents, rng_dec)
                g = logits.argmax(dim=1).cpu().numpy()
                hits.append((g == ((q + key) % K)).astype(np.float32))
        return float(np.mean(np.concatenate(hits)))
    finally:
        (TPM.CONDITION_GATE, TPM.GATE_TARGET, TPM.BILINEAR, TPM.BILINEAR_RANK) = saved


def run_retain_compose_diagnostic_probe(seeds, episodes=1500, n_agents=16, K=6, lr=0.02,
                                        conditions=("same_tick", "oracle", "learned")):
    """Entraîne (q+key)%K sur chaque condition, par seed ; renvoie médianes + gap_verdict."""
    per = {c: [] for c in conditions}
    for s in seeds:
        for c in conditions:
            per[c].append(_train_eval_condition(s, c, episodes, n_agents, K, lr))
    bar = 1.0 / K + 0.15
    med = {c: float(np.median(per[c])) for c in conditions}
    st, oc, ln = med.get("same_tick"), med.get("oracle"), med.get("learned")
    if st is not None and oc is not None and ln is not None:
        if st > bar and oc > bar and ln <= bar:
            verdict = "RETENTION"
        elif st > bar and oc <= bar:
            verdict = "REPRESENTATION"
        else:
            verdict = "INCONCLUSIVE"
    else:
        verdict = "INCONCLUSIVE"
    out = {f"{c}_median": med[c] for c in conditions}
    out.update({"gap_verdict": verdict, "per_seed": per, "n": len(seeds), "bar": bar})
    return out


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("RC_SEEDS", "12"))))
    r = run_retain_compose_diagnostic_probe(seeds, episodes=int(os.environ.get("RC_EPISODES", "1500")))
    print(json.dumps({k: v for k, v in r.items() if k != "per_seed"}, ensure_ascii=False, indent=2))
