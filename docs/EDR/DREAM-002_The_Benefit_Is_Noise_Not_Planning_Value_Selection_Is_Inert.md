---
id: EDR-DREAM-002
type: EDR
title: "Le bénéfice du « rêve » est du BRUIT, pas de la planification : un rêve FACTICE (branche gardée au hasard) reproduit 100 % de l'effet — la sélection-par-valeur est INERTE"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
corrects: [EDR-095]
---

## Question
[[EDR-DREAM-001]] a établi que forcer le rêve **améliore** la survie des fondateurs (+77 %) et multiplie
la reproduction par 15.7 — l'inverse de ce que publiait EDR-095. Restait le mécanisme.

La lecture du code donne l'hypothèse : le rêve explore K branches bruitées de l'état caché `H`, lit le
**logit de valeur** (nœud 28) de chacune, et **remplace `H` par la meilleure** (`mamba_agent` ~L590-604).
C'est une montée de gradient sur la valeur prédite. Hypothèse : *le bénéfice vient de cette sélection.*

Mais le rêve fait **deux choses simultanément** — il BRUITE `H`, et il SÉLECTIONNE. Elles sont séparables.

## Méthode — ablation within-subject du MÉCANISME
Bras **`sham8`** (`MambaBatchModel.DREAM_SHAM`, défaut OFF = prod inchangée) : **mêmes K branches, même
bruit, même coût de calcul, même lecture du logit de valeur** — mais la branche conservée est tirée
**au hasard** (échantillonnage par réservoir : garde la branche *k* avec proba 1/(k+1)). Seul le
CRITÈRE de sélection change.

Prédiction falsifiable posée avant le run : si le bénéfice vient de la sélection, `sham` retombe sur
`off` ; s'il vient du bruit, `sham` reproduit `dream`.

3 bras × 12 seeds, `stoneage`, organe ON 100 %, sweet spot, 25 agents, 80 ticks, K=8.
Artefact : `results/dream_mechanism_3arms.json`.

## Résultats

| métrique | contraste | médianes | ratio | favorables | `wilcoxon_p` |
|---|---|---|---|---|---|
| âge fondateurs | off → dream8 | 35.5 → 54.5 | 1.54 | 8/12 | 0.1467 |
| âge fondateurs | off → **sham8** | 35.5 → **55.5** | **1.56** | **10/12** | **0.0135** |
| âge fondateurs | **sham8 → dream8** | 55.5 → 54.5 | **0.98** | 4/12 | 0.3505 |
| `n_lived` | off → dream8 | 56.5 → 756 | 13.38 | 12/12 | 0.0025 |
| `n_lived` | off → **sham8** | 56.5 → **1057** | **18.71** | **12/12** | **0.0025** |
| `n_lived` | **sham8 → dream8** | 1057 → 756 | **0.72** | 5/12 | 0.0917 |
| proies mangées | off → dream8 | 73 → 250 | 3.42 | 12/12 | 0.0025 |
| proies mangées | off → **sham8** | 73 → **299.5** | **4.10** | 11/12 | 0.0033 |
| proies mangées | **sham8 → dream8** | 299.5 → 250 | 0.83 | 3/12 | 0.0414 |

## Verdict
**`THE_BENEFIT_IS_NOISE_NOT_PLANNING__VALUE_SELECTION_IS_INERT`**

**Le bras factice reproduit la TOTALITÉ du bénéfice.** Il ne sélectionne rien et fait aussi bien sur les
trois métriques. Le contraste direct `sham → dream` est **plat partout** : 4/12, 5/12, 3/12.

**La sélection-par-valeur ne contribue RIEN de détectable.** Ce qui agit, c'est la **perturbation
stochastique de l'état récurrent** — le « rêve » fonctionne comme du bruit d'exploration, pas comme de
la planification. L'hypothèse de montée de gradient sur la valeur est **réfutée**.

> ⚠️ **Une lecture que je m'interdis.** `preys` sur `sham → dream` donne `p = 0.0414` en faveur du
> factice, ce qui suggérerait que sélectionner est *activement nuisible*. Avec **15 comparaisons**, ça
> ne survit à aucune correction de multiplicité. Je ne l'affirme pas — c'est le reproche exact fait à
> `champion_body` ([[EDR-S2-012]], volet `life_score` qui tombe à 2/5 sous Holm).
> La conclusion tient sans lui : elle repose sur un **motif** (sham ≥ dream sur 3 métriques, contraste
> direct nul 3 fois) et non sur une valeur-p isolée.

## Fil EXPLORATION (thèse EDR-014) — NON TESTABLE dans ce régime
EDR-095 rejetait l'organe MCTS comme levier d'exploration ; [[EDR-DREAM-001]] a fait sauter le motif de
ce rejet. Le test direct était donc possible — `altars_solved` / `spears_crafted` étaient déjà portés
par l'agent, simplement jamais remontés par la sonde. Remontés ici :

**`altars_solved` = 0.0 dans les TROIS bras, 0/12 seeds.** Aucun autel résolu par personne, jamais.
`spears_crafted` : médianes 1 → 0, comptes de 0 à 3 par ère — au plancher.

**La métrique ne peut pas produire les deux issues** : c'est `assert_not_degenerate` qui se déclenche
sur ma propre expérience. La thèse d'EDR-014 n'est donc **ni confirmée ni réfutée — elle est
INTESTABLE dans ce régime**. Converge avec [[world-floor-survivability-gate]] (l'autel stoneage est du
code mort pondéré 0.6 ; l'apex s'atteint par coopération, pas par l'outil). La tester exigerait un monde
où les autels sont effectivement résolubles.

## Conséquences
* **Pour l'organe MCTS** : EDR-095 le rejetait pour la mauvaise raison (« planifier est un luxe » —
  réfuté par DREAM-001). Ce record fournit la bonne : **sa partie PLANIFICATION est inerte**. Le rejet
  de l'approche A tient donc, mais sur un fondement entièrement différent — et il ne dit toujours rien
  de l'exploration.
* **Converge avec le fil planification du dépôt** : [[planner-depth1-refuted]] (la profondeur n'était
  pas le levier) et PLAN-001 (c'est la FORME du modèle — bilinéaire vs linéaire — qui décide, pas la
  recherche). Ici, la recherche ne décide rien non plus ; seul le bruit agit.
* **Piste ouverte, désormais bien posée** : si un bruit stochastique sur `H` vaut +56 % de survie et
  ×18.7 de reproduction, **c'est le BRUIT qu'il faut étudier comme levier**, pas le planificateur. Quelle
  amplitude ? quel schéma ? est-ce de l'échappement d'attracteur, ou du recuit ?

## Leçons (registre des erreurs)
* **Un mécanisme plausible lu dans le code n'est pas un mécanisme mesuré.** L'hypothèse « montée de
  gradient sur la valeur » venait d'une lecture correcte du code — et elle est fausse. Le code dit ce
  qui est CALCULÉ, pas ce qui est CAUSAL.
* **Une intervention qui fait deux choses doit être ablatée composante par composante.** Le rêve
  bruitait ET sélectionnait ; il a fallu un bras appariant tout sauf le critère de sélection pour
  attribuer l'effet. Sans lui, on aurait crédité la planification d'un résultat qui appartient au bruit.
* **La métrique d'exploration est dégénérée, et il fallait le mesurer pour le savoir** — le smoke à
  1 seed l'a montré avant que 60 minutes soient dépensées à interpréter des zéros.

Converge [[EDR-DREAM-001]], [[EDR-095]], [[EDR-094]], [[planner-depth1-refuted]],
[[world-floor-survivability-gate]], REF-EXPERIMENT-PREFLIGHT.
