---
id: EDR-LANG-PERCEPTION
type: EDR
title: "Première arête MESURÉE du graphe AGI-Taxonomy : la coordination référentielle DEMANDE la perception (ablation d'entrée within-subject, X_DEMANDED ; inerte en NO-COORD)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
SP-1 a livré le graphe capability-demand (vide). Première arête MESURÉE : « language/coordination demande
perception » ? On l'établit sur le proxy bon marché du jeu de Lewis, par ablation d'ENTRÉE within-subject.

## Méthode
Jeu référentiel torch (sender/receiver = MambaAgent, learn_episode). Ablation = dérangement du one-hot cible
du sender À L'ÉVAL (derange_rows, in-distribution). COORD : le receiver ne lit que le signal. NO-COORD
(contrôle de demande VIVANT) : le receiver a une vue directe BRUITÉE de la cible (flip_p=0.3). n=12 seeds,
`ablation_verdict` (floor=1/K). Sonde calibrée (sender oracle → effondre ; aléatoire → inerte).

Bornage du coût : smoke à 3 seeds (episodes=300/600/900, n_agents=16) pour mesurer le débit et la trajectoire
d'apprentissage avant le run n=12 ; episodes=800/n_agents=16 retenus par interpolation (coord_intact médian
projeté ~0.34, au-dessus du seuil vivant 1/K+0.15≈0.317). Le run n=12 en tâche de fond s'est révélé orphelin
(aucune sortie après 92 min, `TaskStop` ne retrouvait plus la tâche) ; relancé au premier plan via un pilote
verrouillé (mêmes fonctions internes de la sonde, `_train_and_eval` + `ablation_verdict`, checkpointé par
cellule seed×condition) — terminé en 237.5 s, confirmant que le run de fond initial était bloqué et non
simplement lent.

## Résultat
COORD : X_DEMANDED (ratio 2.115 ; intacte médiane 0.34375, ablée 0.1625 ~ hasard 1/K=0.167). Le seuil
« vivant » retenu pour le bornage n'est PAS 1/K mais 1/K+0.15≈0.317 (marge d'émergence, pas le simple
plancher de hasard) : la médiane intacte le dépasse de +0.027 seulement — marge NARROW sur la médiane
seule. Ce qui rend le verdict robuste n'est pas cette marge de médiane mais la séparation **12/12 seeds à
recouvrement ZÉRO** entre intacte (min 0.306) et ablée (max 0.184) : aucun seed n'échappe au collapse, la
médiane étroite est un artefact de l'échelle, pas un signal fragile.
NO-COORD : X_DECOY, inerte sur métrique VIVANTE (intacte médiane ~0.74, ablée ~0.74 ; nocoord_alive=True,
specificity_control = pass). Donc la coordination LIT causalement la perception de la cible — arête
`language → perception` gravée dans `data/agi_taxonomy/demands.json`, validée par `check_agi_taxonomy`.
`functional_aliasing = "n/a"` (ablation d'entrée, pas de fuite de substrat) justifié par le contrôle de
demande. Accuracies complètes persistées dans `results/sp2_edge_accuracies.json`, régénérées par un appel
DIRECT et bloquant à `run_perception_coordination_demand_probe` (le point d'entrée calibré, pas le pilote
de secours) — reproduit à l'identique (mêmes tableaux, `_train_and_eval` est déterministe par seed).

## Portée (bornée)
Proxy hors-monde (jeu de Lewis), pas la biosphère. Une seule arête ; les autres (perception→memory, …) sont
des itérations ultérieures. Coût borné (smoke + run n=12 plafonné, accuracies persistées
`results/sp2_edge_accuracies.json`).

## Ce que ça débloque
Le graphe AGI-Taxonomy n'est plus vide : première arête MESURÉE, opposable au validateur SP-1. Le pipeline
« mesurer une arête par ablation + garde de spécificité → écrire une arête valide » est prouvé de bout en bout.
Cf. `docs/superpowers/specs/2026-07-24-sp2-first-measured-edge-design.md`.
