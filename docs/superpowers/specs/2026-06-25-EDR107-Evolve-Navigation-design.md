# EDR 107 — Ré-évoluer la NAVIGATION en Lewis : le substrat peut-il forger l'atteinte de proies ?

## Contexte et motivation

EDR 106 a tranché que le mur d'approche du forage est **POLITIQUE** (la politique de navigation évoluée
du champion), pas cinématique : figer entièrement les proies ne fait passer `p_reach` que de 0.16 à
0.21 (≪ 0.5). Pour des **réplicas** (pas d'évolution), cette politique est figée → le déficit vit dans
le **substrat évolué** : les champions forgés en *stoneage* ne naviguent pas vers les proies de Lewis.

EDR 107 est un **changement de registre** : on quitte les knobs de monde (mesure de réplicas) pour
**faire tourner l'évolution EN Lewis** et observer si la navigation (mesurée par `p_reach`) **émerge au
fil des générations**. La question : le substrat actuel, *sélectionné dans Lewis*, débloque-t-il la
navigation que les champions stoneage n'ont pas ?

Enjeu de fond : le bug `from_genome` (résolu, `preserve_dims=True` par défaut dans `main`) a rendu
l'évolution topologique ACTIVE (les réseaux grossissent). EDR 107 teste si CE substrat, sous sélection
Lewis, forge la navigation.

Lignée : 090→…→101→105→106→**107**.

## Le piège d'EDR 090, et comment EDR 107 l'évite

EDR 090 a évolué la **survie** en Lewis et a conclu « pas de premier barreau survivable » — paysage de
fitness trop plat. EDR 107 ne re-tread PAS 090 : il cible le métrique-goulot précis isolé par EDR 106,
**`p_reach`** (atteindre une cellule-proie), qui possède un gradient exploitable :

- `calculate_life_score = age*0.1 + preys_eaten*50 + ...` : le terme **`preys_eaten*50` domine** et exige
  exactement d'atteindre une proie → forte pression de sélection sur les « atteigneurs ».
- Le scaffold `approach_reward` donne de l'énergie pour la **réduction de distance** → prolonge la vie →
  `age` → `life_score` : gradient de navigation **dense** (pas binaire).

## Variable d'expérience (Commandement 15)

La « variable » est le **temps évolutif** (numéro de génération). Tout le reste est gelé : `N_APEX=0`,
`base_metabolism=0`, `forage_payoff=3`, `num_agents=24`, `max_ticks=80`, sélection sur
`calculate_life_score`, cliquet best-ever (top-5 global). Métrique observée : `p_reach` de la population
à chaque génération (instrument `trace_forage` d'EDR 105).

### Le scaffold reste chaud par construction

Chaque génération est lancée comme une **ère fraîche avec `current_era=1`** (pattern d'`evolve_competence`).
Donc `anneal(current_era=1, scaffold_eras)` est quasi-plein à **chaque** génération : le gradient de
navigation du scaffold reste chaud sans rien forcer. (L'annealing ne mord que dans une sim continue
multi-ères.) On donne ainsi à la navigation sa **meilleure chance** → un verdict SUBSTRAT BLOQUÉ serait
d'autant plus crédible (test conservateur).

### Pourquoi `base_metabolism=0`

La navigation a besoin de **temps de vie** pour s'exprimer : à `metab=0` les agents vivent ~27 ticks
(EDR 101), assez pour atteindre une proie. À `metab=0.25` ils meurent au tick 5 (trop court — le piège
d'EDR 090). La pression de sélection pour atteindre vient de `preys_eaten*50`, indépendante du métab.

## Verdict pré-enregistré (gelé avant données)

```
first = mediane(p_reach des 5 premieres generations)
last  = mediane(p_reach des 5 dernieres generations)
```

| Condition | Verdict | Lecture |
|---|---|---|
| `last >= first + 0.15` | **NAVIGATION EVOLUE** | la boucle de prod forge la navigation-Lewis → le substrat n'est PAS bloqué ; il fallait sélectionner EN Lewis |
| sinon | **SUBSTRAT BLOQUE** | même avec sélection Lewis + gradient dense + scaffold chaud, la navigation n'émerge pas → verrou plus profond (connectome, NAS) |

**Ancrage du seuil +0.15** : EDR 106 a montré que figer entièrement les proies (intervention forte) ne
déplaçait `p_reach` que de **+0.05**. Un seuil de **+0.15** = 3× cet effet → une hausse qui ne peut être
ni du bruit cinématique résiduel ni une fluctuation de population. Baseline ~0.18 → franchir ~0.33 =
navigation réellement améliorée. Une **tendance** (régression linéaire ou Jonckheere-Terpstra sur la
trajectoire) est rapportée en appui, mais le gate first-vs-last porte le verdict.

**Falsifiable dans les deux sens.** SUBSTRAT BLOQUÉ est un résultat fort (renvoie au connectome comme
verrou ultime) ; le design maximise les chances de NAVIGATION ÉVOLUE (scaffold chaud, sélection Lewis,
métab=0), donc un plat est informatif.

## Architecture logicielle (réemploi maximal)

Réemploi :
- `_reproduce(champions, num_agents, mc)` (cliquet élite + mutés) — d'`evolve_competence`.
- `_setup_critical(env, 0.0, n_apex=0)` (Lewis vidé d'apex) — de `lewis_critical`.
- `calculate_life_score` (fitness) — de `persistence`.
- L'instrument `trace_forage` (pose `agent["_forage_min_dist"]`) — d'EDR 105. Ici **seul `trace_forage`**
  suffit : `p_reach` = fraction du pool avec `_forage_min_dist <= 0`. Pas de `drain_t`, donc pas besoin de
  co-activer `trace_energy_sinks`.

Nouveau code dans `tools/lewis_survival_sweep.py` :
- `_p_reach_of_pool(pool)` : fraction des agents du pool avec `_forage_min_dist <= 0` (helper isolé,
  réutilisé par le smoke test).
- `_evolve_nav_gen(cfg, genomes, max_ticks)` : lance une ère en Lewis (`_setup_critical` n_apex=0,
  `trace_forage`, `memory_retriever.stop()`), renvoie `(scored, p_reach, stats)` où `scored` = liste des
  top-5 `(life_score, genome)` pour le cliquet, `p_reach` = `_p_reach_of_pool(pool)`, `stats` =
  `{"ticks", "eaten", "p_reach"}`.
- `main_evolve_nav(generations=20, num_agents=24, max_ticks=80, seed=None, _return=False)` : boucle
  cliquet (best-ever top-5), enregistre `p_reach[]` par génération, rapporte trajectoire + verdict.
- `_verdict_evolve_nav(traj)` : `"NAVIGATION EVOLUE"` si `median(traj[-5:]) >= median(traj[:5]) + 0.15`,
  sinon `"SUBSTRAT BLOQUE"` (avec garde : si `len(traj) < 10`, compare moitié haute vs basse).

## Paramètres de run

`generations=20`, `num_agents=24`, `max_ticks=80`, `N_APEX=0`, `base_metabolism=0`, `forage_payoff=3`,
`seed=107`. L'évolution est **lourde** ; comme 101/105/106, on prévoit le run **réduit d'emblée** et une
réduction supplémentaire (générations/pop) documentée si trop lent. `max_ticks=80` borne la croissance
de population (à metab=0) tout en laissant le temps d'atteindre une proie (qui se joue tôt). Provenance :
`results/lewis_evolve_nav_107.json`. Repro : `_disable_kuzu()`, `Harness(with_db=False)`, `seed_at` par
génération, `memory_retriever.stop()+clear()`.

## Testing (TDD)

1. **Verdict** : `_verdict_evolve_nav` sur trajectoires synthétiques → `"NAVIGATION EVOLUE"` (montée
   ≥ +0.15) vs `"SUBSTRAT BLOQUE"` (plat), aux frontières du seuil.
2. **p_reach correct** : `_p_reach_of_pool` sur un pool synthétique avec des `_forage_min_dist` connus
   (certains ≤ 0, d'autres > 0) → fraction exacte ; pool vide → 0.0.
3. **Smoke génération** : `_evolve_nav_gen` sur 1 génération en Lewis (petite pop, `max_ticks` court) →
   `p_reach ∈ [0,1]`, `scored` non vide (liste de tuples `(float, genome)`), `stats` finies.

## Ce que l'EDR ne fait PAS (YAGNI)

- Pas de fitness navigation custom (on sélectionne sur la fitness de PROD `calculate_life_score` — c'est
  le résultat qui compte ; une béquille synthétique ne dirait rien de la prod).
- Pas d'A/B multi-signaux (un run lourd, pas deux).
- Pas de modification du connectome / de l'archi (EDR 107 mesure si l'évolution *actuelle* débloque ; si
  BLOQUÉ, l'archi devient le sujet d'un EDR ultérieur côté NAS).
- Pas de langage / coopération (N_APEX=0, forage solo).

## Lignée et provenance

Outils : `tools/lewis_survival_sweep.py` (`main_evolve_nav`, `_evolve_nav_gen`, `_verdict_evolve_nav`,
`_p_reach_of_pool`), réemploi `evolve_competence._reproduce`, `lewis_critical._setup_critical`,
`persistence.calculate_life_score`, instrument `trace_forage` (EDR 105). Provenance :
`results/lewis_evolve_nav_107.json`. Lignée : 090→…→101→105→106→**107**.
