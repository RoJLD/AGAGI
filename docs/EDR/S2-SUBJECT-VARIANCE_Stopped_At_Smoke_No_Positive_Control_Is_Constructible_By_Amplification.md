---
id: EDR-S2-SUBJECT-VARIANCE
type: EDR
title: "ARRÊTÉ AU SMOKE : aucun contrôle POSITIF in-world n'est constructible par amplification dans `stoneage` — plus on couple la politique à l'observation, moins on survit (27,5 → 13,8 → 6,2)"
status: active
verdict: STOPPED_AT_SMOKE_NO_INWORLD_POSITIVE_CONTROL_BY_AMPLIFICATION
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
extends: [EDR-S2-BLIND-CHAMPION]
---

> ⚠️ **Aucune mesure de la DV scellée n'est rapportée** : le smoke a fait échouer les contrôles, et la
> règle (`docs/preregistrations/S2-SUBJECT-VARIANCE.json`) impose alors `INDETERMINE-INSTRUMENT` sans
> lire la suite. Ce record grave la règle, le résultat du smoke, et les deux mesures qu'il a produites.

## La question, et l'amendement qui l'a précédée

`EDR-S6-FALLBACK-RATE` a montré en mini-monde que le marqueur de demande mesure si **CE sujet** a un
repli survivable sans X. Prédiction in-world : dans le MÊME monde, des sujets d'origines différentes
doivent rendre des verdicts différents. Sinon la propriété est celle du monde, et S6 est borné au
jouet — résultat qui RENFORCE les records existants.

**La règle de lecture d'origine était elle-même une famille non contrôlée**, et c'est la garde `E23`
(`assert_control_family`, livrée la veille) qui l'a fait voir AVANT tout run : « ≥ 2 sujets rendent
des verdicts différents » sur 7 sujets, c'est **21 paires**, et `ablation_verdict` lit une médiane sur
K ères — donc le critère pouvait être franchi alors que le sujet ne change RIEN. Correctif scellé
avant la première cellule : un **bras de RÉPLICATION du MÊME sujet** (7 graines de monde), qui MESURE
le désaccord dû au seul bruit. La lecture devient `d_inter > d_intra`, et `VERDICT_IS_WORLD_BOUND`
exige en plus `d_intra == 1` — sinon on ne distingue pas « le monde décide » de « l'instrument ne voit
rien ».

## Le smoke (`results/s2_subject_variance_smoke.json`, 4 cellules, 122 s)

| cellule | rôle | verdict | survie médiane | plancher 24,0 |
|---|---|---|---|---|
| champion HoF | sujet | `PERCEPTION_DECOY` | 27,5 | au-dessus |
| réplicat (seed 3026) | réplicat | `PERCEPTION_DECOY` | 24,2 | au-dessus |
| **réflexe câblé** | contrôle négatif | `INCONCLUSIVE_DEGENERATE` | **8,0** | SOUS |
| **lecteur câblé** | contrôle positif | `INCONCLUSIVE_DEGENERATE` | **6,0** | SOUS |

Les deux contrôles câblés à la main **ne franchissent pas le plancher** `PLANCHER_NOPERC["stoneage"]`
= 24,0, donc l'instrument refuse de les lire — et la règle refuse de lire quoi que ce soit d'autre.
Verdict : **`INDETERMINE-INSTRUMENT`**. Coût : 30,6 s/cellule, soit ~9 min pour le plan complet, qui
n'a PAS été lancé.

**Grandeurs scellées, publiées telles quelles** (le cliquet `check_preregistration_applied` exige
qu'une DV scellée ne soit jamais silencieuse) : chaque cellule publie `intact_median` face à `floor`
(24,0 pour `stoneage`), son `within_ratio` — 0,991 / 0,924 / 0,970 / 1,000 dans l'ordre du tableau —
et son `between_ratio` (champion vs réflexe, mesuré par l'instrument mais NON décisif ici : la règle
scellée ne le lit que dans des branches non atteintes). Le monde `soup` n'a PAS été mesuré : le design
est mono-monde par construction, parce que `stoneage` est le seul point où le plancher no-perception
est mesuré au régime gravé — mesurer un autre monde exigerait de re-sceller (issue 2 ci-dessous).

## Les deux mesures que le smoke a produites

**1. Le contrôle NÉGATIF existe, mais il faut le DÉRIVER du champion.** Un génome bâti de zéro
(diagonale +10) survit 8 ticks ; un champion dont on annule les lignes d'entrée de `W` en survit
**38,2** — au-dessus du plancher, et il rend bien `PERCEPTION_DECOY`. C'est ce contrôle négatif qui a
ouvert [[EDR-S2-BLIND-CHAMPION]].

**2. Le contrôle POSITIF n'est PAS constructible par amplification, et la dose-réponse dit pourquoi.**
Multiplier le couplage `obs → action` du champion effondre la survie, monotonement :

| couplage `obs → action` | survie médiane | verdict |
|---|---|---|
| ×1 (champion) | 27,5 | `PERCEPTION_DECOY` |
| ×3 | **13,8** | `INCONCLUSIVE_DEGENERATE` |
| ×8 | **6,2** | `INCONCLUSIVE_DEGENERATE` |

Plus la politique dépend de l'observation, moins elle survit — même direction qu'[[EDR-EVO-011]]
(r=0,631) et que le champion aveuglé qui survit 39 % mieux. Il n'existe donc pas, dans ce monde et par
cette voie, de sujet qui soit à la fois **au-dessus du plancher** et **dépendant de la perception** :
c'est précisément ce qu'un contrôle positif in-world devrait être.

## Ce que ça dit du marqueur de demande in-world

C'est une **contrainte de constructibilité**, pas encore un verdict. Le gabarit within-subject
(REF-DEMAND-MARKER) a été validé sur vérité-terrain dans quatre modalités PROXY ; in-world, ce smoke
est la première tentative documentée de lui fournir un contrôle positif, et elle échoue par
amplification. Trois issues restent ouvertes, dans cet ordre de coût :

1. un sujet dont la dépendance perceptive est **bénéfique** (câbler un comportement obs-dirigé
   utile — approcher la proie, fuir l'apex) plutôt qu'amplifier un couplage existant ;
2. un autre monde : `PLANCHER_NOPERC` est mesuré pour 5 mondes, et rien n'oblige à rester dans
   `stoneage` ;
3. abaisser le plancher du contrôle : **refusé** — ce serait déplacer le seuil après avoir vu le
   résultat, exactement ce que la pré-inscription existe pour empêcher.

⚠️ La lecture de ce smoke est bornée par [[EDR-S2-BLIND-CHAMPION]] : le même jour, le no-op exact a
chiffré à **±6-8 %** le plancher de bruit de `run_ablation_map` (désynchronisation de bande RNG). Les
écarts rapportés ici (27,5 vs 13,8 vs 6,2) lui sont très supérieurs et ne sont pas menacés ; les
verdicts `PERCEPTION_DECOY` du champion, eux, se lisent à l'intérieur de ce bruit.

Converge [[EDR-S6-FALLBACK-RATE]] (la question), [[EDR-S2-BLIND-CHAMPION]] (le contrôle négatif et le
plancher de bruit), [[EDR-EVO-011]] (même direction, mesurée sur un lecteur câblé).
