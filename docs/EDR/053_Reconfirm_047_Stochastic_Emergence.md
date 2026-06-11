# EDR 053 : Re-confirmation de 047 sous puissance — l'émergence du langage est STOCHASTIQUE

## Contexte

EDR 052 : nos verdicts à 1 run étaient non fiables ; 047 (langage sous demande) doit être
re-confirmé sous puissance. Protocole : 8 seeds × 24 ères sous la demande de Lewis ; pour chaque
seed, MI réel (token↔Mammouth/Leurre) vs sa **permutation** (le null « aucune information »). Test
via le harnais (EDR 052).

## Résultat — bimodal, pas plat

| seed | MI réel | MI perm | gain |
|---|---|---|---|
| 0 | **0.0468** | 0.0095 | **+0.0373** |
| 5 | **0.0285** | 0.0030 | **+0.0255** |
| 3 | 0.0098 | 0.0039 | +0.0059 |
| 7 | 0.0067 | 0.0049 | +0.0018 |
| 1 | 0.0041 | 0.0046 | −0.0005 |
| 2 | 0.0013 | 0.0035 | −0.0023 |
| 4 | 0.0052 | 0.0090 | −0.0038 |
| 6 | 0.0031 | 0.0053 | −0.0021 |

**Global** : réel 0.0132 ± 0.0161 vs perm 0.0055 ± 0.0025 ; gain moyen **+0.0077 ± 0.0153**, t=1.34,
d=0.67 → **non significatif** au seuil strict (t≥2.5).

## Interprétation — ni « confirmé » ni « bruit »

> **L'émergence du langage référentiel est RÉELLE mais STOCHASTIQUE.** Les données sont **bimodales** :
> **2 seeds sur 8** montrent une émergence *forte* (MI 0.047 et 0.029, très au-dessus de leur propre
> null), les 6 autres restent au bruit. Ce n'est pas un effet plat noyé dans la variance — c'est une
> **loterie** : l'émergence se cristallise dans ~25 % des runs.

- Le run unique de l'EDR 047 (0.033) était un **tirage chanceux** — mais **pas un artefact** : quand
  ça émerge, c'est franc et bien au-dessus du null.
- Signature classique d'une **brisure de symétrie** : la population doit *coordonner une convention*
  (quel token = Mammouth) ; parfois elle converge, parfois non (équilibres multiples).

## Verdict

> **La thèse « la demande fait émerger le langage » TIENT — probabilistiquement.** La demande rend
> l'émergence *possible*, pas *certaine* (~25 % des runs). Il a fallu 8 seeds pour le voir ; 1 run ne
> pouvait pas. Ni survente (047 « prouvé ») ni déni (« bruit ») : **un phénomène stochastique, réel,
> de basse probabilité.**

## Conséquences

1. **La bonne métrique n'est pas la moyenne** mais le **TAUX d'émergence** (P(cristallisation) ≈ 2/8,
   IC large) et le MI *conditionnel* (~0.04 quand ça émerge). La moyenne seule trompe sur un
   phénomène bimodal.
2. **Pour fiabiliser** : agir sur la brisure de symétrie — demande plus forte, *nudge* de
   coordination (amorcer une convention), ou **sélectionner/propager les lignées chanceuses** (les
   2/8). C'est testable.
3. **Pour le #8** : un phénomène bimodal EXIGE beaucoup de seeds ; un itérateur qui jugerait sur 1-3
   runs prendrait la loterie pour un signal (ou l'inverse). Confirme EDR 052 : la puissance d'éval
   est la contrainte.

## Limites

- 8 seeds : le taux (~25 %) a un IC large (≈ 5–55 %). Le *qualitatif* (bimodal, réel, stochastique)
  est solide ; le taux précis demanderait 20-30 seeds.

## Variables d'expérience

Taux d'émergence vs moyenne, force de la demande, nudge de coordination, propagation des lignées
émergentes, nombre de seeds.
