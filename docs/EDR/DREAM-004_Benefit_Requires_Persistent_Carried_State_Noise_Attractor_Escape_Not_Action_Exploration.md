---
id: EDR-DREAM-004
type: EDR
title: "Le bénéfice exige un bruit PORTÉ par l'état récurrent, pas de l'exploration d'action : du bruit transitoire sur les logits d'action reproduit le FOURRAGE (83 %) mais PAS la reproduction (13 %, écart direct 7.4×) — échappement d'attracteur, pas ε-greedy déguisé"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-DREAM-003]
---

## Question
[[EDR-DREAM-003]] a montré que l'amplitude du bruit sur l'état caché `H` est le levier (+1500-2200 % de
reproduction, cloche, pic σ≈0.2). Le bruit de rêve perturbe `H`, **porté** au tick suivant
(`mamba_agent.py` : `self.H_prev_batch = H`) — perturbation **persistante**. Deux mécanismes rivaux,
posés AVANT le run :

* **Échappement d'attracteur** : la dynamique récurrente non perturbée se stabilise dans un bassin
  passif ; le bruit sur l'état PORTÉ l'en éjecte et l'y maintient. → **exige la persistance**.
* **Exploration / jitter** : l'agent sous-explore ; n'importe quel bruit d'action suffit. L'organe se
  réduirait à un ε-greedy, et le verrou serait le **régime d'exploration**, pas la récurrence.

## Méthode — contrôle de LOCUS / persistance
Seam `MambaBatchModel.ACTION_NOISE` (défaut 0 = prod inchangée) : bruit sur les 8 logits de
déplacement, chez les **mêmes** porteurs d'organe que le rêve, mais **TRANSITOIRE** (par-tick,
n'écrit pas dans `H` → non porté). Placé juste avant le retour de `forward`, après consommation de
toutes les sous-sorties internes → ne perturbe QUE l'action lue par le monde.

**Calibré 5/5** (`tests/sandbox/test_action_noise_seam.py`) : no-op EXACT à σ=0, perturbe l'action à
σ>0, **spécificité de population** (un non-porteur reste intact même à σ=5 → même population que le
rêve), monotonie. Smoke : le bruit d'action MORD in-world (`preys` +50-200 % à σ=8) → bras vivant, pas
un no-op (classe E1 écartée). Balayage géométrique 2→8→32 pour **encadrer l'optimum de l'action** et
donner à l'hypothèse exploration sa meilleure chance. n=12, `stoneage`, 25 agents, 80 ticks, organe
100 %. Endpoint PRIMAIRE = `n_lived`. Artefact : `results/dream_locus_n12.json`.

## Résultats

| contraste | `n_lived` | `preys` | `med_founder_age` |
|---|---|---|---|
| off → **H_0.2** (porté) | **22.30×** (12/12) | 4.22× (12/12) | 1.55× (9/12, p=0.019) |
| off → act_2 | 2.33× | 2.69× | 0.89× (n.s.) |
| off → act_8 | 2.68× | 3.26× | 1.04× (n.s.) |
| off → act_32 | 3.00× | 3.52× | 0.85× (n.s.) |
| **act_32 → H_0.2** (direct) | **7.43×** (12/12, p=0.0025) | **1.20×** (10/12, p=0.007) | — |
| **act_8 → H_0.2** (direct) | — | — | 1.49× (10/12, p=0.015) |

**Contrôle positif intégré, reproduit à la décimale** : off → H_0.2 = 22.30× / médiane 1260 = *exactement*
le bras s0.2 de [[EDR-DREAM-003]]. Le seam ACTION_NOISE à 0 ne perturbe pas la trajectoire portée →
instrument validé avant lecture du reste.

## Verdict
**`BENEFIT_REQUIRES_PERSISTENT_CARRIED_STATE_NOISE__ATTRACTOR_ESCAPE_NOT_ACTION_EXPLORATION`**

Le bruit d'action transitoire, à sa MEILLEURE magnitude (σ=32, qui sature quasiment le fourrage),
reproduit **13,5 %** du bénéfice de reproduction (3.00× vs 22.30×) et **0 %** du bénéfice de survie
(inerte, 0.85-1.04×). Le contraste direct meilleur-action → H est **7.43× sur `n_lived`** (12/12) et
**1.49× sur l'âge** (10/12). **« ε-greedy déguisé » est réfuté** : le bruit perturbe pourtant le
comportement (contrôle vivant). Le bénéfice exige que le bruit soit sur l'état récurrent **porté** —
c'est de l'échappement d'attracteur, pas de l'exploration d'action.

## La dissociation qui tranche le mécanisme
Sur le **fourrage**, le bruit d'action atteint 83 % de H (écart direct 1.20×). Sur la **reproduction**,
le même bruit atteint 13 % (écart direct 7.43×). **Si la reproduction était un sous-produit du fourrage,
égaler l'un égalerait l'autre.** Ce n'est pas le cas : le bruit d'action achète le fourrage mais pas la
reproduction ; le bruit porté achète les deux. Le +2000 % de reproduction n'est donc pas un effet
d'activité — il est **gaté par quelque chose dans l'état persistant** que l'activité seule ne débloque
pas. (Piste ouverte : quoi ? un registre interne de satiété/maturité reproductive qui reste coincé sans
perturbation de l'état ?)

## Ce que je m'interdis (borne, pas extrapolation)
Le balayage d'action s'arrête à σ=32. La revendication « aucune magnitude n'atteint H » est **bornée**,
pas extrapolée — mais fondée : (a) la tendance est quasi-plate (2.33→2.68→3.00 pour σ ×16) ; (b) le
fourrage SATURE déjà à σ=32 (3.52×) ; (c) au-delà, l'action devient uniformément aléatoire (marche
aléatoire → le fourrage REDESCEND, cf. seeds 4/8 où act_32 s'effondre). Il n'existe pas de magnitude
d'action plausible qui atteigne 22×.

## Conséquences
* **Converge avec la thèse du dépôt** : le verrou n'est pas l'architecture (l'organe MCTS) mais le
  **régime dynamique de l'état récurrent**. Recoupe [[planner-depth1-refuted]] / PLAN-001 (c'est la
  FORME du modèle qui décide, pas la recherche) — ici, ce n'est pas la recherche NI l'exploration
  d'action, c'est la perturbation de l'état porté.
* **Ferme la chaîne DREAM-001→004** : (001) le rêve forcé AIDE +77 % ; (002) c'est le BRUIT, pas la
  sélection ; (003) l'amplitude est le levier, cloche pic σ≈0.2 ; (004) le bruit doit être PORTÉ par
  l'état, pas transitoire sur l'action. Le « rêve »/organe MCTS agit comme un **régulateur de bruit
  d'état**, jamais comme un planificateur.

## Leçons (registre)
* **Une intervention qui fait deux choses doit être ablatée sur l'axe qui les sépare.** Ici l'axe
  n'était pas « où » (H vs action) seul mais « persistant vs transitoire ». La dissociation
  fourrage/reproduction n'apparaît QUE parce que le bras d'action égale presque le fourrage — un bras
  d'action trop faible aurait raté les deux et on aurait conclu « locus » pour la mauvaise raison.
* **Donner à l'hypothèse rivale sa meilleure chance** (balayer l'action jusqu'à saturation du fourrage)
  est ce qui rend le verdict robuste au reproche « pas assez de bruit ».

Converge [[EDR-DREAM-003]], [[EDR-DREAM-002]], [[EDR-DREAM-001]], [[planner-depth1-refuted]],
REF-EXPERIMENT-PREFLIGHT.
