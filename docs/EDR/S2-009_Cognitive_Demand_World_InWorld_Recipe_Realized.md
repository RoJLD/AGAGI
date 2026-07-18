---
id: EDR-S2-009
type: EDR
title: "La recette de demande cognitive RÉALISÉE in-world : la survie stoneage devient perception-SENSIBLE (flip S2-003)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-006 donnait la recette (corps insuffisant + demande structurée + devise de survie) en SIM. Tient-elle
DANS la biosphère ? Peut-on rendre la survie stoneage causalement perceptive — flip du NEUTRE in-world de
S2-003 (où l'ablation-perception du champion n'effondrait PAS la survie) ?

## Méthode
Flag `cognitive_demand` sur stoneage (`config.py` + `world_1_stoneage.py`, guardé défaut OFF, strictement
non-régressif) : chaque agent reçoit un signal 2-bits PAR-AGENT dans son obs (bit_a/bit_b) → sa direction
nourricière correcte ; s'y déplacer paie `cog_gain` en ÉNERGIE ; gains standard neutralisés au run
(`forage_payoff=0` + `base_metabolism` dur = corps insuffisant). Oracle lecteur-de-signal
(`tools/cognitive_demand_inworld.py`, `CognitiveOracleBatchModel`) intact vs ablé (obs dérangée =
`derange_rows`, within-subject), mode ON vs OFF ; verdict via `demand_marker.ablation_verdict` (n=12 ères).
Calibration retenue : `base_metabolism=0.75`, `cog_gain=12.0`, seed=2026, 12 agents, 200 ticks.

## Résultats

| mode | ratio (survie intact / ablé) | verdict |
|---|---|---|
| **ON** (cognitive_demand) | **21.05** | **PERCEPTION_DEMANDED** (n=12) |
| OFF | 1.00 | NEUTRAL (n=12) |

Pilote de calibration (n=2/ère, robustesse du régime) : intact→cap(200) / ablé→~9-14 sur metab∈{0.5,0.75,1.0}
avec cog apparié → ratio 16-25× ; l'oracle intact (100% hit vérifié) survit, l'ablé (signal d'un pair,
~75% de ratés) meurt en ~10 ticks.

## Verdict
**`COGNITIVE_DEMAND_RECIPE_REALIZED_INWORLD`** — la recette S2-006 rend la survie stoneage **causalement
perceptive IN-WORLD** : l'ablation-perception de l'oracle effondre la survie **21×** en mode ON, et reste
**inerte (ratio 1.0) en OFF**. **Flip décisif du NEUTRE de S2-003** : le monde n'exigeait pas la perception
par CONSTRUCTION D'OBJECTIF (survie = corps), pas par incapacité — en satisfaisant les 3 conditions
(corps insuffisant + demande structurée par-agent + devise de survie), il l'exige causalement. Le pont
proxy(sim S2-004→008)→in-world est franchi pour la recette constructive. G0 devient mesurable in-world :
un agent qui utilise sa perception survit, un agent privé de perception (within-subject) meurt.

## Finding méthodologique (root cause du run)
Un signal GLOBAL (identique à tous les agents) **défait l'ablation-par-permutation** (`derange_rows`) : la
permutation de lignes est un NO-OP sur un canal identique entre agents → l'agent ablé lit le même signal
correct → ratio 1.0 trompeur. **L'ablation within-subject doit cibler un canal PAR-AGENT** (chaque sujet a
sa propre perception) pour que la permutation décorrèle. Fix : signal par-agent (parallèle exact à S2-003,
où l'obs égocentrique du champion EST par-agent). Corollaire pour REF-DEMAND-MARKER : vérifier que le canal
ablaté est bien per-subject ; sinon utiliser une ablation de contenu (bruit/zéro du canal), pas de permutation.

## Portée & limites
- **Oracle = preuve que le MONDE exige la perception** (100% hit vérifié, ablation le prive → mort), PAS
  que le CRÉDIT in-world l'apprend (sonde intra-vie `use_torch_inworld` = suite, EDR addendum/Task 4).
- Flag guardé défaut OFF (non-régressif, tests 3/3 + non-régression 10/10). cog food = direction-signalée
  par-agent (proxy fidèle du mécanisme obs→action→énergie), pas une écologie riche.
- Régime « corps insuffisant » obtenu par `forage_payoff=0` + `base_metabolism` calibré ; revenus corporels
  résiduels (ver/trésor) négligeables à ce régime (l'ablé meurt ~10 ticks, l'intact cap).
Converge S2-004→008 (recette sim), S2-001/002/003 (le NEUTRE in-world qu'on inverse ici), REF-DEMAND-MARKER,
[[s2-world-demand-thread]], [[within-subject-demand-marker]].
