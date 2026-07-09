---
id: EDR-162
type: EDR
title: "Le crédit épisodique NE rachète PAS la rétention du craft (EDR-127) — 2e proxy H-unif, NÉGATIF qui RAFFINE le pari. Sous un coût de craft ≥0.3, ON (gate+learn_episode) ET OFF (TD) abandonnent le craft (craft_late ~0.04, adv ~0), alors qu'à c=0 ON retient à peine (+0.02). Mécanisme : valeur du moyen = −c + r·P(ends|means) ; avec binding FAIBLE (P≈0.25, plafond substrat) le craft est net-négatif même quand r−c>0 → abandon rationnel + cercle vicieux. La rétention est EN AVAL de la FORCE du binding, pas un problème de crédit séparé → le crédit épisodique active le binding (161) mais pas assez FORT. Tempère l'axe 3 H-unif"
status: accepted
gate: null
verdict: NO_RETENTION_ADVANTAGE_RETENTION_DOWNSTREAM_OF_BINDING_STRENGTH
---

# EDR 162 : le crédit épisodique ne rachète pas la rétention du craft (elle est en aval de la force du binding)

> **⚠️ MÉCANISME CORRIGÉ PAR EDR-164.** Le constat (rétention à COÛT échoue) TIENT, mais l'explication
> ci-dessous est FAUSSE : `P(consume|craft)` est en réalité HAUT (0.79-0.97), pas « ≈0.25 » (0.25 = le
> comp_rate INCONDITIONNEL, pas le P conditionnel). Le binding est FORT ; l'effondrement est une
> INSTABILITÉ DYNAMIQUE de bassin (falaise nette à c*≈0.04, ≪ borne statique r·P), pas une
> non-rentabilité statique. Levier corrigé = warm-start / bassin (131/132), pas « renforcer le binding ».
> Lire EDR-164 pour le mécanisme correct.

## Contexte

2e proxy standalone du pari H-unif ([[torch-inworld-integration-plan]] : rétention(127), spécialisation
et binding partageraient le MÊME verrou de crédit conditionnel, rachetable par `learn_episode`). EDR-161
a validé l'axe binding/composition (la capacité PAIE sous demande). Ici l'axe RÉTENTION : EDR-127 = le
craft est ATTEINT mais NON RETENU. Prédiction H-unif : une action CRAFT coûteuse (−c immédiat) à payoff
DIFFÉRÉ (+r au consume) devrait être RETENUE sous crédit épisodique (voit le net r−c) mais décroître
sous TD 1-pas (voit le coût immédiat). STANDALONE (`tools/craft_retention_probe.py`).

## Méthode

Jeu craft→consomme : S1 CRAFT coûte −c immédiat ; S2 CONSUME paie +r SSI craft fait. TD reçoit le coût
à S1 et le bénéfice à S2 ; épisodique reçoit le retour net. Métrique NOUVELLE vs 161 : `craft_late`
(rétention en fin d'entraînement) + trajectoire early→late + sweep du COÛT c. Capacité ON (gate additif
task-agnostique + `learn_episode`, 159) vs OFF (`learn` TD, 148). 3 coûts × 2 seeds × 800 ép, r=1.0.

## Constat

| coût c | craft_late ON | craft_late OFF | avantage | comp_late ON / OFF |
|---|---|---|---|---|
| 0.00 | 0.14 | 0.12 | +0.02 | 0.11 / 0.03 |
| 0.30 | 0.04 | 0.05 | −0.00 | 0.01 / 0.01 |
| 0.60 | 0.04 | 0.04 | −0.00 | 0.01 / 0.01 |

`VERDICT = NO_RETENTION_ADVANTAGE`. Dès un coût ≥0.3, ON ET OFF effondrent le craft au plancher (~0.04) ;
le crédit épisodique n'apporte AUCUN avantage de rétention. À c=0 (sans pression), ON ne retient qu'à
peine (0.14, +0.02). L'avantage NE croît PAS avec le coût — l'inverse de la prédiction H-unif.

## Lecture

- **La rétention est EN AVAL de la FORCE du binding, pas un problème de crédit séparé.** Valeur espérée
  du moyen : `E[craft] = −c + r·P(consume | craft)`. Le binding est FAIBLE sur ce substrat (P≈0.25,
  plafond vu en 158/159/161) → à c=0.3, `E[craft] = −0.3 + 1.0·0.25 = −0.05 < 0` : le craft est
  net-NÉGATIF même quand le net IDÉAL r−c=+0.7 serait positif. Abandon RATIONNEL, puis **cercle vicieux**
  (craft ↓ → moins d'occasions de consume → binding ↓ → craft encore moins rentable → effondrement).
- **Le crédit épisodique ACTIVE le binding (161) mais pas assez FORT pour soutenir un moyen coûteux.**
  Les 3 phénomènes du pari H-unif ne sont donc PAS rachetés uniformément par le même mécanisme : la
  rétention exige une FORCE de binding (P(ends|means) > c/r) que ce substrat dégénéré n'atteint pas.
- **Ne contredit pas 161** : 161 avait un coût de faim mais AUCUN coût sur le moyen lui-même (craft
  gratuit) → l'avantage émergeait. 162 met un coût SUR le moyen → révèle le seuil de rentabilité que le
  binding faible ne franchit pas. Les deux ensemble bornent : la capacité paie si le moyen est gratuit
  ou le binding fort ; elle échoue si le moyen est coûteux ET le binding faible.

## Conséquences

- **Tempère l'axe 3 H-unif (in-world)** : NE PAS supposer que porter `learn_episode` rachète
  automatiquement la rétention du craft (127). Le rachat de 127 est CONDITIONNEL à `P(consume|craft) >
  coût/récompense` — donc à une FORCE de binding que le substrat actuel n'a pas (plafond ~0.25). Levier
  requis = RENFORCER le binding (capacité substrat, pas crédit), OU réduire le coût relatif du craft
  in-world. Informe [[torch-inworld-integration-plan]] avant l'exécution de l'axe 3.
- **Réconcilie EDR-127** : « craft attaint mais non retenu » = le craft n'est pas rentable tant que la
  suite (consume) n'est pas fiable ; la rétention n'est pas un knob indépendant, elle SUIT la force du
  binding. Converge le diagnostic 127 (verrou = rétention) en le raffinant (rétention ⊂ force binding).
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-162`.

## Caveats

1. **Substrat dégénéré 172-nœuds** (binding plafonne ~0.25) : sur un substrat à binding fort, la
   rétention POURRAIT être rachetée (le seuil c/r serait franchi). Le négatif est SUR CE substrat ;
   il ne réfute pas la rétention en général, il la subordonne à la force du binding.
2. 2 seeds, 800 ép ; le ROBUSTE est l'effondrement au plancher dès c≥0.3 pour les DEUX bras (pas de
   séparation ON/OFF), pas les valeurs absolues.
3. Seuil non localisé finement (testé c ∈ {0, 0.3, 0.6}) ; la rétention tient peut-être à c très faible
   (<0.1) — bornage, mais même à c=0 l'avantage est marginal (+0.02), donc pas de régime à fort gain.
4. Proxy synthétique 2-pas ; le test réel de l'axe 3 reste in-world (replay sous crédit épisodique).
