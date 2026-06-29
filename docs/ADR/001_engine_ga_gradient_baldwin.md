---
id: ADR-001
type: ADR
title: Moteur GA externe + gradient interne + Baldwin
status: validated
gate: null
motivates: []
triggers: []
tests: []
---
# ADR-001 — Le moteur invariant des portes

Décision : le GA explore le substrat (topologies, demandes-monde, diversité), le gradient
(Actor-Critic intra-vie) apprend dans la vie, Baldwin façonne des inits apprenables.
Le GA n'est PAS le moteur de l'intelligence mais de la recherche de substrat.
Fondé sur EDR 064/067-070 (mutation seule = chercheur faible). Réf : spec §2.
