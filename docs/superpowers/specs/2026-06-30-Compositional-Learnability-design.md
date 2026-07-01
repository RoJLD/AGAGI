# Design — Learnabilité compositionnelle : le substrat torch craque-t-il le means→ends de l'apex ?

Date : 2026-06-30

## Question scientifique

Convergence 104-113 : le verrou de l'apex (~0.21, chasse coop mammouth) est le SUBSTRAT (apprentissage),
pas le monde (111), ni la capacité réseau (105/110), ni l'horizon de crédit (113). L'audit SOTA
([[sota-gap-substrate]]) précise : le « Mamba » est un Liquid Time-Constant network écrit à la main en
numpy, ~5 cachés, SANS gradient → « ne peut pas apprendre de politiques COMPOSITIONNELLES ». Le barreau-0
de migration moteur est livré (`src/agents/backend.py`/`backend_torch.py`, ADR-003) et `tools/substrate_ab.py`
montre que torch (autograd) bat legacy (hebbien/gradient-main) sur une contingence SIMPLE (10/10 seeds).

MAIS l'apex est COMPOSITIONNEL : crafter EN état-1 (récompense immédiate nulle) débloque la récompense de
chasser EN état-2 — un means→ends à crédit différé. `substrate_ab` ne teste PAS cette structure (mono-étape
réactive). **Un substrat torch (autograd) apprend-il une contingence compositionnelle means→ends que le
substrat legacy (hebbien/Actor-Critic TD main, ~5 cachés) NE PEUT PAS ?** C'est la PORTE DE DÉCISION (que
l'audit appelle explicitement) avant le gros chantier torch-en-prod.

Lien EDR 113 : le γ-sweep n'a pas levé l'apex (horizon de crédit éliminé) AVEC le substrat legacy. Ce banc
isole POURQUOI : est-ce que la RÈGLE D'APPRENTISSAGE legacy (hebbien/gradient-main) ne peut PAS faire le
crédit compositionnel — alors que l'autograd torch le peut ? Si oui, l'apex n'est pas bloqué par « l'horizon
est inutile » mais par « le substrat ne sait pas EXPLOITER l'horizon ».

## Contexte (vérité terrain)

- `src/agents/backend.py` : `PopulationModel` ABC — `forward(batch_obs, env_surprise_batch=None)`,
  `learn(rewards_batch, actions_batch=None)`, `extract()`. `make_population(agents, backend="legacy"|"torch")`.
  legacy = wrapper `MambaBatchModel` (non-régressif) ; torch = `TorchPopulationModel` (LTC différentiable +
  Actor-Critic TD par autograd). LIVRÉ par session // — NE PAS le modifier.
- `tools/substrate_ab.py` : `run_substrate_ab(backend, seed, ticks, n_agents, target_move)` entraîne une pop
  à émettre `target_move` sur une obs FIXE (contingence mono-étape) ; `compare(seeds, ticks, n_agents)` A/B
  apparié ; `compute_ab_verdict(rows, band=0.02)` PUR (median_diff, n_gradient_favorable, sign_p, verdict
  GRADIENT_GAGNE/HEBBIEN_GAGNE/NEUTRE). `_MOVE=8` logits de déplacement. `actions_batch` = liste de dicts
  `{"move": int, "grab": 0, "rub": 0}`.
- Le substrat a une RÉCURRENCE (`H_prev`, LTC) → mémoire intra-épisode disponible (nécessaire pour la
  composition : se souvenir d'avoir fait X).

## Hypothèse (3 issues)

1. **Substrat-règle = verrou (gate OUVERTE)** : torch apprend la composition (X-puis-Y), legacy NON, à taille
   cachée fixe → la RÈGLE D'APPRENTISSAGE (autograd vs hebbien/main) est ce qui bloque le compositionnel/apex
   → torch-en-prod justifié pour lever l'apex (dé-risque le gros chantier). Raffine EDR 113 (le legacy ne
   sait pas exploiter l'horizon, pas « l'horizon est inutile »).
2. **Taille aussi requise** : les DEUX échouent à ~5 cachés → le gradient seul ne suffit pas, il faut aussi
   plus de cachés (représentation) → informe le dimensionnement du substrat cible.
3. (garde-fou tâche) **les deux réussissent** → la micro-tâche est trop facile (réactive, pas vraiment
   compositionnelle) → re-spécifier (rendre le crédit plus différé / la mémoire obligatoire).

## Architecture — `tools/substrate_ab_compositional.py` (nouveau, réutilise le backend)

### Tâche compositionnelle 2-étapes (means→ends en miniature)

Un ESSAI = 2 ticks consécutifs sur la même population batchée :
- **Étape 1 (état S1)** : obs fixe `obs_A` (motif aléatoire seedé). `pop.forward(obs_A)` → `move1`.
  `did_X[i] = (move1[i] == TARGET_X)`. Récompense étape 1 = **0.0** (le « craft » ne paie pas immédiatement) ;
  `pop.learn(zeros, [{"move": move1[i], "grab":0, "rub":0}])` (laisse l'Actor-Critic TD propager via la
  valeur de S2).
- **Étape 2 (état S2)** : obs fixe `obs_B` (motif distinct). `pop.forward(obs_B)` → `move2`.
  Récompense étape 2 = **+1.0 si `move2[i]==TARGET_Y` ET `did_X[i]`**, sinon **−1.0**.
  `pop.learn(reward2, [{"move": move2[i], ...}])`.
- `obs_B` NE CONTIENT PAS `did_X` → l'agent doit s'en souvenir via sa récurrence (mémoire obligatoire =
  vraie composition, pas deux réflexes).

Métrique = taux d'essais PLEINEMENT corrects (X puis Y) début vs fin → `delta` = apprentissage compositionnel.
A/B apparié `legacy` vs `torch` par seed ; verdict via `compute_ab_verdict` (réutilisé, importé de
`substrate_ab`). `TARGET_X`/`TARGET_Y` = 2 moves distincts (ex. 0 et 4).

### Fonctions (miroir de `substrate_ab`, DRY)

- `run_compositional(backend, seed, trials, n_agents) -> dict` : boucle d'essais, renvoie
  `{backend, seed, trials, n_agents, hit_start, hit_end, delta}` (hit = essai pleinement correct).
- `compare(seeds, trials, n_agents) -> dict` : A/B apparié, réutilise `compute_ab_verdict` de `substrate_ab`.
- `main()` : env `SABC_SEEDS`/`SABC_TRIALS`/`SABC_AGENTS`, imprime le verdict + par-seed.

## Instrument & verdict

A/B `legacy` vs `torch` apparié par seed (≥5 seeds), `delta` compositionnel (taux X-puis-Y fin − début) :
- **GRADIENT_GAGNE** (median_diff > band, sign_p bas) → issue 1 : torch craque la composition, legacy non.
- **NEUTRE + les deux deltas HAUTS** → issue 3 : tâche trop facile (garde-fou, re-spécifier).
- **NEUTRE + les deux deltas BAS** → issue 2 : taille/représentation aussi requise.
Rapporter `hit_start`/`hit_end`/`delta` PAR bras et par seed (jamais le scalaire nu).

## Garde-fous anti-théâtre

- **La tâche compositionnelle DOIT être plus dure que la mono-étape** : VÉRIFIER que le legacy la RATE
  (`legacy delta` faible) — sinon elle ne teste pas la composition (issue 3). Contrôle : le legacy réussit
  la version mono-étape de `substrate_ab` mais doit échouer la compositionnelle.
- **Mémoire obligatoire** : `obs_B` n'encode pas `did_X` → un substrat sans mémoire utile ne peut pas (la
  composition n'est pas réactible).
- A/B apparié par seed, déterministe (`np.random.seed` + `torch.manual_seed`), contraste sur la MÊME
  tâche/taille.
- **Verdict BORNÉ** : micro-tâche proxy, PAS une preuve de transfert apex en prod. C'est une PORTE DE
  DÉCISION (torch-en-prod vaut-il l'investissement), pas une conclusion sur l'apex réel.

## Tests

- **`compute_ab_verdict` réutilisé** (déjà testé dans `substrate_ab` ; ne pas re-tester).
- **Contingence de la tâche** : test pur que la récompense d'étape 2 vaut +1 SSI (`move2==TARGET_Y` ET
  `did_X`), −1 sinon — sur des `move1`/`move2` synthétiques connus (4 cas : X✓Y✓ → +1 ; X✓Y✗ → −1 ;
  X✗Y✓ → −1 ; X✗Y✗ → −1). Pas de backend requis (fonction de scoring pure).
- **Smoke A/B** (`slow` si torch lent) : `compare(seeds=(0,), trials=40, n_agents=4)` tourne pour les deux
  backends et renvoie un dict avec `verdict` ∈ {GRADIENT_GAGNE, HEBBIEN_GAGNE, NEUTRE} et `per_seed` non vide.
  (Skip propre si `import torch` échoue — `pytest.importorskip("torch")`.)

## Hors périmètre (YAGNI)

- Pas de torch-en-prod (`env.step`/contrat forward complet = gros chantier multi-sessions, séparé).
- Pas de modif de `backend.py`/`backend_torch.py`/`substrate_ab.py` (propriété session // ; on IMPORTE
  `make_population` + `compute_ab_verdict`, on n'altère rien).
- Pas de facteur taille cachée (suite si issue 1 ou 2). Pas de re-test apex réel (bloqué hors torch-prod).

## Suite (selon issue)

- **Issue 1 (gradient gagne)** : porte OUVERTE → le gros chantier torch-en-prod (contrat forward complet)
  est justifié pour re-tester l'apex réel sur substrat gradient. Coordonner avec la session // qui possède
  le backend.
- **Issue 2 (taille aussi)** : ajouter un facteur taille cachée au banc avant l'investissement prod.
- **Issue 3 (trop facile)** : durcir la tâche (crédit plus différé, k>2 étapes, mémoire plus exigeante).

## Variables d'expérience

`backend` (legacy/torch), tâche compositionnelle (`TARGET_X`/`TARGET_Y`, structure de récompense X-gate-Y),
`trials`/`n_agents`/`seeds`. EDR cible = prochain libre (sessions // ont pris 113/114 ; viser **115**, à
reconfirmer à l'écriture).
