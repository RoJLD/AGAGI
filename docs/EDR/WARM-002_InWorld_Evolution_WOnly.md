---
id: EDR-WARM-002
type: EDR
title: "Évolution in-world W-only : le paysage de fitness de survie est PLAT (aucun gradient cognitif à escalader)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
L'oracle S2-009 prouve que le monde `cognitive_demand` EXIGE la perception (survie 200 vs plancher 7), mais
le REINFORCE à froid ne l'apprend pas. L'optimiseur que le SIM AGAGI utilise réellement n'est PAS le
gradient : c'est l'ÉVOLUTION (mutation + sélection). Un hill-climb sur `genome.W` pour la survie
franchit-il le verrou là où le gradient échoue ? Cadrage décisif : pour que la comparaison n'ait qu'UNE
variable (l'optimiseur), l'évolution n'optimise QUE `W` (`_mutate_W_only`, pas W_router/bytecode/organes),
le MÊME espace de recherche que le gradient (les génomes MambaAgent ont `W_router=None` par défaut → gradient
torch et évolution opèrent tous deux sur `genome.W` seul).

## Méthode
`tools/warmstart_evolution_inworld.py::run_inworld_evolution` : population de MambaAgents (W aléatoire),
UN épisode `cognitive_demand` par génération (la population partage un rollout, signal per-agent), fitness =
âge (survie), sélection top-k (25%) + élitisme + descendance mutée W-only. Régime S2-009 (metab=0.75,
cog_gain=12, forage_payoff=0, corps gaté). Verdict marqueur+survie (`verdict_demand_marker`, forward mamba,
K=12 ères, ablation within-subject `derange_rows`) sur le meilleur génome final. Sensibilité sur 3 régimes.

## Résultats

| régime | trend top-k (début→fin, max) | best_age | verdict marqueur (intact/ablé/ratio) |
|---|---|---|---|
| 50 gén, pop 24, mut_power 0.15 | 8.5 → 5–6 (max 9.0) | — | intact 5.0 / ablé 5.0 / **ratio 1.00 → NEUTRAL** (n=12) |
| 80 gén, pop 24, mut_power 0.5 | 8.5 → 8.5 (max 9.0) | 9 | intact 7.2 / ablé 7.0 / **ratio 1.04 → NEUTRAL** (n=12) |
| 80 gén, pop 32, mut_power 1.0 | 8.5 → 6.0 (max 8.5) | 10 | intact 7.2 / ablé 7.0 / **ratio 1.04 → NEUTRAL** (n=12) |

Repères : plancher no-perception ≈ 7 ; oracle intact ≈ 200 (S2-009). Le meilleur génome évolué survit
5–10 ticks (= plancher) et son ablation-perception ne change RIEN (ratio ≈ 1) sur les 3 régimes.

## Verdict
**`INWORLD_EVOLUTION_WONLY_FLAT_FITNESS_LANDSCAPE`** — l'évolution W-only ne franchit PAS le verrou (FAIL,
robuste aux 3 régimes de mutation). Le trend ne monte jamais (plat/déclinant autour du plancher), et le
meilleur génome n'utilise pas causalement la perception (NEUTRAL). Cause : le paysage de fitness de survie
est **PLAT** — un suiveur-de-signal PARTIEL survit AUSSI PEU qu'un non-suiveur (la survie est un accumulateur
multiplicatif qui ne récompense qu'au-delà de ~99% d'accuracy de perception, cf. WARM-001), donc la sélection
n'a **aucun gradient de fitness cognitif** à escalader. Augmenter la puissance de mutation (0.15→1.0) ne
crée pas de gradient là où il n'y en a pas.

## Portée & limites
- Budget modéré (≤80 générations, pop ≤32). Un NÉGATIF sous ce budget = « pas franchi ni de gradient
  détectable », robuste aux 3 régimes ; il n'exclut pas qu'un curriculum de létalité graduée FABRIQUE un
  gradient (barreaux survivables intermédiaires) — c'est le levier suivant documenté, pas testé ici.
- W-only volontaire (comparaison propre au gradient). L'évolution TOPOLOGIQUE complète (`apply_mutations`)
  est une variante de robustesse non lancée.
- Complémentaire de WARM-001 : gradient/imitation bute sur le shift de covariables ; l'évolution bute sur
  le paysage plat. Même cause profonde : la survie a un gradient cognitif quasi-nul (converge le fil S2).

Converge [[EDR-WARM-001]], [[decisive-substrate-thesis-test]], [[warm-start-transversal-law]],
[[s2-world-demand-thread]], REF-DEMAND-MARKER, S2-009.
