# Ledger — chantier g_bilinear_probe (EDR 193)

Worktree : `.claude/worktrees/g-bilinear` (branche `chantier/g-bilinear`, off origin/main 0cdcdf3).
Plan : `docs/superpowers/plans/2026-07-02-g-bilinear-fidelity.md`. Spec : `.../specs/2026-07-02-g-bilinear-fidelity-design.md` (commit ba55fbf).
Un g BILINEAIRE (ΔH = H.W_a, etat-dependant) est-il G_FIDELE la ou le lineaire d'EDR 135 etait NEUTRE ? Fit offline ridge sur transitions latentes reelles d'un rollout env-grille deterministe. Additif, import read-only de g_fidelity_probe (EDR-135) + src.mamba_agent. Zero modif src/probe. EDR 193 (bloc 190+, distant du debordement // ~161).

- BASE plan = ba55fbf (spec) ; plan+ledger a suivre.
- Task 1 (machinerie offline pure-numpy : split + fits + ratios + verdict) : pending.
- Task 2 (rollout env-grille -> triplets + main_bilinear_check + smoke ; REMPLACE l'import de tete) : pending.
