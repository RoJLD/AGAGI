---
id: EDR-EVO-004
type: EDR
title: "Les politiques évoluées in-world dépendent à peine de l'observation courante : la saillance action/canal est au PLANCHER sur TOUS les canaux (~200× sous un lecteur), ni survie ni cognitif — la racine mécaniste de « proxy 9 / in-world 0 »"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-003]
---

## Question
[[EDR-EVO-003]] a montré que la politique in-world ignore causalement UN canal cognitif (le type d'apex,
obs[4]). L'outil — perturber un canal d'obs, mesurer Δ sur les logits d'action — **généralise** : pour
CHAQUE canal, la politique évoluée le LIT-elle ? Hypothèse mécaniste testable du gap « proxy 9 / in-world 0 » :
les champions lisent-ils les canaux de SURVIE (direction proie, hp) et ignorent-ils les canaux COGNITIFS
(type d'apex, bits d'autel, langage) ?

## Méthode
`measure_channel_saliency` (`tools/evo_memory_inworld.py`) : in-contexte (obs RÉELLES du monde), pour chaque
agent et chaque canal `k`, mettre obs[k]=+1 vs −1 et lire la moyenne |Δ logits[:8]| (logits d'action), forward
NON destructif (`recurrent_forward` sur le H courant). Renvoie la saillance par canal = de combien l'action
dépend de ce canal. Carte des canaux (`world_1_stoneage.py:611-624`) : SURVIE = 0-3 (direction proie), 36
(hp), 43 (num_preys), 19-22 (lidar) ; COGNITIF = 4 (type apex), 11-13 (autel + bits cognitive_demand), 15-18
(langage in_hear). Sujets : 4 champions évolués in-world (`evolve_inworld`, 64-dim natifs).

**Contrôle positif de la sonde (générateur A)** : un génome SYNTHÉTIQUE qui câble obs[4] vers les move-outputs.

## Résultats

| sujet | saillance SURVIE | saillance COGNITIF | canal le PLUS lu |
|---|---|---|---|
| **lecteur synthétique** (obs[4]→action) | 0.000 | 0.124 (= 0.99 sur le seul canal 4) | **0.993** |
| champion in-world seed0 | 0.0021 | 0.0012 | 0.0044 |
| champion in-world seed1 | 0.0081 | 0.0127 | 0.0238 |
| champion in-world seed2 | 0.0052 | 0.0052 | 0.0092 |
| champion in-world seed3 | 0.0044 | 0.0027 | 0.0055 |
| **médiane champions** | **0.0048** | **0.0039** | ≤ 0.024 |

- Instrument VALIDÉ : le lecteur synthétique isole parfaitement son canal (0.99 sur obs[4], 0.000 partout
  ailleurs) -> la sonde est sensible ET spécifique.
- Les champions lisent l'obs courante **~200× plus faiblement** qu'un lecteur (médiane 0.004 vs 0.99). Le
  canal le PLUS lu de n'importe quel champion est à **≤ 0.024**.
- **Ni survie ni cognitif** : `survie ≈ cognitif` sur tous les seeds (seed1 lit même un peu plus le cognitif).
  L'hypothèse « lit la survie, ignore le cognitif » est RÉFUTÉE — ils ne lisent presque RIEN, des deux.

## Contrôle positif au niveau de l'OBJECTIF (le maillon manquant, ajouté 2026-07-23)
Le contrôle ci-dessus est un contrôle d'INSTRUMENT (un génome câblé à la main), pas un contrôle SCIENTIFIQUE :
il laissait ouverte l'échappatoire « l'opérateur d'évolution de ce dépôt est peut-être incapable de produire
un lecteur, quel que soit l'objectif » — auquel cas le verrou serait la RECHERCHE, pas l'objectif. Fermé sur le
banc proxy d'[[EDR-EVO-002]] (`measure_cue_saliency`) : MÊME substrat, MÊME opérateur (`apply_mutations`),
MÊME banc — seul l'OBJECTIF change.

| source (objectif d'évolution) | acc rappel différé | `sign_flip` (lit-il l'indice ?) |
|---|---|---|
| **DEMAND** (l'objectif EXIGE la mémoire), 3/3 seeds | 1.00 | **1.00** |
| MEMORYLESS (leurre à l'encode -> mémoire inutile), médiane | ~0.5 | **0.00** |
| FRESH (non évolué), médiane | ~0.5 | 0.48 (bruit, pas de suivi systématique) |

**L'évolution produit un lecteur PARFAIT quand l'objectif l'exige, et AUCUN quand il ne l'exige pas.** Le
verrou est donc bien l'objectif et non la recherche. Validation interne fortuite : le seed MEMORYLESS qui
présentait la « fuite incidente » d'EVO-002 (acc xeval 1.00) rend `sign_flip = 1.00` — l'instrument est
d'accord avec l'accuracy jusque sur le cas atypique, il ne la fabrique pas.

## Robustesse : le verdict survit au changement de GRANDEUR mesurée (classe E17)
⚠️ En construisant le contrôle ci-dessus, l'instrument s'est fait prendre à son propre piège : la saillance en
AMPLITUDE ne séparait rien (DEMAND à `acc 1.00` mesuré 0.13, soit SOUS un génome frais à 0.10). Cause : le
substrat est CONTRACTIF et la décision se lit par `np.sign(preds)` — **le signe porte l'information, pas
l'amplitude**. C'est la 2ᵉ occurrence de cette erreur dans l'arc (après la réfutation de `sep(D)`), désormais
**classe E17 du registre**, née `exécutable` (contre-exemple gelé : un génome qui RÉSOUT la tâche, `acc 1.000`,
a une saillance en amplitude de **2e-6**, indiscernable d'un non-lecteur à 0.0).

Ce record utilisant lui aussi une saillance en amplitude, il a été **immédiatement re-mesuré sur la grandeur
qui AGIT in-world** — le taux de bascule de l'action, `action = argmax(logits[:8])`
(`world_1_stoneage.py:1291`), via `measure_channel_saliency(decision=True)` :

| sujet | bascule d'`argmax` (max sur canaux) |
|---|---|
| lecteur synthétique (canal 4 câblé) | **1.00** |
| champions in-world (3 seeds) | **0.003 · 0.060 · 0.003** |

**Le verdict TIENT** : perturber n'importe quel canal ne change l'action choisie que dans ≤ 6 % des
(agent × tick), contre 100 % pour un lecteur avéré sur son canal. Un verdict qui survit à un changement de la
grandeur mesurée — obtenu en cherchant à le casser — est bien plus solide qu'un verdict jamais réinterrogé.

## Verdict
**La politique évoluée in-world dépend à peine de l'observation courante** : sa sensibilité instantanée
action/obs est au plancher sur TOUS les canaux (~200× sous un lecteur avéré). Les champions survivent par une
**règle quasi-fixe, faiblement réactive** — ils ne PROCESSENT pas le monde perçu pour agir. C'est la racine
mécaniste la plus profonde de « proxy 9 / in-world 0 » : la cognition exige de LIRE et transformer l'entrée ;
la politique évoluée par la survie ne le fait quasiment pas.

Unifie l'arc : [[EDR-EVO-001]] (l'évolution GÈLE le substrat, contractif+sparse) · [[EDR-EVO-003]] (elle
IGNORE le canal de type) · EVO-004 (elle ignore ~TOUS les canaux). Converge causalement [[EDR-S2-012]] : la
survie n'a aucun contenu cognitif, donc n'exige PAS de lire les canaux — et l'évolution ne les lit pas. Le
verrou est l'OBJECTIF, confirmé jusqu'au niveau du câblage obs→action.

## Conséquence
Renforce la prescription de tout l'arc : investir dans un OBJECTIF qui EXIGE de lire et transformer l'entrée
(comme le proxy EVO-002, qui bâtit la mémoire quand l'objectif l'exige), pas dans l'archi/substrat. Un objectif
de survie, même durci, ne fait pas apparaître la LECTURE du monde.

## Portée (hedges)
* Saillance = sensibilité INSTANTANÉE (un pas) obs→action. N'exclut pas une intégration LENTE de l'obs dans le
  H récurrent sur plusieurs ticks ; mais pour la cognition réactive (traiter l'entrée courante), la sensibilité
  instantanée au plancher est décisive, et cohérente avec la near-stationarité d'EVO-003 (moved_frac≈0.06).
* Mesuré sur des champions `evolve_inworld` (**59** entrées natives = la dimension du monde sur cette
  branche, `WorldConfig.num_inputs = 59`) ; le HoF principal `data/hall_of_fame.pkl` est en **64 entrées /
  126 sorties**, donc INCOMPATIBLE avec ce monde (dette de divergence d1↔main) — non probé ici.
  ⚠️ **Correction du 2026-07-27** : la 1ʳᵉ rédaction de ce hedge INTERVERTISSAIT les deux dimensions
  (« champions 64-dim, HoF 59-dim »). La conclusion — incompatibilité, HoF canonique non probé — est
  inchangée, mais le SENS de l'écart était faux, ce qui enverrait quiconque reprend le fil construire un
  adaptateur à l'envers. Les deux nombres sont désormais MESURÉS (`WorldConfig().agent.num_inputs` = 59 ;
  `pickle.load('data/hall_of_fame.pkl')` -> `(num_inputs, num_outputs, num_nodes) = (64, 126, 172)` sur
  les 10 entrées) et non plus écrits de mémoire — mandat D du pré-vol appliqué aux MÉTADONNÉES.
* Saillance ~0.004 ≠ zéro strict (le non-lecteur synthétique rend 0.000 EXACT) : les champions lisent un
  RÉSIDU, ~200× sous un vrai lecteur. « À peine », pas « rien du tout ». ⚠️ Depuis E17, **l'amplitude n'est
  plus la grandeur de référence** : lire le verdict sur la bascule d'`argmax` (≤ 6 % vs 100 %), pas sur le
  0.004. Les deux concordent ici, mais seule la seconde est la grandeur qui agit.
* Le contrôle positif au niveau de l'objectif est mesuré sur le banc PROXY (I=8), pas in-world : il établit
  que l'OPÉRATEUR sait produire un lecteur, pas qu'il le saurait à 64 canaux. Les deux mondes diffèrent aussi
  en dimension d'entrée — l'argument porte sur la présence/absence de lecture, pas sur une comparaison
  d'amplitudes entre bancs.

Converge [[EDR-EVO-001]], [[EDR-EVO-002]], [[EDR-EVO-003]], [[EDR-S2-012]], REF-EXPERIMENT-PREFLIGHT.
