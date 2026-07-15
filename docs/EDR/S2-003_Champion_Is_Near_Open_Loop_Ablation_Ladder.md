---
id: EDR-S2-003
type: EDR
title: "Le champion HoF est QUASI OPEN-LOOP : l'échelle d'ablation localise la compétence hors de la perception"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-002 a montré `INWORLD_PERCEPTION_DECOY` sur 5 mondes (`within ≈ 1.0` : permuter la perception du
champion ne dégrade pas sa survie), mais l'interprétation restait ambiguë : **(a)** le champion IGNORE
son entrée (open-loop), ou **(b)** il est closed-loop mais ROBUSTE à une décorrélation in-distribution.
Trancher (a) vs (b) interroge directement G0 (« le monde exige-t-il l'intelligence ? »).

## Méthode
`tools/s2_openloop_probe.py` : même champion HoF, échelle d'ablations within-subject de sévérité
CROISSANTE, toutes world-agnostic (aucun mapping de colonnes), via le seam `batch_model_cls` de
`s2_demand.run_condition` (importé, non modifié) :

| barreau | obs vue par la politique | classe |
|---|---|---|
| intact | vraie | (moteur normal) |
| permuted | obs d'un pair (dérangement) | `PerceptionAblatedMamba` (S2-002) |
| noise | bruit gaussien à échelle appariée | `NoiseObsMamba` |
| zero | vecteur nul (aucune information) | `ZeroObsMamba` |

Ratio par barreau = `ablation_verdict(intact.era_survival, barreau.era_survival)["ratio"]` (apparié par
ère). 3 mondes diversifiés, seed=2026, K=12 ères, agents=12, ticks=200. Verdict monde : `OPEN_LOOP` si
les 3 ratios ≤ 1.3 ; `INPUT_SENSITIVE` si un ratio ≥ 1.5 ; sinon `MIXED`.

## Résultats

| monde | intact_med | permuted | noise | zero | verdict |
|---|---|---|---|---|---|
| soup | 29.2 | 1.00 | 0.98 | 1.07 | OPEN_LOOP |
| stoneage | 27.5 | 0.99 | 1.22 | 1.28 | OPEN_LOOP |
| famine | 27.5 | 1.07 | 1.26 | 1.34 | MIXED |

**Aucun barreau, sur aucun monde, n'atteint le seuil d'effondrement (1.5×) — même l'obs NULLE.** Un
gradient monotone faible existe (permuted < noise < zero) et croît avec la dureté du monde (famine passe
en MIXED, `zero`=1.34 > plafond leurre 1.3).

## Verdict
**`CHAMPION_IS_NEAR_OPEN_LOOP`** — la compétence de survie du champion vit dans sa distribution d'actions
INPUT-INDÉPENDANTE, pas dans la lecture du monde. L'ambiguïté S2-002 est levée vers la lecture (a) :
priver le champion de TOUTE information (obs nulle) ne l'effondre pas. Le champion extrait un *filet*
d'information (gradient faible, sous-seuil), donc « quasi » et non « strictement » open-loop.

Conséquence pour G0 : le verdict between de `s2_demand` (« le monde exige l'intelligence », champion
4.7-5.2× le réflexe) **confond « survit bien » et « utilise sa perception »**. Le ladder within-subject
montre que, pour CE champion dans ces mondes (benchmark_mode, nuit OFF, scaffolds OFF), la survie n'est
pas médiée par l'entrée. Corrobore le fil « in-world NEUTRE » et la thèse substrat/crédit : le régime de
crédit a récompensé une politique open-loop ; ces mondes n'exigent pas de boucle perception→action au
niveau où opère le champion.

## Portée & limites
- Claim sur le champion HoF COURANT, pas une preuve qu'aucun agent ne pourrait exploiter la perception :
  l'évolution a TROUVÉ une stratégie open-loop, elle ne prouve pas qu'elle soit forcée.
- « Near » open-loop : le gradient monotone montre un usage résiduel, plus net en monde dur (famine).
- Ablation du flux égocentrique COMPLET (perception + proprioception) ; l'affinage canal-par-canal reste
  un follow-up. Corroborant |W| indisponible (poids HoF non exposés).
- 3 mondes (soup/stoneage/famine) ; S2-002 couvrait les 5 avec le même signal `within ≈ 1.0`, donc le
  ladder sur un sous-ensemble diversifié est représentatif.

## Suite
Reco G0 : le témoin de « le monde exige l'intelligence » doit être within-subject (ce ladder), pas
between. Pour rendre G0 non-trivial, câbler une DEMANDE perceptive survivable (tâche où l'obs porte
l'action nourricière/le danger) puis re-mesurer le ladder — si le champion reste open-loop là, le verrou
est le régime de crédit, pas le monde. Converge avec `REF-DEMAND-MARKER`, S2-001, S2-002.
