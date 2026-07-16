# Contrôle du confond Adam par-tête (EDR 153) — design

> **Date** : 2026-07-01. **Type** : contrôle décisif d'EDR 152 (confond I1). Tooling additif, zéro collision.
> **Question** : le gain de DISJOINT (EDR 152 : DISJOINT_HELPS mais cosinus≈0, gain MSE-only) vient-il d'un
> **équilibrage de crédit** capturable dans le substrat PLAT, ou de l'isolation architecturale (#5) ?

## 1. But & falsifiabilité

EDR 152 a montré : têtes disjointes battent le plat (+43 %) MAIS sans interférence (cos≈0), le gain concentré sur
les têtes MSE (value/pred), la tête action (CE) inchangée → signature du **conditionnement Adam par-tête** (I1),
pas de l'isolation. Ce contrôle teste directement : un fix **cheap** côté FLAT (équilibrage d'échelle de loss)
recouvre-t-il le gain de DISJOINT ?

**Bras** (mêmes profs/données/seeds — réutilise la machinerie d'`tools/disjoint_heads_ab.py`, sur main via PR #118) :
- **FLAT** : baseline (trunc partagé, loss combinée, 1 Adam). Via `_train_arm("flat", ...)`.
- **DISJOINT** : référence EDR 152 (3 sous-réseaux, 3 Adam). Via `_train_arm("disjoint", ...)`.
- **FLAT_NORM** : `FlatModel` (architecture PLATE identique à FLAT, même init au seed) + **1 seul Adam**, mais
  losses **pondérées par tête** (GradNorm-lite : poids `w_k = 1/EMA(loss_k)` normalisés à moyenne 1) → contre la
  domination de l'échelle CE identifiée par opus. **Ne change QUE l'équilibrage d'échelle de loss.**

**Verdict pré-enregistré** (gelé), sur le **recouvrement** par FLAT_NORM du gain DISJOINT (têtes MSE value+pred) :
`recovery_k = (FLAT_k − FLATNORM_k) / (FLAT_k − DISJOINT_k)`, moyenné sur {value, pred}, par seed.
- `CONFOUND_CONFIRMED` si `recovery ≥ 0.50` sur **≥ 3/5 seeds** → le fix cheap suffit ; **migration #5 (têtes
  disjointes architecturales) RÉFUTÉE comme levier** ; le levier réel = équilibrage de crédit dans le plat.
- `CONFOUND_REFUTED` si `recovery ≤ 0.20` sur ≥ 3/5 → l'équilibrage d'échelle ne suffit pas ; le gain exige plus
  (moments Adam séparés / architecture) → pointe une V3 (4e bras FLAT+Adam-par-tête).
- `CONFOUND_PARTIAL` sinon.

## 2. Lecture des issues

- **CONFIRMED** : résultat NET et actionnable — le substrat plat n'a pas besoin d'être refondu (#5) ; un
  équilibrage de crédit (GradNorm/lr-par-tête) capture le gain. Renforce l'arc « verrou = régime
  d'apprentissage/crédit, pas topologie ».
- **REFUTED** : l'équilibrage d'échelle seul ne suffit pas. Comme EDR 152 a déjà réfuté l'interférence (cos≈0), le
  gain reste **côté optimiseur** (moments Adam séparés) plutôt qu'architectural — mais la démonstration exige une
  V3. Honnête : ce banc ne tranche pas optimiseur-vs-archi dans ce cas, il élimine « l'équilibrage d'échelle ».
- **PARTIAL** : recouvrement intermédiaire → l'échelle explique une partie ; le reste est optimiseur/archi.

## 3. Composants

- **Nouveau fichier** `tools/disjoint_heads_confound.py`. Importe d'`tools.disjoint_heads_ab` : `_make_teachers`,
  `_make_data`, `FlatModel`, `_losses`, `_eval_losses`, `_train_arm`, et constantes `N_HEADS, HELDOUT, BATCH,
  STEPS, LR, torch`. **Ne modifie PAS** `disjoint_heads_ab.py` (fichier EDR 152, sur main).
- `_train_flat_norm(seed, teachers, steps=STEPS, decay=0.99) -> dict` : FlatModel + Adam unique + pondération EMA.
- `_recovery(flat, flatnorm, disj) -> float` : recouvrement moyen sur {value, pred} (garde `|denom|<1e-9`).
- `_verdict_confound(per_seed_recovery) -> str` : GELÉ (seuils 0.50 / 0.20, majorité).
- `_report_confound(...)` : table ASCII (par seed : MSE value/pred des 3 bras + recovery) + verdict.
- `main_confound_check(K=5, base=2200, steps=STEPS, _return=False) -> dict|None`.

## 4. Mécanisme FLAT_NORM (pondération EMA détachée — déterministe)

À chaque pas : `ls = (la, lv, lp)` ; `det = [float(la), float(lv), float(lp)]` (détaché) ; EMA
`ema = det` au 1er pas, sinon `decay*ema + (1-decay)*det` ; poids `w = 1/(ema+1e-8)`, normalisés `w = w/ w.sum() *
N_HEADS` (moyenne 1) ; `loss = w0*la + w1*lv + w2*lp` ; `backward()` ; `step()`. L'EMA vient de floats détachés →
strictement déterministe. Architecture et init IDENTIQUES à FLAT (même `FlatModel`, même seed) → seule la
pondération de loss diffère.

## 5. Déterminisme, structure, coordination

- `torch.manual_seed`+`np.random.seed` par bras (hérité de `_train_arm` ; répliqué dans `_train_flat_norm`).
  `torch.use_deterministic_algorithms(True)` (try) + **`torch.set_num_threads(1)`** dans `main` (leçon EDR 152 M2).
  **Run = 2 passes byte-identiques.**
- Auto-contenu PyTorch, PAS de Biosphere/src. **Tooling additif** : nouveau fichier + test, zéro modif d'un
  fichier existant. Ne touche NI `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil torch //).
- Prints exécutés = **ASCII-only** (cp1252). Accents seulement en docstrings/commentaires.
- **K = 5 seeds** (base 2200, seeds 2200..2204 — mêmes que EDR 152 pour comparabilité directe).
- **EDR 153** (bloc 150+, convention `parallel-sessions-shared-tree`).
- Test smoke `tests/sandbox/test_disjoint_heads_confound.py` : `main_confound_check(K=1, steps=30, _return=True)` →
  verdict ∈ ensemble valide + `per_seed` présent ; + test unitaire `_verdict_confound` (3 branches).

## 6. Non-périmètre / caveats hérités

- Hérite des caveats d'EDR 152 : proxy supervisé (pas RL in-world) ; profs quasi-orthogonaux (I2) ; têtes non
  appariées (I3). Ce contrôle N'ajoute PAS un bras architecture-sans-optimiseur ; en cas de REFUTED, la distinction
  optimiseur-vs-archi reste pour une V3.
- 1 variable (Commandement 15) : FLAT vs FLAT_NORM ne diffèrent QUE par la pondération de loss (même archi, même
  init, même données, même optimiseur unique).
