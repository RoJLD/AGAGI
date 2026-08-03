---
id: EDR-EVO-012
type: EDR
title: "Le POINT DE FONCTIONNEMENT sépare le lecteur du porteur d'arête : R = |w_signal| / |logit| — 20 chez le lecteur, 0.01-0.07 chez les porteurs"
status: active
verdict: OPERATING_POINT_RATIO_SEPARATES_READER_FROM_CARRIER
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-010]
---

## Question

[[EDR-EVO-010]] laisse un fait inexpliqué : **4 champions sur 4 PORTENT l'arête lectrice sans lire**, et
élaguer les entrées concurrentes ne récupère que 8 % de l'effet. Qu'est-ce qui distingue un **porteur**
d'un **lecteur** ? Règle scellée avant la mesure : `docs/preregistrations/EVO-012.json`.

**Hypothèse pré-enregistrée — le POINT DE FONCTIONNEMENT.** La décision est `sign(logits[8])`. Pour qu'une
perturbation d'amplitude `w` fasse basculer le signe, il faut `|logit| < w`. Ce n'est pas une hypothèse
statistique mais une **nécessité arithmétique** : la mesure ne fait que dire dans quel régime chacun se
trouve.

## Résultats

Mesure purement mécaniste (passages avant + inspection de `W`) — n'utilise NI le harnais de survie NI les
compteurs du monde, tous deux défaillants ([[EDR-EVO-011]] arrêté au pré-vol).

| génome | \|w\| arête | **\|logit\| médian** | **R = w/\|logit\|** | bascule |
|---|---|---|---|---|
| **LECTEUR** (baseline seed 0) | 0.144 | **0.007** | **≈ 20** | **1.000** |
| porteur `wake20` s0 | 0.120 | 10.25 | 0.012 | 0.000 |
| porteur `wake20` s2 | 0.453 | 12.53 | 0.036 | 0.008 |
| porteur `wake20` s3 | 0.661 | 9.00 | 0.073 | 0.000 |

**Séparation de ~1500× sur le point de fonctionnement, sans recouvrement**, et dans le sens
contre-intuitif : le lecteur a l'arête la **plus faible** du lot (0.144 contre 0.45 et 0.66). Le lecteur
opère **exactement au seuil de décision** ; les porteurs en sont très loin. `frac<1` (fraction des ticks
où le logit est à portée du signal) : **1.000** pour le lecteur, 0.20-0.26 pour les porteurs.

## Ce que ça reclasse

L'« exclusivité de la sortie » d'EVO-010 n'était qu'un **proxy** : 70 entrées concurrentes éloignent le
logit du seuil, mais c'est la **distance au seuil** qui décide, pas le nombre de voisins. Ça explique
enfin le 8 % de l'élagage — couper les concurrents rapproche du seuil sans y amener.

**Et le même ratio explique EVO-009 ET EVO-010 d'un seul coup**, parce que R est **invariant d'échelle**
(multiplier toutes les entrées du nœud ne change pas R) :

| | effet sur R | issue |
|---|---|---|
| [[EDR-EVO-009]] biais CIBLÉ | numérateur ↑, dénominateur ~ | R ↑ → **12/12 lecteurs** |
| [[EDR-EVO-010]] VOLUME | numérateur ↑ **et** dénominateur ↑ | R ~ → **0/12** |

Le levier ne peut donc pas être un redimensionnement : il doit augmenter le poids du signal **sans**
augmenter le reste.

## ⚠️ Ce qui n'est PAS établi : le test causal a ÉCHOUÉ À MANIPULER

Tentative de centrer le logit d'un porteur en retranchant son biais médian via le canal constant
`obs[6] = 1` :

| seed | logit avant | logit après | bascule |
|---|---|---|---|
| s0 | +10.25 | +5.36 | 0.000 |
| s2 | +12.53 | +12.08 | 0.000 |
| s3 | +9.00 | **+10.86** (monte) | 0.000 |

**Le contrôle de manipulation NE PASSE PAS** : l'intervention ne centre pas le logit (un seed le voit même
augmenter), parce que la dynamique récurrente — accumulation de `H`, activation avec `f(0) ≠ 0`, seuils —
ne traduit pas 1:1 un poids ajouté en valeur de sortie.

Ce n'est donc **pas une réfutation du mécanisme, mais un échec d'implémentation du levier**. Écrire
« centrer ne sert à rien » serait faux : une manipulation qui ne bouge pas sa cible ne teste rien.

## Verdict

**`OPERATING_POINT_RATIO_SEPARATES_READER_FROM_CARRIER`**, avec sa borne explicite :

1. **Fortement indiqué** : le ratio R sépare lecteur et porteurs de ~1500×, sans recouvrement, et il
   repose sur une **nécessité arithmétique** (`|logit| < w` est requis pour basculer un signe) — pas
   seulement sur une corrélation. Il unifie EVO-009 (R ↑) et EVO-010 (R ~) sans hypothèse ajoutée.
2. **PAS causalement établi** : aucune intervention n'a réussi à manipuler R. La seule tentée échoue son
   contrôle de manipulation.
3. **Levier prédit, et il est agnostique** : augmenter R en ajoutant du poids de signal **sans** ajouter
   d'entrées concurrentes. C'est structurellement ce que fait EVO-009 ; reste à le formuler sans
   connaissance de la tâche — piste : contraindre le fan-in par sortie **pendant** l'évolution, plutôt que
   d'ajouter des arêtes partout.

## Portée (hedges)

* **n = 1 lecteur contre 3 porteurs.** L'écart est énorme et l'argument arithmétique est général, mais un
  seul lecteur a été disséqué — c'est le seul dont on dispose ([[EDR-EVO-007]] : 1/12).
* Les porteurs viennent tous du bras `wake20` : le régime dense pourrait produire de grands logits par une
  voie sans rapport avec le nombre d'entrées. Un porteur issu du régime BASELINE n'a pas été disséqué.
* `frac<1` utilise un seuil de 1.0 arbitraire ; le seuil pertinent est `|w|`, qui varie par génome. La
  colonne est indicative, pas load-bearing.
* Aucune mesure de survie ici : ce record porte sur le MÉCANISME de la lecture, pas sur son utilité.

Converge [[EDR-EVO-008]], [[EDR-EVO-009]], [[EDR-EVO-010]], REF-EXPERIMENT-PREFLIGHT.
