---
id: REF-LTC-2021
type: REF
title: Liquid Time-constant Networks
url: https://arxiv.org/abs/2006.04439
method: RNN à constante de temps adaptative (ODE) entraîné par gradient ; expressif à petit nombre de neurones
lib: ncps (mlech26l/ncps)
maturity: production
adopt_for: [EDR-111, ADR-003, EDR-115, EDR-134, EDR-135, EDR-137, EDR-138, EDR-139, EDR-140, EDR-141, EDR-143, EDR-144, EDR-145, EDR-146, EDR-147, EDR-148, EDR-158, EDR-159, EDR-160, EDR-161, EDR-162, EDR-163]
---
# REF-LTC-2021 — Hasani, Lechner et al. (AAAI 2021)

Le moteur « Liquid Mamba » d'AGAGI (`agents/mamba_agent.py`, δⱼ=sigmoid(W[j,j]), ODE
discrétisée) est une **réimplémentation main d'un LTC** — mais privée de ce qui le rend SOTA :
l'entraînement par **gradient** (autodiff), absent (numpy pur, ~5 nœuds cachés).

Pont AGAGI : adopter `ncps` (LTC/CfC officiels, PyTorch) entraînés par gradient est le levier
direct contre le **verrou substrat** prouvé par EDR-111 (le monde exige l'outil mais le
substrat ne le prend pas). Axe 1 du plan de migration.
