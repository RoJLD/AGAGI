---
id: EDR-S2-006
type: EDR
title: "Le théorème général de la demande in-world (3 conditions) + la frontière input/calcul de l'instrument"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
foundational: true
---

## Synthèse (clôt l'arc « recette » S2-003→004→005)
S2-003 (négatif) : la survie in-world est corps-driven, sans contenu cognitif → tout test in-world NEUTRE
par construction. S2-004 (perception) et S2-005 (mémoire) donnent la contrepartie constructive. Cet EDR
généralise en un THÉORÈME + une frontière de portée de l'instrument.

## Théorème général de la demande in-world
Un objectif de SURVIE in-world exige une capacité X ssi TROIS conditions nécessaires tiennent ENSEMBLE :

1. **Corps INSUFFISANT** (`body_gain < metab`) — sinon la survie plafonne sur le phénotype métabolique et
   X est un leurre (NEUTRE). C'est le mécanisme de S2-003 / de la biosphère (le champion survit par le corps).
2. **Demande STRUCTURÉE par X** — l'information/le calcul porteur de survie EXIGE X : l'obs (perception),
   le passé (mémoire, rappel différé), la coordination (communication), le futur (anticipation), le
   chaînage (composition). Sans cette structure, X n'a rien à faire.
3. **Devise de SURVIE** — le succès de X paie dans la devise SÉLECTIONNÉE (énergie de survie), pas une
   devise séparée (fitness/points → NEUTRE quelle que soit la magnitude, cf. s2-cognition-body).

Confirmé sur DEUX modalités disjointes à vérité-terrain (perception S2-004, mémoire S2-005) : la cellule
qui satisfait les 3 conditions est SENSIBLE (ratio ~10×), toutes les autres NEUTRES.

## Frontière de portée de l'instrument : INPUT vs CALCUL
Le demand-marker ablate un **INPUT** (within-subject). Il couvre donc proprement les capacités-INPUT —
perception (ablate l'obs), mémoire (ablate l'état mémoire), communication (ablate le canal) : chacune est
un input ablatable. Les capacités-CALCUL — anticipation (forward-model), composition (chaînage) — ne sont
PAS des inputs mais des computations : mesurer LEUR demande exige une **ablation de MODULE** (couper le
calcul), un instrument distinct et plus lourd. C'est exactement le territoire de G4/PLAN (forward-model)
et G2/COS (gate compositionnel). **L'arc input-ablation est complet ; l'arc module-ablation reste ouvert.**

Corroborant : le poids appris |W| est nécessaire mais PAS suffisant (S2-005 : |W|=0.909 alors que NEUTRE) —
seule l'ablation (input OU module) tranche causalement.

## Corollaire — pourquoi « proxy 9 / in-world 0 »
La biosphère actuelle échoue les TROIS conditions pour la cognition : (1) le corps est SUFFISANT (le
champion survit seul, S2-002/003 + s2-cognition-body) ; (2) les tâches ne sont pas structurées pour
exiger la cognition (la survie ne dépend pas de lire/mémoriser/anticiper) ; (3) quand la cognition opère,
elle ne paie pas en devise de survie (life_score = corps aussi). Donc chaque test cognitif in-world est
NEUTRE PAR CONSTRUCTION — ce n'est ni le substrat ni le crédit, c'est l'OBJECTIF qui n'a pas de contenu
cognitif. Mécaniquement, ça explique le méta-gap proxy-fort / in-world-neutre.

## Actionnable
Pour rendre G1-G4 in-world MESURABLES : construire un monde biosphère satisfaisant les 3 conditions
(métabolisme rendant le réflexe insuffisant + canal cognitif obs/mémoire-déterminé + payé en énergie).
Alors l'ablation-perception/mémoire du champion y effondrerait la survie (SENSIBLE), et les portes
auraient un gradient de sélection non-nul. Pour G4/G2 : développer l'ablation-MODULE (forward-model, gate).
Converge S2-001..005, MEM-001, REF-DEMAND-MARKER, [[s2-world-demand-thread]], [[within-subject-demand-marker]].
