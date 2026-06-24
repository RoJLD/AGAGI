# Spec — D2 KWTA modéré (sparsité imposée) + mesure

> **Statut** : design validé (2026-06-24), prêt pour plan.
> **Valide** : `docs/roadmap/NAS.md` §2 Axe D — D2 (pivot après réfutation de D1).
> **Contexte** : D1 a montré que la sélection ne sparsifie PAS (`mean_active` plat). D2 **impose** la
> sparsité structurellement et mesure son **coût en compétence**.

## 1. Question falsifiable

La sparsité **imposée** (modérée, sur les nœuds cachés) est-elle **gratuite** (NEUTRE/EFFICACE :
compétence préservée à `mean_active` réduit) ou **coûteuse** (NUIT : compétence/survie s'effondre) ?

## 2. Mécanisme (cœur) — KWTA sur les cachés

Dans `MambaBatchModel.forward` (`src/agents/mamba_agent.py`), **après la finalisation de `H`**
(résolution du dreaming, ~l.568) et **avant l'extraction des sorties** (l.570), appliquer par agent un
masque **k-winners-take-all sur les nœuds CACHÉS uniquement** :
- Positions cachées de l'agent `i` = `map_idx[I_i : N_i - O_i]` (via `self.mappings[i]`).
- Garder les `n_keep = max(1, ceil(keep * n_hidden))` plus grands `|H|`, **zéro** les autres.
- **Entrées** (`map_idx[0:I_i]`, ré-injectées chaque tick) et **sorties** (`map_idx[N_i-O_i:N_i]`,
  lues pour preds/attention/NTM/goal/pred) **JAMAIS masquées** → la politique n'est pas cassée.
- Appliqué sur `H` avant `self.H_prev_batch = H` (l.579) ⇒ l'état récurrent ET le compteur D1
  `activation_cost_batch` (l.581) reflètent la sparsité.

### Gating (attribut de classe, comme `ABLATE_*`/`METABOLIC_ACTIVE_EPS`)
`MambaBatchModel.KWTA_KEEP_FRAC = 1.0` (défaut ⇒ **off, non-régression bit-exacte** : `if keep < 1.0`).
Choisi attribut de classe (pas kwarg `__init__`) pour ne pas casser le *seam* `batch_model_cls`
(BaselineBatchModel S2 n'accepterait pas le kwarg). Le forward lit `MambaBatchModel.KWTA_KEEP_FRAC`.

### Propagation depuis la config
- `WorldConfig.kwta_keep_frac: float = 1.0` (`src/environments/config.py`).
- `world_1_stoneage`, juste avant la construction du batch model (~l.959) :
  `MambaBatchModel.KWTA_KEEP_FRAC = getattr(self.config, "kwta_keep_frac", 1.0)`
  (réassigné à chaque step ⇒ reflète toujours la config courante ; séquentiel ⇒ pas de course).

## 3. Mesure — généraliser l'outil X2 existant

`tools/metabolic_cost_sweep.py` balaye aujourd'hui `metabolic_cost_coef` (baseline 0.0). Le généraliser
pour balayer un **knob de config arbitraire** (rétro-compatible) :
- `_make_cfg(param, value)` : `setattr(cfg, param, value)` (au lieu de `cfg.metabolic_cost_coef=coef`).
- `run_lineage(seed, value, ..., param="metabolic_cost_coef")`.
- `run_sweep(seeds, values, ..., param="metabolic_cost_coef", baseline=0.0)` : la baseline (au lieu du
  `0.0` codé en dur) est prependée si absente ; ratios calculés vs la lignée `baseline`.
- `main()` : env `MCS_PARAM` (défaut `metabolic_cost_coef`), `MCS_BASELINE` (défaut `0.0`),
  `MCS_SWEEP`, `MCS_SEEDS`, etc. **D1 reste lançable à l'identique** (défauts inchangés).

Pour D2 : `MCS_PARAM=kwta_keep_frac MCS_BASELINE=1.0 MCS_SWEEP=1.0,0.7,0.5,0.3`.

KPIs/verdict inchangés (compétence, `mean_active`, efficiency, survival ; EFFICACE/NEUTRE/NUIT).
Lecture D2 : **NEUTRE/EFFICACE = sparsité gratuite** (poursuivre typage/MoE) ; **NUIT = le réseau a
besoin de sa densité** (abandonner l'axe sparsité).

## 4. Tests (TDD)

**Cœur (KWTA)** :
1. Défaut `KWTA_KEEP_FRAC=1.0` ⇒ forward bit-identique au baseline (réutiliser le pattern
   `test_wired_genes`/`test_metabolic_cost` : deux agents identiques, H final inchangé vs sans KWTA).
2. `KWTA_KEEP_FRAC=0.5` ⇒ le nb de cachés actifs (`|H|>0` sur le slice caché) ≈ moitié ; **inputs et
   outputs inchangés** (comparer `H[inputs]`/`H[outputs]` avec et sans KWTA → identiques).
3. `n_keep ≥ 1` même à keep très bas (pas de réseau totalement éteint).
4. `WorldConfig.kwta_keep_frac` défaut = 1.0 (non-régression).
5. Propagation : après un step de monde avec `config.kwta_keep_frac=0.5`,
   `MambaBatchModel.KWTA_KEEP_FRAC == 0.5` (smoke léger ou via lecture de l'attribut).

**Outil généralisé** :
6. `run_sweep(..., param="X", baseline=B)` avec faux runner : baseline prependée, ratios vs B corrects.
7. **Rétro-compat D1** : `run_sweep(seeds, [0.01], ...)` sans `param` ⇒ comportement identique à avant
   (param=metabolic_cost_coef, baseline=0.0).

## 5. Garde-fous / non-régression

- `KWTA_KEEP_FRAC=1.0` et `kwta_keep_frac=1.0` par défaut ⇒ aucun masque ⇒ prod inchangée.
- KWTA ne touche QUE les cachés ⇒ preds/attention/NTM/goal/pred (lus depuis les sorties) intacts.
- L'outil garde ses défauts D1 ⇒ les runs D1 restent reproductibles.

## 6. Hors-périmètre

- Le **run à l'échelle** + EDR de conclusion D2 (compute, après l'outil).
- KWTA adaptatif / par couche / sur entrées → si D2 est NEUTRE et qu'on veut pousser (séparé).
- D3 (nœuds typés) → séparé.
