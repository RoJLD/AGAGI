---
id: EDR-134
type: EDR
title: "A/B in-world torch vs legacy — INCONCLUSIF (confondu) : le barreau-0 gradient ne réplique pas en monde ; les organes omis (NTM/router/TTC) sont PORTEURS pour les champions"
status: accepted
gate: null
verdict: INCONCLUSIF_CONFONDU
---

# EDR 134 : A/B in-world torch vs legacy — inconclusif (confondu), organes porteurs

## Contexte

EDR-115 (barreau-0) : sur une contingence jouet, le substrat GRADIENT (torch, Actor-Critic TD
autograd) bat le hebbien (legacy numpy) 10/10 (sign_p 0.002). Question : **ça réplique-t-il
in-world ?** ADR-003 a livré `TorchBatchModel` (Tasks 1-2), conforme au seam `batch_model_cls`
(world_1_stoneage.py:42). Aligné sur EDR-129 (le transfert est trivialement parfait faute de
spécialisation), on mesure la **learnabilité IN-WORLD** : le gradient intra-vie fait-il survivre
mieux dans la vraie biosphère ? (`compute_policy_gradient` tourne chaque tick même en
benchmark_mode, world_1_stoneage.py:1447 → la règle d'apprentissage pèse sur la survie.)

## Méthode

`tools/substrate_world_ab.py` : `measure_survival` injecte `env.batch_model_cls` dans une cohorte
fixe au sweet-spot (EDR-085), `memory_retriever` neutralisé. A/B apparié legacy (`MambaBatchModel`,
substrat COMPLET) vs torch (`TorchBatchModel`, core-LTC), K=10 seeds, 12 agents, 300 ticks, stoneage.
Deux bras : (1) cohortes FRAÎCHES (tabula) ; (2) champion HoF #1 stoneage. Verdict = survie médiane
appariée, test de signe (bande 2 ticks). Machine confirmée libre (probe `is_machine_idle` SAFE).

## Constat

| bras | verdict | legacy | torch | median_diff | pro-torch | sign_p |
|---|---|---|---|---|---|---|
| cohortes fraîches | **NEUTRE** | 17.2 | 18.5 | +1.5 | 8/10 | 0.039 |
| champion stoneage | **HEBBIEN_GAGNE** | **74.5** | **38.8** | **−45.8** | 2/10 | 0.109 |

- **Fraîches** : survie ~17-18 ticks = le **plancher létal** (EDR-129). Des agents frais meurent trop
  vite pour que l'apprentissage intra-vie différencie les substrats → NEUTRE. Léger penchant torch
  (8/10, +1.5 tick) mais dans le bruit/bande.
- **Champion** : le legacy fait **~2× la survie** du torch (74.5 vs 38.8), 8/10 pro-legacy, effet
  ÉNORME (−46 ticks) — le barreau-0 s'INVERSE en monde sur substrat compétent.

## Lecture — INCONCLUSIF (deux confonds identifiés, non séparables ici)

Le verdict champion **n'est PAS** un énoncé propre sur la règle d'apprentissage :

1. **Confound d'organes (dominant, attendu)** : le champion a évolué son `W` pour le substrat
   **complet** — NTM (self-wiring), router (neuromodulation), thresholds, TTC. `TorchBatchModel` est
   **core-LTC** : il OMET ces organes. Le champion, exécuté sur torch-core, ne peut plus exprimer sa
   compétence tunée aux organes → survie divisée par 2. Les cohortes fraîches n'ont rien de tuné à
   perdre → pas d'effondrement (NEUTRE). Le pattern (fraîches NEUTRE / champion effondré) est la
   **signature** de ce confound, pas de la règle d'apprentissage.
2. **Confound de plancher** (bras fraîches) : la survie au plancher masque tout signal
   d'apprentissage.
3. Contribution possible non séparable : le gradient torch (lr 0.04, chaque tick) pourrait aussi
   **déstabiliser** une politique déjà bonne (écho EDR-077 « le gradient fort NUIT en RL » ; EDR-095).
   Indissociable du confound d'organes sans un bras **legacy-core** (organes ablés côté legacy aussi).

## Conséquences

- **Le barreau-0 (EDR-115) NE se généralise PAS** tel quel en monde : l'avantage gradient sur une
  contingence jouet ne préserve pas — et semble nuire à — la compétence évoluée d'un champion, une
  fois les organes retirés. **Verdict : INCONCLUSIF** (confondu), pas un « legacy > torch » propre.
- **Leçon ACTIONNABLE (le livrable)** : les organes (NTM/router/TTC) omis par le MVP torch sont
  **PORTEURS** pour les agents compétents (champion −46 ticks sans eux). Un substrat torch de PROD ne
  peut PAS se limiter à core-LTC : il doit **porter les organes** (ou ré-évoluer les champions
  nativement sur le substrat torch). Migrer = répliquer le substrat COMPLET, pas le noyau.
- **Pour un test propre de la règle d'apprentissage** (suite) : (a) bras **legacy-core** (organes
  ablés côté legacy) pour isoler le confound d'organes ; (b) cohortes qui **vivent assez** (champion
  ou monde moins létal) pour dé-masquer le plancher ; (c) idéalement ré-évoluer un champion SUR le
  substrat torch (Baldwin) plutôt que transplanter un génome legacy.
- Outils : `tools/substrate_world_ab.py`, `tools/is_machine_idle.py`. Relié : `REF-LTC -A_ADOPTER_POUR-> EDR-134`.

## Caveats

1. Métrique unique (survie censurée), 1 monde (stoneage), 1 champion.
2. `TorchBatchModel` = MVP (core-LTC, dims homogènes) — le confound d'organes est structurel, pas un bug.
3. `sign_p` champion 0.109 (non significatif à n=10 : 2 seeds pro-torch dont un outlier legacy=254),
   mais la taille d'effet (−46 ticks médian) est massive et cohérente (8/10).
4. async_logger reste actif pendant le run (écrit KuzuDB) malgré memory_retriever off — non bloquant (machine idle).
