# EDR 192 (V4) — La synergie échelle×moments NE ferme PAS le résidu : les deux leviers non-archi sont REDONDANTS sur le canal de crédit par-tête (PARTIAL, 0.70, prédit avant run)

> **Date** : 2026-07-01. **Verdict pré-enregistré** : `recovery = (FLAT − FLATNORM_PERHEAD)/(FLAT − DISJOINT)` sur
> têtes MSE {value, pred}, par seed. `SYNERGY_CLOSES` si `recovery ≥ 0.90` majorité ; `NO_SYNERGY` si `≤ 0.79`
> majorité ; sinon `PARTIAL`.
> **Résultat** : **PARTIAL** (recovery moyen **+0.697** ; 1 seed ≥0.90, 2 ≤0.79). **Combiner** l'échelle de loss (153)
> ET les moments Adam par-tête (154) recouvre **0.697 — SOUS chacun des leviers seuls** (153 : 0.79 ; 154 : 0.73)
> → **la synergie ne ferme PAS le résidu ; les deux leviers sont REDONDANTS** (voire légère anti-synergie) car ils
> agissent sur le **même canal** : le crédit par-tête.
> **Prédiction opus PRÉ-ENREGISTRÉE** (dry-run K=3 : 0.680, SYNERGY_CLOSES exclu) — confirmée (K=5 : 0.697).
> **Outil** : `tools/disjoint_heads_synergy.py`. **Run** : K=5, base=2200, STEPS=2000, `set_num_threads(1)`,
> `use_deterministic_algorithms(True)`, **2 passes byte-identiques**. **Spec/Plan** :
> `docs/superpowers/{specs,plans}/2026-07-01-disjoint-heads-synergy*`.

## 1. Question — les deux leviers non-archi combinés ferment-ils le résidu ~21 % ?

Sous-arc optimiseur : 153 = échelle de loss seule recouvre **0.79** ; 154 = moments Adam par-tête seuls recouvrent
**0.73** ; aucun ne ferme seul le résidu ~21 %. V4 : un bras **FLAT_NORM_PERHEAD** (plat + 3 Adam à moments propres
**ET** échelle de loss EMA `w_k=1/EMA(loss_k)`) recouvre-t-il ≥ 0.90 (→ archi réfutée à ~100 % comme levier), ou
reste-t-il au niveau des leviers seuls (**redondance** : Adam par-tête normalise DÉJÀ par-tête via son second
moment `v`) ?

Bras (Commandement 15, seule variable = optimiseur) : FLAT + DISJOINT (`_train_arm`, 152) + FLAT_NORM_PERHEAD (nouveau).
Mêmes profs/seeds/init que 152/153/154.

## 2. Résultat (run pré-enregistré, 2 passes byte-identiques)

```
  seed | FLAT v/p     | FLAT_NP v/p   | DISJOINT v/p  | recovery | gain-152 v/p
  2200 | 0.027 0.027 | 0.011 0.009 | 0.010 0.011 | +1.039  | 0.017 0.015
  2201 | 0.025 0.027 | 0.012 0.009 | 0.006 0.010 | +0.879  | 0.018 0.018
  2202 | 0.016 0.031 | 0.026 0.010 | 0.006 0.014 | +0.120  | 0.010 0.017
  2203 | 0.028 0.036 | 0.025 0.008 | 0.010 0.011 | +0.637  | 0.018 0.025
  2204 | 0.025 0.030 | 0.017 0.005 | 0.008 0.008 | +0.810  | 0.017 0.022
  MOYEN recovery=+0.697   VERDICT : PARTIAL
```

**Sanity de comparabilité** : les colonnes FLAT et DISJOINT reproduisent 153/154 seed-à-seed (`_train_arm` identique)
→ recovery directement comparable. Gain-152 franc sur les 5 seeds (0.010–0.025) → verdict non dominé par un
dénominateur dégénéré.

## 3. Lecture

1. **SYNERGY_CLOSES exclu (1/5 ≥0.90).** Combiner les deux leviers **ne ferme PAS** le résidu ~21 %.
2. **La combinaison fait MOINS bien que chaque levier seul** : 0.697 < 153 (0.79) et < 154 (0.73). Ce n'est pas une
   synergie — c'est de la **redondance**, avec une légère **anti-synergie** sur certains seeds (seed 2202 s'effondre
   à 0.120 vs 154=0.41).
3. **Mécanisme (revue opus, prédit avant run par dry-run) : Adam par-tête ANNULE le scaling de loss.** Un scaling
   **constant** `g → c·g` donne `m → c·m`, `v → c²·v`, donc `m̂/√v̂ → m/√v` **inchangé** : Adam normalise la
   magnitude, la direction du gradient par-tête est préservée. L'échelle `w_k` par-dessus un Adam dédié à la tête k
   n'ajoute presque rien (le résidu ne vient que de la dérive EMA / `eps` / bias-correction = 2e ordre), et perturbe
   parfois un Adam déjà réglé → recovery légèrement plus bas. **Les deux leviers non-archi agissent sur le MÊME canal :
   le crédit par-tête.**

## 4. Portée — sous-arc optimiseur CLOS

- **`SYNERGY_CLOSES` (le seul embranchement à poids décisif) ne se déclenche pas** → le résidu ~21 % n'est PAS fermé
  par l'union des leviers non-archi ; il reste un effet de 2e ordre (redondance des leviers + part de
  trajectoire/architecture ≤ ~21 %, non départagée). **Mais la conclusion de fond est INCHANGÉE et déjà tranchée par
  191** : l'architecture n'est PAS le levier (réfutée même sous vraie interférence).
- **Lecture des trois leviers non-archi** : échelle de loss (153), moments par-tête (154) et leur combinaison (192)
  recouvrent tous ~0.70–0.79 — **interchangeables et redondants** (même canal de crédit). L'actionnable prod est
  robuste au CHOIX du mécanisme : n'importe quel équilibrage de crédit multi-tête (GradNorm / moments / lr par-tête)
  capture l'essentiel ; les empiler n'aide pas.
- **Arc têtes disjointes DÉFINITIVEMENT CLOS** : 152 (aide, cos≈0) → 153/154 (gain=crédit, leviers ~interchangeables)
  → 190 (corréler n'induit pas le conflit) → 191 (capacité induit, crédit gagne quand même) → **192 (les leviers
  non-archi sont redondants, pas synergiques)**. Migration #5 réfutée comme levier ; recette prod = un équilibrage de
  crédit multi-tête (peu importe lequel), jamais une refonte disjointe.

## 5. Caveats

- **(a) Redondance attendue** : Adam par-tête normalise déjà (via `v`) → l'échelle n'ajoute rien de durable ; `PARTIAL`
  / `NO_SYNERGY` ne signifient PAS « archi compte » (191 l'a réfuté).
- **(e) [revue opus] Seul le NON-déclenchement de `SYNERGY_CLOSES` porte du poids décisif** ; `NO_SYNERGY` et `PARTIAL`
  = **la MÊME lecture** (« la synergie ne ferme pas »). Ne PAS sur-interpréter le PARTIAL comme un résultat distinct
  (154 était lui-même PARTIAL sous ces seuils, dénominateurs `FLAT−DISJ` ~0.01–0.018, forte variance seed).
- **(f) [revue opus] 192 peut passer SOUS les leviers seuls** (0.697 < 0.73/0.79 ; seed 2202 : 0.120) = redondance /
  anti-synergie du scaling sur un Adam déjà réglé, **PAS un signal pro-architecture**.
- **(b) Forward unique + retain_graph** (comme 154) : gradients au même point, updates séquentiels. **(c)** recovery
  peut dépasser 1.0 (seed 2200 = 1.039, FLAT_NORM_PERHEAD bat DISJOINT) — attendu, non clippé ; **verdict au comptage
  de seeds, pas la moyenne** (qui est gonflable par petits dénominateurs). **(d)** `lr` partagé. Hérite 152/153/154.

## 6. Suite

- **Sous-arc optimiseur CLOS** ; l'arc têtes disjointes est complet (152→192). Aucun levier gate-side / optimiseur
  résiduel à ouvrir côté per-type.
- Reste per-type (hors arc disjoint) : worlds 2/3 réels (RISQUÉ — FamineWorld = session //), G2 composition (RISQUÉ
  — EDR 122). Le backlog d'instruments per-type isolés/non-colisionnants est épuisé.

## 7. Provenance / non-périmètre

- `tools/disjoint_heads_synergy.py` (`main_v4_check`, K=5, base=2200, STEPS=2000, `set_num_threads(1)`) ; **2 passes
  byte-identiques** ; AUCUN test relancé après le run.
- **Tooling ADDITIF** : nouveau fichier + test + spec/plan/EDR uniquement ; `src/` VIDE ; `disjoint_heads_ab.py`
  (152), `disjoint_heads_confound.py` (153), `disjoint_heads_v3.py` (154) **intacts** (réutilisés par import). Ne
  touche NI le substrat torch (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil // torch).
- Subagent-driven : 2 tâches (SPEC conforme + qualité Approved chacune, reviewer a vérifié le diff char-par-char),
  revue finale **opus PRÊT À INTÉGRER OUI, 0 Critical**, qui a **prédit PARTIAL avant le run** (dry-run K=3 : 0.680,
  SYNERGY_CLOSES exclu ; 154 reproduit 0.732 = sanity), vérifié la combinaison correcte des 2 leviers + le
  déterminisme, et posé les caveats e/f. Verdict pré-enregistré gelé avant le run.
- **Numérotation** : EDR **192** — bloc **190+** (per-type disjoint extension). 10e instrument per-type, clôt le
  sous-arc optimiseur d'EDR 153/154 ; l'arc de fond était déjà clos par 191.
