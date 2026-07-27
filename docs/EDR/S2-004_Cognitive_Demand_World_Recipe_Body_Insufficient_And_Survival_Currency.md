---
id: EDR-S2-004
type: EDR
title: "Recette d'un monde in-world à demande cognitive : corps INSUFFISANT ET cognition payée en devise de survie"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
corrected_by: [EDR-AUDIT-001]
---

> ⚠️ **CONDITIONS DE NÉCESSITÉ CORRIGÉES le 2026-07-21 — [[EDR-AUDIT-001]].**
> **Ce qui TIENT** : la cellule POSITIVE (corps INSUFFISANT + énergie, ratio 10.71, `|W|obs = 0.931`)
> est un contrôle positif réellement exécuté, avec un W authentiquement entraîné. La **suffisance** des
> conditions est établie.
> **Ce qui NE TIENT PAS** : les 3 cellules NULLES sont des **no-op de construction**, pas des mesures.
> `fit_policy` part de `W = zeros` et n'accepte qu'en `sc > best` STRICT ; quand `score(W=0)` atteint
> déjà le cap, **W ne quitte jamais son initialisation** — mesuré `|W| = 0.0000` exact dans 3 cellules
> sur 4. Avec `W = 0`, `argmax(0·o) = 0` quelle que soit l'obs : la politique est CONSTANTE, ablater
> l'obs est un no-op littéral, et le `ratio 1.00` est une **identité**.
> **Le corroborant est void** : « `|W|obs = 0.000` EXACT partout ailleurs », présenté comme second
> témoin indépendant, est **le zéro de départ** — l'optimiseur n'a jamais accepté un pas. La conclusion
> paraissait doublement étayée ; les deux témoins sortaient du même no-op.

## Question
S2-003 (+ s2-cognition-body sur main) : la survie in-world est perception-NEUTRE / corps-driven — la
survie ET la fitness n'ont aucun contenu cognitif, donc tout test in-world reste NEUTRE par construction.
**Contrepartie constructive** : à quelles CONDITIONS un objectif de survie in-world récompense-t-il la
cognition (survie perception-SENSIBLE), au lieu d'être court-circuité par le corps ?

## Méthode
`tools/cognitive_demand_world_probe.py` (pur numpy, standalone). Mini-sim survie combinant :
- **CORPS** : action-réflexe fixe (a=0) → +body_gain, obs-indépendante (le phénotype métabolique).
- **COGNITION** : action nourricière qui VARIE chaque tick, révélée par l'obs → +cog_gain SSI on lit l'obs.
Métabolisme draine `metab`=1.0/tick. Politique entraînée (hill-climb) à MAXIMISER la survie ; témoin =
échelle d'ablation demand-marker (vrai/permuté/bruit/zéro) → verdict SURVIE. Grille 2×2 : régime du corps
(SUFFISANT body_gain=1.2>metab, survit seul / INSUFFISANT 0.5<metab, réflexe seul meurt) × devise de la
cognition (`energy`=devise de survie / `separate`=autre devise, ex. points/fitness). cog_gain=2.0>metab.
8 seeds, K=5, ticks=300.

## Résultats

| cellule | permuted | noise | zero | \|W\|obs | verdict |
|---|---|---|---|---|---|
| corps SUFFISANT (1.2) + énergie | 1.00 | 1.00 | 1.00 | 0.000 | SURVIVAL_NEUTRAL |
| **corps INSUFFISANT (0.5) + énergie** | **10.71** | **9.84** | **10.91** | **0.931** | **SURVIVAL_SENSITIVE** |
| corps INSUFFISANT (0.5) + devise séparée | 1.00 | 1.00 | 1.00 | 0.000 | SURVIVAL_NEUTRAL |
| corps SUFFISANT (1.2) + devise séparée | 1.00 | 1.00 | 1.00 | 0.000 | SURVIVAL_NEUTRAL |

**Une SEULE cellule est SENSIBLE** : corps INSUFFISANT + énergie. Effondrement ~10× jusqu'à l'obs NULLE,
et le corroborant |W|obs = 0.931 (la politique pèse l'obs) UNIQUEMENT là ; 0.000 EXACT partout ailleurs.

## Verdict
**`COGNITIVE_DEMAND_REQUIRES_TWO_CONDITIONS`** — un objectif de survie in-world n'exige la cognition QUE si
DEUX conditions nécessaires tiennent ensemble :
1. **le CORPS est INSUFFISANT seul** (`body_gain < metab`) — sinon la survie PLAFONNE sur le corps et
   l'obs est un leurre (NEUTRE) ; c'est exactement le mécanisme de S2-003 / de la biosphère (le champion
   survit par le corps).
2. **le succès cognitif paie dans la DEVISE SÉLECTIONNÉE** (énergie de survie), pas une devise séparée —
   une cognition payée en fitness/points (devise séparée) laisse la survie NEUTRE quelle que soit la
   magnitude (reproduit « la fitness est corps » de s2-cognition-body).

## Portée & limites
- Existence-proof + recette de DESIGN, pas une modification de la biosphère (nouveau monde in-world =
  chantier séparé, // territoire mondes). Le sim est fidèle au MÉCANISME (corps métabolique + canal
  cognitif obs-déterminé), pas à la richesse de la biosphère.
- « INSUFFISANT » suppose que le canal cognitif est le SEUL recours survivable (pas d'autre action-corps
  suffisante) — la biosphère devra retirer les shortcuts corporels (cf. EDR-090 « pas de premier barreau
  survivable » : durcir la létalité SANS canal cognitif = mort partout ; ici on APPAIRE dureté + canal).

## Suite (portage in-world)
Câbler un monde biosphère où (1) le métabolisme rend le réflexe insuffisant ET (2) une action nourricière
obs-déterminée paie EN ÉNERGIE (pas en life_score). Alors la survie devient un objectif à contenu cognitif,
et G1-G4 in-world deviennent mesurables (l'ablation-perception du champion y effondrerait la survie).
Converge S2-001/002/003, REF-DEMAND-MARKER, et l'analyse cognition-vs-corps de [[s2-world-demand-thread]].
