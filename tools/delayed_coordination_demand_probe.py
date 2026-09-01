"""DELAYED-COORD — MESURE de l'arête « coordination référentielle DIFFÉRÉE demande RÉTENTION d'état ».

Protocole de Lewis DIFFÉRÉ, dérivé trait pour trait de `tools/perception_coordination_demand_probe.py`
(deux populations SÉPARÉES sender/receiver, canal = entier ré-encodé en one-hot, `_onehot`/`_noisy_onehot`/
`_sample` identiques) et de `tools/memory_perception_demand_probe.py` (boucle `_forward_seq` multi-ticks,
`acts` à actions neutres aux ticks intermédiaires, crédit `learn_episode`). L'identité de construction est
ce qui rend la mesure comparable aux deux arêtes déjà gravées.

UN ESSAI (longueur D+2, IDENTIQUE dans les deux bras) :
  tick 0        : le sender voit un référent `first`, émet `sig_first` ; le receiver reçoit `onehot(sig_first)`
  ticks 1..D    : vecteur NUL des deux côtés (les slots d'entrée sont écrasés à chaque tick,
                  `backend_torch.py:123` -> un tick sans obs EST un vecteur nul)
  tick D+1      : le sender voit un référent `last`, émet `sig_last` ; le receiver reçoit `onehot(sig_last)`
                  et c'est LÀ qu'on lit son choix `argmax(logits[:, :K])`.

LES DEUX BRAS SONT SYMÉTRIQUES PAR LA DATE de présentation de la cible au sender — canal, sender, longueur
de séquence et nombre de forwards IDENTIQUES ; SEULE la date change :
  RETAIN  (bras testé)   : `first = target`, `last = decoy` -> le receiver doit RETENIR à travers D ticks.
  PRESENT (contrôle)     : `first = decoy`, `last = target` -> le receiver résout SANS rien retenir.
Le référent-leurre est tiré UNIFORMÉMENT sur [0,K) et INDÉPENDAMMENT de la cible — jamais « différent de
la cible » (la contrainte biaiserait le plancher). C'est la leçon MEM-PERCEPTION : dans un contrôle de
spécificité sur tâche récurrente, le canal ablaté doit être DÉCORRÉLÉ de la réponse, sinon un confond
d'entraînement fabrique une fausse demande.

PLAFONNEMENT STRUCTUREL (parade E19) : le référent est montré au sender à travers `_noisy_onehot(flip_p)`
AUX DEUX DATES -> le signal EFFECTIVEMENT PORTEUR de chaque bras (celui du tick 0 dans RETAIN, celui du
tick D+1 dans PRESENT) passe par le bruitage, plafond `(1-flip_p)+flip_p/K` = 0.75 à flip_p=0.3, SOUS la
barre de vitalité quel que soit le `lr`. Bruiter les DEUX dates est ce qui garantit qu'aucun signal PROPRE
sur la cible ne subsiste au tick 0 de PRESENT : un tel signal rendrait la rétention à nouveau PAYANTE dans
le contrôle (version dynamique du piège de MEM-PERCEPTION itération 1). Bruiter le leurre ne change rien à
son contenu informationnel (un uniforme bruité reste uniforme et indépendant de la cible) : les deux bras
restent construits à l'identique.

⚠️ L'ABLATION EST UNE SUBSTITUTION D'ÉTAT DÉCORRÉLÉE, PAS UN H-RESET (non négociable).
Le H-reset à zéro est FAUX ici : sur ce substrat `logit_j = (1-δ_j)·H_prev_j + δ_j·tanh(...)` avec δ médian
0.500, et 108 des 113 nœuds portés SONT les readouts (`N-O = 64`, readouts 64..171) ; remettre H à zéro ne
coupe pas un canal, ça supprime LA MOITIÉ DE LA SORTIE. Mesuré sur le contrôle : intact
[0.510, 0.658, 0.592] -> H-reset [0.988, 0.994, 0.994] — l'ablation AMÉLIORE de +0.40, 3/3 seeds ; et sous
H-reset le contrôle rend `pass` sur un design DÉLIBÉRÉMENT CASSÉ comme sur un design correct : il ne mesure
plus rien. Le repli « n'effacer que les nœuds non-readout » est écarté aussi : seuls 5 nœuds (59..63) ne
sont ni entrée ni readout -> mesuré INERTE (`VACUOUS_ABLATION`).
L'ablation retenue REJOUE le préfixe (émission + délai) avec un symbole SUBSTITUÉ, sur le MÊME agent et les
MÊMES poids, puis présente le tick de choix INCHANGÉ (cf. `_prefix_state`). H n'est JAMAIS remis à zéro
entre le préfixe et le tick de choix. `ablation_target = 'substrate'` : contrairement aux deux arêtes
gravées (ablation d'ENTRÉE, `functional_aliasing='n/a'`), celle-ci touche l'ÉTAT PORTÉ -> Task 3 devra
mesurer `functional_aliasing` sur un bras ALIAS dédié, jamais le déclarer 'n/a'.

CHEMIN DE CRÉDIT (`credit=`) — le patron copié ne peut PAS entraîner un report, et c'est mesuré.
`learn_episode` détache l'état à CHAQUE pas (`backend_torch.py:357`, `H = H.detach()`). Au tick de choix,
l'état qui porte le signal du tick 1 est donc une CONSTANTE : le gradient apprend à LIRE ce qui a été
porté, jamais à le REPORTER. Trois chemins sont exposés, le défaut traverse le report :
  `bptt`      (défaut) `learn_episode_bptt(..., truncate=False)` — même REINFORCE épisodique, même
              avantage baseliné, mêmes actions échantillonnées que `learn_episode` : une SEULE variable
              change, la troncature. C'est le chemin comparable aux arêtes gravées.
  `imitate`   `imitate_episode_bptt` masqué sur le DERNIER pas — BPTT supervisé, supprime en plus la
              variance REINFORCE (avec `n_agents` génomes SÉPARÉS, `backend_torch.py:85-86`, le batch
              effectif est 1 : c'est la cause racine E19 de RETAIN-COMPOSE). Le sender reste REINFORCE
              (aucun symbole « correct » n'existe : le code est émergent). VÉRIFIÉ dans le code, pas
              supposé : `imitate_episode_bptt` part de `H = zeros` (`backend_torch.py:295`) — compatible,
              `_forward_seq` part aussi de H=0.
  `reinforce` `learn_episode` — le chemin TRONQUÉ du brief, gardé comme contrôle négatif du diagnostic.
⚠️ Nuance mesurée, à ne pas sur-lire : la troncature n'interdit pas TOUTE rétention. Le report peut être
PASSIF — `_step` écrit l'obs dans `H[:, :I]` et la porte à δ≈0.5 sans qu'aucun poids ne l'apprenne, et le
readout final apprend à la décoder. C'est ainsi que l'arête gravée `memory→perception` atteint 0.564 à
D=2 SOUS `learn_episode`. Ce que la troncature interdit, c'est d'APPRENDRE À ÉCRIRE dans le report.

Ce module ne rend PAS de verdict : Task 3 ajoute le bras ALIAS, `ablation_verdict`, `specificity_control`
et la calibration. Pur torch CPU, aucun bail `kuzu`, aucun monde.
Usage : python tools/delayed_coordination_demand_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

ARMS = ("RETAIN", "PRESENT")
CREDIT_PATHS = ("bptt", "imitate", "reinforce")   # cf. docstring — `reinforce` = chemin TRONQUÉ du brief


def _onehot(idx, size, I, n_agents):
    m = np.zeros((n_agents, I), dtype=np.float32)
    m[np.arange(n_agents), idx % size] = 1.0
    return m


def _zeros(I, n_agents):
    """Tick SANS observation. Les slots d'entrée étant écrasés à chaque tick (`backend_torch.py:123`,
    `H[:, :I] = obs_t`), un tick de délai EST structurellement un vecteur nul — ce n'est pas un choix."""
    return np.zeros((n_agents, I), dtype=np.float32)


def _noisy_onehot(referents, K, I, n_agents, flip_p, rng):
    """Vue BRUITÉE du référent montré au sender : avec proba flip_p, one-hot sur un référent ALÉATOIRE.
    Plafonne le bras porteur à `(1-flip_p)+flip_p/K` (0.75 à flip_p=0.3, K=6) — parade E19 : le plafond
    vient de la TÂCHE, pas d'un sous-entraînement, donc il ne dépend pas du `lr`."""
    shown = np.where(rng.random(n_agents) < flip_p, rng.randint(0, K, size=n_agents), referents)
    return _onehot(shown, K, I, n_agents)


def _softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sample(preds, n, rng, n_agents):
    p = _softmax(np.asarray(preds)[:, :n])
    return np.array([rng.choice(n, p=pi) for pi in p])


def _emit(sender, s_in, V, rng, n_agents):
    """Émission du sender : H remis à zéro AVANT chaque émission -> le sender est MÉMOIRE-LIBRE, exactement
    comme `_signal_from(..., 'learned')` de la sonde de référence. C'est une condition de validité du
    protocole : un sender qui RETIENDRAIT pourrait ré-encoder le référent du tick 0 dans `sig_last`, et la
    demande de rétention du receiver s'évaporerait (le tick de choix porterait déjà la réponse)."""
    import torch
    sender.H = torch.zeros((n_agents, sender.N))
    preds, _ = sender.forward(s_in)
    return _sample(preds, V, rng, n_agents)


def _forward_seq(agent, inputs):
    """Forward la séquence en PORTANT l'état récurrent ; renvoie les preds du DERNIER tick.
    `TorchPopulationModel.forward` renvoie `(logits, 0)` — le 2e élément est un PLACEHOLDER entier, PAS
    l'état — et met déjà à jour `agent.H` EN INTERNE. Un reset à zéro en tête suffit ; NE JAMAIS
    réassigner `agent.H` depuis le retour de `forward`."""
    import torch
    agent.H = torch.zeros((agent.W.shape[0], agent.N))
    preds = None
    for x in inputs:
        preds, _ = agent.forward(x)
    return preds


def _prefix_state(receiver, sig_first, V, I, n_agents, D, deranged, rng):
    """Rejoue émission + délai et LAISSE `receiver.H` dans l'état porté correspondant (aucun retour).

    `deranged=True` : le symbole du préfixe est remplacé par un tirage UNIFORME sur [0,V) INDÉPENDANT
    -> la distribution marginale de H, sa norme et ses corrélations internes sont préservées ; seule
    l'information sur la cible de CE trial est détruite. Analogue-état de `derange_rows`, l'ablation des
    deux arêtes déjà gravées. Le tirage est UNIFORME, jamais « différent du vrai symbole » : la contrainte
    biaiserait le plancher (une coïncidence résiduelle de 1/V avec le vrai symbole est ATTENDUE)."""
    import torch
    s = rng.randint(0, V, size=n_agents) if deranged else sig_first
    receiver.H = torch.zeros((n_agents, receiver.N))
    receiver.forward(_onehot(s, V, I, n_agents))
    for _ in range(D):
        receiver.forward(_zeros(I, n_agents))
    # PAS de reset de H ici : l'appelant enchaîne DIRECTEMENT le tick de choix sur cet état porté.


def _trial_draw(arm, K, I, n_agents, flip_p, rng):
    """Un tirage d'essai. Renvoie (target, s_first, s_last) — les entrées BRUITÉES du sender aux deux dates.
    `decoy` est tiré UNIFORMÉMENT sur [0,K) et INDÉPENDAMMENT de `target`."""
    target = rng.randint(0, K, size=n_agents)
    decoy = rng.randint(0, K, size=n_agents)          # UNIFORME et INDÉPENDANT de target
    first = target if arm == "RETAIN" else decoy
    last = decoy if arm == "RETAIN" else target
    return (target,
            _noisy_onehot(first, K, I, n_agents, flip_p, rng),
            _noisy_onehot(last, K, I, n_agents, flip_p, rng))


def _train_and_eval_arm(seed, arm, D, episodes, n_agents, K, V, lr, flip_p, eval_batches=40,
                        credit="bptt"):
    """Entraîne le couple sender/receiver sur UN bras, puis évalue INTACT vs SUBSTITUÉ sur les MÊMES
    essais (appariement par essai : chaque trial est rejoué deux fois, une fois intact une fois substitué,
    même agent, mêmes poids). Renvoie (acc_intact, acc_ablated). `credit` : cf. docstring du module."""
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    if arm not in ARMS:
        raise ValueError(f"bras inconnu : {arm!r} (attendu parmi {ARMS})")
    if credit not in CREDIT_PATHS:
        raise ValueError(f"chemin de crédit inconnu : {credit!r} (attendu parmi {CREDIT_PATHS})")

    np.random.seed(seed)
    torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.GATE_TARGETS)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    TorchPopulationModel.GATE_TARGETS = None
    try:
        sender = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        receiver = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        I = sender.I
        rng = np.random.RandomState(seed + 1)
        sender.opt = torch.optim.Adam([sender.W], lr=lr)
        receiver.opt = torch.optim.Adam([receiver.W], lr=lr)

        for _ in range(episodes):
            target, s_first, s_last = _trial_draw(arm, K, I, n_agents, flip_p, rng)
            sig_first = _emit(sender, s_first, V, rng, n_agents)
            sig_last = _emit(sender, s_last, V, rng, n_agents)
            inputs = ([_onehot(sig_first, V, I, n_agents)]
                      + [_zeros(I, n_agents) for _ in range(D)]
                      + [_onehot(sig_last, V, I, n_agents)])
            preds = _forward_seq(receiver, inputs)
            guess = _sample(preds, K, rng, n_agents)
            adv = (guess == target).astype(np.float32)
            adv = adv - adv.mean()
            # crédit du DERNIER tick (le choix) ; ticks intermédiaires = actions neutres (patron
            # memory_perception_demand_probe : chaque tick contribue à total_logp)
            acts = [[{"move": 0} for _ in range(n_agents)] for _ in range(len(inputs) - 1)]
            acts.append([{"move": int(g)} for g in guess])
            if credit == "bptt":            # REINFORCE identique, mais le gradient TRAVERSE le report
                receiver.learn_episode_bptt(inputs, acts, adv, truncate=False)
            elif credit == "imitate":       # BPTT supervisé sur le SEUL tick de choix (masque)
                tgt_seq = [target for _ in inputs]
                mask = [np.zeros(n_agents, dtype=np.float32) for _ in inputs]
                mask[-1] = np.ones(n_agents, dtype=np.float32)
                receiver.imitate_episode_bptt(inputs, tgt_seq, mask_seq=mask)
            else:                           # `reinforce` : chemin TRONQUÉ du brief (contrôle négatif)
                receiver.learn_episode(inputs, acts, adv, gate_last_only=True)
            # le sender est mémoire-libre (H remis à zéro par émission) -> deux épisodes d'UN tick,
            # exactement le patron de la sonde de référence, et non un épisode à deux ticks (qui
            # rejouerait un H porté que le forward n'utilise jamais).
            sender.learn_episode([s_first], [[{"move": int(x)} for x in sig_first]], adv,
                                 gate_last_only=False)
            sender.learn_episode([s_last], [[{"move": int(x)} for x in sig_last]], adv,
                                 gate_last_only=False)

        hits_i, hits_a = [], []
        for _ in range(eval_batches):
            target, s_first, s_last = _trial_draw(arm, K, I, n_agents, flip_p, rng)
            sig_first = _emit(sender, s_first, V, rng, n_agents)
            sig_last = _emit(sender, s_last, V, rng, n_agents)
            choice_in = _onehot(sig_last, V, I, n_agents)       # tick de choix INCHANGÉ par l'ablation
            for deranged, hits in ((False, hits_i), (True, hits_a)):
                _prefix_state(receiver, sig_first, V, I, n_agents, D, deranged, rng)
                pr, _ = receiver.forward(choice_in)             # enchaîné sur l'état porté du préfixe
                guess = np.asarray(pr)[:, :K].argmax(axis=1)    # argmax DÉTERMINISTE
                hits.append((guess == target).astype(np.float32))
        return float(np.mean(np.concatenate(hits_i))), float(np.mean(np.concatenate(hits_a)))
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.GATE_TARGETS) = saved


def run_delayed_coordination_demand_probe(seeds, D=2, episodes=800, n_agents=16, K=6, V=8, lr=0.05,
                                          flip_p=0.3, arms=ARMS, eval_batches=40, credit="bptt"):
    """Mesure « la coordination référentielle DIFFÉRÉE demande la rétention d'état ».

    Par seed et par bras : éval INTACTE vs SUBSTITUTION D'ÉTAT (appariées par essai). Renvoie les
    accuracies brutes ; le VERDICT (ablation_verdict / specificity_control / functional_aliasing) est
    ajouté par Task 3 avec le bras ALIAS. Attendu : RETAIN s'effondre (`X_DEMANDED`, arithmétiquement
    forcé — ce n'est donc PAS le résultat) ; PRESENT vivant SOUS 0.75 et INERTE (c'est LUI qui porte le
    contenu empirique)."""
    import torch
    torch.set_num_threads(1)                 # FOREGROUND, mono-thread : reproductibilité du débit
    out = {"n": len(seeds),
           "_params": {"D": D, "episodes": episodes, "n_agents": n_agents, "K": K, "V": V, "lr": lr,
                       "flip_p": flip_p, "arms": list(arms), "eval_batches": eval_batches,
                       "seeds": list(seeds), "threads": torch.get_num_threads(),
                       "credit": credit, "ablation_target": "substrate",
                       "ceiling_bayes": (1.0 - flip_p) + flip_p / K, "floor": 1.0 / K}}
    for arm in arms:
        out[arm + "_intact"], out[arm + "_ablated"] = [], []
    for s in seeds:
        for arm in arms:
            i, a = _train_and_eval_arm(s, arm, D, episodes, n_agents, K, V, lr, flip_p,
                                       eval_batches=eval_batches, credit=credit)
            out[arm + "_intact"].append(i)
            out[arm + "_ablated"].append(a)
    return out


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("DC_SEEDS", "3"))))
    r = run_delayed_coordination_demand_probe(
        seeds,
        D=int(os.environ.get("DC_D", "2")),
        episodes=int(os.environ.get("DC_EPISODES", "800")),
        n_agents=int(os.environ.get("DC_AGENTS", "16")),
        lr=float(os.environ.get("DC_LR", "0.05")),
        credit=os.environ.get("DC_CREDIT", "bptt"),
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
