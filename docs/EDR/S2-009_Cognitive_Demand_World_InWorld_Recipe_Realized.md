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

> ⚠️ **CONTRÔLE NÉGATIF CORRIGÉ le 2026-07-21 — [[EDR-AUDIT-001]] (calibration P2.10).** Ce record ne
> publiait que des **ratios, aucune valeur absolue**. Re-mesuré au régime publié (metab=0.75, cog=12.0,
> seed 2026, K=12) :
>
> | mode | intact | ablé | ratio | statut |
> |---|---|---|---|---|
> | **ON** | **200.0** | **9.0** | **22.22** | ✅ **CONFIRMÉ** — `X_DEMANDED`, amplitude réelle, non dégénéré |
> | **OFF** | **7.0** | **7.0** | 1.00 | ❌ **DÉGÉNÉRÉ** — bras **bit à bit identiques sur les 12 ères** |
>
> **Le bras ON tient, et c'est lui qui porte le verdict.** Mais la ligne OFF est un **no-op LITTÉRAL** :
> en mode OFF, `forage_payoff = 0` et aucune nourriture cognitive → tout le monde meurt à ~7 ticks quoi
> qu'il fasse. Le ratio 1.00 ne montre donc pas « le marqueur reste inerte quand la perception ne paie
> pas », mais « le marqueur rend 1.00 quand la métrique est morte ». Un vrai contrôle négatif exige un
> monde où les agents **SURVIVENT** et où la perception ne paie pas.
>
> **Portée stricte** : la **spécificité du marqueur est établie AILLEURS**, par des bras où les agents
> vivent et le ratio vaut 1.0 — S2-001 (monde TRIVIAL), LANG-006 (MI 0.000), MEM-001. C'est **cette
> ligne** qui ne la démontre pas, pas la propriété. Le verdict `COGNITIVE_DEMAND_RECIPE_REALIZED_INWORLD`
> n'est pas remis en cause. `ablation_verdict` rendrait aujourd'hui `INCONCLUSIVE_DEGENERATE` sur OFF.

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

## Sonde crédit intra-vie (Task 4, bornée) — le monde EXIGE, le crédit N'APPREND PAS (à froid)
`tools/cognitive_demand_inworld.py::run_credit_probe` : cohorte FRAÎCHE `use_torch_inworld` (REINFORCE
in-world), mode cognitive_demand (corps insuffisant STRUCTUREL — ver/trésor/alignment gatés), 6 ères,
metab=0.75/cog_gain=12. **Résultat : survie médiane PLATE ~7-8 sur les 6 ères** (torch_pop actif) = le
PLANCHER no-perception (≈ l'oracle ablé à ~9), TRÈS loin de l'oracle intact (200). **Le crédit in-world
n'apprend PAS à utiliser la perception à froid.** Sépare nettement les deux verrous : le MONDE est résolu
(la recette le rend perceptif, oracle 200 vs 7) mais le CRÉDIT est le verrou restant. Corrobore directement
[[warm-start-transversal-law]] (le crédit ne bootstrappe pas à froid) et [[decisive-substrate-thesis-test]]
(verrou = crédit, pas substrat/monde). ⚠️ BORNÉ : 6 ères, cohorte fixe, SANS warm-start/curriculum — la loi
prédit qu'un bassin pré-formé franchirait le bootstrap ; à tester en suite (warm-start + run_credit_probe).

## Portée & limites
- **Oracle = preuve que le MONDE exige la perception** (100% hit vérifié, ablation le prive → mort) ; la
  sonde crédit ci-dessus montre que le CRÉDIT ne l'apprend pas à froid (verrou séparé, isolé).
- Flag guardé défaut OFF (non-régressif, tests 3/3 + non-régression 10/10). cog food = direction-signalée
  par-agent (proxy fidèle du mécanisme obs→action→énergie), pas une écologie riche.
- Régime « corps insuffisant » obtenu par `forage_payoff=0` + `base_metabolism` calibré ; revenus corporels
  résiduels (ver/trésor) négligeables à ce régime (l'ablé meurt ~10 ticks, l'intact cap).
Converge S2-004→008 (recette sim), S2-001/002/003 (le NEUTRE in-world qu'on inverse ici), REF-DEMAND-MARKER,
[[s2-world-demand-thread]], [[within-subject-demand-marker]].
