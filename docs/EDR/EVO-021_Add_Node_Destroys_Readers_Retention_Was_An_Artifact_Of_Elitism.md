---
id: EDR-EVO-021
type: EDR
title: "UN SEUL add_node désaligne un lecteur 56 % du temps (le bloc de sortie glisse) — la « rétention » d'EVO-008 était un artefact de l'élitisme"
status: active
verdict: READERS_ARE_FRAGILE_BY_OUTPUT_INDEX_SHIFT
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

### ⛔ Mécanisme initialement proposé — RÉFUTÉ PAR INTERVENTION (2026-08-04)

La première version de ce record attribuait la destruction au **nœud inséré sans diagonale** (`δ = 0.5`,
nœud à MÉMOIRE) qui convertirait un chemin réactif en chemin dérivant. C'était une inférence tirée de la
structure du code, pas une intervention — et le record le signalait comme non isolé.

**L'intervention a été faite ([[EDR-EVO-022]], arrêtée au pré-vol) : elle réfute ce mécanisme.** Donner au
nœud inséré la diagonale de sa destination ne change **rien** — destruction 13/20 dans les deux bras. La
clause scellée a stoppé le run avant toute dépense.

### ✅ Mécanisme RÉEL, mesuré

Un chiffre trahissait déjà la fausse piste : la destruction est de ~65 %, or le lecteur n'a **qu'une**
arête parmi ~173 entrées non nulles — `add_node` ne peut la scinder que dans ~0.6 % des cas. **65 % ne
peut pas venir d'une scission.**

`add_node` insère une ligne et une colonne à l'indice `j`, **sans jamais mettre à jour `num_inputs` ni
`num_outputs`**. Insérer DANS le bloc de sortie décale donc l'indice de chaque sortie : l'arête câblée
survit intacte, mais elle ne pilote plus la même décision. Mesuré sur 200 insertions
(`tools/evo_runs/probe_output_block_shift.py`) :

| après une insertion | |
|---|---|
| l'arête pilote encore `throw` | 44 % |
| **DÉSALIGNÉE** — elle survit mais pilote autre chose | **56 %** |
| dont glissement du bloc d'ENTRÉE (`j ≤ 5`) | 0.5 % |

**56 % de désalignement pour ~65 % de destruction** : la correspondance est nette. Le défaut est dans
`src/seed_ai/mutation.py:54-73` — un vrai défaut du code de production, pas une propriété du substrat.

⚠️ **Et ça corrige la réfutation que ce record faisait de la revue.** J'avais mesuré « `j < num_inputs` :
0.0 % sur 3 000 tirages » et conclu que le décalage d'indices « ne se produit jamais en pratique ». C'était
mesuré sur une **soupe fraîche**, où les arêtes vont d'une entrée vers une sortie (`j ≥ 64` toujours). Un
génome porteur d'auto-boucles diagonales a un `j` uniforme sur TOUS les nœuds. La revue avait raison sur
le fond ; c'est mon contre-test qui portait sur le mauvais régime — **E9, dans une réfutation**.

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
* Le mécanisme retenu (décalage du bloc de sortie) est mesuré sur un lecteur CÂBLÉ. Sur un génome ÉVOLUÉ,
  la distribution de `j` diffère (moins d'auto-boucles) — le taux de désalignement n'y est pas mesuré.
* ⚠️ **Dette ouverte** : `add_node` ne met à jour ni `num_inputs` ni `num_outputs`. Corriger la production
  changerait le comportement de TOUT l'arc et invaliderait la comparabilité des runs ; à traiter comme une
  migration, pas comme un patch. Inscrit au backlog.

## Provenance

Trouvé en vérifiant une critique de **revue adversariale** — 7 critiques lancées, 1 confirmée
([[EDR-EVO-019]]), 6 rejetées par leur propre vérification. Celle-ci était parmi les rejetées : fausse
sur son allégation, **mais la sonde écrite pour la réfuter a trouvé un mécanisme réel**. Bilan du dépôt
sur l'arc WARM : 7 revues → 7 erreurs réelles ; ici 7 → 1 erreur + 1 découverte.

Converge [[EDR-EVO-005]], [[EDR-EVO-008]], [[EDR-EVO-014]], [[EDR-EVO-018]], REF-EXPERIMENT-PREFLIGHT.
