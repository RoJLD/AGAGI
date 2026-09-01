---
id: EDR-EVO-023
type: EDR
title: "La clôture n'est PAS un artefact du défaut d'indices : sans aucune croissance de nœuds, toujours 0/12"
status: active
verdict: CLOSURE_SURVIVES_THE_DEFECT_CREATION_IS_BINDING
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-021]
---

## Question — la plus lourde de l'arc

[[EDR-EVO-021]] a mesuré que `add_node` **désaligne 56 %** des arêtes câblées : il n'ajuste ni
`num_inputs` ni `num_outputs`, donc insérer dans le bloc de sortie re-mappe quelle décision chaque nœud
pilote. Le taux de découverte observé dans tout l'arc est donc un **PRODUIT** : création de l'arête ×
survie au défaut.

> **La conclusion centrale — « le verrou est le TIRAGE » — attribue-t-elle à la RARETÉ ce qui vient en
> fait de la DESTRUCTION par un défaut du code de production ?**

Règle scellée : `EVO-023.json`, lecture **continue** (Fisher calculé par le runner), confond déclaré
avant le run.

## Méthode

2 bras × 12 seeds, sous-tâche `throw`, `hazard=15`, `W=0` (survie seule) — strictement le dispositif
d'[[EDR-EVO-018]]. Seul le taux de croissance change. Plafond de coût **déterministe** en agent-ticks
(garde E13), 0 abandon.

**Le pré-vol a intercepté un levier qui ne levait rien** — et c'est sa 3ᵉ interception de la journée :

| bras | `num_nodes` après 200 mutations |
|---|---|
| témoin (`add_node_rate=0.4`) | 172 → **276** |
| ⛔ 1ʳᵉ version : `add_node_rate=0` seul | 172 → **198** |
| ✅ retenue : `add_node` **et** méso désactivés | 172 → **172** |

`add_node` n'est **pas** la seule voie de croissance : `add_meso_gated_unit`
(`src/seed_ai/mutation.py:188`) fait **deux `np.insert` de plus**, avec le même décalage d'indices.
« Désactiver `add_node` » sonnait comme une manipulation atomique — elle ne l'était pas. Sans le contrôle
scellé, j'aurais comparé deux bras qui croissent tous les deux et conclu « pas d'effet » pour la mauvaise
raison. **Conséquence rétroactive : le défaut d'indices est plus large qu'`add_node`.**

## Résultats

DV primaire, telle que scellée : `measure_decision_saliency` sur `obs[5] → logits[8]`, seuil 0.5 — la
colonne « sal max » ci-dessous en est le maximum par bras.

| bras | **lecteurs** | sal max | `raw` méd | `N` méd | abandons |
|---|---|---|---|---|---|
| témoin (croissance) | **0/12** | 0.013 | 0.485 | 178 | 0 |
| **sans croissance** | **0/12** | 0.000 | 0.516 | **172** | 0 |

**Fisher exact bilatéral : p = 1.000.**

## Verdict

**`CLOSURE_SURVIVES_THE_DEFECT_CREATION_IS_BINDING`**

**La clôture d'[[EDR-EVO-018]] n'est pas un artefact.** En supprimant *toute* croissance de nœuds — donc
toute possibilité de désalignement — on obtient **exactement zéro lecteur**, comme le témoin.

Les deux composantes du verrou sont réelles, mais **une seule est contraignante** :

| composante | mesurée | contraignante ? |
|---|---|---|
| **création** de l'arête (~3 sur 11 000, [[EDR-EVO-014]]) | oui | **OUI** |
| **destruction** par décalage d'indices (56 %, [[EDR-EVO-021]]) | oui | **non** |

On ne peut pas détruire ce qui n'apparaît pas. La fragilité existe, elle ne mord pas — parce que l'arête
n'est presque jamais créée en amont. **L'énoncé s'affine plutôt qu'il ne s'affaiblit : le verrou est la
CRÉATION, pas la conservation.**

⚠️ **Ça ne disculpe PAS le défaut.** Il reste une dette de production réelle (backlog), et il redeviendra
contraignant dès qu'un levier fera monter le taux de création — c'est-à-dire exactement dans le régime
où l'on voudrait qu'il ne nuise pas.

## Portée (hedges)

* **n=12 par bras. Puissance déclarée AVANT le run** : 40 % contre 0 % est détectable (p≈0.04), 17 %
  contre 0 % ne l'est pas (p≈0.48). Ce run peut confirmer un effet FORT ; il ne réfute pas un effet
  faible. Un défaut contribuant marginalement resterait invisible.
* **Le confond déclaré d'avance est devenu sans objet** : supprimer la croissance retire aussi la capacité
  d'ajouter des nœuds cachés, ce qui aurait rendu un POSITIF ambigu. Le résultat étant nul, la question ne
  se pose pas — mais elle se reposera si un futur levier rend ce bras positif.
* Le `raw` médian du bras sans croissance (0.516) dépasse à peine le plafond de politique fixe (0.5) avec
  une saillance de 0.000 : c'est du bruit d'échantillonnage, pas un progrès partiel.
* Mesuré sur la sous-tâche `throw` uniquement. Sur `move` (argmax), non testé.

Converge [[EDR-EVO-014]], [[EDR-EVO-018]], [[EDR-EVO-021]], REF-EXPERIMENT-PREFLIGHT.
