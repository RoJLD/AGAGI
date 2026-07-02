# Ledger — chantier disjoint_heads_synergy (EDR 192, V4)

Worktree : `.claude/worktrees/disjoint-synergy` (branche `chantier/disjoint-synergy`, off origin/main 7128add).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-synergy.md`. Spec : `.../specs/2026-07-01-disjoint-heads-synergy-design.md` (commit 665f453).
Bras combine FLAT_NORM_PERHEAD (echelle 153 x moments 154) : la synergie ferme-t-elle le residu ~21% (archi refutee ~100%) ou redondance ? Additif, reutilise disjoint_heads_ab (152) + disjoint_heads_confound (153). Zero src. EDR 192 (bloc 190+). Clot le sous-arc optimiseur (l'arc de fond deja clos par 191).

- BASE plan = 665f453 (spec) ; plan+ledger a suivre.
- Task 1 (_train_flat_norm_perhead + _verdict_v4) : pending.
- Task 2 (report + main_v4_check + smoke) : pending.
