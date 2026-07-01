# Ledger — chantier disjoint_heads_capacity (EDR 191)

Worktree : `.claude/worktrees/disjoint-capacity` (branche `chantier/disjoint-capacity`, off origin/main 94f193e).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-capacity.md`. Spec : `.../specs/2026-07-01-disjoint-heads-capacity-design.md` (commit 453d496).
Sweep de capacite (H reduit) : sous un trunc RARE, vraie interference ? credit plat recouvre-t-il encore l'avantage disjoint (153/154 robuste) ou l'archi compte-t-elle enfin ? Profs INDEPENDANTS (152). Modeles/bras REIMPLEMENTES parametres par H (fideles a 152/153 ; H=48 = sanity byte-identique). Zero src. EDR 191 (bloc 190+).

- 1er commit du chantier = rename EDR 155->190 (collision cross-session avec 155_Famine_Full_Pipeline PR#124), commit 7ca52c9.
- BASE plan = 453d496 (spec) ; plan+ledger a suivre.
- Task 1 (FlatModelH/DisjointModelH + _interference_cosine_h + _verdict_capacity) : pending.
- Task 2 (_train_arm_h + _train_flat_norm_h + report + main_capacity_check + smoke) : pending.
