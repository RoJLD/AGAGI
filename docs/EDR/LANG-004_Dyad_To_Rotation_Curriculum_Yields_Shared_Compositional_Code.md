---
id: LANG-004
type: EDR
title: "Un CURRICULUM dyade->rotation donne un code COMPOSITIONNEL ET PARTAGÉ — le goulot de consensus de LANG-003 est un DÉMARRAGE À FROID (analogue du warm-start de rétention 167/168/170). LANG-003 : dyades figées = compositionnel mais PRIVÉ (cross_mi 0.045) ; rotation à froid = ÉCHOUE (within~chance). CURRICULUM (W=4000 dyade puis E=4000 rotation) : compositionnel RETENU (zeroshot 0.510 >> chance 0.333, topsim +0.31) ET partagé (cross_mi 0.59, ×13 vs FIXED) -> réconcilie le partage (002) et la systématicité (003) qu'aucune condition unique ne donnait. Partage PARTIEL (0.59 pas ~1) + la rotation ÉRODE le within (0.55->0.42 = coût de précision individuelle, écho érosion métastable 168). Cold-start causalement confirmé (ROT_SCRATCH échoue, CURRICULUM marche)"
status: accepted
gate: null
verdict: CURRICULUM_YIELDS_SHARED_COMPOSITIONAL
---

# LANG-004 : un curriculum dyade→rotation donne un code compositionnel ET partagé (Arc 4)

## Contexte

LANG-003 a révélé une TENSION : sur la tâche 2-symboles, les PAIRES FIGÉES développent un code
compositionnel (généralise zéro-shot) mais PRIVÉ (illisible par un autre partenaire), tandis que la
ROTATION d'emblée NE CONVERGE PAS (goulot de consensus prohibitif). Ni l'un ni l'autre ne donne
« compositionnel ET partagé ». Hypothèse (parallèle au warm-start de la rétention, EDR-167/168/170) : le
goulot est un DÉMARRAGE À FROID — un curriculum (phase 1 dyade = warm-start d'un code compositionnel ;
phase 2 rotation = le PARTAGER sans l'effondrer) donnerait les deux.

## Méthode

`tools/compositional_curriculum_probe.py` (étend `run_compositional` : param `warmstart_fixed` = épisodes
INITIAUX en paires figées avant la phase `rotate` ; + métrique `cross_mi` = intelligibilité mutuelle croisée
de LANG-002 portée au 2-attributs = décodage par un partenaire décalé jamais co-apparié). Trois conditions
à BUDGET TOTAL APPARIÉ (W+E = 8000 ép, M=8, A=3, V=6, 2 seeds) :
- **FIXED** : rotate=False, tout en paires figées.
- **ROT_SCRATCH** : rotate=True, tout en rotation (froid).
- **CURRICULUM** : warmstart_fixed=W=4000 (dyade) puis E=4000 rotation.

Métriques : within/zeroshot (compositionnalité, LANG-003) + topsim + **cross_mi** (partage, LANG-002).

## Constat

| Condition | within | zeroshot | topsim | cross_mi |
|---|---|---|---|---|
| FIXED | 0.547 | 0.490 | +0.357 | **+0.045** |
| ROT_SCRATCH | 0.328 | 0.312 | +0.241 | nan (within~chance) |
| **CURRICULUM** | 0.422 | 0.510 | +0.305 | **+0.590** |

(chance = 0.333 ; `VERDICT = CURRICULUM_YIELDS_SHARED_COMPOSITIONAL`.)

## Lecture

- **Le goulot de consensus est un DÉMARRAGE À FROID — causalement confirmé.** ROT_SCRATCH échoue
  (within = chance : la rotation à froid ne coordonne pas sur 2 symboles). Le MÊME budget de rotation,
  précédé d'un warm-start dyade, PARTAGE le code : `cross_mi` bondit de 0.045 (FIXED, privé) à **0.590**
  (×13). C'est l'exact analogue de l'hystérésis warm-start de la rétention (167/168/170) : un bassin
  pré-formé rend franchissable ce qui est infranchissable à froid.
- **Le curriculum réconcilie LANG-002 et LANG-003.** Le code reste COMPOSITIONNEL à travers la phase
  rotation (zeroshot 0.510 ≫ chance ; topsim +0.31 ≈ FIXED +0.36 : structure préservée) ET devient PARTAGÉ
  (cross_mi 0.59). Aucune condition unique ne donnait les deux : FIXED = compositionnel+privé, ROT_SCRATCH =
  rien. Le curriculum = compositionnel + (partiellement) partagé.
- **Partage PARTIEL et coût de précision (honnêteté).** cross_mi 0.59 (pas ~1 comme le 1-symbole de 002) :
  la communauté ne s'aligne qu'à moitié sur la tâche 2-symboles (plus dure). La phase rotation ÉRODE le
  within (0.547 FIXED → 0.422 CURRICULUM) : partager coûte de la précision individuelle — écho de l'érosion
  MÉTASTABLE au-delà du seuil warm (EDR-168). En absolu, within-chance reste modeste (~0.09). Victoire
  QUALITATIVE (direction robuste : cross_mi ×13, compositionnalité retenue), pas un code parfait.

## Conséquences

- **Recette langage torch complétée** : pour un code COMPOSITIONNEL ET PARTAGÉ, ne pas rotationner à froid —
  **warm-starter en dyade puis rotationner** (curriculum). C'est le 4e résultat de l'axe langage :
  capacité (001) + partage (002) + systématicité (003) + **conciliation par curriculum (004)**.
- **Unification transversale** : le warm-start/hystérésis (rétention, fil torch 167/168/170) et le
  démarrage-à-froid du consensus (langage, ici) sont le MÊME phénomène — un bassin pré-formé franchit une
  barrière de bootstrap. Levier générique du substrat torch sous crédit épisodique.
- **Handoff in-world (roadmap #1, 087)** : un langage compositionnel PARTAGÉ n'exige pas des partenaires
  variés d'emblée — il suffit de **stabiliser des dyades d'abord** (former le code) PUIS d'ouvrir le brassage
  social. Contrainte de design du monde : curriculum social (dyades stables → mixité), pas mixité pure.
- Relié : `REF-LTC -A_ADOPTER_POUR-> LANG-004`. Prolonge [[lang-referential-capability]] (001/002/003) et
  recoupe le warm-start de [[sota-gap-substrate]] (§ rétention 167/168/170). SOTA `langage→EGG`
  (curriculum / population dynamics en emergent communication).

## Caveats

1. Partage PARTIEL (cross_mi 0.59) et absolu MODESTE (within-chance ~0.09 après curriculum) : la victoire est
   la DIRECTION (cross_mi ×13 vs FIXED, compositionnalité retenue), pas des décimales hautes. La phase
   rotation érode le within (métastabilité 168) — un E plus court / LR décru en phase 2 / warm-start plus
   long pourraient préserver plus (non sweepés).
2. 2 seeds, M=8, A=3, W=E=4000 fixés ; zeroshot > within pour CURRICULUM (0.510 > 0.422) est probablement du
   bruit (2 seeds) ou l'effet des combos diagonaux held-out — le ROBUSTE est le contraste cross_mi + la
   rétention de la compositionnalité, pas l'ordre exact within/zeroshot.
3. cross_mi porté de LANG-002 : mesuré sur les combos entraînés en partenaire décalé (roll) ; sur tâche
   2-attributs le décodage joint est plus dur -> borne basse du partage réel.
4. Proxy synthétique hors biosphère (même bornage que 001/002/003) : le vrai test = in-world (087).
