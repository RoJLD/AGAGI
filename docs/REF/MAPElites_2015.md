---
id: REF-MAPElites-2015
type: REF
title: Illuminating search spaces by mapping elites (MAP-Elites / Quality-Diversity)
url: https://arxiv.org/abs/1504.04909
method: archive de niches par descripteurs comportementaux ; garde le meilleur par cellule
lib: pyribs
maturity: production
---
# REF-MAPElites-2015 — Mouret & Clune (2015)

Quality-Diversity : illuminer l'espace par descripteurs comportementaux plutôt qu'optimiser
un seul optimum.

Pont AGAGI : `seed_ai/map_elites.py` (descripteur taille×tier) réimplémente MAP-Elites ; l'axe
A2 a montré QD≈HoF (pas de gain net). La lib SOTA `pyribs` (CMA-ME, descripteurs continus)
surpasse une grille discrète 8×4 — à adopter si l'axe diversité est rouvert.
