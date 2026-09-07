---
id: SDR-G4
type: SDR
title: L'agent anticipe-t-il (capstone)
status: open
gate: G4
motivates: [EDR-095, EDR-142]
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
✅ **Fix de persistance LIVRÉ et VÉRIFIÉ le 2026-09-07** (`mamba_agent.py` : `planner_G` est
re-persisté APRÈS `update_transition` ; `tests/test_planner_g_persistence.py` PASSE sur cette branche,
test `slow`, 40 s). Il n'est donc plus « recommandé, WIP » — l'étape suivante est de tester `g`
bilinéaire ; mais le NEUTRE du linéaire (qui accumule pourtant) suggère que la forme de `g` n'est pas le
verrou. ⚠️ **Et la revue adversariale du 2026-09-06 va plus loin : ce NEUTRE est FORCÉ par la forme du
mesureur.** Sur les dims non-écrasées par l'obs, la transition exacte est
`ΔH_j = δ_j·(tanh(e_j − thr_j) − H_j)` : la variance de `ΔH` est dominée par le terme
ÉTAT-DÉPENDANT `−δ·H`, que tout `g` delta-constant-par-action ignore — le ratio tend vers 1 QUEL QUE
SOIT le contenu anticipable. Le plancher `r = 1.0` (g≡0) est donc IMPORTÉ (E8), pas mesuré. Le
plancher MESURÉ in situ est l'oracle **action-AGNOSTIQUE** (une carte linéaire-en-H, qui capture la
relaxation endogène du connectome sans anticiper quoi que ce soit) et la question honnête devient :
le `g` PER-ACTION bat-il l'agnostique, contre un bras à labels PERMUTÉS comme plancher de bruit ? Outil `tools/g_fidelity_probe.py` (injection champion + gating KuzuDB).
