---
id: EDR-EVO-021
type: EDR
title: "UN SEUL add_node détruit un lecteur 6 fois sur 10 — la « rétention » d'EVO-008 était un artefact de l'élitisme"
status: active
verdict: READERS_ARE_FRAGILE_RETENTION_IS_ELITISM
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-008]
---

## Origine — une critique de revue, fausse, qui a mené à une mesure vraie

La revue adversariale de l'arc a allégué deux bugs dans `src/seed_ai/mutation.py` : `add_node` insérerait
à `j < num_inputs` (décalant silencieusement le bloc d'entrée, `num_inputs` n'étant jamais mis à jour), et
`new_W[i, j] = 1.0` utiliserait l'ancien `i` après un décalage de lignes (off-by-one pour `i >= j`).

**Les deux sont réfutés par la mesure** — sur 3 000 tirages d'arête depuis une soupe fraîche :

| condition alléguée | fréquence |
|---|---|
| `j < num_inputs` (décalage du bloc d'entrée) | **0.0 %** |
| `i >= j` (off-by-one sur la source) | **0.0 %** |

Les arêtes existantes vont d'une entrée (`i < 59`) vers une sortie (`j ≥ 64`) : `i < j` et
`j ≥ num_inputs` **toujours**. Le code est fragile en théorie, jamais atteint en pratique dans ce régime.
⚠️ Mesuré sur UNE soupe fraîche — un génome très mué pourrait sortir de ce régime, non testé.

**Mais la sonde écrite pour vérifier ça en a trouvé un autre, réel.**

## Résultat — un lecteur câblé ne survit pas à une insertion

10 seeds, un lecteur câblé (saillance 1.000), **un seul `add_node`**, toutes les autres mutations
désactivées (`weight_mutate_rate=0`, `add_connection_rate=0`, `prune_rate=0`) :

| | arête `SIG→throw` | saillance |
|---|---|---|
| 4 seeds / 10 | +3.00 | **1.000** |
| **6 seeds / 10** | **+0.00** | **0.000** |

**Mécanisme, mesuré** : `add_node` **scinde** une arête existante — il met `W[i,j] = 0`, insère un nœud,
puis recâble `i → nouveau` (poids 1.0) et `nouveau → j` (ancien poids). Le chemin survit *topologiquement*.
Mais le nœud inséré arrive avec une **diagonale nulle**, donc `δ = sigmoid(0) = 0.5` : c'est un nœud à
MÉMOIRE. Le chemin réactif direct devient un chemin **dérivant**, et la dérive d'état (classe **E6**) noie
le signal — exactement le mécanisme mesuré au pré-vol d'[[EDR-EVO-005]] (+7.45 ± 9.8 après 25 ticks).

`add_node_rate = 0.4` dans **tous** les runs de l'arc.

## Verdict

**`READERS_ARE_FRAGILE_RETENTION_IS_ELITISM`**

**La « rétention 28/29 ères » d'[[EDR-EVO-008]] n'est pas une propriété du lecteur — c'est un artefact du
protocole.** Les élites sont **clonées sans mutation** (`el = [a["model"].genome.clone() for a in chosen]`) ;
seuls les enfants mutent. Le champion lecteur survit donc parce qu'il est **recopié**, pas parce qu'il
résiste. Confronté à l'opérateur de variation, il est perdu **6 fois sur 10 en une seule insertion**.

**Conséquence pour l'arc, et elle est nouvelle** : un lecteur ne peut pas se **PROPAGER** dans la
population. Chaque enfant qui en hérite a ~60 % de le perdre au premier `add_node`. Le lecteur reste donc
confiné à la lignée élite, ce qui explique pourquoi les taux observés restent à ~1 seed sur 12-24
([[EDR-EVO-019]], [[EDR-EVO-020]]) au lieu d'envahir la population une fois découverts.

Le verrou d'[[EDR-EVO-018]] gagne donc une **seconde composante mesurée** : la découverte est rare (3 sur
~11 000, [[EDR-EVO-014]]) **et** ce qui est découvert est fragile (6/10 détruit par insertion). Les deux
se multiplient.

⚠️ **Ça ne rouvre PAS la clôture** : la fragilité aggrave le problème, elle ne fournit aucun levier. Un
opérateur qui préserverait les chemins réactifs (en donnant au nœud inséré une diagonale héritée, par
exemple) serait testable — et deviendrait le premier candidat agnostique non réfuté depuis
[[EDR-EVO-017]].

## Portée (hedges)

* **10 seeds, un seul type de lecteur** (câblé, réflexe, sous-tâche `throw`). Non testé sur un lecteur
  ÉVOLUÉ ni sur `move`.
* La sonde force `add_node_rate = 1.0` et désactive tout le reste : elle mesure l'effet **par insertion**,
  pas la probabilité par ère dans un run réel (où d'autres mutations coexistent).
* Le mécanisme (nœud inséré sans réflexe → dérive) est **inféré de la structure du code plus la mesure**,
  pas isolé par une intervention : donner au nœud inséré une diagonale à +10 et re-mesurer serait le test
  causal. Non fait.
* Les deux bugs allégués par la revue sont réfutés **dans ce régime** ; ils restent des fragilités réelles
  du code (`num_inputs`/`num_outputs` ne sont jamais mis à jour par `add_node`).

## Provenance

Trouvé en vérifiant une critique de **revue adversariale** — 7 critiques lancées, 1 confirmée
([[EDR-EVO-019]]), 6 rejetées par leur propre vérification. Celle-ci était parmi les rejetées : fausse
sur son allégation, **mais la sonde écrite pour la réfuter a trouvé un mécanisme réel**. Bilan du dépôt
sur l'arc WARM : 7 revues → 7 erreurs réelles ; ici 7 → 1 erreur + 1 découverte.

Converge [[EDR-EVO-005]], [[EDR-EVO-008]], [[EDR-EVO-014]], [[EDR-EVO-018]], REF-EXPERIMENT-PREFLIGHT.
