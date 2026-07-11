---
id: PLAN-003
type: EDR
title: "La profondeur de planning AIDE — mais la FIDÉLITÉ du modèle plafonne le gain (G4, complète le diptyque PLAN-001/002). MPC depth-k (receding horizon, énumération des séquences, score = distance MIN au but sur le rollout PRÉDIT) vers des buts jamais vus. Modèle FIDÈLE (parfait/bilinéaire) : profondeur -> +0.20 de succès (0.66->0.85, la profondeur trouve des chemins multi-pas que le depth-1 greedy rate). Modèle BRUITÉ : gain moitié (+0.10) et plafond plus bas (0.74) = l'erreur composée sur le rollout érode les prédictions profondes. Modèle INADÉQUAT (linéaire) : aucun gain, coincé au hasard (0.39) à TOUTE profondeur -> planifier profond ne rachète pas un mauvais modèle. Piège méthodo capté : MPC à coût TERMINAL biaise contre la profondeur (corrigé en min-sur-rollout)"
status: accepted
gate: null
verdict: PLANNING_DEPTH_HELPS_GATED_BY_MODEL_FIDELITY
---

# PLAN-003 : la profondeur de planning aide, plafonnée par la fidélité du modèle (G4)

## Contexte

PLAN-001 (la FORME du modèle détermine le comportement) + PLAN-002 (le modèle est apprenable en ligne sous
couverture) ont établi l'anticipation depth-1. Question naturelle : planifier PLUS profond (depth-k, séquence
d'actions anticipée) aide-t-il ? Résultat classique du model-based RL : avec un modèle IMPARFAIT, chaque pas
de rollout COMPOSE l'erreur → la valeur de la profondeur dépend de la fidélité. On teste l'interaction
profondeur × fidélité.

## Méthode

`tools/planning_depth_probe.py` (pur numpy). Planner depth-k par MPC (receding horizon) : à chaque pas réel,
énumère les séquences d'actions de longueur k, roule le MODÈLE k pas, score = distance **MIN au but sur le
rollout prédit**, exécute la 1ʳᵉ action dans la VRAIE dynamique, re-planifie. Modèles de fidélité
décroissante : `perfect` (dynamique vraie), `bilinear` (ajusté), `bilinear_noisy` (ajusté + bruit de
prédiction σ=0.15), `linear` (ajusté, inadéquat car dynamique action-conditionnée). d=8, K=4, exec=5,
depths 1–4, 4 seeds, buts jamais vus.

**Piège méthodo capté** : la 1ʳᵉ version scorait seulement l'état FINAL du rollout (coût terminal) → même le
modèle parfait se dégradait avec la profondeur (0.66→0.40), car l'objectif est « se rapprocher à UN MOMENT »,
pas « être proche à exactement k pas ». Corrigé en score min-sur-rollout (matche l'objectif).

## Constat

| modèle | k=1 | k=2 | k=3 | k=4 | gain(profondeur) |
|---|---|---|---|---|---|
| perfect | 0.650 | 0.792 | 0.883 | 0.804 | +0.23 |
| bilinear | 0.658 | 0.833 | 0.825 | 0.854 | +0.20 |
| bilinear_noisy | 0.637 | 0.717 | 0.738 | 0.729 | +0.10 |
| linear | 0.325 | 0.371 | 0.392 | 0.350 | +0.07 |

`VERDICT = PLANNING_DEPTH_HELPS_GATED_BY_MODEL_FIDELITY`.

## Lecture

- **La profondeur AIDE beaucoup quand le modèle est fidèle.** Perfect et bilinéaire gagnent +0.20–0.23 de
  succès en passant de depth-1 à depth-3/4 (0.66 → 0.85). La profondeur trouve des chemins MULTI-PAS vers le
  but que le depth-1 greedy rate (il faut parfois s'éloigner d'abord pour contourner l'attracteur).
- **La FIDÉLITÉ plafonne la valeur de la profondeur.** Le modèle bruité gagne MOITIÉ moins (+0.10) et plafonne
  plus bas (0.74 vs 0.85 clean vs 0.88 perfect) : le bruit de prédiction COMPOSE sur le rollout → les
  prédictions profondes deviennent peu fiables, érodant le bénéfice de la profondeur. Le gain de profondeur
  ordonne les modèles par fidélité (bilinéaire +0.20 > bruité +0.10 > linéaire +0.07).
- **Un mauvais modèle est inutile à TOUTE profondeur.** Le linéaire (inadéquat pour une dynamique
  action-conditionnée) reste coincé au hasard (~0.39) quelle que soit k : planifier profond ne rachète PAS un
  modèle fondamentalement faux. La profondeur amplifie un bon modèle, pas un mauvais.

## Conséquences

- **Trilogie G4 close en proxy** : PLAN-001 (forme→comportement) + PLAN-002 (apprenable en ligne sous
  couverture) + PLAN-003 (profondeur utile, plafonnée par la fidélité). L'anticipation instrumentale est une
  capacité atteignable ET améliorable par la profondeur — À CONDITION d'un modèle fidèle (bilinéaire).
- **Reco in-world précise** : accorder la profondeur de planning à la fidélité du modèle appris. Avec un g
  bilinéaire fidèle, planifier depth-3/4 (pas seulement depth-1, réfuté avec le modèle LINÉAIRE en 095/
  planner-depth1) ; avec un modèle bruité/peu appris, rester peu profond (le compounding annule le gain). Ne
  jamais planifier profond sur un mauvais modèle.
- **Réhabilite le planning profond** : le depth-1 linéaire réfuté (PLAN_PERD) n'était pas une condamnation du
  planning profond — avec le BON modèle (bilinéaire), la profondeur est le levier qui débloque le plus de
  compétence. Le verrou était (encore) le MODÈLE, pas la profondeur.
- Relié : `REF-LTC -A_ADOPTER_POUR-> PLAN-003`. Complète [[fil-directeur-agi-gates]] §G4 (PLAN-001/002,
  EDR-193) et [[planner-depth1-refuted]]. Motif [[warm-start-transversal-law]] : capacité débloquée en levant
  le vrai verrou (ici : fidélité du modèle, pas la profondeur ni la capacité).

## Caveats

1. Proxy SYNTHÉTIQUE (dynamique action-conditionnée) hérité de PLAN-001/002 : établit le PRINCIPE
   (profondeur × fidélité), pas la magnitude in-world.
2. Planner par ÉNUMÉRATION exhaustive des séquences (K^k) : exact mais coûteux ; in-world, du shooting
   échantillonné serait nécessaire à grande profondeur (K^k explose). Depths testées ≤4.
3. `bilinear_noisy` = bruit de prédiction INJECTÉ (σ=0.15) comme proxy d'un modèle imparfait ; un vrai modèle
   sous-appris aurait une structure d'erreur différente (biais + variance) — le principe (compounding plafonne
   le gain) tient, la forme exacte de la dégradation varierait.
4. 4 seeds, dynamique contractante ; le ROBUSTE = l'ORDONNANCEMENT (gain croît avec la fidélité, plafond aussi)
   + linéaire coincé au hasard, pas les décimales. Le léger repli de `perfect` à k=4 (0.80 vs 0.88 à k=3) =
   bruit d'échantillon.
