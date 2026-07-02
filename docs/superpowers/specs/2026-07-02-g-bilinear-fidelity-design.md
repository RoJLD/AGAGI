# EDR 193 — Un g BILINÉAIRE (état-dépendant) est-il G_FIDÈLE là où le g linéaire d'EDR 135 était NEUTRE ? (design)

> **Date** : 2026-07-02. **Fil** : G4 / anticipation (extension d'EDR 135). **Bloc de numérotation** : 193 (bloc
> 190+, distant du débordement des fils // à ~161). **Statut** : design approuvé (brainstorming), à implémenter en
> subagent-driven.

## 1. Contexte et question

EDR 135 (« anticipation dé-pausée ») a mesuré la **fidélité de g** — la capacité de `g(H, a)` à prédire la transition
latente `H → H'` mieux que la baseline « pas de changement ». Le `g` du modèle (`planner_G` / `G_batch`) est
**LINÉAIRE** : un delta constant **par action**, `ΔH = g_delta[a]`, **indépendant de H courant**. Verdict d'EDR 135
sur obs riches (env-grille causal) : **NEUTRE** (ratio ~1.0) — le g linéaire n'anticipe pas.

EDR 135 conclut explicitement que **le dernier levier non testé du fil G4 est un `g` BILINÉAIRE** : rendre le delta
**état-dépendant**, `ΔH = W_a · H` (une matrice par action, multipliée par H courant). Question falsifiable :

> **Un g bilinéaire (`ΔH = W_a · H`) prédit-il les transitions latentes réelles mieux que la baseline ET mieux que le
> g linéaire, sur les mêmes trajectoires obs-riches où le linéaire était NEUTRE ?**

Le modèle n'apprenant qu'un g linéaire, on ne peut PAS lire un g bilinéaire du modèle : on le **fitte OFFLINE** sur les
vraies transitions latentes (trajectoire FIXE), et on compare les fidélités à la même métrique ratio.

## 2. Substrat de trajectoires — env-grille (déterministe, isolé)

Rollout grille 1-D (longueur L=7, obs = one-hot(pos) ++ one-hot(danger), moves {gauche, rester, droite}), **miroir de
`collect_ratios_env` d'EDR 135** : action → pos' → obs' est couplé (obs riche causal), round-robin des 3 actions, `g`
appris en ligne (`PLAN_BIAS=0.5`, `PLAN_A=3`, `PLAN_LR=0.1`, restaurés en `finally`). **Pas de Biosphere, pas de HoF,
pas de KuzuDB** → auto-contenu, reproductible (`np.random.seed(seed)` + numpy pur). C'est le régime où EDR 135
mesurait le g linéaire NEUTRE → comparaison directe.

## 3. Collecte des triplets

Pour chaque tick `t ≥ warmup` où une transition existe, capturer un triplet :
- `H_prev` = `H_rec` au tick t-1 (latent pré-rêve, `m.H_rec_batch[0, map_idx]`), forme `(N,)`, `N = num_nodes = 172`.
- `move` = action jouée au tick t-1.
- `H_next` = `H_rec` au tick t.
- `g_learned` = `m.G_batch[0][:, map_idx][move]` au tick t (le g LINÉAIRE appris par le modèle — mesure exacte
  d'EDR 135, sert de référence).

`ΔH_true = H_next − H_prev`. Cible de prédiction = `ΔH_true` (comme `transition_error(H_prev, ΔH_pred, H_next)`).

## 4. Prédicteurs comparés (offline, PAR SEED)

Chaque seed = réseau distinct = espace latent distinct → **fit PAR SEED, aucun pooling inter-seed**. Split **temporel
70/30 par action** (les premiers 70 % des triplets d'une action = train, les 30 % suivants = test) → mesure la
généralisation temporelle, pas la mémorisation.

Sur le **test set**, pour chaque triplet, ratio = `pred_err / base_err` (filtré `base_err > 1e-4`, seuil env-one-hot
d'EDR 135) :
- **baseline** : `ΔH_pred = 0` → `base_err`.
- **linéaire-appris** (référence EDR 135) : `ΔH_pred = g_learned`.
- **linéaire-offline** (contrôle) : `ΔH_pred = c_a` où `c_a` = moyenne des `ΔH_true` du TRAIN pour l'action a
  (delta constant par action, ré-estimé offline).
- **bilinéaire** (la question) : `ΔH_pred = W_a · H_prev`, `W_a (N×N)` fitté par **ridge** sur le train de l'action a :
  `W_a = ΔY^T X (X^T X + λ I)^{-1}`, où `X` = matrice des `H_prev` train (lignes), `ΔY` = matrice des `ΔH_true` train,
  `λ = 1.0` (gelé). Résolution via `np.linalg.solve` (déterministe).

Justification du bas-rang : le connectome a ~5 cachés EFFECTIFS (audit) → la carte de transition latente est
effectivement bas-rang → `W_a` est fittable depuis ~200 triplets/action avec ridge, malgré N=172.

## 5. Verdict pré-enregistré (gelé), agrégé sur K seeds

Réutilise `fidelity_verdict` (EDR 135) : `G_FIDELE` si `median(ratio) < 0.95` ET majorité favorable ; `G_INUTILE` si
`median > 1.05` ; sinon `NEUTRE`.

Verdict combiné (sur les ratios test-set poolés des K seeds) :
- **BILINEAR_FIDELE** si `fidelity_verdict(ratios_bilin)` = `G_FIDELE` **ET** `median(ratios_bilin) <
  median(ratios_learned)` (le bilinéaire bat la référence linéaire-apprise) → **la FORME état-dépendante est le levier**
  là où le linéaire était NEUTRE.
- **BILINEAR_NEUTRAL** si `fidelity_verdict(ratios_bilin)` ∈ {`NEUTRE`, `G_INUTILE`} → le bilinéaire n'aide pas non
  plus → **la forme de g n'est PAS le verrou** (confirme le soupçon d'EDR 135 : le linéaire accumulait mais restait
  neutre).
- **PARTIAL** sinon (bilinéaire fidèle mais ne bat pas le linéaire-appris).

## 6. Interprétation (les issues)

- **BILINEAR_FIDELE** : découverte positive — le fil G4 avait un levier (la forme de g). Actionnable : embarquer un g
  bilinéaire dans le planificateur. (Le moins probable au vu du soupçon d'EDR 135.)
- **BILINEAR_NEUTRAL** : **clôt le fil G4 « forme de g »** — ni linéaire (135) ni bilinéaire n'anticipent les
  transitions latentes réelles → le verrou de l'anticipation n'est PAS la forme du modèle de transition, mais ailleurs
  (latent trop pauvre / non prédictible / crédit). Cohérent avec l'arc substrat (le verrou = crédit/substrat).
- **PARTIAL** : le bilinéaire fitte quelque chose mais ne dépasse pas le linéaire-appris → forme insuffisante.

## 7. Caveats (à graver)

- **(a) Fit offline ≠ appris en ligne** : le bilinéaire est fitté par ridge sur les triplets, pas appris par le
  modèle. On teste si la FORME (état-dépendante) PEUT prédire, pas si le modèle SAURAIT l'apprendre en ligne. Un
  BILINEAR_FIDELE serait une borne HAUTE optimiste (oracle de fit).
- **(b) Sous-détermination** : `W_a` (172×172) fitté depuis ~200 triplets → fortement régularisé (λ=1.0). Le test-set
  tranche l'overfit ; λ non swept (gelé). Si bas-rang réel (~5 cachés), suffisant.
- **(c)** Split temporel : suppose quasi-stationnarité après warmup ; round-robin garantit chaque action échantillonnée
  régulièrement. **(d)** Substrat env-grille seul (obs riche causal) ; stoneage/synthétique non inclus (isolation).
  Hérite des caveats d'EDR 135 (mesure de fidélité latente, pas de survie).

## 8. Périmètre / tooling additif

- **Nouveau fichier** : `tools/g_bilinear_probe.py`. Réutilise par **import** de `tools.g_fidelity_probe` :
  `MambaAgent, MambaBatchModel, transition_error, fidelity_verdict, _obs_bench, _GRID_L, _N_MOVES, _OBS_DIM,
  _T_WARN_PERIOD`. `numpy as np`.
- **Nouveau test** : `tests/sandbox/test_g_bilinear_probe.py` (unit verdict + unit fit ridge sur données jouet +
  smoke du rollout+fit à petite échelle).
- **NE modifie NI** `tools/g_fidelity_probe.py` (mergé EDR-135) **NI** `src/` (import read-only de `mamba_agent`),
  ni le substrat torch (`torch_batch_model.py`/`backend_torch.py`/`substrate_*` — fil //).
- **Prints exécutés = ASCII-only** (cp1252) ; accents seulement en docstrings.
- **Déterminisme** : rollout `np.random.seed(seed)` + ridge `np.linalg.solve` (numpy pur, pas de torch) ; run en
  **2 passes byte-identiques**. Flags `PLAN_*` restaurés en `finally`.

## 9. Interfaces produites

- `_collect_transitions_env(seed, warmup, measure) -> list[dict]` (triplets `{H_prev, move, H_next, g_learned}`).
- `_fit_bilinear(train_triples, n_moves, N, lam) -> dict[move -> W_a]` (ridge par action).
- `_fit_linear_offline(train_triples, n_moves, N) -> dict[move -> c_a]` (delta moyen par action).
- `_split_temporal(triples, n_moves, frac=0.7) -> (train, test)`.
- `_ratios_for_predictor(test, predictor_fn, base_thresh=1e-4) -> list[float]`.
- `_verdict_bilinear(ratios_bilin, ratios_learned) -> str` (`BILINEAR_FIDELE`/`BILINEAR_NEUTRAL`/`PARTIAL`, gelé §5).
- `main_bilinear_check(seeds=(0..7), warmup=300, measure=600, lam=1.0, _return=False) -> dict|None`
  (`{verdict, median_bilin, median_learned, median_linoff, per_ratios...}`).

## 10. Numérotation

**EDR 193** — bloc **190+** (distant du débordement des fils //). Extension isolée d'EDR 135 (G4/anticipation).
