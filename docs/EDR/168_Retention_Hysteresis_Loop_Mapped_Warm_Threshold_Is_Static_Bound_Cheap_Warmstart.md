---
id: EDR-168
type: EDR
title: "Boucle d'hystérésis de la rétention CARTOGRAPHIÉE (item a) : seuil cold ≈0.04 (barrière de bootstrap) vs seuil warm ≈ r·P ≈ 0.9 (rentabilité STATIQUE) = hystérésis ~22×, validant la borne r·P d'EDR-164. Au-dessus de 0.9 (crafter net-négatif) le bassin haut est MÉTASTABLE (tient à 600ép, s'érode à 2000ép : craft 0.13→0.05). Profondeur du warm-start : ~50 ép suffisent (levier bon marché). Complète 164/167"
status: accepted
gate: null
verdict: RETENTION_HYSTERESIS_LOOP_MAPPED_WARM_THRESHOLD_IS_STATIC_BOUND
---

# EDR 168 : la boucle d'hystérésis de la rétention, cartographiée (seuil warm = borne statique, warm-start bon marché)

## Contexte

EDR-167 a montré une hystérésis large (cold s'effondre à c*≈0.04, warm retient ≥0.30) prouvant la
bistabilité d'EDR-164. Item (a) : localiser le BORD SUPÉRIEUR (seuil warm c_hi) et la PROFONDEUR de
warm-start nécessaire — pour fermer la boucle d'hystérésis.

## Constat

**EXP1 — seuil warm (ws=400, 2 seeds, 600 ép mesurés) :**

| c | warm craft_late | P |
|---|---|---|
| 0.3 | 0.119 | 0.91 |
| 0.5 | 0.121 | 0.91 |
| 0.7 | 0.118 | 0.91 |
| 0.9 | 0.117 | 0.92 |
| 1.1 | 0.107 | 0.91 |

**Contrôle métastabilité (c=1.1, ws=400, trajectoire early→late) :** ep=600 craft 0.141→0.121 (decay
+0.02) ; **ep=2000 craft 0.129→0.052 (decay +0.077)** → à c=1.1 le bassin S'ÉRODE lentement vers le
niveau cold.

**EXP2 — profondeur du warm-start (c=0.2, 2 seeds) :**

| warmstart_episodes | craft_late | P |
|---|---|---|
| 0 (cold) | 0.049 | 0.27 |
| 50 | 0.127 | 0.91 |
| 100 | 0.114 | 0.90 |
| 200 | 0.118 | 0.89 |
| 400 | 0.121 | 0.91 |

`VERDICT = RETENTION_HYSTERESIS_LOOP_MAPPED`.

## Lecture

- **La boucle d'hystérésis a DEUX seuils de nature différente**, validant EDR-164 :
  - **cold c* ≈ 0.04 = barrière de BOOTSTRAP** (dynamique) : au-dessus, impossible d'ENTRER le bassin haut
    depuis froid (le coût tue le craft avant que le binding ne monte).
  - **warm c_hi ≈ r·P ≈ 0.9 = rentabilité STATIQUE** : en-dessous, le bassin haut est un vrai attracteur
    STABLE (crafter net-positif E[craft]=−c+r·P>0, le gradient le maintient) ; à 600 ép warm tient
    jusqu'à ~0.9 franchement.
  - **Au-delà de r·P (crafter net-négatif) : MÉTASTABLE** — le « warm tient à 1.1 » de 600 ép est un effet
    de TIMESCALE ; à 2000 ép le craft décroît (0.13→0.05) car E[craft]<0 érode lentement. La borne r·P
    d'EDR-164 est donc LE seuil warm réel (à convergence), pas 1.1.
  - Hystérésis stable ≈ [0.04 → 0.9] = **~22×**, plus une frange métastable au-dessus.
- **Le warm-start est BON MARCHÉ** : ~50 ép de pré-entraînement à coût 0 suffisent à verrouiller le bassin
  haut (craft 0.13, P 0.91) vs cold-collapse ; transition nette entre 0 et 50. Au-delà de 50, plateau.

## Conséquences

- **Boucle d'hystérésis de la rétention COMPLÈTE** : entrer ≤0.04 (cold) ; stable jusqu'à r·P≈0.9 (warm) ;
  métastable au-delà. Confirme causalement et quantitativement la bistabilité d'EDR-164 et sa borne r·P.
- **Levier in-world (axe 3) affiné et QUANTIFIÉ** : un warm-start COURT (~50 ép à coût faible) suffit à
  rescaper la rétention d'un moyen coûteux, tant que c < r·P (coût du moyen < récompense × fiabilité du
  binding). Pratique : garantir c/r·P < 1 in-world OU curriculum bref. Ferme la trilogie rétention
  (162→164→167→168).
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-168`. Aucun nouveau code (sweeps de `warmstart_episodes`, 167).

## Caveats

1. c_hi≈r·P inféré (stable à 600ép jusqu'à ~0.9 + métastabilité démontrée à 1.1) ; la valeur exacte du
   seuil de convergence n'est pas localisée finement (bornage — un sweep long par coût le préciserait).
2. Profondeur ~50 ép à c=0.2 ; le minimum pourrait varier avec c (non sweepé en 2D).
3. 2 seeds (EXP1/EXP2), 1 seed (métastabilité) ; le ROBUSTE = les DEUX seuils de nature distincte + la
   métastabilité au-dessus de r·P, pas les valeurs absolues. Substrat dégénéré, proxy 2-pas.
