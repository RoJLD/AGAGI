# De-confond p_reach — re-base les baselines de forage (knob `disable_repro`)

> **Spec de conception** — 2026-06-30. Chantier TOOLING + re-mesure (dette d'EDR 114).
> Outil : `tools/lewis_survival_sweep.py` UNIQUEMENT (zero fichier partage -> zero collision avec la
> session // qui pilote la migration moteur torch). Doc = `docs/EDR/114b` (addendum, pas de numero
> EDR contendu : la session // a deja claime 115/116/117).

## 1. Contexte & dette

EDR 114 a decouvert que `p_reach` mesure par `_measure_forage` (sur le pool `agents + dead_agents`)
est **confondu par la reproduction intra-monde** : quand le forage reussit, la population explose
(n: ~192 initiaux -> ~5857) et les **nouveau-nes tardifs** (spawn tick 140+, pas le temps d'atteindre
en 150 ticks) **diluent** `p_reach`. Diagnostic EDR 114 (oracle, figees) : 0.47 (avec repro) -> 0.875
(sans repro, cohorte fixe). Le confond deflate `p_reach` de **2-4x**.

Consequence : les baselines `p_reach` REPLICA d'EDR 105 (mobiles ~0.18) / 106 (figees ~0.21) SOUS-
ESTIMENT la vraie capacite de la politique apprise. **Dette** : exposer le de-confond dans le harnais
forage et **re-baser** ces magnitudes.

**Decouverte (lecture du code) qui simplifie le chantier** : le mecanisme de de-confond EXISTE DEJA.
`Biosphere3D.benchmark_mode` (attribut, defaut `False`, l.46) gate les TROIS chemins de reproduction
(energie l.1341 `not self.benchmark_mode` ; social/MATE + HGT l.1544 `if self.benchmark_mode: [],[]`).
EDR 112 (G0) l'utilise deja (« cohorte fixe, pas de reproduction/mutation/HGT »). Il n'est juste PAS
expose dans `_measure_forage`. **Le chantier = cabler le flag existant + re-mesurer + documenter.**

## 2. Architecture (zero-collision)

Tout dans `tools/lewis_survival_sweep.py`. AUCUN fichier partage (`config.py`, `world_1_stoneage.py`)
n'est touche -> pas de conflit de merge avec la session // (qui edite activement monde/backend torch).
Le flag `benchmark_mode` est pose APRES construction de l'env (`env.benchmark_mode = True`), comme le
fait deja EDR 112.

## 3. Composants & interfaces

### 3.1 `_measure_forage(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150, disable_repro=False)`
- Ajouter le parametre `disable_repro=False` (defaut -> comportement actuel byte-identique).
- Apres `env = Biosphere3D(cfg)` (l.385), inserer : `if disable_repro: env.benchmark_mode = True`.
  -> cohorte fixe (pas de repro energie/MATE/HGT) -> pool = cohorte initiale, pas de dilution.
- Rien d'autre ne change. A `disable_repro=False` : non-regression totale.

### 3.2 `main_forage_deconfound(speeds=(1.0, 0.0), n_eval=8, R=1, seed=1140, _return=False)`
- Matrice **2x2 {disable_repro False/True} x {prey_speed 1.0 mobiles, 0.0 figees}**, politique APPRISE
  (`reach_oracle` non pose = False ; replicas `_load_champions`). Graines APPARIEES
  (`base + r*1000 + i`, comme `main_approach`).
- Pour chaque `(disable_repro, speed)` : `cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True,
  trace_forage=True, prey_speed_scale=speed)` ; `agg = _measure_forage(cfg, seeds, n_apex=0,
  max_ticks=150, disable_repro=disable_repro)`. Collecte 4 `(disable_repro, speed, agg)`.
- Co-active `trace_forage=True` ET `trace_energy_sinks=True` (exige de `_measure_forage`).
- Puis `_report_deconfound`.

### 3.3 `_verdict_deconfound(aggs)`
- `aggs` = liste `(disable_repro: bool, speed: float, agg: dict)`. Compare la cellule FIGEE
  (speed=0.0) avec-repro vs sans-repro : `ratio = p_reach[norepro,frozen] / max(p_reach[repro,frozen],
  1e-9)`. **CONFOND CONFIRME** si `ratio >= 1.5` (la deflation par pooling est reelle et materielle) ;
  **CONFOND NEGLIGEABLE** si `ratio < 1.5`. Cellule manquante -> "INDETERMINE".

### 3.4 `_report_deconfound(h, aggs, R, n_eval, _return)`
- Table ASCII (1 ligne/cellule : disable_repro, speed, p_reach, p_cap, mean_min_dist, n) + facteur de
  deflation par vitesse (sans-repro / avec-repro) + baselines corriges (sans-repro) vs confondus
  (avec-repro, ~ EDR 105/106) + verdict. Sauvegarde JSON (`reached_raw` retire). Tout ASCII (cp1252).

## 4. Re-base attendue (d'apres les diagnostics EDR 114)

| condition (apprise) | avec-repro (confondu) | sans-repro (corrige) |
|---|---|---|
| figees (speed 0) | ~0.21 (EDR 106) | ~0.43 (EDR 114 diag) |
| mobiles (speed 1) | ~0.18 (EDR 105/107) | a mesurer |

Verdict attendu : `CONFOND CONFIRME` (ratio figees ~2x). Donne les vrais p_reach de la politique
apprise (sa capacite etait sous-estimee, pas nulle), sans changer les conclusions QUALITATIVES de
l'arc (le mur reste le substrat : EDR 114 a montre apprise 0.43 ≪ oracle 0.875 a condition egale).

## 5. Tests (TDD, banc `tests/sandbox/test_p_reach_deconfound.py`)

1. **`_measure_forage` accepte `disable_repro`** : signature OK ; `disable_repro=False` par defaut.
2. **De-confond effectif (comportemental)** : a `prey_speed_scale=0.0` (figees), comparer p_reach
   `disable_repro=False` vs `True` sur memes graines (n_eval reduit, p.ex. 4) -> `p_reach[True] >
   p_reach[False]` ET le pool sans-repro est BEAUCOUP plus petit (`n_agents[True] ≪ n_agents[False]`,
   prouvant que la reproduction est bien coupee). C'est la verification directe du mecanisme.
3. **Non-regression `disable_repro=False`** : deux appels `_measure_forage(..., disable_repro=False)`
   memes graines -> `p_reach` identique (le defaut ne change rien ; determinisme).
4. **`_verdict_deconfound` branches** : aggs synthetiques -> `CONFOND CONFIRME` (ratio 2.0) /
   `CONFOND NEGLIGEABLE` (ratio 1.1) / `INDETERMINE` (cellule figee absente).
5. **Smoke** : `main_forage_deconfound(speeds=(0.0,), n_eval=2, R=1, seed=99140, _return=True)` tourne,
   renvoie un verdict valide, JSON ecrit. **Seed distinct du run reel** (provenance).

## 6. Cout & repli

4 cellules (mais sans-repro = pool petit = rapide ; avec-repro = comme EDR 105) x `n_eval=8`,
`_measure_forage` SANS evolution -> modere. R=1, seed reel 1140. Repli : n_eval=4. Run reel APRES
revue ; AUCUN test relancé apres (provenance — lecon EDR 107).

## 7. Provenance, determinisme, non-regression

- `results/` gitignore ; harnais `name="lewis_forage_deconfound"` -> JSON distinct (pas de collision
  avec `lewis_reach_oracle`/`lewis_forage`). Seed reel 1140 ; smoke 99140 distinct.
- Determinisme verifie (test 3) ; run reel reproduit une fois.
- **Non-regression** : `disable_repro=False` defaut -> `_measure_forage` byte-identique ; tous les
  appelants existants (`main_forage`/`main_approach`) inchangés (param optionnel). AUCUN fichier
  partage touche.
- ASCII-only dans tout `print` execute (cp1252).

## 8. Doc & memoire

- **Doc** : `docs/EDR/114b_P_Reach_Deconfound_Corrected_Forage_Baselines.md` (addendum a EDR 114, pas
  de numero EDR contendu). Contenu : le confond (rappel EDR 114), la table 2x2 corrigee, le facteur de
  deflation, l'outil `disable_repro`, et la re-base explicite des baselines 105/106 (qualitatif
  intact, magnitudes corrigees).
- **Memoire** : `lewis-energy-economy-wall.md` -> noter les p_reach corriges (apprise figees ~0.43,
  mobiles corrige) et que l'outil de de-confond est cable (`disable_repro`).

## 9. Coordination (sessions paralleles)

Chantier choisi explicitement pour NE PAS entrer en collision avec la session // qui pilote la
migration moteur torch (backend ADR-003, EDR 115 compositional, FamineWorld) : (a) tooling-only dans
`lewis_survival_sweep.py` (la session // edite `backend*.py`/`world`/`config`) ; (b) doc en `114b`
(pas de numero EDR que la session // pourrait vouloir) ; (c) reutilise le `benchmark_mode` EXISTANT
(pas de nouveau mecanisme monde). Commits path-scoped.
