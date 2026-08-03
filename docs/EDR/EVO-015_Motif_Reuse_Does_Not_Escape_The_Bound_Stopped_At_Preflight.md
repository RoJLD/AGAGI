---
id: EDR-EVO-015
type: EDR
title: "La réutilisation de motif n'échappe PAS à la borne — arrêté au pré-vol, et le raisonnement scellé était FAUX"
status: active
verdict: MOTIF_REUSE_DOES_NOT_ESCAPE_THE_BOUND
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-014]
---

## Question

[[EDR-EVO-014]] ferme les leviers agnostiques par **tirage uniforme sur des arêtes isolées** (borne :
6 372 candidates, 3 bonnes, narrowing 1.7× au mieux) et laisse ouverte une famille : les opérateurs
**STRUCTURÉS**, qui exploitent ce que le génome a déjà trouvé. Levier testé : **réutilisation de motif** —
copier une arête entrée→sortie existante vers une AUTRE sortie, en héritant de la source.

## Pré-vol : les contrôles PASSENT, et pourtant on n'a pas lancé

| bras | copies | arêtes E→S finales | vivants | NaN |
|---|---|---|---|---|
| baseline | 0 | 31 | 2 | non |
| motif | **66** | **40** | 3 | non |

Compteur instrumenté **dans les deux bras** cette fois (classe E4, 4 fois cette semaine un compteur n'a pu
lire que zéro). Manipulation réelle, viabilité comparable. Le run était techniquement prêt.

**Il n'a pas été lancé, parce que l'arithmétique refaite au pré-vol le rend ininterprétable d'avance.**

## ⚠️ Le raisonnement SCELLÉ était faux — et le sceau l'a rendu constatable

La règle scellée (`EVO-015.json`) justifiait le levier ainsi : « si l'entrée héritée est un canal de
signal, **3 des 108 destinations sont bonnes** → ~3 % par copie contre 0.05 %, soit ~60× ».

**C'est faux.** Chaque canal de signal a **UNE SEULE** sortie correcte — `SIG_COLS[1]` va vers `throw`,
pas vers n'importe laquelle des trois sous-tâches. Le calcul juste :

| opérateur | probabilité qu'un tirage crée une arête LECTRICE |
|---|---|
| baseline (uniforme) | 3 / 11 000 ≈ **2.7 × 10⁻⁴** |
| motif (source héritée) | (3/59 que la source soit un canal) × (1/108 que la destination soit la bonne) ≈ **4.7 × 10⁻⁴** |

Soit **1.7×** — exactement le gain du prior structurel déjà réfuté par [[EDR-EVO-014]], pas les 60×
annoncés. À n=12 sur une base de ~8 %, ça donnerait ~1.7 lecteur contre 1 : **indétectable**. Lancer
aurait produit 25 minutes de calcul pour un nul qu'on n'aurait pas su lire.

Le sceau a fonctionné comme prévu : l'erreur est datée dans le fichier, je ne peux pas la réécrire, et
c'est ce qui rend la correction vérifiable plutôt que déclarative.

## Verdict

**`MOTIF_REUSE_DOES_NOT_ESCAPE_THE_BOUND`** — la réutilisation de motif **hérite la source mais pas la
cible**, et c'est la cible qui porte l'information. Elle reste donc dans la famille bornée par EVO-014.

**Correction à porter à [[EDR-EVO-014]]** : sa « seule direction restante » était trop optimiste. Réutiliser
un motif ne suffit pas ; il faudrait réutiliser une **paire (source, cible) déjà éprouvée**. Or dans ce
dispositif, la seule façon de savoir qu'une paire est bonne est de mesurer qu'elle paie — c'est-à-dire
**la sélection elle-même**, qui clone déjà les élites. L'opérateur structuré n'ajoute rien que la
sélection ne fasse pas.

**Ce qui reste, et c'est plus étroit qu'annoncé** : un signal interne qui ORIENTE la recherche sans
connaître la tâche — nouveauté, diversité comportementale, ou un critère de « sortie dont la variation
change le comportement ». Ces approches ne narrowent pas l'espace a priori : elles le parcourent en
s'auto-évaluant. Aucune n'est testée ici, et aucune n'est bon marché.

## Portée (hedges)

* Aucun run n'a été fait : ce record documente un **arrêt au pré-vol**, pas un résultat empirique. Le
  levier n'est pas mesuré nul — il est calculé sous-puissant.
* Le calcul suppose que la source héritée est tirée uniformément parmi les arêtes E→S existantes ; si
  l'évolution enrichissait les canaux de signal en source, le gain serait supérieur. Non mesuré.
* La soupe fraîche contient **0** arête E→S : le levier est vide tant qu'`add_connection` n'en a pas créé
  une, donc il ne peut pas accélérer la PREMIÈRE découverte — seulement la propager.

Converge [[EDR-EVO-014]], [[EDR-EVO-012]], REF-EXPERIMENT-PREFLIGHT.
