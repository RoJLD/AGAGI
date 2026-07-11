---
id: LANG-005
type: EDR
title: "Le PLAFOND de compositionnalité (within ~0.54) est le RÉGIME D'OPTIMISATION, PAS la capacité/budget/crédit. Ablation FIXED du within-train : INVARIANT au budget (2× épisodes : 0.547->0.547 exact), à la structure de crédit (per_attr ~ joint), ET à la CAPACITÉ (num_nodes 172->384, nœuds cachés 5->217 = ×43 : 0.547->0.542, plat) -> plafond = équilibre partiel de la co-adaptation REINFORCE 2-politiques à baseline faible (optimum local du jeu), même verrou récurrent 'régime d'optim pas capacité' (H-unif 131/132/133, capacité éliminée 105/110). MAIS capacité ET crédit par-attribut améliorent la GÉNÉRALISATION zéro-shot (0.49->0.57) sans toucher l'accuracy -> levier de systématicité DISTINCT du plafond. Le sweep capacité a RETOURNÉ le diagnostic préliminaire (capacité par élimination = faux)"
status: accepted
gate: null
verdict: COMPOSITIONAL_CEILING_IS_OPTIMIZATION_REGIME_NOT_CAPACITY
---

# LANG-005 : le plafond de compositionnalité est le régime d'optimisation, pas la capacité (Arc 4)

## Contexte

LANG-003/004 : le code compositionnel émerge mais IMPARFAIT (within-train ~0.54, ~0.2 au-dessus de la
chance). Trois causes candidates au plafond : (1) VARIANCE DE CRÉDIT (le retour JOINT crédite symbole_t par
le succès des deux attributs) ; (2) BUDGET (convergence incomplète) ; (3) CAPACITÉ (substrat LTC — à
num_nodes=172 défaut, I=59+O=108 laissent seulement **5 nœuds cachés**). Question : lequel borne le plafond ?

## Méthode

`tools/compositional_ceiling_probe.py` (étend `run_compositional` : params `credit` ∈ {joint, per_attr} et
`num_nodes`). FIXED (paires figées, M=8, A=3, V=6, 2 seeds).
- **Crédit** : `joint` (retour = fraction d'attributs corrects, crédite les 2 symboles) vs `per_attr`
  (symbole_t/guess_t crédité par la correction de a_t SEULE ; épisodes 1-pas séparés, H réinitialisé).
- **Budget** : 8000 vs 16000 épisodes.
- **Capacité** : num_nodes 172 (5 cachés) → 256 (89) → 384 (217).

## Constat

**Ablation crédit × budget (num_nodes=172) :**

| Crédit | ép | within | zeroshot | topsim |
|---|---|---|---|---|
| joint | 8000 | 0.547 | 0.490 | +0.357 |
| joint | 16000 | 0.547 | 0.500 | +0.333 |
| per_attr | 8000 | 0.505 | 0.542 | +0.261 |
| per_attr | 16000 | 0.531 | 0.594 | +0.287 |

**Sweep capacité (joint, 8000 ép) :**

| num_nodes | cachés | within | zeroshot | topsim |
|---|---|---|---|---|
| 172 | 5 | 0.547 | 0.490 | +0.357 |
| 256 | 89 | 0.536 | 0.552 | +0.340 |
| 384 | 217 | 0.542 | 0.573 | +0.390 |

`VERDICT = COMPOSITIONAL_CEILING_IS_OPTIMIZATION_REGIME_NOT_CAPACITY`.

## Lecture

- **Le plafond de within (~0.54) est INVARIANT aux TROIS leviers.** Budget : 2× épisodes → 0.547→0.547
  (exact). Crédit : per_attr ≈ joint (0.531 vs 0.547). Capacité : ×43 nœuds cachés (5→217) → 0.547→0.542
  (plat). **Aucun ne lève le plafond** → ce n'est ni le budget, ni la variance de crédit, ni la capacité.
- **Le plafond est le RÉGIME D'OPTIMISATION.** Deux politiques (sender, receiver) co-s'adaptent sous
  REINFORCE à baseline faible (moyenne de batch) : le système converge vers un **équilibre partiel du jeu**
  (optimum local), pas une limite de représentation. C'est le verrou RÉCURRENT du projet — « le verrou est le
  régime d'optim / le mécanisme de crédit, PAS la capacité » (binding H-unif 131/132/133 ; capacité réseau
  éliminée comme verrou 105/110 ; SOTA-gap = mécanisme de crédit). Le sweep capacité **RETOURNE** le
  diagnostic préliminaire (« capacité » par élimination était faux : il éliminait budget+crédit et défaussait
  sur la capacité — le bras capacité la réfute aussi).
- **MAIS capacité et crédit par-attribut améliorent la GÉNÉRALISATION, pas l'accuracy.** zeroshot monte avec
  la capacité (0.490 → 0.552 → 0.573) ET avec per_attr (0.490 → 0.594), sans toucher le within. Deux leviers
  indépendants convergent : un substrat plus large / un crédit plus net produisent un code plus SYSTÉMATIQUE
  (transfère mieux aux combos inédits) sous le MÊME plafond d'accuracy. La systématicité (généralisation) et
  l'accuracy (maîtrise) sont des axes DISSOCIÉS : la première dépend de capacité+crédit, la seconde du régime
  d'optim.

## Conséquences

- **Levier pour la compositionnalité PARFAITE = le RÉGIME D'OPTIMISATION, pas un substrat plus gros.** Pistes :
  actor-critic à baseline apprise (critique) au lieu de REINFORCE à baseline-moyenne ; réduction de variance
  (contrôle de variance, récompense par composante déjà testée = insuffisante sur l'accuracy) ; curriculum de
  co-adaptation (geler une politique, entraîner l'autre par tours). C'est la même reco que la migration moteur
  (meilleur optimiseur), ciblée : **le crédit/optimiseur, pas la taille**.
- **Leçon in-world** : (1) pour la MAÎTRISE (accuracy), améliorer le CRÉDIT (critique/variance), pas empiler
  des neurones ; (2) pour la GÉNÉRALISATION/systématicité, la capacité et le crédit par-composante PAIENT.
  Deux axes à optimiser séparément.
- **Clôt le backlog « compositionnalité parfaite »** de l'axe langage : le plafond n'est pas franchissable par
  budget/capacité — c'est un problème d'optimiseur (hors périmètre du proxy ; = la migration moteur).
- Relié : `REF-LTC -A_ADOPTER_POUR-> LANG-005`. Prolonge [[lang-referential-capability]] (001-004) et scelle
  la thèse [[sota-gap-substrate]] (verrou = crédit/optim, pas capacité) sur l'axe langage.

## Caveats

1. 2 seeds, M=8, A=3 : le ROBUSTE = l'INVARIANCE du within aux 3 leviers (surtout budget 0.547→0.547 exact,
   capacité plate malgré ×43 cachés) + le trend monotone zeroshot(capacité). Décimales bruitées.
2. « Régime d'optimisation » est un diagnostic par TRIANGULATION (les 3 autres causes réfutées) + cohérence
   avec le verrou récurrent ; non prouvé DIRECTEMENT (un banc actor-critic vs REINFORCE le confirmerait —
   backlog, = migration moteur, hors proxy).
3. num_nodes monte les nœuds CACHÉS mais garde I/O et le crédit tronqué 1-pas de `learn_episode` : on teste la
   capacité de représentation, pas la profondeur de crédit temporel (qui exigerait BPTT, EDR-146).
4. Proxy synthétique hors biosphère (même bornage que 001-004) : le vrai test = in-world (087).
