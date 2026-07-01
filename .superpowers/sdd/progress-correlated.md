# Ledger — chantier disjoint_heads_correlated (EDR 155, V2)

Worktree : `.claude/worktrees/disjoint-correlated` (branche `chantier/disjoint-correlated`, off origin/main 1f1b5d0).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-correlated.md`. Spec : `.../specs/2026-07-01-disjoint-heads-correlated-design.md` (commit 2e66a9d).
Profs correles (sous-espace partage signe, sweep rho) : induit une vraie interference et re-teste si le credit-equilibrage plat (FLAT_NORM, 153) recouvre encore l'avantage DISJOINT. Additif (nouveau fichier), reutilise disjoint_heads_ab (152) + disjoint_heads_confound (153) sur main. Zero src. EDR 155 (bloc 150+).

- BASE plan = 2e66a9d (spec+plan sur la branche).
- Task 1 (_make_correlated_teachers + _verdict_correlated) : pending.
- Task 2 (report + main_correlated_check sweep + smoke) : pending.
