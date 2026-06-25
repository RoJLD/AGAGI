# EDR 105 — Décomposition de l'entonnoir de forage (versant ACQUISITION)

## Contexte et motivation

Le thread énergie-**dépense** est clos (EDR 090→101). EDR 101 a tranché : réduire
`base_metabolism` aide ×5 mais **sature à 27 ticks ≪ gate 120**, *même à métabolisme nul*. Un
**second mur — l'ACQUISITION (forage)** — limite la survie : partant de E=80, à `N_APEX=0` (monde
vidé d'apex, zéro combat) avec un drain résiduel de ~1-2/tick, les champions s'épuisent en ~27
ticks. Ils **n'exploitent pas les 15 proies régulières** pour rester à flot.

EDR 105 est le **premier pas sur le versant acquisition** — l'analogue de l'EDR 099 (décomposition
du drain), mais pour le **revenu** au lieu de la dépense. On **localise** où l'acquisition casse
**avant** d'intervenir (même discipline que 099→100→101 côté dépense).

Lignée : 090→093→094→098→099→100→101→**105**. (102/103/104 = lignée parallèle « champion =
monoculture », sans rapport.)

## Mécanique de forage (établie par lecture de `world_1_stoneage.py`)

Un agent capture une proie régulière en **se tenant sur sa cellule exacte** (`agent["x"]==p["x"]
and agent["y"]==p["y"]`, l.685) : l'attaque est alors **automatique** (pas de garde d'action), 10
dégâts à mains nues. Les proies régulières (Lapin/Cerf/Sanglier, hp<50) tuées ajoutent
`prey_reward(hp) × forage_payoff` à l'énergie (l.744, plafonnée à `energy_max`) et incrémentent
`agent["preys_eaten"]`. Un scaffold d'approche annelé récompense la réduction de distance vers la
proie la plus proche (l.649-653), via `agent["last_prey_dist"]`.

**Le forage est donc un entonnoir séquentiel à 3 étages**, chacun conditionnant mécaniquement le
suivant (sans co-localisation, zéro contact possible ; sans contact, zéro capture ; sans capture,
zéro revenu).

## Variable d'expérience (Commandement 15 : 1 variable)

**Variable balayée : `base_metabolism ∈ {0.0, 0.25}`.** Tout le reste gelé : `N_APEX=0`,
`forage_payoff=3` (sweet-spot 085), `PREY_COUNT=15`, `NUM_AGENTS=24`, mêmes seeds appariés entre
niveaux.

- **metab=0** porte le **verdict** : acquisition isolée (le drain métabolique est annulé, EDR 101),
  seul subsiste un drain résiduel ~1-2/tick. L'entonnoir y est mesuré **sans le confond de la
  dépense**.
- **metab=0.25** est rapporté **en parallèle** (même table) mais **ne porte pas le verdict** : il
  confirme que l'entonnoir y est *vide* (mort au tick ~5 *avant* de forager, `p_reach≈0`) — preuve
  que le drain masquait l'acquisition.

## Les 3 étages et leur instrumentation

| Étage | Question | Métrique (par agent, sur sa vie) |
|---|---|---|
| **1. APPROCHE** | L'agent atteint-il une proie ? | `min_dist` = distance Manhattan minimale jamais atteinte vers la proie la plus proche |
| **2. CAPTURE** | Le contact se convertit-il en kill ? | `contacts` = ticks co-localisé (attaques portées) ; `captures` = `preys_eaten` |
| **3. REVENU** | Le kill couvre-t-il le drain ? | `income`/tick = énergie foragée ÷ âge, vs `drain` résiduel/tick |

**Flag opt-in `trace_forage`** (calqué exactement sur `trace_energy_sinks` : défaut `False`,
**byte-identique** quand off — protège les sessions parallèles). Quand `True`, trois hooks ASCII-only
dans `world_1_stoneage.py` posent sur l'agent :

- `agent["_forage_min_dist"]` — mis à jour au calcul de distance (l.~653) : `min(prev, d)`.
- `agent["_forage_contacts"]` — incrémenté à chaque attaque co-localisée (l.~685).
- `agent["_forage_income"]` — sommé au revenu régulier (l.~744 ; **uniquement** la branche proie
  régulière, pas l'apex/leurre).

Les captures se lisent dans `agent["preys_eaten"]` (déjà existant).

### Le drain résiduel/tick : mesure INDÉPENDANTE du revenu (anti-circularité)

Le `drain_t` de l'étage REVENU **ne doit pas** être dérivé du bilan énergétique de l'agent. Sur une
vie finissant en famine, `Δénergie = revenu − drain = final − 80 ≈ −80`, donc `drain = revenu + 80`
*par construction* : comparer revenu-vie et drain-vie serait **tautologique** (le drain gagne
toujours de 80). La vraie question REVENU est un **taux de soutenabilité** : le revenu de forage/tick
couvre-t-il le **coût structurel forage-indépendant**/tick ?

Ce coût structurel est mesuré **indépendamment** en **co-activant l'instrumentation
`trace_energy_sinks` existante** (EDR 099/100, déjà inerte et testée) et en sommant les *buckets de
pure dépense* — `bio_metab + bio_terrain + bio_carry + brain + action + mouvement` (à metab=0,
`bio_metab=0`) — dont le revenu de forage est **exclu par construction** (le revenu vit dans
`bio_autres`, jamais sommé ici). Donc :

```
drain_t  = mediane( -(bio_metab+bio_terrain+bio_carry+brain+action+mouvement) / age )   # >0
income_t = mediane( _forage_income / age )                                              # >=0
```

Co-activer `trace_energy_sinks` ne viole **pas** le Commandement 15 : la variable balayée reste
`base_metabolism` seule ; `trace_energy_sinks` et `trace_forage` sont des **instruments inertes**, pas
des variables. La comparaison `income_t < drain_t` devient ainsi genuinement falsifiable.

### Pourquoi un hook dédié plutôt que `_e_bio["autres"]`

La phase « autres » (l.771) mélange déjà approche + forage + jump/heal. Réutiliser ce bucket
confondrait le revenu de capture avec la prime de scaffold d'approche. Un hook dédié au point de
revenu régulier (l.744) isole **l'énergie réellement extraite des proies** — la seule grandeur qui
répond à « foragent-ils assez ? ».

## Verdict pré-enregistré (gelé avant données)

Cascade « premier étage cassé », évaluée sur la population à **metab=0** :

```
reached  = (min_dist <= 0)        # a réellement atteint une cellule-proie
captured = (preys_eaten >= 1)     # a tué au moins une proie
p_reach  = fraction d'agents avec reached
p_cap    = fraction des "reached" qui ont captured
income_t = médiane(income/tick) ;  drain_t = médiane(drain résiduel/tick)
```

| Condition (évaluée dans l'ordre) | Verdict | Lecture |
|---|---|---|
| `p_reach < 0.5` | **GOULOT=APPROCHE** | la majorité n'atteint jamais une proie (navigation) |
| sinon si `p_cap < 0.5` | **GOULOT=CAPTURE** | atteignent mais ne convertissent pas (10 dmg, quittent la cellule) |
| sinon si `income_t < drain_t` | **GOULOT=REVENU** | capturent mais le revenu ne couvre pas le drain résiduel |
| sinon | **FORAGE SUFFISANT** | l'entonnoir tient → le mur des 27 ticks est ailleurs |

**Falsifiable dans les deux sens.** Une branche `FORAGE SUFFISANT` qui sort alors que les agents
meurent à 27 ticks serait elle-même un résultat fort (le revenu couvre le drain mais un autre
mécanisme tue : distribution spatiale, épuisement des 15 proies). Le seuil 0.5 et `min_dist<=0`
strict (« réellement sur la cellule ») sont gelés ici.

## Architecture logicielle

Trois unités, frontières nettes :

1. **`world_1_stoneage.py`** — les 3 hooks `trace_forage` (inertes quand off). Une responsabilité :
   exposer les compteurs d'entonnoir.
2. **`tools/lewis_survival_sweep.py`** — `_cfg` gagne un param `trace_forage=False` (rétro-compatible).
   `main_forage` construit son `cfg` avec **les deux instruments co-activés** (`trace_forage=True`,
   `trace_energy_sinks=True`) — l'un pour le revenu, l'autre pour le coût structurel.
   `_measure_forage(cfg, seeds, n_apex=0, ...)` (calquée sur `_measure_drain` : lit les compteurs
   `_forage_*` + `preys_eaten` + les buckets `_e_phases`/`_e_bio` + âge sur le pool, agrège par
   agent) ; `_verdict_forage(agg)` (la cascade ci-dessus) ; `_report_forage(h, aggs, ...)` (table
   ASCII + verdict sur metab=0 + provenance) ; `main_forage(metab_levels=(0.0, 0.25), n_eval=8, R=4,
   seed=None, _return=False)`.
3. **Tests** — `tests/test_edr105_forage_funnel.py`.

`_measure_forage` renvoie par niveau : `{p_reach, p_cap, income_t, drain_t, mean_captures,
mean_contacts, mean_min_dist, n_agents}`.

## Paramètres de run

`N_APEX=0`, `forage_payoff=3`, `PREY_COUNT=15`, `NUM_AGENTS=24`. **`max_ticks=150`** d'emblée : le
run gelé EDR 101 a montré qu'à metab=0 les agents vivent + se reproduisent → population au cap → ères
très lentes. L'entonnoir se mesure sur la durée de vie réelle (~27 ticks ≪ 150 → aucune censure). Si
même 150 est trop lent au run gelé (`R=4, n_eval=8`), repli sur run réduit (`R=1, n_eval=3`)
documenté **surdéterminé** (précédent EDR 101). Provenance : `results/lewis_forage_funnel_105.json`.

Reproductibilité : `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ;
`memory_retriever.stop()+clear()` ; mêmes seeds entre niveaux (appariement).

## Testing (TDD)

1. **Inertie** : `trace_forage=False` → aucune clé `_forage_*` posée sur l'agent ; un `env.step()`
   est inchangé (byte-identique au comportement actuel).
2. **Verdict** : `_verdict_forage` sur tables synthétiques → les **4 branches** (GOULOT=APPROCHE /
   CAPTURE / REVENU / FORAGE SUFFISANT), aux frontières des seuils.
3. **Mesure** : mini-run `_measure_forage` à 2 seeds, `trace_forage=True` → clés présentes,
   `p_reach ∈ [0,1]`, `p_cap ∈ [0,1]`, `income_t ≥ 0`, `n_agents > 0`.

## Ce que l'EDR ne fait PAS (YAGNI)

- Pas d'intervention (pas de sweep de levier forage) — localiser d'abord.
- Pas de nouveau flag pour le drain : **réutilise l'instrument `trace_energy_sinks` existant** (EDR
  099/100) pour le coût structurel — pas de bilan énergétique circulaire.
- Pas de distinction par espèce de proie (Lapin/Cerf/Sanglier agrégés) — le grain « espèce » est un
  EDR ultérieur si le goulot est CAPTURE ou REVENU.

## Lignée et provenance

Outils : `tools/lewis_survival_sweep.py` (`main_forage`, `_measure_forage`, `_verdict_forage`,
`_report_forage`, param `_cfg(trace_forage=…)`), `src/seed_ai/exp_stats.py`. Provenance :
`results/lewis_forage_funnel_105.json`. Lignée : 090→093→094→098→099→100→101→**105**.
