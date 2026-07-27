---
id: PLAN-004
type: EDR
title: "La profondeur de planning ADAPTATIVE (choisie via la fidélité MESURÉE du modèle) égale le succès de la meilleure profondeur fixe à ~2.5× MOINS de calcul (capstone de la trilogie G4 PLAN-001/002/003). L'agent observe le MSE de prédiction 1-pas de son propre modèle (signal gratuit) et règle sa profondeur par seuils gradués. Sur une gamme de fidélités : modèle fidèle -> plan profond (k=4) ; bruité -> mi-profond (k=2, ~même succès à 1/32 du calcul) ; mauvais (linéaire) -> greedy (k=1). Succès adaptatif 0.69 ≈ fixe-max 0.69 >> fixe-1 0.59, calcul -59%. Cas révélateur : sur un mauvais modèle, planifier profond ÉGARE activement (fixe-max 0.37 < adaptatif greedy 0.43) -> l'adaptatif gagne en succès ET en calcul. Politique fidélité->profondeur = décision de conception (seuils gradués, choix robla)"
status: accepted
gate: null
verdict: ADAPTIVE_DEPTH_MATCHES_BEST_SUCCESS_AT_LOWER_COMPUTE
---

# PLAN-004 : profondeur de planning adaptative = même succès, moins de calcul (capstone G4)

## Contexte

Trilogie G4 : PLAN-001 (la FORME du modèle détermine le comportement), PLAN-002 (le modèle est apprenable en
ligne sous couverture), PLAN-003 (la profondeur aide proportionnellement à la fidélité, planifier profond sur
un mauvais modèle GASPILLE du calcul K^k). Capstone : et si l'agent MESURAIT la fidélité de son propre modèle
et réglait sa profondeur en conséquence ? Traduit PLAN-003 en POLITIQUE, directement utile in-world (budget de
calcul fini).

## Méthode

`tools/adaptive_planning_probe.py` (pur numpy). L'agent observe un signal GRATUIT de fidélité : le MSE de
prédiction 1-pas de son modèle vs l'état vrai suivant (il voit s' après avoir agi). Il règle sa profondeur via
`depth_from_fidelity(recent_mse, depth_max)`. **Politique = décision de conception** (choix robla en learning
mode, parmi seuils gradués / gate binaire / continue inverse) → **seuils gradués** : MSE<0.02→k=4 ;
<0.06→k=2 ; <0.12→k=2 ; sinon k=1 (exploite le régime bruité intermédiaire, coupe la profondeur si douteux).
Comparé, sur une gamme de fidélités (parfait, bilinéaire, bilinéaire+bruit ×2, linéaire), à FIXE-1 et
FIXE-max, en succès ET en calcul (rollouts modèle évalués). MPC min-sur-rollout (PLAN-003). d=8, K=4, exec=5,
depth_max=4, 4 seeds.

## Constat

| régime | MSE mesuré | k adaptatif | succ_ada | succ_1 | succ_max | calcul_ada | calcul_max |
|---|---|---|---|---|---|---|---|
| perfect | 0.000 | 4 | 0.854 | 0.654 | 0.829 | 614k | 614k |
| bilinear | 0.013 | 4 | 0.796 | 0.654 | 0.821 | 614k | 614k |
| bilinear_noisy+0.1 | 0.023 | 2 | 0.796 | 0.633 | 0.825 | 19k | 614k |
| bilinear_noisy+0.25 | 0.074 | 2 | 0.608 | 0.575 | 0.596 | 19k | 614k |
| linear | 0.152 | 1 | 0.404 | 0.429 | 0.367 | 2.4k | 614k |

**Global** : succès adaptatif **0.692** ≈ fixe-max **0.687** >> fixe-1 **0.589** ; calcul adaptatif 1.27M vs
fixe-max 3.07M → **économie 59%**. `VERDICT = ADAPTIVE_DEPTH_MATCHES_BEST_SUCCESS_AT_LOWER_COMPUTE`.

## Lecture

- **L'adaptatif égale la meilleure profondeur fixe en succès, à ~2.5× moins de calcul.** Il plane profond
  (k=4) quand le modèle est fidèle (perfect/bilinéaire, MSE<0.02) — aucun gaspillage, comportement correct ;
  il coupe la profondeur (k=2) sur les modèles bruités où le gain de profondeur ne justifie plus le coût
  (~même succès à 1/32 du calcul) ; il reste greedy (k=1) sur le modèle mauvais.
- **Cas révélateur (modèle mauvais)** : sur le linéaire, planifier profond ne gaspille pas seulement (256×),
  ça ÉGARE ACTIVEMENT — fixe-max 0.367 < adaptatif greedy 0.404. Le planner suit avec confiance des rollouts
  prédits attractifs mais FAUX. Rester greedy quand on ne fait pas confiance à son modèle est plus efficace ET
  plus sûr → l'adaptatif gagne sur les DEUX axes.
- **Le signal de fidélité est gratuit et suffisant.** Le MSE 1-pas (observable en ligne dès qu'on agit)
  ordonne correctement les régimes (0.00→0.15) et pilote une politique par seuils qui capture le gradient
  profondeur×fidélité de PLAN-003. Pas besoin de connaître σ ni la vraie dynamique.

## Conséquences

- **Trilogie G4 → tétralogie, capstone POLITIQUE** : PLAN-001 (forme) + 002 (en ligne/couverture) + 003
  (profondeur/fidélité, constat) + **004 (profondeur adaptative, politique actionnable)**. L'anticipation
  instrumentale n'est pas seulement atteignable — elle est PILOTABLE efficacement par un agent qui monitore
  son propre modèle.
- **Reco in-world directe** : un agent doté d'un modèle appris devrait (a) monitorer son erreur de prédiction
  1-pas, (b) régler sa profondeur de planning dessus — profond si fiable, greedy sinon. Économise le calcul ET
  évite l'auto-tromperie par un modèle sous-appris (crucial tôt dans l'apprentissage en ligne, PLAN-002 où le
  modèle démarre rugueux). Branche sur la boucle biosphère (frontière #3).
- **Caveat honnête de la politique graduée** : au bord de seuil (bilinéaire_noisy+0.1, MSE 0.023 juste
  au-dessus de 0.02), elle sacrifie un cheveu de succès (0.796 vs 0.825, −0.03) pour 97% de calcul en moins —
  compromis net positif mais réel ; un gate à seuil plus haut garderait ce cas en profond.
- Relié : `REF-LTC -A_ADOPTER_POUR-> PLAN-004`. Clôt [[fil-directeur-agi-gates]] §G4 (PLAN-001/002/003,
  EDR-193). Motif [[warm-start-transversal-law]] : capacité rendue actionnable en identifiant le bon signal de
  contrôle (ici la fidélité auto-mesurée).

## Caveats

1. Proxy SYNTHÉTIQUE (dynamique action-conditionnée) hérité de la trilogie : établit le PRINCIPE (adaptatif
   domine l'enveloppe succès×calcul), pas la magnitude in-world.
2. Fidélité variée par bruit de prédiction INJECTÉ + régime linéaire ; un vrai modèle sous-appris aurait une
   structure d'erreur différente. Le MSE 1-pas reste le bon proxy de fidélité (validé par l'ordonnancement).
3. Politique par SEUILS fixes (0.02/0.06/0.12) calibrés sur les échelles de MSE de PLAN-001/003 ; robuste au
   sens de l'ORDONNANCEMENT, pas des décimales. Seuils à recalibrer si les échelles d'erreur in-world diffèrent.
4. Calcul = compte analytique de rollouts modèle (K^k × longueur) ; ignore le coût fixe de mesure de fidélité
   (négligeable : n prédictions 1-pas). 4 seeds ; le ROBUSTE = adaptatif≈fixe-max en succès + économie ~60%.
