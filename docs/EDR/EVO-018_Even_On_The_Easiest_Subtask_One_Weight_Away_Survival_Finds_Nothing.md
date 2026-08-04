---
id: EDR-EVO-018
type: EDR
title: "Même sur la sous-tâche la PLUS FACILE — un seul poids, ×2.4 de durée de vie — la survie seule ne trouve rien : le hedge est fermé"
status: active
verdict: CLOSURE_HOLDS_ON_THE_EASIEST_TARGET
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-017]
---

## Question

[[EDR-EVO-016]] et [[EDR-EVO-017]] portaient tous deux le **même hedge** : la lecture y passe par un
`argmax` à 8 voies — la sous-tâche DURE au sens d'[[EDR-EVO-007]] — et un **seuil de signe** serait plus
facile à découvrir, sans avoir été testé sous survie seule. **Ce record teste ce hedge**, c'est-à-dire
l'endroit le plus probable où l'énoncé de clôture casse. Règle scellée : `EVO-018.json`.

## Méthode

Identique à EVO-016 — `hazard=15`, `W=0`, survie seule, n=12, mêmes graines — **sauf la sous-tâche** :

| | `move` (EVO-016/017) | **`throw` (ici)** |
|---|---|---|
| opérateur de décision | `argmax` à 8 voies | **seuil de signe** |
| câblage minimal | 2 poids, et il faut GAGNER l'argmax | **1 seul poids** |

## Pré-vol — lire paie encore PLUS que sur `move`

| génome | âge médian |
|---|---|
| non-lecteur | **9.0** |
| LECTEUR câblé | **22.0** |

**×2.4 de durée de vie** (contre ×2.15 sur `move`). Le banc peut répondre, et la cible est la plus
atteignable de tout l'arc.

## Résultats

| bras | **lecteurs** | sal max | `raw` méd | âge méd |
|---|---|---|---|---|
| hazard0 | **0/12** | 0.028 | 0.502 | 18 |
| hazard15 | **0/12** | 0.013 | 0.485 | 15 |

**Et ce nul est plus PUR que celui d'EVO-016.** Sur `move`, le hazard poussait `raw` de 0.035 à 0.423 :
il restait un plateau non-cognitif à gravir, et la sélection s'y engouffrait — on pouvait objecter
« elle a pris le gain facile ». Ici, `raw` vaut **0.485-0.502 dans les DEUX bras**, exactement le plafond
d'une politique fixe : un logit de signe constant décroche 50 % sans rien lire. **Il n'y a aucun gain
intermédiaire à ramasser** — la seule façon de progresser est de lire. Le hazard n'a donc rien d'autre
vers quoi pousser, et il ne produit **aucun mouvement** (0.502 → 0.485).

## Verdict

**`CLOSURE_HOLDS_ON_THE_EASIEST_TARGET`** — branche pré-enregistrée « 0/12 ». **Le hedge d'EVO-016/017 est
fermé et l'énoncé de clôture se renforce.**

Récapitulatif de ce qui a été offert à la sélection, et refusé :

| condition | valeur mesurée |
|---|---|
| la lecture PAIE | **×2.4** de durée de vie |
| la capacité est ATTEIGNABLE | **1 seul poids** |
| l'opérateur de décision est le plus SIMPLE | seuil de signe, pas `argmax` |
| aucun plateau non-cognitif à gravir | `raw` déjà à 0.5 sans lire |
| la sélection est DÉMONTRÉE capable | EVO-016 : elle déplace `raw` de 0.035 à 0.423 |
| **issue** | **0/12** |

Toutes les échappatoires sont épuisées. Ce n'est ni l'objectif, ni la récompense, ni l'atteignabilité, ni
la difficulté de la cible, ni l'inertie de la sélection. **C'est le tirage** : `add_connection` doit tomber
sur une arête précise parmi ~11 000, et [[EDR-EVO-014]]/[[EDR-EVO-017]] ont montré qu'aucune méthode de
recherche testable ici ne change cette probabilité.

## Portée (hedges)

* n=12 par bras borne une FRÉQUENCE (borne sup ~22 %), pas une impossibilité.
* 35 ères. Un horizon beaucoup plus long reste non testé — mais le tirage étant à ~3/11 000 par
  `add_connection`, l'espérance ne devient favorable qu'à des budgets d'un autre ordre.
* Le hazard vient d'une SOUS-CLASSE du monde : on teste « un monde où lire paie », pas le monde de prod.
* Le `raw` à 0.5 sans lecture est spécifique aux sous-tâches en seuil de signe (50 % par construction) ;
  c'est ce qui rend le nul pur, et c'est aussi ce qui empêche de lire `raw` comme un progrès partiel.

Converge [[EDR-EVO-014]], [[EDR-EVO-016]], [[EDR-EVO-017]], REF-EXPERIMENT-PREFLIGHT.
