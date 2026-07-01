---
id: ADR-003
type: ADR
title: Abstraction de backend — colonne numpy gardee, frontiere population, engagement framework differe
status: accepted
gate: null
motivates: []
triggers: []
tests: []
---
# ADR-003 — Abstraction de backend neuronal

Contexte : l'audit SOTA (mémoire `sota-gap-substrate`, spec
`superpowers/specs/2026-06-29-SOTA-Migration-design.md`) établit que le moteur « neuronal »
est du numpy maison (gradient dérivé à la main, ~5 nœuds cachés) et que le verrou prouvé
(EDR 104-111) est la **capacité d'apprentissage du substrat**. On veut migrer vers un substrat
entraîné par gradient **sans perdre** la liberté de réinvention (topologie évolutive,
paradigmes non-gradient).

## Décision

1. **Colonne numpy GARDÉE.** Le GA (topologies hétérogènes, mutation, repro), la reproductibilité
   (seed aux frontières, Harness D1) et les paradigmes **non-gradient** (spiking, pure-évo,
   discret) restent en numpy/Python — c'est l'actif et le bac à sable de réinvention.

2. **Frontière = population batchée**, pas l'agent unique. Couture canonique :
   `materialize(genomes) -> PopulationModel` (génomes hétérogènes → tenseur padé+masqué,
   `max_N=256`) ; `forward` ; `learn` (gradient ; no-op/hebbien pour legacy) ; `extract`
   (write-back Baldwin). La **topologie reste en espace-génome numpy** ; le backend ne voit
   qu'un tenseur de forme fixe → torch ET jax sans friction topologie. Le backend se choisit
   **par ère/run**, jamais par agent.

3. **Engagement framework DIFFÉRÉ (valide-ou-revert, Cmd 15).** L'interface rend le backend
   remplaçable → pas de mariage. Ordre : backend `legacy` (wrapper non-régressif du
   `MambaBatchModel` actuel) → backend **torch** (`ncps`/LTC) pour l'Axe 1 (Windows-natif,
   migration douce, premier A/B sur `transfer_ratio`) → **évaluer jax** (QDax/evosax, PRNG-keys
   alignés repro, DreamerV3 officiel) à l'Axe 5/QD, **seulement si** l'ergonomie population de
   torch limite et avec preuve. Aucun pari irréversible.

## Conséquences

- Tout backend SOTA est **opt-in** ; le chemin legacy numpy reste vert (non-régression).
- « 1 variable » au niveau infra : un backend change à la fois, et doit **battre le legacy**
  (`transfer_ratio`) ou il dégage — la décision framework devient falsifiable.
- **Pas de fork** : la réinvention différentiable passe par les points d'extension (autograd
  custom), la non-gradient par le backend numpy ; aucun besoin de posséder torch/jax.
- Plan d'exécution : `superpowers/plans/2026-06-29-SOTA-Migration.md` (Axe 1 en tête).
  SOTA visé : REF-LTC-2021 (substrat), REF-DreamerV3-2023 (anticipation).
