---
id: EDR-S2-CREDIT-RETENTION
type: EDR
title: "Le crédit in-world publié, à dose NON bornée par la mort, EFFACE le bassin DAgger de WARM-003 (survie 36,0 → 8,0, 12/12 seeds, écart médian −28) et ne construit RIEN à froid (7,5 < plancher 9,0) — il apprend, et ce qu'il apprend tue"
status: active
verdict: ERODE_AND_PAS_APPRIS_FROID_THE_CREDIT_LEARNS_SOMETHING_THAT_IS_NOT_SURVIVAL
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-CALIB-LEARNER, EDR-WARM-003, EDR-175, EDR-S2-010, EDR-S2-011]
corrected_by: [EDR-S2-REWARD-ABLATION]
---

> ⚠️ **Corrigé le 2026-09-15 par [[EDR-S2-REWARD-ABLATION]]** (le verdict ERODE + PAS_APPRIS_FROID TIENT et
> se réplique bit-identiquement ; ce qui tombe est l'hypothèse mécaniste et la description de la récompense) :
> (1) le terme de **curiosité est MORT sous le backend torch** — `backend_torch.py` n'écrit jamais
> `model.surprise`, seul le forward legacy le pose — donc la récompense que ce run a réellement optimisée est
> `Δénergie + nouveauté`, pas « Δénergie + curiosité + nouveauté » ; (2) **Δénergie SEULE érode autant**
> (−28,5 vs −28,25, 12/12, différence appariée médiane 0,0) : l'érosion ne vient d'aucun terme intrinsèque,
> elle vient du mécanisme de crédit lui-même.

## Question (backlog, bloc « 🧭 2026-09-14 », rang 4 — P4.4 ; règle scellée AVANT toute cellule)

Règles : `docs/preregistrations/S2-CREDIT-RETENTION.json` (contenu), `-bis` (markup `dv_primaire`),
`-ter` (budget de coût relevé sur mesure, voir § Coût). [[EDR-CALIB-LEARNER]] a établi que l'apprenant
in-world tel que publié (Actor-Critic TD(0) par tick + REINFORCE épisodique k = 8, lr 0,04) APPREND la
tâche linéaire quand la mort ne borne plus sa dose, et qu'un apprenant meurt ~100× plus qu'un
non-apprenant. Restait le seul maillon jamais mesuré de la chaîne warm-start in-world (tous les verdicts
WARM gèlent `lr = 0`) : **ce crédit RETIENT-il ou ÉTEND-il le bassin DAgger persisté de
[[EDR-WARM-003]] (survie publiée 35,2/200), et construit-il de la survie à FROID ?** Les branches, dans
l'ordre imposé : INCOMPLET → INDETERMINE_HARNAIS (`S_a` < 20) → INDETERMINE_DOSE (< 1000 TD/agent) →
RETENU_ETENDU / ERODE (signe 10/12 ET ±5 ticks sur `d_ba`) / RETENU_NEUTRE → APPRIS_FROID (`S_c` > 2 ×
plancher 9,0 sur 10/12 seeds et en médiane) / PAS_APPRIS_FROID.

## Méthode

* `tools/evo_runs/s2_credit_retention.py`. Par seed (2026-2037, n = 12, unité = le seed), trois bras
  APPARIÉS (même monde, même seed) : **(a)** bassin cloné ×12, W GELÉ ; **(b)** bassin cloné ×12 + crédit
  publié ; **(c)** cohorte fraîche ×12 + crédit publié. Monde `cognitive_demand` 2-bits au régime S2-009
  (bloc `regime` du JSON : `cog_gain 12,0`, `base_metabolism 0,75`, `forage_payoff 0`, `benchmark_mode`,
  nuit OFF, `energy_start 80`).
* **Phase 1, IMMORTELLE** (énergie remise à 80 sous 30, hp au plafond sous 50, morts intra-tick
  ressuscitées ; 2000 ticks) : (b) et (c) apprennent ; dose comptée par `count_learning_events`
  (`dose_b`, `dose_c` = mises à jour TD par agent) et `resurrections` publiées. Vérifié : la recharge
  entre deux ticks n'entre PAS dans la récompense (`old_energies` capturé à l'intérieur du tick,
  `world_1_stoneage.py:1221`, `new_energies` à sa fin, `:1702`).
* **Phase 2, MORTELLE** (200 ticks, mêmes objets-agents, poids GELÉS `lr = 0` + TD coupé, forward torch
  identique à la phase 1 ; `Σ|ΔW| = 0` asserté) : `S_a`, `S_b`, `S_c` = survie médiane des 12 agents
  (âge à la mort, censuré à 200) ; `d_ba` = `S_b` − `S_a` apparié par seed.
* `declare_design` (unité = seed, n = 12, famille de contrôles 12), `assert_no_io_overlap` sur le bassin
  (59 + 108 ≤ 172), provenance git `05cf8888` (arbre sale : session parallèle).

## Résultat (`results/s2_credit_retention.json`)

| bras | survie médiane (phase 2) | dose (TD / agent) | résurrections (phase 1, médiane) |
|---|---|---|---|
| (a) bassin gelé | **36,0** (min 17,0 · max 50,0) | 0 | 0 |
| (b) bassin + crédit | **8,0** (7,0-9,5) | 1999 | 10 (2-30) |
| (c) froid + crédit | **7,5** (7,0-8,5) | 1999 | 62 (5-946) |

`d_ba` par seed : −24,5 · −28,0 · −36,5 · −32,0 · −33,0 · −27,5 · −28,0 · −28,5 · −41,0 · −33,5 · −9,0 ·
−17,0 — **médiane −28,25, 12/12 négatifs, 0/12 positifs**. `S_c` au-dessus de 2 × plancher : **0/12**.
Censures en phase 2 : 0 dans les trois bras (personne n'atteint 200 ticks).

## Verdict (branches scellées, lues dans l'ordre)

1. n = 12 : pas INCOMPLET. 2. `S_a` médiane 36,0 ≥ 20 : le bassin TRANSFÈRE dans ce harnais (WARM-003
publiait 35,2 — même chiffre, deux harnais). 3. `dose_b` = `dose_c` = 1999 ≥ 1000 : le crédit s'est
appliqué. 4. **ERODE** : `d_ba` < 0 sur 12/12 seeds ET médiane −28,25 ≤ −5. 5. **PAS_APPRIS_FROID** :
`S_c` médiane 7,5 < 18, 0/12 seeds au-dessus.

**Le crédit publié, laissé apprendre sans être borné par la mort, EFFACE une compétence de survie
qu'il n'avait pas construite, et n'en construit aucune à froid.** Ce n'est pas un nul de dose (1999
mises à jour, contre ~48 dans S2-010/S2-011) ni un artefact de harnais (bassin à 36, poids gelés en
test). Lu avec [[EDR-CALIB-LEARNER]] — le même apprenant APPREND la tâche linéaire (12/12) et meurt
~100× plus en apprenant — le tableau est cohérent : **le crédit apprend quelque chose, et ce quelque
chose n'est pas la survie.** La récompense qu'il optimise est `Δénergie + curiosité + nouveauté`
(`world_1_stoneage.py:1713`) ; un agent immortel dont le drain est constant reçoit surtout les deux
termes de droite. Hypothèse mécaniste NON testée ici, et c'est le prochain run : **le crédit poursuit
la curiosité et la nouveauté, pas l'énergie** (ablation des deux termes, même dispositif).
⚠️ **RÉFUTÉE le 2026-09-15 par [[EDR-S2-REWARD-ABLATION]]** : Δénergie seule érode autant ; et la curiosité
n'a jamais été dans cette récompense (surprise jamais écrite sous torch).

## Portée (hedges)

* **Distribution d'états (E6)** : la phase 1 entraîne des agents « bien nourris » (énergie 30-100,
  jamais morts) ; la phase 2 les évalue dans la distribution naturelle. Un ÉRODÉ sous ce régime
  d'entraînement n'établit pas que le crédit érode aussi sous le régime mortel — mais sous le régime
  mortel la dose est bornée à ~48 et la survie est au plancher aussi ([[EDR-S2-010]]) : les deux régimes
  donnent le plancher, par des chemins différents.
* Une seule lignée de bassin (`n_lineage = 1`, WARM-003), un monde, un régime, 200 ticks de test.
* Le bras (c) montre une létalité d'apprentissage très variable selon le seed (5 à 946 résurrections) :
  non expliquée, publiée.
* La recharge d'immortalité ne fabrique pas de récompense (vérifié) ; elle fabrique un ÉTAT.

## Coût (E12 sur le coût, attrapée AVANT engagement — et une garde qui gardait mal)

La première projection a été **REFUSÉE** par `project_cost` : l'unité mesurée (un seed complet, trois
bras) valait **675 s**, contre ~136 s extrapolés d'un smoke à 200-400 ticks — le coût par tick CROÎT
avec le remplissage du monde (agents qui agissent, objets). Budget relevé de 7200 à 25200 s dans le
`-ter`, sur cette mesure, sans toucher n, dose ni cohorte. Réel : **190 min** (projeté 407 avec marge
×3 ; un seed à 65 min sous charge machine). Défaut d'outil trouvé : le runner écrivait le JSON APRÈS
la garde, donc une projection refusée perdait ses 11 minutes de mesure — corrigé (sauver AVANT).

## Ce que ça change

* **Pari C** (SPECIFICATION_10ANS) est tranché dans son sens défavorable : le warm-start franchit le
  bootstrap (loi transversale), mais le crédit in-world publié DÉTRUIT ce qu'il reçoit. « Warm-start +
  ce crédit » n'est pas un régime : c'est une érosion à dose contrôlée.
* La porte IW-1 (P4.6, « le crédit étend un demi-lecteur ») ne s'ouvre pas : elle exigeait un bassin
  non érodé.
* Le prochain run n'est pas un autre warm-start : c'est **l'ablation de la récompense** (P4.8) — même
  dispositif, bras (b) avec `Δénergie` seule, `Δénergie + curiosité`, `Δénergie + nouveauté`. Si
  l'érosion disparaît sans les termes intrinsèques, le mur est une récompense mal alignée, pas un
  crédit incapable ; si elle reste, c'est le mécanisme TD(0) sur critic saturé qu'il faut viser.

Converge [[EDR-175]] (érosion quand r·P < coût : ici r·P n'est même plus la question, le crédit
efface à récompense pleine), [[EDR-EVO-011]] (l'acte débloqué coûte), [[EDR-WARM-010]] (le paysage
récompense la compétence partielle — et le crédit la défait), REF-EXPERIMENT-PREFLIGHT.
