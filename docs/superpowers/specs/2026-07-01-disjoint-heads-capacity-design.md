# EDR 191 — Sous pression de capacité (H réduit), l'architecture compte-t-elle enfin ? (design)

> **Date** : 2026-07-01. **Fil** : têtes/facultés (per-type, bloc **190+** — collision 155, cf.
> `parallel-sessions-shared-tree`). Suite d'EDR 152/153/154/190.
> **Statut** : design approuvé (brainstorming), à implémenter en subagent-driven.

## 1. Contexte et question

Arc têtes disjointes :
- **152** : DISJOINT bat le plat (+43 %) mais cosinus-conflit ≈ 0 → interférence réfutée ; gain = optimiseur.
- **153/154** : le crédit-équilibrage plat (échelle de loss / moments) recouvre ~75-79 % → **crédit, pas archi**.
- **190 (ex-155)** : corréler les profs **n'induit PAS** de conflit de trunc (le readout linéaire absorbe le signe ;
  trunc H=48 **surdimensionné** = 3 tâches conjointement satisfiables). Corréler = **aide**, pas conflit.

**Le régime interférent n'a jamais été atteint** → la conclusion « archi ne compte pas » (153/154) reste peut-être
**bornée au régime sur-capacité**. **Correction d'une erreur de conception (EDR 190 §4)** : réduire H **uniformément**
PRÉSERVE la parité inter-bras (FLAT `D·H` et DISJOINT `3·(D·H/3)` scalent tous deux avec H). Donc **la capacité est le
vrai knob** : sous un trunc RARE (H petit), le substrat plat NE PEUT PAS servir toutes les têtes → les têtes se
disputent les dims → **vraie interférence**. EDR 191 teste : **quand la rareté force enfin le conflit (cosinus < 0),
le crédit-équilibrage plat (FLAT_NORM, 153) recouvre-t-il encore l'avantage DISJOINT, ou l'architecture compte-t-elle
enfin ?**

**Profs INDÉPENDANTS (152)** : 190 a montré que corréler AIDE (features partagées moins chères). Pour MAXIMISER le
conflit sous rareté, il faut des tâches DIVERSES qui se disputent des dims rares → on réutilise `_make_teachers`
(indépendants). Seule variable du sweep = **H** (la capacité).

## 2. Mécanisme — sweep de capacité H, parité inter-bras préservée

`disjoint_heads_ab` (152) **fige H=48** dans `FlatModel`/`DisjointModel`. On réimplémente localement des modèles
**paramétrés par H**, FIDÈLES au code revu de 152 (mêmes couches, même ordre → à H=48 l'init est byte-identique à
152) :
- `FlatModelH(H)` : `trunk = Linear(D, H)`, `head_action = Linear(H, K_A)`, `head_value = Linear(H, 1)`,
  `head_pred = Linear(H, P_PRED)`. Ordre des couches IDENTIQUE à `FlatModel` (152).
- `DisjointModelH(H)` : `w = H // N_HEADS` ; `trunk_action/value/pred = Linear(D, w)` puis
  `head_action/value/pred = Linear(w, K_A/1/P_PRED)`. Ordre IDENTIQUE à `DisjointModel` (152).
  `head_param_groups()` : 3 groupes `[trunk_k + head_k]`.
- **Contrainte** : H divisible par N_HEADS(=3). Parité de params trunc à tout H : FLAT `D·H` = DISJOINT
  `3·(D·(H/3))`.

Trois bras paramétrés par H, FIDÈLES à 152/153 (même seed order `manual_seed → np.seed → held → model`, mêmes graines
`held=seed+10_000`, `batch=seed*1_000_003+t`) :
- `FLAT` : trunc partagé, loss combinée `(la+lv+lp)`, 1 Adam ; renvoie `(eval, cos)`.
- `DISJOINT` : 3 sous-réseaux, 3 Adam, losses séparées (`retain_graph`) ; renvoie `(eval, None)`.
- `FLAT_NORM` : plat + équilibrage d'échelle de loss GradNorm-lite (EMA, `w_k=1/EMA(loss_k)`), 1 Adam ; renvoie
  `eval`. **Fidèle à `_train_flat_norm` (153)**.
- `_interference_cosine_h(model, batch)` : cosinus moyen des 3 gradients par-tête w.r.t. `model.trunk.weight`
  (FLAT). Fidèle à `_interference_cosine` (152).

## 3. Sweep et bras

- **H ∈ {48, 6, 3}** ; **K=5**, base=2200 (comparabilité seeds avec 152-154). H=48 = **sanity** (doit reproduire
  152/153 au chiffre — init/arms identiques).
- Par `(H, seed)` : `FLAT` (+cos), `DISJOINT`, `FLAT_NORM` ; `improv=_seed_improv(flat,disj)` (152),
  `recovery=_recovery(flat,flatnorm,disj)` (153), `cos`.

## 4. Verdict pré-enregistré (gelé), 2 axes mesurés à H=3 (capacité minimale)

`maj = K//2 + 1 = 3`.
- **Axe A — interférence** : `cos(seed)` à H=3. **`INDUCED`** si `cos ≤ −0.05` sur ≥3/5 ; sinon **`NOT_INDUCED`**.
- **Axe B — robustesse du crédit** : `recovery(seed)` à H=3. **`CREDIT_ROBUST`** si `recovery ≥ 0.50` sur ≥3/5 ;
  **`ARCH_MATTERS`** si `recovery ≤ 0.20` sur ≥3/5 ; sinon **`CREDIT_PARTIAL`**.
- **Verdict combiné** = `f"{A}+{B}"`.

## 5. Interprétation (les issues)

- **`INDUCED+CREDIT_ROBUST`** : même sous vraie interférence (rareté), le crédit-équilibrage **plat** recouvre
  l'avantage disjoint → **la conclusion 153/154 tient sous interférence** ; l'archi reste non nécessaire (le plus fort).
- **`INDUCED+ARCH_MATTERS`** : sous rareté, le crédit plat échoue et l'avantage disjoint survit → **l'isolation
  architecturale compte enfin** → conclusion 153/154 **bornée au régime sur-capacité** ; la migration devrait
  reconsidérer #5 quand les facultés se disputent une capacité rare (le plus surprenant / important).
- **`INDUCED+CREDIT_PARTIAL`** : intermédiaire, rapporté tel quel avec la courbe cos(H) et improv(H).
- **`NOT_INDUCED+*`** : même la rareté extrême (H=3) ne fait pas passer le cosinus `∂L/∂trunk.weight` sous −0.05 →
  la sonde reste absorbée par le readout même sous capacité minimale → borne la question (pointe vers une sonde
  `∂L/∂h` pré-readout comme seule voie), et renforce que le conflit de trunc mesuré n'est pas le mécanisme.

## 6. Caveats (à graver dans l'EDR)

- **(a)** À H=3, DISJOINT donne 1 seul neurone caché par tête (`w=1`) : régime extrême ; l'avantage/désavantage à
  H=3 peut refléter cette granularité autant que l'interférence — lire la **tendance** cos(H) sur les 3 points.
- **(b)** La sonde reste `∂L/∂trunk.weight` (comme 152/190) → si NOT_INDUCED persiste, cela ne prouve pas l'absence
  de conflit de représentation (le readout peut absorber même sous rareté) ; sonde `∂L/∂h` = piste future.
- **(c)** Sanity H=48 : les colonnes FLAT/DISJOINT à H=48 DOIVENT reproduire 152/153 seed-à-seed (init/arms
  identiques) — à vérifier/rapporter comme attestation de fidélité de la réimplémentation.
- **(d)** dénominateur recovery petit (protégé par comptage de seeds + colonne gain FLAT−DISJ). Hérite 152/153
  (proxy supervisé, têtes non appariées).

## 7. Périmètre / tooling additif

- **Nouveau fichier** : `tools/disjoint_heads_capacity.py`. Réutilise par **import** (H-indépendants) :
  - de `tools.disjoint_heads_ab` : `torch, nn, F, _make_teachers, _make_data, _losses, _eval_losses, _seed_improv,
    D, K_A, P_PRED, N_HEADS, TEACHER_SEED, HELDOUT, BATCH, STEPS, LR`.
  - de `tools.disjoint_heads_confound` : `_recovery`.
  - `numpy as np`.
- **Réimplémentés localement** (car H figé dans 152) : `FlatModelH`, `DisjointModelH`, `_train_arm_h`,
  `_train_flat_norm_h`, `_interference_cosine_h`.
- **Nouveau test** : `tests/sandbox/test_disjoint_heads_capacity.py` (unit verdict + unit models H-parity + smoke).
- **NE modifie NI** `disjoint_heads_ab.py` **NI** `disjoint_heads_confound.py`, ni `src/`, ni le substrat torch
  (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil // torch).
- **Prints exécutés = ASCII-only** (cp1252) ; accents seulement en docstrings.
- **Déterminisme** : `set_num_threads(1)` + `use_deterministic_algorithms(True)` ; run en **2 passes byte-identiques**.

## 8. Interfaces produites

- `FlatModelH(H) -> nn.Module` (`forward(x)->(a,v,p)`) ; `DisjointModelH(H) -> nn.Module`
  (`forward`, `head_param_groups()`).
- `_train_arm_h(arm, seed, teachers, H, steps=STEPS) -> (eval_dict, cos_or_None)` (`arm in {"flat","disjoint"}`).
- `_train_flat_norm_h(seed, teachers, H, steps=STEPS) -> eval_dict`.
- `_interference_cosine_h(model, batch) -> float`.
- `_verdict_capacity(cos_list, recovery_list) -> str` (combiné `{A}+{B}`, seuils §4, gelé).
- `_report_capacity(h_rows) -> None` ; `main_capacity_check(K=5, base=2200, Hs=(48,6,3), steps=STEPS,
  _return=False) -> dict|None` (`{verdict, per_H, h_min}`).

## 9. Numérotation

**EDR 191** — bloc **190+** (per-type disjoint extension, post-collision). 9e instrument per-type, suite d'EDR
152/153/154/190.
