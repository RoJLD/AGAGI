"""AGI-Taxonomy — MESURE de l'arête « language demands memory » (delayed-code-application).

Un MÊME agent (tête d'action à 8 logits partagée, `_MOVE_LOGITS=8`) apprend DEUX capacités
distinguées par les slots actifs de l'observation : LANG = `(q+key)%K` (nécessite le `key` RETENU
via l'état récurrent H PORTÉ encode -> délai -> quête) ; CONTROL = copier `c` (feedforward,
1 tick, indépendant de la mémoire). Ablation SUBSTRAT = reset de H à l'usage (efface le portage) ;
c'est la 1ʳᵉ ablation SUBSTRAT du graphe AGI-Taxonomy (les 2 arêtes précédentes ablataient
l'ENTRÉE, `functional_aliasing='n/a'`) — ici le garde CALIB-ALIAS `functional_aliasing` DOIT être
MESURÉ ('pass'/'fail'), jamais 'n/a' : `ablation_verdict` sur LANG (X_DEMANDED si la rétention
porte la réponse) ; leakage sur CONTROL (bouge-t-il aussi sous le même reset ? si oui, l'ablation
n'est pas chirurgicale, SURGICAL/FUNCTIONAL_LEAK/VACUOUS_ABLATION cf. `run_language_memory_demand_probe`).

⚠️ Vérifié contre le code réel (`src/agents/backend_torch.py`, comme `memory_perception_demand_probe.py`) :
`TorchPopulationModel.forward(x)` renvoie `(logits, 0)` — le 2e élément est un PLACEHOLDER entier, PAS
l'état — et `forward` met déjà à jour `self.H` EN INTERNE (`self.H = H_new.detach()`). NE PAS réassigner
`agent.H` depuis le retour de `forward` (l'entier 0 écraserait la récurrence). Readout =
`np.asarray(logits)[:, :K].argmax(axis=1)`. `learn_episode(obs_seq, actions_seq, rewards,
gate_last_only=True)` REJOUE la séquence depuis un `H` LOCAL initialisé à zéro (détaché à chaque pas —
crédit 1-pas, la valeur PORTÉE traverse quand même la séquence en avant) : il NE dépend PAS de
`agent.H` externe, donc un `_reset_H(agent)` avant `learn_episode` est un no-op inoffensif — mais reste
INDISPENSABLE avant les `agent.forward(...)` utilisés pour ÉCHANTILLONNER l'action créditée (ceux-là
LISENT et ÉCRIVENT `agent.H`), sinon un trial fait fuir son état résiduel dans le suivant.

⚠️ DIVERGENCE avec le brief initial, CORRIGÉE ici : le brief créditait la RÉPONSE CIBLE (`tgt`) comme
« action prise », pondérée par l'avantage centré `(guess==tgt)-mean`. C'est un REINFORCE mal posé — les
agents qui se TROMPENT (avantage négatif) reçoivent alors un gradient qui POUSSE la probabilité de la
BONNE réponse VERS LE BAS (puisque `loss = -(R * logp).mean()` et `R<0`). Corrigé en créditant le GUESS
RÉELLEMENT ÉCHANTILLONNÉ (comme `memory_perception_demand_probe.py`, motif REINFORCE standard déjà
calibré) : avantage positif renforce le guess qui a marché, avantage négatif le décourage — jamais
l'inverse de la bonne réponse.

⚠️ POUR LA TÂCHE 2 (run-verdict) : au smoke (Task 1), `lang_intact` (mode `memory_mode="learned"`) reste
COLLÉ AU PLANCHER (~0.15-0.33, floor=1/K) sur un balayage large — `learn_episode` tronqué 1-pas (D∈{0,1,2},
lr∈{0.02,0.05,0.1}, jusqu'à 3000 épisodes), `learn_episode_bptt(truncate=False)` (BPTT réel, D∈{1,2},
1200 épisodes), ET `imitate_episode_bptt` SUPERVISÉ+BPTT+masqué sur le dernier pas (D∈{0,1}, jusqu'à
lr=0.05/5000 épisodes) — AUCUNE de ces variantes ne fait décoller LANG au-dessus de 1/K+0.15, y COMPRIS
à D=0 (query immédiatement après l'encodage, donc PAS un problème de rétention sur le délai : c'est la
COMBINAISON `(q+key)%K` de deux one-hot injectés à des ticks séparés qui semble dure à représenter/
apprendre pour ce substrat dans ces budgets, indépendamment de la méthode de crédit). `CONTROL`, lui,
APPREND bien (médianes 0.54-0.61 après le correctif d'alignement train/éval ci-dessus, >> 1/K+0.15) —
la tête d'action PARTAGÉE n'empêche donc PAS l'apprentissage en soi. La calibration (oracle/aléatoire/
leaky, ce module) est INDÉPENDANTE de ce risque (elle bypasse l'agent) et reste valide. Avant de lancer
le run n=12, la Tâche 2 devrait soit élargir encore la recherche d'hyperparamètres (episodes/lr/D/n_agents),
soit envisager une tâche de combinaison plus simple, soit documenter un NULL honnête (précédent :
`specificity_control` de MEM-PERCEPTION, EDR-MEM-PERCEPTION) — ne pas forcer.

Le nom `run_*probe` trippe le cliquet -> calibré (oracle/aléatoire/leaky) dans
`tests/sandbox/test_instrument_calibration.py`. Pur torch CPU, aucun bail.
Usage : python tools/language_memory_demand_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.demand_marker import ablation_verdict


def _slot(idx, K, offset, I, n_agents):
    """one-hot de idx dans les slots [offset:offset+K] d'un vecteur d'obs (I,)."""
    m = np.zeros((n_agents, I), dtype=np.float32)
    m[np.arange(n_agents), offset + (idx % K)] = 1.0
    return m


def _zeros(I, n_agents):
    return np.zeros((n_agents, I), dtype=np.float32)


def _reset_H(agent):
    import torch
    agent.H = torch.zeros((agent.W.shape[0], agent.N))


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _carry(agent, key, K, I, n_agents, D, rng):
    """Reset H puis encode(key) + D ticks de délai. H porte le key retenu (MAJ interne de self.H
    à chaque forward). Contexte PARTAGÉ pour l'éval LANG et CONTROL (même substrat ablaté)."""
    _reset_H(agent)
    agent.forward(_slot(key, K, 0, I, n_agents))               # encodage (slots [0:K])
    for _ in range(D):
        agent.forward(_zeros(I, n_agents))                     # délai (H porté, MAJ interne)


def _lang_move(agent, q, K, I, n_agents):
    """Forward LANG (quête aux slots [K:2K]) -> guess = argmax(logits[:, :K])."""
    logits, _ = agent.forward(_slot(q, K, K, I, n_agents))
    return np.asarray(logits)[:, :K].argmax(axis=1)


def _control_move(agent, c, K, I, n_agents):
    """Forward CONTROL (cible aux slots [2K:3K]) -> guess = argmax(logits[:, :K])."""
    logits, _ = agent.forward(_slot(c, K, 2 * K, I, n_agents))
    return np.asarray(logits)[:, :K].argmax(axis=1)


def _train_and_eval(seed, episodes, n_agents, K, D, lr, memory_mode, control_mode, eval_batches=40,
                     train_control=True, weight_decay=0.0):
    """Entraîne l'agent (learned) sur LANG+CONTROL interleavés (même tête d'action, même W), puis
    évalue LANG et CONTROL intact vs H-reset. Renvoie (lang_i, lang_a, ctrl_i, ctrl_a) = accuracies.

    Crédit REINFORCE standard : le GUESS échantillonné (pas la cible) est l'« action prise »,
    pondérée par l'avantage centré (guess correct -> avantage>0 -> renforce ce guess). Les ticks
    intermédiaires (encode/délai) portent une action neutre `{"move": 0}` mais reçoivent le MÊME
    retour épisodique (`gate_last_only=True` ne pilote que le gate, désactivé ici ; le crédit
    d'action, lui, s'applique à CHAQUE pas via `total_logp`, cf. `learn_episode`).

    `train_control=False` (Tâche 2, levier 1 : isoler l'interférence de tête partagée) SAUTE le
    bloc d'entraînement CONTROL -> seul LANG entraîne W. Défaut True = comportement Tâche 1 inchangé
    (calibration non affectée : oracle/random/leaky utilisent episodes=0, ce bloc n'exécute jamais).
    `weight_decay` (Tâche 2, levier 2 : grokking) est threadé dans le constructeur Adam ; défaut 0.0
    = comportement Tâche 1 inchangé (Adam sans decay)."""
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
            agent.opt = torch.optim.Adam([agent.W], lr=lr, weight_decay=weight_decay)
            for _ in range(episodes):
                # --- trial LANG : encode(key) + délai + usage(query) -> (q+key)%K ---
                key = rng.randint(0, K, size=n_agents)
                q = rng.randint(0, K, size=n_agents)
                _reset_H(agent)
                enc = _slot(key, K, 0, I, n_agents)
                seq = [enc] + [_zeros(I, n_agents) for _ in range(D)] + [_slot(q, K, K, I, n_agents)]
                logits = None
                for x in seq:
                    logits, _ = agent.forward(x)                # forward() porte agent.H en interne
                guess = _sample(logits, K, rng, n_agents)
                tgt = (q + key) % K
                adv = (guess == tgt).astype(np.float32); adv = adv - adv.mean()
                acts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(seq) - 1)]
                acts.append([{"move": int(g)} for g in guess])  # crédit du GUESS échantillonné
                agent.learn_episode(seq, acts, adv, gate_last_only=True)

                if not train_control:
                    continue  # levier Tâche 2 #1 : isoler l'interférence de tête partagée -> W ne voit que LANG

                # --- trial CONTROL : encode(nuisance) + délai + usage(control) -> c (feedforward) ---
                # ⚠️ CORRIGÉ : entraîner CONTROL sur H=0 pur (reset direct avant le tick unique) désaligne
                # l'entraînement de l'ÉVAL, qui porte `c` sur le MÊME contexte que LANG (`_carry`, H non nul
                # à l'intact). Sans ça, l'agent apprend « CONTROL sous H=0 », et à l'éval intact (H≠0,
                # hors-distribution) performe PIRE que sous ablation (H=0, distribution d'entraînement) —
                # un artefact qui inverserait le sens de la mesure de fuite. Ici la clé de nuisance est
                # DÉCOUPLÉE de `c` (comme le leurre PRESENT de MEM-PERCEPTION) : le gradient n'a aucune
                # raison d'utiliser H, donc CONTROL apprend à ÊTRE feedforward et voit la MÊME distribution
                # qu'à l'éval (carried H).
                nuisance = rng.randint(0, K, size=n_agents)
                c = rng.randint(0, K, size=n_agents)
                _reset_H(agent)
                cenc = _slot(nuisance, K, 0, I, n_agents)
                cseq = [cenc] + [_zeros(I, n_agents) for _ in range(D)] + [_slot(c, K, 2 * K, I, n_agents)]
                clog = None
                for x in cseq:
                    clog, _ = agent.forward(x)
                cguess = _sample(clog, K, rng, n_agents)
                cadv = (cguess == c).astype(np.float32); cadv = cadv - cadv.mean()
                cacts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(cseq) - 1)]
                cacts.append([{"move": int(g)} for g in cguess])
                agent.learn_episode(cseq, cacts, cadv, gate_last_only=True)

        def _eval_lang(ablate):
            hits = []
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); q = rng.randint(0, K, size=n_agents)
                _carry(agent, key, K, I, n_agents, D, rng)
                if ablate:
                    _reset_H(agent)                              # ABLATION MÉMOIRE : efface le key retenu
                if memory_mode == "oracle":
                    g = ((q + key) % K) if not ablate else rng.randint(0, K, size=n_agents)  # key parfait vs perdu
                elif memory_mode == "random":
                    g = rng.randint(0, K, size=n_agents)
                else:
                    g = _lang_move(agent, q, K, I, n_agents)
                hits.append((g == ((q + key) % K)).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        def _eval_control(ablate):
            hits = []
            for _ in range(eval_batches):
                key = rng.randint(0, K, size=n_agents); c = rng.randint(0, K, size=n_agents)
                _carry(agent, key, K, I, n_agents, D, rng)       # même contexte porté que LANG
                if ablate:
                    _reset_H(agent)
                if control_mode == "leaky":
                    # CONTROL forcé de dépendre du key retenu -> ablater fait FUIR (vérité-terrain du garde)
                    g = c if not ablate else rng.randint(0, K, size=n_agents)
                elif memory_mode in ("oracle", "random"):
                    g = c                                        # contrôle feedforward parfait (bypass)
                else:
                    g = _control_move(agent, c, K, I, n_agents)
                hits.append((g == c).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return _eval_lang(False), _eval_lang(True), _eval_control(False), _eval_control(True)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def run_language_memory_demand_probe(seeds, episodes=1200, n_agents=16, K=6, D=2, lr=0.02,
                                     memory_mode="learned", control_mode="feedforward",
                                     train_control=True, weight_decay=0.0):
    """Mesure « language demands memory ». Par seed : LANG et CONTROL, chacun éval intact/ablé (H-reset).
    LANG -> ablation_verdict (X_DEMANDED) ; CONTROL -> garde functional_aliasing (leakage≈0 -> pass,
    1er usage réel du jalon CALIB-ALIAS sur une ablation SUBSTRAT — les 2 arêtes précédentes du graphe
    AGI-Taxonomy ablataient l'ENTRÉE, `functional_aliasing='n/a'`).

    `train_control` / `weight_decay` : knobs diagnostiques Tâche 2 (défauts = comportement Tâche 1
    inchangé), cf. docstring de `_train_and_eval`."""
    li, la, ci, ca = [], [], [], []
    for s in seeds:
        l_i, l_a, c_i, c_a = _train_and_eval(s, episodes, n_agents, K, D, lr, memory_mode, control_mode,
                                             train_control=train_control, weight_decay=weight_decay)
        li.append(l_i); la.append(l_a); ci.append(c_i); ca.append(c_a)

    floor = 1.0 / K
    lang = ablation_verdict(li, la, intervention_verified=True, floor=floor, ceiling=1.0)
    leakage = abs(float(np.median(ci)) - float(np.median(ca)))
    x_response = abs(float(np.median(li)) - float(np.median(la)))
    tol = 0.05                                                  # tolérance de fuite (bruit d'échantillon)
    if x_response <= tol:
        alias = "VACUOUS_ABLATION"
    elif leakage <= tol:
        alias = "SURGICAL"
    else:
        alias = "FUNCTIONAL_LEAK"
    fa = "pass" if alias == "SURGICAL" else "fail"
    return {"lang_demand": lang, "functional_aliasing": fa, "alias_verdict": alias,
            "leakage": leakage, "x_response": x_response, "n": len(seeds),
            "lang_intact": li, "lang_ablated": la, "control_intact": ci, "control_ablated": ca}


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("LM_SEEDS", "12"))))
    r = run_language_memory_demand_probe(seeds, episodes=int(os.environ.get("LM_EPISODES", "1200")),
                                         n_agents=int(os.environ.get("LM_AGENTS", "16")))
    print(json.dumps({k: v for k, v in r.items()
                      if k in ("lang_demand", "functional_aliasing", "alias_verdict", "leakage",
                               "x_response", "n")}, ensure_ascii=False, indent=2))
