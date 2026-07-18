# EDR 202 KCHAIN — Phase B FINDING : le binding compositionnel de COS était SCAFFOLD-DÉPENDANT

**Statut : Phase B livrée (code reviewed-clean, 12/12), run décisif NON lancé — le diagnostic pré-run a rendu le verdict.**
Le levier de la Phase B ne binde PAS la composition, même au cas de base K=2. Ce n'est pas un échec d'implémentation
(l'apprenant fonctionne parfaitement, cf. K=1) mais un **résultat de frontière** sur ce que le crédit peut bootstrapper.

## La question

EDR 202 devait tester si le levier COS (crédit-horizon × curriculum, verdict [2] CRÉDIT-ATTRIBUÉ / BOTH-NECESSARY,
#155/#159) **généralise à la profondeur de composition K**. Phase A (#163) a livré le monde KCHAIN(K) et prouvé sa
viabilité à tout K∈{2,3,4,5}. Phase B a livré l'apprenant (`NpChainLearner`), la **fenêtre-crédit W** (généralisation
du tick-return), le **curriculum progressif-K warm→cold**, et les verdicts gelés (courbe de généralité + 2×2).

## Le diagnostic pré-run (avant d'engager le run ~1h)

Un smoke au budget prévu a montré **surv=0, bind=0 à K=2 ET K=3** (verdict brut : `COS-SPECIFIQUE(2)`). Investigation
systématique (6 probes) pour départager sous-entraînement / bug / difficulté structurelle :

| Test | Résultat | Ce que ça élimine |
|---|---|---|
| **K=1** (bandit, always-CONSUME trivial) | surv **1.000** bind **1.000** cons_rate **1.000** | l'apprenant/REINFORCE/fenêtre-W n'est PAS buggé |
| K=2, budget {40,80,160,320} | collapse do-nothing, surv 0 | pas un manque de budget (pire avec plus) |
| K=2, E0 {16,32,64} × entropie {0.01,0.05} | surv 0 partout | pas E0 ni exploration |
| K=2, recuit graduel c_empty 0.5→6, R∈{4,8} | collapse (do-nothing @R=4 / always-consume @R=8), surv 0 | pas le saut warm→cold, pas R |
| **K=2, prog OBSERVABLE** | surv 0 aussi | **pas le compteur caché / l'absence de BPTT** |

Observation clé : en **warm** (coût mis-émission relâché + entropie) l'agent consomme et **réussit souvent**
(`cons_ok` élevé, ex. 4721/25512) — l'exploration TROUVE la séquence STEP→CONSUME. Mais il ne **retient jamais** un
CONSUME conditionné précisément : au passage à coût plein il collapse vers une politique dégénérée (do-nothing, ou
always-consume à haut R). La précision de timing du warm (~12%) est très en-dessous du seuil de rentabilité de la loi
de rétention `R·P > coût·(1−P)` (ici P>0.6 requis).

## Cause racine : le succès de COS reposait sur son ÉCHAFAUDAGE

L'apprenant fonctionne (K=1 parfait). Le mur est le **bootstrap du crédit compositionnel STEP→CONSUME en séquence
plate** — et il révèle **ce qui faisait marcher COS** :

- **COS avait un bit de phase** (S1-craft / S2-consume OBSERVABLE) + un **tick-return créditant la PAIRE craft+consume
  comme une unité**. Le rythme à 2 temps était **donné par l'observation** ; l'agent n'avait qu'à apprendre une règle
  réactive par phase.
- **KCHAIN** (séquence plate, `prog` caché OU observable, fenêtre glissante) exige que l'agent **auto-organise** le
  rythme STEP×(K−1)+CONSUME **sans scaffold de rythme**. C'est un problème de crédit compositionnel qualitativement plus
  dur — il échoue dès **K=2**, avant toute question de profondeur.

Corollaire méthodologique : **la fenêtre glissante W n'était PAS une généralisation fidèle du tick-return de COS**
(crédit apparié tick-aligné + rythme observable). Elle ne reproduit même pas le cas de base de COS.

## Le finding (converge la thèse)

**Le binding compositionnel de COS était SCAFFOLD-DÉPENDANT.** Le crédit (tick-return + curriculum) ne bootstrappe la
composition means→ends **que si la STRUCTURE DE TÂCHE fournit un rythme observable** qui découpe la composition en
décisions réactives. Retire ce scaffold → le même levier échoue au cas de base, malgré un substrat capable (K=1),
un budget suffisant, un headroom calibré, un curriculum warm→cold et un recuit graduel.

Ça **sharpe la loi transversale** (`[[warm-start-transversal-law]]`, `[[decisive-substrate-thesis-test]]`) : le verrou
est bien le crédit/objectif — et plus précisément, **la capacité du crédit à bootstrapper dépend de la structure de
l'objectif/tâche**. « IMPOSER via l'objectif bat SÉLECTIONNER » a une condition : l'objectif doit exposer un rythme que
le crédit peut suivre. C'est aussi cohérent avec l'audit mémoire (`[[memory-architecture-audit]]` : la mémoire paie en
isolation avec BPTT mais pas in-world sans crédit temporel) et avec `[[lang-referential-capability]]`/LANG-006 (le
langage paie SSI la tâche exige de résoudre une asymétrie — la structure de tâche décide).

## Statut & suite

- **Phase A** = acquis solide, reste sur PR #163 (monde KCHAIN viable tous K).
- **Phase B** = code livré + reviewed-clean (12/12) conservé comme INSTRUMENT (il a servi tous les diagnostics). Le run
  `--kchain` n'est PAS lancé : son verdict brut `COS-SPECIFIQUE(2)` serait **trompeur** (il refléterait l'échec de
  bootstrap au cas de base, pas une limite de profondeur). Ce document EST le résultat de la Phase B.
- **Piste future non retenue ici** (choix robla « reporter le finding ») : un rework du levier en tick-return fidèle
  sur ticks explicites de K sous-pas + rythme observable répondrait à la question profondeur, mais risquerait d'être
  trivial (GÉNÉRIQUE) une fois le rythme scaffoldé — l'intérêt scientifique s'est déplacé vers le finding scaffold.
