---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-007
type: EDR
title: "Swarm Biosphere (In-Vivo Evolution)"
status: legacy
gate: foundational
---

# EDR 007 : Swarm Biosphere (In-Vivo Evolution)

## Contexte
L'algorithme génétique classique d'AGIseed fonctionnait par "Générations". Il arrêtait le monde physique tous les N pas pour évaluer la fitness, tuer les faibles et croiser les forts. Cette approche "Laboratoire" empêchait les comportements sociaux émergents (coopération asynchrone, HGT).

## Décision (V7.0)
- **Destruction des Générations** : Le monde est devenu continu (`Biosphere3D`). La boucle de jeu ne s'arrête plus.
- **Métabolisme & Mort** : Chaque action motrice et chaque "cycle d'horloge" du Bytecode consomme de l'Énergie. Un agent qui n'optimise pas son code ou ne chasse pas tombe à $0$ d'énergie et est instantanément effacé de la matrice. L'Agent ressent implicitement l'urgence de vivre.
- **Mitose Asexuée** : Si un agent atteint une abondance d'énergie ($100.0$), il subit une division cellulaire. Il dépense 50 points pour créer une copie mutée de lui-même. C'est l'essence même de l'Open-Ended Evolution (Vie Artificielle).

## Conséquences
- La fitness n'est plus une "fonction de coût" dictée arbitrairement par le créateur. La survie EST la seule mesure de succès.
- Des phases massives d'extinction peuvent avoir lieu si aucune mutation viable n'émerge assez vite.
- Le monde physique dicte désormais la démographie du réseau (les zones riches en proies auront une densité d'agents plus élevée).
