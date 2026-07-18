# EDR 154 (V3) — Le résidu ~21 % d'EDR 153 est-il les moments Adam séparés ? (design)

> **Date** : 2026-07-01. **Fil** : têtes/facultés (per-type, bloc 150+). Suite directe d'EDR 152/153.
> **Statut** : design approuvé (brainstorming), à implémenter en subagent-driven.

## 1. Contexte et question

Arc têtes disjointes :
- **EDR 152** : DISJOINT (3 sous-réseaux, 3 Adam, losses séparées) bat le substrat plat (+43 %) MAIS sans
  interférence (cosinus≈0), gain concentré sur les têtes MSE (value/pred) → suspicion : conditionnement d'optimiseur
  par-tête, pas isolation architecturale.
- **EDR 153** : FLAT_NORM (plat, **1 Adam**, équilibrage d'échelle de loss GradNorm-lite) recouvre **79 %** du gain
  DISJOINT → CONFOUND_CONFIRMED. **Résidu ~21 %** (concentré sur la tête pred) non recouvré par le seul équilibrage
  d'échelle.

Le gain DISJOINT peut avoir trois contributeurs : **(a)** équilibrage de crédit/échelle de loss, **(b)** moments
Adam séparés (chaque sous-réseau a ses `m`/`v` propres), **(c)** isolation architecturale (trunc splitté). EDR 153
a montré que **(a) seul recouvre 79 %** → borne haute de **(c) architecture ≤ 21 %**. **V3 teste (b)** : les moments
Adam séparés ferment-ils le résidu que l'échelle de loss a laissé ?

**Question pré-enregistrée** : un bras **FLAT + Adam-par-tête** (archi PLATE, trunc partagé, mais **3 Adam** à
moments propres, SANS équilibrage d'échelle) recouvre-t-il le gain DISJOINT ?

## 2. Bras (Commandement 15 — seule variable = optimiseur, pas l'architecture)

Tous les bras partagent profs/données/seeds/init (même ordre `manual_seed → FlatModel`, mêmes graines
`held=seed+10_000`, `batch=seed*1_000_003+t`).

- **FLAT** : trunc partagé, loss combinée, **1 Adam** (baseline). Via `_train_arm("flat", ...)` d'EDR 152.
- **DISJOINT** : 3 sous-réseaux, 3 Adam, losses séparées (référence). Via `_train_arm("disjoint", ...)`.
- **FLAT_PERHEAD** (NOUVEAU) : `FlatModel` (archi PLATE identique, même init au seed), **3 optimiseurs Adam** sur
  `model.parameters()` (tous les params, trunc partagé), **un par tête**, `lr=LR`. Par step : **1 forward**, puis
  pour chaque tête `k` — `opt_k.zero_grad(set_to_none=True)` → `ls[k].backward(retain_graph=(k < N_HEADS-1))` →
  `opt_k.step()`. Les 3 gradients sont évalués au **même point** (forward unique + `retain_graph`), appliqués en
  **séquence**, chacun avec les moments `m`/`v` **propres** de son Adam.

**Différence unique** avec FLAT_NORM (153) : moments séparés au lieu d'échelle de loss.
**Différence unique** avec DISJOINT : trunc **partagé** (pas de split architectural).

## 3. Verdict pré-enregistré (gelé avant le run)

Mêmes seeds que 153 pour comparabilité directe : **K=5, base=2200, STEPS=2000**.

`recovery_v3_k = (FLAT_k − FLATPERHEAD_k) / (FLAT_k − DISJOINT_k)`, moyenné sur les têtes MSE {value, pred}, par
seed (formule identique à 153, réutilise `_recovery`).

- **OPTIMIZER_CONFIRMED** si `recovery ≥ 0.90` sur ≥ 3/5 seeds → les moments Adam séparés ferment le résidu →
  **architecture réfutée à ~100 % comme levier** (le résidu ~21 % était l'optimiseur, pas la topologie).
- **REFUTED** si `recovery ≤ 0.79` sur ≥ 3/5 → les moments séparés ne font **pas mieux** que l'échelle de loss
  (153) → le résidu résiste aux **deux** leviers non-architecturaux pris isolément → la borne haute architecturale
  (~21 %) tient (non tranché à 100 % : un bras combiné échelle+moments le fermerait).
- **PARTIAL** sinon.

## 4. Interprétation (les 3 issues)

- **OPTIMIZER_CONFIRMED** : avec 153, les deux facteurs non-archi (échelle 79 %, moments ~100 %) recouvrent le gain
  → l'audit #5 (têtes disjointes) est **réfuté à 100 % comme levier** ; actionnable prod = crédit multi-tête
  (GradNorm/lr/moments-par-tête), jamais une refonte topologique.
- **REFUTED** : le résidu ~21 % n'est refermé par **aucun** levier non-archi seul → soit contribution
  architecturale réelle (borne ~21 %), soit **synergie** échelle×moments → suite = 5e bras FLAT_NORM+PERHEAD.
- **PARTIAL** : recouvrement intermédiaire, à rapporter tel quel avec la décomposition par tête (value vs pred).

## 5. Caveats (à graver dans l'EDR)

- **(a) Forward unique + `retain_graph`** : les 3 gradients sont évalués au **même point**, updates séquentiels
  (coordinate-blocked) — c'est l'analogue **plat** le plus proche de DISJOINT, **PAS** 3 trajectoires d'optimisation
  indépendantes (dans DISJOINT chaque sous-réseau a son propre forward). L'écart résiduel FLAT_PERHEAD↔DISJOINT
  peut donc inclure cette différence de trajectoire, pas seulement l'architecture.
- **(b) Ordre des têtes** : l'update de la tête 0 précède le backward de la tête 1 sur le trunc partagé ; l'ordre
  est fixe (action, value, pred) et identique à tous les seeds → n'affecte pas l'équité inter-bras, mais borne
  l'interprétation (effet d'ordre non isolé).
- **(c) Dénominateur petit** (`FLAT−DISJOINT` ~0.01–0.02) : hérité de 153 ; afficher le gain-152 par seed pour
  attester qu'aucun recovery n'est porté par un dénominateur dégénéré. Verdict par **comptage de seeds**, pas la
  moyenne.
- Hérite des caveats 152/153 : proxy supervisé teacher-student (pas in-world), profs quasi-orthogonaux, têtes non
  appariées.

## 6. Périmètre / tooling additif

- **Nouveau fichier** : `tools/disjoint_heads_v3.py`. Réutilise par **import** :
  - de `tools.disjoint_heads_ab` : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm,
    N_HEADS, HELDOUT, BATCH, STEPS, LR`.
  - de `tools.disjoint_heads_confound` : `_recovery` (calcul de recouvrement value+pred).
- **Nouveau test** : `tests/sandbox/test_disjoint_heads_v3.py` (smoke : K=1, steps réduits → verdict dans
  l'ensemble valide + `per_seed` présent).
- **NE modifie NI** `tools/disjoint_heads_ab.py` **NI** `tools/disjoint_heads_confound.py`, ni `src/`, ni le
  substrat torch (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil // torch).
- **Prints exécutés = ASCII-only** (cp1252 Windows) : accents seulement en docstrings.
- **Déterminisme** : `torch.set_num_threads(1)` + `use_deterministic_algorithms(True)` ; run en **2 passes
  byte-identiques**.

## 7. Interfaces produites

- `_train_flat_perhead(seed, teachers, steps=STEPS) -> dict` (eval dict `{action, value, pred}` via `_eval_losses`).
- `_verdict_v3(per_seed_recovery) -> str` (`OPTIMIZER_CONFIRMED` / `REFUTED` / `PARTIAL`, gelé §3).
- `_report_v3(rows, verdict, mean_rec) -> None` (report ASCII 3-bras + colonne gain-152).
- `main_v3_check(K=5, base=2200, steps=STEPS, _return=False) -> dict|None`
  (`{verdict, mean_recovery, per_seed}`).

## 8. Numérotation

**EDR 154** — bloc **150+** (convention `parallel-sessions-shared-tree` : per-type/ToM en 150+, fils // en
120-149). 7e instrument per-type, suite directe d'EDR 152/153.
