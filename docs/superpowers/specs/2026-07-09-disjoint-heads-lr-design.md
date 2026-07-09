# EDR 194 — Bras lr-par-tête : le résidu de l'arc têtes disjointes est-il fermé par le seul bouton de crédit qu'Adam n'annule pas ?

> **Date** : 2026-07-09. **Fil** : têtes disjointes / typologie d'intelligence (extension, bloc 190+).
> **Type** : instrument isolé, proxy supervisé teacher-student. Auto-contenu PyTorch, additif (ne touche NI `src/`
> NI le fil torch //).

## 0. Contexte et question

L'arc têtes disjointes (152→192) a établi que le gain des têtes disjointes (sous-réseaux indépendants) sur le
substrat PLAT (trunc partagé) n'est **pas** de l'isolation d'interférence architecturale mais un **équilibrage de
crédit** côté optimiseur. Trois leviers *non-archi* côté FLAT récupèrent le gain, sans jamais le fermer entièrement :

| Levier (côté FLAT) | EDR | Recovery moyen |
|---|---|---|
| Échelle de loss (GradNorm-lite EMA) | 153 | 0.79 |
| Moments Adam par-tête (3 Adam) | 154 | 0.73 |
| Les deux combinés (synergie) | 192 | 0.70 (redondant) |

Le point décisif d'EDR 192 : **« Adam par-tête annule le scaling »**. Adam est ~invariant d'échelle — multiplier la
loss de la tête *k* par un facteur `c` multiplie son gradient par `c`, mais Adam divise par `√v ∝ c`, donc le pas
effectif est ~inchangé (aux termes ε/biais près). Donc sous Adam par-tête, l'échelle de loss est un quasi no-op :
c'est pourquoi combiner les deux (192) ne dépasse pas les leviers seuls.

**Il reste alors un seul bouton de crédit qu'Adam ne normalise PAS : le learning rate.** `lr_k` multiplie
directement le pas d'Adam de la tête *k* (Adam met à l'échelle le gradient à norme unité, puis multiplie par `lr`).
Le résidu ~0.21–0.30 que le scaling ne fermait pas est donc peut-être fermable par un **lr adaptatif par-tête**.

**Question falsifiable** : un bras FLAT + 3 Adam par-tête où le *lr* (et non la loss) est modulé par `1/EMA(loss_k)`
ferme-t-il le résidu (→ le résidu était un déséquilibre de *pas* par-tête, archi réfutée à ~100 %), ou plafonne-t-il
au niveau des leviers interchangeables ~0.7–0.79 (→ le résidu ~0.27 est un vrai plancher *architectural*, petit) ?

## 1. Architecture

Un seul nouveau fichier, strictement additif, calqué sur la famille :

- `tools/disjoint_heads_lr.py` — importe **read-only** :
  - de `tools.disjoint_heads_ab` (152) : `torch`, `FlatModel`, `_make_teachers`, `_make_data`, `_losses`,
    `_eval_losses`, `_train_arm`, `N_HEADS`, `HELDOUT`, `BATCH`, `STEPS`, `LR`.
  - de `tools.disjoint_heads_confound` (153) : `_recovery`.
- `tests/sandbox/test_disjoint_heads_lr.py` — tests TDD.

Aucune modification d'aucun fichier existant. Aucun import de `src/`. Le banc n'utilise que la machinerie
teacher-student déjà figée (3 profs MLP tanh fixes, dims `D=32 H=48 N_HEADS=3`, `STEPS=2000`, `LR=1e-3`).

## 2. Cœur — `_train_flat_lr_perhead(seed, teachers, steps=STEPS, decay=0.99)`

Calqué **exactement** sur `_train_flat_norm_perhead` d'EDR 192, à **une seule différence** : au lieu de scaler la
*loss* de la tête *k* par `w_k`, on scale le *learning rate* de son optimiseur par `w_k` (la loss reste brute).

Structure :
1. `torch.manual_seed(seed)` ; `np.random.seed(seed)` ; `held = _make_data(HELDOUT, seed + 10_000, teachers)`.
2. `model = FlatModel()` (même init au seed que tous les bras) ; `opts = [Adam(model.parameters(), lr=LR) for _ in range(N_HEADS)]`.
3. `model.train()` ; `ema = None`.
4. Pour `t in range(steps)` :
   - `batch = _make_data(BATCH, seed * 1_000_003 + t, teachers)`.
   - `ls = _losses(model(batch[0]), batch)` (forward UNIQUE).
   - `det = np.array([float(ls[0]), float(ls[1]), float(ls[2])], dtype=np.float64)`.
   - `ema = det.copy() if ema is None else decay * ema + (1.0 - decay) * det`.
   - `w = _norm_weights(ema)` (helper pur ci-dessous → `mean(w) = 1`).
   - Pour `k in range(N_HEADS)` :
     - `opts[k].param_groups[0]["lr"] = LR * float(w[k])`   ← **la seule ligne qui change vs 192**
     - `opts[k].zero_grad(set_to_none=True)`
     - `ls[k].backward(retain_graph=(k < N_HEADS - 1))`   ← **loss BRUTE, non scalée**
     - `opts[k].step()`
5. `return _eval_losses(model, held)`.

Helper pur (testable en isolation) :

```python
def _norm_weights(ema, eps=1e-8):
    """Poids par-tête normalisés à moyenne 1 : w_k ∝ 1/(EMA_k+eps), w.sum() == N_HEADS.
    Miroir de la normalisation d'EDR 153/192, extrait ici pour testabilité (test 2)."""
    w = 1.0 / (np.asarray(ema, dtype=np.float64) + eps)
    return w / w.sum() * N_HEADS
```

Notes de correction (pour l'implémenteur) :
- Adam lit `lr` depuis `param_groups` au moment de `.step()` → muter `param_groups[0]["lr"]` avant `.step()` prend
  effet au pas courant. Chaque optimiseur possède TOUS les params (`model.parameters()`) mais ne fait un pas qu'avec
  le gradient de la loss de sa tête (grâce au `zero_grad` + un seul `ls[k].backward()` avant son `step`). Le trunc
  partagé reçoit donc `N_HEADS` mises à jour par pas, chacune avec le gradient de sa tête, son propre état de moments
  Adam, et **son `lr_k`** — exactement la structure d'EDR 192 mais avec le lr modulé au lieu de la loss.
- À `t = 0`, `ema` est initialisé à `det` → `w` est bien défini dès le premier pas.

## 3. Mesure et verdict

- `recovery = _recovery(flat, flat_lr_perhead, disj)` (moyenne des têtes MSE `value` et `pred` de
  `(flat − levier)/(flat − disj)`, garde `|denom| < 1e-9` sautée). **Directement comparable** à 0.79/0.73/0.70.
- `flat, _ = _train_arm("flat", seed, teachers, steps)` et `disj, _ = _train_arm("disjoint", seed, teachers, steps)`
  (bras de référence figés d'EDR 152).

**Verdict pré-enregistré `_verdict_lr(per_seed_recovery)` — GELÉ, seuils calqués sur 192 pour comparabilité :**
- `LR_CLOSES` si `recovery ≥ 0.90` sur une majorité de seeds → le résidu était un déséquilibre de *pas* par-tête,
  archi réfutée ~100 %.
- `LR_INTERCHANGEABLE` si `recovery ≤ 0.79` sur une majorité → lr-par-tête est **interchangeable** avec les leviers
  de crédit ~0.70–0.79 (153/154/192) et **ne ferme pas** le résidu. ⚠️ Cela **n'établit PAS** que le résidu ~0.27
  soit *architectural* : ne pas le fermer avec CE bouton de crédit (lr adaptatif doux, mean(w)=1) laisse ouvert que
  d'autres mécanismes de crédit non testés (lr par-paramètre, 2ᵉ ordre, schedules) le ferment. Seul `LR_CLOSES`
  réfuterait l'archi ; `LR_INTERCHANGEABLE` dit « le résidu résiste aux boutons de crédit *testés* », pas plus.
- `PARTIAL` sinon (fermeture partielle du résidu).

Majorité = `n // 2 + 1` (identique à toute la famille).

**Prédiction pré-enregistrée (honnête)** : `LR_INTERCHANGEABLE` ou `PARTIAL` attendu — v3 (moments seuls, 0.73)
contient déjà 3 Adam par-tête et la modulation de lr est douce (mean(w)=1, bornée par l'EMA). Mais `LR_CLOSES` reste
ouvert et serait le résultat fort (le résidu s'effondre sous le bon bouton de crédit).

## 4. `main_lr_check(K=5, base=2200, steps=STEPS, _return=False)`

Miroir de `main_v4_check` (192) :
- Garde `SKIPPED_NO_TORCH` si `torch is None`.
- `torch.use_deterministic_algorithms(True)` (try/except) ; `torch.set_num_threads(1)`.
- `teachers = _make_teachers()`.
- Pour `i in range(K)`, `s = base + i` : calcule `flat`, `flat_lr_perhead`, `disj` et `recovery` par seed.
- Verdict = `_verdict_lr(recoveries)` ; `mean_recovery = mean(recoveries)`.
- Rapport table (miroir de `_report_v4` : `seed | FLAT v/p | FLAT_LR v/p | DISJOINT v/p | recovery`).
- `res = {"verdict", "mean_recovery", "per_seed"}` ; retourne `res` si `_return`.

## 5. Rigueur / déterminisme

- `set_num_threads(1)` + `use_deterministic_algorithms(True)` → **2 passes byte-identiques** exigées au run
  (via `main_lr_check(_return=True)` comparé sur `mean_recovery` et `per_seed` recoveries).
- Hyperparamètres figés hérités de 152 (`D H N_HEADS K_A P_PRED STEPS LR BATCH HELDOUT`) — aucune re-définition.
- Le run réel : `K=5`, `base=2200`, `STEPS=2000` (identique à toute la famille pour comparabilité des recoveries).

## 6. Tests (TDD)

`tests/sandbox/test_disjoint_heads_lr.py` :
1. **Déterminisme** : deux appels `main_lr_check(K=2, base=2200, steps=50, _return=True)` → `mean_recovery` et les
   recoveries par-seed byte-identiques.
2. **Normalisation w** : dans une reproduction locale du calcul EMA (ou en exposant un helper), `mean(w) == 1`
   (i.e. `w.sum() == N_HEADS`) à tolérance flottante, pour un vecteur de pertes arbitraire positif.
3. **Bras lr-par-tête fonctionne** : `_train_flat_lr_perhead(seed=2200, teachers, steps=50)` retourne un dict à 3
   clés `action/value/pred`, toutes finies (`np.isfinite`).
4. **Différence effective vs 192** : sur ≥1 seed à `steps` court, `_train_flat_lr_perhead` et
   `_train_flat_norm_perhead` (192) donnent des pertes `value/pred` **différentes** (preuve que moduler le lr ≠
   moduler la loss sous Adam — le cœur de l'hypothèse).
5. **Verdict gelé** : `_verdict_lr` renvoie `LR_CLOSES` / `LR_INTERCHANGEABLE` / `PARTIAL` sur des listes de recovery
   synthétiques couvrant les trois régimes et la règle de majorité.
6. **Smoke** : `main_lr_check(K=2, base=2200, steps=30, _return=True)` s'exécute, `verdict` ∈ ensemble attendu,
   `len(per_seed) == 2`.

Tests conçus pour tourner vite (`steps` court) sauf le run scientifique (`steps=2000`).

## 7. Provenance / non-périmètre

- **Additif strict** : un fichier tool + un fichier test + spec/plan/EDR. `src/` intact, aucun import de `src/`.
  Réutilise par import la machinerie figée de 152 (`disjoint_heads_ab`) et 153 (`_recovery`). Ne touche pas le fil
  torch // (`torch_batch_model.py`, `backend_torch.py`, `substrate_*`) ni le fil famine/Lewis.
- **Numérotation** : EDR **194**, bloc **190+** (extension de l'arc têtes disjointes ; 190/191/192 = correlated/
  capacity/synergy ; 193 = g bilinéaire, fil G4). Convention collisions : cf. mémoire `parallel-sessions-shared-tree`.
- **Subagent-driven** : machinerie (tool + tests) en tâches TDD, revue par-tâche (spec + qualité), revue finale opus
  (validité scientifique + verdict gelé avant run). Verdict figé AVANT toute exécution du run réel.
