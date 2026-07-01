# EDR 123 — L'avantage du gradient ne s'ELARGIT PAS avec le delai (horizon de credit REFUTE) ; mais BPTT domine la mutation a TOUS les delais

> **Date** : 2026-06-30. **Verdict pre-enregistre** : `HORIZON CONFIRME` si gap(D_max) - gap(D_min) >= 0.20 ET (exists D : bptt>=0.90 ET mut<=0.65) ; sinon `HORIZON REFUTE`.
> **Resultat** : **HORIZON REFUTE** (delta gap 0.106 < 0.20 ; la mutation ne s'effondre jamais sous 0.65). L'avantage du gradient est ~CONSTANT (+0.08 a +0.24), pas un effet d'horizon qui s'elargit.
> **Outil** : `tools/memory_credit_horizon.py` (`main_credit_horizon`) + bras mutation `tools/grad_mem.py::train_mutation`. **Seed** : 1167 (smoke 99167). **Commit** : dda4080.
> **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-06-30-memory-credit-horizon*`. Chantier P1 de l'audit memoire (`docs/AUDIT_MEMOIRE_INTELLIGENCE.md`).

## 1. Question

EDR 067 a montre que le BPTT resout un K-bit recall (0.78->1.00) la ou la mutation sature, mais a
**delai fige (D=3)**. EDR 119/120 (session //) ont localise le verrou de la tache COMPOSITIONNELLE dans
l'**assignation de credit** (TD ne franchit pas la frontiere d'un pas), la memoire etant PORTEE par H
(AUC~0.90). Question jamais testee : si on fait VARIER le delai D d'un recall, l'**avantage du gradient
sur la mutation s'ELARGIT-il quand D croit** ? Si oui -> le verrou est l'horizon de credit (assigner du
credit a travers le temps) et l'effet doit s'amplifier avec le delai. Sinon -> le delai n'est pas le
facteur separateur.

## 2. Methode

Banc `memory_credit_horizon` : reseau simplifie numpy (dynamique LTC de `grad_mem`), tache K-bit recall
(encoder K bits -> D ticks silencieux -> "go" -> relire les K bits). Frontiere = accuracy (sign-match)
vs delai `D in {1,3,6,10,16,24}` a `K=4` fixe, R=3 seeds APPARIES, `epochs=400`. Deux bras sur le MEME
reseau/tache/budget : **BPTT** (`train`, Adam) vs **mutation** (1+1)-ES same-batch (`train_mutation`).
Verdict porte par la croissance du gap et l'effondrement de la mutation. **Equite (revue opus)** : a
epochs egal la mutation fait 2 forwards/epoch (incumbent+candidat) vs 1 pour BPTT -> l'asymetrie de
compute joue CONTRE un faux CONFIRME (la mutation est sur-, pas sous-, dotee).

## 3. Resultat (run pre-enregistre, seed 1167, R=3, 2 passes byte-identiques)

```
  D | acc_bptt acc_mut |   gap
   1 |    1.000  0.900 | +0.100
   3 |    1.000  0.917 | +0.083
   6 |    0.990  0.882 | +0.108
  10 |    1.000  0.760 | +0.240
  16 |    0.979  0.802 | +0.176
  24 |    0.968  0.762 | +0.206
  D_max(acc>=0.95) : bptt=24  mutation=0
  VERDICT : HORIZON REFUTE
```

`gap(D=24) - gap(D=1) = 0.206 - 0.100 = 0.106 < 0.20` (pas de croissance suffisante) ET la mutation ne
descend jamais sous 0.65 (min 0.760 a D=10) -> les deux conditions du CONFIRME echouent -> **REFUTE**.
Determinisme verifie (pass 1 == pass 2 au chiffre pres).

## 4. Lecture (mon hypothese est FALSIFIEE, avec une nuance importante)

- **L'horizon de credit (croissance dramatique de l'avantage avec D) est REFUTE.** Le gap monte
  modestement (~0.10 a D=1 -> ~0.20 a D>=10) puis **plafonne** ; il n'atteint pas la marge 0.20 et la
  mutation **ne s'effondre pas** (reste ~0.76-0.92 meme a D=24). L'avantage du gradient est un **ecart
  de competence ~CONSTANT**, pas une falaise qui s'ouvre avec le delai.
- **MAIS BPTT DOMINE a TOUS les delais.** Par le critere strict `acc>=0.95`, la frontiere est
  **bptt=24 vs mutation=0** : BPTT resout le recall a tout delai teste, la mutation jamais parfaitement.
  Le gradient est un meilleur optimiseur ICI aussi (raffine EDR 067 : il resout a TOUT D, pas seulement
  en repoussant une frontiere).
- **Recall-across-delay != credit gap compositionnel.** La mutation reste competente sur le RECALL
  (~0.8) la ou elle ECHOUE sur la tache COMPOSITIONNELLE d'EDR 119/120 (hit_end ~0). Le recall (tenir
  un bit puis le rendre) est plus facile que l'assignation de credit moyens->fins (agir en S1 SANS
  signal, recolter en S2). Conflater les deux serait une erreur : le verrou d'EDR 119/120 n'est pas le
  delai de memoire mais le credit a travers une action non-recompensee.

## 5. Caveats (perimetre du verdict)

- Verdict pre-enregistre au regime **(K=4, D<=24, N=19 = 3 caches)**. A K plus grand (tache plus dure)
  ou D plus long, la mutation pourrait s'effondrer et le gap s'elargir — mais ce serait du POST-HOC ;
  ici, dans le regime pre-enregistre, l'hypothese est falsifiee.
- `sigma=0.1` du bras mutation non balaye (expose en kwarg). L'asymetrie de compute (mutation 2x
  forwards/epoch) rend la DOMINANCE de BPTT conservatrice, pas un artefact ; et un REFUTE ne peut etre
  ecarte comme "mutation affamee".
- Reseau simplifie (pas le vrai MambaAgent) : choix delibere pour avoir le BPTT SANS torch (zero
  collision avec la migration moteur de la session //). Le BPTT sur le vrai substrat reste un chantier
  torch (gap audit P2/#4).

## 6. Suite & provenance

- **Suite** : l'avantage du gradient n'etant pas un effet d'horizon mais une dominance constante sur le
  recall, et le vrai verrou (EDR 119/120) etant le credit compositionnel (pas le delai de memoire), la
  priorite reste la migration moteur (substrat differentiable + assignation de credit, TD(lambda)/
  curriculum means->ends, [[sota-gap-substrate]]). Le banc reste reutilisable pour un balayage K dur ou
  D long si on veut sonder l'effondrement de la mutation.
- **Provenance** : `Harness(name="memory_credit_horizon")` -> `results/memory_credit_horizon_1167.json`
  (gitignore) ; seed 1167, smoke 99167 distinct ; 2 passes byte-identiques ; AUCUN test relance apres
  le run (lecon EDR 107). Tooling-only : `git diff src/` VIDE (zero collision session // torch).
- **Revue** : subagent-driven (Task 1 + Task 2 SPEC ok + quality Approved) ; revue finale **opus**
  READY TO MERGE — instrument equitable/apparie/falsifiable, asymetrie de compute biaisee CONTRE le
  faux CONFIRME.
