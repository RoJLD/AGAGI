# EDR 011 : World Model — Tête Prédictive (RND) & Réparation de la Surprise

## Contexte

Levier 1 de l'audit (EDR 010), première moitié de la **Vague 0**. Le scan a établi que le cerveau *ne prédit pas* : pas de modèle du monde → le "dreaming" ne rêve rien, la surprise n'est pas une vraie erreur de prédiction, la value head n'est jamais un critic.

Pire, deux découvertes du code l'imposaient :
- **`predictor_head` était une tête fantôme** : le réseau émet 8 logits de "prédiction" (`mamba_agent.py:510-514`) que **rien ne compare jamais** à une cible.
- **La surprise était morte en production** : dans `MambaBatchModel.forward`, `H` était copié de `H_prev_batch` puis la surprise calculée comme `mean((H − H_prev_batch)²)` = **0 à chaque tick**. Conséquence en cascade : `surprise_momentum` restait à 0, donc le **déclencheur du dreaming** (`momentum > 0.05`) ne se déclenchait **jamais**, et la récompense intrinsèque du monde (qui lit `a.surprise`) était inerte.

## Décision (V18.0)

Brancher un **World Model façon RND** (Random Network Distillation) : un modèle de transition linéaire qui prédit une projection *aléatoire fixe* de l'observation suivante. L'erreur de prédiction devient la **vraie surprise**, qui alimente gratuitement la curiosité intrinsèque (axe 4.1) et réveille le dreaming.

```
pred(t)   = obs(t)   @ Wp        # Wp APPRIS en ligne (SGD/EQM)
target(t) = obs(t+1) @ P         # P : projection aléatoire FIXE (non apprise)
surprise  = mean((pred − target)²)   # par agent, clampée [0,1]
```

**Pourquoi P fixe** : c'est ce qui interdit l'effondrement trivial. Un agent ne peut pas rendre sa cible facile — il ne peut que mieux *modéliser* la dynamique. La surprise chute donc sur le familier (appris) et reste haute sur le nouveau.

### Choix d'architecture

| Choix | Décision | Raison |
|---|---|---|
| Cible | Projection aléatoire de `obs(t+1)` (8D) | Ancrée dans le vrai monde, aucun choix arbitraire, capte l'info distribuée |
| Apprentissage | SGD en ligne sur l'EQM (`Wp -= lr·objᵀ·diff/B`) | Cohérent avec le substrat NumPy, pas de backprop inventé |
| Portée | **Partagé** par la population (1 `Wp`), erreur **par agent** | Premier socle simple et batchable ; per-agent = raffinement futur |
| Possession | Le **monde** possède le `WorldModel` | Persiste sur toute l'ère (le batch est recréé à chaque step) |
| Persistance `last_obs` | **Par agent** (round-trip comme `surprise_momentum`) | Le batch étant éphémère, l'état transite par les agents |

### Fichiers

- `src/agents/world_model.py` — la classe `WorldModel` (P, Wp, `observe`).
- `src/agents/mamba_agent.py` — câblage dans `MambaBatchModel` (param `world_model`, buffers `last_obs_batch`/`has_last_batch`, remplacement du calcul de surprise mort, write-back `a.last_obs`).
- `src/worlds/world_1_stoneage.py` — `self.world_model = WorldModel(config.agent.num_inputs)` passé au batch.
- `tests/sandbox/test_world_model.py` — 8 tests (déterminisme, apprentissage, surprise familier vs nouveau).

## Conséquences (vérifiées)

Micro-run E2E (6 ticks, prod) :

| Métrique | Avant | Après |
|---|---|---|
| `a.surprise` | `0.0` (bug) | `[0.17, 0.19, 0.05]` — non nulle |
| `surprise_momentum` | `0.0` → dreaming jamais | `[0.42, 0.42, 0.21]` → **> seuil 0.05** |
| `‖Wp‖` | `0.0` | `0.63` — **le modèle a appris** |

Dynamique de curiosité correcte : surprise saturée à `1.0` aux premiers ticks (Wp=0, tout est nouveau), puis décroissante à mesure que le modèle apprend. 29 tests verts au total, aucune régression.

**Un seul branchement répare trois choses** : surprise réelle, déclencheur de dreaming, récompense intrinsèque du monde — sans toucher au monde (la récompense lit déjà `a.surprise`).

## Limites & questions ouvertes

- **Partagé & linéaire** : un seul `Wp` par population, modèle linéaire. Un World Model **par agent** (chaque cerveau modélise) et **non-linéaire** (lecture du latent `H`) sont les raffinements suivants.
- **Récompense de curiosité gated** : le chemin intrinsèque du monde est conditionné par `active_exp_variable` — à activer/mesurer explicitement (Step 2).
- **`pred_logits` (l'ancienne tête fantôme)** est désormais redondant → candidat au nettoyage Vague 1.
- **Transmission** : un World Model par agent pourrait être hérité à la mitose (transmission lamarckienne du savoir du monde) — à explorer.
