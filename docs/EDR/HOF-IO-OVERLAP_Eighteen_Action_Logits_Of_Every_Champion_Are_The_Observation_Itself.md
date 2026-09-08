---
id: EDR-HOF-IO-OVERLAP
type: EDR
title: "Les blocs d'ENTRÉE et de SORTIE se chevauchent : 18 des 126 logits d'action de CHAQUE champion du Hall of Fame SONT l'observation — sans traverser un seul poids (10/10 entrées ; 0/348 génomes persistés)"
status: active
verdict: HOF_GENOMES_HAVE_18_SLOT_IO_OVERLAP_ACTION_LOGITS_ARE_OBSERVATION
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-BLIND-CHAMPION]
---

> Trouvé **par accident**, en cherchant pourquoi un contrôle avait échoué. Aucun run de monde n'a été
> nécessaire : tout ce qui suit est une sonde pure numpy et trois entiers.

## Le fait

`MambaBatchModel` dispose les nœuds en `[entrées | cachés | sorties]` et calcule
`max_H = max_N − max_I − max_O`. **Rien ne vérifie que `max_H >= 0`.** Le génome du champion déclare
**64 entrées et 126 sorties dans un réseau de 172 nœuds** : 64 + 126 = 190 > 172.

`forward` écrit l'observation dans `H[:, :max_I]` puis lit les logits d'action à partir de
`max_I + max_H` = 64 − 18 = **46**. Les 18 premiers logits d'action sont donc les composantes 46 à 63
de l'observation, multipliées par le masque d'attention.

**Vérifié composante par composante**, sur un génome dont on a en plus mis `W[:num_inputs, :] = 0` :

| | valeur |
|---|---|
| `max(abs(logits[0:18] − (obs·masque)[46:64]))` | **0,0025** |
| exemple, agent 0 | logits `[0.0955, 1.0501, 0.0601, 0.3086, 0.1501]` vs obs `[0.0955, 1.0501, 0.0599, 0.3086, 0.1501]` |

L'écart de 0,0025 n'est pas du bruit : c'est exactement la mise à jour récurrente
`(1−δ)·H + δ·tanh(...)` appliquée à ces mêmes slots.

## L'étendue, mesurée

| population | `num_inputs` | `num_outputs` | `num_nodes` | chevauchement |
|---|---|---|---|---|
| **Hall of Fame — 10 entrées sur 10** | 64 | 126 | 172 | **+18** |
| génomes persistés `data/genomes/*.npz` — **0 sur 348** | 59 | 108 | 172-176 | −5 à −9 |
| `MambaAgent()` frais | 59 | 108 | 172 | −5 |

Le défaut est **entièrement contenu dans le Hall of Fame**, et il y est **universel**. C'est la face
non mesurée de la divergence de lignée `num_inputs` 64 ↔ 59 déjà connue : on savait les dimensions
divergentes, personne n'avait calculé ce que 64 + 126 fait dans 172.

## Quels canaux, exactement

Le monde livre **64 colonnes** (comptées dans `get_batch_observations`, `np.column_stack`) — donc
aucun bourrage : les 18 slots partagés portent des canaux réels et nommés :

| slot d'obs | canal | devient le logit d'action |
|---|---|---|
| 46-50 | `in_mem[0..4]` — les 5 canaux de mémoire | 0-4 |
| 51-53 | `in_confort`, `is_night`, `fire_nearby` | 5-7 |
| 54-58 | `ntm_mem[0..4]` — la mémoire NTM | 8-12 |
| 59-63 | `manager_goal[0..4]` | 13-17 |

Autrement dit, pour tout champion du HoF, **les 18 premières décisions d'action sont un fil droit
depuis la mémoire, le contexte et le but** — aucun poids entre les deux.

## Sur le champion INTACT : dix décisions du monde sont EXACTEMENT une observation

L'identité ci-dessus a été mesurée sur un génome dont `W` était annulé. Sur le champion **INTACT**, le
slot partagé vaut `(1−δ)·obs + δ·tanh(excitation)` : le terme d'observation y est toujours, mais il est
accompagné. Affirmer « les logits SONT l'observation » sans mesurer cette part serait une inférence de
plus. Mesuré (400 observations tirées au hasard, no-op de la sonde à **0,0**) :

| logits | corrélation avec `obs[46+k]` | pente | ce que le monde en fait |
|---|---|---|---|
| **8 à 17** | **r = +1,0000 exactement** | **+0,5000** | `do_throw`, `do_jump`, `do_duck`, visée (×2), `out_share`, `out_accept`, `out_mate` |
| 0 à 7 | r = 0,51 à 0,88 | 0,43 à 0,65 | `argmax(logits[:8])` — le mouvement |

`r = 1,0000` et pente `0,5000` signifient que le terme calculé est **constant** sur ces dix slots : ils
valent `0,5 · obs` à une constante près. Le monde applique ensuite un test de SIGNE, et l'accord est
**total** :

| opérateur réellement appliqué par le monde | accord | hasard |
|---|---|---|
| `(logits[8] > 0) == (obs[54] > 0)` — **`do_throw`** | **1,000** | 0,5 |
| `(logits[9] > 0) == (obs[55] > 0)` — **`do_jump`** | **1,000** | 0,5 |
| `argmax(logits[:8]) == argmax(obs[46:54])` — le mouvement | 0,445 | 0,125 |

Autrement dit, pour ce champion :

> **`do_throw` EST `ntm_mem[0] > 0`. `do_jump` EST `ntm_mem[1] > 0`. `do_duck` EST `ntm_mem[2] > 0`.
> La visée EST `(ntm_mem[3], ntm_mem[4])`. `out_share`, `out_accept` et `out_mate` SONT
> `manager_goal[0..2]`.** Aucun poids appris n'intervient.

Le **mouvement**, lui, est un mélange : l'argmax coïncide avec celui des canaux bruts
(`in_mem[0..4]`, `in_confort`, `is_night`, `fire_nearby`) dans 44,5 % des cas contre 12,5 % attendus
par hasard — le réseau y contribue réellement, mais il ne décide pas seul.

Seules la parole (`logits[19:23]`) et le frottement (`logits[25]`) tombent **hors** de la zone
partagée : ce sont les seules sorties consommées par le monde qui soient entièrement calculées.

## Ce que ça n'invalide PAS

* **Les verdicts `PERCEPTION_DECOY` de S2-002/003 et d'`EDR-124` tiennent.**
  `PerceptionAblatedMamba` permute `batch_obs` **à l'entrée** : il ablate donc les deux chemins, le
  fil droit compris. L'instrument mesure bien ce qu'il annonce.
* **`EDR-EVO-011` n'est pas touché** : ses sujets sont des génomes câblés `Genome(W, 59, 108)`, soit
  167 ≤ 172, sans chevauchement — vérifié. Son `o = N − num_outputs` vaut 64, et sa lecture de
  `logits[8]` est bien une lecture de sortie.

## Ce que ça change

1. **On ne peut pas aveugler un champion en annulant des poids.** C'est ainsi que le défaut a été
   trouvé : [[EDR-S2-BLIND-CHAMPION]] a vu son contrôle échouer, et la chasse à la cause a éliminé
   successivement le monde-modèle (inactif, `world_model` vaut `None`), le routeur neuromodulateur et
   le compilateur NTM — tous **mesurés**, tous innocentés — avant d'arriver à l'arithmétique des blocs.
2. **La lecture d'[[EDR-EVO-004]] doit être reprise.** Ce record conclut « saillance action/canal au
   PLANCHER sur TOUS les canaux » **sur ce champion**. Une saillance nulle mesurée sur une politique
   dont un septième des sorties EST l'entrée ne dit pas la même chose selon qu'on regarde les 18
   logits partagés ou les 108 autres : sur les partagés, la saillance devrait être **maximale par
   construction**. Le mesurer sépare deux hypothèses que le record ne distingue pas — et c'est peu
   coûteux, la sonde de saillance existe et est calibrée. Inscrit **P2.46**.
3. **`max_H` négatif ne doit plus être silencieux.** `assert_no_io_overlap` (classe **E24**) le
   chiffre et lève, dans le pré-vol et non dans le substrat : faire lever `MambaBatchModel.__init__`
   casserait tout run utilisant le champion, et on ne répare pas un génome déjà publié — on rend son
   défaut visible. Quatre cas de calibration, dont le no-op (un génome frais passe) et le cas LIMITE
   (`in + out == N` : zéro nœud caché mais aucun slot partagé — la garde porte sur le chevauchement,
   pas sur la platitude du connectome, qui est légitime, cf. [[intelligence-typing-flat-connectome]]).

## Le sous-produit : un CONTRÔLE POSITIF gratuit, sur un sujet réel

Le chevauchement fournit 18 paires (canal, logit) dont la réponse est connue **par identité**. Mesuré
sur `recurrent_forward` — le chemin exact par lequel `measure_decision_saliency` lit les logits, et
donc celui d'[[EDR-EVO-004]] — fonction pure, aucun monde, aucun bail :

| | bascules de signe | saillance de décision |
|---|---|---|
| 18 paires DIAGONALES (`obs[46+k]` → `logits[k]`) | **18/18** | **1,000** |
| 18 paires hors diagonale, mêmes canaux | 0/18 | 0,000 |
| no-op de la sonde (deux appels identiques) | — | **0 exactement** |

**L'opérateur de saillance n'est donc PAS aveugle** : il voit une dépendance parfaite quand elle
existe, et ne voit rien quand elle n'existe pas. C'est le contrôle positif que cette famille de
mesures n'avait jamais eu — et il était déjà dans le sujet, gratuit, depuis le début.

Ce que cela règle, et ce que cela ne règle pas : une saillance nulle rapportée par cet instrument est
**interprétable** (l'instrument sait dire oui). Mais « saillance au PLANCHER sur TOUS les canaux »
n'est compatible avec 1,000 sur ces 18 paires que si elles n'ont pas été mesurées — ce qui reste à
**vérifier dans le détail des paires (canal, sortie) d'EVO-004**, pas à supposer. Le contrôle est
désormais gelé dans `tests/sandbox/test_control_family.py`, cas
`test_l_operateur_de_saillance_VOIT_une_dependance_qui_existe_par_IDENTITE` : s'il tombe un jour, ce
n'est pas que le champion a cessé de lire, c'est que l'opérateur a cessé de voir.

## Ce qui reste ouvert

* **Pourquoi le HoF est-il en 64/126 quand tout le reste est en 59/108 ?** Le chevauchement est la
  conséquence, pas la cause. La cause est la divergence de lignée, et elle n'est pas datée ici.
* **Le chevauchement a-t-il été SÉLECTIONNÉ ?** Un fil droit mémoire → action est une politique
  gratuite, disponible sans apprendre un seul poids. Si l'évolution s'en sert, c'est un résultat sur
  ce que la survie récompense ; si elle ne s'en sert pas, c'est un résultat sur la sélection. Les deux
  se mesurent en ablatant les 18 slots partagés seuls — mais cela demande une règle scellée, et ce
  record n'en porte aucune.

Converge [[EDR-S2-BLIND-CHAMPION]] (par lequel il a été trouvé), [[EDR-EVO-004]] (dont il rouvre la
lecture), [[EDR-EVO-011]] (qu'il laisse intact, et pour une raison mesurée).
