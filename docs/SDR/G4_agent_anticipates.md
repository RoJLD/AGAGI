---
id: SDR-G4
type: SDR
title: L'agent anticipe-t-il (capstone)
status: open
gate: G4
motivates: [EDR-095, EDR-135]
requires_ref: true
---
# SDR-G4 — Planification instrumentale

Hypothèse : brancher l'organe de rêve sur `world_model.predict()` (vraie simulation, pas le
random-shooting latent réfuté EDR 095 ni le depth-1 linéaire réfuté) produit une anticipation
qui paye. KPI `anticipation_bench`, depth-k / g bilinéaire. Réf : spec §3 G4.

**Dé-pause + re-mesure (EDR-135).** L'arc était en pause car la fidélité de `g` sur obs riches rendait
n=0 (survie). EDR-129 (sweet-spot + champion, survie 66-135) lève ce blocueur : n=71 transitions
mesurables. Mais DEUX blocueurs plus profonds apparaissent : (1) l'organe `g` est **inerte in-world**
(bug d'ordre de persistance : `planner_G` extrait AVANT l'update de `compute_policy_gradient` → mean|G|=0,
update perdu chaque tick) ; (2) une fois le bug simulé-corrigé, `g` **linéaire** est **NEUTRE sur obs
riches** (median_ratio 1.008, 14/44 fav) alors qu'il est G_FIDELE dans la grille-jouet (0.132, 82 %) →
sa fidélité NE transfère PAS au monde riche (confirme l'« easy-grid caveat »). `SDR-G4` reste `open`.
Fix de persistance recommandé (1 ligne, `mamba_agent.py` — à coordonner, WIP //) PUIS tester `g`
bilinéaire ; mais le NEUTRE du linéaire (qui accumule pourtant) suggère que la forme de `g` n'est pas le
verrou. Outil `tools/g_fidelity_probe.py` (injection champion + gating KuzuDB).
