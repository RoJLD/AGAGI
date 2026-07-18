# EDR 106 — Décomposition de l'APPROCHE : le mur est-il CINÉMATIQUE ou POLITIQUE ?

## Contexte et motivation

EDR 105 a localisé le mur d'acquisition à l'**APPROCHE** (`GOULOT=APPROCHE`) : à `N_APEX=0`/`metab=0`,
seuls **18%** des agents atteignent un jour une cellule-proie (`p_reach=0.18`), mais quand ils y
arrivent ils capturent à **100%** (`p_cap=1.00`). Le `min_dist` moyen plafonne à **1.24** : les agents
s'approchent à ~1 case mais ne franchissent pas la **dernière case**.

L'exploration du code (`world_1_stoneage.py:_move_preys`, `config.py:preys`) révèle un mécanisme
candidat précis — la **cinématique des proies** :

| Proie (régulière, présente à N_APEX=0) | hp | comportement vs agent | `moves_per_tick` |
|---|---|---|---|
| Lapin | 1.0 | **FUIT** | **2** (2× l'agent) |
| Cerf | 3.0 | **FUIT** | 1 (= l'agent) |
| Sanglier | 5.0 | **APPROCHE** (+ riposte 10) | 0.5 |

L'agent se déplace à **1 case/tick**. Donc le **Lapin fuit deux fois plus vite** que l'agent
(kinématiquement increatchable par poursuite naïve) et le **Cerf fuit à vitesse égale** (increatchable
sauf cornering). Seul le **Sanglier vient à l'agent**. Le plateau `min_dist=1.24` s'explique :
**l'agent colle une proie qui court plus vite que lui.**

EDR 106 décompose l'APPROCHE pour trancher : le mur est-il **CINÉMATIQUE** (les proies fuient trop
vite) ou **POLITIQUE** (l'agent ne navigue pas vers les proies, même immobiles) ?

Lignée : 090→093→094→098→099→100→101→105→**106**.

## Variable d'expérience (Commandement 15 : 1 variable)

**Variable balayée : `prey_speed_scale ∈ {1.0, 0.5, 0.25, 0.0}`** — un multiplicateur global de la
vitesse de toutes les proies. À `0.0`, les proies sont **figées** (ne fuient plus). Tout le reste gelé :
`N_APEX=0`, `metab=0`, `forage_payoff=3`, `PREY_COUNT=15`, `NUM_AGENTS=24`.

Métrique : **`p_reach`** (fraction d'agents atteignant une cellule-proie), lue via l'entonnoir
`trace_forage` existant (EDR 105 — réemploi DRY).

## Verdict pré-enregistré (gelé avant données)

**Le verdict est porté par le niveau FIGÉ (`scale=0.0`)** — il retire entièrement le confond
cinématique, ne laissant que la navigation pure :

| Condition | Verdict | Lecture |
|---|---|---|
| `p_reach(figé) ≥ 0.5` | **KINEMATIQUE** | proies immobiles → les agents les atteignent → le mur ÉTAIT la fuite (vitesse relative) |
| `p_reach(figé) < 0.5` | **POLITIQUE** | proies immobiles non atteintes → le mur est la navigation/répertoire, pas la cinématique |

Les niveaux intermédiaires (0.5, 0.25) donnent la **dose-réponse** : le déblocage est-il gradué avec la
vitesse ? Testé par Jonckheere-Terpstra (tendance de `p_reach` quand la vitesse baisse).

**Falsifiable dans les deux sens.** Un `POLITIQUE` (figer ne suffit pas) serait un résultat fort : la
navigation elle-même est le mur, indépendamment de la cinématique → pivot vers le répertoire/scaffold.

### Pourquoi figer plutôt que comparer les vitesses

À `scale=1.0` on ne distingue pas « ne sait pas naviguer » de « ne peut pas rattraper ». En **annulant**
la vitesse des proies, on supprime mécaniquement l'hypothèse cinématique. Même logique d'isolation que
`base_metabolism=0` en EDR 101 (annuler le terme pour voir s'il était *le* mur).

## Enrichissement par espèce (secondaire, descriptif — NE porte PAS le verdict)

À chaque niveau de vitesse, la table rapporte les captures **par espèce** (Lapin/Cerf/Sanglier). Un
compteur `agent["_forage_species"]` est posé dans le hook revenu de `trace_forage` (même garde opt-in,
même point de code que `_forage_income`). Prédiction falsifiable : à `scale=1.0` les captures sont
quasi toutes du **Sanglier** (seul qui approche) ; en figeant, **Lapin/Cerf** (les fuyards) se
débloquent. Ce contraste *montre* le mécanisme cinématique espèce par espèce.

## Architecture logicielle (réemploi maximal d'EDR 105)

1. **`src/environments/config.py`** — champ `prey_speed_scale: float = 1.0`.
2. **`src/worlds/world_1_stoneage.py`** :
   - `_move_preys` : `moves_per_tick = (cfg.moves_per_tick if cfg else 0) * prey_speed_scale` ; la
     fuite-au-feu est gatée par `prey_speed_scale > 0` (désactivée seulement quand figé). **Invariant
     RNG** : à `scale=1.0`, la valeur de `moves_per_tick` est inchangée → même `int`, même tirage
     `np.random.rand()` (consommé dans le même ordre) → trajectoire **byte-identique**. Le
     multiplicateur ne doit PAS changer la consommation du RNG à `scale=1.0`.
   - Hook par espèce dans la branche kill régulière (`trace_forage`, à côté de `_forage_income`) :
     `agent["_forage_species"][type] += 1`.
3. **`tools/lewis_survival_sweep.py`** :
   - `_cfg` gagne `prey_speed_scale=1.0` (rétro-compatible).
   - `_measure_forage` lit `agent.get("_forage_species", {})` et ajoute au dict retourné les clés
     `cap_lapin`, `cap_cerf`, `cap_sanglier` (moyennes par agent ; **additif**, ne casse pas EDR 105).
   - `_verdict_approach(aggs)` : `aggs` = liste `(scale, agg)` ; sélectionne `scale==0.0`, renvoie
     `"KINEMATIQUE"` si `p_reach ≥ 0.5` sinon `"POLITIQUE"`.
   - `_report_approach(h, aggs, R, n_eval, _return)` : table ASCII (1 ligne/vitesse : p_reach, p_cap,
     captures totales + par espèce) + JT + verdict (sur le figé) + provenance.
   - `main_approach(speed_levels=(1.0, 0.5, 0.25, 0.0), n_eval=8, R=4, seed=None, _return=False)` :
     co-active `trace_forage=True` et `trace_energy_sinks=True` ; sweep `prey_speed_scale`.
4. **Tests** — `tests/sandbox/test_edr106_approach_kinematics.py`.

## Paramètres de run

`N_APEX=0`, `metab=0` (`base_metabolism=0.0`), `forage_payoff=3`, `PREY_COUNT=15`, `NUM_AGENTS=24`,
**`max_ticks=150`**. Comme EDR 101/105, le run gelé (`R=4, n_eval=8`) est impraticablement lent à
`metab=0` (et pire à `scale=0` : agents bien nourris survivent plus longtemps) → **run réduit fidèle
d'emblée** (`R=1, n_eval=3`), surdéterminé (`p_reach` estimé sur ~1000+ agents ; seuil 0.5 loin).
Provenance : `results/lewis_approach_kinematics_106.json`.

Reproductibilité : `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ;
`memory_retriever.stop()+clear()` ; mêmes seeds appariés entre niveaux.

## Testing (TDD)

1. **Inertie / invariant RNG** : `prey_speed_scale=1.0` (défaut) → après `env.step()` à graine fixe, les
   proies occupent **exactement** les mêmes positions qu'avec `scale` absent (byte-identique). C'est la
   garantie de non-régression pour les sessions parallèles.
2. **Figeage** : `prey_speed_scale=0.0` → après plusieurs `step()`, **aucune proie n'a bougé** (positions
   initiales conservées).
3. **Compteur espèce** : `trace_forage=True` + un kill régulier → `agent["_forage_species"]` porte la
   bonne espèce ; absent quand `trace_forage=False` (inertie).
4. **Verdict** : `_verdict_approach` sur aggs synthétiques → les 2 branches (KINEMATIQUE si
   `p_reach(figé) ≥ 0.5`, POLITIQUE sinon), aux frontières du seuil.
5. **Mesure** : mini-run `_measure_forage` avec `prey_speed_scale=0.0` → clés `cap_lapin/cap_cerf/
   cap_sanglier` présentes, `p_reach ∈ [0,1]`.

## Ce que l'EDR ne fait PAS (YAGNI)

- Pas d'intervention sur la vitesse de l'AGENT (l'autre face de la vitesse relative) — c'est un EDR
  suivant *si* le verdict est KINEMATIQUE ; le faire ici = 2 variables.
- Pas de scaffold d'approche modifié — localiser (kinématique vs politique) d'abord.
- Pas de cornering/obstacles explicites — hors scope.

## Lignée et provenance

Outils : `tools/lewis_survival_sweep.py` (`main_approach`, `_verdict_approach`, `_report_approach`,
param `_cfg(prey_speed_scale=…)`), hook `prey_speed_scale` + compteur espèce dans
`src/worlds/world_1_stoneage.py`, `src/seed_ai/exp_stats.py`. Provenance :
`results/lewis_approach_kinematics_106.json`. Lignée : 090→…→101→105→**106**.
