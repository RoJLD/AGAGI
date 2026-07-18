# EDR 201 — Décomposition + robustesse du verdict COS [2] CRÉDIT-ATTRIBUÉ

## Contexte

EDR 200 CRAFT-OR-STARVE Phase B (mergé #155) a livré le verdict **[2] CRÉDIT-ATTRIBUÉ** : sur le MÊME réseau
12-cachés, seul le barreau L2 (crédit tick-return + curriculum warm-start) binde la composition craft→consume ;
L0 (crédit substep) et L1 (tick-return seul) échouent. → le verrou est le crédit/objectif, pas le substrat.

La revue finale opus (merge-gate) a laissé **deux caveats honnêtes, non-bloquants** :
1. **[2] regroupe DEUX interventions** (crédit-horizon tick-return + curriculum). Au config testé, le levier
   *décisif* semble le curriculum (dissociation entropie-vs-curriculum faite), mais la décomposition propre
   crédit-horizon × curriculum n'a pas été isolée.
2. **Portée** : le verdict catégorique repose sur N=4 seeds, un seul E0 (16.0), un seul jeu d'hyperparamètres.

EDR 201 ferme ces deux caveats, entièrement dans l'outil `tools/craft_or_starve_edr.py` (mergé, collision-safe,
pur numpy). But : passer de « résultat décisif » à « mécanisme précis + robuste ».

## Objectif

- **Composant 1 (caveat #1)** : décomposition factorielle 2×2 `crédit ∈ {substep, tick-return}` ×
  `curriculum ∈ {off, on}` sur le bras inesc, à E0=16 → isoler le levier DÉCISIF.
- **Composant 2 (caveat #2)** : sweep de robustesse du verdict ladder sur E0 ∈ {12, 16, 24, 32} → confirmer que
  [2] n'est pas config-fragile.

## Contraintes globales

- **Additif strict** : APPEND uniquement à `tools/craft_or_starve_edr.py` (+ `--edr201` dans `__main__`) et
  `tests/sandbox/test_craft_or_starve_edr.py`. Ne PAS éditer le code existant (Phase A, L0/L1/L2, ladder). AUCUN
  import de `src/`/`world_1_stoneage.py`/`backend_torch.py`. PUR NUMPY.
- **Réutilise** les primitifs Phase B : `NpReinforceLearner`, `NpTickLearner`, `rollout_learn`,
  `rollout_learn_tick`, `rollout_learn_curriculum`, `evaluate_learner`, `ladder_verdict`, `PILOT_SEEDS`,
  `LADDER_BIND_PASS=0.5`, `LADDER_SURV_PASS=0.5`, `_rung_composes`, `replace`, `Params`.
- **Déterminisme** : `np.random.default_rng(seed)` ; deux runs au même seed byte-identiques. Path-scopé.
- **Ne PAS préjuger le verdict** : les tests vérifient le CONTRAT (structure) et des sanités connues (L2 compose,
  L0 non), jamais le résultat de la cellule ouverte (substep, on).

## Composant 1 — décomposition 2×2

### Mécanique

Quatre cellules, bras inesc, E0=16, médiane sur `seeds` (défaut 3-4 seeds) :

| | curriculum OFF | curriculum ON |
|---|---|---|
| **crédit substep** | (L0) `rollout_learn` — connu ❌ | **NOUVEAU** : substep + warm→cold ❓ |
| **crédit tick-return** | (L1) `rollout_learn_tick` — connu ❌ inesc | (L2) `rollout_learn_curriculum` — connu ✅ |

La seule cellule non encore mesurée = **(substep, curriculum-ON)** : le crédit substep faible, mais avec le
schedule curriculum warm→cold (c_consume_empty réduit en warm puis plein). Elle tranche le levier décisif.

### Entraîneur de cellule

`_train_cell(credit, curriculum, arm, params, seed, M, n_episodes, n_warm, n_cold) -> learner` :
- `credit="substep"` → `NpReinforceLearner(seed, arm)` ; si `curriculum` : phase WARM
  `rollout_learn(learner, arm, replace(params, c_consume_empty=0.5), seed, M, n_warm)` puis phase COLD
  `rollout_learn(learner, arm, params, seed+100, M, n_cold)` ; sinon `rollout_learn(..., n_episodes)`.
- `credit="tick"` → `NpTickLearner(seed, arm)` ; si `curriculum` :
  `rollout_learn_curriculum(learner, arm, params, seed, M, n_warm, n_cold)` ; sinon
  `rollout_learn_tick(..., n_episodes)`.

(Le schedule substep-curriculum réplique EXACTEMENT celui de `rollout_learn_curriculum` — warm c_warm=0.5 +
seed / cold params pleins + seed+100 — mais avec `rollout_learn` au lieu de `rollout_learn_tick`. Le
`entropy_beta` n'existe pas pour L0/substep : la phase warm substep n'a pas de bonus d'entropie, cohérent avec
le fait que l'entropie n'est PAS le levier porteur, cf revue finale.)

### Évaluation + verdict gelé

Chaque cellule : `evaluate_learner(learner, "inesc", params, seed+5000, M)` → binding_gap, survival.
`composes = _rung_composes(binding, survival)` (seuils gelés 0.5).

`decompose_2x2(seeds=PILOT_SEEDS[:3], E0=16.0, M=32, n_episodes=120, n_warm=80, n_cold=80) -> dict` retourne :
`{"cells": {("substep","off"): {...}, ("substep","on"): {...}, ("tick","off"): {...}, ("tick","on"): {...}},
"verdict": <str>}` où chaque cellule = `{"binding", "survival", "composes"}` (médianes sur seeds).

**Verdict gelé** (`_decomp_verdict(cells)`), arbre de décision gaté sur la cellule CONNUE-composante (tick,on)=L2 :
- Si NON `(tick,on).composes` → `"INCOHERENT"` (contredit le verdict merge — signale un artefact à investiguer).
- Sinon, (tick,on) compose (attendu), on classe le levier décisif :
  - `"CURRICULUM-SUFFISANT"` si `(substep,on).composes` — le curriculum SEUL rachète le crédit faible → le
    BOOTSTRAP est LE levier décisif, le crédit-horizon est secondaire.
  - sinon `"CREDIT-SUFFISANT"` si `(tick,off).composes` — tick-return seul binde sans curriculum (a priori
    improbable : L1 échoue inesc).
  - sinon `"BOTH-NECESSARY"` — ni le curriculum seul (substep,on) ni le crédit-horizon seul (tick,off) ne
    composent, mais les deux ensemble (tick,on) oui → [2] regroupe légitimement crédit-horizon ET bootstrap.

(Clés de dict = tuples ; en JSON/print on les rend `"substep|off"` etc. dans le rapport.)

## Composant 2 — sweep de robustesse

`robustness_sweep(seeds=PILOT_SEEDS[:3], e0_grid=(12.0,16.0,24.0,32.0), M=32, n_episodes=120, n_warm=80,
n_cold=80) -> dict` : pour chaque E0, `res = ladder_verdict(seeds, E0, M, n_episodes, n_warm, n_cold)` ;
collecte `{"E0", "verdict", "L0_composes", "L1_composes", "L2_composes"}`.

**Verdict gelé** : `"[2]-ROBUSTE"` si le verdict par-E0 == `"[2] CREDIT-ATTRIBUE"` pour TOUS les E0 du grid ;
sinon `"[2]-FRAGILE"` avec la fenêtre (liste des E0 conformes / non-conformes).

Retourne `{"grid": [ ... ], "robust": bool, "verdict": <str>}`.

## Composant 3 — CLI + rapports

- `_report_decompose(res)` : imprime la grille 2×2 (binding/survie/compose par cellule) + le verdict.
- `_report_robustness(res)` : imprime la table par-E0 (verdict + L0/L1/L2 compose) + `[2]-ROBUSTE|FRAGILE`.
- `__main__` : ajouter la branche `--edr201` qui lance `_report_decompose(decompose_2x2())` PUIS
  `_report_robustness(robustness_sweep())`. (Conserver `--ladder`, `--learner`, défaut `calibrate`.)

## Tests (`tests/sandbox/test_craft_or_starve_edr.py`, APPEND)

- `test_train_cell_determinism` : `_train_cell("substep", True, ...)` au même seed → poids byte-identiques
  (W_out/W_hh/W_ih). Config minuscule (M=8, n_warm=8, n_cold=8).
- `test_decompose_2x2_contract` : `decompose_2x2(seeds=(1000,), M=8, n_episodes=10, n_warm=10, n_cold=10)` →
  4 cellules présentes (clés attendues), chaque cellule a `{binding, survival, composes}`, `verdict` ∈ l'ensemble
  gelé. (NE vérifie PAS quelle cellule compose — c'est le résultat du run.)
- `test_robustness_sweep_contract` : `robustness_sweep(seeds=(1000,), e0_grid=(16.0, 24.0), M=8, n_episodes=10,
  n_warm=10, n_cold=10)` → `grid` longueur 2, chaque ligne a `{E0, verdict, L0_composes, L1_composes,
  L2_composes}`, `robust` booléen.
- `test_decomp_sanity_known_cells` : sur une config un peu plus grande mais bornée (M=16, n_episodes=40,
  n_warm=40, n_cold=40, seed 1000), (tick,on) compose ET (substep,off) ne compose PAS — les deux cellules
  CONNUES (sanité, pas la cellule ouverte). ⚠️ config choisie pour que (tick,on) binde de façon fiable ; si trop
  petite pour binder, relever à la config validée (M=32, 80+80).

## Verdict décisif du contrôleur (hors tests)

`python -m tools.craft_or_starve_edr --edr201` (2 passes byte-identiques). Résultats :
- **Décomposition** : la cellule (substep, on) tranche → `CURRICULUM-SUFFISANT` (bootstrap = levier) ou
  `BOTH-NECESSARY` (crédit-horizon + bootstrap requis). Les deux RAFFINENT le verdict [2] sans le contredire.
- **Robustesse** : `[2]-ROBUSTE` sur E0 {12,16,24,32} → verdict non config-fragile ; sinon fenêtre auditée.

Un `INCOHERENT` (décomposition) ou un `[2]-FRAGILE` large (robustesse) serait un signal d'artefact à investiguer
AVANT de consolider — mais a priori improbable vu la séparation stark 1.0-vs-0.0 du verdict merge.

## Compute

Décomposition = 4 cellules × 3 seeds (E0=16). Robustesse = 3 barreaux × 3 seeds × 4 E0. Épisodes réduits
(3 seeds vs 4, séparation nette) → cible ~20-30 min pour 2 passes byte-identiques.
