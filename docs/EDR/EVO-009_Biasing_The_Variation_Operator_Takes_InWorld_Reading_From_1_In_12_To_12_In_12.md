---
id: EDR-EVO-009
type: EDR
title: "Biaiser l'OPÉRATEUR DE VARIATION fait passer la lecture in-world de 1/12 à 12/12, sans coût de survie — le verrou était la découverte, et il est levable"
status: active
verdict: VARIATION_OPERATOR_IS_THE_LEVER
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-008]
---

## Question

[[EDR-EVO-008]] a établi que le verrou de la lecture in-world est la **DÉCOUVERTE** et non la rétention :
le circuit apparaît d'un saut mutationnel unique (saillance 0.00 → 1.00 en une ère) puis est conservé
28 ères sur 29. La lecture du code donne le taux attendu : `add_connection` tire une arête parmi
~11 000 candidates dont **3** seulement sont « lectrices », et `mutate_weights` ne touche que les poids
**non nuls** — il ne peut donc jamais créer l'arête, seulement l'affiner.

> **Si la découverte est un tirage combinatoire, biaiser le tirage doit faire bondir le taux.**

C'est la première prédiction de tout l'arc EVO qui porte sur l'**optimiseur** plutôt que sur l'objectif.
Règle de lecture scellée avant le run : `docs/preregistrations/EVO-009.json`.

## Méthode — une seule variable

2 bras × 12 seeds × 35 ères, jeu MIXTE, `W=5000`, mêmes graines, même monde, même fitness, même substrat.
**Seule la loi de tirage de `add_connection` change** : dans le bras `biased`, une fois sur deux, les
candidats sont restreints aux paires (canal de signal → nœud de sortie noté). Monkeypatch **local** au
banc — `src/seed_ai/mutation.py` n'est jamais modifié, l'opérateur d'origine est restauré en sortie.
Sous bail `kuzu` et plafond de coût (garde E13) ; 0 abandon.

**Pré-vol** — la manipulation change-t-elle réellement la loi de tirage ?

| bras | création d'arête lectrice |
|---|---|
| baseline | **4 lignées sur 40** (10 %) en 200 mutations |
| biaisé | **42 arêtes** en 200 mutations |

⚠️ La première version de ce pré-vol affichait « baseline : 0 arête créée » — un **artefact de compteur**
(seule la fonction biaisée était instrumentée), qui se lisait comme un contraste écrasant 0 contre 42.
Classe **E4** : une vérification qui ne peut pas échouer, ici du côté du contrôle. Le baseline a été
re-mesuré séparément, par diff de `W` sur les paires cibles.

## Résultats

| bras | **lecteurs** | `raw` méd | âge méd | proies méd |
|---|---|---|---|---|
| baseline | **1/12** | 0.453 | 13 | 8 |
| **biaisé** | **12/12** | **0.748** | 13 | 7 |

**12/12 contre 1/12 — Fisher exact bilatéral p = 9.6 × 10⁻⁶.** Les douze champions du bras biaisé ont
une saillance de décision de **1.000**, indiscernable d'un lecteur câblé à la main.

**La survie est INTACTE** : âge médian 13 dans les deux bras, proies 7 contre 8. La branche pré-enregistrée
« le biais paie la lecture en survie » ne s'applique pas — il n'y a pas de compromis mesuré ici.

## Verdict

**`VARIATION_OPERATOR_IS_THE_LEVER`** — le verrou de la lecture in-world était bien la DÉCOUVERTE, et il
est **levable**. L'arc se referme sur un diagnostic net :

| record | ce qui a été manipulé | issue |
|---|---|---|
| [[EDR-EVO-004]] | rien (survie seule) | ne lit RIEN |
| [[EDR-EVO-005]] | **poids** de l'objectif | plafond non-cognitif, rien au-delà |
| [[EDR-EVO-007]] | **granularité** de l'objectif | 0/12 |
| **EVO-009** | **opérateur de variation** | **12/12** |

Quatre records ont cherché le bon **objectif**. [[EDR-EVO-008]] a montré que l'objectif faisait déjà la
moitié du travail — il RETIENT la lecture dès qu'elle existe. Ce qui manquait était en amont, dans la
capacité de l'opérateur de mutation à **produire** le câblage. Cette expérience le confirme au niveau
d'évidence le plus fort obtenu dans cet arc.

## ⚠️ Ce que ce record N'établit PAS (à lire avant de le citer)

**Ce n'est pas un algorithme, c'est un DIAGNOSTIC.** Le biais utilise la connaissance des arêtes qui
comptent — il dit à l'opérateur *où chercher*. Sur un vrai problème, cette information n'existe pas. La
valeur du résultat est donc de **localiser le verrou de façon décisive**, pas de fournir une solution
déployable.

La suite qui en découle, et qui est la vraie question ouverte : **existe-t-il un biais AGNOSTIQUE à la
tâche qui produise le même effet ?** Candidats testables — augmenter la densité générale des arêtes
entrée→sortie, augmenter `add_connection_rate`, ou rendre `mutate_weights` capable de réveiller des poids
NULS (ce qu'il ne fait pas aujourd'hui, et c'est précisément ce qui rend la découverte dépendante d'un
seul opérateur).

## Portée (hedges)

* `raw` médian du bras biaisé = 0.748, contre ~0.94 pour un lecteur câblé sur les 3 sous-tâches : les
  champions lisent typiquement **UNE** sous-tâche, pas les trois. Le biais lève le verrou de la première
  découverte, il ne produit pas un lecteur complet.
* Les seeds biaisés lisent des sous-tâches différentes (`accept` 7 fois, `throw` 5 fois) — cohérent avec
  un tirage, et rien n'indique une préférence systématique.
* L'absence de coût de survie est mesurée **dans ce régime** (`W=5000`, jeu mixte) ; elle ne se transporte
  pas automatiquement à un objectif cognitif plus exigeant.
* Le taux baseline de création d'arête (10 % par lignée sur 200 mutations) est proche du taux de
  découverte observé (8 %). ⚠️ **Coïncidence NOTÉE, PAS convertie en mécanisme** : la mesure est une chaîne
  de mutations SANS sélection, et mes propres traces montrent des champions porteurs de l'arête avec une
  saillance nulle ([[EDR-EVO-008]], ères 2/4/5). C'est la leçon d'[[EDR-EVO-006]], rétracté la veille.
* Une micro-explication séduisante (« la sortie doit être DOMINÉE par un seul canal ») est restée à n=1 et
  a été explicitement **exclue** de la règle de lecture scellée. Elle n'entre pas dans ce verdict.

Converge [[EDR-EVO-004]], [[EDR-EVO-005]], [[EDR-EVO-007]], [[EDR-EVO-008]], REF-EXPERIMENT-PREFLIGHT.
