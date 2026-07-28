---
id: EDR-EVO-008
type: EDR
title: "La lecture apparaît d'un SAUT mutationnel unique et se maintient ensuite — le verrou est la DÉCOUVERTE, pas la rétention"
status: active
verdict: DISCOVERY_IS_THE_BOTTLENECK_NOT_RETENTION
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-007]
---

## Question

[[EDR-EVO-007]] a rétracté le verdict d'[[EDR-EVO-006]] mais a laissé un **fait sans explication** : le
seed 0 construit un lecteur authentique et reproductible (bascule de `sign(logits[8])` sous `obs[10]`
= 1.000, quatre reproductions bit pour bit) là où 11 autres lignées n'en construisent aucune, et où le
crédit partiel comme la facilité de la tâche ont été éliminés comme explications.

> **QUAND et COMMENT ce circuit apparaît-il dans la lignée ?**

La forme de la courbe départage deux mondes incompatibles : un **saut** signifierait un événement
mutationnel unique — auquel cas il n'y a pas de mécanisme à chercher, seulement un TAUX ; une **montée**
signifierait qu'un gradient existait dans cette lignée-là, et rouvrirait une piste mécaniste. Règle de
lecture scellée avant le run : `docs/preregistrations/EVO-008.json`.

## Méthode

Rejouer l'évolution des seeds 0 (lecteur), 1 et 2 (non-lecteurs) en sondant le **meilleur génome à chaque
ère** avec `measure_decision_saliency` (instrument calibré). 35 ères, mêmes graines, même monde, sous bail
`kuzu` et plafond de coût (garde E13).

## Résultats

| seed | courbe de saillance par ère | verdict |
|---|---|---|
| **0** (lecteur) | 0.00 ×6 puis **1.00 dès l'ère 7**, maintenu **28/29** ères | **SAUT** |
| 1 (non-lecteur) | 0.00 sur les 35 ères | plat |
| 2 (non-lecteur) | 0.00 sur les 35 ères | plat |

* **SAUT, sans ambiguïté** : la saillance passe de `0.00` (ère 6) à `1.00` (ère 7). Aucune valeur
  intermédiaire, dans aucune ère, dans aucun seed. Il n'y a pas de gradient — il y a un événement discret.
* **RETENUE** : une fois apparu, le circuit est conservé sur **28 ères sur 29** (un seul décrochage,
  ère 26). La sélection sous objectif cognitif fait donc parfaitement son travail de conservation.
* **Contrôles plats** : les deux lignées non-lectrices restent à 0.00 sur 35 ères — la sonde par-ère
  n'est pas bruitée, et la courbe du seed 0 est donc lisible.

## Verdict

**`DISCOVERY_IS_THE_BOTTLENECK_NOT_RETENTION`** — et ça reclasse tout l'arc EVO.

L'objectif cognitif **sait retenir** la lecture (28/29 ères) ; ce qu'il ne sait pas faire, c'est la
**créer**. Le verrou n'est donc ni la forme de l'objectif, ni son poids ([[EDR-EVO-005]] : dose-réponse
monotone jusqu'au plafond non-cognitif), ni sa granularité ([[EDR-EVO-007]] : 0/12 avec crédit partiel) —
c'est l'**opérateur de variation**, c'est-à-dire la probabilité que la mutation produise le câblage
entrée→sortie.

Ça explique rétrospectivement le négatif d'EVO-007 **sans hypothèse supplémentaire** : le crédit partiel
sert à gravir un gradient, or il n'y a pas de gradient à gravir. On ne rend pas un tirage de dé plus
fréquent en lissant la récompense.

**Prochain pas, directement testable** : si la découverte est le verrou, augmenter l'exploration
mutationnelle (taux de mutation des poids, biais vers les arêtes entrée→sortie) doit augmenter le TAUX de
découverte. À n=12, passer de 1/12 à une fraction nettement supérieure serait décisif — et c'est la
première prédiction quantitative de cet arc qui porte sur l'optimiseur plutôt que sur l'objectif.

## Portée (hedges)

* **L'émergence est tracée sur UNE lignée** (la seule qui découvre). La forme « saut » est donc n=1 :
  elle décrit comment ça s'est passé cette fois, pas comment ça se passe en général. La RÉTENTION
  (28/29) est également intra-lignée.
* Les contrôles (seeds 1-2) établissent que la sonde ne fabrique pas de pics, pas que toutes les lignées
  non-lectrices se ressemblent.
* La saillance est mesurée sur la sous-tâche `throw` (celle qui est apprise) ; l'apparition d'un circuit
  sur une AUTRE sortie ne serait pas vue par cette courbe.
* Le taux de découverte (1/12 sur 35 ères) est estimé sur un seul jeu de sous-tâches et un seul régime de
  mutation ; il n'a pas d'intervalle de confiance utile à ce n.

## ⚠️ Ce record a failli être un artefact — et c'est le cas-témoin qui l'a sauvé

La **première** version de la sonde par-ère rendait une courbe **PLATE pour le seed 0**, c'est-à-dire
« le lecteur apparaît de nulle part ». C'était faux, et lisible comme un résultat.

Cause : `measure_decision_saliency` appelait `np.random.seed(...)`, ce qui **réécrit le RNG global**.
Inoffensif après un run ; destructeur intercalé ENTRE deux ères, où la sonde détourne l'évolution qu'elle
est censée OBSERVER. Je n'ai pas rejoué la lignée du seed 0 : j'en ai fabriqué une autre à chaque ère.
C'est la classe **E5** (aliasing — l'acte de mesurer mute le système mesuré) transposée de la mémoire à
l'**état global**.

Ce qui l'a révélé n'est ni une relecture ni une intuition : c'est d'avoir mis dans le dispositif un cas à
**réponse connue** — le seed 0 DEVAIT sortir lecteur. Sans ce témoin, la courbe plate partait au record.

**Garde livrée dans la même passe** : l'instrument sauvegarde et restaure l'état du RNG (valeur mesurée
inchangée, flux de l'appelant intact), avec deux tests gelés — l'un vérifie qu'aucune trace n'est laissée,
l'autre que la restauration n'altère pas la mesure. Non-régression vérifiée : le résultat publié
d'EVO-006 (raw 0.612 / throw 0.925 / saillance 1.000) reproduit à l'identique après le correctif.

Converge [[EDR-EVO-005]], [[EDR-EVO-006]] (rétracté), [[EDR-EVO-007]], REF-EXPERIMENT-PREFLIGHT.
