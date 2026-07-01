---
id: EDR-126
type: EDR
title: Pipeline-complet en famine — la competence de survie cyclique EMERGE (leve le confond GA d'EDR-121), mais le stockage explicite reste REDONDANT (survie par buffer d'energie)
status: accepted
gate: G1
tests: [SDR-G1]
verdict: COMPETENCE_EMERGE_STOCKAGE_REDONDANT
---

# EDR 126 : Pipeline-complet en famine — la compétence émerge, le stockage explicite est redondant

## Contexte

EDR-121 avait laissé l'évolvabilité du stockage **INCONCLUSIVE**, avec deux confusions : (1) les champions
famine mouraient avant la famine (`delta_famine=0`), (2) le **GA léger** (`evolve_in_famine` : mono-champion,
mutation forte, pas d'élitisme HoF ni de fitness moyennée) subissait un **meltdown** — il érodait même un
warm-start compétent (stoneage 53-200 → 7-12 ticks). EDR-121 avait explicitement pré-scopé le test propre :
le **pipeline biosphère complet** (`main_biosphere` : élitisme HoF, reproduction in-world, reseed depuis le
HoF chaque ère). Cadrage (robla) : **HoF dédié** (chemin séparé, ne pas écraser le champion stoneage = le
contrôle) + **smoke d'abord** (le pipeline produit-il un champion famine compétent ?).

## Méthode

Seams livrés (commit 50d3e49, wiring 4/4 + non-régression 20/20) : `HALL_OF_FAME_PATH` configurable via
env-var `HOF_PATH` (`persistence.py`, non-breaking, 40+ appelants intacts) ; câblage `world_type=="famine"`
→ `FamineWorld` dans `main_biosphere` ; `MAX_ERAS` configurable. Run : `main_biosphere` sur famine,
**3 seeds (42, 43, 44)**, 60 ères, HoF dédié par seed (`data/hall_of_fame_famine_s*.pkl`). **HoF stoneage
global INTACT** vérifié (md5 `844ed69…` inchangé avant/après toute la campagne → isolation OK, contrôle
sauf). Champion extrait (`load_hall_of_fame()` → `entries[0].genome`) puis **ablation** via le probe
(`measure_genome`, cache ON vs OFF, cycle abondance 30 / famine 40, sweet-spot métab).

## Constat — compétence ÉMERGE (3/3), stockage explicite REDONDANT (3/3)

| seed | survie cache_ON | cache_OFF | delta (ON−OFF) | réserve à la transition | compétent (atteint la famine, tick 30) |
|---|---|---|---|---|---|
| 42 | 84 | 108 | **−24** | 0.00 | ✅ |
| 43 | 200 | 200 | **0** | 0.00 | ✅ (survit tout le run, censuré) |
| 44 | 38 | 41 | **−3** | 0.00 | ✅ |

1. **Compétence de survie cyclique ÉMERGE (3/3)** : tous les champions atteignent et **dépassent** la
   famine (84 / 200 / 38 ticks), contre 7-12 ticks pour le GA léger d'EDR-121. **→ Le confond meltdown-GA
   d'EDR-121 est LEVÉ** : l'érosion était bien l'artefact du GA léger, pas une limite du substrat. Avec
   l'élitisme HoF, la compétence est maintenue ET évoluée.
2. **Le stockage explicite n'émerge PAS (3/3)** : `réserve=0` partout (aucun agent ne banque), et le delta
   d'ablation est **≤ 0** (−24 / 0 / −3) → activer la banque ne rend JAMAIS service, elle est redondante
   voire un tax. La survie de famine est obtenue par **bufferisation d'énergie naturelle** (forager haut en
   abondance, planer sur la réserve d'énergie du moteur pendant la famine), PAS via le cache/banque construit.

## Lecture (nuancée)

- **La vraie question n'était pas « le substrat sait-il stocker ? » mais « sait-il survivre une famine
  cyclique ? » — et la réponse est OUI.** La gratification différée émerge au niveau **comportemental**
  (forager au-delà du besoin immédiat en abondance → dépenser en famine), mais via le **tank d'énergie
  naturel** (`energy_max`), pas via l'affordance explicite qu'on a ingénieurée. Le cache/banque est
  **redondant** parce que le buffer d'énergie suffit à franchir une famine de 40 ticks à ces paramètres.
- **Nuance importante au « verrou horizon »** (EDR 095/113/117) : le substrat PEUT évoluer une compétence
  temporelle/cyclique quand le pipeline d'évolution est adéquat (élitisme HoF). Ce n'est donc pas un verrou
  absolu de l'horizon ; c'est (a) une question d'algorithme d'évolution (le GA léger échouait), et (b) le
  fait que le monde n'EXIGE pas le stockage explicite tant que le buffer naturel suffit.

## Conséquences

- **Correctif d'EDR-121** : l'érosion/non-émergence y était **confondue par le GA léger**. Le pipeline
  complet le démontre : compétence maintenue (3/3). EDR-121 reste valide sur son périmètre (le GA léger ne
  suffit pas), mais son INCONCLUSIF est ici **résolu du côté compétence**.
- **Sur le stockage explicite** : il ne s'évalue proprement que si le monde l'EXIGE — c.-à-d. une famine
  assez dure pour que le buffer d'énergie naturel NE suffise PAS (`energy_max` insuffisant pour franchir la
  famine). À ces paramètres (cycle 30/40, sweet-spot), le buffer suffit → stockage redondant. **Prochaine
  calibration** : durcir la famine (famine plus longue / drain plus fort / `energy_max` plus bas) jusqu'à ce
  que la survie EXIGE une réserve au-delà du buffer, PUIS re-mesurer l'émergence du stockage.
- **`SDR-G1`** : signal **partiellement positif** — le substrat évolue une compétence de survie cyclique
  (temporelle). Piste north-star : mesurer si cette compétence **transfère** (G1 : famine→stoneage ou
  inverse), maintenant qu'on sait produire un champion famine compétent.

## Caveats (honnêteté)

1. **Métrique unique** (survie) ; le « stockage » est jugé via `réserve` + delta d'ablation, pas via une
   analyse comportementale fine du forage.
2. **Stockage redondant ≠ non-évolvable** : le buffer d'énergie suffit à ces paramètres → le monde n'exige
   pas le stockage explicite ; on ne peut donc PAS conclure « le substrat ne peut pas stocker », seulement
   « il n'en a pas besoin ici ». Une famine plus dure trancherait.
3. **n=3** (smoke-confirmatoire, pas fortement powered) ; robuste sur le pattern (3/3 compétents, 3/3
   réserve=0, 3/3 delta≤0) mais pas un verdict multi-seed lourd.
4. **Déterminisme** : `main_biosphere` ne `clear()` pas le `memory_retriever` entre ères (non-déterminisme
   résiduel) ; `EXPERIMENT_SEED` fixé par run. KuzuDB ambiant = corruption logging seule.
5. **Isolation HoF vérifiée** : HoF stoneage global md5 inchangé → aucune contamination du contrôle ni des
   runs d'autres sessions.
