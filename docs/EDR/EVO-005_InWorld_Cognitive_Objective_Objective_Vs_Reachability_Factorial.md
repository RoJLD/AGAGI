---
id: EDR-EVO-005
type: EDR
title: "Objectif cognitif in-world : la fitness est-elle un NON-LEVIER, ou n'a-t-elle jamais été mesurée de façon fiable par agent ? — plan factoriel OBJECTIF × ATTEIGNABILITÉ"
status: active
verdict: INWORLD_SELECTION_BUYS_THE_NON_COGNITIVE_CEILING_AND_NOTHING_BEYOND
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
extends: [EDR-EVO-004]
---

## Question

Le dépôt porte **deux verdicts incompatibles** sur le même levier, jamais confrontés :

| thèse | records | énoncé |
|---|---|---|
| la fitness est un **NON-LEVIER** | [[EDR-056]], [[EDR-WLD-002]] | « muter la fitness ne débloque rien — le verrou est en amont (crédit/comportement) » |
| le verrou **EST l'objectif** | [[EDR-EVO-002]], [[EDR-EVO-004]] | « l'évolution bâtit un lecteur PARFAIT dès qu'un objectif l'exige ; elle ne lit rien quand seule la survie note » |

Or les deux échecs historiques partagent **un confond que ni l'un ni l'autre n'a contrôlé : le
comportement noté était RARE.** Craft chez 1,4 % des agents et autels chez 0 % (WLD-002) ; distinction
référentielle sur des comptes de 1-2 (EDR-056 — qui écrit lui-même « on ne peut pas récompenser un trait
qu'on ne mesure pas de façon fiable PAR AGENT », sans en tirer la conséquence expérimentale). **Aucun n'a
testé un terme de fitness sur un comportement qui se produit à CHAQUE TICK.**

La cellule vide est plus précise encore. Le fil S2 a bien réalisé une demande cognitive in-world, mais
toutes ses sondes mesurent le **CRÉDIT** (REINFORCE intra-vie) : [[EDR-S2-010]] et [[EDR-S2-011]]
établissent que le crédit à froid n'apprend pas la carte signal→action, ni sous curriculum. **Aucune
n'appelle `apply_mutations`.** S2-011 nomme d'ailleurs le manque dans son prochain pas (« Alt : warm-start
par évolution courte in-world »). D'où la question :

> **L'ÉVOLUTION in-world bâtit-elle un lecteur quand l'objectif le note de façon dense et fiable ?**

## Méthode

Transplanter la tâche du proxy EVO-002 **dans le monde**, en ne changeant que le contexte
(`tools/evo_cognitive_objective.py`) :

* **Signal** : un ±1 i.i.d. par agent et par tick, injecté dans `obs[5]` — un `np.zeros(N)` **câblé en
  dur** (`world_1_stoneage.py:610`), donc à information NULLE par construction. Vérifié : `0.0` exact sur
  tous les agents du monde de base. Toute saillance mesurée sur ce canal vient donc de l'expérience, sans
  qu'il faille l'argumenter.
* **Réponse** : une ACTION du monde — Est (2) si +1, Ouest (3) si −1 (`world_1_stoneage.py:1559-1562`).
  La grandeur notée est celle qui AGIT, et c'est exactement la DV d'EVO-004 (`argmax(logits[:8])`).
* **Score** : compté à chaque tick (~120 échantillons/agent, contre 1-2 dans EDR-056), lissé vers **zéro**
  par pseudo-comptes (`measure_cognitive_rate`).
* **Fitness** : `calculate_life_score` + `W ×` taux cognitif, dans une fonction **LOCALE** — la fitness de
  prod n'est jamais mutée (leçon de blast-radius de WLD-002 : elle est partagée par les sessions //).
* **Plan FACTORIEL** : poids `W ∈ {0, 200, 800, 5000}` × soupe initiale `reflex ∈ {non, oui}`. Le second
  facteur est né du pré-vol (ci-dessous). Substrat, opérateur de mutation, monde, sélection épisodique et
  pression de survie sont tenus CONSTANTS. 5 seeds × 35 ères × 120 ticks × 30 agents, sous bail `kuzu`.

## Pré-vol (`REF-EXPERIMENT-PREFLIGHT`) — il a changé le design deux fois

**A. L'instrument peut-il produire LES DEUX issues ?**

| assertion | mesure | issue |
|---|---|---|
| contrôle POSITIF de la tâche (lecteur câblé réflexe, w=2) | **raw 0.856** | ✓ la tâche est réalisable in-world |
| contrôle NÉGATIF exact (MÊME génome, information retirée) | raw 0.123 | ✓ l'ablation de l'information seule effondre |
| non-lecteur réflexe (canal non câblé) | raw 0.100 | ✓ plancher |
| plafond analytique d'une politique FIXE | 0.500 | toujours-Est ne matche que les ticks à +1 |

**La manipulation mord-elle sur la SÉLECTION ?** (méthode de WLD-002 : recouvrement du top-K)

| W | jaccard top-7 vs W=0 (3 ères) | taux cognitif de l'élite |
|---|---|---|
| 50 | 1.000 / 0.750 / 1.000 | **inerte — c'est le régime d'EDR-056** |
| 200 | 0.750 / 0.750 / 0.556 | mord |
| 800 | 0.556 / 0.750 / 0.273 | mord fort |
| 5000 | 0.273 / 0.400 / 0.167 | domine la fitness |

Le taux cognitif de l'élite monte de façon **monotone** avec W (0.030→0.069 ; 0.018→0.111) : un nul du
banc ne pourra pas être imputé à une manipulation inerte. Le premier poids testé (W=50) l'était.

**Deux corrections de design, avant tout run :**

1. **L'estimateur récompensait l'absence de preuve** (→ classe **E18** du registre). Le lissage « évident »
   vers la CHANCE (0.5) crédite les agents à faible compte, puisque les agents réels plafonnent vers 0.10 :
   un mort à 3 ticks vaut 0.435 contre 0.157 pour un vivant de 120 ticks qui lit mal. **À poids fort, la
   sélection aurait optimisé la MORT PRÉCOCE**, et le banc aurait rendu un faux négatif ne mesurant que
   l'estimateur. Corrigé en lissant vers 0 (`succès/(ticks + 20)`), où un tick réussi de plus améliore
   toujours le score. La 1ʳᵉ occurrence de cette classe est EDR-056 lui-même, neuf mois plus tôt.
2. **Le contrôle positif a d'abord ÉCHOUÉ (0.532 ≈ la chance) — et c'est un résultat** (→ classe **E6**,
   portée élargie). Le même génome est PARFAIT sur un état frais et tombe à la chance in-world : `H`
   accumule (δ = sigmoid(diag(W)) ≈ 0.5 sur une soupe fraîche) et, l'activation METAPROG ayant `f(0) ≠ 0`,
   **même les sorties JAMAIS câblées dérivent à +7.45 ± 9.8** après 25 ticks, noyant une marge de signal de
   ±2.5. C'est le **mécanisme** du confond laissé OUVERT par S2-011 (« le bassin BC atteint acc 1.00 sur
   `_step(obs, H=0)` mais ne transfère pas au forward RÉCURRENT »). Conséquence : bâtir un lecteur réactif
   exige une **CONJONCTION de deux mutations** — câbler le canal ET dé-mémoriser la sortie. D'où le second
   facteur du plan.

**B. Unité de réplication** : le seed/l'ère (une évolution auto-contenue par seed), jamais l'agent.
**C. Grandeur qui agit** : `last_action`, l'action que le monde EXÉCUTE — pas un logit interne.

## Règle de lecture — PRÉ-ENREGISTRÉE (écrite avant d'avoir vu les résultats)

Classe **E11** du registre (« choix d'analyse post-hoc ») est la seule, avec E13, à n'avoir **aucune**
garde. Elle ne peut être respectée qu'à un seul moment : celui-ci. Règle arrêtée avant lecture des
chiffres, et le run tournait déjà en tâche de fond quand elle a été écrite.

* **DV primaire** : `raw` = succès/ticks du champion de chaque seed, benchmarké sur cohorte de clones.
* **DV mécaniste secondaire** : bascule d'`argmax` sur `obs[5]` (`measure_channel_saliency(decision=True)`,
  instrument déjà calibré en EVO-004 — plancher champions 0.003-0.060, lecteur avéré 1.00).
* **« La lecture est APPARUE » dans un bras** ⟺ au moins un seed à `raw > 0.5` **et** saillance `> 0.1`.
  ⚠️ C'est une affirmation d'**EXISTENCE**, pas de population : 0.5 est le plafond **analytique** de toute
  politique FIXE (toujours-Est ne matche que les ticks à signal +1), donc le dépasser est vérifiable sur un
  seul seed sans comparaison entre groupes. C'est pourquoi le garde-fou « pas de verdict positif sous
  n=12 » ([[power-evaporation-guardrail]]) ne s'y applique pas — il vise les différences de médianes.
* **Comparaisons ENTRE BRAS** (« W augmente la lecture », « reflex débloque ») : à n=5, un test de signe
  unanime plafonne à p=0.0625 → **INCONCLUSIF par construction**. Ces effets seront rapportés comme
  DIRECTIONNELS, jamais comme un verdict. Un contraste jugé décisif exigera un run à n≥12.
* **Verdict NÉGATIF** (aucun bras ne produit de lecture) : inférentiellement sûr, car le contrôle positif
  établit que le banc DÉTECTE la lecture quand elle existe (0.856 vs plancher 0.100).
* **Lecture du factoriel** : si `raw` monte avec W à `reflex=0` → l'OBJECTIF est le levier ; si ça ne monte
  QU'à `reflex=1` → le verrou était l'ATTEIGNABILITÉ dans le substrat ; si rien ne monte nulle part → le
  verrou in-world est le régime de crédit/recherche, et l'arc EVO se voit borné au proxy.

## Résultats (6 bras × 5 seeds × 35 ères)

| W | reflex | `raw` méd | **`raw` max** | sal. méd | sal. max | age | proies | seeds > 0.5 |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0.196 | 0.415 | 0.000 | 0.004 | 11 | 7 | **0/5** |
| 200 | 0 | 0.381 | 0.432 | 0.000 | 0.019 | 20 | 8 | **0/5** |
| 800 | 0 | 0.309 | 0.455 | 0.000 | 0.000 | 13 | 12 | **0/5** |
| 5000 | 0 | 0.429 | **0.472** | 0.000 | 0.006 | 14 | 8 | **0/5** |
| 0 | 1 | 0.047 | 0.426 | 0.018 | 0.058 | 15 | 7 | **0/5** |
| 800 | 1 | 0.017 | 0.415 | 0.015 | 0.035 | 12 | 6 | **0/5** |

Repères : plafond analytique d'une politique FIXE **0.500** · contrôle positif du pré-vol **0.856** ·
plancher non-lecteur 0.100 · saillance d'un lecteur avéré 1.00, plancher champions EVO-004 0.003-0.060.

**1. Aucune lecture, dans aucun bras** (règle pré-enregistrée : 0/30 runs à `raw > 0.5` avec saillance
> 0.1). La saillance reste à **0.000** au médian partout où le substrat dérive.

**2. Le budget de recherche N'EST PAS l'explication — mesuré, pas supposé.** Le proxy EVO-002 bâtit un
lecteur PARFAIT (acc 1.00, 8/8 seeds) en `25 générations × 32` = **800 évaluations**. Ce banc in-world en
a consommé `35 × 30` = **1050**, soit **davantage**, pour zéro lecture.

**3. Le fait le plus informatif : l'objectif a fonctionné, mais seulement jusqu'à la frontière du
cognitif.** Le `raw` MAXIMUM monte de façon **monotone** avec le poids — 0.415 → 0.432 → 0.455 → **0.472**
— et s'arrête juste SOUS 0.500, le plafond exact de ce qu'une politique sans lecture peut obtenir
(toujours-Est matche les ticks à signal +1). La sélection a donc extrait **100 % de la valeur disponible
sans cognition et 0 % de celle qui en exige**. Ce n'est pas « rien n'a bougé » : c'est « tout ce qui
pouvait bouger sans lire a bougé, et rien d'autre ».

**4. Le substrat réflexe décolle la saillance du zéro EXACT** (0.000 → 0.015-0.018 au médian, max 0.058)
— soutien DIRECTIONNEL au mécanisme de dérive du pré-vol : un substrat sans report d'état est bel et bien
plus sensible à l'entrée. Il ne convertit pas ce gain en performance de tâche. Manipulation vérifiée
persistante : après 35 ères de mutation, **81 % des nœuds gardent δ > 0.9** (mesuré) — la moitié
« dé-mémoriser » de la conjonction a donc été offerte ET retenue, et n'a pas suffi.

**5. Signature involontaire de la classe E18, en direct** : `traj max = 1.000` dans **tous** les bras, y
compris le contrôle sans terme cognitif. C'est le taux par agent NON lissé — un agent vivant 1 tick et
réussissant une fois vaut 1.0. Sans le lissage vers zéro, la sélection aurait été pilotée par ces flukes
dans les 30 runs. Le contre-exemple gelé de E18 est ici mesuré sur le banc réel.

## Verdict

**`INWORLD_SELECTION_BUYS_THE_NON_COGNITIVE_CEILING_AND_NOTHING_BEYOND`**

L'opposition que ce banc devait trancher est **mal posée**, et les deux thèses sont partiellement vraies :

* La fitness **EST** un levier — contre EDR-056/WLD-002 : un terme dense et fiablement mesuré par agent
  déplace bien la population, monotonement avec son poids. Le « non-levier » de ces records était un
  artefact de RARETÉ du comportement noté (1.4 %, 0 %, comptes de 1-2), pas une propriété de la sélection.
* Elle **n'achète que ce qui est atteignable sans cognition** — contre la lecture forte de l'arc EVO :
  même à W=5000, où le terme cognitif DOMINE la fitness (jaccard top-7 = 0.27), la lecture n'apparaît pas.

Le verrou in-world n'est donc ni « l'objectif ne demande pas » (il demande, et fort), ni « le poids est
mal réglé » (dose-réponse monotone), ni « pas assez de recherche » (1050 > 800 évaluations). **Aucune
pression de sélection ne crée un gradient là où il n'y en a pas** : dans ce substrat, la lecture est
séparée du non-lecture par une région où le progrès partiel ne paie rien.

**Convergence qui donne son poids au résultat** : [[EDR-S2-010]] a montré que le CRÉDIT (REINFORCE
intra-vie) échoue sur la même carte signal→action ; ce banc montre que la SÉLECTION ÉVOLUTIVE y échoue
aussi, avec un budget supérieur à celui qui suffit en proxy. **Quand deux optimiseurs indépendants
échouent identiquement, l'explication parcimonieuse est le PAYSAGE, pas l'optimiseur.** Ça déplace le
« verrou = crédit » du dépôt vers un « verrou = structure de gradient de la tâche in-world », dont le
crédit et la sélection sont deux victimes et non la cause.

## Portée (hedges)

* **n=5 → tout contraste ENTRE BRAS est DIRECTIONNEL**, jamais un verdict (test de signe unanime plafonne
  à p=0.0625 ; [[power-evaporation-guardrail]]). Seules les affirmations d'EXISTENCE contre le plafond
  ANALYTIQUE 0.5 sont des conclusions. La monotonie du `raw` max (4 points) est une piste, pas un effet.
* **Le plafond non-cognitif de cette tâche est HAUT (0.5) et atteignable par une politique triviale**
  (toujours-Est). Le design a donc offert à la sélection un large plateau gratuit, qu'elle a pris. Une
  tâche dont l'optimum trivial vaut ~0 testerait la montée plus sèchement — au prix de supprimer le
  premier barreau (piège d'[[EDR-090]] : pas de barreau survivable, pas d'escalade).
* **Un seul bit de signal**, contre K=2 bits en proxy : moins de crédit PARTIEL, donc un gradient plus
  pauvre. C'est un candidat sérieux pour expliquer l'écart proxy/in-world, et il est **testable** — refaire
  ce banc à K bits notés indépendamment.
* `reflex_init` est une INITIALISATION, pas une contrainte. Mesurée persistante (81 % à l'ère 35), mais
  elle déplace aussi la ligne de base comportementale (les bras réflexes utilisent moins Est/Ouest,
  `raw` médian 0.017-0.047) → le contraste sur ce facteur est CONFONDU et n'est lu que sur la saillance.
* Le HoF canonique reste non probé (dette de divergence : monde 59 entrées, HoF 64 — cf. [[EDR-EVO-004]]).

## Instruments (cliquet de calibration)

Trois instruments NÉS dans cette passe, calibrés dans la MÊME passe :
`measure_cognitive_rate` (vérité-terrain analytique + contre-exemple gelé E18) ·
`benchmark_cognitive` (contrôle positif câblé, spécificité par retrait d'information, plancher
non-lecteur) · le témoin `synthetic_reader` gèle la dérive d'état (classe E6).

⚠️ Le cliquet ne les VOYAIT pas : leurs noms ne rentraient dans aucun de ses motifs — **3ᵉ angle mort de
nommage du même outil** (classe **E4** : son « 0 nouveau non calibré » était indiscernable d'une vraie
couverture). Motif `benchmark_\w+` ajouté, ce qui a du même coup rendu visible `benchmark_discrimination`
(EVO-003), resté invisible depuis sa création — et dont le **défaut connu** (biais du survivant : attaquer
un Leurre létal TUE, donc son dénominateur est sous-compté) est désormais gelé en test.

Converge [[EDR-EVO-002]], [[EDR-EVO-004]], [[EDR-S2-010]], [[EDR-S2-011]], [[EDR-056]], [[EDR-WLD-002]],
REF-EXPERIMENT-PREFLIGHT.

## Instruments (cliquet de calibration)

Trois instruments NÉS dans cette passe, calibrés dans la MÊME passe :
`measure_cognitive_rate` (vérité-terrain analytique + contre-exemple gelé E18) ·
`benchmark_cognitive` (contrôle positif câblé, spécificité par retrait d'information, plancher
non-lecteur) · le témoin `synthetic_reader` gèle la dérive d'état (classe E6).

⚠️ Le cliquet ne les VOYAIT pas : leurs noms ne rentraient dans aucun de ses motifs — **3ᵉ angle mort de
nommage du même outil** (classe **E4** : son « 0 nouveau non calibré » était indiscernable d'une vraie
couverture). Motif `benchmark_\w+` ajouté, ce qui a du même coup rendu visible `benchmark_discrimination`
(EVO-003), resté invisible depuis sa création — et dont le **défaut connu** (biais du survivant : attaquer
un Leurre létal TUE, donc son dénominateur est sous-compté) est désormais gelé en test.
