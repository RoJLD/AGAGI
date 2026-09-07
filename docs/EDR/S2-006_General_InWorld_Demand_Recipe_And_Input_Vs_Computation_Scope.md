---
id: EDR-S2-006
type: EDR
title: "Le théorème général de la demande in-world (3 conditions) + la frontière input/calcul de l'instrument"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
foundational: true
corrected_by: [EDR-AUDIT-001]
---

> ⚠️ **DÉRIVATION CORRIGÉE le 2026-07-21 — [[EDR-AUDIT-001]]. Record `foundational`, à lire avec ceci.**
> **Deux failles dans la démonstration** :
> 1. **La prémisse « le corps de la biosphère est SUFFISANT » n'a jamais été mesurée.** Dans le jouet,
>    « corps suffisant » signifie `body_gain > metab` → survie INFINIE, plafond 300/300. Dans la
>    biosphère, le champion **meurt à 27.5 ticks sur 200** (chiffre de S2-003, ~14 % du cap) : son corps
>    n'est pas suffisant au sens du théorème. Le transfert est une **analogie**, pas une mesure — classe
>    **E8** et [[causal-chain-does-not-cross-populations]].
> 2. **L'exclusion causale « ce n'est ni le substrat ni le crédit » est tirée d'un nul in-world SANS
>    contrôle positif in-world** — la forme exacte de l'erreur de WARM-002.
>
> ⚠️ **TROISIÈME faille, trouvée le 2026-09-07 (revue adversariale du gap S6) : la moitié NÉCESSITÉ du
> théorème est DÉFINITIONNELLE, pas mesurée.** Vérifié en forme close sur le code, sans aucun run :
> `survive` fait `E += gain - metab` puis `if E <= 0: return t+1`, sinon `return ticks`
> (`cognitive_demand_world_probe.py:60-74`) — la survie ne dépend donc que du **SIGNE du gain net**,
> c'est une **métrique-SEUIL**, pas une mesure graduée. Et `fit_policy` part de `W = zeros`,
> `b = zeros` (`:81-82`) avec une acceptation **STRICTE** `sc > best` (`:92`) : dans toute cellule à
> corps suffisant (`body_gain > metab`), la politique INITIALE survit déjà au plafond 300/300, donc
> **aucune candidate n'est jamais acceptée** — `|W| = 0.0000` est l'**init**, pas un résultat, et
> l'ablation y est inerte PAR CONSTRUCTION. Une cellule « nulle » de ce théorème ne pouvait pas rendre
> autre chose que NEUTRE : c'est la classe **E1** (un contrôle qui ne peut pas échouer), appliquée à la
> moitié « nécessité ».
>
> **Ce qui TIENT** : la moitié SUFFISANCE (la cellule à 3 conditions rend SENSIBLE, ratio ~10×) — un
> positif ne peut pas être fabriqué par cette identité. **Ce qui NE TIENT PLUS** : « chaque condition
> est NÉCESSAIRE, mesuré sur cinq modalités » — les cellules nulles sont des définitions. **Règle qui en
> sort, réutilisable** : une cellule NULLE se déclare avec le plancher « privé de X SEULEMENT » ; **si
> ce plancher égale l'intact, la cellule est une définition, pas une mesure.**
>
> Conséquence sur le corollaire in-world (« NEUTRE par construction, ni substrat ni crédit ») : il perd
> sa base mesurée — le champion à 27,5/200 n'est de toute façon pas dans le régime « corps suffisant »
> (faille 1). L'explication du gap proxy 9 / in-world 0 revient donc au **CHEMIN** ([[EDR-LOCK-001]],
> [[EDR-EVO-016]]), pas au contenu de l'objectif. Le design qui MESURERAIT la nécessité (taux de repli
> `k(σ)` sous init non nulle, pur numpy) est au backlog, gap S6.
>
> S'y ajoute l'héritage : les conditions 1 et 3 du « théorème » viennent de cellules de S2-004/005 où le
> bras de référence est à 300/300 avec `W` **gelé à son initialisation** (voir le bandeau de S2-004).
>
> **⚠️ CE QUI N'EST PAS RÉFUTÉ POUR AUTANT** : la conclusion large — la survie et la fitness n'ont pas de
> contenu cognitif dans la biosphère par défaut — a un appui **INDÉPENDANT** : l'arc cognition-vs-corps,
> où `champion_body` (génome du champion + actions ALÉATOIRES) survit ~4× le plancher. C'est la
> **dérivation** de ce record qui est fautive, pas nécessairement son verdict. Réfuter un raisonnement
> n'est pas réfuter sa conclusion.
>
> **⚠️⚠️ AMENDÉ le même jour, après avoir mesuré ce filet de sécurité — [[EDR-S2-012]].** La phrase
> ci-dessus disait « verdict BODY unanime **5/5 mondes** » : c'est **4 mondes au plus**, car
> `IndustrialWorld` est un clone de `Biosphere3D` (compteur `pollution` jamais lu par la biologie) et
> `stoneage` **EST** `Biosphere3D` — l'unanimité comptait deux fois la même simulation. Par ailleurs la
> moitié « la cognition n'apporte rien » de `champion_body` est elle aussi un **nul in-world sans
> contrôle positif in-world** — le défaut même qu'elle était censée rattraper ici. **L'appui reste réel
> dans sa direction, mais il est plus faible qu'annoncé.** *Un filet de sécurité qu'on n'a pas vérifié
> n'en est pas un.*

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
