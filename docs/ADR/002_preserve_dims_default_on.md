---
id: ADR-002
type: ADR
title: preserve_dims ON par defaut (evolution topologique active)
status: validated
gate: null
motivates: []
triggers: []
tests: []
---
# ADR-002 — Évolution topologique en prod

Décision : `preserve_dims=True` par défaut (PR #58) → `from_genome` n'aplatit plus l'archi,
`add_node` persiste, les réseaux grossissent (cap soft 256). Escape-hatch `=False` conservé.
Corrige le bug keystone. Réf : mémoire from-genome-flattens-architecture.
