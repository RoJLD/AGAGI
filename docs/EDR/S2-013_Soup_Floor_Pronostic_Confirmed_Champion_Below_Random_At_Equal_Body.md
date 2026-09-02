---
id: EDR-S2-013
type: EDR
title: "Pronostic du plancher soup CONFIRMÉ — la ligne soup de S2-002 est illisible, la politique du champion vaut moins que le hasard à corps égal"
status: active
verdict: SOUP_FLOOR_PRONOSTIC_CONFIRMED
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
extends: [EDR-S2-002]
---

## Question — un pronostic gravé AVANT le run

Au câblage des bornes E14 (2026-09-02), la table `PLANCHER_NOPERC` (clones du champion,
`max(zero_obs, random_action)`, seed 3026) a donné **soup = 32.0**, alors que l'annotation de
[[EDR-S2-002]] situe la médiane intacte à ~22-29 (S2-003/S2-012, même config). Pronostic scellé
**avant** le run (`docs/preregistrations/S2-FLOOR-PRONOSTIC.json`) : au régime gravé, l'instrument
doit rendre la ligne soup DÉGÉNÉRÉE. C'est le premier test en conditions réelles du câblage E14 :
un plancher qui ne bascule jamais rien serait un plancher décoratif.

## Méthode

`tools/s2_floor_pronostic_run.py` (sous bail kuzu) : `run_ablation_map` au régime GRAVÉ de S2-002
(12 agents, 200 ticks, K=12, seed 2026), planchers consommés via `_floor_for` (régime-gate E8),
absolus publiés (`intact_median`, `floor` — défaut AUDIT-001 fermé sur cette sonde). Règle de
lecture continue : l'écart intact−plancher se rapporte pour les 5 mondes, jamais de suppression.

## Résultats

| monde | intact | plancher | écart | within | verdict |
|---|---|---|---|---|---|
| **soup** | **29.25** | **32.00** | **−2.75** | 1.00 | **INCONCLUSIVE_DEGENERATE** |
| stoneage | 27.50 | 24.00 | +3.50 | 0.99 | PERCEPTION_DECOY |
| agricultural | 31.25 | 25.25 | +6.00 | 1.19 | PERCEPTION_DECOY |
| industrial | 27.50 | 24.00 | +3.50 | 0.99 | PERCEPTION_DECOY |
| famine | 27.50 | 21.75 | +5.75 | 1.07 | PERCEPTION_DECOY |

Mondes dégénérés : **1/5** (soup) — branche scellée « soup_sous_son_plancher ».

## Verdict

1. **La ligne soup de [[EDR-S2-002]] est ILLISIBLE à ce régime** : son argument de lisibilité
   (« intact ~22-29, loin du plancher 9.0 de WARM-010 ») reposait sur un plancher d'agents FRAIS ;
   contre le plancher clones-du-champion (32.0), le bras intact est DESSOUS. Le `within ≈ 1.00` de
   soup peut être fabriqué par la borne — annoté sur le record.
2. **Fait mesuré, non prévu par aucun modèle antérieur** : la politique du champion sur soup vaut
   **moins que le hasard à corps égal** (29.25 vs 32.0 pour ses propres clones sans perception ou à
   action aléatoire). La perception intégrée ne rapporte rien sur soup — et coûte peut-être.
3. **Les 4 autres mondes tiennent AU-DESSUS de leur plancher** (+3.50 à +6.00) : leurs lignes
   PERCEPTION_DECOY sont désormais adossées à des bornes MESURÉES, plus au 9.0 hérité — le verdict
   central de S2-002 (désaccord between/within) **sort renforcé** là où il reste lisible.

## Portée (hedges)

* L'écart soup (−2.75 ticks) est **petit et inter-seed** (plancher mesuré à seed 3026, run à seed
  2026) : « moins que le hasard » est une estimation ponctuelle, pas un effet élevé — un appariement
  par seed du plancher et de l'intact le trancherait. La règle scellée avait pré-engagé la lecture
  quel que soit ce raffinement.
* `INCONCLUSIVE_DEGENERATE` est le libellé de l'instrument (`ablation_verdict`, garde de borne) —
  il dit « illisible ici », pas « pas de demande ».
* stoneage et industrial restent la même simulation comptée deux fois ([[EDR-S2-012]]) : les
  « 4 mondes au-dessus » en valent au plus 3 indépendants.
* Régime unique (12 agents/200 ticks) — hors de ce point, `_floor_for` rend None par construction.

Converge [[EDR-S2-002]], [[EDR-S2-003]], [[EDR-S2-012]], [[EDR-AUDIT-001]] (publier les absolus),
[[EDR-WARM-010]] (le plancher d'agents frais sous-gardait).
