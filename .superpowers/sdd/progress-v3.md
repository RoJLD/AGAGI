# Ledger — chantier disjoint_heads_v3 (EDR 154, V3)

Worktree : `.claude/worktrees/disjoint-v3` (branche `chantier/disjoint-v3`, off origin/main 7893e2c).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-v3.md`. Spec : `.../specs/2026-07-01-disjoint-heads-v3-design.md` (commit 7de3132).
Bras FLAT+Adam-par-tete : isole le residu ~21% d'EDR 153 (moments Adam separes vs architecture). Additif (nouveau fichier), reutilise `disjoint_heads_ab`+`disjoint_heads_confound` (sur main). Zero src. EDR 154 (bloc 150+).

- BASE plan = 7de3132 (spec+plan sur la branche).
- Task 1 (bras FLAT_PERHEAD + _verdict_v3) : complete (commit d787eb3, 4/4 tests dont autograd smoke OK). SPEC PASS + QUALITE Approved. 2 Minor = imports _train_arm/_recovery "orphelins" MAIS consommes par Task 2 (main_v3_check) -> non-issue. BASE = 4abae9f.
- Task 2 (report + main_v3_check + smoke) : complete (commit d12ecb5, 5/5 tests). SPEC PASS + QUALITE Approved. 1 Minor = mean_recovery absent du chemin SKIPPED_NO_TORCH (pattern herite de 153, inoffensif, torch present au run). BASE = d787eb3.
- 2/2 TASKS COMPLETES.
- REVUE FINALE OPUS : PRET A INTEGRER OUI, 0 Critical. Mecanisme 3-Adam verifie empiriquement propre (moments separes reels, zero etat croise, set_to_none correct). Caveats a graver : I1 (levier = regime optim par-tete = moments + N_HEADS updates trunc/step, pas m/v isoles), I2 (lr partage, lr-par-tete non teste), M3 (sanity : FLAT/DISJOINT doivent reproduire 153 seed-a-seed). Aucun fix code.
- RUN REEL (K=5 base=2200 STEPS=2000, set_num_threads(1), 2 passes BYTE-IDENTIQUES) : VERDICT PARTIAL (recovery moyen +0.729 ; 1 seed >=0.90, 2 <=0.79). Les moments Adam separes recouvrent COMME l'echelle de loss (153 : 0.792), PAS mieux -> le residu ~21% n'est PAS proprement les moments. Sanity M3 CONFIRME : FLAT/DISJOINT reproduisent 153 seed-a-seed exactement. Migration #5 inchangee (credit multi-tete, pas refonte disjointe). Suite = V4 (echelle+moments combines). v3_pass1/2.txt.
- Reste : commit EDR 154 + memoire + PR.
