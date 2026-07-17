# EDR 153 — Le gain des têtes disjointes est un CONFOND D'ÉQUILIBRAGE DE CRÉDIT (CONFOUND_CONFIRMED 5/5, recovery 0.79) : un GradNorm-lite dans le substrat PLAT le recouvre → migration #5 réfutée comme levier

> **Date** : 2026-07-01. **Verdict pré-enregistré** : `recovery_k = (FLAT_k − FLATNORM_k)/(FLAT_k − DISJOINT_k)`
> moyenné sur les têtes MSE {value, pred}, par seed. `CONFOUND_CONFIRMED` si `recovery ≥ 0.50` sur ≥ 3/5 seeds ;
> `CONFOUND_REFUTED` si ≤ 0.20 ; sinon `PARTIAL`.
> **Résultat** : **CONFOUND_CONFIRMED** (5/5 seeds, recovery moyen **+0.79**) — un fix cheap côté FLAT
> (équilibrage d'échelle de loss, GradNorm-lite) recouvre ~79 % du gain de DISJOINT sans aucun changement
> architectural. **Le gain d'EDR 152 n'est PAS l'isolation de gradient ; c'est l'équilibrage de crédit.**
> **Outil** : `tools/disjoint_heads_confound.py` (réutilise `disjoint_heads_ab`, EDR 152). **Run** : K=5, base=2200,
> STEPS=2000, `set_num_threads(1)`, **2 passes byte-identiques**. **Spec/Plan** :
> `docs/superpowers/{specs,plans}/2026-07-01-disjoint-heads-confound*`.

## 1. Question — trancher le confond I1 d'EDR 152

EDR 152 : les têtes disjointes battent le substrat plat (+43 %) MAIS **sans interférence** (cosinus≈0), le gain
concentré sur les têtes MSE (value/pred), la tête action (CE) inchangée. Diagnostic suspecté (réserve opus I1) : le
levier n'est pas l'isolation architecturale mais le **conditionnement d'optimiseur par-tête** — « disjoint » bundle
(a) masque de poids, (b) séparation de loss, (c) 3 Adam à moments propres. Ce contrôle teste la version la plus
**cheap** de l'hypothèse crédit : un simple **équilibrage d'échelle de loss** dans le substrat PLAT recouvre-t-il
le gain ?

**Bras** (mêmes profs/données/seeds/init — Commandement 15, seule variable = pondération de loss entre FLAT et
FLAT_NORM) :
- **FLAT** : trunc partagé, loss combinée, 1 Adam (baseline).
- **DISJOINT** : 3 sous-réseaux, 3 Adam (référence EDR 152).
- **FLAT_NORM** : `FlatModel` (archi PLATE identique, même init au seed), **1 seul Adam**, mais losses **pondérées
  par tête** (GradNorm-lite : `w_k = 1/EMA(loss_k)`, normalisés à moyenne 1). Ne change QUE l'équilibrage d'échelle.

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  seed | FLAT v/p     | FLAT_NORM v/p | DISJOINT v/p  | recovery | gain-152 (FLAT-DISJOINT) v/p
  2200 | 0.027 0.027 | 0.010 0.015 | 0.010 0.011 | +0.872  | 0.017 0.016
  2201 | 0.025 0.027 | 0.010 0.015 | 0.006 0.010 | +0.733  | 0.019 0.017
  2202 | 0.016 0.031 | 0.009 0.020 | 0.006 0.014 | +0.701  | 0.010 0.017
  2203 | 0.028 0.036 | 0.010 0.019 | 0.010 0.011 | +0.830  | 0.018 0.025
  2204 | 0.025 0.030 | 0.008 0.016 | 0.008 0.008 | +0.825  | 0.017 0.022
  MOYEN recovery=+0.792
  VERDICT : CONFOUND_CONFIRMED
```

(La colonne gain-152 est ajoutée à l'interprétation, sur reco de la revue opus : le dénominateur du recovery est
ce gain, ~0.01–0.02 — **franc sur les 5 seeds**, donc le verdict n'est pas dominé par un dénominateur dégénéré.)

## 3. Lecture

1. **CONFOUND_CONFIRMED, net (5/5).** Un équilibrage d'échelle de loss dans le substrat **plat** (trunc partagé, un
   seul Adam) recouvre **~79 %** du gain de DISJOINT. **Le gain d'EDR 152 n'était donc PAS l'isolation
   architecturale** — c'était l'équilibrage de crédit entre facultés d'échelles différentes.
2. **Décomposition par tête** : la tête **value est quasi-intégralement recouvrée** (FLAT_NORM ~0.009 ≈ DISJOINT
   ~0.008), la tête **pred partiellement** (~65 % : FLAT_NORM ~0.017 vs FLAT ~0.030 vs DISJOINT ~0.011). Le résidu
   (~21 % en moyenne, concentré sur pred) est cohérent avec la part que FLAT_NORM ne réplique PAS : les **moments
   Adam SÉPARÉS** de DISJOINT (un `v` propre par sous-réseau), là où FLAT_NORM garde un Adam partagé. C'est **encore
   côté optimiseur/crédit, pas architecture**.
3. **Migration #5 réfutée comme levier.** La refonte « têtes disjointes + isolation de gradient » (audit #5,
   coûteuse) n'est PAS ce qui paie. Ce qui manque au substrat plat est l'**équilibrage du crédit d'apprentissage**
   entre facultés — capturable par un GradNorm-lite / lr-par-tête, bien moins cher et sans changer la topologie.

## 4. Boucle EDR 152 → 153 (fil têtes/facultés)

- **152** : disjoint aide (+43 %) mais cos≈0 → l'interférence est réfutée comme mécanisme ; suspicion optimiseur.
- **153** : un fix crédit côté plat recouvre 79 % du gain → **confirmé : crédit, pas topologie**. Reste ~21 % =
  moments Adam séparés (V3).

Converge avec l'arc substrat : le verrou transverse est le **régime d'apprentissage/crédit**, pas la structure — même
signature que le binding (crédit means→ends, EDR 130/133/136) et la mémoire (crédit vs délai, EDR 123).

## 5. Caveats (revue finale opus — PRÊT À INTÉGRER OUI, 0 Critical)

- **(a) FLAT_NORM n'est pas « qu'une constante d'échelle ».** C'est un contrôleur **adaptatif** (poids issus d'une
  EMA qui évolue). La conclusion « le levier = équilibrage de crédit » tient (c'est bien du crédit, pas de l'archi),
  mais la reformulation exacte est « un rééquilibrage de crédit *adaptatif* », pas une simple renormalisation figée.
- **(b) Dénominateur petit/bruité.** Le gain-152 (`FLAT−DISJOINT`) est ~0.01–0.02 ; un seed à gain quasi-nul
  rendrait le recovery instable. **Ici les 5 seeds ont un gain franc** (§2), donc le verdict est porté par de vrais
  recouvrements, pas par du bruit de dénominateur. Le verdict par **comptage de seeds** (pas la moyenne) borne
  l'influence d'un éventuel outlier.
- **(c) Sensibilité absolue du `1e-8`.** Le `w_k = 1/(EMA+1e-8)` est en valeur absolue ; une tête MSE convergeant
  très bas sature son poids à `N_HEADS=3` (borné par la re-normalisation, pas d'explosion). Effet de second ordre.
- **Non-tranché (par design)** : ce contrôle élimine « l'équilibrage d'échelle » comme explication *suffisante* du
  gain (CONFIRMED). Le résidu ~21 % (moments Adam séparés) vs une éventuelle contribution architecturale n'est PAS
  départagé — un **4e bras V3** (FLAT + Adam par-tête sur params partagés) le trancherait. Hérite aussi des caveats
  d'EDR 152 (proxy supervisé, profs quasi-orthogonaux, têtes non appariées).

## 6. Suite

- **V3 (proposée)** : 4e bras **FLAT + Adam-par-tête** (archi plate, moments Adam séparés sans split architectural)
  → isole la part « moments séparés » du résidu ~21 %. Si ce bras recouvre le reste, l'architecture est réfutée à
  100 % comme levier ; sinon la part résiduelle est architecturale (borne haute ~21 %).
- **Actionnable prod** : le substrat torch de prod devrait embarquer un **équilibrage de crédit multi-tête**
  (GradNorm / uncertainty-weighting / lr-par-tête), PAS une refonte en têtes disjointes — moins cher, capture
  l'essentiel du gain.

## 7. Provenance / non-périmètre

- `tools/disjoint_heads_confound.py` (`main_confound_check`, K=5, base=2200, STEPS=2000, `set_num_threads(1)`) ;
  **2 passes byte-identiques** ; AUCUN test relancé après le run.
- **Tooling ADDITIF** : `git diff` sur toute la branche = nouveau fichier + test + spec/plan/EDR uniquement ;
  `src/` VIDE ; `tools/disjoint_heads_ab.py` (EDR 152) **intact** (réutilisé par import, non modifié). Ne touche NI
  `torch_batch_model.py`/`backend_torch.py`/`substrate_*` (fil torch //).
- Subagent-driven : 2 tâches (SPEC conforme + qualité Approved chacune), revue finale **opus** (validité du
  contrôle) qui a confirmé que FLAT_NORM isole la bonne variable, borné l'inférence REFUTED, et posé les caveats
  a/b/c. Équité « 1 variable » vérifiée : `_train_arm` et `_train_flat_norm` partagent l'ordre init `manual_seed →
  FlatModel` et les graines held/batch (`seed+10_000`, `seed*1_000_003+t`).
- **Numérotation** : EDR 153 — bloc **150+** (convention `parallel-sessions-shared-tree`). 6e instrument per-type,
  suite directe d'EDR 152.
