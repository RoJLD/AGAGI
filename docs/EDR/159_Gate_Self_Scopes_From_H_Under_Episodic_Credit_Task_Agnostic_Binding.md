---
id: EDR-159
type: EDR
title: "Le gate de conditionnement S'AUTO-SCOPE depuis H sous crédit épisodique : le gate UNIFORME (appliqué à tous les pas, sans béquille de phase) binde +0.232 ≈ 77% du gate scopé +0.298 (3 seeds), là où le MÊME gate uniforme sous TD échoue (−0.286, EDR-148). Le gate apprend à conditionner sur l'état récurrent (se déclencher aux états « ends », pas « means ») sans signal de phase → lève la bornage principale d'EDR-158, binding TASK-AGNOSTIQUE prod-ready. Coût résiduel : accomplissement plus bas (contamination S1 résiduelle)"
status: accepted
gate: null
verdict: GATE_SELF_SCOPES_FROM_H_UNDER_EPISODIC_CREDIT
---

# EDR 159 : le gate s'auto-scope depuis H (binding task-agnostique, lève la bornage d'EDR-158)

## Contexte

EDR-158 a livré le binding en prod via `learn_episode` (crédit épisodique + gate + anti-saturation),
mais avec une bornage : le gate était scopé au dernier pas (`gate_last_only=True`, l'action « ends »).
Or le substrat prod est TASK-AGNOSTIQUE — en prod réelle (épisodes de longueur variable, récompense en
ligne) il n'y a pas de « dernier pas » connu. Question décisive pour la migration : **le gate peut-il
apprendre QUAND se déclencher depuis H SEUL** (appliqué uniformément à tous les pas), sans béquille de
phase ? EDR-148 avait montré que le gate uniforme sous TD différé ÉCHOUE (−0.286, contamination S1) ;
reste à tester sous crédit épisodique.

## Méthode

`tools/torch_prod_gate_meansends.py` gagne `gate_uniform` : quand True, le gate est actif à TOUS les
forwards ET `learn_episode(gate_last_only=False)` l'applique à tous les pas (le readout linéaire de H
doit apprendre à ne PAS se déclencher à S1 — did_x indéterminé — et à se déclencher à S2 — did_x présent
dans H). On oppose, crédit épisodique, gate **scopé** (158) vs **uniforme** (self-scope depuis H).
3 seeds, 1000 ép, échantillonnage stochastique, antisat=6. `binding_gap = P(Y|X) − P(Y|¬X)`.

## Constat

| gate épisodique | binding_gap médian | par seed | hit_end | p_x |
|---|---|---|---|---|
| scopé (`gate_last_only`) | +0.298 | [+0.30, +0.36, +0.00] | 0.279 | 0.319 |
| **uniforme (self-scope H)** | **+0.232** | [+0.07, +0.39, +0.23] | 0.155 | 0.176 |
| *réf. TD uniforme (EDR-148)* | *−0.286* | — | — | 0.070 |

`VERDICT = GATE_SELF_SCOPES_FROM_H_UNDER_EPISODIC_CREDIT`. Le gate uniforme binde +0.232 (77% du scopé,
3/3 seeds positifs) SANS béquille de phase, là où le MÊME gate uniforme sous TD échoue (−0.286).

## Lecture

- **Le gate S'AUTO-SCOPE depuis H.** Un readout linéaire de l'état récurrent apprend à conditionner son
  déclenchement sur H (se déclencher aux états « ends » où did_x est présent, pas « means ») — sans
  qu'on lui dise quel est le « dernier pas ». La bornage principale d'EDR-158 (scoping câblé) est LEVÉE :
  le binding est TASK-AGNOSTIQUE, applicable à des épisodes de longueur inconnue.
- **Le crédit épisodique est le facteur permissif.** Contraste décisif : gate uniforme sous TD différé
  = −0.286 (148), sous épisodique = +0.232 (159). Le retour épisodique multi-actions donne au gate le
  signal pour apprendre le self-scoping ; le TD différé 1-pas ne le peut pas.
- **Coût résiduel de l'uniforme** : hit_end 0.155 vs 0.279, p_x 0.176 vs 0.319 → une contamination S1
  RÉSIDUELLE (le gate se déclenche parfois à S1, réduisant X) coûte de l'accomplissement. Le scoping
  n'est donc PAS requis pour le conditionnement mais l'améliore modestement (moins de contamination).

## Conséquences

- **Migration binding — bornage clé LEVÉE** : la recette prod (gate + anti-saturation + `learn_episode`)
  fonctionne en régime TASK-AGNOSTIQUE (gate uniforme self-scopant). Pour la vraie boucle biosphère, on
  peut activer le gate uniformément ; le scoping de phase reste un OPTIONNEL d'accomplissement (+~0.07
  binding_gap, +accomplissement), pas un prérequis.
- **Recette prod affinée** : `CONDITION_GATE=True` + `GATE_TARGET` + `ANTISAT>0` + `learn_episode`
  (`gate_last_only=False` pour task-agnostique, `True` si l'action ends est connue et l'accomplissement
  prime). Adam ; PAS de TD différé, PAS de BPTT dans le chemin de binding.
- Reste (incrément séparé) : intégration boucle biosphère (segmentation d'épisodes, récompense en ligne)
  et réduction de la contamination S1 résiduelle (gate multiplicatif, ou pénalité de déclenchement hors
  contexte). Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-159`.

## Caveats

1. **Tâche DURE** (hit absolu bas) : le résultat ROBUSTE est la COMPARAISON contrôlée (uniforme +0.232 ≈
   scopé +0.298 ; les DEUX >> TD uniforme −0.286), pas l'absolu.
2. 3 seeds, variance (path-dependence : scopé a 1/3 collapse à +0.00, uniforme a un seed faible +0.07) ;
   le signe (self-scope réel sous épisodique) est net et contraste franchement avec 148.
3. means→ends 2-pas seulement : le self-scope est démontré sur 2 états distinguables (H_S1 vs H_S2) ; la
   généralisation à des séquences longues / états ambigus n'est pas testée (bornage).
4. Gate ADDITIF linéaire ; la contamination S1 résiduelle suggère qu'un gate multiplicatif/à porte
   pourrait mieux supprimer le déclenchement hors-contexte (non testé).
