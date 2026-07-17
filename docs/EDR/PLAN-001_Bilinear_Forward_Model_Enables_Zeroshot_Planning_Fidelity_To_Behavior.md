---
id: PLAN-001
type: EDR
title: "La FORME du modèle de transition détermine le COMPORTEMENT — un g BILINÉAIRE rend le planning zéro-shot utile là où le LINÉAIRE échoue (clôt le caveat 'fidélité≠comportement' d'EDR-193). Dynamique vraie action-conditionnée (matrice par action, = la structure que 193 a trouvée dans le latent) ; g ajusté hors-ligne goal-agnostique ; planning depth-1 model-predictive vers des buts JAMAIS vus. Fidélité 1-pas : bilinéaire MSE 0.012 vs linéaire 0.163 (13.3×, même ordre que les 17× de 193). Comportement : bilinéaire atteint le but (norm_dist 0.475, succès 0.65) vs LINÉAIRE ~ HASARD (0.587/0.32 vs 0.579/0.34) -> reproduit le PLAN_PERD du depth-1 linéaire. La FIDÉLITÉ se traduit en COMPORTEMENT ; le levier G4 est RÉEL"
status: accepted
gate: null
verdict: BILINEAR_FORWARD_MODEL_ENABLES_ZEROSHOT_PLANNING
---

# PLAN-001 : la forme du modèle de transition détermine le comportement (G4 anticipation)

## Contexte

EDR-193 (`g_bilinear_probe.py`, session //) : un modèle de transition BILINÉAIRE g(H,a)→H' prédit le latent
caché ~17× mieux que le linéaire (action-conditionné) → « la FORME de g est un levier G4 ». Caveat explicite :
**fidélité ≠ comportement** (le fit était offline/oracle). Par ailleurs le planning depth-1 à g LINÉAIRE
avait été RÉFUTÉ (planner-depth1 : PLAN_PERD, nuit comme le dreaming 095). Question ouverte : un g BILINÉAIRE
rend-il le planning UTILE là où le linéaire échoue — la fidélité se traduit-elle en comportement ?

## Méthode

`tools/anticipation_planning_probe.py` (pur numpy, standalone, non-collidant). Le vrai avantage d'un modèle
du monde = **zéro-shot à un NOUVEAU but** sans réentraînement (north-star transfert). Planificateur depth-1
model-predictive : `a* = argmin_a ||g(s,a) − but||` → s'adapte à n'importe quel but si g est fidèle.
- **Dynamique VRAIE action-conditionnée** : s' = tanh(W_a·s), une matrice W_a PAR action (= la structure que
  193 a trouvée dans le latent réel). Un g LINÉAIRE partagé (s' ≈ A·s + B[:,a]) ne peut PAS la capturer
  (translation, pas rotation) ; un g BILINÉAIRE (matrice par action) oui.
- g ajusté hors-ligne par moindres carrés sur des transitions aléatoires (goal-AGNOSTIQUE) ; puis planning
  zéro-shot vers 500 buts aléatoires JAMAIS vus, horizon 4. Modèles : `bilinear`, `linear`, `none` (aléatoire).
- Métriques : fidélité 1-pas (MSE held-out) ; comportement (norm_dist = distance min au but / distance
  initiale, <1 = rapproché ; success = distance réduite de moitié). d=8, K=4, 5 seeds.

## Constat

**Fidélité 1-pas (MSE, plus bas = plus fidèle) :** bilinéaire **0.012** vs linéaire **0.163** → **13.3×**
(même ordre que les 17× d'EDR-193, sur dynamique synthétique action-conditionnée).

**Comportement (planning zéro-shot vers buts jamais vus) :**

| Modèle | norm_dist (min, <1=rapproché) | success |
|---|---|---|
| bilinéaire | **0.475** | **0.646** |
| linéaire | 0.587 | 0.324 |
| hasard (none) | 0.579 | 0.338 |

`VERDICT = BILINEAR_FORWARD_MODEL_ENABLES_ZEROSHOT_PLANNING`.

## Lecture

- **La FIDÉLITÉ se traduit en COMPORTEMENT** — caveat d'EDR-193 clos. Le g bilinéaire (13.3× plus fidèle)
  permet un planning qui atteint le but zéro-shot (distance ÷2 dans 65% des cas). La chaîne
  fidélité→comportement est établie DANS une seule expérience auto-contenue.
- **Le g LINÉAIRE est behaviorally INUTILE** : son planning est indistinguable du HASARD (norm_dist 0.587 vs
  0.579 ; success 0.32 vs 0.34). Un modèle qui mal-prédit les conséquences d'action mène le planificateur
  aussi mal qu'au hasard. Ceci **reproduit et EXPLIQUE** le « PLAN_PERD » du depth-1 linéaire (planner-depth1
  réfuté) : ce n'était pas le planning qui était mauvais, c'était le MODÈLE.
- **La FORME de g est un levier G4 comportemental**, pas une curiosité de prédiction. Le seuil de fidélité
  compte : sous un certain niveau (linéaire), le planning n'apporte RIEN ; au-dessus (bilinéaire), il débloque
  un comportement dirigé vers le but, ZÉRO-SHOT à des buts nouveaux (north-star transfert).

## Conséquences

- **Débloque le planning comme capacité G4** : le dreaming/depth-1 a été réfuté (095, planner-depth1) parce
  que le MODÈLE était linéaire/inadéquat, pas parce que le planning est intrinsèquement nuisible. Un g
  BILINÉAIRE (action-conditionné) est le prérequis → in-world, remplacer le forward model linéaire par un
  bilinéaire est le levier pour rendre l'anticipation instrumentale (branche sur `world_model.predict()`,
  frontière #3 « vrai planning »).
- **Dé-risque l'axe G4** comme les proxies langage/H-unif ont dé-risqué leurs axes : la capacité de planning
  anticipatif utile EST présente dès qu'on donne un modèle fidèle ; reste = fidélité du g APPRIS EN LIGNE
  in-world (ici fit offline, cf. caveats) et le bénéfice de survie.
- Relié : prolonge EDR-193 (`g_bilinear_probe`, [[fil-directeur-agi-gates]] §G4) au niveau COMPORTEMENTAL ;
  recoupe [[planner-depth1-refuted]] (explique le PLAN_PERD) et le [[dreaming-organ-not-dead]] (095). Nouvel
  axe → ID préfixé `PLAN-` (espace EDR-NNN contesté par sessions //).

## Caveats

1. Proxy SYNTHÉTIQUE (dynamique action-conditionnée tanh(W_a·s)) : capture la STRUCTURE que 193 a trouvée dans
   le latent réel, mais n'est pas le latent réel. Le résultat établit le PRINCIPE (forme→comportement), pas la
   magnitude in-world.
2. g ajusté HORS-LIGNE (fit oracle, comme 193) sur transitions aléatoires : le vrai test est un g APPRIS EN
   LIGNE pendant la survie (bien plus dur ; exploration, non-stationnarité). Caveat hérité de 193.
3. Planning depth-1 (une action anticipée) ; la vraie dynamique est nonlinéaire (tanh) donc même le bilinéaire
   n'est pas parfait (norm_dist 0.475, pas 0). Depth-k / modèle nonlinéaire pousseraient plus loin (non testé).
4. 5 seeds ; le ROBUSTE = le CONTRASTE (bilinéaire << linéaire ≈ hasard sur les deux métriques + 13.3×
   fidélité), pas les décimales. Buts « atteignables » échantillonnés dans le manifold (tanh) — buts hors
   manifold rendraient tous les modèles moins bons.
