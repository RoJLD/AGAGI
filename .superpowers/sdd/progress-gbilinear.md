# Ledger — chantier g_bilinear_probe (EDR 193)

Worktree : `.claude/worktrees/g-bilinear` (branche `chantier/g-bilinear`, off origin/main 0cdcdf3).
Plan : `docs/superpowers/plans/2026-07-02-g-bilinear-fidelity.md`. Spec : `.../specs/2026-07-02-g-bilinear-fidelity-design.md` (commit ba55fbf).
Un g BILINEAIRE (ΔH = H.W_a, etat-dependant) est-il G_FIDELE la ou le lineaire d'EDR 135 etait NEUTRE ? Fit offline ridge sur transitions latentes reelles d'un rollout env-grille deterministe. Additif, import read-only de g_fidelity_probe (EDR-135) + src.mamba_agent. Zero modif src/probe. EDR 193 (bloc 190+, distant du debordement // ~161).

- BASE plan = ba55fbf (spec) ; plan+ledger a suivre.
- Task 1 (machinerie offline pure-numpy) : complete (commit 0197451, 6/6 tests, ridge valide numeriquement). SPEC OK (byte-identique) + QUALITE Approved. BASE = c7e14a2.
- Task 2 (rollout env-grille + main_bilinear_check + smoke) : complete (commit faaba32, 7/7 tests). SPEC OK (verbatim) + QUALITE Approved. Minors herites du brief (_median recompute, import mid-file, np.random.seed global = pattern EDR-135). BASE = 0197451.
- 2/2 TASKS COMPLETES (machinerie de base).
- REVUE FINALE OPUS : NON PRET, 1 Critical (2 facettes). C1 : la premisse est FAUSSE (verifie en relancant EDR 135 : env-grille = G_FIDELE median 0.75, NEUTRE = synthetique). C2/Q5 : un bilin<learned sur env-grille = artefact de decalage one-hot d'ENTREE (pos deterministe par action), pas anticipation latente. Opus predit BILINEAR_FIDELE mais ARTEFACTUEL.
- DECISION UTILISATEUR : PIVOT vers I/O vs caches (re-examine EDR 135). Controle decisif = ratio restreint aux noeuds CACHES [I, N-O) = [14,64) (layout verifie mamba_agent:356-376). Reutilise collecte+ridge, ajoute masque + verdict de decomposition. Spec REFORMULE (v2). NE PAS lancer l'ancien run (artefactuel).
- Reste : plan-delta -> SDD (rework) -> run 2-passes -> EDR 193 + memoire + PR.
