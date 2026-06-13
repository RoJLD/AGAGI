# EDR 083 : Co-évoluer l'USAGE du langage — tendance positive préliminaire

## Contexte

EDR 082 : imposer le décode-et-agis ne paye pas ; il faut SÉLECTIONNER l'usage. Test direct : on
n'impose RIEN — les agents ÉCOUTENT via leur connectome (`in_hear` → action) et ÉVOLUENT sous sélection
robuste (K=4) dans Lewis. Deux régimes : locuteurs **FIABLES** (têtes co-entraînées → `in_hear`
cohérent) vs **BRUITÉS** (connectome → `in_hear` ~ loterie 053). Si écouter un signal fiable est
sélectionné, la chasse doit mieux évoluer avec des locuteurs fiables. `tools/coevolve_language.py`.

## Résultat — tendance positive, sous le seuil de robustesse

| Locuteurs (15 gens) | Mammouths tués (moyenne ± écart, 8 ères) |
|---|---|
| **FIABLES** | 5.25 ± 3.11 |
| **BRUITÉS** | 3.62 ± 3.00 |
| écart | **+1.62 ± 1.63 (SE)** |

> **Tendance POSITIVE (+1.62 Mammouths)** quand les locuteurs sont fiables — l'OPPOSÉ du décode-et-agis
> *imposé* (082, qui était négatif). **Mais sous 2 SE** : préliminaire, pas robuste.

## Lecture

- Directionnellement, ça **soutient la thèse d'EDR 082** : laisser l'usage du langage ÉMERGER sous
  sélection (avec un signal fiable à exploiter) va dans le bon sens, là où l'imposer échouait. La
  différence clé : ici le connectome *évolue* à écouter ; en 082 on *forçait* l'action.
- Sous 2 SE → **à powerer** (R répétitions de la co-évolution complète) avant toute conclusion. La
  discipline du projet : un signal sous le seuil n'est pas un résultat (cf. 057/077/082).

## Résolution (POWERED, R=4) — la tendance rétrécit, non robuste

| | préliminaire (1 run) | **powered (R=4)** |
|---|---|---|
| écart FIABLE−BRUITÉ (Mammouths) | +1.62 | **+0.29 ± 0.65 (SE)** |
| par run | — | [+0.2, +0.2, −1.2, +2.0] |
| FIABLE>BRUITÉ | — | 75 % des runs |

> Le +1.62 préliminaire était **gonflé par un run chanceux (+2.0)**. Powered, l'écart tombe à **+0.29,
> sous 2 SE** : tendance *directionnelle* (75 % des runs positifs, et l'OPPOSÉ de l'imposition négative
> de 082) mais **NON robuste**. Co-évoluer l'usage va dans le bon sens, mais l'effet est **faible à cette
> échelle** (12 gens, survie courte, survivants=0). 5ᵉ fois qu'un signal rétrécit sous puissance — la
> discipline tient.

> **Implication** : rendre le langage fonctionnel demande **plus** que ce qu'on a appliqué — vraisem-
> blablement une **survie soutenue bien plus longue** (les agents meurent avant que la coordination paye)
> + une **pression de sélection explicite sur l'usage du signal** + beaucoup plus de générations. Le
> goulot n'est plus le code ni la compétence brute, mais la *durée de vie* + l'*intensité de sélection
> de l'usage*.

## Suite

## Statut

- `coevolve_language.py`. **Tendance positive préliminaire (+1.62 Mammouths, sous 2 SE)** : co-évoluer
  l'usage va dans le bon sens (vs l'imposer, 082), à confirmer en puissance.

## Variables d'expérience

R (puissance), nombre de générations, survie soutenue, fitness récompensant l'usage du signal, taille
de population, durée de vie.
