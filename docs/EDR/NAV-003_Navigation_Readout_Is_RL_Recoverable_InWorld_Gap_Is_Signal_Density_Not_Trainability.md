---
id: EDR-NAV-003
type: EDR
title: Le readout de navigation EST récupérable par crédit RL (recovery 0.92) — le gap in-world est la DENSITÉ du signal, pas la trainabilité du readout
status: accepted
gate: G0
verdict: RL_RECOVERS
---

# EDR-NAV-003 : Le readout de navigation est RL-récupérable — le verrou in-world est le signal, pas le readout

> Territoire NAV. Jalon **M1 offline** du brief T1 (`HANDOFF_T1_NAV_readout_brief.md`). Dé-risque la fourche
> de conception de T1. Banc `tools/nav_readout_trainability.py` (tooling-only, `git diff src/` VIDE, déterministe).

## Question

EDR-NAV-001 : H décode la direction-correcte à ~0.81 (ridge) mais l'agent émet le bon pas à **0.03**
(READOUT_GAP). Le champion a évolué **sous RL** (récompense de forage) et n'a PAS appris ce readout. Fourche
de conception de T1 (brief §Approche) : le readout doit-il être entraîné par **crédit RL** (récompense) ou
par **cibles supervisées** (l'oracle) ? M1 le tranche offline, sans toucher la prod ni la boucle in-world.

## Méthode

Contrôle à UNE variable (comme EDR-COG-001). Sur les MÊMES paires `(H, correct)` FIGÉES capturées par le
probe NAV-001 (cohorte fixe, oracle 114, n=17411 agent-ticks), deux readouts `Linear(N→4)` **identiques**
(même init au seed, même split train/test z-scoré, même Adam/lr/steps) — **seule la perte diffère** :
- **SUP** : cross-entropy sur l'oracle → plafond (≈ ridge NAV-001).
- **RL** : REINFORCE-bandit contextuel, récompense = 1 si l'action échantillonnée == oracle, baseline EMA.
  Signal per-pas **dense et parfaitement aligné** = **BORNE SUPÉRIEURE** de ce que le RL peut faire (le forage
  réel est plus clairsemé/désaligné → s'il échoue ici, il échoue *a fortiori* en monde).

`recovery = (acc_rl − chance) / (acc_sup − chance)`.

## Résultat (n=17411, K=3 inits torch, déterministe)

| readout | acc (par-seed) |
|---|---|
| ridge (NAV-001, réf externe) | 0.825 |
| **SUPERVISÉ** (CE oracle) | **0.858** (0.854 / 0.859 / 0.860) |
| **RL** (REINFORCE-bandit) | **0.822** (0.826 / 0.814 / 0.824) |
| **recovery** | **+0.923** |

Verdict **RL_RECOVERS** (recovery ≥ 0.70). Reproduit en calibration (n=3148 : recovery +0.933). Le RL atteint
le plafond ridge (0.822 ≈ 0.825) ; les deux bras sont serrés sur 3 inits.

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : sur H figé, un readout entraîné par récompense RL **dense et alignée** atteint 92 % du plafond
  supervisé au-dessus du hasard — le readout de navigation **EST RL-récupérable**.
- **INTERPRÉTATION** : l'échec in-world (émise==correct=0.03 malgré une évolution sous RL) n'est **PAS** que
  le readout serait inentraînable par RL. Le verrou est que la récompense de forage in-world est trop
  **clairsemée / désalignée** pour fournir le signal per-pas de direction que le RL exige. → **le gap de
  readout de navigation est un problème de DENSITÉ/ALIGNEMENT du signal, pas de trainabilité du readout.**
- **CONSÉQUENCE pour T1 (dé-risque la fourche)** : T1 doit **FOURNIR un signal per-pas dense de navigation**.
  Deux routes désormais toutes deux étayées : **(a) perte auxiliaire supervisée** sur l'oracle (le signal le
  plus dense — reco d'origine du brief) OU **(b) reward-shaping per-pas dense** (« s'est rapproché de la
  proie » → récompense), puisque le RL récupère dès que le signal est dense. La borne-sup bandit garantit
  qu'un signal per-pas suffit ; le choix (a)/(b) devient un détail d'implémentation, pas un risque.

## Portée / Bornage

1. Le bandit est la **borne supérieure** (récompense per-pas parfaitement alignée sur l'oracle). Il ne prouve
   PAS que la récompense de forage clairsemée réussirait — il prouve l'inverse utile : le readout est capable,
   donc l'échec in-world est **localisé au signal**, pas au readout.
2. Readout entraîné sur H **figé** (isolé de l'encodeur et des têtes concurrentes value/grab/rub). L'entraînement
   in-world réel devra composer avec la non-stationnarité de H et l'interférence inter-têtes (cf. EDR-COG-001 :
   le crédit multi-tête vit dans le tronc partagé) → à valider en M2 in-world.
3. Substrat/données = champion cohorte fixe, forage figé (speed=0, comparable 114b). n grand (17411) → serré.
4. `Linear(N→4)` = même classe que le ridge NAV-001 ; le SUP (Adam+CE) dépasse légèrement le ridge (0.858 vs
   0.825) → régime d'entraînement torch sain, cohérent avec la cible torch de T1.

## Suite

- **Ferme la fourche de conception de T1** : le readout est trainable par crédit dense → T1 (in-world, session
  torch) = injecter un signal per-pas dense (aux supervisé OU shaping). Brief T1 mis à jour.
- M2 in-world reste à la session torch (touche `backend_torch` + boucle = territoire T3/torch) : valider que
  sous non-stationnarité + têtes concurrentes, le signal dense ferme bien émise==correct → p_reach ~0.875.

Lignée : NAV-001 (READOUT_GAP localisé) → NAV-002 (énergie : encodeur riche, readout endogène non isolable)
→ **NAV-003 (readout NAV RL-récupérable : le verrou est le signal dense, pas la trainabilité)**.
Étend [[lewis-energy-economy-wall]] + [[sota-gap-substrate]] ; converge [[coop-competence-is-population-property]]
(signal/crédit, pas substrat).
