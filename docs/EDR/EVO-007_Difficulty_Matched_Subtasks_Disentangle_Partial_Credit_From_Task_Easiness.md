---
id: EDR-EVO-007
type: EDR
title: "Crédit PARTIEL ou sous-tâches plus FACILES ? — plan à difficulté appariée, n=12, et verdict de fréquence sur EVO-006"
status: active
verdict: PARTIAL_CREDIT_DOES_NOT_PRODUCE_INWORLD_READING
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-006]
---

## Question

[[EDR-EVO-006]] a conclu que le **crédit partiel** était le gradient manquant : à K=3 sous-tâches notées
indépendamment, l'évolution in-world bâtit un lecteur parfait là où le tout-ou-rien plafonnait. Le record
portait lui-même sa faiblesse en tête de ses hedges : **ses 3 sous-tâches n'étaient pas d'égale
difficulté**. `move` exige de gagner un `argmax` à 8 voies ; `throw` et `accept` sont de simples seuils de
signe où un unique poids suffit — et c'est `throw` qui a été appris.

Pire, en le relisant : **[[EDR-EVO-005]] (l'échec) n'avait qu'UNE sous-tâche, et c'était la plus DURE.**
Son nul confondait donc deux causes — « pas de crédit partiel » et « tâche unique trop difficile ». Deux
facteurs, jamais séparés :

| | 1 sous-tâche | 3 sous-tâches |
|---|---|---|
| **dure** (`move`) | EVO-005 : échec | — |
| **facile** (seuils de signe) | **jamais testé** ← le contrôle décisif | EVO-006 : succès (mixte) |

Deux questions, un seul dispositif :
1. **Le gain d'EVO-006 vient-il du crédit partiel ou de la facilité ?**
2. **À n=12, quelle est la FRÉQUENCE** du phénomène (EVO-006 n'avait qu'un seed sur cinq) ?

## Méthode — difficulté appariée, et n=12

Trois jeux de sous-tâches, **toutes des seuils de SIGNE sur des décisions que le monde lit** (`do_throw =
logits[8] > 0`, `aim_vec = [logits[11], logits[12]]`) — donc à difficulté APPARIÉE par construction :

* `TASKS_EASY1 = (throw,)` — **1 sous-tâche FACILE, SANS crédit partiel** : le contrôle décisif ;
* `TASKS_MATCHED = (throw, aim_x, aim_y)` — 3 sous-tâches de MÊME difficulté, AVEC crédit partiel ;
* bras de contrôle `W=0` sur `MATCHED` — signal présent, non noté.

3 bras × **12 seeds** × 35 ères, sous bail `kuzu`. n=12 est le seuil qu'exige
[[power-evaporation-guardrail]] pour une affirmation de FRÉQUENCE.

## Pré-vol

| jeu | non-lecteur | 1 câblée | 2 | 3 |
|---|---|---|---|---|
| **EASY1** (`throw`) | **0.498** | **1.000** | — | — |
| **MATCHED** (3 signes) | 0.514 | 0.663 | 0.832 | 1.000 |
| EVO006 (mixte, référence) | 0.378 | 0.581 | 0.751 | 0.939 |

Isolation exacte dans les trois cas (câbler la sous-tâche *k* ne fait monter que *k*). **EASY1 supprime le
plateau gratuit** : son non-lecteur est déjà à 0.498, donc tout progrès EXIGE de lire — c'est ce qui en
fait un contrôle propre.

## Règle de lecture — SCELLÉE, et sa correction rendue VISIBLE

Première application de la garde exécutable de la classe **E11**
([`tools/preregister.py`](../../tools/preregister.py), P3.1 fermée dans cette passe) :
`docs/preregistrations/EVO-007.json`, `-bis.json`, `-bis2.json`.

⚠️ **La règle initiale était INADÉQUATE, et la garde a forcé à le dire au lieu de l'ajuster en silence.**
Le seuil 0.500 avait été hérité d'EVO-005/006, où les jeux contenaient `move` : un non-lecteur y obtient
0.09-0.38, donc 0.5 était une vraie barre (le contrôle d'EVO-006 plafonne à 0.409). Mais sur un jeu
**uniquement** en seuils de signe, une politique fixe obtient 0.5 **en espérance** — donc la moitié des
seeds le dépasse par bruit d'échantillonnage. C'était **déjà lisible au pré-vol** (non-lecteur apparié =
0.514) et je ne l'ai pas vu ; les deux premiers seeds du bras de CONTRÔLE (0.527, 0.505) l'ont rendu
indiscutable.

Le tool refusant de réécrire une règle sous un nom déjà pris, la correction a été scellée séparément
(`-bis`, corrompu par une substitution shell, puis `-bis2`), **les trois fichiers conservés** : la chaîne
du changement de critère est lisible, ce qu'un simple ajustement du seuil aurait effacé.

Critère retenu (`EVO-007-bis2`), scellé alors que **seuls des seeds du bras de CONTRÔLE avaient été vus**
— le nul par construction, dont l'usage pour fixer une valeur critique est légitime :

* **DV primaire** : saillance de DÉCISION sur la sous-tâche la plus haute (bascule de `sign(logits[out])`
  sous `obs[canal]` = ±1) — quasi binaire et CALIBRÉE (lecteur câblé 1.000, non-lecteur 0.000, canal sans
  rapport 0.000). Seuil : **> 0.5**.
* **DV secondaire** : `raw` supérieur au **MAX du bras de contrôle** — le nul EMPIRIQUE du même dispositif,
  et non un nombre importé d'une autre tâche.
* **Existence** : un seed a produit de la lecture ssi les DEUX critères sont satisfaits.
  **Fréquence** : la fraction de seeds les satisfaisant, à n=12.

**Leçon portée au registre** : un seuil pré-enregistré n'est valide que pour la TÂCHE sur laquelle il a
été calibré — re-vérifier le PLANCHER du non-lecteur à chaque changement de jeu de sous-tâches.

## Résultats (3 bras × 12 seeds, 0 abandon)

| bras | **lecteurs** | `raw` méd | `raw` max | saillance max |
|---|---|---|---|---|
| contrôle `W=0` | **0/12** | 0.503 | 0.527 | 0.044 |
| `easy1` — facile, SANS crédit partiel | **0/12** | 0.503 | 0.518 | 0.091 |
| `matched` — facile, AVEC crédit partiel | **0/12** | 0.501 | 0.544 | 0.000 |

Critère scellé : saillance > 0.5 ET `raw` > 0.527 (le nul EMPIRIQUE du contrôle). **Aucun seed, dans aucun
bras, n'en approche** : la saillance maximale toutes conditions confondues est 0.091, contre 1.000 pour un
lecteur avéré. Le `raw` médian des trois bras est à 0.50 — exactement le plafond d'une politique fixe.

**Réplication directe du jeu MIXTE d'EVO-006** (n=12, règle scellée séparément) :

| bras (jeu mixte) | lecteurs | `raw` max | saillance max |
|---|---|---|---|
| contrôle `W=0` | 0/11 | 0.491 | 0.016 |
| `W=5000` | **1/12** — le seed 0 | 0.612 | **1.000** |

Le seed 0 ressort lecteur une **4ᵉ fois**, bit pour bit. Les onze autres : saillance 0.000, sans exception.
**Fisher exact bilatéral, 1/12 vs 0/11 : p = 1.000.**

## Verdict

**`PARTIAL_CREDIT_DOES_NOT_PRODUCE_INWORLD_READING`** — et par conséquent, **le verdict d'[[EDR-EVO-006]]
est RETIRÉ**.

1. **Le crédit partiel n'est PAS le levier.** À difficulté contrôlée, le bras qui en dispose (`matched`,
   3 sous-tâches) produit exactement autant de lecteurs que celui qui n'en a pas (`easy1`, 1 sous-tâche) :
   **zéro**. C'était la prédiction centrale d'EVO-006, et elle est fausse.
2. **La facilité n'est pas le levier non plus.** `easy1` supprime pourtant tout gain gratuit (son
   non-lecteur part de 0.498, au plafond) et donne 0/12. Les deux explications candidates tombent ensemble.
3. **Le lecteur d'EVO-006 est réel, rare, et inexpliqué.** Il se reproduit à l'identique (4 fois), mais à
   1/12 contre 0/11, il est **statistiquement indistinguable du contrôle** : rien ne permet de l'attribuer
   à l'objectif cognitif. EVO-006 est rétrogradé en observation isolée.

**Ce qui reste debout de l'arc**, et qui n'est pas entamé : [[EDR-EVO-005]] — un objectif cognitif dense
déplace la population jusqu'au plafond de ce qu'on gagne SANS lire, et pas au-delà. Ce résultat est
mesuré à n=5 sur une DV à plafond ANALYTIQUE, et EVO-007 le renforce plutôt qu'il ne l'entame : trois bras
supplémentaires, 36 seeds, tous collés au plafond non-cognitif.

**La question redevient ouverte** : ni l'objectif (EVO-005), ni sa granularité (EVO-007), ni le crédit
(S2-010) ne produisent de lecture in-world. Ce qui a marché **une fois** reste sans explication — c'est
la piste, et elle est étroite.

## Portée (hedges)

* **Un négatif à n=12 borne une FRÉQUENCE, il ne prouve pas l'impossibilité.** 0/12 place la borne
  supérieure du taux à ~22 % (95 %). Un phénomène plus rare que ça resterait invisible ici.
* Les sous-tâches appariées sont toutes des **seuils de signe** : le résultat porte sur cette famille
  d'opérateurs. Il n'exclut pas qu'un autre type de sous-tâche décomposable se comporte autrement.
* Le plafond de population `MAX_AGENTS=200` (garde E13) a été ajouté entre EVO-006 et ce run.
  **Vérifié non-régressif** : sur la config d'EVO-006 il ne mord jamais (0/35 ères) et le résultat clé
  reproduit à l'identique — le retrait n'est donc pas un artefact de la garde.
* Le bras de contrôle du jeu mixte a **1 seed abandonné** sur budget (11/12 exploités), compté et
  rapporté — pas silencieusement absent.

## Ce que la méthode a produit ici

La règle de lecture était **scellée avant le run** (première application de la garde E11 fermée dans la
même passe), avec l'engagement explicite que le verdict d'EVO-006 tomberait si les deux bras échouaient.
Sans ce sceau, ces mêmes chiffres m'auraient laissé toute latitude d'expliquer que « le jeu apparié ne
teste pas la même chose ». Le seuil initial, lui, s'est révélé inadéquat en cours de route et la garde a
imposé de le corriger **visiblement** (`-bis2`, les trois fichiers conservés) plutôt qu'en silence.

Converge [[EDR-EVO-005]], [[EDR-EVO-006]] (rétracté), [[EDR-S2-010]], REF-EXPERIMENT-PREFLIGHT.
