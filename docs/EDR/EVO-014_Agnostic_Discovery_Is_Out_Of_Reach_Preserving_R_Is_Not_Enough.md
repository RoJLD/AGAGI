---
id: EDR-EVO-014
type: EDR
title: "La découverte AGNOSTIQUE est hors de portée : préserver R ne suffit pas, et aucun prior structurel ne peut collapser 6372 candidates en 3"
status: active
verdict: AGNOSTIC_DISCOVERY_OUT_OF_REACH
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-013]
---

## Question

[[EDR-EVO-009]] lève le verrou de la découverte (1/12 → 12/12) mais **injecte la réponse** : son biais
connaît les 3 arêtes qui comptent. [[EDR-EVO-010]] réfute le volume. [[EDR-EVO-012]] identifie la grandeur
gouvernante, `R = |w_signal| / |logit|`. [[EDR-EVO-013]] montre que R a deux régimes. Reste la question
qui commande tout l'arc : **un levier AGNOSTIQUE à la tâche peut-il produire des lecteurs ?**

**Contrainte arithmétique posée AVANT toute mesure** (scellée dans `EVO-014.json`) : le biais d'EVO-009
réduit les candidates de ~11 000 à **3**. Un prior purement structurel « entrée → sortie » ne descend qu'à
59 × 108 = **6 372**, dont 3 sont bonnes — gain **1.7×**, pas 100×. **Aucune règle agnostique ne peut
narrower la recherche jusqu'à la réponse.** Si un levier existe, il n'agit donc pas par ciblage mais par
**préservation de R** : garder chaque arête essayée ÉVALUABLE au lieu de la laisser noyée.

## Méthode

2 bras × 12 seeds, jeu MIXTE, `W=5000`, mêmes graines. **Seul `add_connection` change** (patch LOCAL) :
source = nœud d'**ENTRÉE**, destination = **SORTIE de plus faible fan-in**. Aucun canal ni sortie NOMMÉ —
uniquement les rôles structurels.

**Pré-vol** — les deux contrôles obligatoires passent :

| | arêtes E→S créées | fan-in sortie `throw` | `\|logit\|` médian |
|---|---|---|---|
| baseline | (compteur non instrumenté) | **0** — sortie DÉBRANCHÉE | 0.626 (activation à vide) |
| lowfanin | 64 | **1** | **0.000** |

Le `0.000` n'est donc pas une déconnexion : `throw` a bien une entrée, et le logit est **au seuil**. R est
réellement préservé. ⚠️ Le compteur du baseline affiche 0 par artefact (seule la fonction biaisée
l'incrémente) — **classe E4, 4ᵉ fois cette semaine** ; les 64 du bras traité restent valides.

## Résultats

| bras | **lecteurs** | `raw` méd | âge méd | proies méd | échecs |
|---|---|---|---|---|---|
| baseline | 1/12 | 0.453 | 13 | 8 | 0 |
| **lowfanin** | **0/11** | 0.446 | **18** | 9 | 0 |

Saillance maximale du bras traité : **0.023**. Aucun seed n'approche 0.5.

**Les deux échappatoires d'un nul sont fermées** :
* « le levier ne faisait rien » → réfuté par le pré-vol (`|logit|` 0.000 avec entrée réelle, 64 arêtes E→S) ;
* « le bras était cassé » → réfuté par la survie, **meilleure** dans le bras traité (âge 18 vs 13, proies
  9 vs 8, 0 échec numérique). Le coût de viabilité redouté au pré-vol ne s'est pas matérialisé.

R préservé + agents sains + zéro lecteur.

## Verdict

**`AGNOSTIC_DISCOVERY_OUT_OF_REACH`** — branche pré-enregistrée « lecteurs ~ baseline malgré `|logit|`
bas ». Le tableau de l'arc est désormais complet :

| levier | nature | issue |
|---|---|---|
| [[EDR-EVO-009]] ciblage | **injecte la réponse** (11 000 → 3) | **12/12** |
| [[EDR-EVO-010]] volume | agnostique | 0/12 — sature le dénominateur |
| [[EDR-EVO-013]] plafond de fan-in | agnostique | **inerte** (fan-in déjà < 1) |
| **EVO-014** préservation de R | agnostique | **0/11** — R préservé, agents sains, rien |

**Conclusion, et elle est bornée** : dans ce substrat et sous cette recherche, la découverte d'un câblage
cognitif ne s'obtient qu'en **fournissant la réponse**. Préserver R est nécessaire (EVO-012) mais pas
suffisant ; narrower structurellement est arithmétiquement impossible (1.7×) ; augmenter le volume est
contre-productif (EVO-010). L'arc EVO doit le dire plutôt que de continuer à chercher un levier que ces
quatre mesures excluent.

**Ce que ça n'exclut PAS** — et c'est là qu'est la suite : un opérateur qui ne soit pas un tirage uniforme
sur les arêtes. Toutes les variantes testées échantillonnent des arêtes INDIVIDUELLES. Un opérateur
travaillant sur des **sous-espaces** (blocs, motifs répétés, réutilisation de sous-graphes déjà utiles),
ou une recherche guidée par un signal interne (nouveauté, diversité comportementale), n'a pas été testé et
échappe à l'argument arithmétique — qui ne borne que les priors uniformes sur des arêtes isolées.

## Portée (hedges)

* 1 seed abandonné sur budget dans le bras traité (11/12 exploités), compté et rapporté.
* Le baseline reproduit son 1/12 attendu — vérifié AVANT de lire le bras traité, comme annoncé.
* La borne arithmétique (6372 candidates) vaut pour un prior **uniforme sur des arêtes individuelles**.
  Elle ne dit rien des opérateurs structurés, non testés ici.
* Le pré-vol mesurait aussi 64 sorties mortes sur 108 (contre 51 au baseline) : le levier appauvrit le
  répertoire d'actions. Ça n'a pas nui à la survie **dans ce régime**, mais ce n'est pas un no-op.
* n=12 borne une fréquence, pas une impossibilité : un phénomène plus rare que ~22 % resterait invisible.

Converge [[EDR-EVO-009]], [[EDR-EVO-010]], [[EDR-EVO-012]], [[EDR-EVO-013]], REF-EXPERIMENT-PREFLIGHT.
