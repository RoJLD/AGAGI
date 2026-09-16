---
id: EDR-CALIB-LEGACY-LEARNER
type: EDR
title: "L'apprenant LEGACY de l'arc EVO (`MambaBatchModel.compute_policy_gradient`) APPREND la tâche linéaire à un DIXIÈME de son pas publié (11/12 seeds, +0,318 vs lr=0 apparié) et s'EFFONDRE ou DIVERGE à son pas publié (4 seeds à 0,000, 1 seed NaN, 6/12) ; et son W a DEUX auteurs — le gradient et le compilateur NTM, qui survit à un pas nul"
status: active
verdict: LEGACY_LEARNS_AT_LOW_STEP_UNSTABLE_AT_PUBLISHED_STEP_W_HAS_TWO_AUTHORS
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-CALIB-LEARNER, EDR-S2-011]
---

> ⚠️ **CORRIGÉ le 2026-09-15 (soir) — classe E28, mesurée quelques heures après ce record.** La létalité (18 265
> résurrections/seed), les effondrements à 0,000 et le seed NaN étaient un **ARTEFACT** : le World Model PAR AGENT
> (`world_model.py::observe_batch`, SGD brut sur l'observation) diverge dès le tick ~51, son `err` devient NaN, `surprise`
> NaN, `brain_cost` NaN, et le monde faisait `energy = max(0.0, energy - nan)` = 0 — une mort par tick. Mesuré : 669/669 morts
> avaient un Wp non fini ; garder W fini (`LEGACY-NAN-GUARD-R1`) ne changeait rien (ratio 1,00) ; la garde à la SOURCE
> (`LEGACY-WM-GUARD-R1`) rend 139 résurrections (ratio 0,008), 0 effondré, 0 NaN. **Courbe de pas RE-MESURÉE sous garde,
> cinq pas dont la référence** (`LEGACY-LR-CURVE-R2`, `results/legacy_lr_curve_r2.json`, 60 cellules) — branche
> **`APPREND_QUELQUE_PART`, pas 0,001** : lr 0 → 0,126 (référence, 6 résurrections) ; 0,04 → 0,197 (9/12) ; 0,01 → 0,209
> (8/12) ; 0,004 → 0,310 (9/12) ; **0,001 → 0,449 [0,30–0,59], 12/12, 0 effondré, 216 résurrections**.
> **Ce qui tient** : (1) l'apprenant de l'arc EVO apprend la tâche linéaire à pas bas — à 0,001, 12/12 sous garde (0,449,
> contre 0,518 mesuré avec l'artefact) ; la courbe est monotone dans le sens du pas ; le pas publié 0,04 est le plus mauvais ;
> W a deux auteurs (NTM) ; la calibration unitaire. **Ce qui tombe** : « instable au pas publié » (les effondrements et le
> NaN étaient le World Model, pas le gradient : à 0,04 sous garde il est FAIBLE, 0,197, pas instable) ; « la létalité est
> un fait du bras » (18 265 → 140) ; l'addendum (b) « les apprenants meurent par l'énergie » (vrai au sens de `energy = 0`,
> faux au sens d'un puits du monde : c'était `max(0.0, nan)`) ; l'addendum (a) est remplacé par la courbe sous garde
> ci-dessus (0,518 → 0,449 à 0,001 ; 0,446 → 0,310 à 0,004). Gardes posées et testées : `observe_batch` (Wp non fini →
> reset compté), `compute_policy_gradient` (dW non fini → saut compté), `world_1_stoneage` (`brain_cost` non fini → compté,
> pas facturé). Portée AUDITÉE (P2.73 c) : au régime évolutif (`evolve_cognitive`, monde mortel, 3-5 ères, 120-1000 ticks,
> seeds 0-1) `wm_resets` = 0 — la divergence exige des agents qui vivent longtemps sous récompense accumulée (cohorte
> immortelle) ; **l'arc EVO n'est pas touché**, l'artefact était confiné aux mesures legacy à cohorte immortelle du jour.
> Règles scellées de la correction, dans l'ordre : `docs/preregistrations/LEGACY-NAN-GUARD-R1.json` (`PAS_NAN` :
> `ratio_resurrections` 1,00 contre `reference_resurrections` 18 265, `nan_skips` 18 238, `morts_w_non_fini` 0, `effondres` 4,
> `non_mesures` 1), `docs/preregistrations/LEGACY-WM-GUARD-R1.json`
> (`ARTEFACT_WM` : `resurrections` 139 contre `reference_resurrections` 18 265, `wm_resets` 292, `effondres` 0, `non_mesures` 0, `mediane_hit_last` 0,197, `seeds_au_dessus` 8),
> `docs/preregistrations/LEGACY-LR-CURVE-R2.json` (`APPREND_QUELQUE_PART` : par lr `mediane_hit_last`, `seeds_au_dessus`,
> `effondres`, `non_mesures`, `resurrections`, `wm_resets` — tableau ci-dessus).

## Question (backlog P3.4, rang 14)

[[EDR-CALIB-LEARNER]] a calibré l'apprenant **torch** (`use_torch_inworld=True`) : il apprend la tâche
linéaire 1-bit de [[EDR-S2-011]] quand la dose de crédit n'est plus bornée par la mort. Mais le chemin
actif pendant **tout l'arc EVO** est l'autre apprenant : `MambaBatchModel.compute_policy_gradient`
(Actor-Critic TD(0) numpy, `use_torch_inworld=False`, modèle **recréé à chaque tick** par
`_get_batch_model`, W persisté dans `agent.genome.W`). Il n'avait jamais été confronté à une réponse
connue ; le panel du 2026-09-14 l'avait mesuré à n = 1 comme « non plat » (OFF 0,13, naturel 0,35). Les
deux issues étaient nommées d'avance dans le runner : `LEARNER_LEARNS` sur `natural` → l'arc EVO
tournait sur un apprenant capable d'apprendre CETTE tâche ; `LEARNER_INERT` aux deux pas → l'arc EVO
tournait sur un apprenant inerte.

## Méthode

* Même sonde, même compteur, mêmes bras que CALIB-LEARNER : `run_learner_probe(policy="legacy")`
  (cohorte IMMORTELLE, DV = taux de coups `move == int(bit_a > 0)` par bloc de 400 ticks),
  `count_learning_events` étendu au legacy (`legacy_calls` / `legacy_updates`, ΔW mesuré sur les
  GÉNOMES avant/après chaque appel). Les deux pas `LR_ACTOR = 0,04` / `LR_CRITIC = 0,05` sont devenus
  des knobs de classe (bit-identiques) : le bras `lr0_reference` est le **même code à pas nul**, jamais
  un no-op patché.
* Quatre bras appariés par seed : `oracle` (contrôle positif de la DV), `lr0_reference` (plafond de
  l'incapable, mesuré ici), `natural` (0,04 / 0,05, tel que publié), `lr_low` (0,004 / 0,005 — ratio
  critic/acteur gardé ; balayage E19).
* n = **12 seeds** (2026-2037), 12 agents, 2000 ticks ; unité = seed ; `declare_design`, famille de
  contrôles 24 cellules (Bonferroni, α = 0,05) ; coût borné par `project_cost` sur une unité MESURÉE
  (`unit_s` = 78 s ; total **37,8 min** de cellules, `cells_elapsed_s`, sur deux processus — reprise après la cellule non mesurée). Verdict : `learner_verdict` (barre = référence lr=0 + 0,05
  du même run). Régime publié par le runner (bloc `regime`) : identique à CALIB-LEARNER
  (`cog_gain=12.0, base_metabolism=0.75, forage_payoff=0.0, immortal=True, …`). Provenance `02958d9`,
  arbre sale.
* Calibration UNITAIRE, sans monde (`tests/sandbox/test_instrument_calibration.py`,
  `test_learning_events.py`) : premier appel différé ; **signe de l'update PRÉDIT** —
  `sign(ΔW[:, col_move]) == sign(δ·h)` sur les présynaptiques actifs, pour δ > 0 ET δ < 0 ; lr=0
  bit-identique hors NTM ; compteur bit-identique par défaut, coupure, override du pas, restauration.

## Résultats (`results/legacy_learner_calibration.json`)

| bras | hit bloc 1 | hit bloc 5 (méd.) | appels / updates legacy | Σ‖ΔW‖ (méd.) | résurrections (méd./seed) | sep. vs lr0 apparié | seeds > lr0 + 0,05 |
|---|---|---|---|---|---|---|---|
| oracle | 1,000 | **1,000** | 0 / 0 | 0 | 0 | — | — |
| lr0_reference | 0,132 | **0,128** | 2000 / 180 | 814 | 1 717 | — | — |
| natural (0,04) | 0,207 | **0,249** | 2000 / 55 | 118 311 | **18 265** | +0,121 | **6/12** (1 non mesuré) |
| lr_low (0,004) | 0,260 | **0,446** | 2000 / 88 | 12 776 | 10 206 | **+0,318** | **11/12** |

Par seed, bloc 5 — `natural` : 0,51 · **0,000** · **0,000** · **0,000** · **NaN** · 0,51 · **0,000** ·
0,30 · 0,30 · 0,49 · 0,25 · 0,16 ; `lr_low` : 0,37 · 0,59 · 0,52 · 0,14 · 0,46 · 0,22 · 0,54 · 0,45 ·
0,32 · 0,44 · 0,55 · 0,42 ; `lr0_reference` : 0,05-0,21 (chance 1/8 = 0,125).

Les quatre seeds de `natural` à **0,000** ne sont pas « à la chance » : ils sont SOUS la chance, sur
une réponse déterministe FAUSSE (trajectoire 0,207 → 0,085 → 0,0 → 0,0 → 0,0) — les poids saturent au
clip ±5 et la politique devient bang-bang. Le seed 2030 **diverge** : NaN dans les logits (le logger
KuzuDB refuse « Variable nan »), plus AUCUNE décision, `run_learner_probe` refuse de fabriquer un taux
— cellule publiée avec sa raison, comptée dans n et au dénominateur du test des signes.

**Garde E19** (`natural` @0,04 vs `lr_low` @0,004, référence oracle) : `INVARIANT_AU_PAS` — les deux
bras rendent `LEARNER_LEARNS` à la médiane. Mais le test des signes les sépare : 6/12 contre 11/12
(convention de puissance du dépôt : ≥ 11/12, p ≤ 0,0032).

## Verdict

**`LEGACY_LEARNS_AT_LOW_STEP_UNSTABLE_AT_PUBLISHED_STEP_W_HAS_TWO_AUTHORS`**

1. **L'apprenant de l'arc EVO SAIT apprendre la tâche linéaire** — à `lr = 0,004` : 11/12 seeds
   au-dessus de la référence appariée, séparation médiane +0,318, gain +0,186 pendant le run. C'est
   davantage que l'apprenant torch de CALIB-LEARNER au même horizon (0,446 contre 0,277-0,283).
2. **À son pas PUBLIÉ (0,04), il est INSTABLE** : bimodal — 2 seeds à 0,51, 4 seeds effondrés à 0,000
   (sous la chance), 1 seed NaN, 6/12 au-dessus de la référence. `learner_verdict` rend `LEARNER_LEARNS`
   sur la médiane ; la LECTURE honnête est : un apprenant qui apprend ou s'effondre selon le seed, ce
   qui, à n = 1, donne n'importe quel verdict. Le panel a vu 0,35 à n = 1 : dans la bande.
3. **La létalité est un fait du bras, pas du monde** : `natural` ressuscite **18 265** fois par seed
   (≈ 0,76 mort par agent et par tick), `lr_low` 10 206, `lr0` 1 717, l'oracle 0. Dans ce régime, la
   récompense `Δénergie` du tick est dominée par des morts (−80) et non par le `cog_gain` (12) : la
   cohorte « immortelle » est une chaîne de résurrections. Ce qui tue n'est pas mesuré ici (même
   candidats que CALIB-LEARNER : lancers entre pairs, riposte du gibier). Un run MORTEL de l'arc EVO
   sous cet apprenant a donc une dose bornée par sa propre létalité — et à un pas qui l'effondre.
4. **W a DEUX auteurs, et le second survit à un pas nul.** À `lr = 0`, W bouge quand même (180 updates
   médians sur 2000 ticks ; 299/300 hors monde) : ce n'est pas le clip, c'est le **compilateur
   d'auto-câblage NTM** (`NTMProgramCompiler.compile_and_apply`, appelé dans `forward`, écrit `W_batch`
   depuis les slots mémoire ; `compute_policy_gradient` le persiste dans `genome.W`) — `ABLATE_NTM=True`
   → 0/300. La prémisse « lr=0 ⇒ W figé », vraie du backend torch, était FAUSSE du legacy (E8 occ. 5 au
   registre) : le plafond de l'incapable se lit sur la DV (0,128 = chance), pas sur la supposition que W
   est figé. Conséquence pour l'arc EVO : « les champions évolués sont 60× plus sparses et gèlent »
   ([[EDR-EVO-001]]) se lit à côté d'un organe qui réécrit W à chaque tick indépendamment du gradient.

## Ce que ça change, et ce que ça ne change pas

* [[EDR-EVO-005]] tire son poids d'une CONVERGENCE : « le crédit échoue (S2-010) ET la sélection échoue
  → le verrou est le paysage ». CALIB-LEARNER a montré que le nul du crédit était un nul de DOSE ; ce
  record montre que l'apprenant de l'arc EVO apprend à pas réduit et s'effondre au pas publié. **La jambe
  « crédit » de la convergence est retirée, deux fois.** Le résultat de SÉLECTION d'EVO-005 (plafond
  0,500, saillance 0) tient tel quel ; sa lecture « paysage » n'a plus qu'une jambe. Bandeau posé,
  verdict non modifié.
* **PAS un résultat sur la survie** : cohorte immortelle, `forage_payoff = 0`, un banc, une tâche.
* **PAS une recommandation de pas** : 0,004 est le seul autre point mesuré ; la courbe n'est pas tracée.
  → *Tracée le jour même, voir l'addendum ci-dessous (règle `LEGACY-LR-CURVE-R1`).*
* Ce que la calibration a coûté à croire : « ~5 min de calcul » (backlog) — l'unité mesurée était de
  78 s et le run de 37,8 min ; et « lr=0 ⇒ W figé », attrapée par le compteur, pas par moi.

> ⚠️ **BANDEAU DE PORTÉE, posé le 2026-09-16 APRÈS le verdict — deux prémisses de ce record étaient des
> décors, pas des mesures (E8), et elles sont désormais publiées par le runner.**
> **(1) lr/B — E19 occ. 7.** Le bras `torch` comparé ici tourne sous `TorchPopulationModel` : W disjoint par
> agent, perte MOYENNÉE sur B = 12, SGD (`backend_torch.py:117, 219-221`) — le pas RÉELLEMENT appliqué à un agent
> est **lr/12**. « Torch à 0,04 » vaut donc **0,0033 par agent**, et la phrase « le legacy à 0,004 bat torch à
> 0,04 » compare 0,004 à 0,0033 : à pas effectif quasi ÉGAL, le legacy (+0,318) et torch (+0,156, CALIB-LEARNER)
> sont deux règles différentes au même pas, pas une règle à un pas dix fois plus petit. Vérifié par PRÉDICTION
> (`tests/sandbox/test_torch_effective_step.py` : ΔW(B=1) = 12,000 · ΔW(B=12)) ; `count_learning_events` publie
> désormais `lr_effective_per_agent` à côté de `lr`. Les chiffres de ce record sont inchangés ; leur LECTURE
> comparative l'est.
> **(2) Activation — E29 occ. 1.** Le legacy a tourné sous **Swish** (`src/metaprog/sandbox/generated_ops.py`,
> écrit par la boucle métaprog, ignoré par git, ABSENT de HEAD, rechargé à chaque pas) — pas sous `tanh`. Un
> clone qui rejoue R1/R2 sans ce fichier tourne en tanh et n'est PAS bit-identique. Le runner publie désormais
> `regime.legacy_activation` (source / nom / sha256 / `versioned: False`) et `_pinned_substrate` gèle le hash
> présent pour la durée du run (`mamba_agent.pinned_activation`). Le sha256 sous lequel R1/R2 ont tourné n'a
> pas été enregistré à l'époque — il est INCONNU ; le fichier présent le 2026-09-16 (mtime 01:07, réécrit par
> un run cette nuit) est Swish, comme celui d'EDR-139. Dette : décider si le fichier est versionné (backlog).

## Addendum (2026-09-15, P2.72 a) — la courbe de pas : l'instabilité n'est pas un seuil, c'est une pente

Règle scellée avant toute cellule (`docs/preregistrations/LEGACY-LR-CURVE-R1.json`), même dispositif, mêmes 12
seeds, référence lr=0 importée par seed ; résultats `results/legacy_lr_curve_r1.json` (30 min). **Branche scellée :
`SEUIL_ENTRE_0001_ET_001`.**

Grandeurs scellées, telles que publiées par la lecture : `mediane_hit_last` (colonne « hit bloc 5 »),
`seeds_au_dessus` (colonne « seeds > lr0 + 0,05 »), `effondres`, `non_mesures` (colonne « NaN » : 0 et 0),
`legacy_updates` (79,5 à 0,01 ; 109 à 0,001) et `dW_abs_sum` (22 723 à 0,01 ; 4 774 à 0,001 — cinq fois moins de
mouvement de poids pour un meilleur taux).

| lr | hit bloc 5 (méd.) | seeds > lr0 + 0,05 | effondrés (≤ 0,01) | NaN | résurrections (méd.) | source |
|---|---|---|---|---|---|---|
| 0,04 (publié) | 0,249 | 6/12 | 4 | 1 | 18 265 | ce record |
| 0,01 | 0,303 | 8/12 | 1 | 0 | 16 067 | R1 |
| 0,004 | 0,446 | 11/12 | 0 | 0 | 10 206 | ce record |
| **0,001** | **0,518** [0,40–0,74] | **12/12** | 0 | 0 | 5 817 | R1 |
| 0 (référence) | 0,128 | — | — | — | 1 717 | ce record |

Trois faits, tous dans le sens du pas : (a) le taux de coups **monte** quand le pas baisse, jusqu'au point le plus bas
mesuré — 0,001 fait mieux que 0,004 (0,518 contre 0,446), et le seed 2030, NaN à 0,04, y apprend à 0,591 avec ses
2000 mises à jour ; (b) les effondrements s'éteignent avec le pas (4 → 1 → 0 → 0) ; (c) la **létalité** aussi
(18 265 → 16 067 → 10 206 → 5 817 résurrections) — un apprenant à grand pas est un apprenant qui se fait tuer. Le
« plafond » d'apprentissage n'est donc pas atteint : plus bas que 0,001 n'est pas mesuré (2000 ticks ; à 0,001 les
cellules coûtent 2-4× plus — le coût suit le succès). Ce que ça ne dit pas : la valeur asymptotique, ni si la
létalité est cause ou conséquence de l'instabilité (P2.72 b : `cause_de_mort` désormais publiée par la sonde).

## Addendum (2026-09-15, P2.72 b) — ce qui tue : l'ÉNERGIE, jamais les hp

Règle scellée avant toute cellule (`docs/preregistrations/LEGACY-CAUSE-DE-MORT-R1.json`), 3 bras × 12 seeds, même
dispositif ; `run_learner_probe` publie `cause_de_mort` (énergie ≤ 0 / hp ≤ 0 / les deux / `AUCUNE`), compté AVANT la
recharge ; résultats `results/legacy_cause_de_mort.json` (22,5 min). **Branche scellée : `ENERGIE`.** Grandeurs
scellées : `part_energie` / `part_hp` / `part_les_deux` (médianes par seed), `aucune`, `resurrections`.

| bras | `part_energie` | `part_hp` | `part_les_deux` | `aucune` | résurrections (méd.) | seeds sans mort |
|---|---|---|---|---|---|---|
| natural (0,04) | **1,000** | 0 | 0 | 0 | 18 265 | 0 (1 seed NaN, non mesuré — le même 2030 qu'au run principal) |
| lr_low (0,004) | **0,99994** | 0,00006 | 0 | 0 | 9 967 | 0 |
| lr0_reference | **1,000** | 0 | 0 | 0 | 1 708 | 3 |

Les apprenants meurent **par l'énergie**, jamais par les hp : la riposte du gibier et l'attrition (canaux hp) sont hors de
cause. Reste, côté énergie, le drain et le projectile d'un pair — **non départagés ici** ; l'argument « la recharge remet
l'énergie à 80 sous 30, un drain de 0,75/tick ne peut pas tuer en un tick, donc c'est le projectile » est une INFÉRENCE
(E8), plausible et non mesurée : elle demande de compter les lancers reçus par agent, ce que la sonde ne fait pas encore.
Fait annexe : `AUCUNE` = 0 sur 36 cellules (aucun vivant ressuscité — l'instrument est sain), et les résurrections du
bras natural sont bit-identiques à celles du run principal (18 265) : le dispositif est déterministe par seed.
