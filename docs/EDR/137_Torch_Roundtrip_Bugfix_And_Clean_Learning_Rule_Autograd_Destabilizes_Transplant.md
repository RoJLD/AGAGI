---
id: EDR-137
type: EDR
title: "BUGFIX round-trip torch (apprentissage + récurrence intra-vie ne tournaient PAS in-world) + mesure CORRIGÉE : à parité d'organes, le TD autograd DÉSTABILISE le champion transplanté (33.0 < 38.8 statique, 0/10, sign_p 0.004) — confond d'organes toujours réfuté"
status: accepted
gate: null
verdict: TORCH_INTRALIFE_DESTABILISE_TRANSPLANT
---

# EDR 137 : bugfix round-trip torch + règle d'apprentissage propre (l'autograd déstabilise un champion transplanté)

## Contexte

EDR-135 (bras legacy-core) a réfuté le confond d'organes d'EDR-134 et attribué le collapse torch à
la « règle d'apprentissage » (autograd déstabilise). En scoutant la suite #2 (Baldwin natif), on
découvre un **bug d'intégration** qui invalidait cette lecture SECONDAIRE.

## Le bug (méthodologique)

Le monde **reconstruit le batch model à CHAQUE tick** depuis les agents vivants
(`world_1_stoneage.py:992`, dans `step()`). Legacy round-trip son état récurrent et sa transition TD
différée **via l'agent** (`a.H_prev` :380, `a._td` :827) → ils survivent au rebuild. `TorchBatchModel`
les stockait **sur le modèle** (`self.H`, `self._prev`) → **jetés chaque tick**. Conséquences :

- `self.H` repart à **zéro** chaque tick → torch **sans récurrence** in-world.
- `_td_update` (seul endroit avec `opt.step()` + `_write_back`) n'est atteint que si `self._prev`
  existe, or il est None sur chaque instance neuve → **torch n'apprenait JAMAIS** in-world.

**Preuve empirique** (pattern monde = nouvelle instance/tick, mêmes agents, 6 ticks) :
`max|ΔW| legacy = 0.043` (apprend) vs `max|ΔW| torch = 0.000` (n'apprend pas).

**Donc dans EDR-134 et EDR-135, le bras « torch » était un réflexe STATIQUE, sans apprentissage ni
récurrence.** La lecture secondaire d'EDR-135 (« règle d'apprentissage ») était **confondue** : la
règle ne tournait pas. (La lecture PRIMAIRE d'EDR-135 — organes NEUTRE — compare legacy-full vs
legacy-core, deux bras identiques sauf organes, **reste valide**.)

## Le fix

`TorchBatchModel` round-trip désormais, comme legacy, via l'agent : `a._torch_H` (état caché) et
`a._torch_td` (transition TD différée, en numpy) ; `__init__` les restaure (H, `self._prev` batché).
Post-fix, `max|ΔW| torch = 0.015 (>0)` et H persiste entre ticks. Test :
`test_learns_and_carries_H_across_per_tick_rebuild`.

## Mesure CORRIGÉE (A/B 3-bras propre, K=10 stoneage, même champion)

| bras | survie médiane |
|---|---|
| legacy-full | 74.5 |
| legacy-core | 68.2 |
| torch-core (apprentissage RÉPARÉ) | **33.0** |

| lecture appariée | median_diff | verdict | fav | sign_p |
|---|---|---|---|---|
| ORGANES (legacy_full − core) | +0.25 | **NEUTRE** | 5/10 | 1.0000 |
| RÈGLE @parité (torch − core) | **−24.75** | HEBBIEN_GAGNE | **0/10** | **0.0039** |

- **Confond d'organes : toujours RÉFUTÉ** (NEUTRE p=1.0, identique à EDR-135 — legacy déterministe).
- **RÈGLE @parité maintenant PROPRE et SIGNIFICATIVE** : les deux bras apprennent + récurrent, seul
  le moteur diffère → torch-core survit **2× moins** que legacy-core, **0/10** seeds, sign_p 0.004.
- **Clé** : torch AVEC apprentissage (33.0) survit **MOINS** que torch SANS apprentissage (38.8,
  EDR-134/135). L'activation (custom vs `tanh`) est **constante** entre ces deux torch → cet écart
  (−5.8) est **purement l'effet du moteur d'apprentissage** : le TD autograd (lr 0.04, chaque tick,
  à travers le pas LTC récurrent) est **net-DÉSTABILISANT** pour le connectome évolué du champion.

## Lecture

1. EDR-135 avait raison sur le fond (« autograd déstabilise ») mais pour la mauvaise raison ; c'est
   maintenant mesuré proprement. Cohère EDR-077 (« gradient fort NUIT en RL ») et
   [[dreaming-organ-not-dead]] (095, forcer une dynamique nuit).
2. **Nuance décisive** : le champion a été évolué sous la règle numpy. La déstabilisation peut venir
   du MOTEUR **ou** du mismatch (connectome façonné par une autre règle). **Ces deux hypothèses sont
   exactement ce que la suite #2 (Baldwin natif torch) sépare** : un connectome évolué SOUS l'autograd
   dès la naissance évite-t-il l'effondrement ? Le round-trip réparé rend ce test enfin possible
   (l'évolution native torch aurait sinon évolué des réflexes statiques).

## Conséquences

- **Prérequis de migration LEVÉ** : torch apprend + récurrent in-world. `substrate_world_ab` mode
  `arms` est désormais un banc de règle d'apprentissage PROPRE.
- **Reco migration** (affinée) : « torch-en-prod » naïf (lr 0.04/tick sur génome legacy) DÉGRADE une
  politique compétente. Deux pistes non-exclusives : (a) **Baldwin natif** (#2, test-clé) ; (b)
  **apprivoiser le gradient** (sweep lr, gating de l'apprentissage quand la politique est bonne,
  trust-region/KL). Étend [[sota-gap-substrate]].
- Outils : `src/agents/torch_batch_model.py` (round-trip), `tools/substrate_world_ab.py` (arms).
  Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-137`.

## Caveats

1. **Confond résiduel core↔torch** : legacy-core = activation custom (`generated_ops`) + numpy ;
   torch = `tanh` + autograd. Le −24.75 legacy-core vs torch mélange activation + moteur. MAIS le
   sous-écart torch-avec vs torch-sans apprentissage (−5.8) isole le moteur (activation constante).
2. `lr=0.04` non balayé — la déstabilisation pourrait s'atténuer à lr plus bas (piste (b)).
3. 1 champion transplanté (legacy-évolué), 1 monde (stoneage), 1 métrique (survie censurée). Le verdict
   « déstabilise » vaut pour un TRANSPLANT ; le natif (Baldwin) est le test propre du moteur seul.
4. Round-trip validé sur cohorte fixe (A/B) ; en évolution (naissances/morts) l'update TD est sauté
   au 1er tick d'un nouveau-né (self._prev None si un agent manque de transition) — conservateur, non
   bloquant.
