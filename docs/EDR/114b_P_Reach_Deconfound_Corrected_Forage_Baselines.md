# EDR 114b — De-confond p_reach : baselines forage corriges (le pooling-reproduction deflate la metrique 2-4x)

> **Date** : 2026-06-30. **Addendum a [EDR 114](114_Reaching_Primitive_Closes_P_Reach_The_Wall_Is_The_Policy_Reproduction_Pooling_Confounds_The_Metric.md)** (pas de numero EDR contendu : 115/116/117 claimes par la session // moteur torch).
> **Verdict** : **CONFOND CONFIRME** — `_measure_forage` deflate `p_reach` **x2.34 (figees) / x3.26 (mobiles)** par pooling-reproduction. Les baselines forage d'EDR 105/106 (~0.18/0.21) **sous-estimaient 2-4x** la vraie capacite de la politique apprise.
> **Outil** : `tools/lewis_survival_sweep.py` (`main_forage_deconfound`, knob `disable_repro` cable sur le `benchmark_mode` existant). **Seed** : 1140 (smoke 99140). **Commit** : 188e26f.
> **Spec** : `docs/superpowers/specs/2026-06-30-p_reach-deconfound-design.md`. **Plan** : `docs/superpowers/plans/2026-06-30-p_reach-deconfound.md`.

## 1. Dette d'EDR 114

EDR 114 (borne-sup oracle) a decouvert en cours de route un **mode d'echec methodologique** de la
mesure `p_reach` : `_measure_forage` calcule `p_reach` sur le pool `agents + dead_agents`. Quand le
forage reussit, la reproduction intra-monde explose la population (n : ~192 initiaux -> plusieurs
milliers), et les **nouveau-nes tardifs** (spawn tick 140+, sans le temps d'atteindre une proie en 150
ticks) **diluent** `p_reach`. Diagnostic EDR 114 (oracle, figees) : 0.47 (pool, avec repro) -> 0.875
(cohorte fixe, sans repro). La metrique etait deflatee d'un facteur 2-4x.

Consequence : les baselines `p_reach` REPLICA d'EDR 105 (mobiles ~0.18) / 106 (figees ~0.21)
**sous-estimaient** la capacite de la politique apprise. Cet addendum **expose le de-confond** dans le
harnais forage et **re-base** ces magnitudes.

## 2. Methode (knob `disable_repro`, zero nouveau mecanisme)

Le mecanisme de de-confond **existait deja** : `Biosphere3D.benchmark_mode` (attribut, defaut `False`)
gate les TROIS chemins de reproduction (energie `world_1_stoneage:1341` ; social/MATE + HGT `:1544`).
EDR 112 (G0) l'utilisait deja (« cohorte fixe »). Il n'etait juste pas expose dans `_measure_forage`.

Le chantier = cabler le flag existant : `_measure_forage(..., disable_repro=False)` pose
`env.benchmark_mode = True` apres `Biosphere3D(cfg)` -> cohorte fixe -> pool = cohorte initiale, pas de
dilution. Matrice 2x2 `main_forage_deconfound` : `{disable_repro False/True} x {prey_speed 1.0 mobiles,
0.0 figees}`, politique APPRISE (replicas `_load_champions`), graines appariees, SANS evolution,
`N_APEX=0 / metab=0 / forage_payoff=3`. Verdict porte par la cellule figee (speed=0) :
`CONFOND CONFIRME` si ratio (no-repro / repro) >= 1.5 ; `CONFOND NEGLIGEABLE` si < 1.5 ; `INDETERMINE`
si la cellule figee manque.

## 3. Resultat (run pre-enregistre, seed 1140, n_eval=8, 2 runs byte-identiques)

```
  disable_repro | speed | p_reach p_cap | min_dist | n
  False         | 1     |    0.21  0.79 |     1.31 | 2920
  False         | 0     |    0.22  0.81 |     1.31 | 1270
  True          | 1     |    0.69  0.99 |     0.45 | 192
  True          | 0     |    0.52  0.96 |     0.79 | 192
  speed=0 (figees)  : repro=0.223 -> no-repro=0.521  (deflation x2.34)
  speed=1 (mobiles) : repro=0.211 -> no-repro=0.688  (deflation x3.26)
  VERDICT : CONFOND CONFIRME
```

**Controle de coherence** : la cellule (avec-repro, figees) = 0.22 reproduit le baseline confondu d'EDR
106 (~0.21). La cellule (sans-repro, figees) = 0.52 corrobore le diagnostic EDR 114 (oracle figees
0.47->0.875 ; ici politique apprise figees 0.22->0.52). Determinisme verifie (pass 1 == pass 2).

Note marquante : `n` chute de 2920/1270 (pool gonfle par repro) a **192** (cohorte initiale fixe) dans
les cellules `disable_repro=True` -> preuve directe que la reproduction est bien coupee et que le
gonflement de `n` etait la source de la dilution.

## 4. Re-base des baselines (qualitatif intact, magnitudes corrigees)

| condition (politique apprise) | avec-repro (confondu, ~ EDR 105/106) | sans-repro (CORRIGE) | deflation |
|---|---:|---:|---:|
| figees (speed 0) | 0.22 | **0.52** | x2.34 |
| mobiles (speed 1) | 0.21 | **0.69** | x3.26 |

La capacite de navigation de la politique apprise etait **sous-estimee 2-4x**. Vraie capacite a cohorte
fixe : ~0.52 (figees) / ~0.69 (mobiles), pas ~0.2.

## 5. Ce qui NE change PAS (les conclusions de l'arc Lewis tiennent)

Le de-confond corrige des **magnitudes**, pas la **direction** de l'arc :

- **Le mur reste le SUBSTRAT/la POLITIQUE.** A condition egale (cohorte fixe), EDR 114 mesure apprise
  ~0.43-0.52 vs oracle parfait **0.875** (0.984 cohorte equitable). L'ecart apprise <-> oracle persiste
  -> le monde PERMET d'atteindre, c'est la politique apprise qui ne ferme pas. Cote-MONDE de la
  navigation toujours DEFINITIVEMENT CLOS (EDR 105-114).
- **Les leviers-MONDE restent refutes** (energie/cinematique/selection/capacite-reseau/demande-111/
  affordance-reward, EDR 090-114). Le de-confond ne ressuscite aucun levier ; il dit seulement que le
  point de depart de la politique apprise est moins catastrophique qu'affiche (0.5-0.7, pas 0.2).
- **Implication pour la migration moteur** : la cible n'est pas « une politique qui passe de 0.2 a 1.0 »
  mais « de ~0.6 a ~0.9 » — l'ecart a combler vers l'oracle est reel mais plus etroit. Renforce le
  diagnostic [[sota-gap-substrate]] : migrer le MOTEUR (substrat differentiable + plasticite) pour
  fermer l'ecart politique<->oracle, l'INSTRUMENT (harnais/mondes/metriques) etant garde.

## 6. Dette reglee & provenance

- **Dette EDR 114 reglee** : le knob `disable_repro` est desormais cable dans `_measure_forage` /
  `main_forage_deconfound`. Toute mesure future de `p_reach` qui veut la vraie capacite (pas la
  dynamique de population) doit poser `disable_repro=True`.
- **Provenance** : harnais `name="lewis_forage_deconfound"` -> `results/lewis_forage_deconfound_1140.json`
  (gitignore) ; seed reel 1140, smoke 99140 distinct. 2 runs byte-identiques. AUCUN test relance apres
  le run reel (lecon EDR 107).
- **Coordination** : chantier tooling-only (`git diff src/` VIDE) -> zero collision avec la session //
  qui pilote la migration moteur torch.
