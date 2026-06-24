# EDR 098 — Le mur intrinsèque de Lewis est-il le `brain_cost` amplifié par la surprise ? Sweep de `ttc_surprise_scale`

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-24.
**Lignée :** 090 (létalité, NÉGATIF PROFOND) → 093 (revenu réfuté) → 094 (densité d'apex réfutée → **MUR INTRINSÈQUE**) → **098** (le mur intrinsèque = brain_cost surprise-amplifié ?).
**Numéro :** 095/096/097 réservés/à-risque par la session parallèle « dreaming » → ce travail = **098** (clair du bloc).

## 1. Motivation

EDR 094 a établi que la survie en Lewis est **indépendante de l'environnement** : à `N_APEX=0` (monde vidé
d'apex, zéro kill, zéro combat), les champions meurent quand même de FAMINE au tick 5. Le mur est **intrinsèque**.
L'exploration du code (post-094) localise le mécanisme et **réfute la prémisse initiale** (heal-spam) :

> Le drain ~13-16/tick à `N_APEX=0` ne vient **pas** du soin : l'action 6 est gardée par `hp < 100`
> (`world_1_stoneage.py:665`) → sans combat, hp reste 100, le soin ne se déclenche jamais. Le poste de drain
> intrinsèque qui s'applique **chaque tick** est le **`brain_cost`** (`:972`) :
> `brain_cost = ttc_base_cost × (1 + log2(1 + compute_spent)) × night_mult × surprise_scale`, où
> `surprise_scale = 1 + surprise_val × ttc_surprise_scale`. Un `RuntimeWarning: overflow encountered in cast`
> sur `surprise` (`mamba_agent.py:422`) apparaît à **chaque** run : si `surprise_momentum` explose,
> `surprise_scale` explose, `brain_cost` explose → famine en 5 ticks, indépendamment du monde.

EDR 098 teste **cette** hypothèse, et lui seule : le mur intrinsèque est-il le `brain_cost` amplifié par la
surprise ? On balaye `ttc_surprise_scale` (déjà un champ config — **zéro modif du code de production**), à
`N_APEX=0` (isole le drain intrinsèque de tout apex).

**Place dans la séquence (programme en 3 EDR, une variable chacun) :** 098 = sweep `ttc_surprise_scale`,
**instrumenté** (log `surprise_momentum`). Son verdict route le suivant : 099 = soit *fixer l'overflow*
(clamp `surprise_momentum`, écho EDR 086), soit *décomposer le drain complet* (si la surprise est innocentée).

## 2. La prétention (1 variable — Commandement 15)

> Sur Lewis à `N_APEX=0` (vrai monde vide, correctif 094), il **existe** une valeur de `ttc_surprise_scale` où
> les champions survivent (survie médiane > 120 ticks). On mesure *si* et *où*.

**Variable manipulée :** `ttc_surprise_scale` ∈ `(1.0, 0.5, 0.25, 0.0)`. `1.0` = baseline (reproduit le MUR
INTRINSÈQUE de 094 à `N_APEX=0`) ; `0.0` = `brain_cost` **découplé** de la surprise (`surprise_scale = 1`).

**Tout le reste fixe :** `N_APEX = 0` (monde vide), `forage_payoff = 3`, `base_metabolism = 0.25`,
`leurre_frac = 0`, `PREY_COUNT = 15`, `max_ticks = 300`, `num_agents = 24`, champions HoF répliqués, pas
d'évolution, pas de langage.

**Pourquoi ce knob.** À `scale = 0`, le `brain_cost` ne dépend plus de la surprise. Si la survie remonte → le
`brain_cost` surprise-amplifié **EST** le mur intrinsèque. C'est un champ config (comme `forage_payoff`/`N_APEX`),
donc **aucune modification du fichier partagé `world_1_stoneage.py`** — pattern propre 093/094.

## 3. Métriques & règle de verdict (gelées)

- **Métrique primaire :** survie médiane (ticks) par niveau de `ttc_surprise_scale`, R×n_eval ères seedées,
  appariées par seed entre niveaux.
- **Tendance :** Jonckheere-Terpstra one-sided — la survie **croît**-elle quand `ttc_surprise_scale` **décroît** ?
  (groupes en ordre de scale décroissant `1.0→0.0` = ordre naturel des niveaux).
- **Instrumentation (la décomposition du sink, intégrée), par niveau :** `surprise_momentum` lu sur
  `agent["model"]` du pool — **moyenne des |valeurs finies|**, **max fini**, et **fraction non-finie**
  (`inf`/`nan` ; détecte l'overflow). Plus famine/combat/kills comme 093/094.

| Condition | Verdict | → EDR 099 |
|---|---|---|
| survie médiane > 120 à un `ttc_surprise_scale < 1` | **TARIF = SURPRISE×BRAIN_COST** — découpler la surprise débloque la survie ; le mur intrinsèque est le coût de calcul surprise-amplifié. | clamper/réparer la surprise (approche 3, écho 086). |
| survie ≤ 120 partout **+ surprise non-finie** (overflow détecté) | **OVERFLOW = RACINE** — `surprise_momentum` explose (`inf`/`nan`) ; `scale=0` donne `1+inf×0=nan` → ne découple pas proprement. La racine est l'instabilité numérique. | fixer l'overflow (clamp `surprise_momentum`, écho 086 NaN). |
| survie ≤ 120 partout **+ surprise finie** | **PAS LE BRAIN_COST** — découpler la surprise n'aide pas et la surprise est saine ; le drain est ailleurs. | décomposer le drain complet (approche 2 ; suspect = throw `:1122`). |

Les trois branches sont informatives : succès = mur localisé au brain_cost ; chaque échec route le diagnostic
suivant (overflow numérique, ou autre sink).

## 4. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `levels` (`ttc_surprise_scale`) | `(1.0, 0.5, 0.25, 0.0)` | 1.0 = baseline 094 ; 0.0 = découplé |
| `N_APEX` | 0 | monde vide (isole le drain intrinsèque) |
| `forage_payoff` | 3 | 085 (fixe) |
| `base_metabolism` | 0.25 | sweet-spot 085 (fixe) |
| `leurre_frac` | 0 | létalité 0 |
| `PREY_COUNT` | 15 | forage régulier |
| `max_ticks` | 300 | gate >120 valide |
| `num_agents` | 24 | comme 093/094 |
| `n_eval` | 8 | ères par (niveau, répétition) |
| `R` | 4 | répétitions appariées |
| gate de survie | 120 ticks | seuil de barreau survivable |

## 5. Outillage & architecture

- **Extension DRY de `tools/lewis_survival_sweep.py`** (mergé via #31/#33 ; plus aucun propriétaire parallèle) :
  - `_cfg(forage_payoff, ttc_surprise_scale=None)` : pose `cfg.ttc_surprise_scale = float(...)` quand fourni
    (sinon défaut config 1.0) — **rétro-compatible** (les appels 093/094 sans l'argument inchangés).
  - `_measure_survival(..., collect_surprise=False)` : quand `True`, lit `agent["model"].surprise_momentum`
    sur le pool et ajoute une clé `"surprise"` (par ère : `{mean_abs_finite, max_finite, frac_nonfinite}`).
    **Rétro-compatible** : défaut `False` → dict retourné **identique** à 093/094 (les tests qui assertent
    `set(...) == {"ticks","famine","combat","kills"}` restent verts). Lecture read-only → zéro modif prod.
  - `_verdict_surprise(levels, medians, frac_nonfinite_par_niveau, gate=GATE)` → 3 branches §3.
  - `main_surprise(levels=SURPRISE_LEVELS, n_eval=8, R=4, seed=None, _return=False)` : balaye
    `ttc_surprise_scale` à `N_APEX=0` et `forage_payoff=3` fixes → `_measure_survival(_cfg(3, scale), seeds,
    n_apex=0, collect_surprise=True)`. Mêmes seeds entre niveaux (appariement).
  - `_report` réutilisé (déjà paramétré `knob`/`verdict_fn`) ; ajout d'une **colonne surprise** quand les
    groupes portent la clé `"surprise"` (impression conditionnelle, rétro-compatible).
  - `SURPRISE_LEVELS = (1.0, 0.5, 0.25, 0.0)`.
- **Briques réutilisées (inchangées) :** `_setup_critical` (`n_apex=0` → correctif monde vide 094),
  `_disable_kuzu`, `_load_champions`, `_reproduce`, `Harness`, `seed_at`, `st.jonckheere_terpstra`.
- **Reproductibilité :** `_disable_kuzu()` + `Harness(with_db=False)` ; `memory_retriever.stop()`+`clear()` ;
  `seed_at(s,0)` par ère ; mêmes seeds entre niveaux.
- **Garde non-fini :** le verdict lit `frac_nonfinite` ; à `scale=0` avec surprise `inf`, `brain_cost` peut
  devenir `nan` → l'âge/energie peut être non-fini ; le harnais classe ces morts hors famine/combat mais les
  compte dans `n`, et la branche OVERFLOW est déclenchée par `frac_nonfinite > 0`.

## 6. Tests (TDD)

- `_cfg` : `_cfg(3, ttc_surprise_scale=0.0)` pose `cfg.ttc_surprise_scale == 0.0` ; `_cfg(3)` laisse le défaut.
- `_measure_survival(collect_surprise=True)` : ajoute la clé `"surprise"` (longueur = nb ères, chaque entrée a
  `mean_abs_finite/max_finite/frac_nonfinite`) ; `collect_surprise=False` (défaut) → dict **identique** à 093/094.
  Reproductible (seedé).
- `_verdict_surprise` (pur) : 3 branches exactes (TARIF si un scale<1 franchit / OVERFLOW si aucun franchit +
  une fraction non-finie >0 / PAS LE BRAIN_COST si aucun franchit + surprises finies).
- `main_surprise` : forme de sortie (table par niveau de scale, verdict ∈ 3 valeurs, `jt` présent), reproductible.
- **Non-régression :** les 7 tests existants (093+094) restent verts (défaut `collect_surprise=False`, `_cfg`
  rétro-compatible).

## 7. Plan d'exécution

1. Étendre + tester (sub-agent-driven, TDD).
2. **Run direct** : smoke réduit, puis `main_surprise(seed=<S>)` aux params gelés → table survie ×
   `ttc_surprise_scale` + diagnostic surprise, verdict.
3. Écrire l'EDR 098 selon la branche (TARIF / OVERFLOW / PAS LE BRAIN_COST) et amorcer l'EDR 099 correspondant.

## 8. Garde-fous

- `_disable_kuzu()` avant toute création de monde.
- `seed_at` appariement strict entre niveaux ; mêmes seeds réutilisés à chaque scale.
- `N_APEX=0` → correctif `_setup_critical` (monde vraiment vide) déjà validé EDR 094.
- Lecture `surprise_momentum` read-only (pas de modif du monde/agent) ; garde `np.isfinite`.
- Worktree `worktree-edr098-surprise-sweep` sur `main` (inclut #31/#33) ; commits path-scopés.

## 9. Provenance attendue

`results/lewis_surprise_sweep_<seed>.json` : `levels (ttc_surprise_scale), R, n_eval, table (survies + causes +
kills + surprise par niveau), medians, jt, verdict`. Outils : `tools/lewis_survival_sweep.py` (étendu),
`src/seed_ai/exp_stats.py`. Lignée : 090→093→094→**098**.
