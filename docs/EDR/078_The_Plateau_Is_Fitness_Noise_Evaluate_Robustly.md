# EDR 078 : Le plateau de compétence est un problème de MESURE — évaluer robustement

## Contexte

EDR 077 : la mutation forge bien « quand le signal est bon » ; la biosphère évalue un génome sur UNE ère
(extinction ~30-60 ticks) — une fitness ULTRA-BRUITÉE (≈ `eval_B=1`, un seul échantillon). Hypothèse :
le plateau de compétence (076) vient du BRUIT du signal de fitness, pas du moteur. Test sur banc
(foraging-mémoire RL) : on fait varier `eval_B` (nb d'épisodes pour évaluer un génome) et on mesure la
compétence forgée par la mutation. `tools/fitness_noise.py`, 3 seeds, 300 gens.

## Résultat — relation MONOTONE, nette

| `eval_B` (propreté du signal) | compétence forgée |
|---|---|
| **1** (~ biosphère, 1 ère bruitée) | **2.03 ± 0.39** |
| 2 | 2.79 ± 0.37 |
| 4 | 3.51 ± 0.58 |
| 8 | 4.32 ± 0.19 |
| 16 | 4.74 ± 0.08 |
| **64** (signal propre) | **5.79 ± 0.13** |

> **La compétence forgée passe de 2.0 à 5.8 (≈ ×3) UNIQUEMENT en nettoyant le signal de fitness.**

## Le détail qui ferme tout

> `eval_B=1` (fitness d'une seule ère, comme la biosphère) donne **2.03** — *exactement* le plateau de
> 076 **et** le score du BPTT (2.10, EDR 077). En évaluant chaque génome sur **une seule ère bruitée**,
> la biosphère se condamne au même mauvais résultat que le pire moteur. Avec un signal propre
> (`eval_B=64`), la mutation atteint **5.79** — elle BAT le one-step (4.96) et ÉCRASE le BPTT (2.10).

## Conclusion — le plateau est la MESURE, pas le moteur

> **Le plateau de compétence (076) n'est NI le moteur** (la mutation forge à 5.8 avec un bon signal)
> **NI l'absence de gradient** (le BPTT est pire, 077) — **c'est la fitness BRUITÉE.** La sélection sur
> un seul échantillon bruité choisit les génomes CHANCEUX, pas les BONS ; le cliquet best-ever VERROUILLE
> même une chance. **Levier : ÉVALUER ROBUSTEMENT** — plusieurs eres/épisodes par génome avant sélection.

## L'arc de la compétence se résout

| EDR | acquis |
|---|---|
| 075 | la compétence est le goulot (le langage ne paye pas sans elle) |
| 076 | la compétence PLAFONNE sous mutation+extinction (cliquet maintient) |
| 077 | le BPTT n'est PAS le remède — il NUIT en RL (variance) |
| **078** | **le remède = évaluation ROBUSTE (le plateau était du bruit de mesure)** |

## Application à la biosphère (concrète, actionnable)

La biosphère sauve au HoF les top-5 d'UNE ère (life_score bruité). Correctif : **ré-évaluer les
candidats sur K eres indépendantes et moyenner** avant de committer au HoF — la sélection cesse de
récompenser la chance. Coût : K× l'évaluation, mais le gain (×3 sur banc) le justifie largement. À
valider sur `evolve_competence.py` (donner une fitness robuste → le plateau de 076 doit se lever).

## Honnêteté

- Banc individuel (chaque génome évalué solo) ; la biosphère a une fitness de GROUPE
  (fréquence-dépendante) — une source de bruit *en plus*, qui va dans le même sens (la robustesse aide).
- Caveat : robuste = K× plus cher. L'arbitrage K vs coût reste à régler dans le vivant.

## Statut

- `fitness_noise.py` (banc) + `train_mutation(eval_B=...)`. **Plateau de compétence = bruit de fitness,
  prouvé** (2.0 → 5.8 monotone). Levier biosphère : évaluation robuste (multi-ères) du HoF.

## Variables d'expérience

K (nb d'évaluations par génome) vs coût, fitness de groupe vs solo, longueur d'ère, application à
`evolve_competence` (HoF robuste), réduction de variance de la fitness biosphère.
