---
id: EDR-S2-008
type: EDR
title: "Demand-marker par ablation de MODULE : la COMPOSITION means→ends (G2) — la recette couvre input ET calcul"
status: active
gate: G2
tests: [SDR-G2]
adopts: [REF-DEMAND-MARKER]
corrected_by: [EDR-AUDIT-001]
---

> ⚠️ **LECTURE DES CELLULES DE CONTRÔLE CORRIGÉE le 2026-09-14 — [[EDR-AUDIT-001]], étendu (P2.51).**
> **Ce qui TIENT** : la cellule POSITIVE (corps INSUFFISANT + chaîne2 + énergie, ratio **8.45**,
> `SURVIVAL_COMPOSITION_SENSITIVE`) — une demande de composition réellement mesurée, à 8 seeds.
> **Ce qui NE TIENT PAS** : les trois cellules publiées `SURVIVAL_NEUTRAL` ne sont pas neutres, elles
> sont **INDÉCIDABLES**. Même mécanisme que S2-004 (AUDIT-001) : `fit_policy` part de `W = np.zeros`
> et n'accepte qu'en `sc > best` STRICT (`composition_demand_world_probe.py:103,114`) ; quand le
> score de départ atteint déjà le cap, W ne quitte jamais son initialisation, la politique est
> CONSTANTE, et ablater le module est un no-op littéral — les deux bras sont **identiques point par
> point**. Mesuré le 2026-09-09 : l'instrument (`ablation_verdict`, garde de dégénérescence armée le
> 2026-07-21) rend `INDETERMINE_DEGENERATE` sur ces cellules, et
> `tests/test_composition_demand_world_probe.py` le gèle (deux cas, branchés sur la CI).
> **Conséquence sur la lecture** : « le contrôle est neutre, donc la demande est SPÉCIFIQUE à la
> chaîne à 2 pas » n'est pas établi par ces cellules. Ce qu'elles disent : *aucun effondrement n'y
> est détectable*, ce qui est compatible avec « pas de demande » ET avec « l'ablation ne s'est pas
> appliquée ». La spécificité de la demande de composition reste **À ÉTABLIR** par une cellule de
> contrôle dont le W est entraîné (`|W| > 0` mesuré), comme S2-005 en possède une (rappel PRÉSENT,
> `|W| = 0.909`). Le tableau ci-dessous est conservé tel que publié.

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
