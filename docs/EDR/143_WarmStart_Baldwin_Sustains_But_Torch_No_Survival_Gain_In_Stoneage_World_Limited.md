---
id: EDR-143
type: EDR
title: "Exploiter torch (item 4) : le warm-start Baldwin SOUTIENT la population (556t vs tabula 45t) mais la plasticité torch N'AMÉLIORE PAS la survie du champion en stoneage (+1.0 tick, bruit) → survie WORLD-limitée, pas substrat-limitée ; le payoff de torch vit sur les tâches gradient-exigeantes (means→ends), pas la survie"
status: accepted
gate: null
verdict: WARMSTART_SUSTAINS_TORCH_NO_SURVIVAL_GAIN_WORLD_LIMITED
---

# EDR 143 : exploiter torch — warm-start Baldwin soutient mais n'améliore pas la survie stoneage (world-limité)

## Contexte

EDR-140/141 ont établi la FAISABILITÉ de migration (torch ≈ legacy-core, p=0.46). Reste la VALEUR :
« exploiter torch » (item 4). Premier test faisable et aligné sur le fil : **warm-start Baldwin** —
évoluer NATIVEMENT sur torch à partir du champion legacy (pas tabula, qui s'éteint EDR-138) et voir si
la plasticité différentiable + sélection **améliore** la survie.

## Méthode

`tools/substrate_world_ab.py::evolve_native(seed_genome=champion)` (mode `evolve`, `SWA_WARMSTART=1`) :
cohorte initiale = 24 clones du champion HoF #1, `benchmark_mode=False` (repro/mutation/HGT actives),
`TorchBatchModel` défaut (auto→swish), stoneage sweet-spot, cap 1200 ticks, `pop_cap=120`. On mesure
le champion SEED sous torch (baseline) vs le BEST évolué sous torch (et sous legacy). K_eval=10.

## Constat

```
EVOLVE-NATIVE-TORCH warm_start=True ticks=556 best_age=555 births=12 peak_pop=35 final_pop=0 extinct=True
  seed champion sous torch (baseline) : 38.2
  best ÉVOLUÉ-torch sous torch  : 39.2   (delta vs seed = +1.0)
  best ÉVOLUÉ-torch sous legacy : 63.8
```

- **Le warm-start SOUTIENT** : 556 ticks avant extinction (vs **45** en tabula, EDR-138) — partir
  compétent évite l'effondrement immédiat.
- **Mais torch N'AMÉLIORE PAS** : best évolué 39.2 vs seed 38.2 = **+1.0 tick (bruit)**. La plasticité
  différentiable + sélection n'a rien tiré de plus. Sous legacy le best fait 63.8 (≈ toujours le
  champion seed → l'évolution torch ne l'a pas transformé).
- La population s'éteint quand même (556t, 12 births ≈ peu de générations).

## Lecture

- **En stoneage, la survie n'est PAS une tâche torch-exploitable.** Cohérent EDR-139 (apprentissage
  intra-vie neutre ici) et tout le fil « le monde exige-t-il l'intelligence ? » ([[s2-world-demand-thread]],
  [[nas-bottleneck-is-substrate-not-search]]) : la survie est **limitée par le MONDE** (plancher létal,
  plafond de compétence), pas par une structure gradient-apprenable. Le champion est déjà au plafond du
  monde → **rien à exploiter pour le gradient ICI**.
- **Le payoff de torch vit AILLEURS** : sur des tâches qui EXIGENT une structure apprenable par
  gradient — le **means→ends compositionnel**, où le chantier // a montré torch > hebbien sous
  curriculum (EDR-122/126 : le hebbien ne binde JAMAIS, torch monte les marginales/craque partiellement).
  La survie stoneage n'a pas ce besoin.

## Conséquences

- **Migration : FAISABILITÉ close (140/141), VALEUR conditionnelle** — torch ne « paie » que là où la
  tâche demande de l'apprentissage de structure. Choisir les bancs torch en conséquence (compositionnel,
  means→ends, mémoire-exigeante), PAS la survie stoneage.
- **Le warm-start est l'outil correct** pour toute évolution native sous torch (tabula s'éteint) —
  réutilisable pour des mondes/tâches gradient-exigeants.
- **Frontière torch non encore bâtie** (le vrai gain que numpy interdit) : apprenants plus forts —
  BPTT multi-tick, meta-RL (RL²), Dreamer — au-delà de l'Actor-Critic TD 1-pas actuel. C'est là que la
  migration devient un LEVIER, pas juste une parité. Affine [[sota-gap-substrate]].
- Outils : `tools/substrate_world_ab.py` (`evolve_native(seed_genome=...)`, mode `evolve` warm-start).
  Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-143`.

## Caveats

1. **Apprenant torch FAIBLE** : Actor-Critic TD 1-pas (lr 0.04). BPTT/meta-RL/Dreamer NON testés → le
   « pas de gain » vaut pour CET apprenant, pas pour le potentiel de torch.
2. 556 ticks / 12 births = **peu de générations** ; un run plus long/large pourrait laisser la sélection
   agir davantage (mais le signal est net : +1.0, et EDR-139 dit apprentissage neutre en survie).
3. 1 champion, 1 monde (stoneage), 1 seed (42). « best » = proxy plus-vieil-agent (pas un vrai HoF).
4. La conclusion « world-limité » est cohérente avec 4 fils convergents, mais reste une inférence sur ce
   monde ; un monde gradient-exigeant est le test complémentaire (backlog).
