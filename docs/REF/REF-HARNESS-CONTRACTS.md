---
id: REF-HARNESS-CONTRACTS
type: REF
title: "Les deux contrats du harnais — Task et Learner, en prose"
status: active
adopt_for: [ADR-004, ADR-005]
---

## Énoncé

Le harnais (ADR-004, spec `docs/superpowers/specs/2026-09-16-harness-contracts-design.md` §2.1) compose
deux contrats INDÉPENDANTS. Une `Task` (`src/seed_ai/harness_task.py`) ne connaît ni learner, ni torch,
ni monde : elle génère des épisodes, note une politique, et déclare la capacité qu'elle exige avec
l'ablation qui la teste. Un `Learner` (`src/seed_ai/harness_learner.py`) ne connaît pas la Task au-delà
de son interface : il apprend à dose comptée, et déclare ses pièces avec, pour chacune, la variante
« sans cette pièce ». Ce document est la référence en PROSE que le prompt du proposeur (`tools/harness/propose.py`,
semaine 5) citera pour écrire de nouvelles tâches, et que tout runner de cellule doit satisfaire avant le
premier entraînement. Il ne contient aucun code : le code source des contrats est
`src/seed_ai/harness_task.py::assert_task_contract` et `src/seed_ai/harness_learner.py::assert_learner_contract` ;
lire leurs docstrings pour la forme exécutable exacte.

## Le contrat Task

Une Task déclare : le nom de la capacité qu'elle exige, la liste de ses ablations (chacune nommée, sur un
site d'entrée ou d'état, marquée mordante ou non), un oracle câblé et un vérifieur indépendant de cet
oracle, un plafond de représentation avec sa provenance et son statut, et son régime publié tel quel.
`assert_task_contract` est une garde posée EN TÊTE, sans le moindre entraînement, qui refuse en quelques
millisecondes — elle répond à la question A du pré-vol expérimental (REF-EXPERIMENT-PREFLIGHT) : l'instrument
peut-il produire LES DEUX issues, avant qu'un seul poids ne bouge. Ses clauses :

- **(a) Les deux issues sont possibles.** Au moins une ablation est marquée `must_bite=True` (elle DOIT
  faire tomber la performance : la capacité EXIGE ce canal) et au moins une est `must_bite=False` (contrôle
  de spécificité : elle ne doit PAS mordre). Une tâche dont toutes les ablations mordent, ou dont aucune ne
  mord, ne peut jamais rendre qu'une seule conclusion — c'est la classe E2 appliquée à l'instrument de
  demande. Toute ablation dont le site est `"state"` exige qu'un split `"control"` distinct existe (le bras
  de contrôle d'`alias_guard_verdict`).
- **(b) Le vérifieur n'est pas l'oracle (E1).** `score(oracle)` doit valoir exactement 1.0 — le contrôle
  positif de la mesure — mais un oracle DÉCALÉ (`(x+1) % K`) doit tomber à exactement 0.0. Si le vérifieur
  notait simplement « est-ce la sortie de l'oracle », il ne pourrait jamais détecter un oracle faux : c'est
  un contrôle qui ne peut pas échouer (E1), donc il ne prouve rien.
- **(c) Chaque ablation rend les deux issues, pas seulement leur possibilité déclarée.** Toute ablation
  d'entrée doit changer l'observation sur au moins un pas — sinon c'est de nouveau un contrôle qui ne peut
  pas échouer (E1). Sous une ablation `must_bite=True`, l'oracle doit tomber au plancher de Bayes déclaré
  (± 2 erreurs-types) : elle doit vraiment MORDRE. Sous une ablation `must_bite=False`, l'oracle doit rester
  au-dessus de 0.9 : elle ne doit vraiment RIEN mordre. Une ablation qui prétend être un contrôle de
  spécificité mais fait chuter l'oracle n'est pas un contrôle, elle mord.
- **(d) Reproductibilité et absence d'aliasing.** Deux appels à `episodes()` avec le même état de générateur
  aléatoire rendent des épisodes bit-identiques (aucun tirage caché hors du `rng` passé en argument).
  `apply()` d'une ablation ne partage JAMAIS de mémoire avec l'épisode intact (`np.shares_memory` faux, sur
  `obs_seq` et sur `mask_seq`) : écrire dans l'épisode ablaté ne doit pas muter la source. Une ablation ne
  change JAMAIS la cible (`target`) — la vérité est invariante à l'ablation, seule l'observation change.
- **(e) Le plafond de représentation a une provenance.** `incapable_ceiling`, quand il est déclaré, porte
  une provenance d'au moins 20 caractères, une valeur dans `]0, 1]`, et cette valeur n'est JAMAIS égale au
  niveau de chance `1/K` — confondre le plafond de l'INCAPABLE avec le niveau de CHANCE est exactement le
  défaut fondateur de la classe P2.15 : une barre bâtie sur `1/K + marge` peut être franchie par un
  substrat prouvablement incapable si son plafond de représentation dépasse déjà cette marge.
- **(f) Le régime est publié, et rien n'est fabriqué sur une collection vide.** `regime()` ne rend jamais un
  dictionnaire vide (E8 : une prémisse est une mesure, jamais recopiée de mémoire). `score()` appelé sur un
  lot de zéro épisode doit LEVER, jamais rendre une constante silencieuse (porte 14 du hook : une
  agrégation qui rend une constante sur une collection vide fabrique un résultat qu'aucune donnée ne
  soutient).

Le principe **E1** (« un contrôle qui ne peut pas échouer, ou un bras qui ne peut pas réussir, ne prouve
rien ») traverse (b) et (c) : c'est la raison d'être du vérifieur indépendant de l'oracle et de l'exigence
que chaque ablation morde ou ne morde pas EFFECTIVEMENT, pas seulement par construction déclarative.

## Le contrat Learner

Un Learner déclare : ses pièces (`tuple[Piece, ...]`, chacune avec sa variante « sans », son sham à
paramètres appariés ou `None`, sa dose appariée), la tâche d'entrée de sa famille (`entry_task`, le billet
E2 déjà payé), le `K` maximal qu'il supporte, l'ensemble des ablations d'état qu'il sait appliquer
(`supported_state_ablations`), et un balayage d'au moins deux réglages distincts de son axe d'optimisation
(`sweep()`). `build(reference=True)` doit rendre le bras de référence de la condition d'acquisition : même
init, mêmes tirages, même boucle, apprentissage COUPÉ. `assert_learner_contract` est également une garde EN
TÊTE, sur une petite population et quelques épisodes d'apprentissage, avant toute cellule à 12 seeds :

- **(L0) La tâche est dans les moyens du learner.** `task.K <= learner.max_K`, et toute ablation de la tâche
  dont le site est `"state"` doit figurer dans `supported_state_ablations` — sinon le learner ne peut même
  pas exécuter le protocole d'ablation d'état que la tâche exige.
- **(L1) Déterminisme et no-op EXACT.** Deux appels à `build(seed)` rendent des logits bit-identiques (le
  learner ne tire rien hors de son seed). `build(without={})` — la variante « rien retiré » — est
  bit-identique à l'intact, À L'INIT et APRÈS `n_learn` pas d'apprentissage : le no-op n'est pas approximatif,
  c'est un plancher de bruit à ZÉRO exact, faute de quoi tout ratio de contraste mesuré plus tard est
  indiscernable de ce bruit d'implémentation.
- **(L2) REFERENCE_LEARNS.** Le bras de référence (`reference=True`) soumis à `n_learn` appels de `learn`
  ne bouge JAMAIS : `dparam_abs_sum == 0` et `updates == 0`, tout en consommant le même nombre d'appels
  que l'intact. Une référence qui apprend contamine la barre de la condition d'acquisition — le sujet
  serait comparé à une référence qui a elle-même appris une partie de la tâche.
- **(L3) DEAD_LEARNER.** Le bras intact soumis à `n_learn` appels de `learn` DOIT bouger
  (`dparam_abs_sum > 0`) — c'est le cas « curiosité morte » (P4.8) : un apprenant inerte ne peut rendre
  aucun verdict d'acquisition interprétable, quelle que soit la tâche.
- **(L4) VACUOUS_PIECE.** Pour chaque pièce en portée, `build(without=p.without)` — soumise aux MÊMES
  `n_learn` pas d'apprentissage que l'intact, sur les MÊMES épisodes — doit rendre des logits qui diffèrent
  de l'intact sur au moins un logit, APRÈS ce même entraînement (jamais comparée à l'init : un apprenant
  non entraîné rend des zéros avec ou sans sa table, ce qui rendrait toute pièce du chemin de crédit
  invisible à cette clause). Une variante « sans » qui ne change RIEN dit que la pièce déclarée n'existe
  pas, opérationnellement, dans ce learner.
- **(L5) Aucune vue de l'état dans la sortie.** Les logits rendus par `act()` ne partagent aucune mémoire
  avec l'état récurrent (`assert_no_aliasing`) — sinon écrire dans une sortie muterait l'état porté, et un
  chemin d'IDENTITÉ non tracé par des poids fausserait toute mesure de saillance ou d'ablation (classe E24).
- **(L6) Le billet d'entrée existe.** `entry_task` n'est pas vide : la famille du learner a payé son
  contrôle positif d'acquisition (règle E2) avant d'entrer dans une cellule de nécessité.
- **(L7) Le sweep a au moins deux points distincts.** `len(sweep()) >= 2`, avec au moins deux réglages
  réellement différents — un seul point ne permet jamais de distinguer un nul de CAPACITÉ d'un nul de
  RÉGLAGE (garde E19, `assert_verdict_invariant_to_optimizer`), qui a besoin d'au moins deux pas pour
  fonctionner.

## Déroulé d'une cellule : cinq bras, trois conditions

Une CELLULE compose une Task acceptée, un Learner accepté, 12 seeds, et une règle scellée
(`tools/preregister.py`). Chaque seed construit CINQ bras, tous consommant les MÊMES tirages
(`_ARMS` de `src/seed_ai/harness_verdict.py`) :

- **A** — le sujet intact, au premier pas du sweep.
- **A0** — la référence (`build(reference=True)`), même init, apprentissage coupé : la barre de la
  condition d'acquisition.
- **A2** — le sujet intact, au second pas du sweep (garde E19 sur l'acquisition).
- **D** — le sujet sans la pièce ciblée (`build(without=p.without)`), au premier pas.
- **D2** — le sujet sans la pièce ciblée, au second pas (garde E19 sur la nécessité ; lancé seulement sur
  la branche nulle ou partielle de la condition de nécessité).

Le verdict d'une cellule lit trois conditions, dans cet ordre (`harness_verdict_lecture`, PURE, composant
des instruments déjà calibrés) :

1. **DEMANDE (i)** — `ablation_verdict` sur le sujet intact contre chacune de ses ablations : une ablation
   `must_bite=True` doit démontrer `X_DEMANDED` (ratio de chute >= 1,5, hors de la bande de bruit mesurée
   par `measure_noise_floor`) ; une ablation `must_bite=False` doit rendre `X_DECOY`. Une ablation de site
   `"state"` passe en plus par `alias_guard_verdict`, qui doit rendre `SURGICAL`.
2. **ACQUISITION (ii)** — `learner_verdict` sur les médianes par seed du sujet intact (premier pas, mi-dose,
   dernier pas) contre sa référence appariée : la barre est `référence + min_sep` ; 12/12 seeds doivent la
   franchir. `assert_bar_separates_the_incapable` confronte systématiquement cette barre au plafond de
   représentation déclaré, et publie le résultat (`representational_ceiling_above_bar`) — sans jamais le
   transformer en refus bloquant : le harnais doit pouvoir DIRE que sa barre est sous le plafond de
   représentation, pas le cacher.
3. **NÉCESSITÉ (iii)** — `ablation_verdict` entre le sujet intact et le sujet sans la pièce : `NECESSARY`
   ssi la chute est hors bande de bruit ET que la variante « sans » retombe au niveau de la référence (elle
   ne fait plus mieux que ne pas avoir appris) ; `PIECE_PARTIAL` si la chute est hors bande mais que la
   variante franchit quand même la barre d'acquisition ; `NOT_NECESSARY` sinon. Tout verdict nul ou partiel
   — et, depuis la revue du 2026-09-16, tout verdict `NECESSARY` aussi — passe par la garde E19
   (`assert_verdict_invariant_to_optimizer`) : l'écart entre les deux bras doit survivre au second pas du
   sweep, sinon c'est un artefact de PAS, pas de capacité.

Les quinze branches possibles, dans l'ORDRE de sévérité imposé (`BRANCHES` de `src/seed_ai/harness_verdict.py`,
la plus sévère d'abord) : `INCOMPLET`, `INCONCLUSIVE_N`, `INDETERMINE_HARNAIS`, `LR_ARTIFACT`,
`NOT_ACQUIRED`, `NOT_DEMANDED`, `DEMAND_WITHIN_NOISE`, `DEMAND_INCONCLUSIVE`, `INCONCLUSIVE_SPECIFICITY`,
`INCONCLUSIVE_ALIAS`, `PIECE_NOT_NECESSARY`, `PIECE_INCONCLUSIVE`, `PIECE_PARTIAL`,
`DEMANDED_ACQUIRED_NECESSARY`, `AUTRE`. Aucune branche ne rend une constante sur une collection vide : une
série manquante, vide ou non finie (`nan`/`inf`) LÈVE plutôt que de se lire comme un verdict.

## Ce que ces contrats ne couvrent pas

Ni `Task` ni `Learner` ne décident seuls d'une cellule : le déroulé (proposition, revue humaine,
scellement, pré-vol, cinq bras, verdict, record) est décrit au spec §2.3 et implémenté par
`tools/harness/cell.py::run_harness_cell`, hors du périmètre de ce document. Le registre des pièces
biologiques est publié séparément (REF-HARNESS-PIECES).
