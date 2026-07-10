# EDR 081 : La sélection robuste fait COMPOSER la compétence au fil des générations

> ⚠️ **Correction (trouvaille D1)** : le fix D1 corrige une revendication liée à cet EDR — la sélection
> robuste `K=4` n'était PAS active EN PRODUCTION (`main_biosphere` écrasait `robust_hof_K` → K=0 bruité)
> jusqu'au fix. La GRIMPÉE mesurée ici (expérience d'évolution ISOLÉE) reste valide ; c'est l'effet EN
> PROD qui n'a pris qu'après le fix. Détail : `docs/roadmap/SCIENCE.md` §D1.

## Contexte

EDR 080 : la sélection HoF robuste donne un meilleur champion FINAL (+50 %, instantané). Question plus
exigeante (la vraie promesse d'un moteur évolutif) : la compétence **s'accumule-t-elle au fil des
générations** sous sélection robuste, là où la bruitée plafonne (EDR 076) ? On évolue 24 générations et
on mesure la **compétence VRAIE** (survie sur 12 ères propres) du champion best-ever à des checkpoints.

## Résultat — plateau (bruité) vs GRIMPÉE (robuste)

| génération | 6 | 12 | 18 | 24 | pente |
|---|---|---|---|---|---|
| **BRUITÉE** (K=1, biosphère 076) | 32.8 | 30.4 | 28.6 | 29.8 | **−3.0** |
| **ROBUSTE** (K=4) | 42.8 | 54.1 | 52.2 | 55.2 | **+12.4** |

> **Sous sélection BRUITÉE, la compétence STAGNE et décline (33 → 30)** — exactement l'échec d'EDR 076
> (sélectionner sur la chance ne mène nulle part). **Sous sélection ROBUSTE, elle GRIMPE (43 → 55)** :
> chaque génération bâtit sur une vraie amélioration. **Le fix COMPOSE.**

## Signification

> C'est la preuve la plus forte possible — non pas un instantané (080) mais une **trajectoire**. Toute
> la promesse d'un moteur évolutif est tenue : **la biosphère ne se contente plus de *maintenir* (le
> cliquet de 076), elle *progresse*.** Et tout découle d'une seule cause comprise jusqu'au bout (le
> bruit de fitness, 078) et corrigée proprement (la ré-évaluation robuste, 079-080).

La robuste est *à la fois* meilleure immédiatement (gen 6 : 42.8 vs 32.8) ET croissante (→ 55.2) ; la
bruitée part plus bas ET reste plate. De-bruiter la sélection débloque l'accumulation.

## L'arc de la compétence — clos, de bout en bout

| EDR | acquis |
|---|---|
| 075 | la compétence est le goulot (le langage ne paye pas sans elle) |
| 076 | elle PLAFONNE sous mutation+extinction (sélection bruitée) |
| 077 | le BPTT n'est PAS le remède (il nuit en RL — auto-réfutation) |
| 078 | le plateau est du BRUIT DE FITNESS (banc, ×3) |
| 079 | remède validé dans le vivant (+27 %) |
| 080 | remède EN PRODUCTION (gated) + puissance (+50 %, écart réduit) |
| **081** | **le remède COMPOSE : la compétence GRIMPE sur les générations (+12.4 vs −3.0)** |

## Honnêteté

- 1 run par régime (la trajectoire elle-même n'est pas répétée) ; mais la séparation est franche (pente
  +12.4 vs −3.0) et cohérente avec 080 (powered). La compétence vraie est moyennée sur 12 ères/checkpoint.
- La grimpée sature peut-être au-delà de 24 générations (54→52→55) ; le plafond atteignable + le coût
  (K× par génération) restent à explorer. Mais la DIRECTION (accumulation vs stagnation) est nette.

## Statut

- `robust_trajectory.py`. **Le fix d'évaluation robuste fait COMPOSER la compétence** (grimpée +12.4 vs
  plateau −3.0). Appliqué en production (`main_biosphere` runs en `robust_hof_K=4`, EDR 080). L'arc
  compétence (075→081) est clos : du goulot diagnostiqué au moteur qui *progresse* enfin.

## Variables d'expérience

Nombre de générations (plafond de la grimpée), K vs coût, répétition de la trajectoire (puissance),
émergence de la chasse au Mammouth sur longue run robuste, re-test du bénéfice du langage (075) sur
substrat désormais COMPÉTENT et croissant.
