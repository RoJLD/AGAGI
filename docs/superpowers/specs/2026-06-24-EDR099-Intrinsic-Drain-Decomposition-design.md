# EDR 099 — Décomposer le drain intrinsèque de Lewis : quel poste porte les ~13-16/tick ?

**Statut :** pré-enregistrement (gelé avant données).
**Date :** 2026-06-24.
**Lignée :** 090 (létalité) → 093 (revenu) → 094 (densité apex → MUR INTRINSÈQUE) → 098 (brain_cost/surprise) → **099**.
Quatre leviers réfutés ; le drain de ~13-16/tick au tick 5 reste **non identifié**. 099 cesse de deviner et le
**mesure**.
**Numéro :** 099 (095 = dreaming session ; 096-098 libres/098 pris par ce travail ; 099 vérifié libre).

## 1. Motivation

EDR 094 a montré que la survie en Lewis est indépendante de l'environnement (MUR INTRINSÈQUE : famine au tick 5
même à `N_APEX=0`). EDR 098 a réfuté le `brain_cost` surprise-amplifié (surprise clampée [0,1] → `brain_cost`
×2 max d'un `ttc_base_cost=0.01`, deux ordres sous le drain). **Leçon 098 : deviner le poste (heal, brain_cost)
mène à des faux.** Le drain réel de ~13-16/tick reste non nommé.

EDR 099 **décompose** le bilan énergétique par tick à `N_APEX=0` (monde vide), pour **nommer** le poste dominant
plutôt que continuer à sweeper à l'aveugle. À `N_APEX=0` : combat=0 (pas d'apex), heal gardé off (`hp<100` faux,
hp reste 100). Les postes restants se regroupent en **3 phases** dans `world_1_stoneage.py:step()` :

- **brain** : `brain_cost` (loop 1, l.978) — 098 le dit petit ;
- **action** : `throw` (−10/−5, l.1128) + signal + divers (loop 2, avant `_resolve_biology`) ;
- **biologie** : `_resolve_biology` (l.1255) = métabolisme + terrain + carry (+ heal/hunt, ≈0 ici) ;
- **mouvement** : pénalité de **move bloqué** (`−2.0`, l.1288, `elif action < 6`) — l'agent vise un mur. Poste
  distinct (friction de locomotion), **après** `_resolve_biology` dans la boucle 2.

**Amendement (avant données) :** la première version de cette spec ne traçait que `[e0 … après _resolve_biology]`
et ratait la pénalité de mouvement bloqué (l.1288), ~moitié du drain (révélé par la revue finale du code, **pas**
par les données — aucun run gelé n'a eu lieu). On étend le span à la fin de l'itération (après le mouvement) et
on ajoute la phase **mouvement** : l'instrument couvre désormais **tout** le drain par tick. Corriger un défaut
d'instrument détecté par lecture de code, avant toute donnée officielle, est méthodologiquement propre.

## 2. La prétention (mesure, pas de variable manipulée)

> À `N_APEX=0` (Lewis vide), le drain énergétique de ~13-16/tick (qui tue par famine au tick 5) est porté
> **majoritairement par une phase identifiable** du step. On mesure la décomposition par phase et on nomme le
> poste dominant.

Pas de variable manipulée (Commandement 15 trivialement satisfait) : c'est une **observation instrumentée** de
la condition gelée Lewis-vide (091..098). Tout fixe (`N_APEX=0`, `forage_payoff=3`, `base_metabolism=0.25`,
`leurre_frac=0`, `PREY_COUNT=15`, `num_agents=24`, `max_ticks=300`), champions répliqués, pas d'évolution/langage.

## 3. Métriques & règle de verdict (gelées)

- **Métrique primaire :** énergie moyenne drainée **par tick et par agent**, décomposée en **4 phases**
  (`brain`, `action`, `biologie`, `mouvement`), agrégée sur les ticks de vie × agents × R×n_eval ères.
- **Décomposition (les 4 deltas somment au drain net par construction — télescopage) :**
  - `brain = e0 − e_brain` (avant/après `brain_cost`, l.973/978) ;
  - `action = e_brain − e_prebio` (fin loop 1 → avant `_resolve_biology`) = throw + signal + divers ;
  - `biologie = e_prebio − e_postbio` (avant/après `_resolve_biology`, l.1255) = métab + terrain + carry ;
  - `mouvement = e_postbio − e_fin` (après `_resolve_biology` → après le move bloqué, l.1288) = friction murs.
- **Sous-produit :** part (%) de chaque phase dans le drain total. `net = brain+action+biologie+mouvement`
  couvre désormais **tout** le drain par tick (vérifier au run : `net` ≈ ~13-16/tick).

| Condition | Verdict |
|---|---|
| phase **action** porte > 50% du drain | **TARIF=THROW** — coût de lancer ; EDR 100 : paramétrer/baisser le coût throw. |
| phase **biologie** porte > 50% | **TARIF=BIOLOGIE** — métab/terrain/carry ; rééquilibrer le métabolisme de Lewis. |
| phase **mouvement** porte > 50% | **TARIF=MOUVEMENT** — friction de move bloqué (murs) ; le mur est la **géométrie/locomotion** ; EDR 100 : géométrie moins confinée ou pénalité de blocage plus douce. |
| phase **brain** porte > 50% | **TARIF=BRAIN** — contredit 098 (flag) ; ré-investiguer `brain_cost`/compute. |
| aucune phase > 50% | **DRAIN DIFFUS** — drain réparti ; lever exige plusieurs ajustements. |

Le seuil **50%** est gelé : « majoritaire » = une phase porte plus que toutes les autres réunies. Chaque
branche route l'action suivante.

## 4. Paramètres pré-enregistrés (gelés)

| Paramètre | Valeur | Note |
|---|---|---|
| `N_APEX` | 0 | monde vide (isole le drain intrinsèque) |
| `forage_payoff` | 3 | 085 (fixe) |
| `base_metabolism` | 0.25 | sweet-spot 085 (fixe) |
| `leurre_frac` | 0 | létalité 0 |
| `PREY_COUNT` | 15 | forage régulier |
| `max_ticks` | 300 | (les agents meurent ~tick 5 ; borne large) |
| `num_agents` | 24 | comme 093/094/098 |
| `n_eval` | 8 | ères par répétition |
| `R` | 4 | répétitions appariées |
| seuil de phase dominante | 50% | gelé |
| `trace_energy_sinks` | `True` (mesure) | défaut `False` partout ailleurs |

## 5. Outillage & architecture

- **Code de production (changement opt-in minimal, défaut OFF → zéro changement de comportement) :**
  - `src/environments/config.py` : `WorldConfig.trace_energy_sinks: bool = False` (1 champ).
  - `src/worlds/world_1_stoneage.py` : **5 captures** gardées par `if getattr(self.config, "trace_energy_sinks", False):` :
    - l.973 (entrée loop 1) : `agent["_e0"]` ;
    - après l.978 (après `brain_cost`) : `agent["_e_brain"]` ;
    - avant l.1255 (`_resolve_biology`) : `agent["_e_prebio"]` ;
    - après l.1255 (`_resolve_biology`) : `agent["_e_postbio"]` (capture seule) ;
    - après le move bloqué (l.1288, fin de l'itération de la boucle 2, **avant** le bloc survie/reproduce qui
      reset l'énergie à 50) : `e_fin = agent["energy"]` et **enregistrer** `agent["_e_phases"]` cumulatif
      `{brain, action, biologie, mouvement}` (les 4 deltas).
  - **Inertie garantie :** sans `trace_energy_sinks=True`, ces lignes ne s'exécutent pas → survie/repro
    inchangées (non-régression testée).
- **Harnais — extension DRY de `tools/lewis_survival_sweep.py`** (mergé) :
  - `_cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False)` : pose le flag quand fourni.
  - `_measure_drain(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS)` : lance les ères avec
    `trace_energy_sinks=True`, lit `agent["_e_phases"]` du pool, agrège l'énergie/tick par phase (normalisée
    par l'âge de l'agent). Renvoie `{"brain", "action", "biologie", "mouvement", "net", "n_agents"}` (moy./tick).
  - `_verdict_drain(phases) -> str` (pur) : **5 branches** §3 selon la part > 50%.
  - `_report_drain(h, agg, R, n_eval, _return)` : table des **4 phases** (valeur/tick + %), verdict, provenance.
  - `main_decompose(n_eval=8, R=4, seed=None, _return=False)`.
- **Réutilisé inchangé :** `_setup_critical` (`n_apex=0` → correctif monde vide 094), `_disable_kuzu`,
  `_load_champions`, `_reproduce`, `Harness`, `seed_at`.
- **Reproductibilité :** `_disable_kuzu()` + `Harness(with_db=False)` ; `memory_retriever.stop()`+`clear()` ;
  `seed_at` par ère.

## 6. Tests (TDD)

- `WorldConfig.trace_energy_sinks` défaut `False` ; `_cfg(3, trace_energy_sinks=True)` le pose.
- **Inertie (non-régression) :** une ère avec `trace=False` ne pose pas `_e_phases` et donne la **même** survie
  qu'avant (les 11 tests 093/094/098 restent verts).
- **Traçage :** avec `trace=True`, les agents du pool portent `_e_phases` avec les 3 clés ; les 3 deltas somment
  au drain net (à epsilon près) ; valeurs ≥ 0.
- `_verdict_drain` (pur) : 4 branches exactes (action>50 / biologie>50 / brain>50 / diffus).
- `_measure_drain` : forme `{brain, action, biologie, net, n_agents}`, reproductible (seedé).
- `main_decompose` : forme de sortie (3 phases + verdict ∈ 4 valeurs), reproductible.

## 7. Plan d'exécution

1. Implémenter + tester (sub-agent-driven, TDD) : config flag → hooks world → harnais.
2. **Run direct** : smoke réduit, puis `main_decompose(seed=<S>)` → table des 3 phases + verdict.
3. Écrire l'EDR 099 selon la branche (TARIF=THROW / BIOLOGIE / BRAIN / DIFFUS) et amorcer l'EDR 100.

## 8. Garde-fous

- Hooks **strictement gardés** par `trace_energy_sinks` (défaut False) → inertes pour 087-098 et sessions
  parallèles ; non-régression testée.
- `N_APEX=0` → correctif `_setup_critical` (monde vide) déjà validé 094.
- `_disable_kuzu()` + `seed_at` ; lecture `_e_phases` post-ère read-only.
- Normalisation : énergie/tick = somme des deltas de phase / âge de l'agent (évite de biaiser vers les
  survivants longs).
- Worktree `worktree-edr099-drain-decompose` sur `main` ; commits path-scopés (2 fichiers prod partagés +
  harnais + tests — `git -C add` exact, jamais `git add -A`).

## 9. Provenance attendue

`results/lewis_drain_decompose_<seed>.json` : `phases (brain/action/biologie valeur+%), net, n_agents, R,
n_eval, verdict`. Outils : `tools/lewis_survival_sweep.py` (étendu), `src/worlds/world_1_stoneage.py` (hooks
opt-in), `src/environments/config.py` (flag). Lignée : 090→093→094→098→**099**.
