---
id: EDR-EVO-006
type: EDR
title: "Le crédit PARTIEL est-il le gradient manquant ? — objectif cognitif in-world à K sous-tâches indépendantes, à une seule variable près d'EVO-005"
status: active
verdict: PARTIAL_CREDIT_IS_THE_MISSING_GRADIENT
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-005]
---

## Question

[[EDR-EVO-005]] a mesuré qu'un objectif cognitif in-world dense déplace la population **jusqu'au plafond
exact de ce qu'on gagne sans lire (0.472 contre un plafond analytique de 0.500), et pas au-delà** — avec
un budget de recherche SUPÉRIEUR à celui qui suffit en proxy (1050 contre 800 évaluations). Il en a tiré
« verrou = structure de gradient », renforcé par le fait que le CRÉDIT ([[EDR-S2-010]]) échoue sur la même
carte : deux optimiseurs indépendants au même mur désignent le paysage, pas l'optimiseur.

Ce record met cette conclusion **à l'épreuve**, sur la seule différence structurelle qui restait entre le
proxy qui réussit et l'in-world qui échoue :

| | proxy EVO-002 | in-world EVO-005 |
|---|---|---|
| sorties notées | **K=2 bits, INDÉPENDAMMENT** | 1 seule (`argmax`) |
| gain d'une mutation partielle | +1/K même si le reste est faux | **0 — tout ou rien** |
| issue | lecteur PARFAIT, 8/8 seeds | aucune lecture, 0/30 runs |

> **Le verrou d'EVO-005 était-il la GRANULARITÉ du crédit ?**

## Méthode — une seule variable change

Le monde consomme **plusieurs décisions indépendantes par tick**, pas seulement le déplacement :
`action = argmax(logits[:8])` (`world_1_stoneage.py:1291`), `do_throw = logits[8] > 0` (:1319) et
`out_accept = logits[14] > 0` (:957). D'où K=3 sous-tâches indépendantes, chacune avec **le même plafond
de politique fixe (0.5) qu'à K=1** — le repère d'EVO-005 est donc conservé À L'IDENTIQUE :

* 3 signaux ±1 i.i.d. dans `obs[5]`, `obs[10]`, `obs[23]` — trois canaux `np.zeros` **câblés en dur**,
  re-vérifiés à `0.0` EXACT dans le monde de base ;
* réponses : Est/Ouest (l'action exécutée), signe de `logits[8]`, signe de `logits[14]`, capturés via
  `_apply_social_consensus` — donc **les logits exacts sur lesquels le monde décide** ;
* `_cog_ticks` compte les ESSAIS (K par tick), donc `measure_cognitive_rate` et le plafond CHANCE=0.5
  restent valides sans modification, à K quelconque. Poids identiques à EVO-005 (0 / 200 / 800 / 5000),
  5 seeds × 35 ères, sous bail `kuzu`. **K=1 reste le défaut** : les instruments calibrés d'EVO-005 sont
  inchangés (non-régression vérifiée).

## Pré-vol — l'assertion CENTRALE est neuve : le crédit partiel existe-t-il vraiment ?

Si câbler 1 sous-tâche sur 3 ne rendait pas un score strictement entre le plancher et le lecteur complet,
il n'y aurait **aucun gradient à offrir** et le banc ne testerait rien (`assert_ablation_changes_something`
appliqué à la GRANULARITÉ). Mesuré sur des lecteurs câblés à la main :

| câblé | `raw` | move | throw | accept |
|---|---|---|---|---|
| 0/3 | 0.378 | 0.093 | 0.502 | 0.538 |
| **1/3** | **0.581** | **0.736** | 0.524 | 0.484 |
| 2/3 | 0.751 | 0.743 | **1.000** | 0.510 |
| 3/3 | **0.939** | 0.817 | 1.000 | 1.000 |

Deux propriétés font de ce banc un test valide, et elles sont MESURÉES, pas argumentées :

1. **Isolation exacte** : câbler la sous-tâche *k* ne fait monter que *k* ; les autres restent collées à
   0.50, le plafond d'une politique fixe. La sonde est sensible ET spécifique.
2. **Une seule mutation réussie FRANCHIT la barre** : 1/3 câblé donne 0.581 > 0.500. C'est précisément ce
   qui était impossible à K=1, où il fallait un lecteur complet d'un coup.

Contrôle négatif : le lecteur complet privé de l'information tombe de 0.939 à **0.369**.

## Règle de lecture — PRÉ-ENREGISTRÉE (écrite avant d'avoir vu les résultats)

Identique à celle d'EVO-005 (classe E11), plus une clause propre à K>1 :

* **DV primaire** `raw`, plafond ANALYTIQUE 0.500. Le franchir est une affirmation d'**EXISTENCE**
  (vérifiable sur un seul seed), pas une comparaison de populations -> le garde-fou « pas de verdict
  positif sous n=12 » ne s'y applique pas. Contrastes ENTRE BRAS : **directionnels** seulement (n=5).
* **NOUVEAU — lecture par sous-tâche** : une sous-tâche au-dessus de 0.5 pendant que les autres y restent
  est la signature du crédit PARTIEL saisi. C'est l'issue qui confirmerait « le verrou était la
  granularité ».
* **Ce qui RÉFUTERAIT le verdict d'EVO-005** : si rien ne dépasse 0.5 alors que le gradient est VÉRIFIÉ
  au pré-vol et qu'une seule mutation suffit à franchir la barre, alors « verrou = structure de gradient »
  est faux et le blocage est ailleurs (opérateur de mutation, taille de population, ou le monde lui-même).
  Ce record est donc écrit pour pouvoir **casser** le précédent, pas pour le confirmer.

## Résultats (4 bras × 5 seeds × 35 ères, K=3)

| W | `raw` méd | move | throw | accept | **`raw` max** |
|---|---|---|---|---|---|
| 0 | 0.343 | 0.021 | 0.496 | 0.512 | 0.409 |
| 200 | 0.464 | 0.429 | 0.487 | 0.520 | 0.501 |
| 800 | 0.354 | 0.050 | 0.498 | 0.503 | 0.468 |
| 5000 | 0.466 | 0.432 | 0.496 | 0.495 | **0.612** |

**Le bras W=5000, seed 0 FRANCHIT le plafond analytique : `raw = 0.612`, avec la signature exacte que la
règle pré-enregistrée annonçait — `throw = 0.925` pendant que `move` (0.434) et `accept` (0.477) restent
à la chance.** Une sous-tâche apprise, les deux autres non : c'est le crédit PARTIEL saisi.

**Confirmation mécaniste** (champion REPRODUIT à l'identique — `raw` 0.612, `throw` 0.925 — puis persisté
dans `results/evo006_champion_w5000_seed0.npz`) :

| sujet | `obs[10]` → bascule de `sign(logits[8])` | canal 5 (sans rapport) |
|---|---|---|
| **champion évolué** | **1.000** | 0.000 |
| lecteur CÂBLÉ à la main (contrôle +) | 1.000 | 0.000 |
| non-lecteur (plancher) | 0.000 | 0.000 |

La politique évoluée lit causalement `obs[10]` et le convertit en sa décision de lancer sur **100 % des
couples agent × tick** — indiscernable d'un lecteur câblé, et **exactement spécifique** (rien sur un canal
non pertinent). C'est le premier lecteur in-world bâti par l'évolution dans ce dépôt.

⚠️ **La règle pré-enregistrée n'était pas applicable telle qu'écrite, et je ne l'assouplis pas après
coup.** Elle exigeait `raw > 0.5` **ET** saillance > 0.1 sur le même seed. Or la saillance pré-enregistrée
(`measure_channel_saliency(decision=True)`) lit la bascule d'`argmax(logits[:8])` : elle est **aveugle par
construction** aux sous-tâches `throw`/`accept`, qui ne passent pas par l'argmax — sur un lecteur `throw`
PARFAIT elle rend 0.000 (contre-exemple désormais gelé en test). Statut honnête des deux moitiés :
* la **DV primaire est pré-enregistrée et satisfaite** (0.612 > plafond ANALYTIQUE 0.500) ;
* la confirmation mécaniste utilise un instrument (`measure_decision_saliency`) choisi **APRÈS** avoir vu
  quelle sous-tâche avait bougé — donc **post-hoc (classe E11)**. Elle est corroborative, pas
  constitutive du verdict. Elle porte toutefois ses deux contrôles MESURÉS (lecteur câblé 1.000,
  non-lecteur 0.000) et une spécificité de canal exacte, ce qu'un choix opportuniste n'aurait pas.

## Verdict

**`PARTIAL_CREDIT_IS_THE_MISSING_GRADIENT`** — l'hypothèse d'[[EDR-EVO-005]] sort **renforcée de l'épreuve
montée pour la casser**. À une seule variable près (la granularité du crédit), l'issue s'inverse :

| record | crédit | issue |
|---|---|---|
| [[EDR-EVO-004]] | survie seule | ne lit RIEN — saillance au plancher sur tous les canaux |
| [[EDR-EVO-005]] | objectif dense, **tout ou rien** | achète le plafond NON-cognitif (0.472) et rien au-delà |
| **EVO-006** | objectif dense, **PARTIEL** | **lecteur PARFAIT sur une sous-tâche (bascule 1.000)** |

Le mécanisme est intelligible et mesuré : à K=1, franchir 0.5 exigeait un lecteur complet d'un seul coup ;
à K=3, **une seule mutation réussie** fait passer de 0.378 à 0.581 (pré-vol). L'évolution in-world n'était
pas incapable de bâtir de la lecture — **elle n'avait aucun premier barreau**. C'est la loi d'[[EDR-090]]
(« pas de barreau survivable, pas d'escalade ») transposée du curriculum de létalité à la STRUCTURE DU
CRÉDIT, et ça rejoint [[warm-start-transversal-law]] : le verrou est le régime, pas la capacité.

Conséquence pour le fil in-world : « la survie n'a pas de contenu cognitif » ([[EDR-S2-012]]) reste vrai,
mais insuffisant comme diagnostic. **Ajouter du contenu cognitif ne suffit pas — il faut qu'il soit
DÉCOMPOSABLE**, c'est-à-dire qu'un progrès partiel soit payé. C'est une prescription de design d'objectif,
opposable et testable, là où « investir dans l'objectif » restait une orientation.

## Portée (hedges)

* **EXISTENCE, pas systématicité** : 1 seed sur 5 franchit (et 1 de plus effleure, 0.501 à W=200). La
  médiane ne franchit dans aucun bras. Conforme à la règle pré-enregistrée — 0.5 est un plafond
  ANALYTIQUE, donc le franchir est vérifiable sur un seul seed — mais **ce record n'affirme PAS que
  l'évolution in-world bâtit systématiquement un lecteur**. Un verdict de fréquence exige n ≥ 12.
* Les contrastes entre bras (W, et K=3 vs K=1) restent **DIRECTIONNELS** à n=5.
* **Les trois sous-tâches ne sont pas d'égale difficulté** : `throw`/`accept` sont des seuils de SIGNE
  (un seul poids suffit) tandis que `move` exige de gagner un `argmax` à 8 voies. Sans surprise, c'est
  `throw` qui est appris. Le résultat dit donc « il existe un barreau franchissable », pas « toutes les
  sous-tâches le sont » — et une partie du gain vient de ce que j'ai ajouté des sous-tâches PLUS FACILES,
  pas seulement plus nombreuses. Distinguer les deux exigerait K sous-tâches de difficulté APPARIÉE.
* On note la **décision**, pas son effet : un `throw` décidé sans lance ne part pas (le monde gate).
* ⚠️ **Le seuil 0.500 est valide POUR CE JEU DE SOUS-TÂCHES, et ne se transporte pas** (constaté le
  2026-07-27 en montant EVO-007). Il sépare ici parce que le jeu contient `move`, dont un non-lecteur
  n'obtient que 0.09-0.38 : le bras de CONTRÔLE plafonne à **0.409**, donc aucun seed ne le franchit par
  bruit, et le 0.612 est bien un signal. Mais sur un jeu de sous-tâches **uniquement** en seuils de SIGNE,
  une politique fixe obtient 0.5 EN ESPÉRANCE et la moitié des seeds le dépasse par bruit
  d'échantillonnage (mesuré : non-lecteur apparié = 0.514, et 2 seeds de contrôle d'EVO-007 à 0.527 /
  0.505). **Règle** : re-vérifier le PLANCHER du non-lecteur à chaque changement de jeu de sous-tâches ;
  un seuil pré-enregistré n'est valide que pour la tâche sur laquelle il a été calibré.
* Génome persisté cette fois (`results/evo006_champion_w5000_seed0.npz`) — la passe EVO-005 ne l'avait pas
  fait, en violation de la consigne de `CLAUDE.md`, ce qui a coûté un ré-entraînement pour le prober.
  ⚠️ `results/` est gitignoré : l'artefact est LOCAL. Il n'est pas load-bearing pour autant — le champion
  se régénère **bit pour bit** par `evolve_cognitive(5000.0, 0, eras=35, K=3)` (reproduction vérifiée :
  `raw` 0.612 et `throw` 0.925 à l'identique), ce qui est la garantie qui compte.

Converge [[EDR-EVO-005]], [[EDR-EVO-004]], [[EDR-EVO-002]], [[EDR-S2-010]], [[EDR-090]],
REF-EXPERIMENT-PREFLIGHT.
