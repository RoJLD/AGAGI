# Design — Intégration torch in-world (axe 1, chemin critique G1)

> Session 2026-07-02. Cadre : clôture de la carte valeur torch (parité 140/141, mémoire BPTT 145,
> binding `learn_episode` 158/159). Reste explicite du fil G1 = allumer cette carte dans la boucle
> biosphère. Backlog : [`../../BACKLOG.md`](../../BACKLOG.md) §2026-07-02. Méthode : Commandement 15.

## Problème

La recette de binding means→ends (`gate + crédit épisodique + anti-saturation`) est prouvée en
isolation (EDR-158/159, `TorchPopulationModel.learn_episode`, +0.298 vs +0.000 pour le TD différé).
Elle n'a **jamais tourné dans la biosphère**. EDR-148 a montré que le `learn()` TD par tick ne porte
pas le binding — il faut le crédit épisodique. Or la biosphère est une boucle continue sans notion
d'épisode. **La question de design est : comment définir un épisode in-world et y brancher
`learn_episode`, sans régresser le chemin legacy.**

## Contrainte d'architecture décisive

Le `batch_model` est **transitoire** : [`world_1_stoneage.py:992`](../../../src/worlds/world_1_stoneage.py)
le ré-instancie à chaque tick. L'état durable (H, poids) vit dans les agents (`a["model"]`), pas sur
le modèle batché. Conséquences :

1. Le **buffer de trajectoire** de `learn_episode` ne peut pas vivre sur le batch_model (jeté/tick) →
   il est porté par le **monde** (`self._torch_traj`).
2. Le `pop` torch doit **persister entre ticks** (sinon l'optimiseur SGD et `w_gate`/`b_gate` sont
   recréés à chaque tick, perdant l'apprentissage) → il est **hissé hors de la boucle par-tick** pour
   le backend torch. Le legacy reste recréé/tick (strictement non-régressif).

Le banc 158/159 masquait ce point : là-bas `pop` persiste sur tout l'épisode naturellement.

## Architecture retenue

### Couture
La boucle biosphère passe par **`make_population`** (ADR-003 — dette payée : aujourd'hui seuls
tools/tests l'utilisent, la biosphère utilise le seam `batch_model_cls`). Un flag opt-in
**`USE_TORCH_INWORLD`** (défaut off) sélectionne le backend torch persistant ; off = chemin legacy
inchangé.

### Définition d'épisode : fenêtre glissante K ticks
L'épisode = les K derniers ticks d'un buffer glissant `(obs, actions, reward)` porté par le monde.
Tous les K ticks : `pop.learn_episode(obs_seq, actions_seq, returns)` en **plus** du crédit par tick
(`learn`/`compute_policy_gradient` conservé). Retour épisodique `returns` = somme actualisée des
rewards de la fenêtre, baseliné par le caller (moyenne de population).

Alternatives écartées : **vie de l'agent** (crédit trop dilué, durées variables, mémoire O(vie)) ;
**segments événementiels** (détection reward-major à câbler — reporté). K devient une **variable EDR
propre** (le régime K≈fenêtre est exactement celui de 158/159).

### Placement du buffer
`self._torch_traj = deque(maxlen=K)` sur l'instance monde. Chaque tick, après forward + calcul des
rewards (déjà présents [`world_1_stoneage.py:1445`](../../../src/worlds/world_1_stoneage.py)), on
push `(batch_obs, actions_batch, rewards)`. Sur cohorte **variable** (naissances/morts), on n'inclut
dans `learn_episode` que les agents présents sur toute la fenêtre (alignement par identité d'agent) —
sinon les indices batch se décalent. Reco : figer la cohorte de la fenêtre (agents nés avant le début
de fenêtre et vivants à la fin), congruent avec la règle cohorte-fixe d'EDR-114b.

## Progression flag-par-flag (Commandement 15, 1 variable)

Chaque cran = 1 EDR powered avec banc in-world. On ne passe au cran N+1 que si N est mesuré.

| Cran | Variable allumée | Attendu | Banc |
|---|---|---|---|
| 0 | `USE_TORCH_INWORLD` (forward seul) | parité survie vs legacy | déjà prouvé hors-boucle 140/141 ; re-vérifier in-world |
| 1 | + `learn_episode` (gate off) | crédit épisodique ne régresse pas la survie | A/B survie K=... |
| 2 | + gate (`CONDITION_GATE`, `GATE_TARGET`) | binding in-world émerge (P(Y\|X) > y_rate) | banc binding in-world |
| 3 | + `ANTISAT` | binding 10/10 propre (cf. 136) | idem + décompo |
| 4 | + gate multiplicatif (`GATE_MULT`, EDR-160, en vol) | suppression propre hors-contexte | idem |

## Banc in-world (l'instrument)
Nouveau `tools/torch_inworld_ab.py` : A/B survie **apparié multi-seed** entre `USE_TORCH_INWORLD`
off/on à budget compute égal, verdict {TRANSFERE/NEUTRE/NUIT} via `substrate_ab.compute_ab_verdict`.
Réutilise `Harness`/`seed_boundary` (D1) et la cohorte-fixe (114b). Pour le cran 2+, mesurer le
**binding in-world** = P(action ends | contexte means) vs marginale, décodé des trajectoires
bufferisées (l'instrument direct P(Y|X) d'EDR-126, pas le joint).

## Error handling / non-régression
- `USE_TORCH_INWORLD=False` → zéro changement de comportement legacy (test de non-régression :
  run identique bit-à-bit au chemin actuel).
- torch absent (dépendance optionnelle) → le flag on lève une erreur claire au boot, pas en plein run.
- Buffer sur cohorte incomplète → skip `learn_episode` ce cycle (log), ne crashe pas.
- `pop` persistant : invalider/reconstruire quand la topologie évolue (add_node change N) — détecter
  le changement de dimension et reconstruire le `pop` proprement.

## Testing
- Non-régression legacy (flag off) : nouveau test sandbox, run court identique.
- Boot torch persistant : `pop` survit ≥2 ticks, `w_gate`/`opt` conservés.
- Buffer glissant : maxlen respecté, cohorte alignée, `learn_episode` appelé tous les K ticks.
- Reconstruction sur add_node : dimension N change → pop reconstruit sans perte de génome.
- Chaque cran : le banc `torch_inworld_ab.py` produit un verdict (le livrable EDR).

## Hors scope (repoussé)
Axe 2 (`transfer_ratio` à l'échelle, en //), axe 3 (replay 127/156/157 sous crédit épisodique — test
de H-unif, APRÈS cran 1), axe 4 (G4/G2). Segments événementiels comme définition d'épisode.
