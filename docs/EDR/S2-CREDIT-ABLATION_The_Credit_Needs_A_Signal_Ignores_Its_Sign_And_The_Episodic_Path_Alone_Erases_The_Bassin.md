---
id: EDR-S2-CREDIT-ABLATION
type: EDR
title: "Sans signal, le crédit publié ne bouge ni n'érode le bassin DAgger (33,25 ≈ 36,0, mouvement 2 %) ; avec un signal de signe INVERSÉ il l'efface autant que le signal vrai (7,25 vs 8,0, 12/12) ; la voie ÉPISODIQUE seule suffit (7,5, 12/12, à 8 % du mouvement) — l'érosion exige un signal, ignore son signe, n'est pas proportionnelle au mouvement, et un pas 10× plus petit retient plus que le pas publié sur 12/12 seeds sans retenir le bassin (21,5) ; les deux mécanismes candidats de P4.8 sont RÉFUTÉS"
status: active
verdict: SIGNAL_QUELCONQUE_EPISODIQUE_SUFFIT_ATTENUE_A_PETIT_PAS_BOTH_P48_CANDIDATE_MECHANISMS_REFUTED
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-S2-REWARD-ABLATION, EDR-S2-CREDIT-RETENTION, EDR-CALIB-LEARNER, EDR-LOCK-002]
---

## Question (backlog P4.9, rang 4 ter ; règle scellée AVANT toute cellule)

[[EDR-S2-REWARD-ABLATION]] a établi que le crédit in-world publié (Actor-Critic TD(0) par tick + REINFORCE
épisodique k = 8, lr 0,04) EFFACE le bassin DAgger de [[EDR-WARM-003]] à `Δénergie` seule autant qu'à récompense
complète (36,0 → 8,0, 12/12 seeds) : le mur est le mécanisme de crédit, pas la récompense. Son § Portée nommait
deux mécanismes candidats avec leurs prédictions opposées : **(i) dérive à avantage constant négatif** sous critic
tanh saturé (prédit : sans signal, pas d'érosion ; signal inversé, pas d'érosion ou extension) ; **(ii) pas trop
grand** (E19, [[EDR-LOCK-002]] ; prédit : sans signal, érosion AUSSI, par le bruit d'estimation). Ce run les
départage. Règle : `docs/preregistrations/S2-CREDIT-ABLATION.json` (10 branches ordonnées, budget 57 600 s dérivé
des coûts mesurés de P4.8, charge machine déclarée).

## Pré-vol — ce qui ATTEINT le learner d'origine sous chaque variante (réponse connue, publié dans le JSON)

Les originaux `learn` / `learn_episode` sont interceptés SOUS `count_learning_events` (`_learning_trace`), 4
agents, 32 ticks immortels : `reward_scale = 0` → toutes les récompenses TD et épisodiques reçues sont nulles ET
des mises à jour ont lieu (31 TD) ; `reward_scale = −1` → la trace du premier tick est la négation bit-exacte de
la trace publiée (`[2,72, 2,85, 2,51, 2,27]`, non nulle) ; `td_enabled = False` → `learn` jamais appelé, 4
épisodes vivants, Σ|ΔW| > 0 ; `lr = 0,004` → pas LU sur l'optimiseur SGD = 0,004 < 0,04 publié, Σ|ΔW| moindre
(36 vs 186). Un contre-exemple (seam qui fuit) fait LEVER le pré-vol (`preflight_credit_seams`, testé).
Observation du pré-vol, reprise dans la règle avant le run (branche 7) : sans signal, le critic converge et les
poids bougent à 2 % du bras complet — un NEUTRE de ce bras se lit AVEC son ratio de mouvement.

## Méthode

* `tools/evo_runs/s2_credit_ablation.py`, dispositif de P4.4/P4.8 réutilisé (`phase1_learn_immortal` paramétré
  par `reward_scale` / `td_enabled` / `lr`, défauts = chemin publié bit-identique ; `immortal_refill` extrait sans
  changer une ligne). Par seed (2026-2037, n = 12, LES MÊMES seeds que P4.4/P4.8, unité = le seed), six bras
  APPARIÉS sur le bassin DAgger cloné ×12 : **(a)** `a_frozen`, W gelé, re-mesuré ; **(b_full)** crédit publié,
  récompense complète ; **(b_zero)** `reward_scale = 0` ; **(b_neg)** `reward_scale = −1` ; **(b_lr)**
  `lr = 0,004` ; **(b_tdoff)** `td_enabled = False` (REINFORCE épisodique seul). Phase 1 IMMORTELLE 2000 ticks
  (dose comptée, `resurrections` publiées), phase 2 MORTELLE 200 ticks à poids GELÉS (`Σ|ΔW| = 0` asserté).
  Régime publié (bloc `regime`, `lr_published` 0,04 lu sur l'optimiseur) : `cog_gain 12,0`, `base_metabolism 0,75`,
  `forage_payoff 0`, `benchmark_mode`, nuit OFF, `energy_start 80`.
* **Réplication** : `b_full` mesuré sur le seed 2026 est BIT-IDENTIQUE à la ligne P4.4 (âges, dose 1999,
  12 résurrections, `Σ|ΔW|` 18242,04) ; les 11 autres seeds de `b_full` sont IMPORTÉS de
  `results/s2_credit_retention.json` (`imported_from`), comme le prévoyait la règle.
* `declare_design` (unité = seed, n = 12, famille 12), `assert_no_io_overlap` sur le bassin. Provenance : run
  lancé le 2026-09-15 depuis l'arbre à `9de2b3b` (sale), AVANT le commit du runner (`4309041`, fichier identique)
  et avant le versionnement de l'activation legacy (E29, `3e2a9f8`) : ce run est sur le chemin TORCH
  (`use_torch_inworld`), dont le forward n'exécute pas l'activation legacy de `generated_ops` (importée par
  `mamba_agent.py` pour le forward numpy) ; la réplication bit-identique de `b_full` contre
  P4.4 (run à `05cf888`) et P4.8 (run à `1fffb0a`) atteste la stabilité du chemin sur ces trois commits.

## Résultat (`results/s2_credit_ablation.json`)

| bras | survie médiane (phase 2) | écart au bassin (médiane ; signe −/+ sur 12) | classe | dose | `Σ|ΔW|` / bras complet (médiane) | `resurrections` (phase 1, médiane, min–max) |
|---|---|---|---|---|---|---|
| (a) `S_a` bassin gelé | **36,0** (17,0–50,0) | — | — | 0 | 0 | 0 |
| (b_full) `S_full` | **8,0** | `d_full` **−28,25** ; 12/0 | ERODE | `dose_full` 1999 | `dW_full` 1,00 | 10 (2–30) |
| (b_zero) `S_zero` sans signal | **33,25** | `d_zero` **−0,75** ; 8/2 | NEUTRE | `dose_zero` 1999 | `dW_zero` **0,025** | **179** (5–380) |
| (b_neg) `S_neg` signal inversé | **7,25** | `d_neg` **−28,75** ; 12/0 | ERODE | `dose_neg` 1999 | `dW_neg` 0,12 | 32 (1–183) |
| (b_lr) `S_lr` pas 0,004 | **21,5** (11,0–43,0) | `d_lr` **−14,0** ; 9/3 | NEUTRE | `dose_lr` 1999 | `dW_lr` 0,12 | 17,5 (7–25) |
| (b_tdoff) `S_tdoff` épisodique seul | **7,5** | `d_tdoff` **−29,0** ; 12/0 | ERODE | `dose_tdoff` 250 épisodes | `dW_tdoff` 0,08 | 3,5 (2–26) |

`d_zero` par seed : +0,5 · −5,0 · −7,0 · −7,5 · −0,5 · −8,5 · −0,5 · 0 · +2,0 · −7,5 · 0 · −1,0.
`d_lr` par seed : −20,5 · −20,0 · −31,0 · −22,0 · −9,5 · −22,5 · +1,0 · −12,0 · −7,0 · −16,0 · +2,0 · +3,5
(hétérogène : quatre seeds quasi intacts — 2030, 2032, 2034, 2037 — huit érodés à 11-19).
`S_lr` − `S_full` apparié : **+4,0 à +34,0, 12/12 positifs** (médiane +13,75). Censures : 0 partout.

## Verdict (branches scellées, lues dans l'ordre)

1. n = 12. 2. `S_a` 36,0 ≥ 20. 3. doses TD 1999 ≥ 1000 sur quatre bras, `dose_tdoff` 250 ≥ 100. 4. `d_full`
ERODE (12/12, −28,25) : la prémisse se REPRODUIT. 5. `d_zero` NEUTRE (8/12 < 10, −0,75) ; `d_neg` ERODE ;
`d_lr` NEUTRE (9/12 < 10) ; `d_tdoff` ERODE. **6b. `d_zero` non ERODE ET `d_neg` ERODE → SIGNAL_QUELCONQUE.**
7. `d_tdoff` ERODE → **EPISODIQUE_SUFFIT** ; `d_lr` non ERODE → **ATTENUE_A_PETIT_PAS**, lu AVEC `dW_lr` 0,12
(pas assez bougé à dose égale, jamais « inoffensif ») ; `neg_etend` faux.

**Les deux mécanismes candidats de [[EDR-S2-REWARD-ABLATION]] sont réfutés.** (ii) « pas trop grand / bruit
d'estimation » prédisait `b_zero` ERODE : sans signal, le crédit ne bouge presque pas (2,5 % du mouvement) et
n'érode pas (33,25 ≈ 36,0). (i) « avantage constant négatif » prédisait `b_neg` NEUTRE ou ETENDU : le signal
INVERSÉ efface le bassin exactement autant que le signal vrai (7,25 vs 8,0, 12/12), avec 8× moins de mouvement.
**L'érosion exige un signal non nul, ignore son signe, et n'est pas proportionnelle au mouvement des poids**
(0,08× érode autant que 1× ; 0,12× érode tout par le signe inversé et la moitié par le petit pas). **La voie
ÉPISODIQUE seule suffit** : REINFORCE k = 8 (`learn_episode`, `gate_last_only = True`), sans un seul appel du TD
par tick, efface le bassin en 250 mises à jour — le TD par tick, qui CONTRIBUE à apprendre la tâche linéaire
([[EDR-CALIB-LEARNER]]), n'est pas nécessaire à la destruction. Le pas 10× plus petit, à dose de ticks égale,
retient PLUS que le pas publié sur 12/12 seeds sans retenir le bassin (21,5, hétérogène).

## Portée (hedges)

> **Précisé le 2026-09-24 par [[EDR-S2-CREDIT-ABLATION-2]] (P4.16)** : le TD par tick SEUL (épisodique coupé)
> amène le bassin au plancher lui aussi (8,5 contre un plancher froid mesuré à 7,5, saturation 96 %) — « le TD
> n'est pas nécessaire » tient, mais il SUFFIT, et le run ne peut PAS classer les deux voies entre elles (DV
> saturée) ; un retour constant POSITIF érode à mi-chemin (23,25, 11/12, à 5,4 % du mouvement) — ce bras mesure un
> OFFSET POSITIF de l'avantage, pas une absence de contenu ; l'épisodique seul à 0,004 érode (17,0, 11/12) mais
> **moins que le même bras à pas publié** (−19,0 contre −29,0, 12/12 appariés) : l'`ATTENUE_A_PETIT_PAS` de ce
> record TIENT et se reconduit à voie unique. Prochain contrôle : le bruit apparié en mouvement (P4.18).

* **Le bras sans signal ne sépare pas « le pas est inoffensif » de « le pas n'a pas eu lieu »** : avec
  `reward_scale = 0` l'erreur TD tend vers 0 (V → 0) et l'avantage épisodique aussi, donc les poids ne bougent
  qu'à 2,5 %. Ce que le bras ÉTABLIT : la machinerie sans signal ne fabrique pas d'érosion par elle-même (pas de
  bruit intrinsèque qui pousse la politique). Ce qu'il n'établit pas : ce que ferait un pas de même amplitude
  que le bras complet sans contenu — c'est le bras « retour CONSTANT » du prochain run.
* **`b_lr` NEUTRE est une atténuation à dose de TICKS égale, pas une innocuité** (branche 7, déclarée avant le
  run) : à 12 % du mouvement, 9/12 seeds érodent (jusqu'à −31) et l'hétérogénéité par seed n'est corrélée ni aux
  `resurrections` (ρ 0,12) ni à `S_a` (ρ −0,29) ; faiblement au mouvement (ρ −0,50 avec `dW_lr`/`dW_full`).
  À dose de MOUVEMENT égale (10× plus de ticks), non mesuré.
* **`resurrections`** : le bassin intact (b_zero) meurt ~180 fois par 2000 ticks dans l'arène immortelle de
  12 clones (contre 10 pour le bras complet, 32 inversé, 17,5 petit pas, 3,5 épisodique seul) : l'érosion
  s'accompagne d'une chute des morts intra-tick de 5 à 50×. Non expliqué ici ; la létalité de l'apprenant
  (P1.6, résidu i) reste ouverte, et ce chiffre dit que c'est le bassin, pas l'apprenant, qui meurt dans l'arène.
* Réserve E6 héritée (phase d'apprentissage immortelle, test mortel) ; une lignée de bassin, un monde, un régime,
  200 ticks de test ; `b_full` importé pour 11/12 seeds sur réplication bit-identique.
* Pourquoi le signal inversé bouge 8× moins que le signal vrai (`dW_neg` 0,12) n'est pas expliqué : publié.

## Coût (temps mur, charge déclarée — et une cellule hors de toute échelle)

Unité mesurée sur le seed 2026 : gelé 1 s ; complète **713 s** (283 s en P4.8 : six worktrees d'agents
chargeaient la machine, charge déclarée dans la règle) ; sans signal 108 s ; inversé 26 s ; petit pas 358 s ;
épisodique seul 62 s. Projeté (`b_full` importé, marge ×3) 20 007 s = 5,6 h. Réel **40 759 s = 11,3 h**, sous le
budget scellé de 16 h — dont **33 060 s pour UNE cellule** (`b_zero`, seed 2029 ; les 59 autres : 26 à 3885 s,
total 7699 s = 2,1 h, DANS la projection). Cause non établie (machine suspendue pendant la nuit du 15 au 16, ou
contention) : `project_cost` / `CostGuard` mesurent du temps MUR, indistinguable d'une suspension — P2.78 au
backlog. Le coût suit le comportement dans les deux sens : le bras inversé, qui érode tout, coûte 30 s par seed.

## Ce que ça change

* **Le destructeur est la mise à jour ÉPISODIQUE elle-même, nourrie de n'importe quel signal non nul.** Ni
  centrer la récompense (le signe est indifférent), ni réduire le pas (12/12 mieux que le pas publié, mais 9/12
  érodent encore), ni couper le TD par tick ne suffit. Prochain run (P4.16, même dispositif, ~1-3 h) : **TD seul**
  (épisodique coupé, seam à ajouter et calibrer), **retour CONSTANT** (+1 partout : signal non nul, contenu nul —
  si ça érode, c'est la dérive de politique de REINFORCE, indépendante du contenu), **épisodique seul à pas
  0,004** ; puis, selon l'issue, une ANCRE au bassin (perte d'imitation / KL vers la politique DAgger pendant le
  crédit, la forme classique DAgger + RL) comme remède candidat à sceller.
* Pour P4.11 (run n° 3 de la file biomimétique, prérequis « ce record ») : la lecture du crédit publié est celle
  d'un opérateur qui efface une politique de survie dès qu'on lui donne un signal, quel qu'il soit.
* Le pari C ([[EDR-S2-CREDIT-RETENTION]]) reste tranché dans son sens défavorable et se précise une seconde fois :
  ni la récompense (P4.8) ni son signe (P4.9) ne sont le levier ; c'est l'opérateur de crédit épisodique.

Converge [[EDR-LOCK-002]] (le pas est un levier, mais ici il n'atteint que l'atténuation), [[EDR-CALIB-LEARNER]]
(le même apprenant apprend une tâche linéaire à cette dose), [[EDR-175]] (érosion r·P : l'érosion ne dépend plus
même du signe de r), REF-EXPERIMENT-PREFLIGHT (question 2 : les quatre seams vérifiés sur ce qui atteint le
learner d'origine, pas sur la formule).
