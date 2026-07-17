---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-103
type: EDR
title: "Préserver l'architecture est un no-op pour l'apex — le verdict MONOCULTURE tient sous topologie réelle"
status: legacy
gate: foundational
---

# EDR 103 : Préserver l'architecture est un no-op pour l'apex — le verdict MONOCULTURE tient sous topologie réelle

## Contexte

EDR 102 a conclu MONOCULTURE (champion ≈ mono_fresh < tabula diverse, apex) mais sur agents APLATIS :
`from_genome` jetait l'architecture du génome ([[from-genome-flattens-architecture]], forçait ~172
nœuds au lieu de ~320 réels). Caveat ouvert : l'archi évoluée du champion confère-t-elle une compétence
apex masquée par l'aplatissement ? Contrôle (spec/plan `2026-06-25-Preserve-Dims-3way-Rerun`) : knob
`CT_PRESERVE_DIMS` câblé aux 3 modes de `target_competence_probe` ; re-run du 3-way avec
`preserve_dims=True`, même config appariée (stoneage, sweet spot, 8 ères, 40 agents, 300 ticks).

## Constat — préserver ne change RIEN

| bras | apex APLATI (102) | apex PRÉSERVÉ | Δ | median_C préservé |
|---|---|---|---|---|
| tabula (diverse) | 0.211 | 0.214 | +0.003 | 0.287 |
| **champion** (mono HoF) | **0.162** | **0.162** | **+0.000** | 0.256 |
| mono_fresh (mono frais) | 0.158 | 0.158 | +0.000 | 0.246 |

Contrastes appariés par ère (préservé, n=8) :
- **champion vs mono_fresh** : Δapex **+0.004**, 4/8 ères, **sign_p = 1.000** → identiques.
- **champion vs tabula** : Δapex −0.052, 3/8 ères, sign_p 0.727 → champion sous la diverse.

## Verdict — ARCHITECTURALE réfutée, MONOCULTURE confirmée

> Préserver l'architecture du génome est un **no-op pour l'apex** : le champion préservé (0.162) est
> EXACTEMENT identique à sa version aplatie (0.162), et reste ≈ mono_fresh (sign_p 1.0) < tabula. Le
> verdict d'EDR 102 (MONOCULTURE, pas génome) tient SOUS topologie réelle. Le caveat d'EDR 102 est
> **RÉSOLU** : le déficit du champion n'est ni le génome ni l'architecture — c'est la monoculture.

L'hypothèse « compétence apex ARCHITECTURALE masquée par l'aplatissement » est **réfutée**.

## Signification — l'architecture évoluée du champion est fonctionnellement inerte pour l'apex

L'identité EXACTE (champion 0.162→0.162, mono_fresh 0.158→0.158 sur 8 ères appariées) signifie que les
~148 nœuds que l'aplatissement supprimait sont **fonctionnellement inertes** pour la chasse apex :
préserver ≡ aplatir pour ces génomes monoculture. Cohérent avec le finding parallèle « connectome 97%
I/O, hidden=5/172 » ([[nas-d1-metabolic-cost-refuted]]) : l'essentiel de la topologie ne calcule rien.
La diversité (tabula) bouge légèrement (med_C 0.313→0.287, `frac_tool` 0.016→0.022) car elle inclut
quelques génomes aux archis non-inertes — mais l'apex reste plat (0.211→0.214).

> Convergence : le verrou de la compétence apex n'est NI la recherche/sélection d'un champion, NI son
> architecture individuelle — c'est une propriété ÉMERGENTE de la DIVERSITÉ de population
> ([[coop-competence-is-population-property]]). Étend la méta-leçon
> [[nas-bottleneck-is-substrate-not-search]] : enrichir l'individu (archi, sélection) ne capture pas
> une compétence qui vit dans la variété.

Anti-théâtre : le knob `CT_PRESERVE_DIMS` (défaut OFF, non-régressif) + le smoke (preserve ne crash pas,
dims compatibles) ont permis de tester le caveat proprement. Le régime absolu rapporté (apex inchangé
aux 3 décimales) est le cœur du résultat — pas seulement l'écart inter-bras.

## Statut

- Caveat EDR 102 RÉSOLU : MONOCULTURE confirmée sous topologie préservée (apex no-op). Trilogie close :
  EDR 097 (champion < frais) → EDR 102 (monoculture, pas génome) → EDR 103 (ni architecture).
- **Piste suivante** (la seule restante du levier diversité) : **dose de diversité** — balayer la
  fraction de clones (0 % = diverse → 100 % = monoculture) → courbe diversité→apex (où la coordination
  s'effondre). Le knob `CT_PRESERVE_DIMS` peut rester OFF (no-op confirmé) pour ce sweep.

## Variables d'expérience

Fraction de clones (dose diversité→apex), `coop_reward` (ablation → l'écart diverse/monoculture
disparaît-il ?), `MEC_SEED_SPREAD`-style diversité de graines, K ères/seeds (ici n=8). `preserve_dims`
peut être ignoré en aval (no-op pour l'apex).
