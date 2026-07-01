---
id: EDR-135
type: EDR
title: "G4 anticipation dé-pausée : le blocueur n=0 (survie) est levé (champion+sweet-spot, n=71) mais DEUX blocueurs plus profonds apparaissent — (1) l'organe g est INERTE in-world (bug d'ordre de persistance : planner_G extrait AVANT l'update -> mean|G|=0) ; (2) une fois le bug simulé-corrigé, g LINÉAIRE est NEUTRE sur obs riches (median_ratio 1.008, 14/44 fav) alors qu'il est G_FIDELE dans la grille-jouet (0.132, 82%) -> la fidélité ne transfère PAS au monde riche"
status: accepted
gate: G4
tests: [SDR-G4]
verdict: G_INERTE_PUIS_LINEAIRE_NEUTRE_OBS_RICHES
---

# EDR 135 : Anticipation — l'organe g est inerte in-world (bug), et g linéaire est neutre sur obs riches

## Contexte

L'arc « dreaming → planificateur » (anticipation conditionnée par l'action `g(H,a)→H'`, depth-1) était
en **PAUSE** (mémoire `planner-depth1-refuted`) : la sonde de fidélité de `g` sur obs riches stoneage
rendait **n=0** (agents frais morts ~10-15 ticks < warmup → aucune transition mesurable). Décision robla :
« la cognition reprendra quand le substrat survivra ». **EDR-129 lève ce présupposé** : au sweet-spot
métabolique (EDR-085), un champion HoF survit 66-135 ticks, pas 10. Le blocueur survie est donc
potentiellement levé → on re-mesure enfin si `g` est fidèle sur le VRAI monde (le prérequis nommé du fil,
avant tout Dyna/bilinéaire). Pivot depuis le frontier binding/moteur (saturé de WIP parallèle).

## Méthode

`tools/g_fidelity_probe.py` étendu (TDD, non-breaking) : injection d'un **champion** + **cohorte fixe**
(`genome`/`benchmark`), régime EDR-129 (sweet-spot, nuit OFF, scaffolds OFF). **Correctif de perf** :
l'`async_logger` KuzuDB (écriture par tick) est sauté en benchmark → run de **>120 s à 2,4 s** (×50),
inutile pour une mesure de fidélité. Verdict = ratio `g_err/base_err` apparié (test de signe), contrôle
= la grille-jouet 1-D (`run_probe_env`).

## Constat — deux blocueurs sous la survie

**1. Survie levée, mais `g` INERTE in-world.** Champion (dims 64/126) en stoneage : **n=71 transitions
mesurables** (blocueur n=0 levé) MAIS `mean|G[a]| = 0.0000` partout → verdict NEUTRE trivial
(median_ratio 1.000 : `g=0 ⟹ g_err=base_err`). `g` ne s'apprend **jamais** (benchmark ET libre, 35 ticks).

**Diagnostic (instrumenté).** `update_transition` EST appelé (241×), `move ∈ [0,8)` à **100 %** → l'update
se déclenche et s'applique bien à `G_batch` en place. Le verrou est un **bug d'ordre de persistance** dans
`MambaBatchModel` :
- forward : `G_batch` remis à zéro (`mamba_agent.py:435`) puis restauré depuis `agent.planner_G` (:437-440),
  puis `agent.planner_G = G_batch` **extrait** (:744) ;
- PUIS `compute_policy_gradient` (:819) met à jour `G_batch` — **après** l'extraction ;
- tick suivant : `G_batch` re-remis à zéro depuis le `planner_G` **périmé** → l'update est **perdu**.

Le banc-grille échappe au bug (boucle propre) → il montrait `g` fidèle, masquant l'inertie in-world.

**2. Bug simulé-corrigé (re-persister `planner_G` APRÈS `compute_policy_gradient`, par monkeypatch — le
fichier `mamba_agent.py` est WIP parallèle, non patché ici) : `g` accumule (mean|G|>0) mais reste NEUTRE.**

| condition | verdict | median_ratio | n_fav / n | note |
|---|---|---|---|---|
| grille-jouet 1-D (contrôle) | **G_FIDELE** | **0.132** | ~82 % | `g` linéaire prédit bien (7,6×) |
| stoneage, organe tel quel | NEUTRE (trivial) | 1.000 | 0/71 | `g≡0` (bug de persistance) |
| stoneage, fix simulé (5 seeds, 24 ag) | **NEUTRE** | **1.008** | **14/44** | `g` accumule mais n'aide pas |

`g` linéaire est **NEUTRE sur obs riches** (median_ratio ≈ 1,0, 32 % favorables, sign_p 0,03 côté
inutile) — sa fidélité de la grille-jouet **ne transfère PAS** au monde riche.

## Lecture

- La question en pause est **résolue avec preuve** (pas « impossible à mesurer ») : sur obs riches, le
  `g` LINÉAIRE depth-1 n'a pas de fidélité → confirme et étend le **« easy-grid caveat »** de la mémoire
  (fidèle seulement dans le cas 1-D éparse le plus favorable au `g` linéaire état-indépendant).
- Deux verrous distincts, tous deux **sous** la survie (qui était le blocueur supposé) : un **bug de code**
  (organe mort in-world) PUIS un **verrou de fond** (le `g` linéaire ne modélise pas la dynamique latente
  riche). Convergent avec le fil substrat (connectome plat, organes souvent inertes en prod :
  [[nas-bottleneck-is-substrate-not-search]], [[intelligence-typing-flat-connectome]]).

## Conséquences

- **Livré (path-scoped, non-colliding)** : `g_fidelity_probe` — injection champion (lève n=0, n=71) +
  gating KuzuDB (×50 perf) + test TDD. Réutilisable pour toute future variante d'anticipation.
- **Fix recommandé (NON appliqué — `mamba_agent.py` est WIP parallèle, MambaCoreBatchModel)** : déplacer
  la persistance `planner_G` APRÈS `compute_policy_gradient`, ou re-extraire en fin de step. Une ligne.
  À coordonner avec la session qui édite `mamba_agent.py` ([[parallel-sessions-shared-tree]]).
- **Levier restant du fil** = `g` **bilinéaire** état-dépendant (`H'=H_rec+W_a·H`) — le seul non testé.
  MAIS le NEUTRE du linéaire (avec `g` qui accumule pourtant) suggère que la forme de `g` n'est pas le
  vrai verrou ; à re-mesurer une fois le bug de persistance corrigé, avant d'investir dans Dyna/depth-k.

## Caveats (honnêteté)

1. **Fix par monkeypatch** (pas dans le code de prod) : le résultat « corrigé » suppose que re-persister
   `planner_G` après l'update est la bonne correction ; à valider quand le fix réel sera appliqué.
2. **La sonde mesure `g` contre les transitions de `H_prev`** (latent principal) alors que `g` est entraîné
   sur `H_rec` (récurrent) — léger désalignement hérité de la sonde ; le contrôle grille utilise la même
   sonde et sort G_FIDELE, donc le NEUTRE stoneage est un contraste valide à méthode constante.
3. **n=44** transitions non-triviales (5 seeds, 24 agents) — powered mais modeste ; un run plus large
   confirmerait le NEUTRE. (Un petit run 16 agents donnait n=6 et un faux signal « latent statique »
   non répliqué à 24 agents : 44/44 transitions non-triviales → H_rec bouge bien.)
4. **Numérotation** : EDR-135 sur `feat/d1` (max 134) ; sessions // ont leur propre 132/133 non mergés
   → collision de numéros possible ([[parallel-sessions-shared-tree]]).
