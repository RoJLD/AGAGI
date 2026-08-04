---
id: EDR-EVO-017
type: EDR
title: "La recherche par NOUVEAUTÉ diversifie sans découvrir — la dernière famille de leviers tombe, l'arc EVO se clôt"
status: active
verdict: NOVELTY_DIVERSIFIES_WITHOUT_DISCOVERING
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-016]
---

## Question

[[EDR-EVO-016]] a établi que le verrou est le **RÉGIME DE RECHERCHE** : même quand lire double la durée de
vie et tient en un seul fil, la sélection ne le trouve pas. [[EDR-EVO-014]] avait fermé les leviers
agnostiques par tirage uniforme ; [[EDR-EVO-015]] la réutilisation de motif. Restait **une** famille : une
recherche guidée par un **signal interne**, qui ne réduit pas l'espace *a priori* mais le parcourt en
s'auto-évaluant.

Règle scellée : `EVO-017.json`, corrigée en `EVO-017-bis.json` (cf. ci-dessous).

## Méthode

Identique à EVO-016 — `hazard=15`, `W=0`, survie seule — **sauf la sélection des élites** :

| bras | élites |
|---|---|
| baseline | 7 par `life_score` |
| nouveauté | 4 par `life_score` + **3 par NOUVEAUTÉ** |

Nouveauté = distance du profil de comportement à la moyenne de population. **Descripteur agnostique** :
taux de bascule d'`argmax` sur **TOUS les canaux** (59), 3 ticks. Aucun canal n'est nommé.

## Pré-vol — le descripteur a dû être CORRIGÉ, et le changement est visible

| descripteur | coût | nouveauté du lecteur | médiane foule | **rang** |
|---|---|---|---|---|
| 4 canaux au hasard × 20 ticks | 0.9 s | 0.0144 | 0.0144 | **3/30** |
| **59 canaux × 3 ticks** | 1.2 s | **0.9667** | 0.0351 | **1/30** |

Le premier descripteur — celui de la règle initiale — est **AVEUGLE** : un lecteur n'est atypique que sur
**le canal qu'il lit**, donc échantillonner 4 canaux en profondeur le rate 93 % du temps. À coût égal, la
couverture complète et superficielle le place **premier sur trente**.

**Règle de conception qui en sort, et qui dépasse cette expérience** : pour détecter une propriété RARE et
CONCENTRÉE, large-et-superficiel bat étroit-et-profond. Le changement a été scellé en `-bis`, pas corrigé
en silence.

## Résultats

| bras | **lecteurs** | sal max | `raw` méd | âge méd | abandons |
|---|---|---|---|---|---|
| baseline | **0/12** | 0.019 | 0.423 | 13 | 0 |
| **nouveauté** | **0/12** | 0.028 | **0.193** | 16 | 0 |

Le baseline **reproduit EVO-016 à l'identique** (0.019 / 0.423 / 13) — les bras sont comparables, vérifié
avant de lire le bras traité.

**La pression a MORDU** : le `raw` médian chute de 0.423 à **0.193**. La nouveauté a bien détourné la
population de l'optimum de fitness, c'est-à-dire empêché la convergence sur la politique FIXE à ~50 %.
Elle a donc **diversifié sans découvrir** : saillance maximale 0.028, contre 0.5 requis et 1.000 pour un
lecteur avéré.

## Verdict

**`NOVELTY_DIVERSIFIES_WITHOUT_DISCOVERING`** — branche pré-enregistrée « 0/12 comme EVO-016 ». **La
dernière famille de leviers testable ici est réfutée, et l'arc EVO se clôt.**

| levier | nature | issue |
|---|---|---|
| [[EDR-EVO-009]] ciblage | injecte la réponse | 12/12 |
| [[EDR-EVO-010]] volume | agnostique | 0/12 |
| [[EDR-EVO-013]] plafond de fan-in | agnostique | inerte |
| [[EDR-EVO-014]] préservation de R | agnostique | 0/11 |
| [[EDR-EVO-015]] réutilisation de motif | agnostique | sous-puissant par construction |
| **EVO-017 nouveauté** | agnostique, auto-évaluée | **0/12 — diversifie sans découvrir** |

**Ce qui unit les cinq échecs** : aucun ne remplace le tirage combinatoire à 3 sur ~11 000. Le ciblage
seul y parvient, en fournissant la réponse. La nouveauté change la MONNAIE de la sélection — elle paie
l'atypicité plutôt que la survie — mais elle ne change pas la **probabilité qu'une arête utile soit
créée**, qui reste celle de `add_connection`.

**Énoncé de clôture** : dans ce substrat, sous les méthodes de recherche testables ici, la découverte d'un
câblage cognitif ne s'obtient qu'en fournissant la réponse. Ce n'est ni un problème d'objectif
([[EDR-EVO-005]], [[EDR-EVO-016]]), ni d'atteignabilité (un fil suffit), ni de récompense (elle double la
durée de vie) — **c'est un problème de mesure de la recherche**, et il n'a pas de levier connu ici.

## Portée (hedges)

* n=12 par bras borne une FRÉQUENCE (borne sup ~22 %), pas une impossibilité.
* **Un seul descripteur et un seul dosage** (3 élites sur 7) ont été testés. Un dosage plus agressif, ou
  un descripteur portant sur les trajectoires plutôt que sur la sensibilité, restent non explorés.
* 35 ères : la nouveauté est réputée lente. Un horizon plus long n'est pas exclu — mais le budget mesuré
  (~90 s/seed) rend un run à 200 ères coûteux, pas impossible.
* La chute de `raw` (0.423 → 0.193) montre que la nouveauté **coûte** en performance de tâche ; à dosage
  plus fort, ce coût croîtrait probablement avant que la découverte n'arrive.
* La lecture requise passe par un `argmax` à 8 voies (sous-tâche DURE, [[EDR-EVO-007]]) ; un seuil de
  signe serait plus facile à découvrir et n'a pas été testé sous nouveauté.

Converge [[EDR-EVO-014]], [[EDR-EVO-015]], [[EDR-EVO-016]], REF-EXPERIMENT-PREFLIGHT.
