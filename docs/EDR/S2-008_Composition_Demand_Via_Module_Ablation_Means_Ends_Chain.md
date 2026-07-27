---
id: EDR-S2-008
type: EDR
title: "Demand-marker par ablation de MODULE : la COMPOSITION means→ends (G2) — la recette couvre input ET calcul"
status: active
gate: G2
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
S2-007 a instrumenté l'anticipation (G4) par ablation de MODULE. Cet EDR réalise le 2e jalon de l'arc
module-ablation sur le CŒUR du projet : la COMPOSITION means→ends (G2, la ligne binding/COS). La recette
générale (S2-006) tient-elle pour la composition ?

## Méthode
`tools/composition_demand_world_probe.py` (pur numpy, standalone — NE touche PAS le code biosphère COS).
Mini-sim survie : CORPS (réflexe a=0 → +body_gain) + COMPOSITION (chaîne 2-étapes : stage 0 = MOYEN
`means_t` non-récompensé, révélé UNIQUEMENT par le module de plan → passe stage 1 ; stage 1 = FIN (action
END fixe) → +cog_gain énergie). Le moyen ne paie pas ; seul le chaînage complet paie (craft-or-starve).
Module INTACT : plan = one-hot(means_t) au stage 0. **Ablation de MODULE** : plan→0 → agent MYOPE (le moyen
a 0 récompense immédiate et plus d'info) → reste bloqué stage 0 → ne craft jamais → meurt (corps
insuffisant). Le plan ne porte QUE le moyen (la FIN fixe est apprenable de l'obs) → évite le faux-positif
de redondance (cf. S2-005). cog_gain=3.0 > 2·metab (chaîne 2-ticks nette survivable). Grille
(corps × chaîne × devise), 8 seeds, K=5, ticks=300. Contrôle chain_len=1 (fin directe, pas de moyen) →
plan vide → ablation inerte.

## Résultats

| cellule | ratio | verdict |
|---|---|---|
| corps SUFFISANT (1.2) + chaîne2 + énergie | 1.00 | SURVIVAL_NEUTRAL |
| **corps INSUFFISANT (0.5) + chaîne2 + énergie** | **8.45** | **SURVIVAL_COMPOSITION_SENSITIVE** |
| corps INSUFFISANT (0.5) + chaîne1 (pas de moyen) + énergie | 1.00 | SURVIVAL_NEUTRAL |
| corps INSUFFISANT (0.5) + chaîne2 + devise séparée | 1.00 | SURVIVAL_NEUTRAL |

Une SEULE cellule est composition-SENSIBLE : corps INSUFFISANT + chaîne ≥2 + énergie (effondrement ~8×).

## Verdict
**`COMPOSITION_DEMAND_VIA_MODULE_ABLATION`** — la survie in-world exige la COMPOSITION (chaîner un moyen
non-récompensé vers une fin) SSI (1) corps INSUFFISANT, (2) chaîne ≥2 (un MOYEN non-récompensé est
requis — l'analogue « demande structurée » de S2-006 pour le chaînage), (3) devise de survie. **La recette
générale (S2-006) tient donc sur les CINQ capacités testées** : perception + mémoire (ablation d'INPUT,
S2-004/005) ET anticipation + composition (ablation de MODULE, S2-007/008). L'arc module-ablation est
complet pour les deux capacités-calcul.

## Portée & limites
Sim faithful au mécanisme means→ends (moyen non-payé + fin payée), pas la biosphère COS (dont ce probe ne
touche AUCUN fichier). Teste la DEMANDE de composition (la tâche exige-t-elle un chaînage), pas
l'APPRENABILITÉ du binding (couverte par la ligne COS/EDR-200 : gate + tick-return). Le PORTAGE biosphère
de la recette (monde à corps insuffisant + canal cognitif/chaîné payé en énergie) reste le chantier
suivant. Converge S2-004..007, REF-DEMAND-MARKER, la ligne binding/COS ([[coop-competence-is-population-property]],
[[decisive-substrate-thesis-test]]).
