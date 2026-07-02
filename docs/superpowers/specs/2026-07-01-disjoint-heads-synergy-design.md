# EDR 192 (V4) — La synergie échelle×moments ferme-t-elle le résidu ~21 % (archi réfutée à ~100 %) ? (design)

> **Date** : 2026-07-01. **Fil** : têtes/facultés (per-type, bloc 190+). Clôt le sous-arc optimiseur d'EDR 153/154.
> **Statut** : design approuvé (brainstorming), à implémenter en subagent-driven.

## 1. Contexte et question

Sous-arc optimiseur des têtes disjointes :
- **EDR 153** : FLAT_NORM (plat, 1 Adam, **échelle de loss** GradNorm-lite) recouvre **0.79** du gain DISJOINT.
- **EDR 154** : FLAT_PERHEAD (plat, **3 Adam à moments propres**, sans échelle) recouvre **0.73** — comme l'échelle,
  pas mieux. Résidu ~21 % non fermé par l'un OU l'autre levier non-architectural pris seul.

**Question** : les deux leviers non-archi **combinés** ferment-ils le résidu ? Un 5e bras **FLAT_NORM_PERHEAD**
(plat + 3 Adam **ET** échelle de loss) recouvre-t-il ≥ 0.90 (→ archi réfutée à ~100 % comme levier), ou reste-t-il au
niveau des leviers seuls (~0.75 → le ~21 % est architectural / trajectoire, et/ou les deux leviers sont redondants) ?

**Nuance mécaniste (à graver)** : l'Adam par-tête **normalise déjà par-tête** (via son second moment `v`) → ajouter
l'échelle de loss `w_k` par-dessus peut être **largement redondant** (même effet de rééquilibrage de crédit). Un
`NO_SYNERGY` serait alors la lecture attendue : les deux leviers agissent sur le même canal (le crédit par-tête), pas
sur deux canaux complémentaires.

## 2. Bras (Commandement 15 — seule variable = optimiseur, pas l'architecture)

Mêmes profs/données/seeds/init que 152/153/154 (`manual_seed(seed)` → `np.random.seed(seed)` → `FlatModel()`,
graines `held=seed+10_000`, `batch=seed*1_000_003+t`).
- **FLAT** : trunc partagé, loss combinée, 1 Adam (baseline). Via `_train_arm("flat", ...)` (152).
- **DISJOINT** : 3 sous-réseaux, 3 Adam, losses séparées (référence). Via `_train_arm("disjoint", ...)` (152).
- **FLAT_NORM_PERHEAD** (NOUVEAU) : `FlatModel` (archi PLATE identique, même init au seed), **N_HEADS optimiseurs
  Adam** (un par tête, moments propres) sur `model.parameters()`, **ET** échelle de loss EMA (GradNorm-lite de 153).
  Forward unique ; EMA sur les pertes détachées → poids `w_k = 1/(EMA(loss_k)+1e-8)` normalisés (moyenne 1) ; par tête
  `k` : `opt_k.zero_grad(set_to_none=True)` → `(w_k · ls_k).backward(retain_graph=(k < N_HEADS-1))` → `opt_k.step()`.
  Combine **strictement** les deux leviers : moments séparés (154) ET échelle (153).

**Différence unique** avec FLAT_PERHEAD (154) : ajout de l'échelle `w_k`. **Différence unique** avec FLAT_NORM (153) :
moments séparés (3 Adam) au lieu de 1 Adam. **Différence unique** avec DISJOINT : trunc partagé (pas de split archi).

## 3. Verdict pré-enregistré (gelé), mesuré à K=5, base=2200

`recovery_k = (FLAT_k − FLATNORM_PERHEAD_k)/(FLAT_k − DISJOINT_k)`, moyenné sur têtes MSE {value, pred}, par seed
(formule identique à 153/154, réutilise `_recovery`).
- **SYNERGY_CLOSES** si `recovery ≥ 0.90` sur ≥ 3/5 → les deux combinés ferment le résidu → **architecture réfutée à
  ~100 % comme levier** (tout le gain DISJOINT est capturable par du crédit plat).
- **NO_SYNERGY** si `recovery ≤ 0.79` sur ≥ 3/5 → pas mieux que l'échelle seule (153) → le résidu ~21 % **résiste aux
  leviers non-archi même combinés** (architectural / trajectoire, et/ou les deux leviers redondants sur le même canal
  de crédit).
- **PARTIAL** sinon.

## 4. Interprétation (les issues)

- **SYNERGY_CLOSES** : clôt le sous-arc optimiseur — l'union des deux leviers non-archi capture ~tout le gain →
  l'audit #5 (têtes disjointes) est **réfuté à 100 % comme levier** ; le résidu de 153/154 était la conjonction
  échelle+moments, pas l'architecture. Renforce maximalement la migration « crédit multi-tête, pas refonte ».
- **NO_SYNERGY** : les deux leviers sont **redondants** (même canal de crédit par-tête) OU le résidu ~21 % est
  irréductiblement architectural/trajectoire (borne haute ~21 %). Cohérent avec la nuance §1 (Adam par-tête normalise
  déjà). Le sous-arc reste ouvert sur « ~21 % non-attribué », mais **la conclusion de fond est INCHANGÉE** (191 a déjà
  tranché que l'archi n'est pas le levier, même sous interférence).
- **PARTIAL** : recouvrement intermédiaire, rapporté tel quel avec la décomposition par tête.

## 5. Caveats

- **(a) Redondance attendue** : Adam par-tête normalise déjà par-tête (via `v`) → l'échelle `w_k` peut n'ajouter
  presque rien ; `NO_SYNERGY` ne signifie PAS « archi compte » (191 l'a réfuté), mais « les 2 leviers non-archi
  agissent sur le même canal ».
- **(b) Forward unique + retain_graph** (comme 154) : les 3 gradients au même point, updates séquentiels
  (coordinate-blocked), pas 3 trajectoires indépendantes.
- **(c) Dénominateur recovery petit** (`FLAT−DISJOINT` ~0.01–0.02) : protégé par comptage de seeds + colonne gain-152
  par seed dans le report.
- **(d)** `lr` partagé entre les 3 Adam. Hérite 152/153/154 (proxy supervisé, têtes non appariées).

## 6. Sanity (à vérifier au run)

Les colonnes FLAT et DISJOINT (via `_train_arm`, code identique) doivent reproduire 153/154 **seed-à-seed** (mêmes
seeds base=2200) → atteste la comparabilité d'environnement et que le recovery est directement comparable à 153/154.

## 7. Périmètre / tooling additif

- **Nouveau fichier** : `tools/disjoint_heads_synergy.py`. Réutilise par **import** :
  - de `tools.disjoint_heads_ab` : `torch, FlatModel, _make_teachers, _make_data, _losses, _eval_losses, _train_arm,
    N_HEADS, HELDOUT, BATCH, STEPS, LR`.
  - de `tools.disjoint_heads_confound` : `_recovery`.
  - `numpy as np`.
- **Nouveau test** : `tests/sandbox/test_disjoint_heads_synergy.py` (unit verdict + smoke du bras + smoke main).
- **NE modifie NI** `disjoint_heads_ab.py` **NI** `disjoint_heads_confound.py`, ni `disjoint_heads_v3.py`, ni
  `disjoint_heads_correlated.py`, ni `disjoint_heads_capacity.py`, ni `src/`, ni le substrat torch
  (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil // torch).
- **Prints exécutés = ASCII-only** (cp1252) ; accents seulement en docstrings.
- **Déterminisme** : `set_num_threads(1)` + `use_deterministic_algorithms(True)` ; run en **2 passes byte-identiques**.

## 8. Interfaces produites

- `_train_flat_norm_perhead(seed, teachers, steps=STEPS, decay=0.99) -> dict` (eval `{action,value,pred}`).
- `_verdict_v4(per_seed_recovery) -> str` (`SYNERGY_CLOSES` / `NO_SYNERGY` / `PARTIAL`, seuils §3, gelé).
- `_report_v4(rows, verdict, mean_rec) -> None` (report ASCII 3-bras + colonne gain-152).
- `main_v4_check(K=5, base=2200, steps=STEPS, _return=False) -> dict|None` (`{verdict, mean_recovery, per_seed}`).

## 9. Numérotation

**EDR 192** — bloc **190+** (per-type disjoint extension). 10e instrument per-type, clôt le sous-arc optimiseur
d'EDR 153/154 (l'arc de fond étant déjà clos par 191).
