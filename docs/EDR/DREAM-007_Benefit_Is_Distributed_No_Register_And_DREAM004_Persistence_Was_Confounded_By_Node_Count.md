---
id: EDR-DREAM-007
type: EDR
title: "Il n'y a PAS de registre localisé : à compte de nœuds apparié (~8) aucun rôle ne reproduit le bénéfice (le meilleur = 9 % de tout) — le bénéfice est DISTRIBUÉ, et ça révèle que le « porté ≫ transitoire » de DREAM-004 était confondu par le NOMBRE de nœuds"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
corrects: [EDR-DREAM-004]
extends: [EDR-DREAM-006]
---

## Question
[[EDR-DREAM-006]] a montré que la localisation par rôle (input/hidden/output) est confondue par la
taille des groupes (59/5/108 nœuds). Design corrigé : specs **appariées en taille** (~5-8 nœuds) pour
que seul le RÔLE varie. Question : à compte égal, quel registre de l'état porté débloque la reproduction ?

## Méthode
Seam `DREAM_NOISE_GROUP` étendu avec des specs de ~5-8 nœuds, calibrées (comptes exacts, disjonction,
`test_dream_node_group_mask.py` 8/8) :
* **`action8`** = les 8 logits de déplacement PORTÉS (sorties preds 0-7) — les MÊMES nœuds que le bruit
  d'action transitoire de [[EDR-DREAM-004]], mais persistants dans `H`.
* `input8` / `outhi8` (8 sorties non-action) / `hidden` (les 5 du cœur) = contrôles à COMPTE ÉGAL.

n=12, `stoneage`, 25 agents, 80 ticks, organe 100 %. Endpoint PRIMAIRE `n_lived`. `H_all` = contrôle
positif intégré. Artefact : `results/dream_register_n12.json`.

## Résultats — `n_lived`

| bras | nœuds | ratio vs off | favorables | wilcoxon | vs `H_all` |
|---|---|---|---|---|---|
| **H_all** | 172 | **22.30×** | 12/12 | 0.0025 | — |
| action8 | 8 | 2.04× | 12/12 | 0.0025 | **÷10.96** (12/12) |
| outhi8 | 8 | 1.78× | 10/12 | 0.0108 | |
| hidden | 5 | 1.73× | 12/12 | 0.0025 | |
| input8 | 8 | 1.40× | 10/12 | 0.0376 | |

`H_all` reproduit `s0.2` de DREAM-004 à l'identique (22.30×, médiane 1260) → instrument validé.

## Verdict
**`NO_LOCALIZED_REGISTER__BENEFIT_IS_DISTRIBUTED__DREAM004_PERSISTENCE_CONFOUNDED_BY_COUNT`**

**1. Il n'y a pas de registre.** À compte apparié (~8 nœuds), tous les bras donnent 1.4-2.0× ; le
meilleur (`action8`) est à **9 %** de `H_all` (contraste direct ÷10.96, 12/12). Aucun rôle — action,
sortie, entrée, cœur — ne reproduit le bénéfice. Il est **DISTRIBUÉ** : il faut perturber une large
fraction de l'état porté (8 nœuds → ~2×, 172 nœuds → 22×). Ce n'est pas une porte qu'on débloque, c'est
un bassin dont on ne sort qu'en secouant beaucoup de dimensions — cohérent avec l'attracteur contractif
de [[EDR-DREAM-005]].

**2. Correction de DREAM-004.** `action8` PORTÉ (2.04×) ≈ le bruit d'action TRANSITOIRE de DREAM-004
(2.3-3.0×) sur les MÊMES 8 nœuds. Le « porté ≫ transitoire » de DREAM-004 (22× vs 3×) comparait donc
**172-nœuds-portés** vs **8-nœuds-transitoires** — deux facteurs à la fois. À compte égal, la
persistance sur ces 8 nœuds n'ajoute presque rien : **le 22× vient du NOMBRE de dimensions perturbées,
pas de la persistance en soi.** L'attribution mécaniste de DREAM-004 est donc partiellement
reportée : locus/persistance n'était pas le driver dominant, le **nombre de dimensions** l'est.

## Ce qui TIENT de DREAM-004/005, et ce qui bascule
* **TIENT** : le bruit d'action transitoire ne reproduit pas le bénéfice (13 %) ; `H_all` (172,
  porté) le reproduit (22×) ; la dissociation fourrage/reproduction ; l'attracteur contractif et le
  P2 rigoureux de DREAM-005 (le bruit d'action laisse l'état bit-identique).
* **BASCULE** : « c'est la PERSISTANCE qui fait tout » → « c'est la DISTRIBUTION (nombre de dimensions
  de l'état porté perturbées) ». La persistance reste nécessaire pour qu'un bruit atteigne l'état, mais
  à dimension égale elle n'est pas le multiplicateur.

## La portance RESTE nécessaire (le « confondant résiduel » se dissout à l'analyse)
J'ai d'abord noté comme test ouvert « transitoire sur TOUS les nœuds vs porté sur tous ». **Il est mal
posé** : les nœuds CACHÉS n'ont pas de canal transitoire — ils ne sont jamais lus en sortie, ils
n'agissent QUE portés. Or les cachés contribuent au bénéfice distribué (`hidden` seul = 1.73×). Donc
la **portance demeure nécessaire pour la part cachée** de l'effet ; on ne peut pas la remplacer par du
transitoire. Ce qui bascule n'est donc PAS « la portance est dispensable » mais « la portance n'est pas
le grand MULTIPLICATEUR — le nombre de dimensions l'est ». Sur le seul canal où transitoire ET porté
existent (les 8 logits d'action), ils sont équivalents (2.04× vs 2.3-3×) : c'est là, et là seulement,
que DREAM-004 a sur-attribué à la persistance.

## Leçon (registre) — le confondant de DREAM-004 attrapé en le CONTRÔLANT
DREAM-004 a comparé deux bras qui différaient sur DEUX axes (locus/persistance ET nombre de nœuds) et a
attribué l'effet au premier. C'est la classe E9 (généralisation) sous un autre visage : conclure sur un
facteur quand un second covarie. Il a fallu apparier le nombre de nœuds (DREAM-006→007) pour le voir.
*Un contraste à deux facteurs n'attribue à aucun.* Chaque raffinement de cet arc a révélé le confondant
du précédent — c'est le fonctionnement voulu, pas un échec.

Converge [[EDR-DREAM-006]], [[EDR-DREAM-005]], [[EDR-DREAM-004]], [[from-genome-flattens-architecture]],
REF-EXPERIMENT-PREFLIGHT.
