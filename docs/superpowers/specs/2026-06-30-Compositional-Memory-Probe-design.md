# Design — Sonde mémoire compositionnelle (suite EDR 119, Issue C → H1)

Date : 2026-06-30

## Question scientifique

EDR 119 a tranché : grossir la couche cachée ×16 ne lève pas la composition means→ends (Issue C — la
TAILLE n'est pas le verrou). Le verrou est le **mécanisme** : crédit compositionnel / mémoire
récurrente. Ce chantier attaque la PREMIÈRE des trois hypothèses emboîtées :

1. **Mémoire** — la récurrence ne *porte* pas `did_x` jusqu'à l'état qui produit `move2` (info absente
   → aucune règle ne peut l'utiliser).
2. **Crédit** — l'info est portée, mais la règle n'assigne pas le crédit de la récompense S2 vers
   l'action S1.
3. **Découverte** — la règle pourrait lier, mais la récompense jointe trop rare ne donne jamais de
   signal d'amorçage.

Cette sonde tranche H1 (mémoire), prérequis logique : si l'info n'est pas portée, le curriculum
(H2/H3) serait futile. Question opérationnelle : **`did_x` est-il décodable linéairement de l'état
récurrent `H_S2` qui produit `move2` ?**

## Hypothèse — 3 issues

Lues sur l'**AUC d'un décodeur linéaire `did_x ~ état`**, comparée à un contrôle au hasard :

- **MEMORY_PRESENT** (AUC_S2 ≫ 0.5 sur les deux backends, delta vs contrôle franc) → la récurrence
  porte `did_x` → le verrou est EN AVAL (crédit/découverte) → prochain chantier = curriculum.
- **MEMORY_ABSENT** (AUC_S2 ≈ 0.5 / delta ≈ 0) → la récurrence *lave* `did_x` en un pas → le verrou
  est la MÉMOIRE → besoin d'un mécanisme explicite (la récurrence LTC mono-pas ne préserve pas le
  précondition discret).
- **ASYMÉTRIQUE** (un backend porte, l'autre non) → les substrats diffèrent en capacité mémoire →
  informe quel moteur cibler.

## Architecture — `tools/substrate_ab_compositional.py::memory_probe` (notre banc, commit `fbec167`+ extensions EDR 119)

### Mesure pure, sans apprentissage (capacité intrinsèque à l'init, W aléatoire)

Par trial, sur une population fraîche (réutilise `_build_agents` / `make_population`) :

1. Lire l'état AVANT S1 : `H_pre = _read_state(pop, backend)`.
2. `forward(obs_a_t)` → `move1 = argmax(preds[:, :_MOVE])` → `did_x = (move1 == target_x)`.
3. `forward(obs_b)` → (move2 non utilisé) → lire `H_S2 = _read_state(pop, backend)`.
4. Enregistrer `(H_pre[:, I:], H_S2[:, I:], did_x)` par agent.

- **`obs_a` VARIÉ par trial** (RNG seedé) → fait varier `did_x` indépendamment de l'identité de
  l'agent (dissout le confond « `did_x` = constante de l'agent ») ET donne un contrôle au hasard propre.
- **`obs_b` FIXE** → comme la tâche (S2 n'encode pas `did_x` ; seule la récurrence peut le porter).
- **Pas de `pop.learn`** → on mesure la capacité architecturale à l'init, pas l'apprentissage.
- Décodage sur la tranche **non-input** `H[:, I:]` (nœuds cachés + sortie ; les `I` premiers nœuds ne
  portent que l'obs injectée, constante/non informative).

### Lecture d'état backend-agnostique (lecture seule, zéro modif des fichiers //)

`_read_state(pop, backend) -> np.ndarray (B, N)` :
- `legacy` : `pop._model.H_prev_batch.copy()` (mis à jour par `forward`, vérifié (B,172)).
- `torch` : `pop.H.detach().cpu().numpy()` (mis à jour par `forward`, vérifié (B,172)).

### Décodeur PAR AGENT (fidèle au readout per-agent du substrat)

Pour chaque agent (ses `trials` échantillons) :
- Régression logistique `sklearn.linear_model.LogisticRegression` (avec `StandardScaler`), `did_x ~
  H_S2[:, I:]`, **split train/test intra-trials** (ex. `train_test_split` stratifié 70/30 ou
  `cross_val_score` AUC). Métrique = **ROC-AUC** (sans seuil, robuste au déséquilibre ~1/8).
- Inclus seulement si les DEUX classes de `did_x` sont présentes avec ≥ `MIN_PER_CLASS` (ex. 8)
  échantillons par classe → sinon agent exclu. **Le nombre d'agents qualifiants est REPORTÉ** (pas de
  drop silencieux).
- Idem pour le contrôle `H_pre[:, I:]`.

Agrégation : médiane des AUC par agent qualifiant, par backend, par seed. A/B `legacy` vs `torch`,
≥3 seeds, `n_agents=16`, `trials=300`.

### Fonctions

- `_read_state(pop, backend) -> np.ndarray`
- `_decode_auc(X, y, *, min_per_class, seed) -> float | None` (None si classes insuffisantes ; pur,
  testable sur signal synthétique).
- `memory_probe(seeds=(0,1,2), n_agents=16, trials=300, num_nodes=172, target_x=0) -> dict` :
  `{cells: [{backend, seed, n_qualifying, base_rate, median_auc_s2, median_auc_pre, median_delta,
  per_agent: [...]}], verdict}`.
- `main_memory_probe()` (ou extension de `main` derrière un env flag) : knobs `SABC_MP_SEEDS`/
  `SABC_MP_AGENTS`/`SABC_MP_TRIALS`, imprime la table AUC_S2/AUC_pre/delta par backend + verdict, dump
  JSON optionnel `SABC_MP_OUT`.

## Garde-fous anti-théâtre

1. **Contrôle au hasard = le héros** : le MÊME décodeur sur `H_pre` (état AVANT d'avoir vu `obs_a_t`,
   ne peut pas contenir le `did_x` de ce trial) doit donner **AUC ≈ 0.5**. Le **delta AUC_S2 −
   AUC_pre** isole la mémoire S1→S2 réelle du confond identité-agent/historique. Si AUC_pre est haut,
   le décodage exploite l'identité, pas la mémoire → verdict suspendu.
2. **`obs_a` varié** : sans ça, `did_x` serait quasi-constant par agent et l'identité décoderait
   trivialement.
3. **Décodage per-agent** (pas cross-agent) : fidèle au readout réel du substrat (chaque agent a son
   propre W) ; un décodage cross-agent sous-estimerait si l'encodage est agent-spécifique.
4. **Déterminisme** : `np.random.seed` + `torch.manual_seed` ; RNG du décodeur seedé.
5. **Jamais de scalaire nu** : AUC par agent conservé, médianes + base_rate + n_qualifying par cellule.
6. Détection de succès **par EXIT CODE** (pas de grep sur log redirigé).

## Tests

- **Pur — `_decode_auc`** : sur un signal SYNTHÉTIQUE linéairement séparable (`X` corrélé à `y`) →
  AUC ≈ 1 ; sur du bruit pur (`X` aléatoire indépendant de `y`) → AUC ≈ 0.5. Valide la mécanique de
  décodage sans backend. Renvoie `None` si une classe manque.
- **Pur — `_read_state` forme** : `legacy` renvoie (B, N) ; `torch` idem (skip propre si torch absent
  via `importorskip`).
- **Smoke `slow`** (`importorskip("torch")`) : `memory_probe(seeds=(0,), n_agents=8, trials=60)`
  renvoie `cells` non vide avec les clés attendues, `median_auc_pre` ≈ 0.5 (contrôle sain, tolérance
  large ex. [0.3, 0.7]), `verdict` ∈ {MEMORY_PRESENT, MEMORY_ABSENT, ASYMÉTRIQUE}.
- **Non-régression** : la suite existante de `test_substrate_ab_compositional.py` reste verte (ajouts
  seulement).

## Hors périmètre (YAGNI)

- Pas de sonde post-apprentissage (la capacité à l'init suffit pour trancher H1).
- Pas de curriculum (chantier suivant si MEMORY_PRESENT).
- Pas de mécanisme mémoire explicite (chantier suivant si MEMORY_ABSENT).
- Pas de modif de `backend.py` / `backend_torch.py` / `substrate_ab.py`.
- Pas de sweep taille (clos par EDR 119) ; `num_nodes=172` par défaut.

## Suite (selon issue)

- **MEMORY_PRESENT** : curriculum progressif (récompenser `did_x` seul puis Y|X) — tranche
  crédit (H2) vs découverte (H3).
- **MEMORY_ABSENT** : mécanisme mémoire explicite (mémoire adressable type NTM entraînée, ou
  traces d'éligibilité préservant le précondition) sur le banc.
- **ASYMÉTRIQUE** : cibler le backend qui porte la mémoire pour le substrat de prod.

## Livrable & contraintes

- EDR cible = **120** (vérifier libre — tree partagé, collisions possibles).
- Commits **path-scoped** (sessions parallèles sur `feat/d1-prod-pairing`).
- **Pas de PR-off-main** (même dépendance backend qu'EDR 117/119 : le banc importe
  `backend.py`/`substrate_ab.py` absents d'`origin/main`).

## Variables d'expérience

`backend` (legacy/torch), `seed`, `n_agents`, `trials`, état décodé (`H_S2` vs `H_pre` contrôle).
Tâche X-gate-Y inchangée (`obs_a` varié pour le probe, `obs_b` fixe). `num_nodes=172`.
