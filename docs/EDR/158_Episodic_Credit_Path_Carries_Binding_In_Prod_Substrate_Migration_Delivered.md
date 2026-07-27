---
id: EDR-158
type: EDR
title: "Chemin de crédit ÉPISODIQUE dans le substrat prod (learn_episode) : PORTE le binding means→ends là où le TD différé échoue — episodic+gate +0.298 vs td+gate +0.000 (3 seeds), reproduit la recette 147 (+0.30) comme MÉTHODE réutilisable du substrat prod. 2×2 crédit×gate isole : binding = gate ET crédit épisodique (conjonction). Exécute la reco d'EDR-148. ADDITIF/flag-OFF (banc // intact)"
status: accepted
gate: null
verdict: EPISODIC_CREDIT_CARRIES_BINDING_IN_PROD
---

# EDR 158 : le crédit épisodique porte le binding dans le substrat prod (migration livrée)

## Contexte

EDR-148 a montré que la recette de binding (gate + anti-saturation, 129/136/147) NE tient PAS dans le
`learn()` prod (Actor-Critic TD(0) DIFFÉRÉ 1-pas) : gate ≈ nogate ≈ 0. Diagnostic : le verrou n'est ni
le gate, ni l'exploration, ni la contamination S1, mais le MÉCANISME DE CRÉDIT — toute la recette a été
validée sous REINFORCE épisodique, jamais le TD différé. **Reco d'EDR-148 : porter le binding via un
crédit ÉPISODIQUE/multi-pas.** Ce build exécute cette reco : ajouter ce chemin de crédit AU substrat prod
et vérifier qu'il porte le binding.

## Méthode

`TorchPopulationModel.learn_episode` (ADDITIF : ne touche NI forward, NI learn, NI learn_episode_bptt) :
rejoue l'épisode en TRONQUANT la récurrence (H détaché entre pas = crédit 1-pas par pas) mais crédite
les actions par le RETOUR ÉPISODIQUE multi-actions (REINFORCE + baseline caller) ; applique le gate de
conditionnement (biais appris sur `GATE_TARGET`, `gate_last_only=True` → au SEUL dernier pas, l'action
« ends », pour éviter la contamination « means » d'EDR-148) + anti-saturation de la marginale de base.
C'est la recette 147 rendue MÉTHODE du substrat prod (réutilisable), pas une boucle de banc.
`tools/torch_prod_gate_meansends.py` gagne un axe `credit='td'|'episodic'` : 2×2 crédit × gate sur
means→ends, `binding_gap = P(Y|X) − P(Y|¬X)` poolé sur le dernier quart.

## Constat

**2×2 crédit × gate (3 seeds, 1000 ép ; épisodique en échantillonnage stochastique) :**

| crédit × gate | binding_gap médian | par seed | hit_end |
|---|---|---|---|
| td + nogate | +0.052 | [+0.05, +0.02, +0.11] | 0.034 |
| td + gate | +0.000 | [+0.00, −0.33, +0.05] | 0.008 |
| episodic + nogate | +0.019 | [+0.02, +0.01, +0.02] | 0.070 |
| **episodic + gate** | **+0.298** | [+0.30, +0.36, +0.00] | 0.279 |

`VERDICT = EPISODIC_CREDIT_CARRIES_BINDING_IN_PROD`. Le crédit épisodique + gate BINDE (+0.298, hit
0.279) là où toutes les autres cellules ≈0. Reproduit EDR-147 (+0.30) via la MÉTHODE du substrat.

## Lecture

- **Migration LIVRÉE** : le substrat prod dispose maintenant d'un chemin de crédit qui PORTE le binding
  (`learn_episode`). La reco d'EDR-148 est exécutée et validée.
- **Le 2×2 isole une CONJONCTION** : le binding exige **le gate ET le crédit épisodique**. Ni le gate
  seul (td+gate +0.000), ni le crédit épisodique seul (episodic+nogate +0.019) ne suffit. C'est la
  synthèse causale de tout le fil : gate = ROUTAGE (129/136/147), crédit épisodique = VÉHICULE (148/158).
- **1/3 seeds s'effondre** (+0.00, path-dependence / bassin d'optim, cf. EDR-131/133/147) : médiane
  robuste, mais la fiabilité seed reste le résidu connu (init/bassin, pas le mécanisme).

## Conséquences

- **Carte de valeur torch — COMPLÈTE et exécutable en prod** : (a) faisabilité/parité (140/141) ;
  (b) mémoire multi-pas via BPTT (145) ; (c) binding compositionnel via **gate + crédit épisodique**
  (`learn_episode`, 158) — chacune LIVRÉE comme capacité du substrat prod, flag-gated OFF par défaut.
- **Recette prod du binding** : `CONDITION_GATE=True` + `GATE_TARGET` + `ANTISAT>0` + crédit via
  `learn_episode` (PAS `learn` TD différé, PAS BPTT dans le chemin de binding — EDR-147). Adam requis
  (SGD trop lent pour le gate).
- Head + méthode + banc réutilisables. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-158`.

## Caveats

1. **Tâche DURE** (hit absolu ~0.28 au mieux, substrat 172-nœuds dégénéré) : le résultat ROBUSTE est la
   COMPARAISON contrôlée crédit-épisodique(+0.30) vs TD-différé(~0), MÊME substrat/gate — pas l'absolu.
2. 3 seeds, 1/3 collapse (path-dependence) ; le SIGNE et l'ampleur du delta épisodique-vs-TD sont nets
   et reproduisent 147.
3. `gate_last_only=True` : le gate est scopé au dernier pas via le banc (le substrat prod task-agnostique
   ne connaît pas « le dernier pas » en général — en prod réelle il faudrait un signal de phase/contexte,
   ou apprendre le scoping depuis H). Bornage : la GÉNÉRALISATION à N pas / gate uniforme appris n'est pas
   validée ici (means→ends 2-pas seulement).
4. Crédit épisodique = fenêtre COMPLÈTE de l'épisode fournie par le caller ; l'intégration dans la boucle
   biosphère (épisodes de longueur variable, récompense en ligne) est un incrément d'ingénierie séparé.
