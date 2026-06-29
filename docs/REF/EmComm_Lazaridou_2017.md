---
id: REF-EmComm-2017
type: REF
title: Multi-Agent Cooperation and the Emergence of (Natural) Language + framework EGG
url: https://arxiv.org/abs/1612.07182
method: jeux référentiels de Lewis entraînés par gradient ; émergence de conventions sous demande communicative
lib: EGG (facebookresearch/EGG)
maturity: production
rediscovered_by: [EDR-047]
adopt_for: [EDR-047]
---
# REF-EmComm — Lazaridou et al. (ICLR 2017) + EGG (Kharitonov et al. 2019)

Sous-champ entier de l'*emergent communication* : le langage référentiel émerge quand la
tâche le rend nécessaire (jeu de Lewis), avec un framework outillé (EGG).

Pont AGAGI : EDR-047 (« le langage référentiel émerge sous demande de Lewis ») est le résultat
phare de ce sous-champ. `seed_ai/referential_head.py` réimplémente à la main un signaling game
+ straight-through estimator → adopter EGG donnerait métriques, vocab compositionnels et
baselines gratuits.
