# EDR 194 — Le lr adaptatif par-tête est le bouton de crédit qu'Adam n'annule pas : il SUR-récupère le gain des têtes disjointes (LR_CLOSES)

> **Date** : 2026-07-09. **Fil** : têtes disjointes / typologie d'intelligence (extension, bloc 190+).
> **Verdict pré-enregistré** (gelé, seuils calqués sur 192) : `LR_CLOSES` (recovery ≥ 0.90 majorité) /
> `LR_INTERCHANGEABLE` (≤ 0.79 majorité) / `PARTIAL`.
> **Résultat** : **LR_CLOSES**, et au-delà — **sur-récupération** : mean recovery **+1.364** (5/5 seeds
> 1.27–1.46). `FLAT_LR_PERHEAD` (têtes MSE v/p ≈ 0.003) bat non seulement `FLAT`-plain (≈ 0.027) mais **DISJOINT
> lui-même** (≈ 0.010).
> **Prédiction pré-enregistrée** (moi + revue opus) : `LR_INTERCHANGEABLE`/`PARTIAL` — **RÉFUTÉE par le run**.
> **Outil** : `tools/disjoint_heads_lr.py`. **Run** : K=5, base=2200, steps=2000, λ implicite, **2 passes
> byte-identiques**. **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-09-disjoint-heads-lr*`.

## 1. Question et méthode

L'arc têtes disjointes (152→192) a établi que le gain des sous-réseaux disjoints sur le substrat PLAT (trunc
partagé) est un **équilibrage de crédit** côté optimiseur, pas de l'isolation architecturale. Trois leviers *non-archi*
côté FLAT récupèrent le gain sans jamais le fermer : échelle de loss **0.79** (153), moments Adam par-tête **0.73**
(154), les deux combinés **0.70** (192, redondant).

Le point décisif d'EDR 192 : **« Adam par-tête annule le scaling »**. Adam est ~invariant d'échelle — scaler la loss
de la tête *k* par `c` scale son gradient par `c`, mais Adam divise par `√v ∝ c`, donc le pas est ~inchangé (ε→0).
C'est pourquoi 192 (scale + moments) ≈ 154 (moments seuls). **Il reste alors UN seul bouton de crédit qu'Adam ne
normalise PAS : le learning rate** — `lr` multiplie le pas *après* la normalisation à norme unité d'Adam :
`θ ← θ − (lr·w_k)·m̂/(√v̂+ε)`, et le `w_k` ne se simplifie pas.

Ce banc teste ce bouton. `_train_flat_lr_perhead` = clone **exact** de `_train_flat_norm_perhead` (192) à UNE ligne
près : au lieu de scaler la loss par `w_k`, on module le lr : `opts[k].param_groups[0]["lr"] = LR·w_k`, loss brute,
avec `w_k ∝ 1/EMA(loss_k)` normalisé `mean(w)=1`. `recovery = (flat − flat_lr)/(flat − disj)` sur les têtes MSE
{value, pred} (fonction `_recovery` de 153, directement comparable à 0.79/0.73/0.70).

**⚠️ Cadrage précis (crucial — cf. §3bis réconciliation avec EDR-COG-001).** Ce banc n'isole PAS un lr « pur ».
La structure vient de 192/154 : **N_HEADS Adam par-tête**, chacun possédant TOUS les params (trunc inclus), chacun
faisant un pas avec le gradient de SA tête. Le lr `w_k` module donc le pas de chaque Adam **sur le trunc partagé**
(que chaque Adam met à jour, 3 fois/pas). Donc EDR 194 = **154 (moments Adam par-tête) + lr adaptatif appliqué au
TRONC**. Ce n'est pas « lr vs loss » à l'état pur ; c'est « lr adaptatif sur le crédit du tronc, au-dessus des
moments par-tête ». La question « lr sur les *readouts* seuls suffit-il ? » est un bouton DIFFÉRENT, testé par la
session // (EDR-COG-001, ci-dessous) avec un résultat opposé — les deux se réconcilient.

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  seed | FLAT v/p     | FLAT_LR v/p   | DISJOINT v/p  | recovery
  2200 | 0.027 0.027 | 0.003 0.003 | 0.010 0.011 | +1.461
  2201 | 0.025 0.027 | 0.006 0.000 | 0.006 0.010 | +1.275
  2202 | 0.016 0.031 | 0.004 0.002 | 0.006 0.014 | +1.453
  2203 | 0.028 0.036 | 0.005 0.001 | 0.010 0.011 | +1.333
  2204 | 0.025 0.030 | 0.004 0.000 | 0.008 0.008 | +1.300
  MOYEN recovery=+1.364   ->   VERDICT : LR_CLOSES
```

Comparaison famille (recovery moyen du gain DISJOINT par le levier côté FLAT) :

| Levier (côté FLAT) | EDR | recovery |
|---|---|---|
| Échelle de loss (GradNorm-lite) | 153 | 0.79 |
| Moments Adam par-tête (3 Adam) | 154 | 0.73 |
| Échelle × moments | 192 | 0.70 |
| **Moments + lr adaptatif par-tête** | **194** | **1.36** |

## 3. Lecture

1. **LR_CLOSES, décisivement — et le résidu n'est PAS architectural.** Le bouton de crédit qu'Adam n'annule pas
   (le lr par-tête) franchit le seuil 0.90 sur les 5 seeds, sans ambiguïté. La prémisse d'EDR 192 (« Adam annule le
   scaling ») est **confirmée** : les leviers 153/154/192 plafonnaient ~0.7–0.79 *parce qu'*Adam neutralisait
   l'échelle ; le seul knob non neutralisé ferme le résidu.

2. **Sur-récupération : le FLAT+lr bat le DISJOINT lui-même (recovery > 1).** `recovery > 1` signifie
   `flat_lr < disj` : le trunc PARTAGÉ avec crédit par-tête équilibré (0.003) est **meilleur** que les sous-réseaux
   isolés (0.010). Lecture : DISJOINT découpe H=48 en 3×16 → chaque tête ne voit que 16 unités cachées ; FLAT donne
   à chaque tête les 48. Une fois le crédit équilibré par le lr, l'**avantage de capacité** du trunc partagé
   (48 vs 16) domine l'isolation. Donc non seulement l'isolation architecturale n'était pas nécessaire (arc
   152→192), mais elle est **contre-productive** ici : le bon bouton de crédit rend le partage strictement supérieur.

3. **Décomposition nette du crédit.** Moments Adam par-tête *seuls* (154, même structure, lr fixe) = 0.73 ; y
   ajouter le **lr adaptatif** par-tête (sur les mêmes Adams qui possèdent le trunc) = 1.36. Le saut 0.73 → 1.36
   isole le lr adaptatif **sur le tronc** comme le levier de crédit **décisif** — cohérent avec la théorie (Adam
   cancels loss-scaling, pas le lr). C'est le levier de crédit multi-tête le plus fort de tout l'arc.

## 3bis. Réconciliation avec EDR-COG-001 (session // T2/M1, `disjoint_heads_v4.py`)

En parallèle, la session // a testé un **autre** bouton lr-par-tête et obtenu le résultat **opposé en apparence** :
`LR_INSUFFICIENT` (recovery **−0.16**). Ce n'est PAS une contradiction — c'est **où** le lr agit :

| | EDR-COG-001 (// T2/M1) | **EDR 194 (ce banc)** |
|---|---|---|
| lr adaptatif agit sur | **readouts seuls** (trunc figé au lr de base) | **trunc + têtes** (N Adam par-tête possèdent le trunc) |
| moments | uniques (1 Adam à groupes) | **par-tête** (N Adam, = 154) |
| loss / backward | combinée, 1 backward | par-tête, N backwards |
| recovery | **−0.16** (LR_INSUFFICIENT) | **+1.36** (LR_CLOSES, over-recovery) |

**Les deux se renforcent** : COG-001 montre que rééchelonner le lr des **readouts** ne recouvre pas → *le conflit
inter-têtes vit dans le TRONC partagé, pas dans les têtes de lecture*. EDR 194 applique le lr adaptatif AU TRONC (via
les Adams par-tête qui le mettent à jour) → **sur-récupère**. Conclusion conjointe robuste : **le crédit qui compte
est celui du tronc partagé** ; un lr par-tête n'aide que s'il module le gradient du tronc (194), pas les readouts
(COG-001). Cohérent aussi avec 153 (échelle de loss, qui équilibre le gradient du tronc → 0.79) et 154 (moments sur
le tronc → 0.73). **La FORME du levier de crédit importe moins que sa CIBLE : le tronc.** EDR 194 est le premier à
montrer qu'un lr par-tête **sur le tronc** non seulement ferme le résidu mais dépasse le disjoint.

## 4. Portée — clôture forte de l'arc, bornée

- **Actionnable** : si un jour un équilibrage de crédit multi-tête est embarqué en prod (cf. synthèse arc têtes
  disjointes), viser **le gradient du TRONC partagé** (là où vit le conflit, §3bis + COG-001) : un **lr adaptatif
  par-tête sur le tronc** (∝ 1/EMA(loss_k), via optimiseurs par-tête) domine le loss-scaling et les moments et, sous
  crédit équilibré, le trunc **partagé** (plus de capacité par tête) bat le disjoint. ⚠️ Un lr par-tête **sur les
  readouts seuls** ne suffit PAS (EDR-COG-001, −0.16). Aucune refonte architecturale disjointe n'est justifiée
  (renforce EDR 152/153/154/190/191/192 ; complète COG-001).
- **Verdict d'interprétation gelé AVANT le run (revue opus)** : `LR_CLOSES` réfute l'archi ; l'issue symétrique
  `LR_INTERCHANGEABLE` aurait dit « le résidu résiste aux boutons de crédit *testés* », **pas** « le résidu est
  architectural » (espace des mécanismes de crédit non borné). Ici c'est LR_CLOSES : pas de sur-conclusion requise,
  l'archi est réfutée par un knob positif.
- **Borné (caveats)** :
  - **(a) Pertes absolues minuscules** (0.003–0.036) : le proxy teacher-student est facile ; les ratios sur
    quasi-zéro sont bruités en valeur. MAIS le motif est **robuste** (5/5 seeds recovery 1.27–1.46, 2 passes
    byte-identiques) → l'ordre `flat_lr < disj < flat` est stable dans ce banc.
  - **(b) `recovery > 1` sort de l'intervalle [0,1]** que la métrique « fraction du gain récupérée » présuppose
    (levier ∈ [disj, flat]). Le verdict `LR_CLOSES` (≥0.90) tire correctement ; mais la sur-récupération se lit
    comme « le levier dépasse DISJOINT », pas « >100 % d'un gain ». Rapporté tel quel (mean 1.36) sans normalisation.
  - **(c) Proxy supervisé** (pas de RL/monde) : le crédit y est propre ; en RL la variance de crédit confondrait
    (raison du proxy, cf. mem_nas EDR 064). L'avantage de capacité (48 vs 16) est spécifique à ce découpage
    `H//N_HEADS` ; un DISJOINT à capacité appariée n'est pas testé (borne).

## 5. Provenance / non-périmètre

- **Additif strict** : nouveau `tools/disjoint_heads_lr.py` + test + spec/plan/EDR uniquement ; `src/` intact
  (imports read-only de `disjoint_heads_ab` 152 + `disjoint_heads_confound` 153) ; siblings 152/153/192 **intacts**.
  Ne touche NI le fil torch // NI famine/Lewis.
- **Subagent-driven** : 2 tâches TDD (machinerie + runner), revue par-tâche (SPEC conforme + qualité Approved),
  **revue finale opus** = READY (prémisse vérifiée VRAIE — contraste EDR 193 dont la prémisse était fausse). Le seul
  point Important d'opus (le label `LR_INTERCHANGEABLE` sur-concluait « architectural ») a été **corrigé avant le
  run** (docstring + spec §3 durcis, verdict gelé inchangé). **Prédiction pré-enregistrée (moi + opus) RÉFUTÉE par le
  run** — 2ᵉ cas d'affilée (après EDR 193) où l'instrument tranche contre la prédiction, ce qui renforce la valeur du
  verdict gelé. Verdict figé avant exécution.
- **Numérotation** : EDR **194**, bloc **190+** (extension arc têtes disjointes ; 190/191/192 = correlated/capacity/
  synergy ; 193 = g bilinéaire, fil G4). Convention collisions : mémoire `parallel-sessions-shared-tree`.
