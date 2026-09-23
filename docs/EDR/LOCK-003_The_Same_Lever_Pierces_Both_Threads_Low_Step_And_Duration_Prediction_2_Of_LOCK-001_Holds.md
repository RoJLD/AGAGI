---
id: EDR-LOCK-003
type: EDR
title: "Le MÊME levier perce les deux fils — pas bas ET durée font apprendre la rétention différée du fil coordination (0,42 vs 0,17, 12/12 seeds, n=12) comme celle du fil mémoire : la prédiction n° 2 de LOCK-001 tient à puissance"
status: active
verdict: SAME_LEVER_PIERCES_BOTH_THREADS_PREDICTION_2_HOLDS
gate: G1
tests: [SDR-G1]
adopts: [REF-DEMAND-MARKER]
extends: [EDR-LOCK-002, EDR-LOCK-001, EDR-DELAYED-COORD]
---

## Question et règles scellées

[[EDR-LOCK-001]] affirme que trois fils — écriture apprise dans le report, compétence composée,
régime de recherche — creusent **un seul mur**, et rend l'affirmation falsifiable par sa clause n° 2 :
*un levier qui perce UN fil sans effet sur les autres RÉFUTE l'identité*. [[EDR-LOCK-002]] a mesuré
le levier sur le fil mémoire : **pas bas + durée** (`lr=0.0005`, 14 400 épisodes) font apprendre la
rétention à deux délais (4,85×, n=12). Ce record applique le même levier au fil **coordination
référentielle différée** ([[EDR-DELAYED-COORD]], bras RETAIN), dont le n=12 sur substrat plain
plafonnait à `RETAIN_intact` 0,284 (`lr=0.002`, 1 600 ép.).

**Escalier scellé, un barreau à la fois, chaque règle avant son run** (`docs/preregistrations/`,
résultats `results/lock_001_pred2_*.json`) :

| barreau | règle | régime | branche scellée | ce qu'on a appris |
|---|---|---|---|---|
| 1 | `LOCK-001-PRED2-R1` | bilinéaire, 3 600 / 14 400 ép., lr 0,002 / 0,0005 | `SANS_REFERENCE` | PRESENT (sans rétention) n'apprend à aucun point : rien ne se lit |
| 2 | `-R2` | bilinéaire, 3 600 ép., lr 0,05 → 0,0005 | `SANS_REFERENCE` | PRESENT ≈ 0,26 à tous les pas — **le substrat bilinéaire casse la référence de coordination** |
| 3 | `-R3` | **plain**, 3 600 ép., lr 0,05 → 0,0005 | `AUTRE` | PRESENT apprend à pas élevé (0,48), RETAIN monte à pas bas (0,33) — sens inverses |
| 4 | `-R4` | plain, **14 400 ép.**, lr 0,002 / 0,0005 | `PERCE` (n=3) | RETAIN 0,422 / 0,438 / 0,439 à 0,0005 |
| **N12** | `-N12` | plain, 14 400 ép., lr 0,0005, **seeds 0-11, population neuve** | **`PERCE`** | ci-dessous |

Règles scellées de l'escalier, par chemin : `docs/preregistrations/LOCK-001-PRED2-R1.json`, `docs/preregistrations/LOCK-001-PRED2-R2.json`, `docs/preregistrations/LOCK-001-PRED2-R3.json`, `docs/preregistrations/LOCK-001-PRED2-R4.json`, `docs/preregistrations/LOCK-001-PRED2-N12.json` (rattachement explicite, porte `check_preregistration_applied`, 2026-09-16).

La clause E19 est dans chaque règle : **un point ne se lit que si PRESENT y apprend** (médiane ≥ 0,30)
— un nul à référence effondrée est `SANS_REFERENCE`, jamais un nul. Le n=12 exige ≥ 11/12 seeds au-dessus
de 0,30 (test des signes unilatéral, p ≤ 0,0032 — la convention de puissance de DELAYED-COORD) et un
contrôle interne : si PRESENT dépassait RETAIN de plus de 0,10, l'effet serait global et le verdict
`AUTRE`.

Point de fonctionnement LU PAR LE RUNNER depuis la règle (`verify` avant toute cellule) : plain
(`bilinear=False`), D=2, K=6, V=8, `n_agents`=16, `flip_p`=0, crédit `bptt`, `choice_decoy=False`,
`sender_lr`=0,05 **fixe**, `lr`=0,0005, 14 400 épisodes — identique au n=12 de DELAYED-COORD sauf le
pas (0,002 → 0,0005) et la durée (1 600 → 14 400).

## Résultats (n=12, `results/lock_001_pred2_n12.json`, 24 cellules, 2,6 h CPU)

| bras | intact méd. [min–max] | ablaté (H-reset) méd. | seeds > 0,30 |
|---|---|---|---|
| **RETAIN** (`RETAIN_intact`) | **0,420** [0,400–0,439] | 0,170 [0,134–0,180] | **12/12** |
| PRESENT (`PRESENT_intact`, référence) | 0,334 [0,295–0,373] | ≡ intact (no-op exact, cf. DELAYED-COORD) | 11/12 |

`ablated` RETAIN à la chance (1/K = 0,167) : effacer l'état porté entre l'encodage et l'usage ramène la
coordination différée à la chance — `ablation_verdict` (hors règle, indicatif) rend `X_DEMANDED`, ratio
2,47. Référence ≥ 0,30 : le point se lit. Contrôle interne : PRESENT < RETAIN, aucun effet global.

**Branche scellée : `PERCE`.**

## Verdict

**`SAME_LEVER_PIERCES_BOTH_THREADS_PREDICTION_2_HOLDS`**

1. **Le fil coordination apprend la rétention différée au même levier que le fil mémoire.** Sur
   plain, à `lr=0.0005` et 14 400 épisodes, RETAIN passe de 0,284 (meilleur n=12 connu) à **0,420**,
   12/12 seeds, ablation à la chance. Chemin complet : 1 600 ép. → 0,284 ; 3 600 → 0,331 ; 14 400 →
   0,353 (`lr=0.002`) / **0,420** (`lr=0.0005`). Le levier est le même qu'en LOCK-002 : **pas bas
   ET durée** — ni l'un ni l'autre seul.
2. **La prédiction n° 2 de LOCK-001 tient à puissance.** La clause de réfutation (« un levier qui
   perce un fil sans effet sur les autres ») ne s'applique pas : le levier perce les deux fils testés.
   L'identité des trois murs survit à son premier test falsifiable — elle n'est pas *prouvée* (le
   troisième fil, régime de recherche, n'est pas testé ici), elle est *non réfutée là où elle pouvait
   l'être*.
3. **Le SUBSTRAT est un paramètre de l'identité, pas un détail.** Le bilinéaire, qui débloque la
   mémoire (LOCK-002), **casse la référence de coordination** (barreau 2 : PRESENT ≈ 0,26 à tous les
   pas contre 0,48 sur plain). Un même mur, deux substrats favorables différents : l'identité est une
   identité de *levier*, pas de *réglage*.
4. **Les deux bras tirent en sens inverse du pas** (barreau 3, réplique le 12/12 inverse du n=12 de
   DELAYED-COORD) : la référence sans rétention préfère un pas élevé, le bras à rétention un pas bas.
   Une optimisation à pas unique ne peut donc pas servir les deux — ce que la re-mesure du 2026-09-02
   à `lr=0.002`/800 ép. avait vu sans pouvoir le lire.

## Portée — ce que ce record N'ÉTABLIT PAS

* **PAS l'arête AGI-Taxonomy** : le contrôle de spécificité reste structurellement vacueux dans ce
  design (`choice_decoy=False` → l'ablation de PRESENT est un no-op exact, cf. DELAYED-COORD). Aucune
  arête n'entre dans le graphe.
* **PAS le troisième fil** (régime de recherche, [[EDR-EVO-016]]) : l'identité est testée sur deux
  fils sur trois.
* **PAS « écriture apprise » au sens fort** : 0,42 est nettement au-dessus de la chance (0,167) et de
  tout RETAIN mesuré (≤ 0,284), et l'ablation le ramène à la chance ; mais c'est loin du 0,78 du fil
  mémoire — la coordination différée reste une tâche plus dure, ou moins bien réglée (28 800 ép. non
  mesurés).
* ⚠️ **Justification de la barre 0,40, à lire avec précaution.** Les règles R1→N12 la justifient
  comme « au-dessus du plafond 0,3889 de la forme séparable » — or ce plafond a été **RÉFUTÉ le
  2026-09-08** (la forme close du plain compose parfaitement, cf. EDR-BILINEAR). La barre reste
  celle scellée avant chaque run et n'a pas bougé ; sa justification valide est : nettement
  au-dessus de la chance et de tout RETAIN mesuré avant. Même remarque pour LOCK-002 (corrigée
  dans son texte le jour même).
* n=12 seeds, unité = seed ; un seul point (plain, 0,0005, 14 400) porte le verdict — les barreaux 1-4
  sont exploratoires (n=3) et ne fondent rien seuls.

Converge [[EDR-LOCK-001]], [[EDR-LOCK-002]], [[EDR-DELAYED-COORD]], [[EDR-RETAIN-COMPOSE-LR]],
[[lock001-d2-wall-is-learning-rate-artifact]].
