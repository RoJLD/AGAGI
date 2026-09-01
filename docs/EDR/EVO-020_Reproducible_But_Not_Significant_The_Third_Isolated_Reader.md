---
id: EDR-EVO-020
type: EDR
title: "Le troisième lecteur ISOLÉ : reproductible au bit près, et statistiquement indistinguable du bruit (1/17 vs 0/24, p=0.415)"
status: active
verdict: REPRODUCIBLE_BUT_NOT_SIGNIFICANT
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-019]
---

## Question

[[EDR-EVO-019]] avait produit **un** lecteur authentique (saillance 0.982) dans le bras `volume`, à 1/12 —
Fisher p = 1.000, indistinguable. Deux lectures restaient possibles : un vrai effet sous-détecté, ou la
même observation isolée qu'[[EDR-EVO-006]] (rétracté). **Ce record double le n pour trancher.**

Règle scellée : `EVO-020.json`, **première règle écrite sous la nouvelle garde d'exhaustivité** — pas de
branches, une `regle_de_lecture_continue` : le verdict est une FONCTION du taux (Fisher exact bilatéral),
appliquée par le runner lui-même.

## Méthode

2 bras × **24 seeds** (n doublé), sous-tâche `throw`, `hazard=15`, `W=0`, survie seule.
**Pas de plafond de fan-in** : EVO-019 a montré qu'il coûte 5 abandons sur 12 et ampute le bras.

**Puissance déclarée AVANT le run**, dans le fichier scellé : à n=24, un taux vrai de 25 % contre 0 %
donne p≈0.02 (détectable) ; un taux de 8 % contre 0 % donne p≈0.49 (**non détectable**). Ce run peut donc
CONFIRMER un effet fort et **ne peut pas RÉFUTER un effet faible**.

## Résultats

| bras | **lecteurs** | sal max | n effectif | abandons |
|---|---|---|---|---|
| baseline | **0/24** | 0.013 | 24 | 0 |
| **volume** | **1/17** | **0.982** | 17 | **7** |

**Fisher exact bilatéral : p = 0.415** → par la règle scellée, **aucun effet démontré**.

**Le lecteur est REPRODUCTIBLE AU BIT PRÈS.** Comparaison avec EVO-019 (mêmes graines, n plus petit) :

| run | seed | saillance | arêtes créées (compteur) | `\|logit\|` |
|---|---|---|---|---|
| EVO-019 (n=12) | **7** | 0.982 | −12 998 | 0.468 |
| EVO-020 (n=24) | **7** | 0.982 | −12 998 | 0.468 |

Même graine, même génome, même lecture — ce n'est ni du bruit de mesure ni un artefact d'échantillonnage.
L'évolution produit **réellement** un lecteur sur ce seed.

## Verdict

**`REPRODUCIBLE_BUT_NOT_SIGNIFICANT`** — et c'est la distinction que tout l'arc a appris à tenir.

**Reproductibilité et significativité sont des questions DISJOINTES.** Un événement peut être parfaitement
rejouable *et* statistiquement indistinguable du bruit : le déterminisme du seed dit que le phénomène est
réel ; le test dit qu'on ne peut pas l'attribuer au traitement. C'est exactement là qu'[[EDR-EVO-006]] a
dérapé — un lecteur bien réel à 1/12, élevé en mécanisme, puis rétracté.

**Troisième lecteur isolé de l'arc** : EVO-006 seed 0 (jeu mixte, W=5000), puis celui-ci deux fois
(EVO-019 et EVO-020, seed 7, `throw`, W=0). Tous reproductibles, tous à ~1/12–1/24. **Aucune manipulation
n'a jamais déplacé ce taux**, sauf l'injection de la réponse ([[EDR-EVO-009]], 12/12).

Le taux de fond de ~4-8 % de lignées qui découvrent spontanément est donc une **propriété du tirage**, pas
un effet de traitement — cohérent avec l'arithmétique d'[[EDR-EVO-014]] (~0.11 découverte attendue par
lignée) et avec la clôture d'[[EDR-EVO-018]].

## Portée (hedges)

* **Ce run ne réfute pas un effet faible** — la puissance déclarée l'annonçait : à 8 % contre 0 %, p≈0.49.
  Un effet réel mais modeste du `volume` resterait invisible ici. Dire « le volume ne sert à rien » serait
  dépasser la mesure.
* **7 abandons sur 24 dans le bras `volume`** (n effectif 17) : l'opérateur coûte 10 tirages
  supplémentaires par enfant. Le déséquilibre 17 vs 24 est compté et rapporté, pas silencieux.
* Le compteur d'arêtes affiché reste **invalide** (décalage d'indices sous `add_node`, cf. EVO-019) ; il
  n'est reproduit ici que pour établir l'identité bit-à-bit des deux runs, pas comme mesure.
* n=24 borne une fréquence, pas une impossibilité.

## Ce que ce record apporte à la méthode

Première application de la **garde d'exhaustivité** (`IncompleteDiscrimination`), née de l'échec d'EVO-019
dont la règle laissait 1/12 dans un trou entre « ≥ 3/12 » et « 0/12 ». Ici il n'y a plus de branches : le
verdict est calculé par le runner à partir du taux, et **aucune valeur n'échappe à la lecture**.

Converge [[EDR-EVO-006]], [[EDR-EVO-014]], [[EDR-EVO-018]], [[EDR-EVO-019]], REF-EXPERIMENT-PREFLIGHT.
