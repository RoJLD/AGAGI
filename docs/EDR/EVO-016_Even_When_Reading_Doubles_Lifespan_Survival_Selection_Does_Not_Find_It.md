---
id: EDR-EVO-016
type: EDR
title: "Même quand lire DOUBLE la durée de vie et tient en un seul fil, la sélection par la survie ne le trouve pas — le verrou est le RÉGIME DE RECHERCHE"
status: active
verdict: SEARCH_REGIME_IS_THE_LOCK
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-014]
---

## Question

Tout l'arc [[EDR-EVO-005]]→[[EDR-EVO-015]] faisait lire un signal artificiel **que ma propre fitness
payait**. La question d'[[EDR-S2-012]] — *le monde exige-t-il la cognition ?* — n'avait jamais été posée
avec la capacité à la fois **ATTEIGNABLE** et **PAYANTE**. [[EDR-EVO-011]] avait essayé et s'était arrêté
au pré-vol sur trois défauts de harnais.

**Refonte qui évite les trois** : au lieu de forcer une discrimination sur un canal de monde (gaté par
l'inventaire, la visée et un compteur torch-only), on rend le canal **artificiel INFORMATIF pour la
survie**. Signal ±1 = direction à prendre ; se tromper coûte de l'énergie. **Aucun terme cognitif dans la
fitness** (`W=0`) : la sélection ne voit que `calculate_life_score`, la fitness de production.

Règle scellée : `docs/preregistrations/EVO-016.json`.

## Pré-vol — le dommage MORD et lire PAIE

| hazard | génome | âge méd | taux d'erreur | proies |
|---|---|---|---|---|
| 0 | non-lecteur | 24.5 | 0.895 | 12 |
| 0 | LECTEUR câblé | **19.0** | 0.261 | 11 |
| 15 | non-lecteur | 6.5 | 0.823 | 6 |
| 15 | **LECTEUR câblé** | **14.0** | 0.176 | 7 |

**Lire double la durée de vie sous pression** (6.5 → 14.0), et le contrôle à hazard 0 montre que
l'avantage vient bien de l'INFORMATION : sans punition, le lecteur survit *moins* bien (19.0 vs 24.5).
Le banc peut donc répondre, et les deux issues sont interprétables.

⚠️ Défaut trouvé et corrigé au pré-vol : la 1ʳᵉ version lisait `_cog_sig` **avant** `super().step()`, or ce
champ est posé DANS `step()` puis consommé à la fin — le dommage ne pouvait structurellement **jamais**
s'appliquer (mesuré : 0 coup). **5ᵉ défaut « l'effet ne peut pas se produire » de la semaine, 5ᵉ attrapé
au pré-vol.** Corrigé en s'appuyant sur le score que le parent calcule déjà.

## Résultats

| bras | **lecteurs** | saillance max | `raw` méd | âge méd |
|---|---|---|---|---|
| hazard0 (contrôle) | **0/12** | 0.002 | 0.035 | 18 |
| **hazard15** | **0/12** | **0.019** | **0.423** | 13 |

**La sélection A BIEN agi** : le `raw` médian passe de 0.035 à **0.423** — sous le dommage, les agents se
déplacent massivement Est/Ouest. Mais la saillance reste à **0.019** : ils ne LISENT pas. Ils ont adopté
la politique **FIXE** qui rapporte ~50 % sans information — exactement le plafond non-cognitif
d'[[EDR-EVO-005]], retrouvé ici sous survie PURE.

## Verdict

**`SEARCH_REGIME_IS_THE_LOCK`** — branche pré-enregistrée, et c'est le résultat le plus fort de l'arc :

> **Même quand lire double la durée de vie, que la capacité tient en UN SEUL FIL, et que la sélection est
> démontrée capable de façonner le comportement, elle ne trouve pas la lecture.**

Les trois explications concurrentes sont éliminées, chacune par une mesure :

| explication candidate | éliminée par |
|---|---|
| « l'objectif n'a pas de contenu cognitif » | ici il en a un, mesuré : +115 % de durée de vie |
| « la capacité est inatteignable » | un seul poids suffit (lecteur câblé, saillance 1.000) |
| « la sélection est inerte » | elle déplace `raw` de 0.035 à 0.423 |

Reste le **régime de recherche**. Et il est déjà caractérisé par l'arc : la découverte exige de créer une
arête précise (3 sur ~11 000, [[EDR-EVO-008]]) dans un point de fonctionnement favorable
([[EDR-EVO-012]]) — et [[EDR-EVO-014]] a montré qu'aucun prior agnostique ne réduit cette recherche.

**Ça nuance [[EDR-S2-012]] plutôt que de le confirmer platement** : le problème n'est pas que la survie
soit aveugle à la cognition — ici elle la paierait cher. C'est que **la sélection ne peut pas atteindre ce
qu'elle paierait**. Le verrou est en amont de l'objectif, dans la capacité de l'opérateur de variation à
produire le câblage, et il est indépendant de la présence ou non d'une récompense.

## Portée (hedges)

* n=12 par bras borne une FRÉQUENCE (borne sup ~22 %), pas une impossibilité.
* La lecture requise est un `argmax` à 8 voies (sous-tâche DURE au sens d'[[EDR-EVO-007]]) ; une
  sous-tâche en seuil de signe serait plus facile à découvrir. Non testé sous survie seule.
* Le `raw` de 0.423 est proche du plafond de politique fixe (0.5) mais ne l'atteint pas : la sélection
  n'épuise même pas le gain non-cognitif disponible en 35 ères.
* Le hazard est appliqué par une SOUS-CLASSE du monde, pas par le monde de prod — il ne teste donc pas
  « le monde tel qu'il est » mais « un monde où lire paie ». C'est l'intention, et c'est aussi la limite.
* Aucun abandon sur budget dans les deux bras.

Converge [[EDR-EVO-005]], [[EDR-EVO-008]], [[EDR-EVO-012]], [[EDR-EVO-014]], [[EDR-S2-012]],
REF-EXPERIMENT-PREFLIGHT.
