---
id: EDR-S2-REWARD-ABLATION
type: EDR
title: "Δénergie SEULE érode le bassin DAgger exactement autant que la récompense complète (survie 36,0 → 8,0 dans les deux bras, écart médian −28,5 vs −28,25, 12/12 seeds, différence appariée 0,0) — le mur est le MÉCANISME DE CRÉDIT, pas la récompense ; et la curiosité de la récompense in-world est MORTE sous torch depuis toujours (pré-vol)"
status: active
verdict: CREDIT_ERODE_SEUL_PLEIN_THE_WALL_IS_THE_CREDIT_MECHANISM_NOT_THE_REWARD_AND_CURIOSITY_WAS_DEAD
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-CREDIT-RETENTION, EDR-CALIB-LEARNER, EDR-WARM-003]
corrects: [EDR-S2-CREDIT-RETENTION]
---

## Question (backlog, bloc « 🧭 2026-09-14 », rang 4 bis — P4.8 ; règles scellées AVANT toute cellule)

[[EDR-S2-CREDIT-RETENTION]] a établi que le crédit in-world publié, appliqué sans être borné par la mort,
EFFACE le bassin DAgger de [[EDR-WARM-003]] (survie 36,0 → 8,0, 12/12 seeds) et en tirait une hypothèse
mécaniste : la récompense qu'il optimise étant `Δénergie + curiosité + nouveauté`
(`src/worlds/world_1_stoneage.py:1713`), **le crédit poursuivrait les deux termes intrinsèques plutôt que
l'énergie**. Ce run l'ablate. Règles : `docs/preregistrations/S2-REWARD-ABLATION.json` (design original à
cinq bras : gelé / complète / `Δénergie` seule / + curiosité / + nouveauté) puis
`docs/preregistrations/S2-REWARD-ABLATION-bis.json` (design RÉDUIT à trois bras sur le pré-vol ci-dessous,
scellé avant la première cellule du run ; seuils, dose, n, cohorte identiques).

## Pré-vol — deux faits mesurés avant d'engager une cellule

1. **La curiosité est MORTE sous le backend torch.** Trouvé au smoke (`results/s2_reward_ablation_smoke.json`) :
   les bras « + curiosité » étaient BIT-IDENTIQUES à leurs jumeaux sans (mêmes âges, `Σ|ΔW|` 1442,82 =
   1442,82 sur 200 ticks). Cause lue ensuite dans le code : `backend_torch.py` n'écrit jamais `model.surprise`
   (il ne reçoit la surprise que comme argument d'entrée du forward) ; seul le forward legacy numpy la pose
   (`mamba_agent.py:824`). Sous `use_torch_inworld` — le chemin PUBLIÉ depuis S2-009 — le terme
   `curiosity_scale · surprise` vaut 0 à chaque tick, et **la récompense effective du crédit publié est
   `Δénergie + nouveauté`**. Mesuré par `preflight_reward_seam` + `preflight_curiosity_dead` (publiés dans le
   JSON) : 50 ticks immortels, 4 agents, surprise maximale vue par le learner **0,0**, 200 récompenses
   identiques à `curiosity_scale` 0 vs 2,0. Conséquence : deux bras sur cinq du design scellé ne pouvaient
   rien changer (E2) — retirés AVANT ~10 h de calcul, sceau `-bis`. Les grandeurs `S_curiosity`,
   `S_novelty`, `d_curiosity`, `d_novelty`, `dose_curiosity`, `dose_novelty` du sceau original n'ont donc PAS
   été mesurées ; le bras « + nouveauté » EST le bras complet. Le runner refuse tout run à trois bras si la
   surprise se réveille (contre-exemple gelé en test). Classes E16 occ. 2 et E8 occ. 5 au registre ; P2.65 au
   backlog (brancher la surprise dans le forward torch est une EXPÉRIENCE, pas une correction).
2. **Le seam coupe LE chemin, tout le chemin, et rien d'autre** (question 2 du pré-vol). Quatre mondes au
   même seed, identiques jusqu'à la ligne de récompense : à échelles nulles, la récompense passée au learner
   est EXACTEMENT Δénergie (résidu max 1,2e-7) ; le terme de nouveauté vaut `3/√count` avec le compte
   rejoué dans l'ordre des agents ; la somme est additive. Part intrinsèque de |récompense| au tick 1 :
   0,77 (elle décroît ensuite avec les comptes).

## Méthode

* `tools/evo_runs/s2_reward_ablation.py`, dispositif de P4.4 réutilisé tel quel (`_world` et
  `phase1_learn_immortal` de `s2_credit_retention.py` paramétrés par les échelles, `None` = chemin
  bit-identique). Par seed (2026-2037, n = 12, LES MÊMES seeds que P4.4, unité = le seed), trois bras
  APPARIÉS sur le bassin DAgger cloné ×12 : **(a)** `a_frozen`, W gelé ; **(b_full)** crédit publié,
  récompense complète (échelles du monde LUES sur une instance et publiées : curiosité 2,0 — morte —,
  nouveauté 3,0) ; **(b_energy)** crédit publié, `Δénergie` seule (`curiosity_scale = 0`,
  `novelty_scale = 0`). Phase 1 IMMORTELLE 2000 ticks (dose comptée, `resurrections` publiées), phase 2
  MORTELLE 200 ticks à poids GELÉS (`Σ|ΔW| = 0` asserté). Régime publié (bloc `regime`) : `cog_gain 12,0`,
  `base_metabolism 0,75`, `forage_payoff 0`, `benchmark_mode`, nuit OFF, `energy_start 80`.
* **Réplication** : `b_full` mesuré sur le seed 2026 est BIT-IDENTIQUE à la ligne P4.4 du même seed (âges
  `[5, 6, 6, 7, 7, 7, 7, 8, 8, 9, 9, 11]`, dose 1999, 12 résurrections, `Σ|ΔW|` 18242,04 = 18242,04 ;
  P4.4 à `05cf888`). Les 11 autres seeds de `b_full` sont donc IMPORTÉS de `results/s2_credit_retention.json`
  et marqués `imported_from` — re-mesurer un calcul déterministe coûte ~100 min et n'apporte rien ; la règle
  `-bis` le prévoyait. `a_frozen` est re-mesuré sur les 12 seeds (déterministe : médiane 36,0, la même).
* `declare_design` (unité = seed, n = 12, famille de contrôles 12), `assert_no_io_overlap` sur le bassin,
  `assert_ablation_changes_something` sur la récompense du tick 1. Provenance : run lancé à `1fffb0a`
  (arbre sale, session parallèle), code du runner committé identique en `7580e49`.

## Résultat (`results/s2_reward_ablation.json`)

| bras | survie médiane (phase 2) | min–max | dose (TD / agent) | `resurrections` (phase 1, médiane) |
|---|---|---|---|---|
| (a) `S_a` bassin gelé | **36,0** | 17,0–50,0 | 0 | 0 |
| (b_full) `S_full` complète | **8,0** | 7,0–9,5 | 1999 | 10 (2–30) |
| (b_energy) `S_energy` Δénergie seule | **8,0** | 7,0–10,5 | 1999 | 13 (3–21) |

`d_full` = `S_full` − `S_a` : médiane **−28,25**, 12/12 négatifs (réplique P4.4 à l'identique).
`d_energy` = `S_energy` − `S_a` : médiane **−28,5**, **12/12 négatifs, 0/12 positifs**.
`S_energy` − `S_full` apparié : +3,5 · +1,5 · 0 · +1,5 · −2,0 · 0 · −0,5 · 0 · −2,0 · −0,5 · 0 · −0,5 —
**médiane 0,0, 3/12 positifs**. `dose_full` = `dose_energy` = 1999 (médianes). Censures : 0 partout.

## Verdict (branches scellées, lues dans l'ordre)

1. n = 12 : pas INCOMPLET. 2. `S_a` 36,0 ≥ 20 : le bassin transfère. 3. doses 1999 ≥ 1000 : le crédit
s'est appliqué dans les deux bras. 4. `d_full` ERODE (12/12, −28,25) : la prémisse de P4.4 se REPRODUIT.
5–6b. `d_energy` ERODE (12/12, −28,5 ≤ −5) → **CREDIT_ERODE_SEUL** ; `S_energy` − `S_full` médiane 0,0,
3/12 → **PLEIN** (la nouveauté n'atténue ni n'aggrave).

**Δénergie seule suffit à effacer le bassin, et l'efface exactement autant que la récompense complète.**
L'hypothèse de [[EDR-S2-CREDIT-RETENTION]] est réfutée deux fois : le terme de curiosité n'a jamais existé
sur ce chemin, et le terme de nouveauté ne contribue rien à l'érosion (12 différences appariées dans
±3,5 ticks, médiane 0). Le mur n'est pas une récompense mal alignée : **c'est le mécanisme de crédit
lui-même — Actor-Critic TD(0) par tick + REINFORCE épisodique (k = 8, lr 0,04) — appliqué au signal
`Δénergie`, qui détruit une politique de survie qu'il n'a pas construite.**

## Portée (hedges)

* Ce run ne dit pas POURQUOI le crédit sur Δénergie érode. Deux mécanismes candidats, discriminables par le
  prochain run (P4.9, « ablation du CRÉDIT ») : **(i) dérive à avantage constant** — sous immortalité,
  Δénergie par tick est dominé par le drain métabolique (négatif, quasi constant), le critic tanh sature
  (56 % des `value_pred` < −0,99 loggés en P1.6) et l'erreur TD ≈ r < 0 à chaque tick : toute action prise
  reçoit un avantage négatif, la politique s'éloigne de ce qu'elle fait — c'est un DÉSAPPRENTISSAGE par le
  signe, pas par le contenu ; prédiction : un bras à récompense NULLE (`reward_scale = 0`) n'érode PAS ;
  **(ii) pas trop grand** (E19, EDR-LOCK-002 (session parallèle, non encore committé)) — à lr 0,04 toute mise à jour déplace trop la politique
  DAgger ; prédiction : le bras nul érode AUSSI (le bruit d'estimation seul suffit), et lr 0,004 érode moins
  à dose égale. Un troisième bras, TD coupé (épisodique seul), dit si le destructeur est le TD par tick —
  [[EDR-CALIB-LEARNER]] a montré que ce TD CONTRIBUE à l'apprentissage de la tâche linéaire.
* Réserve E6 héritée de P4.4 : la phase d'apprentissage est immortelle (états « bien nourris »), la
  phase de test mortelle ; l'érosion est mesurée sous ce régime d'entraînement.
* Une seule lignée de bassin, un monde, un régime, 200 ticks de test. La létalité de l'apprenant (P1.6,
  résidu i) n'est pas expliquée ici : `resurrections` 13 (Δénergie seule) vs 10 (complète), même ordre.
* Le bras `b_full` est importé pour 11 seeds sur 12 : la réplication bit-identique du seed 2026 (âges,
  dose, résurrections, `Σ|ΔW|` à 1e-9) est la preuve que le même code au même seed rend la même ligne ;
  toute divergence aurait fait mesurer les 12 (`SRA_FULL_ALL=1` force la mesure).

## Coût (le coût suit le comportement, dans les deux sens)

Unité mesurée sur le seed 2026 : gelé 0,9 s ; complète 283 s ; **Δénergie seule 50 s** — 5,6× moins que la
récompense complète à dose IDENTIQUE (1999 TD), donc les agents privés de nouveauté font autre chose
(moins d'objets manipulés ?) — non exploré, publié. Sur les 12 seeds, le bras Δénergie seule va de 50 à
373 s. Projeté 31 min (marge ×3, `b_full` importé), réel **40 min** contre les 7-10 h du design à cinq
bras : le pré-vol a payé ~10 h. Budget scellé 12 h (dérivé des unités P4.4 par type de bras).

## Ce que ça change

* **Le levier n'est pas la récompense.** « Aligner la récompense » (retirer la nouveauté, brancher la
  curiosité) ne peut pas lever l'érosion : elle est déjà pleine à Δénergie seule. Le prochain pas est
  l'ablation du CRÉDIT (P4.9 : récompense nulle / pas 0,004 / TD coupé, même dispositif, ~25 min par bras
  au coût mesuré ici), qui nomme le destructeur avant toute tentative de « warm-start + crédit ».
* **Toute prose qui invoque la « curiosité » in-world depuis EDR 014 décrit le chemin LEGACY.** Sous torch,
  la récompense publiée est `Δénergie + nouveauté` depuis S2-009. `preflight_curiosity_dead` est la garde ;
  P2.65 décide de brancher ou de déclarer.
* Le pari C ([[EDR-S2-CREDIT-RETENTION]]) reste tranché dans son sens défavorable, et se précise : le
  warm-start est effacé par le crédit quelle que soit la récompense qu'on lui donne.

Converge [[EDR-CALIB-LEARNER]] (le même apprenant apprend une tâche linéaire à cette dose — il n'est pas
inerte, il apprend quelque chose qui tue), EDR-LOCK-002 (session parallèle, non encore committé) (un « mur » qui était un artefact de pas :
E19 est le premier suspect de P4.9), [[EDR-175]] (érosion r·P : ici l'érosion ne dépend même plus de r),
REF-EXPERIMENT-PREFLIGHT (question 1 : deux bras qui ne pouvaient rien changer, attrapés au smoke).
