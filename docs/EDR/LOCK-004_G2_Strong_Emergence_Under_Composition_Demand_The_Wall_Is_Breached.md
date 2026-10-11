---
id: EDR-LOCK-004
type: EDR
title: "Franchissement de G2-Fort et du mur EDR-LOCK-001 — La compétence composée ÉMERGE spontanément dans le bras nu sous demande de composition (12/12 seeds, p=0.00024, ratio x10.73)"
status: validated
verdict: G2_STRONG_EMERGENCE_VALIDATED
gate: G2
tests: [SDR-G2]
review: docs/reviews/2026-10-11-LOCK-004-G2-STRONG-EMERGENCE.md
extends: [EDR-LOCK-001, EDR-LOCK-002, EDR-LOCK-003, EDR-161]
---

## 1. Contexte & Défi Historique

Le **Niveau 2 de la porte G2 (G2-Fort / Émergence in-loop non supervisée)** représentait l'un des verrous centraux du projet AGIseed ([[EDR-LOCK-001]]) :
- La demande environnementale était prouvée nécessaire ([[EDR-S2-008]]).
- Le Niveau 1 (Proxy) démontrait que la capacité fournie avec un module de gating additif (`CONDITION_GATE=True`, `GATE_TARGET=USE`) payait sous la demande ([[EDR-161]]).
- Mais le bras **NU** (sans gate, sans oracle, sans curriculum) restait plat à `comp_rate ≈ 0.01-0.03` (hasard/bruit), semblant indiquer que la composition spontanée était inaccessible au substrat sans béquille structurelle.

## 2. Découverte de la Cause Racine (Artefact d'Optimisation E19)

L'enquête méthodique a révélé que le bras nu dans `tools/compositional_world_probe.py` était forcé d'utiliser un véhicule d'apprentissage inadapté :
1. `pop.learn` TD(0) par tick avec `lr=0.05` coupait le crédit entre S1 (CRAFT) et S2 (USE), et appliquait l'erreur TD sur un épisode ultérieur après remise à zéro de `H`.
2. Le learning rate de 0.05 ou 0.02 dégradait immédiatement le gradient subtil de dépendance 2-pas.

En alignant le bras nu sur un **crédit épisodique agnostique** (`learn_episode` sans module de gating) et un taux d'apprentissage adapté (`lr=0.005`, validé par [[EDR-LOCK-002]] et [[EDR-LOCK-003]]), **la composition spontanée émerge directement dans les poids synaptiques récurrents**.

## 3. Protocole & Résultats Officiels (n=12 Seeds Appariés)

Banc exécutable : `tools/g2_strong_emergence_benchmark.py` (800 épisodes, 64 agents, comparaison appariée `d=0.0` vs `d=1.0` sur les graines 0 à 11).
Données de mesure enregistrées dans [`results/g2_strong_emergence_benchmark.json`](../../results/g2_strong_emergence_benchmark.json).

| Graine | comp_rate (d=0.0) | comp_rate (d=1.0) | Différentiel Δ | Statut |
| :---: | :---: | :---: | :---: | :---: |
| Seed 00 | 0.0164 | 0.1667 | +0.1502 | **GAGNÉ** |
| Seed 01 | 0.0156 | 0.1619 | +0.1462 | **GAGNÉ** |
| Seed 02 | 0.0140 | 0.1570 | +0.1430 | **GAGNÉ** |
| Seed 03 | 0.0146 | 0.1684 | +0.1539 | **GAGNÉ** |
| Seed 04 | 0.0154 | 0.1650 | +0.1496 | **GAGNÉ** |
| Seed 05 | 0.0144 | 0.1549 | +0.1404 | **GAGNÉ** |
| Seed 06 | 0.0157 | 0.1581 | +0.1424 | **GAGNÉ** |
| Seed 07 | 0.0142 | 0.1642 | +0.1500 | **GAGNÉ** |
| Seed 08 | 0.0129 | 0.1554 | +0.1425 | **GAGNÉ** |
| Seed 09 | 0.0154 | 0.1593 | +0.1439 | **GAGNÉ** |
| Seed 10 | 0.0177 | 0.1593 | +0.1415 | **GAGNÉ** |
| Seed 11 | 0.0138 | 0.1678 | +0.1541 | **GAGNÉ** |

### Synthèse Statistique
- **Victoires Appariées** : **12 / 12** graines
- **Significativité Binomiale** : **$p = 2^{-12} \approx 0.000244$** (seuil exigé $p \le 0.0032$)
- **Médiane comp_rate (d=0.0)** : **0.0150** (bruit d'exploration aléatoire)
- **Médiane comp_rate (d=1.0)** : **0.1606** (composition structurée installée)
- **Ratio d'Émergence Spontanée** : **$\times 10.73$**

## 4. Verdict & Conséquences

Le critère exécutable de la porte SDR-G2 Niveau 2 est **PLEINEMENT SATISFAIT**.
- Le mur [[EDR-LOCK-001]] est percé sur ses trois piliers :
  1. Écriture dans le report (percé par EDR-LOCK-002).
  2. Coordination différée (percé par EDR-LOCK-003).
  3. Compétence composée non-supervisée G2-Fort (percé par **EDR-LOCK-004**).
- La porte **SDR-G2 passe au statut `status: validated`**.
