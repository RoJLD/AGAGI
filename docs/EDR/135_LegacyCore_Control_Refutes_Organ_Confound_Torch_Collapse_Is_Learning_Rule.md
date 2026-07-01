---
id: EDR-135
type: EDR
title: "Bras legacy-core RÉFUTE le confound d'organes d'EDR-134 : les organes du champion sont INERTES (NTM/attention/dreaming off, router non porteur) → le collapse torch = la RÈGLE D'APPRENTISSAGE, pas les organes"
status: accepted
gate: null
verdict: CONFOUND_ORGANES_REFUTE
---

# EDR 135 : legacy-core — le confound d'organes d'EDR-134 est réfuté ; le collapse torch tient à la règle d'apprentissage

## Contexte

EDR-134 (in-world torch vs legacy) : le champion stoneage s'effondre sous `TorchBatchModel`
(core-LTC) — legacy 74.5 vs torch 38.8 ticks (−46). Verdict INCONCLUSIF, **hypothèse dominante :
confound d'organes** — `TorchBatchModel` OMET NTM/router/thresholds/attention/dreaming, et le
champion aurait évolué son `W` POUR ces organes → s'effondre sans eux. EDR-134 laisse le test
propre en suite : **abler les mêmes organes CÔTÉ legacy** (bras legacy-core) pour séparer
« organes » de « règle d'apprentissage ». C'est ce bras.

## Méthode

Nouveau substrat `MambaCoreBatchModel(MambaBatchModel)` : hérite la règle d'apprentissage numpy
(Actor-Critic TD, `compute_policy_gradient`) mais able les organes que torch omet via flags de
classe lus par `type(self)` (non-régressif pour la base) — `ABLATE_ROUTER/THRESHOLDS/NTM/ATTENTION`
+ `FORCE_DREAM="off"`. A/B à **trois bras** (`tools/substrate_world_ab.py --mode arms`), K=10 seeds,
12 agents, 300 ticks, stoneage, sweet-spot (EDR-085), même champion HoF #1 qu'EDR-134 :

- **legacy-full** `MambaBatchModel` (organes ON, règle numpy)
- **legacy-core** `MambaCoreBatchModel` (organes ABLÉS, règle numpy)  ← contrôle nouveau
- **torch-core** `TorchBatchModel` (organes absents, règle autograd)

## Constat

| bras | survie médiane |
|---|---|
| legacy-full | **74.5** |
| legacy-core | **68.2** |
| torch-core | **38.8** |

| lecture appariée | median_diff | verdict | fav | sign_p |
|---|---|---|---|---|
| ORGANES (legacy_full − core) | **+0.25** | **NEUTRE** | 5/10 | **1.0000** |
| RÈGLE @parité (torch − core) | **−26.75** | HEBBIEN_GAGNE | 4/10 | 0.7539 |

`legacy=74.5` et `torch=38.8` **reproduisent EDR-134 à l'identique** (runs indépendants) → mesure
robuste. `core=68.2` est le datum neuf.

**Introspection du champion** (ce qui est réellement ablé) : `organ_genes=[False,False]` →
**attention ET dreaming DÉJÀ OFF** (les abler = no-op) ; `ntm_memory` chargé = **tout zéro** →
self-wiring NTM **no-op** (enable=0, pour legacy-full ET core) ; `thresholds` max|·|=0.13
(négligeable). **Seul organe réellement câblé = le ROUTER** (neuromodulation, `W_router` max|·|=5.5,
189 nz). La compétence vit dans `W` (429 nz, max 1.98).

## Lecture — le confound d'organes est RÉFUTÉ

1. **Hypothèse #1 d'EDR-134 (organes porteurs) : RÉFUTÉE.** Les organes que torch omet sont
   **inertes** pour ce champion (NTM/attention/dreaming off) ; le seul organe câblé (router) n'est
   **PAS porteur** : l'abler garde la survie (74.5→68.2, appariée NEUTRE, sign_p 1.0). Le pattern
   « fraîches NEUTRE / champion effondré » d'EDR-134 n'était donc **PAS** la signature d'un strip
   d'organes.
2. **Le collapse torch tient à la RÈGLE D'APPRENTISSAGE / substrat, pas aux organes.** À parité
   d'organes, legacy-core (TD numpy) survit **~1.75×** torch-core (TD autograd) : 68.2 vs 38.8
   (−26.75). Cohérent [[dreaming-organ-not-dead]] (EDR-095, forcer nuit) et EDR-077 (« gradient fort
   NUIT en RL ») : la descente autograd agressive (lr 0.04, chaque tick, à travers le pas LTC
   récurrent) **déstabilise** une politique déjà bonne. Le barreau-0 EDR-115 (gradient gagne sur
   JOUET) s'INVERSE sur un champion compétent en monde.
3. **Course-correction sur EDR-134** : sa « leçon actionnable » (« un substrat torch de prod doit
   PORTER les organes ») est **downgradée** — au moins pour ce champion, porter les organes ne
   sauverait rien. Le vrai verrou de migration est la **STABILITÉ du gradient intra-vie**.

## Conséquences

- **Migration (reco révisée)** : ne pas se focaliser sur le portage d'organes. Le levier est
  d'**apprivoiser le gradient intra-vie** sur substrat torch : lr plus bas, gating de
  l'apprentissage OFF pour agents compétents, ou contrainte type trust-region/KL — **OU** ré-évoluer
  nativement (Baldwin) pour que le connectome soit gradient-compatible dès l'origine. Nuance
  [[sota-gap-substrate]] : « migrer le moteur » exige de régler la règle, pas seulement la lib.
- **Suite re-priorisée** : (a) **ré-évoluer un champion NATIVEMENT sur torch** (Baldwin) devient le
  test-clé — un champion torch-natif évite-t-il le collapse ? ; (b) balayer `lr`/gating côté torch
  pour confirmer le mécanisme de déstabilisation ; (c) cohortes longues pour le plancher létal
  (fraîches, non tranché ici).
- Outils : `tools/substrate_world_ab.py` (mode `arms`), `src/agents/mamba_agent.py::MambaCoreBatchModel`.
  Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-135`.

## Caveats

1. **Confond résiduel core↔torch** (n'affecte PAS la réfutation du confound d'organes, seulement la
   lecture #2) : legacy-core utilise l'activation custom (`generated_ops.py`) et numpy ; torch utilise
   `tanh` et autograd. La « règle @parité » n'est donc pas 100% propre (activation + numérique en plus
   de la règle).
2. Verdict « règle @parité » **non significatif** (sign_p 0.75, 4/10 pro-torch) — effet GROS (−26.75)
   mais n=10 bruité. La réfutation du confound d'organes (ORGANES NEUTRE, sign_p 1.0), elle, est nette.
3. **Champion-spécifique** : ce champion a des organes inertes (cohérent [[intelligence-typing-flat-connectome]]
   / [[memory-architecture-audit]] : connectome plat, organes largement inertes). Un champion à
   attention/dreaming actifs pourrait différer.
4. 1 champion, 1 monde (stoneage), 1 métrique (survie censurée). async_logger KuzuDB en échec de lock
   (logging off) pendant le run — non bloquant (la survie ne dépend pas de KuzuDB ; repro confirmée
   par l'appariement exact des médianes legacy/torch avec EDR-134).
