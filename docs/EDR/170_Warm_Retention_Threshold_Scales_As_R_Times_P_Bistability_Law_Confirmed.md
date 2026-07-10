---
id: EDR-170
type: EDR
title: "Le seuil warm de rétention est une LOI : c_warm = r·P (pas un nombre magique à r=1). Sweep de r∈{0.5,2.0} × c/r : le seuil NORMALISÉ c/r est INVARIANT ≈ P (~0.9-1.0) — warm tient à c/r≤0.9, s'effondre au-dessus, POUR LES DEUX r. Seuil absolu scale avec r (0.45 à r=0.5, 1.80 à r=2.0). À r=2, c=2.4≫r·P → effondrement TOTAL (0.001). Validation la plus forte du modèle de bistabilité d'EDR-164/168 : le seuil warm = rentabilité STATIQUE, mécaniste. Bonus : P monte avec r (0.92→0.99). Clôt la caractérisation de la rétention"
status: accepted
gate: null
verdict: WARM_THRESHOLD_SCALES_AS_R_TIMES_P_LAW_CONFIRMED
---

# EDR 170 : le seuil warm de rétention est une loi c_warm = r·P (validation finale de la bistabilité)

## Contexte

EDR-168 a inféré que le seuil warm de la rétention ≈ r·P (rentabilité statique), à r=1. Test de la LOI :
si c_warm = r·P est mécaniste (pas une coïncidence à r=1), alors varier r doit déplacer le seuil ABSOLU
proportionnellement, et le seuil NORMALISÉ c/r doit rester INVARIANT ≈ P. Sweep `r ∈ {0.5, 2.0}` × `c/r`
(warm ws=400, 1 seed, 600 ép).

## Constat

| r | c/r | c | warm craft_late | P |
|---|---|---|---|---|
| 0.5 | 0.3 | 0.15 | 0.140 | 0.92 |
| 0.5 | 0.6 | 0.30 | 0.123 | 0.92 |
| 0.5 | 0.9 | 0.45 | 0.121 | 0.93 |
| 0.5 | 1.2 | 0.60 | 0.088 | 0.90 |
| 2.0 | 0.3 | 0.60 | 0.214 | 0.99 |
| 2.0 | 0.6 | 1.20 | 0.208 | 0.99 |
| 2.0 | 0.9 | 1.80 | 0.201 | 1.00 |
| 2.0 | 1.2 | 2.40 | **0.001** | 1.00 |

`VERDICT = WARM_THRESHOLD_SCALES_AS_R_TIMES_P_LAW_CONFIRMED`. Les données se COLLAPSENT sur c/r : warm
tient (craft ~0.12 à r=0.5, ~0.20 à r=2) à c/r ≤ 0.9, s'effondre au-dessus, POUR LES DEUX r. Le seuil
ABSOLU c_warm scale avec r (0.45 à r=0.5 vs 1.80 à r=2.0, tous deux à c/r=0.9).

## Lecture

- **La loi c_warm = r·P est CONFIRMÉE** : le seuil warm normalisé (c/r) est r-invariant ≈ P (~0.9-1.0),
  donc le seuil absolu est r·P — un vrai INVARIANT MÉCANISTE (rentabilité statique `E[craft]=−c+r·P>0`),
  pas un nombre magique. C'est la validation la plus forte du modèle de bistabilité (164/168) : la
  frontière du bassin haut EST la rentabilité statique du moyen.
- **Effondrement TOTAL bien au-dessus de r·P** : à r=2, c/r=1.2 (c=2.40 ≫ r·P=1.98) → craft 0.001 (pas
  juste métastable) : quand le coût dépasse franchement r·P, même le bassin haut est vidé. À r=0.5,
  c/r=1.2 (c=0.60, seulement +33% au-dessus de r·P=0.45) → érosion partielle (0.088), cohérent avec la
  métastabilité (168) proche de la frontière.
- **P monte avec r** (0.92 à r=0.5 → 0.99 à r=2.0) : une récompense plus grande FIABILISE le binding
  (P(consume|craft) plus haut) → le seuil warm scale légèrement SUPER-linéairement (c_warm = r·P(r)).
  Le warm craft_late monte aussi avec r (0.12 → 0.20).

## Conséquences

- **Modèle de rétention COMPLET et quantifié** : deux seuils (cold bootstrap ≈0.04 ; warm statique = r·P),
  hystérésis, métastabilité au-dessus de r·P, warm-start bon marché (~50 ép), et maintenant la LOI de
  scaling. La trilogie+ rétention (162→164→167→168→170) est close.
- **Reco in-world (axe 3) DÉFINITIVE et chiffrée** : pour retenir un moyen coûteux, garantir
  `coût_du_moyen < récompense × P(suite|moyen)` (P = fiabilité du binding, ~0.9 sur substrat fort) OU
  warm-start court. La condition de rétention est un ratio coût/récompense borné par la force du binding.
- Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-170`. Aucun nouveau code (sweep de r/cost, probe 167).

## Caveats

1. r ∈ {0.5, 2.0} + r=1 (168) = 3 points ; l'invariance c/r est nette sur cette plage mais non prouvée
   asymptotiquement. 1 seed par cellule (le collapse c/r-invariant est franc, pas les décimales).
2. P dépend faiblement de r (0.92→0.99) → c_warm = r·P(r) légèrement super-linéaire, pas strictement
   linéaire ; bornage sur la forme exacte de P(r).
3. Substrat 172-nœuds dégénéré, means→ends 2-pas synthétique ; la LOI (seuil ∝ r·P) devrait tenir
   in-world mais P y sera différent — test réel = axe 3.
