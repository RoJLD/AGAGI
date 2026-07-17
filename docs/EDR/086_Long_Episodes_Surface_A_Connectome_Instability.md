---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-086
type: EDR
title: "Débloquer la survie longue fait surgir (et corrige) une instabilité du connectome"
status: legacy
gate: foundational
---

# EDR 086 : Débloquer la survie longue fait surgir (et corrige) une instabilité du connectome

## Contexte

EDR 085 : le sweet spot d'énergie débloque la survie longue (~160-227 ticks vs ~45). On lance le re-test
du langage (086/087) sur ce substrat… qui **CRASHE** : `ValueError: cannot convert float NaN to integer`
dans `MambaAgent.update_phenotype` — `genome.W` contient des NaN.

## Diagnostic — une instabilité latente, révélée par les longs épisodes

> **Cause-racine** : une **activation générée par le #8** (RSI, EDR 069) à base d'`exp` n'est pas
> numériquement stable. Dans le forward, `excitation = H @ W_no_diag` est sommée sur ~172 nœuds → atteint
> des **centaines** ; sur un long épisode (300 ticks), `exp(centaines)` **overflow → H=inf → dW=NaN →
> genome.W=NaN** (l'apprentissage intra-vie Lamarckien réécrit le NaN dans le génome) → crash au
> `int(...)` suivant.

> **Les épisodes courts (~45 ticks) MASQUAIENT ce bug** : trop peu de ticks pour que l'instabilité
> diverge. Débloquer la survie (085) l'a fait surgir. C'est le genre de bug qu'on ne voit qu'en *changeant
> le régime* — ici, en faisant enfin vivre les agents longtemps.

## Correctif (root-cause, non-régressif)

**Borner l'ENTRÉE de l'activation** dans `mamba_agent` (forward + branche MCTS) :
```python
H = (1 - dt) * H + dt * activation(np.clip(excitation - thr, -30.0, 30.0))
```
- `tanh(±30) ≈ tanh(±800) ≈ ±1` → **non-régressif pour l'activation par défaut** (tanh).
- Stable pour **TOUTE** activation générée (exp, ELU, SELU…) : l'entrée bornée ne peut plus overflow.
- Défense en profondeur : `np.nan_to_num` dans `update_phenotype` (robustesse si un génome HoF chargé est
  déjà corrompu).

**Validation** : 146 tests verts ; 3 générations dans le monde sweet-spot (le chemin qui crashait) →
tous les W finis. Le re-test peut tourner.

## Signification

> C'est un bénéfice secondaire précieux du déblocage de la survie : on a **durci le connectome** contre
> l'instabilité numérique des activations auto-générées. Le #8 (RSI) peut désormais proposer des
> activations exotiques sans faire diverger l'agent sur les longs épisodes — un prérequis pour des vies
> longues et des comportements complexes.

## Statut

- `mamba_agent` : clipping de l'entrée d'activation (forward + MCTS) + `nan_to_num` défensif. **Connectome
  stable sur les longs épisodes**, 146 tests verts. Débloque le re-test langage (087).

## Variables d'expérience

Borne d'activation (±30), stabilité des activations générées par le #8, longueur d'épisode, autres
instabilités latentes que la survie longue pourrait révéler.
