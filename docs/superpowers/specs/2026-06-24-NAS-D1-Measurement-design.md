# Spec — Mesure X2 de D1 (coût métabolique d'activation)

> **Statut** : design validé (2026-06-24), prêt pour plan.
> **Valide** : `docs/roadmap/NAS.md` §3 (Phase 0, étape X2) + le mécanisme D1 mergé (PR #32).
> **Pattern** : calqué sur `tools/curriculum_transfer.py` (paired multi-seed, sign test binomial,
> verdict pur testable, `Harness.save`, injection `run_era_fn`).

## 1. Question falsifiable

Le coût métabolique d'activation (`metabolic_cost_coef > 0`) **sélectionne-t-il des connectomes plus
efficients** (meilleur ratio compétence / nœuds-actifs) **sans effondrer la compétence**, dans un monde
survivable ?

**D1 est une pression de SÉLECTION** (pas un effet intra-vie) : il faut une **trajectoire évolutive**
(E ères + reproduction/cliquet) pour que des cerveaux sparses émergent. On compare donc des *lignées
évoluées* sous `coef=0` (baseline) vs `coef>0`, appariées par seed.

## 2. Banc (décision validée)

**Stoneage survivable seul** : `WorldConfig` avec `base_metabolism=0.25`, `forage_payoff=3.0`
(sweet-spot EDR 085, survie ×4 — mêmes constantes que `curriculum_transfer.SWEET_METAB/PAYOFF`).
Rationale : D1 a besoin d'un substrat où la survie est résolue pour que la sélection agisse ; en Lewis,
le mur intrinsèque (famine tick 5) masquerait l'effet sélectif (cf. mémoire *lewis-energy-economy-wall*).

## 3. Architecture — `tools/metabolic_cost_sweep.py`

Trois couches (la 1ʳᵉ est pure → testable sans biosphère, comme `compute_transfer_verdict`) :

### 3.1 Verdict pur (`compute_sweep_verdict`)
```
compute_sweep_verdict(per_coef: List[Dict], eff_band=0.05, collapse_frac=0.90) -> Dict
```
Chaque entrée `per_coef[i]` = `{coef, eff_ratios: [par seed], surv_ratios: [par seed]}` où
`eff_ratio = efficiency(coef) / efficiency(coef=0)` et `surv_ratio = survival(coef) / survival(coef=0)`,
appariés par seed. Pour chaque coef>0 :
- `median_eff = median(eff_ratios)` ; `n_fav = #{eff_ratio > 1}` ; `sign_p = _sign_test_p(...)`.
- `collapsed = median(surv_ratios) < collapse_frac`.
- **verdict** : `NUIT` si `collapsed` ; sinon `EFFICACE` si `median_eff > 1+eff_band ET 2·n_fav > n` ;
  sinon `NEUTRE`.
Réutilise `_sign_test_p` (copié/importé de `curriculum_transfer`). PUR, déterministe, testable.

### 3.2 Trajectoire évolutive instrumentée (`run_lineage`)
```
run_lineage(seed, coef, eras, num_agents, max_ticks, run_era_fn=None) -> Dict
```
- Pose `SeedManager(seed).seed_boundary(0)` (apparié : même seed pour tous les coefs).
- Boucle évolutive façon `evolve_competence.main` : `best_ever` (cliquet top-5), `_reproduce`
  (`build_population` + ÉLITE + fraction heavy 0.3) à chaque ère.
- `cfg` = `WorldConfig()` avec `base_metabolism=0.25`, `forage_payoff=3.0`, **`metabolic_cost_coef=coef`**.
- Retourne, agrégé sur la **fenêtre des 5 dernières ères** (lignée stabilisée) :
  `{seed, coef, competence, survival, mean_active, efficiency}` où
  `efficiency = competence / max(mean_active, 1e-6)`.
- `run_era_fn` injectable (défaut = `run_era_metab` §3.3) → trajectoire testable sans biosphère.

### 3.3 Ère instrumentée (`run_era_metab`)
Mirror de `evolve_competence.run_era`, + **accumulation de `mean_active`** (instrumentation tool-local,
AUCUN changement du cœur) :
```
run_era_metab(cfg, genomes, max_ticks=400) -> (scored, metrics)
```
- `env = Biosphere3D(cfg)` ; add agents (`energy=80.0`) ; `while env.agents and t<max_ticks: env.step()`.
- **Après chaque `env.step()`** : `active_sum += sum(a["model"].last_activation_cost for a in env.agents)` ;
  `agent_ticks += len(env.agents)`.
- `mean_active = active_sum / max(agent_ticks, 1)`.
- `competence = best life_score` (`calculate_life_score`, comme evolve_competence) ; `survival = t` (ticks).
- Stoppe `env.memory_retriever` si présent (repro, comme evolve_competence:57-58).
- `metrics = {"ticks": t, "score": competence, "mean_active": mean_active}`.

### 3.4 Sweep + save (`run_sweep` / `main`)
```
run_sweep(seeds, coefs, eras, num_agents, max_ticks, run_era_fn=None) -> Dict
```
- Pour chaque `seed`, pour chaque `coef` : `run_lineage(...)`. Calcule baseline (coef=0) par seed,
  puis `eff_ratio`/`surv_ratio` appariés. Assemble `per_coef` et appelle `compute_sweep_verdict`.
- `main()` : params par env (cf. §5), `Harness(seed=min(seeds), name="metabolic_cost_sweep",
  with_db=False, config=WorldConfig())`, `h.save(result)`, log du verdict (comme curriculum_transfer).

## 4. KPIs

| KPI | Définition |
|---|---|
| `competence` | best `calculate_life_score` (fitness sélectionnée), moy. 5 dernières ères |
| `survival` | ères-ticks (longueur d'ère), moy. 5 dernières ères — **garde-fou collapse** |
| `mean_active` | Σ `last_activation_cost` des vivants / nb agent-ticks |
| `efficiency` | `competence / mean_active` (la fitness de la fiche §3) |

## 5. Compute / paramétrage (angle-mort budget)

Tout par env, **petits défauts smoke** (le run à l'échelle est lancé à part) :
- `MCS_SEEDS="0,1,2"` · `MCS_SWEEP="0,0.001,0.003,0.01"` · `MCS_ERAS="15"` ·
  `MCS_NUM_AGENTS="30"` · `MCS_TICKS="400"`.
- `main()` **log** le coût estimé (seeds × coefs × eras) avant de lancer. Le smoke réel (CI/test) tourne
  avec seeds=1, coefs=[0,0.01], eras=2 via `run_era_fn` mocké → pas de biosphère.

## 6. Tests (TDD)

1. `_sign_test_p` / `compute_sweep_verdict` PURS :
   - eff_ratios tous >1, survie OK → `EFFICACE` ;
   - surv_ratios médians <0.90 → `NUIT` (même si eff>1) ;
   - eff_ratios ≈1 → `NEUTRE` ;
   - n=0 → `NEUTRE`, sign_p=1.0.
2. `run_era_metab` accumule `mean_active` : avec un `run_era_fn`/env mocké (ou un mini Biosphere smoke),
   `metrics["mean_active"]` ≥ 0 et ≤ N ; à population vide, pas de division par zéro.
3. `run_lineage` appariement : injectant un `run_era_fn` factice déterministe (renvoie competence/active
   fonction du coef), `efficiency(coef>0) > efficiency(0)` ⇒ `eff_ratio>1` ; même seed ⇒ reproductible.
4. `run_sweep` end-to-end avec `run_era_fn` factice : structure `per_coef` correcte + verdict cohérent.
5. (smoke lourd, opt-in `MCS_SMOKE=1`, non-CI) : 1 seed, coefs [0,0.01], 2 ères réelles → ne crashe pas,
   `mean_active>0`.

## 7. Hors-périmètre

- Le **run à l'échelle** (compute) et l'écriture de l'EDR de verdict → après l'outil.
- Sonde Lewis (2ᵉ banc) → différée (cf. décision banc).
- Aucune modification du cœur (`src/`) : instrumentation 100 % tool-local.
