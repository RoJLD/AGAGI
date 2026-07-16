# Ledger — chantier disjoint_heads_correlated (EDR 155, V2)

Worktree : `.claude/worktrees/disjoint-correlated` (branche `chantier/disjoint-correlated`, off origin/main 1f1b5d0).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-correlated.md`. Spec : `.../specs/2026-07-01-disjoint-heads-correlated-design.md` (commit 2e66a9d).
Profs correles (sous-espace partage signe, sweep rho) : induit une vraie interference et re-teste si le credit-equilibrage plat (FLAT_NORM, 153) recouvre encore l'avantage DISJOINT. Additif (nouveau fichier), reutilise disjoint_heads_ab (152) + disjoint_heads_confound (153) sur main. Zero src. EDR 155 (bloc 150+).

- BASE plan = 2e66a9d (spec+plan sur la branche).
- Task 1 (_make_correlated_teachers + _verdict_correlated) : complete (commit a32e400, 6/6 tests). SPEC OK + QUALITE Approved. Minors = imports consommes par Task 2, guard colnorm marginal, ordre dict garanti 3.7+. Constantes ab confirmees (D=32/K_A=4/P_PRED=8/TEACHER_SEED=777). BASE = d74dfc9.
- Task 2 (report + main_correlated_check sweep + smoke) : complete (commit be1b50c, 7/7 tests). SPEC OK + QUALITE Approved. 1 Minor = import mid-file dans le test (PEP8, conforme spec litteral). BASE = a32e400.
- 2/2 TASKS COMPLETES.
- REVUE FINALE OPUS : PRET A INTEGRER OUI, 0 Critical. A PREDIT NOT_INDUCED avant le run (dry-run K=5 rho=0.95 : cos in [-0.002,+0.039]). Sonde biaisee vers 0 (readout lineaire absorbe le signe SIGMA). Sweep propre (parite, pas de fuite RNG, colnorm OK). Caveats e/f/g. Aucun fix code (le null est le resultat attendu et honnete).
- RUN REEL (K=5 base=2200 rho in {0,0.6,0.95}, 2 passes BYTE-IDENTIQUES) : NOT_INDUCED+CREDIT_ROBUST. rho=0.95 cos +0.015 (0/5 <= -0.05). Confirme opus au chiffre pres. Corr = AIDE pas conflit (improv decroit 0.356->0.187). Axe B moot (denominateur degenere a rho eleve + B conditionne a A=INDUCED). Constat mecanistique : readout absorbe le signe, trunc H=48 surdimensionne = pas d'interference a induire. Suite EDR 156 = H reduit (pression capacite, PRESERVE la parite inter-bras). corr_pass1/2.txt.
- Reste : commit EDR 155 + memoire + PR.
