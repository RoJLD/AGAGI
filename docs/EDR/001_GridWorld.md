---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-001
type: EDR
title: "Passage au Reinforcement Learning (GridWorld)"
status: legacy
gate: foundational
---

# EDR 001 : Passage au Reinforcement Learning (GridWorld)

## Contexte
L'apprentissage supervisé (XOR) était insuffisant pour atteindre l'AGI (Embodied AI). Les réseaux doivent interagir avec une physique simulée pour faire émerger une intelligence de navigation.

## Décision
- Abandonner les datasets fixes (`X`, `y`).
- Créer `src/environments/gridworld.py`, un environnement pur NumPy 2D.
- Remplacer l'entraînement SGD par la sélection naturelle Darwinnienne (Fitness = Récompense accumulée).

## Conséquences
- L'IA apprend à se déplacer.
- La fitness favorise les cerveaux économes (pénalité $\lambda$).
- Le système gagne en scalabilité et respecte le Commandement 3 (Vectorisation NumPy).
