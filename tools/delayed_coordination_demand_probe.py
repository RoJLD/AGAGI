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

LEVIER `choice_decoy` — le référent-leurre est-il PRÉSENTÉ AU RECEIVER ? (défaut `True` = design d'origine)
Le leurre traverse le sender : `_emit` produit `sig_first` ET `sig_last`, et le receiver reçoit
`onehot(...)` des DEUX émissions. « Retirer le leurre » est donc AMBIGU tant qu'on n'a pas dit à quel
niveau. Choix retenu, et il est CONTRAINT par le contrôle de sanité (cf. plus bas) :
  * le SENDER est INCHANGÉ — il voit les deux référents, émet aux deux dates, et reçoit les deux
    `learn_episode` d'émission exactement comme avant. Nombre d'appels, consommation du RNG et crédit du
    sender sont identiques dans les deux réglages ;
  * côté RECEIVER, le tick qui portait le leurre devient un vecteur NUL — le MÊME `_zeros` que les ticks
    de délai. La longueur (D+2) et le nombre de forwards sont INCHANGÉS, dans les deux bras et entre les
    deux réglages : une seule variable change, le contenu d'un tick. RETAIN `[sym] + D×nul + [nul]` (le
    choix se lit sur un tick vide -> la rétention est obligatoire — c'est EXACTEMENT la forme de l'arête
    gravée [[EDR-MEM-PERCEPTION]], `[encode] + D×nul + [test vide]`, d'où « variante fidèle à l'arête
    gravée ») ; PRESENT `[nul] + D×nul + [sym]` (le choix se lit sur le symbole -> rien à retenir). La
    symétrie par la DATE, raison d'être du design, est PRÉSERVÉE ; ce qui disparaît est la réponse
    concurrente injectée dans les logits (EDR-DELAYED-COORD §1 : `logit = (1-δ)·H_prev + δ·tanh(...)`,
    δ≈0.5, 108 des 113 nœuds portés SONT les readouts).
ℹ️ Mettre le tick à zéro ou le RETIRER de la séquence sont ÉQUIVALENTS pour PRESENT, à tout D, et c'est
mesuré (bit-identique) et non pas supposé : depuis H=0, un tick d'entrée nulle laisse H=0 et des logits
nuls -> forward no-op ET gradient exactement nul (la log-proba de l'action neutre y est constante en W).
Le zéro est donc l'intervention MINIMALE, et c'est elle qui est implémentée.
⚠️ CONSÉQUENCE à ne pas ignorer en aval : sous `choice_decoy=False`, le préfixe de PRESENT ne porte AUCUN
symbole — l'ablation y devient un no-op EXACT (Δ=0 par construction, pas par mesure) et le critère
« contrôle inerte » y est VACUEUX. Task 3 doit lire l'inertie de PRESENT autrement sous ce réglage. Le
bras RETAIN, lui, garde son préfixe porteur et son ablation reste informative.

⚠️ `flip_p` — LE CONTRÔLE DE SANITÉ FIXE LE POINT DE FONCTIONNEMENT, et il n'est PAS le défaut du module.
Contrôle prescrit par le rétro-audit : à D=0, PRESENT sans leurre doit reproduire le Lewis publié
([[EDR-LANG-PERCEPTION]] `coord_intact` 0.342 ; 0.338 dans EDR-DELAYED-COORD §1). Mesuré ici à
`episodes=800, n_agents=16, lr=0.05`, seeds 0-2, `credit='bptt'` :
  * `flip_p=0.3` (défaut du module) : avec leurre [0.167, 0.150, 0.156] · sans leurre [0.230, 0.239,
    0.292] -> médiane **0.239**, contrôle ÉCHOUÉ ;
  * `flip_p=0.0` : avec leurre [0.155, 0.150, 0.191] · sans leurre [0.3375, 0.3313, 0.3562] -> médiane
    **0.3375**, contrôle PASSÉ à 0.0005 du 0.338 du record.
La raison est structurelle, pas un réglage de confort : la sonde de RÉFÉRENCE montre au sender un one-hot
PROPRE (`_onehot(targets, ...)`, `perception_coordination_demand_probe.py:86`) — son `flip_p` ne bruite que
la vue DIRECTE du bras NO-COORD. Ici `_noisy_onehot` bruite la vue du SENDER, donc le canal lui-même :
à `flip_p=0.3` le bras le plus FACILE possible (PRESENT à D=0, aucune rétention) plafonne à 0.239, SOUS la
barre de vitalité `1/K+0.15 = 0.317`. À ce réglage la barre est INATTEIGNABLE et un « RETAIN sous la
barre » ne prouve rien (pré-vol, question 1 : l'instrument doit pouvoir rendre LES DEUX issues).
Les chiffres du §1 du record (0.170 / 0.338 / RETAIN 0.223) sont donc à lire à `flip_p=0`.

🔒 CE DÉFAUT EST DÉSORMAIS EXÉCUTABLE, PAS SEULEMENT ÉCRIT — `vitality_bar=` (cf.
`run_delayed_coordination_demand_probe`). Déclarer la barre contre laquelle un verdict sera rendu ARME
`tools/experiment_preflight.assert_bar_is_reachable` AVANT tout entraînement : la sonde ne peut plus
produire de chiffres destinés à une barre que son `flip_p` rend infranchissable. Sans `vitality_bar`
(défaut `None`), aucun verdict n'est rendu, aucune mesure supplémentaire n'est payée et le comportement
est BIT-IDENTIQUE à celui d'avant l'ajout — la vérification est attachée au VERDICT, pas à l'appel.

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


def _prefix_state(receiver, prefix, carried_idx, V, I, n_agents, deranged, rng):
    """Rejoue le PRÉFIXE (tout sauf le tick de choix) et LAISSE `receiver.H` dans l'état porté
    correspondant (aucun retour). `carried_idx` = index, DANS le préfixe, du tick qui porte un symbole
    (`None` si le préfixe n'en porte aucun).

    `deranged=True` : le symbole du préfixe est remplacé par un tirage UNIFORME sur [0,V) INDÉPENDANT
    -> la distribution marginale de H, sa norme et ses corrélations internes sont préservées ; seule
    l'information sur la cible de CE trial est détruite. Analogue-état de `derange_rows`, l'ablation des
    deux arêtes déjà gravées. Le tirage est UNIFORME, jamais « différent du vrai symbole » : la contrainte
    biaiserait le plancher (une coïncidence résiduelle de 1/V avec le vrai symbole est ATTENDUE).

    `carried_idx is None` : rien à substituer -> `deranged` est SANS EFFET (no-op EXACT, le RNG n'est
    même pas consommé). Ce cas n'apparaît QUE sous `choice_decoy=False` (cf. docstring du module)."""
    import torch
    receiver.H = torch.zeros((n_agents, receiver.N))
    for k, x in enumerate(prefix):
        if deranged and k == carried_idx:
            x = _onehot(rng.randint(0, V, size=n_agents), V, I, n_agents)
        receiver.forward(x)
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


def _receiver_seq(arm, sig_first, sig_last, V, I, n_agents, D, choice_decoy):
    """Séquence d'entrées du RECEIVER, et l'index (dans le PRÉFIXE) du tick qui porte un symbole.

    `choice_decoy=True` (défaut) : `[sym(first)] + D×nul + [sym(last)]`, index porté 0 — STRICTEMENT le
    comportement d'origine.
    `choice_decoy=False` : le tick qui portait le LEURRE devient un vecteur NUL. La longueur reste D+2 et
    le nombre de forwards reste identique dans les deux bras et entre les deux réglages — une SEULE
    variable change, le contenu d'un tick. RETAIN `[sym] + D×nul + [nul]` (choix lu sur un tick vide ->
    rétention obligatoire, exactement la forme de l'arête gravée [[EDR-MEM-PERCEPTION]]) et PRESENT
    `[nul] + D×nul + [sym]` (choix lu sur le symbole -> rien à retenir). Cf. docstring du module."""
    show_first = choice_decoy or arm == "RETAIN"      # RETAIN : `first = target`, jamais le leurre
    show_last = choice_decoy or arm == "PRESENT"      # PRESENT : `last  = target`, jamais le leurre
    seq = ([_onehot(sig_first, V, I, n_agents) if show_first else _zeros(I, n_agents)]
           + [_zeros(I, n_agents) for _ in range(D)]
           + [_onehot(sig_last, V, I, n_agents) if show_last else _zeros(I, n_agents)])
    return seq, (0 if show_first else None)           # None -> aucun symbole à substituer (PRESENT sans leurre)


def _train_and_eval_arm(seed, arm, D, episodes, n_agents, K, V, lr, flip_p, eval_batches=40,
                        credit="bptt", choice_decoy=True):
    """Entraîne le couple sender/receiver sur UN bras, puis évalue INTACT vs SUBSTITUÉ sur les MÊMES
    essais (appariement par essai : chaque trial est rejoué deux fois, une fois intact une fois substitué,
    même agent, mêmes poids). Renvoie (acc_intact, acc_ablated). `credit` : cf. docstring du module.
    `choice_decoy` : cf. docstring du module (défaut `True` = design d'origine, bit-identique)."""
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
            sig_first = _emit(sender, s_first, V, rng, n_agents)   # sender INCHANGÉ dans les 2 réglages
            sig_last = _emit(sender, s_last, V, rng, n_agents)
            inputs, _carried = _receiver_seq(arm, sig_first, sig_last, V, I, n_agents, D, choice_decoy)
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
            seq, carried = _receiver_seq(arm, sig_first, sig_last, V, I, n_agents, D, choice_decoy)
            choice_in = seq[-1]                                 # tick de choix INCHANGÉ par l'ablation
            for deranged, hits in ((False, hits_i), (True, hits_a)):
                _prefix_state(receiver, seq[:-1], carried, V, I, n_agents, deranged, rng)
                pr, _ = receiver.forward(choice_in)             # enchaîné sur l'état porté du préfixe
                guess = np.asarray(pr)[:, :K].argmax(axis=1)    # argmax DÉTERMINISTE
                hits.append((guess == target).astype(np.float32))
        return float(np.mean(np.concatenate(hits_i))), float(np.mean(np.concatenate(hits_a)))
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.GATE_TARGETS) = saved


def _easiest_arm_accuracy(seeds, D, episodes, n_agents, K, V, lr, flip_p, eval_batches, credit):
    """Performance du bras le PLUS FACILE du dispositif, AU RÉGIME PASSÉ : PRESENT SANS LEURRE.

    C'est le bras dont on SAIT qu'il doit réussir — `[nul] + D×nul + [sym(cible)]` : le choix se lit sur
    le symbole, aucune rétention n'est demandée, aucune réponse concurrente n'est injectée dans les
    logits. Rien de plus facile n'existe dans cette sonde ; s'il ne franchit pas la barre, rien ne la
    franchira. Renvoie la MÉDIANE des accuracies INTACTES sur les seeds (l'ablation n'a pas de sens ici :
    sous `choice_decoy=False` le préfixe de PRESENT ne porte aucun symbole, l'ablation y est un no-op
    EXACT — cf. docstring du module).

    Mesuré au `D` CONFIGURÉ, sans supposer l'invariance en D — mais celle-ci est CORROBORÉE par le
    record : le contrôle de sanité à D=0 et le balayage du rétro-audit à D=2 rendent le MÊME triplet
    `[0.3375, 0.3313, 0.3562]` à `flip_p=0`. Attendu depuis H=0, un tick d'entrée nulle laisse H=0 et
    des logits nuls (forward no-op, gradient exactement nul).

    ⚠️ COÛT : un entraînement de bras SUPPLÉMENTAIRE par seed (~+50 % sur un appel à deux bras). C'est
    pourquoi il n'est payé QUE si un verdict va être rendu (`vitality_bar` déclarée), et pourquoi
    `easiest_arm_accuracy=` permet d'INJECTER une valeur déjà mesurée au même régime au lieu de la
    re-payer. Aucun cache global : la valeur est reproductible mais l'état global est une classe
    d'erreur du dépôt (E5) — l'économie est EXPLICITE, à la charge de l'appelant."""
    vals = [_train_and_eval_arm(s, "PRESENT", D, episodes, n_agents, K, V, lr, flip_p,
                                eval_batches=eval_batches, credit=credit, choice_decoy=False)[0]
            for s in seeds]
    return float(np.median(vals)), vals


def run_delayed_coordination_demand_probe(seeds, D=2, episodes=800, n_agents=16, K=6, V=8, lr=0.05,
                                          flip_p=0.3, arms=ARMS, eval_batches=40, credit="bptt",
                                          choice_decoy=True, vitality_bar=None,
                                          easiest_arm_accuracy=None, bar_margin=0.0):
    """Mesure « la coordination référentielle DIFFÉRÉE demande la rétention d'état ».

    Par seed et par bras : éval INTACTE vs SUBSTITUTION D'ÉTAT (appariées par essai). Renvoie les
    accuracies brutes ; le VERDICT (ablation_verdict / specificity_control / functional_aliasing) est
    ajouté par Task 3 avec le bras ALIAS. Attendu : RETAIN s'effondre (`X_DEMANDED`, arithmétiquement
    forcé — ce n'est donc PAS le résultat) ; PRESENT vivant SOUS 0.75 et INERTE (c'est LUI qui porte le
    contenu empirique).

    --- `vitality_bar` : la barre du verdict doit être ATTEIGNABLE À CE `flip_p` --------------------------
    `None` (défaut) = aucun verdict n'est rendu -> aucune vérification, aucune mesure supplémentaire,
    comportement BIT-IDENTIQUE à celui d'avant l'ajout. Dès qu'une barre est DÉCLARÉE (typiquement
    `1/K + 0.15`), la sonde mesure d'abord son bras le PLUS FACILE (PRESENT sans leurre, `choice_decoy=
    False`) et passe le couple à `assert_bar_is_reachable` — **AVANT** d'entraîner la moindre cellule
    (garde-avant-entraînement : refuser après avoir payé le run ne protège de rien).

    Sans cette garde, la sonde a réellement produit des chiffres invalides : à `flip_p=0.3`, le défaut
    du module, PRESENT sans leurre plafonne à **0.239** contre une barre à **0.3167** — instrument à
    ISSUE UNIQUE, aucune cellule ne pouvait rendre autre chose qu'« échec ». À `flip_p=0` le même bras
    rend **0.3375** et la barre redevient franchissable. Cf. le défaut d'instrument n°2 de
    `docs/EDR/EDR-DELAYED-COORD_...md` et la docstring d'`assert_bar_is_reachable`.

    FORME ÉCONOMIQUE : `easiest_arm_accuracy=` injecte une valeur DÉJÀ mesurée au même régime (par ex.
    le 0.3375 du record) et supprime entièrement le coût. Aucun plafond ANALYTIQUE ne peut le remplacer :
    `ceiling_bayes = (1-flip_p) + flip_p/K` vaut 0.75 à `flip_p=0.3`, très AU-DESSUS de la barre — il ne
    voit donc pas le défaut, car ce qui plafonne réellement le bras facile n'est pas l'information du
    canal mais l'émergence du code de Lewis. La mesure est nécessaire ; c'est son DÉCLENCHEMENT qui est
    borné (au verdict), pas sa précision.

    `bar_margin` : marge ABSOLUE additionnelle. La marge effective est `max(bar_margin, erreur-type
    binomiale sur n_eval = eval_batches × n_agents)` — cf. `assert_bar_is_reachable`."""
    import torch
    from tools.experiment_preflight import PreflightError, assert_bar_is_reachable
    torch.set_num_threads(1)                 # FOREGROUND, mono-thread : reproductibilité du débit
    if vitality_bar is None and easiest_arm_accuracy is not None:
        # Jamais un no-op SILENCIEUX : un appelant qui fournit la mesure croit avoir armé la garde.
        raise PreflightError(
            "`easiest_arm_accuracy` fourni SANS `vitality_bar` : il ne servirait à rien et la garde "
            "d'atteignabilité ne serait PAS armée. Déclarer la barre du verdict, ou retirer l'argument.")
    bar_info = None
    if vitality_bar is not None:
        if easiest_arm_accuracy is None:
            easiest, per_seed = _easiest_arm_accuracy(seeds, D, episodes, n_agents, K, V, lr, flip_p,
                                                      eval_batches, credit)
        else:
            easiest, per_seed = float(easiest_arm_accuracy), None
        assert_bar_is_reachable(easiest, vitality_bar, n_eval=eval_batches * n_agents,
                                margin=bar_margin,
                                label=f"DELAYED-COORD barre de vitalité (flip_p={flip_p:g})")
        bar_info = {"bar": float(vitality_bar), "easiest_arm": easiest,
                    "easiest_arm_per_seed": per_seed, "easiest_arm_source":
                        "injecté" if easiest_arm_accuracy is not None else "PRESENT sans leurre, mesuré",
                    "n_eval": eval_batches * n_agents, "bar_margin": float(bar_margin)}
    out = {"n": len(seeds),
           "_params": {"D": D, "episodes": episodes, "n_agents": n_agents, "K": K, "V": V, "lr": lr,
                       "flip_p": flip_p, "arms": list(arms), "eval_batches": eval_batches,
                       "seeds": list(seeds), "threads": torch.get_num_threads(),
                       "credit": credit, "choice_decoy": choice_decoy,
                       "ablation_target": "substrate", "vitality_bar": vitality_bar,
                       "ceiling_bayes": (1.0 - flip_p) + flip_p / K, "floor": 1.0 / K},
           "_bar_reachability": bar_info}
    for arm in arms:
        out[arm + "_intact"], out[arm + "_ablated"] = [], []
    for s in seeds:
        for arm in arms:
            i, a = _train_and_eval_arm(s, arm, D, episodes, n_agents, K, V, lr, flip_p,
                                       eval_batches=eval_batches, credit=credit,
                                       choice_decoy=choice_decoy)
            out[arm + "_intact"].append(i)
            out[arm + "_ablated"].append(a)
    return out


if __name__ == "__main__":
    import json
    seeds = list(range(int(os.environ.get("DC_SEEDS", "3"))))
    # `DC_BAR` : barre du verdict à venir. Non déclarée -> aucun verdict, aucune vérification, aucun
    # coût supplémentaire. Déclarée -> la garde d'atteignabilité est armée AVANT tout entraînement
    # (`DC_EASIEST` injecte une mesure déjà faite au même régime pour ne pas la re-payer).
    _bar = os.environ.get("DC_BAR")
    _easiest = os.environ.get("DC_EASIEST")
    r = run_delayed_coordination_demand_probe(
        seeds,
        D=int(os.environ.get("DC_D", "2")),
        episodes=int(os.environ.get("DC_EPISODES", "800")),
        n_agents=int(os.environ.get("DC_AGENTS", "16")),
        lr=float(os.environ.get("DC_LR", "0.05")),
        flip_p=float(os.environ.get("DC_FLIP_P", "0.3")),
        credit=os.environ.get("DC_CREDIT", "bptt"),
        choice_decoy=os.environ.get("DC_CHOICE_DECOY", "1") not in ("0", "false", "False"),
        vitality_bar=float(_bar) if _bar else None,
        easiest_arm_accuracy=float(_easiest) if _easiest else None,
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
