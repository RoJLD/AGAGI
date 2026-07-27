---
id: EDR-174
type: EDR
title: Densifier le crédit du throw-gate BACKFIRE (anti-binding) — les fixes côté SIGNAL de récompense sont épuisés in-world, pivot vers warm-start/curriculum
status: accepted
gate: G1
verdict: DENSITY_BACKFIRES_REWARD_SIGNAL_FIXES_EXHAUSTED
---

# EDR-174 : le levier « densité » d'EDR-173 backfire — le binding in-world ne se répare pas côté signal

> Territoire BIND/torch (suite d'EDR-172/173). Banc `tools/torch_throw_gate_inworld_ab.py`
> (`compare_density`, additif) + shaping `src` `torch_throw_shaping` (flag-guardé, défaut OFF).

## Contexte

Chaîne throw-gate in-world : **EDR-172** (câblage biosphère → NEUTRE) → **NAV-005** (offline : le mur est le
BIAIS −0.5, pas la rareté) → **EDR-173** (débias in-world → NÉCESSAIRE mais PAS SUFFISANT ; verrou résiduel =
`p_success ≈ 0.001`, ~10-20× sous le régime offline NAV-005 ; **levier désigné = DENSITÉ**). Cet EDR teste le
levier densité.

**Question** : un crédit DENSE sur la qualité de visée (proximité projectile→proie) au lieu du hit binaire rare
produit-il le binding ?

## Méthode

- **`src` (flag-guardé, défaut OFF, rétro-compatible)** : `torch_throw_shaping` → `r(throw) = _throw_aim`, où
  `_throw_aim = max(0, 1 − dist(point d'arrivée, proie la plus proche)/R)` ∈ [0,1] (R=5), calculé au bloc
  balistique pour les throws de **spear** (spear-spécifique = préserve la means-spécificité). Densifie le signal
  ~binaire du hit (~0.001).
- **Banc** : `compare_density` apparié **sparse (hit binaire, EDR-173) vs dense (shaping)**, LES DEUX non-biaisés
  (`penalty=0`), chaque bras verdict ON-vs-SHUFFLE. Couche 1 levée (energy 250 / spear lourd / métab 0.05,
  hérité d'EDR-173). **Knob `antisat`** ajouté : à l'anti-sat prod (6.0), `p→0` avant la fenêtre (throw_rate≈0,
  gap non mesurable) → calibré à 0.3 pour un throw_rate mesurable (0.09-0.38).

## Résultat (K=6, couche 1 levée, antisat=0.3)

| bras | verdict | median_diff | throw_rate | gap_ON |
|---|---|---|---|---|
| sparse | **NEUTRE** | 0.000 | ≈0 (anti-sat éteint) | ≈0 (repro EDR-173) |
| dense | **HEBBIEN_GAGNE** | **−0.26** | 0.09-0.38 | **−0.28 à −0.52** |

Le bras dense **anti-binde** : `gap_ON` fortement négatif, le shuffle binde PLUS que le ON (HEBBIEN_GAGNE). La
densité n'a pas débloqué le binding — elle l'a **inversé**.

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : le shaping de visée dense produit un `gap_ON` négatif robuste (6/6 seeds) → le gate throw MOINS avec
  spear qu'sans. Le sparse reste NEUTRE (repro EDR-173).
- **INTERPRÉTATION (mécanisme)** : deux effets se combinent. (1) Le crédit dense augmente la propension à throw
  **globale**, pas spear-conditionnelle. (2) **Throw CONSOMME le spear** → densifier le crédit fait throw
  davantage → l'agent devient spearless plus vite → mais le gate (qui a appris à throw) continue → `P(throw|¬spear)`
  monte → `gap` négatif. Le couplage **action-consommation ⊗ crédit dense** produit l'inverse du binding. (S'y
  ajoute la baseline REINFORCE : les throws ratés dominent, tirent le gradient sous la moyenne.)
- **MÉTA-VERDICT (le point décisif)** : c'est la **3ᵉ tentative côté SIGNAL de récompense** — câblage (172,
  NEUTRE), débias (173, nécessaire-pas-suffisant), densité (174, BACKFIRE). **Aucune retouche du signal de crédit
  ne produit le binding in-world.** Ceci **converge la loi transversale de la session** : sous crédit épisodique
  torch, le binding émerge d'un **bassin pré-formé (warm-start/curriculum)**, PAS de la forme du signal — établi
  sur 4 fils disjoints (rétention 167/168/170 ; langage LANG-004 ; craft-or-starve COS L2 ; difficulté CURR-001).
  Le throw-gate échoue depuis 172 parce que c'est la **mauvaise famille de leviers**.

## Portée / Bornage

1. **Résultat NÉGATIF sur un design de shaping spécifique** (aim-proximité). Un autre signal dense (récompense
   la DÉCISION de throw quand une proie est en portée, sans consommer ; ou crédit non-centré) pourrait éviter le
   couplage consommation. Mais le méta-verdict (signal ≠ le levier) tient sur les 3 tentatives + la loi transversale.
2. `antisat=0.3` calibré pour la mesurabilité, pas la prod (6.0). L'anti-sat prod éteint `p` → confond (3ᵉ après
   survie couche-1 et équilibre de contexte). Le résultat dense tient sur la plage antisat 0.3-2.0 (gap négatif).
3. K=6 ; le dense est robuste (6/6 négatif), le sparse NEUTRE. Pas de verdict POSITIF revendiqué (garde-fou).
4. Couche 1 levée artificiellement (hérité 173).

## Suite

- **Pivot désigné : warm-start / curriculum du throw-gate** (PAS plus de retouche de récompense). Pré-entraîner le
  gate sur un régime FACILE (proies denses / cohorte survivante / hit fréquent) où le binding s'installe, PUIS
  transférer in-world — analogue EXACT de LANG-004 (curriculum dyade→rotation), rétention-167 (warm-start du
  bassin), COS L2 (curriculum débloque le binding que L0/L1 ratent). C'est le prochain chantier.
- **Ne PAS** poursuivre les fixes de signal (sign/densité/anti-sat epuisés). Le knob `torch_throw_shaping` reste
  disponible mais **défaut OFF** (backfire in-world).

Lignée : clôt la sous-ligne « réparer le throw-gate côté signal » (172 câblage / 173 débias / 174 densité) et la
recadre via [[warm-start-transversal-law]] (le levier est le bassin, pas le signal) + [[torch-inworld-integration-plan]].
Converge la thèse CRÉDIT de COS Phase B en la précisant : le crédit doit être ATTRIBUABLE via un bassin pré-formé,
la densité seule ne suffit pas. Étend [[coop-competence-is-population-property]].
