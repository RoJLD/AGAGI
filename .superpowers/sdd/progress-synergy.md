# Ledger — chantier disjoint_heads_synergy (EDR 192, V4)

Worktree : `.claude/worktrees/disjoint-synergy` (branche `chantier/disjoint-synergy`, off origin/main 7128add).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-synergy.md`. Spec : `.../specs/2026-07-01-disjoint-heads-synergy-design.md` (commit 665f453).
Bras combine FLAT_NORM_PERHEAD (echelle 153 x moments 154) : la synergie ferme-t-elle le residu ~21% (archi refutee ~100%) ou redondance ? Additif, reutilise disjoint_heads_ab (152) + disjoint_heads_confound (153). Zero src. EDR 192 (bloc 190+). Clot le sous-arc optimiseur (l'arc de fond deja clos par 191).

- BASE plan = 665f453 (spec) ; plan+ledger a suivre.
- Task 1 (_train_flat_norm_perhead + _verdict_v4) : pending.
- Task 2 (report + main_v4_check + smoke) : complete (commit 7ce062b, 5/5 tests). SPEC OK + QUALITE Approved (reviewer diff char-par-char + verif signatures ab/confound). BASE = b78e380.
- 2/2 TASKS COMPLETES.
- REVUE FINALE OPUS : PRET A INTEGRER OUI, 0 Critical. A PREDIT PARTIAL avant run (dry-run K=3 : 0.680, SYNERGY_CLOSES exclu ; 154 reproduit 0.732 = sanity). Mecanisme : Adam par-tete ANNULE le scaling constant (m^/sqrt(v^) inchange). Caveats e (seul non-declenchement de SYNERGY_CLOSES a du poids ; NO_SYNERGY=PARTIAL) + f (192 sous les leviers = redondance pas pro-archi). Aucun fix code.
- RUN REEL (K=5 base=2200 STEPS=2000, 2 passes BYTE-IDENTIQUES) : PARTIAL recovery +0.697 (1/5 >=0.90). Combiner echelle+moments fait MOINS bien que chaque levier seul (153: 0.79, 154: 0.73) -> REDONDANCE (meme canal = credit par-tete), legere anti-synergie (seed 2202: 0.120). Sanity FLAT/DISJOINT = 153/154 exact. Sous-arc optimiseur CLOS ; arc disjoint 152->192 complet. syn_pass1/2.txt.
- Reste : commit EDR 192 + memoire + PR.
