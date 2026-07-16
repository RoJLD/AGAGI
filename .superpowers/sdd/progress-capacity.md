# Ledger — chantier disjoint_heads_capacity (EDR 191)

Worktree : `.claude/worktrees/disjoint-capacity` (branche `chantier/disjoint-capacity`, off origin/main 94f193e).
Plan : `docs/superpowers/plans/2026-07-01-disjoint-heads-capacity.md`. Spec : `.../specs/2026-07-01-disjoint-heads-capacity-design.md` (commit 453d496).
Sweep de capacite (H reduit) : sous un trunc RARE, vraie interference ? credit plat recouvre-t-il encore l'avantage disjoint (153/154 robuste) ou l'archi compte-t-elle enfin ? Profs INDEPENDANTS (152). Modeles/bras REIMPLEMENTES parametres par H (fideles a 152/153 ; H=48 = sanity byte-identique). Zero src. EDR 191 (bloc 190+).

- 1er commit du chantier = rename EDR 155->190 (collision cross-session avec 155_Famine_Full_Pipeline PR#124), commit 7ca52c9.
- BASE plan = 453d496 (spec) ; plan+ledger a suivre.
- Task 1 (FlatModelH/DisjointModelH + _interference_cosine_h + _verdict_capacity) : complete (commit db172e1, 7/7 dont sanity H=48 byte-identique 152). SPEC OK + QUALITE Approved. BASE = d9fb899.
- Task 2 (_train_arm_h + _train_flat_norm_h + report + main_capacity_check + smoke) : complete (commit 022bb47, 8/8). SPEC OK + QUALITE Approved. Cannot-verify confirmes : _eval_losses renvoie value/pred (ab:133), _interference_cosine_h renvoie float. BASE = db172e1.
- 2/2 TASKS COMPLETES.
- REVUE FINALE OPUS : PRET A INTEGRER OUI, 0 Critical. Verifie fidelite END-TO-END byte-identique (H=48 reproduit 152/153 cos inclus). PREDIT INDUCED a H=3 (dry-run cos 5/5 negatif H=6/H=3). Important : recovery degenere a H=3/H=6 (disjoint perd son avantage global sous rarete) -> lire axe B a H=6 + gain brut ; caveat (e) a graver. Aucun fix code.
- RUN REEL (K=5 base=2200 H in {48,6,3}, 2 passes BYTE-IDENTIQUES) : INDUCED+CREDIT_ROBUST. H=48 cos+0.000 recovery+0.792 (=153 EXACT, sanity). H=6 cos-0.054 (3/5) INDUCED, improv-0.058 (disjoint NUIT!), recovery+3.82. H=3 cos-0.072 (4/5) INDUCED, recovery+1.56. -> capacite INDUIT le conflit (190 null = artefact sur-capacite) ET credit plat depasse disjoint (recovery>1) = CREDIT ROBUSTE a l'interference. Arc CLOS. caveat e (recovery degenere, lire H=6). cap_pass1/2.txt.
- Reste : commit EDR 191 + memoire + PR.
