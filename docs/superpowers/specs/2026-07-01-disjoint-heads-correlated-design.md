# EDR 155 (V2) — Profs corrélés : l'interférence induite change-t-elle la conclusion « crédit, pas archi » ? (design)

> **Date** : 2026-07-01. **Fil** : têtes/facultés (per-type, bloc 150+). Suite d'EDR 152/153/154.
> **Statut** : design approuvé (brainstorming), à implémenter en subagent-driven.

## 1. Contexte et question

Arc têtes disjointes (per-type, #5 de l'audit) :
- **EDR 152** : DISJOINT (3 sous-réseaux) bat le plat (+43 %) MAIS cosinus-conflit inter-têtes ≈ 0 → **interférence
  réfutée** ; le gain = conditionnement d'optimiseur.
- **EDR 153** : FLAT_NORM (plat + équilibrage d'échelle de loss) recouvre 79 % du gain → **crédit, pas archi**.
- **EDR 154** : les moments Adam par-tête recouvrent comme l'échelle (0.73) → résidu = optimiseur de 2nd ordre.

**Caveat I2 (152)** : les 3 profs étaient des MLP **indépendants** (tirages `rng` séparés) → cibles
quasi-orthogonales → **aucune interférence à trouver**. La conclusion « archi ne compte pas » est donc peut-être
**bornée au régime orthogonal**. V2 teste cette prémisse : **induire une vraie interférence** (profs corrélés) et
re-poser la question décisive — quand les gradients par-tête se contredisent réellement (cosinus < 0), l'avantage
DISJOINT reste-t-il recouvré par le crédit-équilibrage **plat** (FLAT_NORM), ou l'**architecture** se met-elle enfin
à compter ?

**Nuance mécaniste (vérifiée en lisant le code)** : le cosinus se mesure sur le gradient du **trunc partagé**. Des
readout linéaires (`nn.Linear(H,out)`) absorbent toute relation linéaire/de signe entre tâches → un simple
sous-espace partagé tend à **aligner** les gradients (cos>0), pas à les opposer. On structure donc ρ avec des
**signes opposés par tête** sur la composante commune. **« Le cosinus devient-il vraiment négatif » reste la question
empirique auto-validante** du sweep : un null (`NOT_INDUCED`) serait lui-même informatif (la corrélation seule ne
crée pas de conflit dans un trunc surdimensionné → renforce 152/153/154).

## 2. Mécanisme — profs corrélés par sous-espace partagé signé (ρ)

`_make_correlated_teachers(rho, seed=TEACHER_SEED)` renvoie le **même format** que `_make_teachers`
(`{"action":(w1,w2), "value":(w1,w2), "pred":(w1,w2)}`, w1 de forme `(D,16)`, w2 de forme `(16,out)`), donc
`_teacher_forward`/`_targets`/`_make_data` (152) marchent **inchangés**.

Construction (numpy `default_rng(seed)`, cibles reproductibles, indépendantes du seed d'entraînement) :
- Tirer une direction **commune** `w1_common` `(D,16)` et 3 directions **indépendantes** `w1_indep_k` `(D,16)`.
- Signes fixes par tête `SIGMA = (+1, +1, -1)` (action/value alignées sur le commun, pred opposée → au moins une
  paire fortement contestée).
- `w1_k(ρ) = colnorm( sqrt(1-ρ)·w1_indep_k + sqrt(ρ)·SIGMA[k]·w1_common )` où `colnorm` renormalise chaque colonne
  à sa norme d'origine moyenne (garde l'échelle des features comparable à travers ρ).
- `w2_k` : tirages **indépendants** par tête (comme 152), non touchés par ρ.

À **ρ=0** → 3 `w1` indépendants (régime ~orthogonal ; NB : construction distincte de `_make_teachers`, donc ρ=0 est
la **baseline orthogonale de CE mécanisme**, pas byte-identique à 152 — sanity attendu : profil FLAT/DISJOINT et
cosinus proches de 152). À **ρ→1** → les 3 têtes lisent le même sous-espace avec signes opposés → conflit maximal
visé.

## 3. Sweep et bras

- **ρ ∈ {0.0, 0.6, 0.95}** ; **K=5**, base=2200 (comparabilité seeds avec 152/153/154).
- Par `(ρ, seed)`, 3 bras (tous via code existant, `teachers=_make_correlated_teachers(rho)`) :
  - **FLAT** : `_train_arm("flat", ...)` → renvoie `(eval, cos)` (cosinus du trunc partagé).
  - **DISJOINT** : `_train_arm("disjoint", ...)` → `(eval, None)`.
  - **FLAT_NORM** : `_train_flat_norm(...)` (153) → `eval`.
- Par `(ρ, seed)` : `improv = _seed_improv(flat, disj)` (152), `recovery = _recovery(flat, flatnorm, disj)` (153),
  `cos` (FLAT).

## 4. Verdict pré-enregistré (gelé avant le run), 2 axes mesurés à ρ=0.95

`maj = K//2 + 1 = 3`.

- **Axe A — interférence** : `cos_moyen(seed)` à ρ=0.95. **`INDUCED`** si `cos ≤ −0.05` sur ≥3/5 seeds ; sinon
  **`NOT_INDUCED`**.
- **Axe B — robustesse du crédit** : `recovery(seed)` à ρ=0.95. **`CREDIT_ROBUST`** si `recovery ≥ 0.50` sur ≥3/5 ;
  **`ARCH_MATTERS`** si `recovery ≤ 0.20` sur ≥3/5 ; sinon **`CREDIT_PARTIAL`**.
- **Verdict combiné** = `f"{A}+{B}"` (ex. `NOT_INDUCED+CREDIT_ROBUST`, `INDUCED+ARCH_MATTERS`).

## 5. Interprétation (les issues)

- **`NOT_INDUCED+*`** : la corrélation de profs ne crée pas de conflit de trunc mesurable (readout linéaire absorbe /
  trunc H=48 surdimensionné) → 152 (cos≈0) **robuste**, la conclusion « archi ne compte pas » n'est PAS un artefact
  du régime orthogonal (aucun régime de conflit atteint par corrélation seule). Renforce 152/153/154.
- **`INDUCED+CREDIT_ROBUST`** : même quand les gradients se contredisent vraiment, le crédit-équilibrage **plat**
  recouvre l'avantage disjoint → **la conclusion 153/154 tient sous interférence** ; l'archi reste non nécessaire.
- **`INDUCED+ARCH_MATTERS`** : sous vraie interférence, le crédit plat échoue et l'avantage disjoint survit →
  **l'isolation architecturale compte dans le régime interférent** → la conclusion 153/154 est **bornée au régime
  faible-conflit** ; la migration devrait reconsidérer #5 quand les facultés interfèrent. (Résultat le plus
  surprenant / le plus important.)
- **`INDUCED+CREDIT_PARTIAL`** : recouvrement intermédiaire, rapporté tel quel avec la courbe cos(ρ).

## 6. Caveats (à graver dans l'EDR)

- **(a)** Le knob ρ+signes est un *essai* d'induction ; le cosinus mesuré tranche s'il fonctionne (auto-validant).
- **(b)** Trunc H=48 surdimensionné → l'interférence peut ne pas biter même corrélé (le readout linéaire absorbe le
  signe ; le vrai conflit exige une pression de capacité, écartée pour préserver la parité de params trunc).
- **(c)** `SIGMA=(+1,+1,-1)` fixe et arbitraire ; d'autres motifs de signe non testés.
- **(d)** ρ=0 de CE mécanisme ≠ byte-identique à `_make_teachers` (152) ; sanity = proximité de profil, pas égalité.
- Hérite 152/153/154 : proxy supervisé teacher-student (pas in-world), têtes non appariées, dénominateur recovery
  petit (protégé par comptage de seeds + colonne gain FLAT−DISJOINT).

## 7. Périmètre / tooling additif

- **Nouveau fichier** : `tools/disjoint_heads_correlated.py`. Réutilise par **import** :
  - de `tools.disjoint_heads_ab` : `torch, np, FlatModel, _train_arm, _interference_cosine, _make_data,
    _seed_improv, D, TEACHER_SEED, N_HEADS, HELDOUT, BATCH, STEPS, LR`.
  - de `tools.disjoint_heads_confound` : `_train_flat_norm, _recovery`.
- **Nouveau test** : `tests/sandbox/test_disjoint_heads_correlated.py` (unit verdict + unit teachers-format + smoke
  du sweep).
- **NE modifie NI** `disjoint_heads_ab.py` **NI** `disjoint_heads_confound.py`, ni `src/`, ni le substrat torch
  (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil // torch).
- **Prints exécutés = ASCII-only** (cp1252) : accents seulement en docstrings.
- **Déterminisme** : `set_num_threads(1)` + `use_deterministic_algorithms(True)` ; run en **2 passes
  byte-identiques**.

## 8. Interfaces produites

- `_make_correlated_teachers(rho, seed=TEACHER_SEED) -> dict` (format `_make_teachers`).
- `_verdict_correlated(cos_list, recovery_list) -> str` (combiné `{A}+{B}`, seuils §4, gelé).
- `_report_correlated(rho_rows) -> None` (report ASCII : par ρ, moyennes cos/improv/recovery + colonnes par seed).
- `main_correlated_check(K=5, base=2200, rhos=(0.0, 0.6, 0.95), steps=STEPS, _return=False) -> dict|None`
  (`{verdict, per_rho, rho_max}`).

## 9. Numérotation

**EDR 155** — bloc **150+** (convention `parallel-sessions-shared-tree`). 8e instrument per-type, suite d'EDR
152/153/154.
