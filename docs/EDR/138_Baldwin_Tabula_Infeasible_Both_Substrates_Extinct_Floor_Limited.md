---
id: EDR-138
type: EDR
title: "Baldwin natif depuis tabula INFAISABLE sur les DEUX substrats (torch ET legacy s'éteignent en ~45 ticks) — plancher létal fresh (EDR-090/129) pré-empte la sélection ; le test moteur-vs-mismatch exige un WARM-START"
status: accepted
gate: null
verdict: BALDWIN_TABULA_INFEASIBLE_FLOOR_LIMITED
---

# EDR 138 : Baldwin natif tabula infaisable (plancher létal) — pivot warm-start

## Contexte

EDR-137 (mesure propre) : à parité d'organes, le TD autograd déstabilise le champion TRANSPLANTÉ
(torch 33.0 vs legacy-core 68.2, 0/10). Question ouverte : moteur autograd OU mismatch de règle
(champion évolué sous numpy) ? La suite #2 (Baldwin natif torch) sépare les deux. **Probe court
d'abord** (décision utilisateur) : évoluer NATIVEMENT sur torch et voir la tendance avant d'investir.

## Méthode

`tools/substrate_world_ab.py::evolve_native` (mode `evolve`) : `benchmark_mode=False` (reproduction/
mutation/HGT ACTIVES), `TorchBatchModel` injecté (seam :992), stoneage sweet-spot (EDR-085),
`memory_retriever` off, 24 agents tabula, seed 42, cap 1500 ticks. Le rebuild par-tick + le round-trip
réparé (EDR-137) rendent l'évolution native possible (offspring héritent du W torch-appris + mutation
= Baldwin/Lamarckien). **Contrôle** : idem sous legacy (`MambaBatchModel`).

## Constat

| substrat natif (tabula) | ticks atteints | best_age | births | pic pop | verdict |
|---|---|---|---|---|---|
| torch | 45 | 44 | 10 | 31 | **EXTINCT** |
| legacy | 42 | 37 | 16 | 33 | **EXTINCT** |

Le « champion » natif-torch (plus vieil agent, age 44 — un tabula, pas un évolué) mesuré ensuite :
survie **24.2** sous torch, **21.2** sous legacy — PIRE que le transplant legacy (33.0 torch / 74.5
legacy). Il n'y a pas de vrai champion : la population meurt avant que la sélection ne façonne quoi
que ce soit.

## Lecture

- **L'extinction n'est PAS propre à torch** : les DEUX substrats s'éteignent en ~42-45 ticks depuis
  tabula. C'est le **plancher létal des cohortes fraîches** (EDR-129 : fresh ~17-18t NEUTRE entre
  substrats) et le **« pas de premier barreau survivable »** de [[edr090-no-survivable-first-rung]] —
  **indépendant du moteur**. Torch survit même un poil plus longtemps (45 vs 42, best 44 vs 37) mais
  reproduit moins (10 vs 16) : aucun avantage/désavantage net au bootstrap.
- **Le probe Baldwin-tabula est donc INCONCLUSIF pour « moteur vs mismatch »** : sans barreau
  survivable, aucune sélection ne peut opérer → l'extinction pré-empte le test. On ne peut pas
  ré-évoluer un champion là où même legacy (qui PRODUIT les champions HoF via le pipeline complet
  d'entraînement) s'éteint en cohorte tabula nue.

## Conséquences

- **Le test Baldwin décisif exige un WARM-START** : semer l'évolution avec le champion legacy
  compétent (HoF #1) et laisser l'apprentissage torch + sélection l'ADAPTER sur générations
  (fine-tuning Lamarckien). Ça teste la vraie question de migration : « torch peut-il adapter un
  connectome déjà compétent pour le rendre gradient-stable ? » — sans buter sur le plancher.
- **Piste parallèle** (moins chère) : sweep `lr`/gating côté torch sur le champion transplanté
  (EDR-137) — apprivoiser le gradient suffit-il DÉJÀ à annuler la déstabilisation (33.0 → 68.2) ?
- **Note d'instrument** : `evolve_native` fonctionne (repro sous torch OK, round-trip EDR-137 validé
  en évolution) ; le blocage est le monde (plancher), pas le harnais. Réutilisable dès qu'on warm-start.
- Outils : `tools/substrate_world_ab.py` (mode `evolve`). Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-138`.

## Caveats

1. 1 seed (42), 1 monde (stoneage), sweet-spot. L'extinction est robuste sur les 2 substrats mais non
   balayée sur seeds.
2. Probe VOLONTAIREMENT court (cap 1500, atteint 45 par extinction). Un pop initial plus grand /
   énergie de départ plus haute pourrait retarder l'extinction sans changer le fond (plancher, EDR-090).
3. Le « champion natif » = plus vieil agent observé (proxy) ; comme la population s'éteint, ce n'est
   pas un produit de sélection — d'où sa faible survie (24.2), attendue.
4. async_logger KuzuDB en échec de lock pendant le run (logging off) — non bloquant.
