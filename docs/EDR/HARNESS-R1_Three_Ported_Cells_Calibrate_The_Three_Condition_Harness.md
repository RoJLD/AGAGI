---
id: EDR-HARNESS-R1
type: EDR
title: "Trois cellules PORTEES calibrent le harnais a trois conditions -- PARTIAL sur bilinear (plafond 0,944 au-dessus de la barre), LR_ARTIFACT sur le rappel (le nul n'est pas invariant au pas), INCONCLUSIVE_ALIAS sur l'etat porte (split control non entraine)"
status: active
verdict: PIECE_PARTIAL/LR_ARTIFACT/INCONCLUSIVE_ALIAS
gate: G2
tests: [SDR-G2]
adopts: [REF-DEMAND-MARKER, REF-HARNESS-CONTRACTS, REF-HARNESS-PIECES]
---

## 1. Règle lue

`docs/preregistrations/HARNESS-R1-ter.json` (seal `e1b66db9a23e441f0f0036cb6a3e411dcf3b999a3c0aaaac5b8e5277ad7f79ca`),
lue par `tools.preregister.verify("HARNESS-R1-ter")` avant toute cellule (`tools/harness/run_r1.py`). C'est
la troisième pré-inscription d'une chaîne dont aucun maillon n'est réécrit — une pré-inscription ne se
corrige pas (`tools/preregister.py`) :

* `docs/preregistrations/HARNESS-R1.json` — le sceau d'origine (tâche 10). N'avait encore lu **aucune**
  cellule quand la revue contrôleur a trouvé huit défauts Important.
* `docs/preregistrations/HARNESS-R1-bis.json` — remplace `docs/preregistrations/HARNESS-R1.json` avant
  toute cellule, `raison_bis` (citée verbatim) : « revue de la tâche 10 : unités non comparables,
  référence A' non mesurée, plancher de bruit absent, issue négative non nommée, famille de contrôles
  sous-déclarée (E2/E8/E23) ». `dv_primaire` est déjà, à ce maillon, la clause scellée : `hits` par seed
  et par bras ; `ratio_within` par ablation ; `sep_ref` (médiane A − médiane A0) ; `dose.updates` par
  bras ; `noise_band` ; `closure` (E19).
* `docs/preregistrations/HARNESS-R1-ter.json` — remplace `docs/preregistrations/HARNESS-R1-bis.json`,
  `raison_ter` (citée verbatim, ruling contrôleur E12 du 2026-09-22, **texte scellé, non reformulé**) :
  « E12 : sous 9 processus python concurrents, la CostGuard par seed (15 x unite) a abandonne les seeds
  2-3 de la cellule A (A0/A2/D/D2) -> INCONCLUSIVE_N ; la marge x3 de project_cost supposait la charge du
  smoke. Le budget est une garde de cout, pas une grandeur lue : la lecture est inchangee. » `-ter` est
  lue depuis le sceau `-bis` déjà écrit, **jamais recalculée depuis le smoke** (`build_rule_r1_ter`,
  `tools/harness/seal_r1.py:278-309`) : QUATRE champs changent par rapport à `-bis` (`budget_s` par
  cellule ×3, `budget_family_s`, `remplace`/`raison_ter`, et `predictions_chiffrees_AVANT_le_run_note` —
  sept clés au total) — `predictions_chiffrees_AVANT_le_run` reste **bit-identique de `-bis` à `-ter`**
  (vérifié champ par champ). ⚠️ Cette bit-identité ne remonte PAS jusqu'à `HARNESS-R1` : `-bis` avait déjà,
  AVANT toute cellule, complété les prédictions de R1 avec des grandeurs MESURÉES au smoke (`raison_bis`)
  — la bande de bruit [0,990 ; 1,034] pour A, la référence lr=0 mesurée 0,161 pour A′, la médiane intacte
  0,928 pour B — et les cellules elles-mêmes diffèrent entre `HARNESS-R1` et `-bis` sur `budget_s`,
  `control_family`, `eval_batches`, `issues`, `n_agents`, et le texte d'`incapable_ceiling` (A). La chaîne
  `HARNESS-R1` → `-bis` n'est donc PAS bit-identique sur ce champ ; seule la chaîne `-bis` → `-ter` l'est.

`dv_primaire` (identique aux trois maillons, vérifié) : « `hits` par seed et par bras ; `ratio_within` par
ablation ; `sep_ref` (mediane A - mediane A0) ; `dose.updates` par bras ; `noise_band` ; `closure` (E19) ».

## 2. E12 en acte

Le premier run réel (`HARNESS-R1-bis`, 2026-09-22 après-midi) a tourné sous une charge mesurée par **UNE
seule lecture globale `tasklist`** (« 13 processus python.exe vus avant le run », `scratchpad_run_r1.log`,
répétée TELLE QUELLE pour les trois cellules) — PAS par `tools.jobs.doctor.project_processes()` lu au
départ de chaque cellule : cette lecture PAR CELLULE, scopée au PROJET (hors éditeurs/extensions, hors
moi-même et mes ancêtres), n'existe que depuis `-ter`, où elle a rendu **0 / 0 / 0** avant chacune des
trois cellules (`scratchpad_run_r1_ter.log`). Le chiffre « 9 processus python concurrents » cité en §1
vient du RULING scellé dans `raison_ter` (texte du contrôleur), pas d'une mesure directement enregistrée
dans le log `-bis` — E12 : un chiffre de coût se lit avec sa charge, et la charge se mesure LÀ où elle est
mesurée. La `CostGuard` PAR SEED de `-bis` vaut `budget_s / 12` = 15 × l'unité scellée du smoke
(`unit_s_given`) — pour la cellule A, 15 × 6,42 s ≈ 96,3 s. Sous cette charge, SIX couples (seed, bras) de
la cellule A ont dépassé ce budget et ont été abandonnés avant la fin de leur bras
(`results/harness_r1_A_0_bis_E12.json`) — DEUX seeds distincts (2 et 3), jamais quatre :

| bras | seeds abandonnés (cellule A, `-bis`) |
|---|---|
| A0 | `[3]` |
| A2 | `[3]` |
| D  | `[2, 3]` |
| D2 | `[2, 3]` |

→ 10 seeds complets < `n_floor`=12 → `INCONCLUSIVE_N` (« 10 seeds complets < n_floor=12 (abandons :
{'A0': [3], 'A2': [3], 'D': [2, 3], 'D2': [2, 3]}) »). Sous la même charge, la cellule B a perdu un seed
(D2 : `[0]`) → également `INCONCLUSIVE_N` (11 < 12, `results/harness_r1_B_0_bis_E12.json`). La cellule A′
a complété ses 12 seeds sans abandon sous `-bis` et rendait déjà `LR_ARTIFACT` — la charge n'a affecté que
le COMPTE de seeds complets, jamais la lecture elle-même.

**Réplication gratuite (A′, non revendiquée avant cette revue) :** A′ a donc tourné DEUX fois, sous `-bis`
PUIS sous `-ter` — les deux blocs `data.db` (`results/harness_r1_Aprime_0_bis_E12.json` et
`results/harness_r1_Aprime_0.json`) sont IDENTIQUES champ pour champ, SAUF `regime.contract_task.elapsed_ms`
(1,2367 ms sous `-bis` contre 1,2950 ms sous `-ter` — un temps CPU de compilation du contrat, pas une
donnée de résultat) : une bit-identité de cellule ENTIÈRE entre deux runs indépendants, plus forte que la
seule bit-identité de RÈGLE affirmée en §1.

Le correctif `-ter` relève le budget de chaque cellule ×3 (`CostGuard` par seed = 45 × l'unité scellée),
sans toucher aucune valeur lue par `harness_verdict_lecture` — le budget est une garde de coût, jamais une
grandeur de `dv_primaire`. Sous `-ter` (2026-09-22 23:21–23:31), **0 abandon** dans les trois cellules.
Unités, sealed vs observées (`actual_s / 60`, moyenne par (seed, bras), même dénominateur que
`n_units` de `project_cost`) :

| cellule | unité scellée (smoke, `unit_s_given`) | unité observée (`actual_s/60`) |
|---|---|---|
| A  | 6,423 s | 3,521 s |
| A′ | 3,345 s | 1,431 s |
| B  | 17,147 s | 8,410 s |

L'unité observée sous `-ter` est environ **moitié** de l'unité scellée au smoke, sur les trois cellules —
la charge machine était retombée entre le smoke et le run `-ter`, ce qui explique à la fois le succès
(0 abandon) et le rapport `actual_s` / `projected_s` très inférieur à 1 (§8). `run_r1.py` documente la
charge lue par `tools.jobs.doctor` juste avant chaque cellule (`load_note`, non repris ici faute d'avoir
été persisté dans les JSON de résultat) ; les trois `cost.machine_load_note` publiés se lisent
littéralement « charge machine a noter dans le record (E12) » — la note qualitative de ce run est donc
celle du paragraphe précédent (0 abandon, unité observée ≈ moitié de l'unité scellée), pas un compte de
processus persisté.

## 3. Régime (`data.regime`, recopié depuis chaque JSON `-ter`, jamais retapé)

### Cellule A (`results/harness_r1_A_0.json`)

```json
{"task": {"task": "composition_same_tick_K6", "K": 6, "T": 1, "same_tick": true, "kind": "composition", "obs_dim": 59, "slots": {"key": [0, 6], "q": [6, 12], "distractor": [12, 18]}}, "learner_name": "connectome_torch", "learner_family": "connectome_torch", "sweep": [{"credit": "supervised", "lr": 0.02, "n_classes": null, "rank": 16}, {"credit": "supervised", "lr": 0.002, "n_classes": null, "rank": 16}], "piece": "bilinear", "without": {"bilinear": false}, "n_agents": 16, "episodes": 300, "eval_batches": 40, "seeds": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "bayes_floors": {"permute_key": {"declared": 0.16666666666666666, "measured": 0.1650390625, "se": 0.005823093691405702, "certified": true}, "permute_query": {"declared": 0.16666666666666666, "measured": 0.176513671875, "se": 0.005823093691405702, "certified": true}, "inject_distractor_slot": {"declared": null, "measured": 1.0, "se": 1.5625e-08, "certified": false}}, "contract_task": {"bayes_floors": {"permute_key": 0.16666666666666666, "permute_query": 0.16666666666666666}, "certified": true, "elapsed_ms": 3.1951998826116323}, "incapable_ceiling": {"proven": false, "provenance": "forme close de backend_torch._step a H_in=0 (logit_j = sigmoid(W[j,j])*tanh(W[key,j]+W[K+q,j])) ; MINORANT 34/36 par charniere a marge FIXE, float64, victoire STRICTE ; re-verifie SANS autograd (python pur) ET IN SITU dans le vrai TorchPopulationModel (34/36 aux deux). ATTENTION : c est un MINORANT qui MONTE avec l effort -- 29/36, 34/36 et 36/36 selon trois chercheurs independants du meme jour. Il ne fonde AUCUN << le substrat ne peut pas >> (E19 occ.4) :  MINORANT, jamais PROUVE.", "value": 0.9444444444444444}, "piece_removed_verified": true}
```

### Cellule A′ (`results/harness_r1_Aprime_0.json`)

```json
{"task": {"task": "recall_same_tick_K6", "K": 6, "T": 1, "same_tick": true, "kind": "recall", "obs_dim": 59, "slots": {"key": [0, 6], "q": [6, 12], "distractor": [12, 18]}}, "learner_name": "connectome_torch", "learner_family": "connectome_torch", "sweep": [{"credit": "supervised", "lr": 0.02, "n_classes": null, "rank": 16}, {"credit": "supervised", "lr": 0.002, "n_classes": null, "rank": 16}], "piece": "bilinear", "without": {"bilinear": false}, "n_agents": 16, "episodes": 150, "eval_batches": 40, "seeds": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "bayes_floors": {"permute_key": {"declared": 0.16666666666666666, "measured": 0.1650390625, "se": 0.005823093691405702, "certified": true}, "permute_query": {"declared": null, "measured": 1.0, "se": 1.5625e-08, "certified": false}, "inject_distractor_slot": {"declared": null, "measured": 1.0, "se": 1.5625e-08, "certified": false}}, "contract_task": {"bayes_floors": {"permute_key": 0.16666666666666666}, "certified": true, "elapsed_ms": 1.2950000818818808}, "incapable_ceiling": null, "piece_removed_verified": true}
```

### Cellule B (`results/harness_r1_B_0.json`)

```json
{"task": {"task": "composition_two_step_K6", "K": 6, "T": 2, "same_tick": false, "kind": "composition", "obs_dim": 59, "slots": {"key": [0, 6], "q": [6, 12], "distractor": [12, 18]}}, "learner_name": "connectome_torch", "learner_family": "connectome_torch", "sweep": [{"credit": "supervised", "lr": 0.002, "n_classes": 6, "rank": 16}, {"credit": "supervised", "lr": 0.001, "n_classes": 6, "rank": 16}], "piece": "recurrent_state", "without": {"feedforward": true}, "n_agents": 16, "episodes": 600, "eval_batches": 40, "seeds": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "bayes_floors": {"permute_key": {"declared": 0.16666666666666666, "measured": 0.1650390625, "se": 0.005823093691405702, "certified": true}, "permute_query": {"declared": 0.16666666666666666, "measured": 0.176513671875, "se": 0.005823093691405702, "certified": true}, "inject_distractor_slot": {"declared": null, "measured": 1.0, "se": 1.5625e-08, "certified": false}}, "contract_task": {"bayes_floors": {"permute_key": 0.16666666666666666, "permute_query": 0.16666666666666666, "state_reset": 0.16666666666666666}, "certified": true, "elapsed_ms": 1.4976998791098595}, "incapable_ceiling": null, "piece_removed_verified": true}
```

## 4. Résultats par cellule

### 4.1 Cellule A — bilinear, `composition_same_tick_K6` — `PIECE_PARTIAL`

`hits` (`last`) par seed, 12 valeurs, dans l'ordre seed 0→11 :

| bras | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | médiane |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A  | 0,9328 | 0,9250 | 0,9375 | 0,9016 | 0,8906 | 0,9250 | 0,9375 | 0,9313 | 0,9469 | 0,9234 | 0,9422 | 0,9688 | **0,9320** |
| A0 | 0,1688 | 0,1984 | 0,1797 | 0,1609 | 0,1844 | 0,1641 | 0,1734 | 0,1625 | 0,1734 | 0,1703 | 0,1672 | 0,1672 | **0,1695** |
| A2 (2e lr) | 0,3750 | 0,4344 | 0,4172 | 0,4484 | 0,4047 | 0,4375 | 0,3516 | 0,4031 | 0,4078 | 0,4234 | 0,3844 | 0,4078 | **0,4078** |
| D (sans bilinear) | 0,2703 | 0,2688 | 0,2531 | 0,2781 | 0,2750 | 0,2766 | 0,2328 | 0,3031 | 0,2719 | 0,2797 | 0,2609 | 0,2672 | **0,2711** |
| D2 (sans bilinear, 2e lr) | 0,1906 | 0,1781 | 0,1906 | 0,1625 | 0,1750 | 0,1906 | 0,1422 | 0,1937 | 0,1828 | 0,1969 | 0,1766 | 0,1531 | **0,1805** |

Acquisition : `bar`=0,2195, `reference_last`(A0)=0,1695, `learner_last`(A)=0,9320, `learner_first`=0,1727,
`per_seed_above_ref`=**12/12**, `saturation`=TENDANCE, `bar_status`=**CEILING_ABOVE_BAR**,
`representational_ceiling_above_bar`=**true** (le plafond de représentation 0,944 = 34/36 forme close est
AU-DESSUS de la barre 0,2195 — le harnais publie ce fait, ne le cache pas). `dose.updates` : A = 300
(gradient_updates, 12/12 seeds) ; A0 = 0 (12/12 seeds, aucun pas — bras de référence gelé). Verdict
d'acquisition : `ACQUIRED`.

Nécessité (`bilinear`) : `med_without`=0,2711 (D), `ratio`=**3,44** hors bande de bruit (`in_noise_band`
false), `sep_ref`=0,9320 − 0,1695 = **0,7625**, `sham`=**DECLARED** (`{"bilinear_sham": true}`, registre
`PIECES` — aucun bras `sham` séparé n'est exécuté, cf. §9) ; `without_clears_bar`=**true** (0,2711 >
0,2195). Verdict : « med(D) 0.271 > barre 0.220, ratio 3.44x hors bande » → **`PIECE_PARTIAL`**.

`ratio_within` de demande, `noise_band`(A) = [0,9649 ; 1,0345] :

| ablation | `must_bite` | ratio | verdict | `in_noise_band` |
|---|---|---|---|---|
| permute_key | oui | 4,39 | X_DEMANDED | non |
| permute_query | oui | 4,35 | X_DEMANDED | non |
| inject_distractor_slot | non (décoy) | 1,00 | X_DECOY | **oui** |

E19 (`condition`=necessity) : `lrs`=[0,02 ; 0,002], `gaps_by_lr`={0,02: 0,6609 ; 0,002: 0,2273},
`closure`=**0,656**, `resolution`=0,1705, `status`=**ROBUST** — le nul (ici, le fait que D reste
au-dessus de la barre sans jamais rattraper A) ne se referme pas au second pas.

### 4.2 Cellule A′ — bilinear, `recall_same_tick_K6` — `LR_ARTIFACT`

`hits` (`last`) par seed :

| bras | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | médiane |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A  | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | **1,0000** |
| A0 | 0,2531 | 0,1453 | 0,1609 | 0,1031 | 0,1422 | 0,2516 | 0,2094 | 0,1281 | 0,2047 | 0,1047 | 0,1422 | 0,1281 | **0,1438** |
| A2 (2e lr) | 0,9750 | 0,9719 | 1,0000 | 0,9906 | 1,0000 | 0,9828 | 0,9875 | 0,9750 | 0,9906 | 0,9859 | 0,9875 | 0,9859 | **0,9867** |
| D (sans bilinear) | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | 1,0000 | **1,0000** |
| D2 (sans bilinear, 2e lr) | 0,8531 | 0,7547 | 0,8500 | 0,8578 | 0,8859 | 0,9297 | 0,8531 | 0,8672 | 0,8656 | 0,8516 | 0,7781 | 0,8375 | **0,8531** |

Acquisition : `bar`=0,1938, `reference_last`(A0)=0,1438, `learner_last`(A)=1,0000, `per_seed_above_ref`=
**12/12**, `saturation`=PLATEAU, `bar_status`=CEILING_UNVALIDATED (aucun `incapable_ceiling` scellé pour
A′), `sep_ref`=1,0000 − 0,1438 = **0,8562** (`acquisition.raw.sep`=0,85625). `dose.updates` : A = 150,
A2 = 150, D = 150, D2 = 150 (12/12 seeds chacun, `unit`=gradient_updates) ; A0 = 0 (12/12 seeds,
`dparam_abs_sum`=0,0 — bras de référence gelé). Verdict : `ACQUIRED`.

`noise_band`(A) = [1,0000 ; 1,0000] — **DÉGÉNÉRÉE** : `last` et `noop` sont tous deux au plafond 1,0 sur
les 12 seeds (`noise_floor.A.band` du JSON) ; cf. §6a, c'est le fait le plus tranchant de la limite de
cette cellule. Nécessité (`bilinear`) au premier pas (lr=0,02) : `med_without`(D)=1,0000, `ratio`=1,00,
`in_noise_band`= **true** → lecture brute au 1er pas : `NOT_NECESSARY` (X_DECOY, « aucun effet de
l'ablation détecté ») — sur une bande réduite à un seul POINT, `in_noise_band=true` ne porte AUCUNE
information (un ratio de 1,000 ne peut pas être ailleurs que dans une bande [1,0 ; 1,0]).

E19 (`condition`=necessity) : `lrs`=[0,02 ; 0,002], `gaps_by_lr`={0,02: **0,0000** ; 0,002: **0,1336**},
`closure`=**1,000**, `resolution`=0,05, `status`=**LR_ARTIFACT**. `why` (citation intégrale) : « nécessité
de la pièce : nul NON robuste au pas -> artefact d'hyperparamètre, PAS un verdict de capacité. L'écart au
bras de référence se REFERME de 100.0% sur le balayage (lr=0.002 : écart 0.1336 -> lr=0.02 : écart 0 ;
seuil 66.7%). Le bras testé REJOINT sa référence quand on change SEULEMENT le réglage : le réglage est un
FACTEUR du verdict. Rejouer, ou refuser le verdict. » **`_demand` n'a jamais tourné** : l'E19 intercepte le
verdict avant que la demande ne soit calculée (`out["demand"]` = `null` dans le JSON) — l'ordre 2.3-b place
`LR_ARTIFACT` (index 3) avant toute branche de demande (index ≥ 5).

### 4.3 Cellule B — recurrent_state, `composition_two_step_K6` — `INCONCLUSIVE_ALIAS`

`hits` (`last`) par seed :

| bras | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | médiane |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A  | 0,9328 | 0,9281 | 0,8969 | 0,9531 | 0,9172 | 0,9641 | 0,9000 | 0,9141 | 0,9062 | 0,9047 | 0,9406 | 0,9391 | **0,9227** |
| A0 | 0,1625 | 0,1781 | 0,1500 | 0,1750 | 0,1609 | 0,1469 | 0,1828 | 0,1266 | 0,1891 | 0,1750 | 0,1625 | 0,1625 | **0,1625** |
| A2 (2e lr) | 0,7016 | 0,6562 | 0,6391 | 0,6766 | 0,6891 | 0,7109 | 0,6938 | 0,6219 | 0,6406 | 0,6594 | 0,7031 | 0,7047 | **0,6828** |
| D (sans recurrent_state) | 0,1781 | 0,1578 | 0,1547 | 0,1578 | 0,1750 | 0,1937 | 0,1656 | 0,1312 | 0,1437 | 0,1672 | 0,1859 | 0,1672 | **0,1664** |
| D2 (sans recurrent_state, 2e lr) | 0,1453 | 0,1656 | 0,1609 | 0,1656 | 0,1609 | 0,1969 | 0,1719 | 0,1359 | 0,1437 | 0,1859 | 0,1719 | 0,1844 | **0,1656** |

Acquisition : `bar`=0,2125, `reference_last`(A0)=0,1625, `learner_last`(A)=0,9227, `per_seed_above_ref`=
**12/12**, `saturation`=TENDANCE, `bar_status`=CEILING_UNVALIDATED, `sep_ref`=0,9227 − 0,1625 = **0,7602**
(`acquisition.raw.sep`=0,76016). `dose.updates` : A = 600, A2 = 600, D = 600, D2 = 600 (12/12 seeds
chacun, `unit`=gradient_updates) ; A0 = 0 (12/12 seeds, `dparam_abs_sum`=0,0 — bras de référence gelé).
Verdict : `ACQUIRED`.

Nécessité (`recurrent_state`) : `med_without`(D)=0,1664, `ratio`=**5,54**, `sham`=**PARAMS_NON_APPARIES**
(aucun sham déclaré pour `recurrent_state` dans le registre `PIECES`), `without_clears_bar`=**false**
(0,1664 ≤ 0,2125) → « med(D) 0.166 <= barre 0.212 (référence + min_sep) » → **`NECESSARY`** au sens de la
seule nécessité. E19 : `lrs`=[0,002 ; 0,001], `gaps_by_lr`={0,002: 0,7563 ; 0,001: 0,5172},
`closure`=**0,316**, `resolution`=0,1670, `status`=**ROBUST**.

Ces deux verdicts (`NECESSARY`, e19 `ROBUST`) sont **publiés mais non décisifs** : l'ordre 2.3-b calcule la
demande APRÈS la nécessité, et c'est elle qui tranche le verdict final.

`ratio_within` de demande, `noise_band`(A) = [0,9650 ; 1,0167] :

| ablation | `must_bite` | ratio | verdict | `in_noise_band` | alias |
|---|---|---|---|---|---|
| permute_key | oui | 4,46 | X_DEMANDED | non | — |
| permute_query | oui | 4,29 | X_DEMANDED | non | — |
| inject_distractor_slot | non (décoy) | 1,00 | X_DECOY | **oui** | — |
| state_reset | oui | 5,73 | X_DEMANDED | non | **FUNCTIONAL_LEAK** |

Bloc alias de `state_reset` (`alias_guard_verdict`) : `functional_aliasing`=fail, `alias_verdict`=
**FUNCTIONAL_LEAK**, `leakage`=**0,7297**, `x_response`=0,7617, `leak_seeds`=12/12,
`leak_seeds_two_sided`=12/12. Split CONTROL (key re-présentée au pas de réponse, censé rester résolu même
état effacé) : `control_intact_median`=**0,9078**, `control_ablated_median`=**0,1781**,
`control_demand.ratio`=**5,10** (X_DEMANDED). Le contrôle, censé être un no-op sous `state_reset`, chute
quasiment autant que la tâche principale sous LA MÊME ablation (contrôle 0,9078 → 0,1781, `leakage`
0,7297 > tol 0,05 ; tâche `A` → `state_reset` 0,9227 → 0,1609, `x_response` 0,7617) : c'est ce
rapprochement — pas le contraste de nécessité `A` → `D` (0,9227 → 0,1664, calculé plus haut) — qui rend
l'alias FUNCTIONAL_LEAK plutôt que SURGICAL, et qui fait le verdict final :
**`INCONCLUSIVE_ALIAS`**, `why` = « state_reset : alias FUNCTIONAL_LEAK ».

## 5. Prédictions scellées vs obtenues

Les trois prédictions (`predictions_chiffrees_AVANT_le_run`) sont scellées dans `-bis` et re-portées
**bit-identiques** dans `-ter` (`predictions_chiffrees_AVANT_le_run_note` : « scellées dans -bis avant
tout run, re-portées telles quelles »).

* **A** — `issues.attendue`=`PIECE_PARTIAL`. **Obtenu : `PIECE_PARTIAL`.** Prédiction confirmée sur la
  branche ET sur l'ordre de grandeur (chute ≥3× hors bande annoncée, obtenu 3,44× ; `bar_status`
  `CEILING_ABOVE_BAR` annoncé et obtenu ; bit-identité seed 0 annoncée 0,9328125/0,2703125 — obtenue
  0,932812511920929/0,270312488079071, identique aux décimales publiées) — SAUF la bande de bruit, la
  SEULE quantité annoncée qui a bougé : scellée [0,990 ; 1,034] (3 seeds au smoke), obtenue [0,9649 ;
  1,0345] (12 seeds) — borne basse ~2,5 points plus bas que l'annoncée. Cela ne change rien à la lecture :
  le décoy `inject_distractor_slot` (ratio 1,0008) tombe DANS les deux bandes, et les ratios demandés
  (4,39 / 4,35) restent très au-delà de l'une comme de l'autre.
* **A′** — `issues.attendue`=`PIECE_NOT_NECESSARY`. **Obtenu : `LR_ARTIFACT`, PAS la branche attendue.**
  `issues.sinon` (citation) : « le bilineaire modifie le rappel same_tick : resultat a graver » — cette
  clause `sinon` ne couvre PAS non plus ce qui a été mesuré : le bilinéaire ne « modifie » rien (D = A =
  1,0 au premier pas, ratio 1,00, X_DECOY) — c'est le SECOND pas du sweep qui rouvre un écart (D2 medD2=
  0,8531 < A2=0,9867) et que l'E19 lit comme non robuste. Ni `attendue` ni `sinon` ne nommaient cette
  troisième possibilité (motif discuté en §6).
* **B** — `issues.attendue`=`DEMANDED_ACQUIRED_NECESSARY`. **Obtenu : `INCONCLUSIVE_ALIAS`, PAS la branche
  attendue.** `issues.sinon` (citation) : « la retention ne passe pas par l'etat porte a ce pas : resultat
  a graver, LOCK-001 rouvert » — cette clause `sinon` ne couvre pas non plus ce qui a été mesuré : la
  nécessité elle-même EST confirmée (`NECESSARY`, D au plancher de Bayes, e19 ROBUST) ; ce qui manque est
  la capacité de la garde d'alias à DISTINGUER cette nécessité d'un artefact de vue partagée, parce que le
  bras CONTROL n'a jamais été entraîné à résoudre sa propre tâche (§6b).

Dans les deux cas où la branche attendue n'a pas été obtenue, ni `attendue` ni `sinon` — les deux
possibilités que le pré-vol avait scellées d'avance — ne nomment le résultat réel : c'est la preuve que le
harnais peut rendre une **troisième famille de lecture**, ni la confirmation ni le résultat négatif nommé
d'avance, et que cette famille est de nature INSTRUMENTALE plutôt que scientifique (§6).

## 6. Deux limites d'INSTRUMENT, pas deux résultats de capacité

### 6a. A′ — l'E19 sur une tâche au plafond mélange saturation et vitesse d'apprentissage

`recall_same_tick_K6` est une tâche à un seul slot à lire (`kind="recall"`, cible = key) : au premier pas
du sweep (lr=0,02, 150 épisodes), la tâche est si facile que le bras SANS bilinéaire (D) atteint DÉJÀ le
plafond (`med(D)`=1,0000, identique à A=1,0000) — ratio 1,00, X_DECOY, `PIECE_NOT_NECESSARY` à ce point
SEUL. **Le fait le plus tranchant de cette limite** : `noise_band`(A) est elle-même DÉGÉNÉRÉE à ce point
([1,0000 ; 1,0000], `noise_floor.A.band` du JSON — `last` et `noop` valent 1,0 sur les 12 seeds). Une bande
réduite à un seul point rend `in_noise_band=true` non informatif : le harnais ne peut littéralement pas
distinguer, à ce pas, un ratio de 1,000 d'une bande de bruit nulle — ce n'est pas seulement que la piece
`bilinear` semble non nécessaire, c'est que l'INSTRUMENT n'a plus aucune capacité de discrimination à ce
point du sweep. La prédiction scellée (`PIECE_NOT_NECESSARY`) avait été mesurée sur ce même point au smoke (« plain =
bilineaire = 1,0 (same_tick supervise 150 ep., MESURE seeds 0-2 au present smoke) ») — un SEUL pas de lr.
Au second pas (lr=0,002), la tâche redevient discriminante : D2 (sans bilinéaire)=0,8531 reste
significativement sous A2 (avec bilinéaire)=0,9867. `assert_verdict_invariant_to_optimizer` lit cette
réouverture d'écart comme la fermeture d'un artefact (`closure`=1,000, le gap passe de 0,1336 à 0,0000) —
alors que ce que la mesure montre réellement est : à un pas assez grand pour saturer les deux bras
(0,02, 150 épisodes), rien ne distingue « la pièce n'est pas nécessaire » de « la tâche est trop facile
pour discriminer » ; à un pas plus petit (0,002), qui laisse de la marge sous le plafond, un écart réel
apparaît. C'est un **mélange de deux régimes** (saturation représentationnelle vs vitesse d'apprentissage
sous ce pas), pas une propriété de la pièce `bilinear` pour cette tâche. Remède pour R2 : sceller A′ soit
avec le SECOND pas déjà mesuré au smoke comme point de référence primaire (au lieu du point saturant),
soit avec un nombre d'épisodes qui ne sature pas à lr=0,02 (le smoke a mesuré `unit_s`/`noise` mais jamais
la fraction d'épisodes nécessaire pour éviter le plafond à ce pas).

### 6b. B — la garde d'alias exige un contrôle ENTRAÎNÉ, pas seulement présenté

Le split `control` (`tools/harness/tasks/composition.py:53-56` — key re-présentée au pas de réponse) est
conçu comme le bras négatif de `alias_guard_verdict` : une politique qui LIT l'entrée n'a besoin d'aucun
état porté pour le résoudre, donc `state_reset` ne devrait pas y mordre. Mais `_run_arm`
(`tools/harness/cell.py:121-127`) n'entraîne JAMAIS sur `split="control"` — la boucle d'apprentissage
n'appelle que `task.episodes(rng, n, "train")` ; le contrôle n'est évalué (`tools/harness/cell.py:146-148`)
qu'APRÈS l'entraînement, sur l'instance entraînée uniquement sur `train`. La politique a appris à lire
`key` à l'étape 0 et à le porter dans son état — jamais à lire `key` re-présentée à l'étape de réponse, une
capacité qu'elle n'a simplement jamais eu à exercer. `state_reset` casse donc le contrôle NON PARCE QUE
l'état est fonctionnellement partagé entre les deux tâches, mais parce que la politique n'a jamais appris
la voie alternative que le contrôle lui offre. Un contrôle NON ENTRAÎNÉ ne peut pas séparer « l'état est
nécessaire » de « le créneau n'est jamais lu » — c'est exactement ce que documente
`tools/language_memory_demand_probe.py` avec son paramètre `train_control=True` (déjà utilisé par
[[EDR-LOCK-002]], barreau 1b, pour la même distinction). Remède pour R2 : `run_harness_cell` doit
entraîner sur un mélange train/control quand une ablation d'état est déclarée (`site == "state"`), ou la
`Task` doit fournir un contrôle que la politique entraînée sur `train` seul peut déjà résoudre sans
apprentissage supplémentaire.

## 7. Ce que ce record NE tranche PAS

* **Les tâches sont PORTÉES, pas générées.** `CompositionTask` reprend `_make_seq`/`_slot` de
  `tools/bilinear_composition_probe.py` sans copie (bit-identité vérifiée sur la cellule A, seed 0). La
  question Q7 (le harnais génère-t-il ses propres tâches, ou seulement des tâches déjà connues du dépôt ?)
  reste ouverte.
* **La nécessité de `bilinear` mesurée ici est une nécessité D'ACQUISITION À CETTE DOSE**, pas un plafond
  absolu : le plafond `plain` en forme close (34/36 = 0,944, MINORANT jamais prouvé) reste AU-DESSUS de la
  barre d'acquisition (0,944 > 0,2195, la barre — PAS 0,932, qui est la MÉDIANE obtenue par `A` elle-même,
  bilinéaire compris : 0,944 > 0,9320 aussi) — `PIECE_PARTIAL` documente que le plain PEUT composer à ce
  budget d'entraînement, pas qu'il ne composera JAMAIS mieux avec plus de budget.
  `representational_ceiling_above_bar`=true est un fait publié, pas une réfutation.
* **Un seul substrat, une seule famille de pièce testée par cellule.** `connectome_torch` uniquement ;
  aucune généralisation à un autre backend.
* **`without={"feedforward": true}` (cellule B)** entraîne un bras qui n'a JAMAIS porté d'état récurrent,
  pas un bras dont l'état a été gelé après coup — c'est la variante « sans pièce » du registre `PIECES`,
  pas un ablation en aval de l'apprentissage.
* **Aucun bras `sham` n'a réellement tourné dans R1** : `matched_sham` déclare `{"bilinear_sham": true}`
  (A, A′) dans le registre `PIECES`, et la nécessité de A publie `sham`=`DECLARED` sur cette base — mais
  les cinq bras réellement exécutés sont `A, A0, A2, D, D2` (`src/seed_ai/harness_verdict.py:47`), aucun
  sixième bras `sham` n'est lancé par `run_harness_cell`. « DECLARED » documente une existence dans le
  registre, pas une mesure.

## 8. Coût

| cellule | unité scellée (smoke) | unité observée (`actual_s/60`) | `budget_s` (`-ter`, garde) | `projected_s` | `actual_s` | abandons `-bis` (E12) | abandons `-ter` |
|---|---|---|---|---|---|---|---|
| A  | 6,423 s | 3,521 s | 3468,57 s | 1156,19 s | 211,24 s (3,5 min) | A0:[3], A2:[3], D:[2,3], D2:[2,3] | aucun |
| A′ | 3,345 s | 1,431 s | 1806,19 s | 602,06 s | 85,89 s (1,4 min) | aucun | aucun |
| B  | 17,147 s | 8,410 s | 9259,57 s | 3086,52 s | 504,61 s (8,4 min) | D2:[0] | aucun |

Réel total `-ter` : 211,24 + 85,89 + 504,61 = **801,74 s ≈ 13,4 min**, contre un projeté total de
1156,19 + 602,06 + 3086,52 = 4844,77 s ≈ 80,7 min (le `budget_family_s` scellé de `-ter`, 14534,33 s ≈
242 min, est la garde ×3 encore au-dessus du projeté — jamais atteinte). Le temps mur publié dans
`cost.actual_s` est un **MAJORANT mesuré sous la charge observée avant chaque cellule** (E12,
`tools/harness/run_r1.py:26-30`) — le rapport `actual_s`/`projected_s` très inférieur à 1 sur les trois
cellules est cohérent avec la charge tombée entre le smoke et le run `-ter` (§2), jamais avec une
sous-estimation de `unit_s_given` (qui reste la valeur scellée, non recalculée).

⚠️ **Le champ `cout` scellé dans `docs/preregistrations/HARNESS-R1-ter.json` est une PRÉMISSE PÉRIMÉE** :
il décrit encore le budget de `-bis` mot pour mot (« budget PAR CELLULE = 3 × unité × 12 seeds × 5 bras
[…] budget_family_s = 81 min ») — `build_rule_r1_ter` (`tools/harness/seal_r1.py:278-309`) ne dérive QUE
`budget_s`/`budget_family_s`/`remplace`/`raison_ter`/`predictions_chiffrees_AVANT_le_run_note` depuis
`-bis` (§1), jamais `cout`, qui reste donc BIT-IDENTIQUE à `-bis` alors que `-ter` porte en réalité un
budget PAR CELLULE = 9 × unité × 12 × 5 et `budget_family_s` = 14534,33 s = 242 min
(`docs/preregistrations/HARNESS-R1-ter.json`, champ `budget_family_s`, vs le texte du champ `cout` qui
affirme encore 81 min). C'est la classe **E8** (une prémisse est une mesure, pas un décor) : les chiffres
justes sont ceux de la table ci-dessus, recomputés depuis les JSON de résultat, jamais le texte de `cout`.
Dette portée en §9.

## 9. Dettes vues en passant

Trouvées EN CHEMIN, pas l'objet de cette tâche — portées au backlog par le contrôleur à la fusion, pas
éditées ici (CLAUDE.md, § Consigner en passant) :

* **Split `control` jamais entraîné** — `tools/harness/cell.py:121-127` (boucle d'entraînement, `split`
  toujours `"train"`) et `tools/harness/cell.py:146-148` (éval du contrôle sur l'instance entraînée
  seulement sur `train`) ; définition du split : `tools/harness/tasks/composition.py:53-56`. Rend
  `alias_guard_verdict` structurellement aveugle sur `state_reset` de la cellule B (§6b).
* **E19 sensible à un plafond de représentation partagé** — `src/seed_ai/harness_verdict.py:288-330`
  (`_e19`) : `reference_floor` protège contre un bras de RÉFÉRENCE qui s'effondre vers zéro, mais pas
  contre les DEUX bras saturés au plafond au même point du sweep (`gap`=0 par plafond, pas par collapse) —
  exactement le mécanisme de la cellule A′ (§6a).
* **`check_preregistration_applied.py` plante sur un `.json` dont `rule` n'est pas un dict** —
  `tools/check_preregistration_applied.py:105-106,154,217` (`payload.get("rule", {}).get(...)` /
  `json.load(f).get("rule", {})` suppose un dict) ; déjà mesuré comme `AttributeError` en écrivant la
  tâche 10 sur un fichier de provenance dont `rule` était une chaîne (cf. `tools/harness/seal_r1.py:30-37`,
  qui documente pourquoi la provenance de `-bis` est tamponnée sur le SMOKE plutôt que sous
  `docs/preregistrations/`).
* **`assert_verdict_invariant_to_optimizer` (P2.21) protège contre l'effondrement complet de la référence,
  pas contre sa dégradation partielle** — `tools/experiment_preflight.py:303-372` : `reference_floor`
  (ici `bar`, la barre d'acquisition à ~0,19–0,22) est un plancher BAS ; un bras de référence qui se
  dégrade significativement sans franchir ce plancher (ex. 1,0 → 0,70, toujours très au-dessus de la
  barre) n'est protégé par aucun garde-fou de mouvement RELATIF de la référence, seulement par le plancher
  absolu.
* **`budget_s` d'une règle sert de garde de coût mais aucune trace n'assure que le régime PUBLIÉ
  (`data.regime`) a bien été mesuré plutôt que recopié des kwargs du runner** — `tools/harness/cell.py:238-245`
  construit `regime` depuis `task.regime()` et les arguments reçus par `run_harness_cell`, jamais
  re-dérivé d'un comptage indépendant des itérations réellement exécutées.
* **Bris d'égalité du second `lr` de B choisit le plus proche de `sweep0_lr`, jamais le mieux séparé** —
  `tools/harness/seal_r1.py:148` (`lr2 = min(tied, key=lambda lr: abs(lr - sweep0_lr))`) : à médiane
  égale entre deux candidats, celui qui maximiserait la puissance statistique n'est jamais préféré.
* **`ConnectomeLearner.build` ne garde pas `n >= 1`** — `tools/harness/learners/connectome.py:194-199`
  valide `obs_dim` et `K`, jamais `n` (nombre d'agents) : un appel à `n=0` construirait une instance vide
  sans lever, plutôt que de refuser en tête de fonction (le motif « garde en tête » que la dette de
  calibration du dépôt a généralisé ailleurs).
* **`TabularLearner.state_dict` omet `seen_cols`** — `tools/harness/learners/tabular.py:103-104` ne
  sérialise que `{"table": ...}` ; `seen_cols` (colonnes actives vues en apprentissage, ligne 31) n'est pas
  restauré par un rechargement depuis cet état, alors qu'il conditionne les clés filtrées lues par `act`
  (ligne 48-51).
* **Aucun bras `sham` n'a tourné dans R1** — `src/seed_ai/harness_verdict.py:47` (`_ARMS = ("A", "A0",
  "A2", "D", "D2")`), malgré `matched_sham` déclaré dans le registre `PIECES` pour `bilinear` (§7).
* **Le champ `cout` de `-ter` décrit le budget de `-bis`, pas le sien** — `build_rule_r1_ter`
  (`tools/harness/seal_r1.py:278-309`) ne dérive QUE `budget_s`/`budget_family_s`/`remplace`/`raison_ter`/
  `predictions_chiffrees_AVANT_le_run_note` depuis `-bis`, jamais `cout`, qui reste donc hérité
  BIT-IDENTIQUE alors que le budget réel a triplé (§8). Preuve :
  `docs/preregistrations/HARNESS-R1-ter.json`, champ `cout` (texte : « budget_family_s = 81 min ») vs
  champ `budget_family_s` (valeur : 14534,33 s = 242 min). Classe E8.

## Registre

Aucune nouvelle classe d'erreur : `E12` (charge machine non bornée dans la marge de coût, déjà nommée dans
`raison_ter`) et `E19` (nul non invariant au pas, déjà dans `CLAUDE.md` et [[EDR-LOCK-002]]) sont
**mesurées en acte** par ce record, pas ouvertes. Converge [[EDR-LOCK-002]] (même garde E19, même motif
« mélange de deux régimes sous le même pas ») et `tools/language_memory_demand_probe.py::train_control`
(le remède déjà existant pour §6b, jamais câblé dans `tools/harness/cell.py`).
