---
id: REF-REINFORCE-1992
type: REF
title: Simple statistical gradient-following algorithms for connectionist RL (REINFORCE)
url: https://doi.org/10.1007/BF00992696
method: gradient de politique à haute variance ; la variance croît avec l'horizon temporel
lib: stable-baselines3 (PPO/A2C)
maturity: production
rediscovered_by: [EDR-077]
---
# REF-REINFORCE-1992 — Williams (Machine Learning, 1992)

La variance du gradient de politique à travers le temps est connue depuis 1992 ; c'est la
raison d'être des correctifs SOTA (baselines, GAE, clipping de PPO/TRPO).

Pont AGAGI : EDR-077 redécouvre empiriquement « le BPTT NUIT en RL » = exactement cette
variance. Levier d'adoption : un optimiseur RL moderne (PPO via stable-baselines3) plutôt
que notre Actor-Critic/BPTT numpy maison.
