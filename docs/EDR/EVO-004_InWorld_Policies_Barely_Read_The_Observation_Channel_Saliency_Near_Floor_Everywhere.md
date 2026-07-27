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
* Mesuré sur des champions `evolve_inworld` (64-dim natifs) ; le HoF principal canonique (59-dim, main) est
  INCOMPATIBLE avec le monde 64-dim de cette branche (dette de divergence d1↔main) — non probé ici.
* Saillance ~0.004 ≠ zéro strict (le non-lecteur synthétique rend 0.000 EXACT) : les champions lisent un
  RÉSIDU, ~200× sous un vrai lecteur. « À peine », pas « rien du tout ».

Converge [[EDR-EVO-001]], [[EDR-EVO-002]], [[EDR-EVO-003]], [[EDR-S2-012]], REF-EXPERIMENT-PREFLIGHT.
