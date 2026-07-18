---
id: EDR-NAV-004
type: EDR
title: La récupération du readout NAV tolère la sparsité (1%) et le bruit (90%) mais le BIAIS est FATAL — le shaping de T1 doit être ALIGNÉ, pas dense
status: accepted
gate: G0
verdict: BIAS_IS_FATAL
---

# EDR-NAV-004 : Sparsité et bruit sont quasi-gratuits, la misattribution est fatale — le levier de T1 est l'ALIGNEMENT

> Territoire NAV. Suite d'EDR-NAV-003. Cartographie la **frontière de récupération** du readout de navigation
> pour guider le design de shaping de T1. Banc `tools/nav_signal_density.py` (tooling-only, `git diff src/`
> VIDE, déterministe).

## Question

EDR-NAV-003 : sur H figé, un readout entraîné par récompense RL **dense et alignée** récupère le readout de
navigation (recovery +0.92) → le gap in-world = densité/alignement du signal, pas la trainabilité. Question
suivante, décisive pour le shaping de T1 : **jusqu'où peut-on dégrader le signal RL avant l'échec, et QUELLE
dégradation compte** — la densité ou l'alignement ?

## Méthode

Trois knobs de corruption INDÉPENDANTS sur la récompense bandit, sur les mêmes paires `(H, correct)` figées
(capture NAV-001, n=12668), contrôle à une variable (un knob varie, les autres à leur valeur facile) :
- **Sparsité ρ** (NON-BIAISÉ, moins de données) : fraction des pas qui reçoivent un gradient.
- **Bruit η** (NON-BIAISÉ, moins de signal) : récompense remplacée par Bernoulli(0.5) aléatoire (moyenne nulle).
- **Misattribution β** (BIAISÉ, mauvais signal) : la récompense cible une direction **systématiquement fausse**
  (`(y+1) mod 4`) → modélise le vrai problème de crédit du forage in-world (atteindre la proie crédite le
  MAUVAIS pas). `recovery = (acc − chance) / (acc_sup − chance)`.

## Résultat (n=12668, K=3 inits, déterministe ; plafond SUP=0.971, chance=0.476)

| knob | valeur → dure | recovery |
|---|---|---|
| **Sparsité ρ** | 1.0 → 0.10 → 0.03 → **0.01** | +1.01 → +0.98 → +0.97 → **+0.91** |
| **Bruit η** | 0.0 → 0.5 → 0.9 → **1.0** | +1.01 → +1.01 → +0.95 → **−0.50** |
| **Misattribution β** | 0.0 → 0.3 → **0.6** → 1.0 | +1.01 → +1.01 → **−0.93** → −0.95 |

Verdict **BIAS_IS_FATAL** (la sparsité tient ≥0.50 ; la misattribution s'effondre ≤0.30). Reproduit en
calibration (n=2927).

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : la dégradation NON-BIAISÉE est **quasi-gratuite** — 1 % des pas récompensés → recovery +0.91 ;
  90 % de bruit aléatoire → +0.95. Le readout récupère d'un signal **faible mais correct**.
- **FAIT** : le bruit à η=1.0 (signal totalement éteint) tombe à −0.50 (≈ hasard) — attendu (aucun signal).
- **FAIT** : la misattribution BIAISÉE est **catastrophique** — dès β=0.6 la recovery plonge à **−0.93**
  (acc 0.016, SOUS le hasard) : le readout apprend **activement la mauvaise politique**. Falaise nette entre
  β=0.3 (+1.01) et β=0.6 (−0.93), près du point de bascule β≈0.5 où la cible fausse domine.
- **INTERPRÉTATION** : ce n'est **PAS la densité** du signal qui compte (elle est presque gratuite), c'est
  l'**ALIGNEMENT**. Un signal rare ou bruité mais correct récupère ; un signal biaisé enseigne le faux.
- **RAFFINE NAV-003 + localise l'échec in-world** : le champion (évolué sous forage clairsemé) émet le bon pas
  à 0.03 — NON parce que la récompense est rare (la sparsité est indulgente) mais probablement parce que le
  crédit de forage est **MISATTRIBUÉ** (atteindre la proie crédite toute la trajectoire, pas le pas de
  direction correct = biais). C'est le mode de corruption FATAL.
- **CONSÉQUENCE pour T1 (design du shaping)** : le signal per-pas doit être **ALIGNÉ**, pas forcément dense.
  → **(a) aux supervisé sur l'oracle** = parfaitement aligné, route sûre. → **(b) reward-shaping** = viable
  SEULEMENT s'il est aligné au **pas de direction** (« s'est rapproché de la proie CE pas »), **JAMAIS**
  agrégé sur la trajectoire (qui misattribue = biais = fatal). La densité du shaping est un faux problème.

## Portée / Bornage

1. Bandit offline sur H **figé** (isolé de l'encodeur + têtes concurrentes — cf. EDR-COG-001 : crédit=tronc).
   Le mode biaisé réel in-world (délai/agrégation trajectoire) est modélisé par un décalage fixe `(y+1)` ;
   la LOCALISATION de la falaise (β≈0.5) est spécifique au modèle, mais le CONTRASTE qualitatif
   non-biaisé-indulgent / biaisé-fatal est robuste (calib + full, déterministe).
2. `recovery > 1.0` aux points faciles = le bandit égale/dépasse marginalement le plafond supervisé (bruit).
3. N_CLASSES=4 (N/S/E/O), forage figé (speed=0, comparable 114b). n grand → serré.

## Suite

- Complète la carte du readout NAV : trainable (NAV-003) ET tolérant à un signal faible mais aligné (NAV-004).
  Le risque de T1 n'est ni la trainabilité ni la densité — c'est l'**alignement per-pas** du signal.
- M2 in-world (session torch, `backend_torch` + boucle) : injecter un signal ALIGNÉ (aux supervisé oracle, ou
  shaping per-pas non-agrégé) ; éviter tout crédit trajectoire-agrégé (biaisé).

Lignée : NAV-001 (READOUT_GAP) → NAV-002 (énergie endogène) → NAV-003 (readout RL-récupérable, signal dense)
→ **NAV-004 (sparsité/bruit indulgents, biais fatal → le levier est l'alignement)**.
Étend [[lewis-energy-economy-wall]] + [[sota-gap-substrate]] ; converge [[coop-competence-is-population-property]].
