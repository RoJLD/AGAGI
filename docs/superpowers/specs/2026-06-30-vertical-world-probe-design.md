# Probe verticalité — `tools/vertical_world_probe.py`

> Probe science backend. Teste si activer `use_3d=True` dans `Biosphere3D` produit un
> signal exploitable : un champion évolué en 2D exploite-t-il spontanément l'affordance
> verticale, ou l'ignore-t-il ? Détecteur de POSITIF bon marché avant tout investissement
> de visualisation 3D (three.js).

## Motivation

La question amont : « three.js serait-il utile ? ». Réponse : seulement si la verticalité
devient une variable scientifique. Avant d'habiller la 3D, on vérifie qu'elle porte du signal.
Le moteur supporte déjà le 3D fonctionnellement (mouvement Up/Down actions 4-5 gardé par
`use_3d`, obs `dup/ddown/abs_z`, geometry cube `(dim_z,size,size)`), mais **aucune science EDR
ne l'utilise**. Ce probe est le premier pas — le moins cher, sans front, sans three.js.

## Hypothèse

Un champion compétent (évolué en 2D, chargé du Hall of Fame) transplanté dans le monde 3D :
- **H1 (Z_UTILISÉ)** : navigue Z spontanément (moves Up/Down au-dessus du plancher de hasard,
  z-range > 0 sur sa vie) → la verticalité est immédiatement exploitable → signal positif.
- **H0 (Z_INERTE)** : reste collé à z=0 (Up/Down ≈ plancher, z-range ≈ 0) → pas de signal.

## Bras (2, appariés, K seeds)

| Bras | `use_3d` | `dim_z` |
|---|---|---|
| A — 2D | `False` | 1 |
| B — 3D | `True` | `size` (cube) |

Même génome, même cohorte fixe de clones, même config par ailleurs. **Zéro changement
d'architecture** : l'obs et l'espace d'action ont la même dimension dans les deux bras
(les slots `dup/ddown/abs_z` et les actions 4-5 existent toujours ; seule leur informativité
change). Le génome 2D est dimensionnellement compatible avec le monde 3D.

## Métriques

**Primaire (décision), mesurée DANS le bras 3D** — le delta 2D/3D est trivial pour Z (z≡0 en 2D) :
- `z_range_3d` = moyenne sur agents de (z_max − z_min) sur la vie.
- `updown_frac_3d` = fraction d'actions Up/Down (4,5) parmi les steps des survivants
  (âge ≥ médiane). Plancher de hasard = 2/8 = 0.25 (repère, pas un test dur).

**Secondaires (interprétatives, NON décisionnelles)** :
- survie médiane par bras (médiane de médianes par ère), `survival_ratio = med_3d / med_2d`.
- `big_kills` (proxy apex/coop) et compteur de craft si exposés — reportés bruts.

Le monde 3D étant un cube plus creux, la survie chute probablement par dilution — d'où le
choix de la Z-utilisation (et non la survie) comme métrique de décision.

## Fonction de décision (PURE, cœur testable)

```
classify_vertical_signal(z_range_3d, updown_frac_3d, updown_floor=0.25, margin=1.2,
                         z_eps=0.5, survival_2d=None, survival_3d=None) -> dict
  z_used   = z_range_3d > z_eps
  updown_used = updown_frac_3d > updown_floor * margin
  verdict = "Z_UTILISE" si (z_used AND updown_used) sinon "Z_INERTE"
  survival_ratio = survival_3d / max(survival_2d, 1e-6)  (si fournis, interprétatif)
  -> { verdict, z_range_3d, updown_frac_3d, threshold=updown_floor*margin, survival_ratio }
```

`z_eps`, `margin`, `updown_floor` sont des paramètres explicites (pas des nombres magiques
cachés) ; défauts justifiés (plancher = 2 actions verticales / 8 ; marge 1.2 = 20 % au-dessus
du hasard ; z_eps 0.5 = au moins une transition de couche).

## Instrumentation (depuis la boucle du tool, ZÉRO modif `src/`)

`agent["last_action"]` est posé chaque step ; `agent["z"]` est à jour. Après chaque `w.step()`,
balayer `w.agents` (+ agents nouvellement morts) et accumuler par `agent["id"]` :
`{ z_min, z_max, ups (last_action==4), downs (last_action==5), steps }`. En fin de run, agréger.

## Mécaniques (calque de `tools/famine_harshness_probe.py`)

- `measure_arm(genome, use_3d, seed, n_eras, n_agents, max_ticks) -> dict` :
  pour chaque ère `seed_at(seed, era)` ; `cfg = WorldConfig(); cfg.use_3d = use_3d` ;
  `w = Biosphere3D(cfg)` ; `w.benchmark_mode = True` (cohorte fixe, sinon survie sature au cap) ;
  si `hasattr(w, "memory_retriever")` → `w.memory_retriever.stop(); .clear()`
  (**hazard mémoire ambiante = non-repro**) ; cohorte de `n_agents` clones `from_genome` ;
  boucle `while w.agents and t < max_ticks` avec instrumentation ; agréger survie + Z-usage.
- Single-process (évite les hazards ProcessPool/KuzuDB).
- K=5 seeds (Commandement 15 : R≥4), `n_eras=2`, `n_agents=12`, `max_ticks=600` — env-configurables
  (`VWP_SEEDS`, `VWP_ERAS`, `VWP_AGENTS`, `VWP_TICKS`), défauts calqués sur le probe famine.
- `main()` : agrège les 2 bras sur K seeds, appelle `classify_vertical_signal`, print table +
  `VWP_JSON {...}`.

## Source du génome

- Le HoF est **gitignored** (`data/*.pkl`) — jamais versionné. Le probe le lit via `HOF_PATH`
  (env, mirroring famine probe ; défaut `data/hall_of_fame.pkl` = HoF stoneage par défaut).
- Pour l'exécution réelle : `HOF_PATH` pointé sur le HoF stoneage existant du tree principal
  (`/c/Users/robla/VScode_Project/AGAGI/data/hall_of_fame.pkl`) — **lecture seule d'un artefact**,
  aucune touche à la branche `feat/d1-prod-pairing`.
- Si le HoF est vide/absent : le probe échoue proprement avec un message clair (précondition,
  comme le probe famine).

## Où ça vit / branche (frontière session parallèle) ⚠️

- **Fichiers neufs uniquement** : `tools/vertical_world_probe.py` + `tests/test_vertical_world_probe.py`.
  **Aucune modification de `src/`** (le probe lit `Biosphere3D`, pose `cfg.use_3d`).
- Worktree dédié `AGAGI-probe`, branche `probe/vertical-world`, **base `main` (PAS `feat/d1-prod-pairing`)**.
  PR vers `main`. La session backend d1 n'est jamais touchée.
- Commits path-scoped, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Pas de numéro EDR maintenant** (collisions inter-sessions) : on construit l'INSTRUMENT ;
  le record EDR (avec numéro) s'écrira après l'exécution, en coordination.

## Caveats (gravés — honnêteté scientifique)

1. **Positif fort, négatif faible.** Le probe transplante un champion évolué en 2D. Un POSITIF
   (navigue Z) est fort. Un NÉGATIF (ignore Z) est ambigu : Z pourrait exiger une évolution *en*
   3D pour être exploité (non testé ici, plus cher). Ce probe est un détecteur de positif, pas
   une réfutation.
2. **Sparsité du cube.** `use_3d` fixe `dim_z=size` (cube `size³`, très creux). Un « Z_INERTE »
   pourrait refléter un monde mal-calibré plutôt qu'une verticalité inutile. Le probe teste la
   3D **telle qu'implémentée**.

## Tests

- `tests/test_vertical_world_probe.py` : tests unitaires de `classify_vertical_signal` (PURE) —
  cas Z_UTILISE, Z_INERTE (z-range nul), Z_INERTE (updown sous seuil), survival_ratio calculé,
  bornes (survival_2d=0 → pas de division par zéro).
- Smoke d'intégration : `measure_arm` sur un monde minuscule (`max_ticks=20, n_agents=3, 1 era,
  use_3d=True`) prouve que l'instrumentation Z tourne sans erreur (pas un test de signal).

## Hors-scope (YAGNI)

- Bras de contrôle Z-inerte (3 bras) — suivi si le 2-bras est ambigu.
- Évolution *en* 3D (arme lourde) — seulement si négatif ET indépendamment motivé.
- Toute plomberie de flux / front / three.js — ne se pose qu'après un positif.
- Modification du monde (dim_z réglable, gravité, ressources verticales) — étude ultérieure.

## Contraintes globales

- Backend, Python. Aucune modification de `src/` (fichiers neufs uniquement).
- Single-process (pas de multiprocess).
- Fonction de décision PURE et testée ; nombres seuils explicites/paramétrés.
- Reproductibilité : `seed_at`, `benchmark_mode`, `memory_retriever.stop()`.
- Branche `probe/vertical-world` (depuis `main`), PR vers `main`.
