---
id: EDR-LOCK-002
type: EDR
title: "La rétention à DEUX délais s'apprend sous REINFORCE au bon pas (4,85×, n=12, garde d'alias SURGICAL) — la « quatrième manifestation » de LOCK-001 était un nul à pas fixe (E19), pas un mur"
status: active
verdict: D2_RETENTION_LEARNED_FOURTH_MANIFESTATION_WAS_E19
gate: G1
tests: [SDR-G1]
adopts: [REF-DEMAND-MARKER]
extends: [EDR-LANG-MEMORY-EDGE-BIS]
corrects: [EDR-LOCK-001]
---

## Question et règles scellées

[[EDR-LOCK-001]] rapportait une **quatrième manifestation** du mur : au point-référence où la
rétention à un tick s'apprend (bilinéaire, `lr=0.002`, 3600 épisodes, médiane 0,744), la MÊME tâche à
**D=2 reste 3/3 à la chance** (0,211 / 0,183 / 0,170), contrôle dégradé (~0,55). Le plan du 2026-09-14
(P4.5) prescrivait d'attaquer ce mur là où il a de la marge, **dans l'ordre du dépôt** — épisodes plus
longs → curriculum → amorçage — et de confronter tout nul à l'optimiseur (E19).

**Barreau 1** — règle scellée AVANT la première cellule, `docs/preregistrations/LOCK-001-PROXY-R1.json` :
D=2, même point, épisodes 7200 et 14400 à `lr=0.002`, **plus un second pas `lr=0.0005` sur le
barreau du haut** (clause E19). Six branches en ordre imposé (INCOMPLET, PERCE_INDICATIF,
PERCE_PAR_LR, TENDANCE, NE_PERCE_PAS, AUTRE), seuils justifiés (0,40 « au-dessus du plafond 0,3889 de
la forme séparable » — ⚠️ chiffre RÉFUTÉ le 2026-09-08 (cf. EDR-BILINEAR) : la barre reste celle
scellée, sa justification valide est « nettement au-dessus de la chance 0,167 et de tout D=2 mesuré
avant » ; 0,30 par seed ; delta 0,10 = deux fois l'écart inter-seeds de la référence), branche
AUTRE prouvée VIDE sur le continuum des médianes (`tests/sandbox/test_lock001_proxy_r1.py`). n=3,
exploratoire : aucune branche ne grave.

**Barreau 1b** — règle scellée avant le run, `docs/preregistrations/LANG-MEMORY-EDGE-D2.json` :
le protocole de [[EDR-LANG-MEMORY-EDGE-BIS]] tel quel (harnais `tools/lang_memory_edge_run.py`,
`EDGE_RULE=LANG-MEMORY-EDGE-D2`), transposé au point qui a percé. Point de fonctionnement LU PAR LE
HARNAIS depuis la règle (`verify` avant toute cellule) : `D=2, K=6, n_agents=16, lr=0.0005,
episodes=14400, control_train_every=1, control_input_noise=0.15`, bilinéaire, `n_seeds=12`, barre 0,5.
Bruit de contrôle 0,15 parce qu'au barreau 1 le contrôle saturait à 1,0/1,0 (la garde d'alias eût rendu
DEGENERATE_CONTROL) ; population NEUVE, jamais mélangée aux 3 seeds du barreau 1. Branches : alias →
PRESENT → PRINCIPAL → barre, la première qui mord arrête.

## Résultats

**Barreau 1** (`results/lock001_proxy_r1.json`, 9 cellules, 75 min CPU réels — projeté 105 à charge
connue, un job in-world tenant `kuzu`) :

| `lr` | épisodes | `lang_i` (seeds 0/1/2) | `lang_a` | `ctrl_i` |
|---|---|---|---|---|
| 0,002 | 7 200 | 0,153 / 0,162 / 0,186 | 0,16–0,18 | **0,24–0,44** (dégradé) |
| 0,002 | 14 400 | 0,178 / 0,167 / 0,156 | 0,15–0,17 | **0,29–0,31** (dégradé) |
| **0,0005** | 14 400 | **0,837 / 0,781 / 0,784** | 0,16–0,19 | 0,98–1,0 |

Grandeurs scellées, telles que lues par `python tools/lock001_proxy_r1.py --lecture` :
`mediane_7200`=0,162 · `mediane_14400_lr0002`=0,167 · `mediane_14400_lr00005`=**0,784** ·
`reference_3600`=0,183 (`results/lang_memory_sweep.json`, lr=0.002|ep=3600|D=2) ; `ctrl_a`=1,0 partout
(0,992 sur une cellule) — le contrôle ablaté reste au plafond, seul `ctrl_i` se dégrade à `lr=0.002`.

Branche : **`PERCE_PAR_LR`**. Les épisodes seuls ne font rien à `lr=0.002` — et le contrôle
feedforward y est *lui aussi* dégradé, signe que le pas est du mauvais côté pour les deux tâches.

**Barreau 1b** (`results/lang_memory_edge_d2.json`, 24 cellules, n=12) :

| bras | verdict `ablation_verdict` | intact méd | ablaté méd | ratio |
|---|---|---|---|---|
| PRINCIPAL (learned, D=2) | **X_DEMANDED** | **0,814** [0,76–0,87] | 0,168 [0,14–0,20] | **4,85** |
| PRESENT (clé re-montrée) | **X_DECOY** | 0,941 [0,89–0,98] | 0,859 [0,80–0,93] | 1,10 |
| CONTROL (garde `alias_guard_verdict`) | **SURGICAL** → functional_aliasing=**pass** | ≈0,86 | ≈0,88 | `leakage`=0,028 |

`leak_seeds`=0 · barre : `coord_intact`=0,814 ≥ `emergence_bar`=0,5 · plafond de contrôle prédit
0,875, mesuré `ctrl_i`≈0,86 / `ctrl_a`≈0,88 (l'injection à dose connue se comporte comme annoncé).

## Verdict

**`D2_RETENTION_LEARNED_FOURTH_MANIFESTATION_WAS_E19`** — branche scellée « mur_perce » (les quatre
lectures positives, dans l'ordre imposé).

1. **La rétention à deux délais S'APPREND sous crédit REINFORCE au bon pas.** Effacer l'état porté
   (H-reset) entre l'encodage et l'usage effondre la tâche à la chance (0,814 → 0,168) pendant que le
   même reset laisse indemnes la tâche à information redondante (0,941 → 0,859) et la tâche
   feedforward (fuite 0,028). C'est la démonstration de [[EDR-LANG-MEMORY-EDGE-BIS]] (D=0, 4,97×)
   **transposée à D=2** (4,85×) : l'arête language→memory est la même, son evidence s'ÉTEND d'un
   délai à deux. Aucune arête nouvelle n'entre dans le graphe.
2. **La quatrième manifestation de LOCK-001 était un nul à pas fixe.** À `lr=0.002`, D=2 reste à la
   chance quel que soit le nombre d'épisodes (3600, 7200, 14400) — et son contrôle est dégradé ; à
   `lr=0.0005`, 12/12 seeds apprennent. C'est le motif exact de [[EDR-RETAIN-COMPOSE-LR]]
   (0,02 → 0,173 / 0,002 → 0,923) un cran plus bas sur l'échelle des pas, et il a été attrapé parce
   que la clause E19 était **scellée avant le run** : sans le second `lr`, la branche eût été
   `NE_PERCE_PAS` et le levier « épisodes » déclaré épuisé.
3. **Le levier qui perce est le PAS, pas la durée** : à `lr=0.002`, 4× plus d'épisodes ne changent
   rien ; à `lr=0.0005` et 14 400 épisodes, tout change. Le point-référence (choisi sur D=0) avait un
   pas trop grand pour D=2 — une tâche à deux délais a un gradient plus bruité par pas, ce que le
   contrôle dégradé disait déjà.

## Portée — ce que ce record N'ÉTABLIT PAS

* **Rien sur l'identité des trois murs** (le cœur de LOCK-001) : ce record retire la quatrième
  manifestation comme *preuve* de l'identité — il ne teste ni EVO-016 (régime de recherche), ni
  DELAYED-COORD (coordination référentielle, `lr=0.05` puis 0,002), ni EDR-156/157. La prédiction
  n° 2 de LOCK-001 (« un levier qui perce UN fil sans effet sur les autres RÉFUTE l'identité ») est
  désormais **testable** : le pas perce ici ; perce-t-il DELAYED-COORD à `lr=0.0005` ?
  **Premier barreau du test, mesuré le jour même** (règle scellée `docs/preregistrations/LOCK-001-PRED2-R1.json`,
  `results/lock001_pred2_r1.json`, 18 cellules) : branche **`SANS_REFERENCE`**. Au point exact de ce
  record (bilinéaire, D=2, `sender_lr`=0,05 fixe), la référence PRESENT — qui ne demande AUCUNE rétention
  — reste sous 0,30 aux trois points (`PRESENT_intact` 0,270 / 0,245 / 0,259 ; `RETAIN_intact` 0,195 /
  0,256 / 0,245 ; `ablated` RETAIN 0,14–0,18, PRESENT ≡ intact, l'ablation y étant un no-op exact),
  là où elle atteint 0,40 à `lr=0.05` sur plain (n=12). La clause E19 scellée interdit
  toute lecture de RETAIN sur un point où la référence n'apprend pas : **ni soutien, ni réfutation**. Ce
  que ça dit : le levier « baisser le pas » n'est pas transportable tel quel — sur la tâche de
  coordination, la référence apprend à un pas ÉLEVÉ. Barreau 2 : trouver d'abord où PRESENT apprend sur
  bilinéaire (balayage `lr`), puis y tester RETAIN.
  **Barreaux 2-4, mesurés dans la nuit du 14 au 15** (règles `LOCK-001-PRED2-R2/R3/R4`, résultats
  `results/lock_001_pred2_r{2,3,4}.json`, n=3 chacun) : (2) sur bilinéaire, `SANS_REFERENCE` aux quatre
  pas — PRESENT ≈ 0,26 partout : **le substrat qui débloque la mémoire casse la référence de
  coordination** ; (3) sur plain à 3 600 ép., `AUTRE` — la référence apprend à pas élevé (0,48 à 0,05),
  RETAIN monte à pas bas (0,331 à 0,002), les deux bras tirent en sens inverse du pas ; (4) **sur plain à
  14 400 ép., `PERCE`** — à `lr=0.0005`, `RETAIN_intact` 0,422 / 0,438 / 0,439 (médiane 0,438 ≥ 0,40,
  3/3 > 0,30), `PRESENT_intact` 0,347. Le même levier — pas bas ET durée — perce le second fil : la
  prédiction n° 2 est **soutenue** à n=3 ; n=12 scellé avant toute gravure (`LOCK-001-PRED2-N12`)
  — **mesuré le 2026-09-15 : `PERCE` à n=12 (0,420, 12/12), gravé dans [[EDR-LOCK-003]].**
* ~~**`lr=0.0005` n'a été mesuré qu'à 14 400 épisodes.**~~ **Mesuré le jour même (barreau 1c, règle
  scellée `docs/preregistrations/LOCK-001-PROXY-R1c.json`, `results/lock_001_proxy_r1c.json`)** : à
  **3 600 épisodes** — le nombre d'épisodes du point-référence — `lr=0.0005` donne
  `mediane_3600_lr00005`=**0,503** (0,523 / 0,503 / 0,420 ; `lang_a` 0,16–0,18 ; `ctrl_i`=`ctrl_a`=1,0),
  contre `reference_14400_lr00005`=0,784 et 0,18 à `lr=0.002`. Branche **`PAS_SEUL`** : le pas seul
  fait franchir la barre 0,40 au point-référence ; la durée amplifie (0,50 → 0,78), elle ne
  débloque pas. La quatrième manifestation tenait à UN paramètre. n=3, indicatif.
* **Rien in-world** : proxy, substrat bilinéaire, K=6, 16 agents ; unité = seed.
* **Population 1b ≠ population barreau 1** (bruit de contrôle 0,15) : les deux se rapportent
  séparément, jamais fusionnées ; les 3 seeds du barreau 1 sont indicatifs, les 12 de 1b portent le
  verdict.

## Registre

E19, occurrence : un nul 2-pas à pas fixe déclaré comme mur (« ni la capacité, ni le pas ne
suffisent » — le pas n'avait pas été balayé), corrigé par la clause scellée. La règle qui en sort
est déjà dans le pré-vol : `assert_verdict_invariant_to_optimizer` ou un second pas scellé sur
**tout** nul sous gradient, avant toute citation.

Converge [[EDR-LANG-MEMORY-EDGE-BIS]], [[EDR-RETAIN-COMPOSE-LR]], [[EDR-LOCK-001]],
[[EDR-DELAYED-COORD]], [[lock001-d2-wall-is-learning-rate-artifact]].
