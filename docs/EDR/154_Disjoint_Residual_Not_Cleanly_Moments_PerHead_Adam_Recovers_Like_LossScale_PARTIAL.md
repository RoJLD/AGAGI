# EDR 154 (V3) — Le résidu ~21 % d'EDR 153 n'est PAS proprement « les moments Adam séparés » : l'Adam-par-tête recouvre comme l'échelle de loss (PARTIAL, recovery 0.73)

> **Date** : 2026-07-01. **Verdict pré-enregistré** : `recovery_k = (FLAT_k − FLATPERHEAD_k)/(FLAT_k − DISJOINT_k)`
> moyenné sur têtes MSE {value, pred}, par seed. `OPTIMIZER_CONFIRMED` si `recovery ≥ 0.90` majorité ; `REFUTED` si
> `≤ 0.79` majorité ; sinon `PARTIAL`.
> **Résultat** : **PARTIAL** (recovery moyen **+0.729** ; 1 seed ≥0.90, 2 seeds ≤0.79, aucune majorité). Les
> moments Adam séparés (bras plat FLAT_PERHEAD) recouvrent le gain DISJOINT **au même niveau que l'échelle de loss**
> d'EDR 153 (~0.79), **pas mieux** — donc le résidu ~21 % de 153 n'est PAS proprement attribuable aux seuls moments.
> **Outil** : `tools/disjoint_heads_v3.py` (réutilise `disjoint_heads_ab` EDR 152 + `_recovery` EDR 153). **Run** :
> K=5, base=2200, STEPS=2000, `set_num_threads(1)`, `use_deterministic_algorithms(True)`, **2 passes
> byte-identiques**. **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-01-disjoint-heads-v3*`.

## 1. Question — trancher le résidu ~21 % d'EDR 153

EDR 152 : les têtes disjointes battent le plat (+43 %) sans interférence (cos≈0) → suspicion optimiseur.
EDR 153 : FLAT_NORM (plat, **1 Adam**, équilibrage d'échelle de loss GradNorm-lite) recouvre **79 %** du gain
DISJOINT → CONFOUND_CONFIRMED, **résidu ~21 %** (tête pred) non recouvré. Le gain DISJOINT a trois contributeurs
possibles : **(a)** équilibrage de crédit/échelle, **(b)** moments Adam séparés, **(c)** isolation architecturale.
153 a montré **(a) seul → 79 %**, bornant **(c) ≤ 21 %**. **V3 teste (b)** : les moments Adam séparés ferment-ils le
résidu ?

**Bras FLAT_PERHEAD** (Commandement 15, seule variable = optimiseur) : `FlatModel` (archi PLATE identique, même
init au seed), **3 optimiseurs Adam** sur `model.parameters()` (trunc partagé), un par tête, **sans** échelle de
loss. Forward unique, puis par tête `k` : `zero_grad(set_to_none=True)` → `backward(retain_graph=k<2)` → `step()`.
- vs FLAT_NORM (153) : archi/seeds/données identiques ; seule différence = **moments séparés au lieu d'échelle**.
- vs DISJOINT : optimiseur par-tête identique ; seule différence = **trunc partagé au lieu de split archi**.

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  seed | FLAT v/p     | FLAT_PH v/p   | DISJOINT v/p  | recovery | gain-152 v/p
  2200 | 0.027 0.027 | 0.010 0.012 | 0.010 0.011 | +0.977  | 0.017 0.015
  2201 | 0.025 0.027 | 0.012 0.010 | 0.006 0.010 | +0.813  | 0.018 0.018
  2202 | 0.016 0.031 | 0.018 0.013 | 0.006 0.014 | +0.406  | 0.010 0.017
  2203 | 0.028 0.036 | 0.022 0.011 | 0.010 0.011 | +0.646  | 0.018 0.025
  2204 | 0.025 0.030 | 0.014 0.009 | 0.008 0.008 | +0.802  | 0.017 0.022
  MOYEN recovery=+0.729
  VERDICT : PARTIAL
```

**Sanity de comparabilité (caveat opus M3) : les colonnes FLAT et DISJOINT reproduisent EXACTEMENT celles d'EDR 153
seed-à-seed** (FLAT 2200 = 0.027/0.027, DISJOINT 2200 = 0.010/0.011, …, les 5 seeds identiques) — `_train_arm` est
le même code, donc l'égalité atteste que l'environnement torch/BLAS n'a pas bougé et que le recovery de V3 est
directement comparable à 153. Gain-152 franc sur les 5 seeds (0.010–0.025) → verdict non dominé par un dénominateur
dégénéré.

## 3. Lecture

1. **PARTIAL, penche vers « pas mieux que l'échelle ».** Recovery moyen **0.729** vs FLAT_NORM **0.792** (153) : les
   moments Adam séparés recouvrent **au même niveau** que l'équilibrage d'échelle, avec **plus de variance**
   (0.41–0.98 vs des recoveries plus serrés en 153). **Le résidu ~21 % de 153 n'est donc PAS proprement fermé par
   les moments séparés** — sinon on aurait vu recovery≥0.90 en majorité. Formellement PARTIAL (1 seed ≥0.90, 2 ≤0.79).
2. **Les deux leviers non-architecturaux sont ~interchangeables (~73–79 %), aucun ne ferme seul le résidu.**
   Échelle de loss (153) et moments par-tête (154) recouvrent chacun ~3/4 du gain DISJOINT ; le résidu ~21–27 %
   **résiste aux deux quand ils sont appliqués isolément**. Cela n'établit PAS une contribution architecturale (2
   seeds recouvrent bien, ≥0.80), mais ne l'exclut pas non plus.
3. **Migration #5 : conclusion INCHANGÉE et renforcée.** L'actionnable prod reste un **équilibrage de crédit
   multi-tête** dans le substrat plat — que ce soit par échelle de loss OU par moments/optimiseur par-tête, les deux
   recouvrent l'essentiel sans aucun split architectural. **La refonte en têtes disjointes n'est pas le levier
   nécessaire** (un substrat plat + un mécanisme de crédit par-tête suffit à ~75 %). Le résidu est une question
   d'optimiseur de **second ordre** (probable synergie échelle×moments), pas d'architecture.

## 4. Boucle EDR 152 → 153 → 154

- **152** : disjoint aide (+43 %) mais cos≈0 → interférence réfutée ; suspicion optimiseur.
- **153** : échelle de loss (plat, 1 Adam) recouvre 79 % → crédit, pas topologie. Résidu ~21 %.
- **154** : moments par-tête (plat, 3 Adam) recouvrent 73 % — **comme** l'échelle, pas mieux → le résidu n'est pas
  proprement « les moments seuls ». Les deux leviers non-archi sont interchangeables ; le résidu ~21–27 % est un
  effet de second ordre (synergie / non-tranché).

Converge avec l'arc substrat : le verrou transverse est le **régime d'apprentissage/crédit**, pas la structure —
même signature que le binding (EDR 130/133/136) et la mémoire (EDR 123).

## 5. Caveats

- **(a) Forward unique + `retain_graph`** : les 3 gradients sont évalués au **même point**, updates séquentiels
  (coordinate-blocked) — analogue **plat** le plus proche de DISJOINT, PAS 3 trajectoires d'optim indépendantes.
- **(a′) Le levier testé = « régime d'optimisation par-tête » = moments propres ET N_HEADS updates séquentiels du
  trunc partagé par step** (revue opus I1). Ce n'est **pas** l'effet des moments `m`/`v` isolés d'un seul pas : en
  FLAT le trunc reçoit 1 update/step sur `(la+lv+lp)`, en FLAT_PERHEAD il en reçoit 3 (un par loss). `recovery`
  mesure l'effet joint moments+fréquence, à nommer comme tel.
- **(b) `lr` partagé** entre les 3 Adam (revue opus I2) — équitable vs DISJOINT (même `lr`), mais le **lr-par-tête**
  reste un levier distinct **non testé** ici.
- **(c) Ordre fixe des têtes** (action, value, pred), identique à tous les seeds et à DISJOINT → n'affecte pas
  l'équité, mais effet d'ordre non isolé.
- **(d) Dénominateur petit** (`FLAT−DISJOINT` ~0.01–0.02) : traité par verdict au **comptage de seeds** (pas la
  moyenne) + colonne gain-152 par seed (franc sur les 5) + garde `|denom|<1e-9` de `_recovery`.
- Hérite des caveats 152/153 : proxy supervisé teacher-student (pas in-world), profs quasi-orthogonaux, têtes non
  appariées.

## 6. Suite

- **V4 (proposée)** : 5e bras **FLAT_NORM + PERHEAD** (plat, échelle de loss **ET** moments par-tête) → teste la
  **synergie** : si l'union des deux leviers non-archi ferme le résidu (recovery→1.0), l'architecture est réfutée à
  ~100 % ; sinon la part résiduelle (~20 %) est architecturale ou un effet de trajectoire (§5a).
- **Actionnable prod (inchangé)** : embarquer un **équilibrage de crédit multi-tête** (échelle de loss / moments
  par-tête / lr-par-tête — tous ~équivalents à ~75 %), **jamais** une refonte en têtes disjointes.

## 7. Provenance / non-périmètre

- `tools/disjoint_heads_v3.py` (`main_v3_check`, K=5, base=2200, STEPS=2000, `set_num_threads(1)`,
  `use_deterministic_algorithms(True)`) ; **2 passes byte-identiques** ; AUCUN test relancé après le run.
- **Tooling ADDITIF** : nouveau fichier + test + spec/plan/EDR uniquement ; `src/` VIDE ; `disjoint_heads_ab.py`
  (EDR 152) et `disjoint_heads_confound.py` (EDR 153) **intacts** (réutilisés par import, non modifiés). Ne touche NI
  `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil torch //).
- Subagent-driven : 2 tâches (SPEC conforme + qualité Approved chacune), revue finale **opus** (validité du
  contrôle) : **PRÊT À INTÉGRER OUI, 0 Critical**, mécanisme 3-Adam vérifié empiriquement propre (moments séparés
  réels, zéro état croisé, `set_to_none` correct), équité 1-variable confirmée, caveats I1/I2/M3 gravés en §5.
- **Numérotation** : EDR 154 — bloc **150+** (convention `parallel-sessions-shared-tree`). 7e instrument per-type,
  suite directe d'EDR 152/153.
