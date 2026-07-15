---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-006
type: EDR
title: "O1-Spiking Bytecode (V6 Core Refactoring)"
status: legacy
gate: foundational
---

# EDR 006 : O1-Spiking Bytecode (V6 Core Refactoring)

## Contexte
La Règle 10 impose une croissance itérative, mais le besoin d'un "Endogenous Control Flow" devenait impératif pour doter les agents de capacités de Test-Time Compute (réflexion longue) et d'asynchronisme. La fusion de 3 paradigmes avancés était nécessaire pour rester dans une implémentation NumPy pure et performante.

## Décision (V6)
Nous avons remplacé la boucle RNN classique par un **Interpréteur de Bytecode**.
1. **Le Génome** possède une séquence d'entiers (`[0, 1, 2, 4, 3]`) qui dicte l'ordre d'exécution (LIRE, ROUTER, PROPAGER, TEST_TIME, AGIR).
2. **Dataflow (Spiking)** : L'instruction `PROPAGER` n'utilise plus toute la matrice. Un neurone accumule un potentiel $H_{pot}$ et ne "tire" ($H_{active}$) que si son potentiel dépasse un seuil génétique $\theta$.
3. **O1 (Test-Time Compute)** : La 8ème sortie du cerveau est le Neurone de Patience. Lors de l'instruction `TEST_TIME`, si ce neurone a tiré, l'interpréteur annule l'action motrice et reboucle au début de la réflexion. 

## Conséquences
- L'espace de mutation est considérablement étendu (le Bytecode peut muter sa longueur et ses instructions).
- Le modèle échappe au dogme "1 cycle d'horloge = 1 action". Un agent peut théoriquement boucler 10 fois pour propager de l'information profondément dans son réseau avant de faire 1 pas physique.
- Cette fondation (V6 Core) est la clé de voûte de la future *Swarm Biosphere*. Un agent pourra "mettre en pause" ses actions motrices pour "télécharger" ou "écouter" les broadcasts génétiques de ses pairs.
