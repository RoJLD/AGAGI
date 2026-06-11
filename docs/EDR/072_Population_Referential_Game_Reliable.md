# EDR 072 : Jeu référentiel de POPULATION par gradient — convention fiable à 100 %

## Contexte

Le vrai défi du langage dans la biosphère n'est pas « 2 agents s'accordent » (EDR 070) mais « une
POPULATION entière partage UNE convention ». Sous mutation : loterie ~25 % (EDR 053). On teste le jeu
référentiel par gradient à l'échelle de la POPULATION, avec les référents de la biosphère (types
d'apex).

## Dispositif (`tools/refgame_pop.py`)

N=6 agents, chacun **locuteur ET auditeur**. À chaque pas : une **paire aléatoire** (locuteur i,
auditeur j) communique un référent (1-hot), gradient (straight-through pour le symbole discret) met à
jour les DEUX. Référents = `[Mammouth, Leurre, Ours, Sanglier]`. Métrique : **decode CROISÉ** (tout
auditeur décode tout locuteur — la convention est-elle *partagée* ?).

## Résultat — parfait et fiable

| seeds (8) | decode croisé population |
|---|---|
| 0–7 | **1.00 (tous)** |

> **decode croisé moyen = 1.000 ; convergence (>0.9) = 100 % des seeds.** Toute la population partage
> *une seule* convention, *à chaque fois* — vs ~25 % de loterie sous mutation (053).

## Insight — la population converge MIEUX que la paire

> Détail contre-intuitif : la version **population (100 %)** converge *mieux* que la paire isolée de
> l'EDR 070 (30-50 %). **L'appariement aléatoire RÉGULARISE** : un agent entraîné contre *tous* ne peut
> pas se caler sur le code idiosyncrasique d'un seul partenaire — il est tiré vers le **consensus de
> population**. **La pression sociale du groupe, sous gradient, brise la symétrie de façon
> coordonnée** — exactement ce que la mutation ne savait pas faire (loterie). Le multi-agent n'est pas
> un obstacle au langage ; sous gradient, c'est un *avantage*.

## Signification

> **Le gradient résout la coordination multi-agent du langage, FIABLEMENT (100 % vs 25 %).** C'est le
> **mécanisme validé à câbler dans Biosphere3D** : remplacer (ou compléter) l'émission de tokens
> apprise par foraging-Actor-Critic (indirecte → loterie) par un **signal référentiel direct par
> gradient** (locuteur↔auditeur), pour transformer la loterie en langage fiable.

## Honnêteté

- Banc **standalone** (MLP, communication supervisée), **pas encore câblé dans la biosphère RL vivante**
  — c'est l'étape d'ingénierie suivante. Mais le *mécanisme* est prouvé, fiable, et avec les vrais
  référents.
- Le code discret reste un straight-through ; la marge V>M (6>4) aide la bijection.

## La suite (le câblage réel)

Wiring dans `Biosphere3D` : pairer des agents proches (locuteur près d'un apex, auditeur à portée),
ajouter une **perte référentielle par gradient** sur leurs connectomes (en plus du foraging), et
mesurer si MI(token; apex) émerge *fiablement* (vs les 25 % d'EDR 053). C'est le chantier qui porte la
percée du banc dans l'agent vivant.

## Statut

- `refgame_pop.py` : convention de population **fiable à 100 %** sous gradient. Mécanisme validé pour
  l'intégration biosphère du langage.

## Variables d'expérience

Taille de population, appariement (aléatoire vs spatial/biosphère), V/M, connectome récurrent vs MLP,
câblage dans Biosphere3D (perte référentielle + foraging), Gumbel vs straight-through.
