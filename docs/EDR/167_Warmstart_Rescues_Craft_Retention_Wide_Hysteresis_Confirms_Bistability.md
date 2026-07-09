---
id: EDR-167
type: EDR
title: "Le WARM-START rescape la rétention du craft — HYSTÉRÉSIS LARGE, preuve causale de la bistabilité d'EDR-164. Pré-entraîner le binding à coût 0 puis monter le coût : le craft est RETENU jusqu'à c=0.30 (warm craft ~0.12, P~0.9) là où un cold-start s'effondre dès c*≈0.04 (~0.05, P~0.3) — soit ~7× le seuil cold. Deux bassins (bistable) : le warm-start place dans le bassin haut qui tolère un coût bien plus grand. Livre le levier ACTIONNABLE pour l'axe 3 in-world (warm-start le binding, converge EDR-132), pas 'renforcer le binding'"
status: accepted
gate: null
verdict: WARMSTART_RESCUES_RETENTION_WIDE_HYSTERESIS
---

# EDR 167 : le warm-start rescape la rétention (hystérésis large) — preuve causale de la bistabilité

## Contexte

EDR-164 a diagnostiqué la rétention comme une BISTABILITÉ (falaise à c*≈0.04, binding fort P≈0.97,
effondrement = instabilité de bassin pas non-rentabilité) et PRÉDIT que le levier est le WARM-START (se
placer dans le bassin haut), pas « renforcer le binding ». Test causal de cette prédiction : si c'est une
bistabilité, un warm-start (pré-entraînement à coût 0) doit RETENIR le craft à des coûts bien supérieurs
au seuil cold → HYSTÉRÉSIS.

## Méthode

`tools/hunif_retention_probe.py` gagne `warmstart_episodes` : phase préalable à coût 0 (bâtit le bassin
haut-craft) AVANT la phase mesurée au coût `cost` (même pop persistante). On oppose cold (warmstart=0) vs
warm (warmstart=400) sur un sweep de coût, 2 seeds, 600 ép mesurés. Capacité ON (gate + learn_episode).

## Constat

| c | cold craft_late | warm craft_late | P cold / warm |
|---|---|---|---|
| 0.05 | 0.070 | 0.130 | 0.35 / 0.87 |
| 0.10 | 0.061 | 0.134 | 0.34 / 0.88 |
| 0.20 | 0.049 | 0.121 | 0.27 / 0.91 |
| 0.30 | 0.045 | **0.119** | 0.29 / **0.91** |

`VERDICT = WARMSTART_RESCUES_RETENTION_WIDE_HYSTERESIS`. Le cold s'effondre à TOUS les coûts (craft
~0.05, P~0.3, réplique 164). Le warm RETIENT à TOUS les coûts jusqu'à c=0.30 (craft ~0.12, P~0.9), soit
~7× le seuil cold c*≈0.04. Reproduit au smoke 1 seed (cold 0.067 vs warm 0.153 à c=0.1).

## Lecture

- **HYSTÉRÉSIS LARGE confirmée** : le même coût (ex. c=0.30) qui effondre un cold-start est RETENU par un
  warm-start. Deux seuils distincts (entrer le bassin ≈0.04 vs le quitter ≥0.30) = signature exacte d'un
  système BISTABLE. **Preuve causale de l'interprétation d'EDR-164** (bistabilité, pas faiblesse de binding
  ni non-rentabilité statique).
- **La prédiction d'EDR-164 est VALIDÉE** : le levier de la rétention est le BASSIN (warm-start), pas la
  force du binding (déjà forte, P~0.9 dans le bassin haut à tous les coûts). Le warm-start place et
  MAINTIENT la population dans le bassin haut, où le gradient continu du binding fort résiste au coût.
- Le warm-craft s'érode LÉGÈREMENT avec le coût (0.13 → 0.12 de c=0.05 à 0.30) mais reste ~2.5× au-dessus
  du cold et P plat ~0.9 → le coût grignote la marge sans franchir la barrière du bassin (dans la plage
  testée). Le seuil warm c_hi n'est pas atteint à 0.30 (hystérésis ≥7×).

## Conséquences

- **Levier in-world (axe 3) LIVRÉ et actionnable** : pour retenir un moyen coûteux in-world (craft, 127),
  **warm-start le binding** — pré-entraîner à coût faible/nul (ou warm-start du gate façon EDR-132) AVANT
  d'exposer au coût plein, OU curriculum de coût croissant (rester dans le bassin haut). Converge EDR-132
  (warm-start du gate) et la path-dependence 131/133. Ce n'est PAS « renforcer le binding » (déjà fort).
- **Ferme la trilogie rétention** (162 constat → 164 mécanisme corrigé → 167 levier validé) : la rétention
  d'un moyen coûteux est une bistabilité rachetable par warm-start ; le pari H-unif tient avec cette
  couche dynamique. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-167`.

## Caveats

1. Warm-start = 400 ép à coût 0 ; la profondeur du warm-start (combien d'ép) vs sa robustesse n'est pas
   sweepée (bornage — 400 suffit ici).
2. Seuil warm c_hi non localisé (≥0.30 tenu ; pas testé au-delà) ; l'hystérésis est ≥7× mais sa largeur
   exacte reste ouverte.
3. 2 seeds, 600 ép mesurés ; le ROBUSTE = cold-collapse vs warm-retient à TOUS les coûts (séparation
   nette ~2.5× + P 0.9 vs 0.3), pas les valeurs absolues.
4. Substrat 172-nœuds dégénéré, means→ends 2-pas synthétique ; test réel = in-world (axe 3).
