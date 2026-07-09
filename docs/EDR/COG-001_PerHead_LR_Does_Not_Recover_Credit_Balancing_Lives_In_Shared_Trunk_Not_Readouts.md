---
id: EDR-COG-001
type: EDR
title: lr-par-tête (readouts seuls) NE recouvre PAS le gain disjoint — l'équilibrage de crédit vit dans le TRONC partagé, pas les têtes de lecture
status: accepted
gate: G0
verdict: LR_INSUFFICIENT
---

# EDR-COG-001 : lr-par-tête ne recouvre pas — le crédit qui compte est sur le TRONC partagé

> Territoire COG. Ferme le caveat d'EDR 154 (« lr-par-tête N'A PAS été testé ») et RAFFINE le mécanisme.
> Banc `tools/disjoint_heads_v4.py` (proxy teacher-student, tooling-only, `git diff src/` VIDE, déterministe).

## Question

L'arc têtes disjointes (EDR 152→154, 190-191) a établi que l'avantage DISJOINT sur le connectome PLAT
= **équilibrage de crédit**, pas l'isolation architecturale (migration #5 réfutée). Deux knobs recouvrent
le gain : l'**échelle de loss** (GradNorm-lite, EDR 153, ~0.79) et les **moments Adam séparés** (EDR 154,
~0.73). EDR 154 laissait un caveat explicite : le **lr-par-tête** n'avait jamais été isolé. M1 le teste
ET compare les trois knobs côte-à-côte (mêmes seeds/init/données par seed, seule la voie d'équilibrage varie).

## Méthode

Banc à 3 bras d'équilibrage sur `FlatModel` (trunc D→H partagé + 3 readouts action/value/pred) :
- **FLAT_NORM** (153) : 1 Adam, losses pondérées `w_k = 1/ema_k` (échelle) → pondère **aussi** le gradient
  du trunc partagé.
- **FLAT_PERHEAD** (154) : N Adam (moments séparés), même lr, sans échelle.
- **FLAT_PERHEAD_LR** (M1, nouveau) : **1 Adam à groupes de params**, lr propre par **readout**
  (`lr_k = LR·w_k`, même formule d'équilibrage que 153), **trunc au lr de base LR**, **moments uniques**,
  loss combinée NON pondérée. → isole « lr-par-tête » : le trunc apprend EXACTEMENT comme le FLAT nu ;
  seuls les lr des readouts changent. `_recovery` = fraction du gain DISJOINT récupérée (têtes MSE value+pred).

## Résultat (K=5, déterministe, re-run byte-identique)

| knob d'équilibrage | recovery moyen | par-seed |
|---|---|---|
| échelle de loss (153) | **+0.792** | 0.87 / 0.73 / 0.70 / 0.83 / 0.83 |
| moments Adam (154) | **+0.729** | 0.98 / 0.81 / 0.41 / 0.65 / 0.80 |
| **lr-par-tête (M1)** | **−0.160** | 0.21 / −0.14 / −0.68 / −0.02 / −0.18 |

Verdict **LR_INSUFFICIENT** (4/5 seeds ≤ 0.20 ; aucun n'atteint la famille ~0.75). Le banc **reproduit
fidèlement** 153 (0.79) et 154 (0.73) → contrôle validé ; le contraste est donc attribuable à la seule voie
d'équilibrage.

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : rééchelonner les lr des **readouts** (trunc au lr de base) NE recouvre PAS le gain disjoint —
  il **nuit légèrement** (−0.16 < 0 : pire que le FLAT nu).
- **FAIT** : les deux knobs qui recouvrent (153 échelle, 154 moments) agissent **tous deux sur le gradient
  du TRONC partagé** ; celui qui n'y touche pas (M1) échoue.
- **INTERPRÉTATION** : le conflit inter-têtes vit dans le **tronc partagé** (la représentation que les 3
  têtes se disputent), pas dans les têtes de lecture. L'équilibrage de crédit ne recouvre que s'il rééquilibre
  **comment chaque tête influence le gradient du tronc**. → **RAFFINEMENT du « crédit pas archi »** : ce n'est
  pas « n'importe quel knob d'équilibrage », c'est **le crédit sur le tronc partagé**.
- **COROLLAIRE prod (met à jour le brief T2)** : porter « lr-par-tête sur les readouts » en prod serait
  **inefficace**. Le mécanisme prouvé à porter reste **GradNorm-lite sur l'échelle de loss** (153, agit sur
  le tronc). Un « lr-par-tête » utile devrait porter le lr sur la **contribution de chaque tête au gradient
  du tronc** — ce qui exige des optimiseurs par-tête (= introduit les moments séparés de 154, plus isolable).

## Portée / Bornage

1. Proxy supervisé teacher-student (le RL confondrait par la variance de crédit — cf. mem_nas EDR 064).
   Dims figées (D=32, H=48, 3 têtes), K=5 seeds, STEPS=2000. Déterministe (num_threads=1, algos déterministes).
2. « lr-par-tête » = **readout-only + moments uniques** (l'isolation propre du lr SANS moments séparés).
   Un lr-par-tête *avec* optimiseurs par-tête est mesuré par 154 (les moments) — il n'existe pas de « lr pur »
   sur le tronc partagé sans introduire des moments séparés. Le négatif borne donc précisément cet angle.
3. Cohérent avec 190/191 (le gain multi-tête dépend du régime de capacité) : l'équilibrage utile est sur
   le tronc, là où la capacité partagée est disputée.

## Suite

- **Ferme le dernier angle proxy** de l'arc disjoint (152-154, 190-191). Actionnable prod = **UN** équilibrage
  de crédit sur le tronc (échelle de loss GradNorm-lite, 153), **JAMAIS** refonte disjointe ni lr-par-readout.
- Le brief T2 (`HANDOFF_T2_multihead_credit_brief.md`) est mis à jour : M2 = GradNorm-lite (échelle), PAS
  lr-par-tête ; payoff prod toujours conditionné à un métrique multi-tête (EDR 191).

Lignée : 152 (interférence réfutée) → 153 (échelle 79 %) → 154 (moments 73 %, caveat lr) → 190/191 (crédit
> archi sous interférence) → **COG-001 (lr-par-readout −0.16 : l'équilibrage vit dans le tronc partagé)**.
Étend [[intelligence-typing-flat-connectome]] + [[coop-competence-is-population-property]].
