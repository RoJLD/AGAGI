---
id: EDR-NAV-005
type: EDR
title: Le mur de crédit in-world du binding (EDR-172) est le BIAIS de la récompense, pas la rareté — correctif actionnable pour le throw-gate torch
status: accepted
gate: G0
verdict: BIAS_NOT_RARITY
---

# EDR-NAV-005 : la couche « rareté du crédit » d'EDR-172 est en fait un BIAIS — et il est réparable

> Territoire NAV. Diagnostic offline d'un mur d'une session parallèle (torch T3, EDR-172), via le prisme
> d'EDR-NAV-004. Banc `tools/nav_credit_structure.py` (tooling-only, `git diff src/` VIDE, déterministe).

## Contexte

EDR-172 (session torch) : le throw-gate câblé in-world NE BINDE PAS (binding_gap = bruit, shuffle binde
autant, `gap_ON` même **négatif**). Diagnostic de la session torch = **substrat, à deux couches** : (1) la
cohorte fraîche s'éteint avant l'horizon d'apprentissage ; (2) le crédit kill-avec-outil est trop **RARE**
(0-6/300 ticks) pour piloter le REINFORCE. Récompense de leur gate : throw+kill → **+1** (rare), throw sans
kill → **−0.5**, pas de throw → 0.

EDR-NAV-004 a montré que la rareté NON-BIAISÉE est quasi-gratuite (ρ=0.01 → recovery +0.91) mais que le
BIAIS est fatal. **Hypothèse testée ici** : le mur de crédit d'EDR-172 (couche 2) n'est pas la rareté mais
le **−0.5** — une pénalité sur le BON geste (throw-avec-spear) quand le kill n'arrive pas.

## Méthode

Modèle offline de la structure de récompense d'EDR-172 sur le readout de navigation (H figé, capture
NAV-001, n=12668) : action correcte → **+1** avec proba `p_success` (modélise le kill rare), sinon `penalty` ;
action incorrecte → 0. Espérance de l'action correcte : `E[correct] = p_success·1 + (1−p_success)·penalty`.
Sweep `p_success ∈ {1.0, 0.3, 0.1, 0.03}` × `penalty ∈ {0 (non-biaisé), −0.5 (biaisé, valeur de T3)}`,
K=3 inits, contrôle à une variable (même init/split/optim que le supervisé).

## Résultat (n=12668, déterministe ; plafond SUP=0.971, chance=0.476)

| p_success | E[correct] non-biaisé | recovery **non-biaisé** | E[correct] biaisé (−0.5) | recovery **biaisé** |
|---|---|---|---|---|
| 1.00 | +1.00 | **+1.01** | +1.00 | +1.01 |
| 0.30 | +0.30 | **+1.01** | −0.05 | **−0.93** |
| 0.10 | +0.10 | +1.00 | −0.35 | −0.96 |
| 0.03 | +0.03 | **+0.97** | −0.45 | −0.96 |

Verdict **BIAS_NOT_RARITY** (reproduit en calibration). L'effondrement du bras biaisé tombe **exactement au
seuil analytique** : sous `penalty=−0.5`, `E[correct] < 0` dès `p_success < 1/3` → le readout apprend à
ÉVITER l'action correcte (recovery négative).

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : la rareté du crédit, SEULE (non-biaisée), est quasi-gratuite — le readout récupère à +0.97 même
  à 3 % de succès. La pénalité `−0.5` sur le bon geste non-payant effondre la récupération sous le hasard
  (−0.93) dès que le succès est rare (`p_success < 1/3`).
- **INTERPRÉTATION (raffine EDR-172, couche 2)** : le mur de crédit in-world du throw-gate n'est **pas la
  rareté** mais le **BIAIS** de sa récompense. In-world, kills ~6/300 → `p_success ≈ 0.02 ≪ 1/3` → sous
  `−0.5`, `E[throw|spear] ≈ −0.47` → le gate apprend à throw MOINS avec spear → `gap_ON` **négatif**
  (précisément ce qu'EDR-172 observe). Le modèle offline **reproduit leur signe négatif** et l'explique.
- **CORRECTIF ACTIONNABLE pour la session torch** : rendre la récompense **NON-BIAISÉE** — récompenser les
  kills (+1), **ne PAS punir** les throws non-payants (0 au lieu de −0.5). Plus généralement, garder
  `penalty ≥ −p_success/(1−p_success)` (≈ **−0.02** au régime in-world) pour que `E[correct] ≥ 0`. NAV-005
  prédit que le gate binde alors même à leur rareté (la sparsité non-biaisée est indulgente).
- **CONVERGE avec la thèse de session** : encore une fois, ce n'est pas le substrat/la représentation ni la
  densité qui bloquent, c'est l'**alignement du crédit** (ici, un terme de shaping mal signé).

## Portée / Bornage (honnêteté)

1. **NAV-005 ne réfute PAS EDR-172 en bloc** — il raffine **sa couche 2 (rareté→biais)**. La **couche 1
   d'EDR-172 (plancher de survie : la cohorte fraîche s'éteint avant d'apprendre)** est un mur de substrat
   RÉEL et SÉPARÉ que NAV-005 n'adresse pas (il opère sur H figé, survie supposée). Le correctif de crédit
   ne paie que si la couche 1 est levée par ailleurs (cohorte pré-entraînée, ou dims torch dynamiques
   permettant l'évolution — leviers (a)/(b) d'EDR-172).
2. Modèle 4-classes (nav) vs gate binaire (throw) : les détails diffèrent, mais le mécanisme `E[correct]`
   est général (toute action correcte punie plus souvent que récompensée est désapprise).
3. `anti-sat` d'EDR-172 (calibré pour la récompense dense de B1) est un facteur ADDITIONNEL possible non
   modélisé ici ; il pousse dans le même sens (supprime le throw), cohérent.

## Suite

- **Hypothèse à tester par la session torch** (leur territoire `backend_torch`/boucle) : rejouer le banc
  B2 d'EDR-172 avec `penalty=0` (récompense non-biaisée) — NAV-005 prédit un binding_gap POSITIF là où
  `−0.5` donnait du bruit/négatif, SI la couche survie est adressée.
- Complète la carte du readout NAV : trainable (003), tolérant sparsité/bruit mais pas le biais (004), et
  ici le biais explique un mur in-world concret (005).

Lignée : NAV-003 (RL-récupérable) → NAV-004 (biais fatal, pas la densité) → **NAV-005 (le biais explique le
mur in-world d'EDR-172 ; correctif = récompense non-biaisée)**. Pont vers [[torch-inworld-integration-plan]]
+ [[coop-competence-is-population-property]] (crédit means→ends). Étend [[sota-gap-substrate]].
