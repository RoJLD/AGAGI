# EDR 094 — MUR INTRINSÈQUE : la survie en Lewis est indépendante de la densité d'apex

## Contexte

La lignée a refermé deux côtés du mur de Lewis. EDR 090 : la létalité n'est pas le goulot (pas de barreau
survivable même à létalité minimale). EDR 093 : le **revenu** n'est pas le goulot (`forage_payoff` ×16 inerte,
survie 5 ticks, kills ~0.18). Le diagnostic post-093 désignait la **dépense** comme mur, avec deux composantes :
le **déclencheur** (densité d'apex `N_APEX`, qui provoque le spam d'actions chères −10) et le **tarif** (le coût
−10 lui-même). EDR 094 teste le **déclencheur**, et lui seul : balayer `N_APEX` sur Lewis à létalité 0.
Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR094-Lewis-Apex-Density-Sweep-design.md`.

Design (gelé avant données) : variable unique = **`N_APEX` ∈ (12, 9, 6, 3, 0)** (12 = baseline 093 ; 0 = Lewis
vidé d'apex). Tout le reste fixe (`forage_payoff=3`, `base_metabolism=0.25`, `leurre_frac=0`, `PREY_COUNT=15`,
`num_agents=24`, `max_ticks=300`). Pas d'évolution, pas de langage : pure mesure de survie des champions
répliqués, appariée par seed entre niveaux. Gate de barreau survivable : survie médiane > 120.

## Le verdict : MUR INTRINSÈQUE

La densité d'apex est **sans effet sur la survie**. Aux cinq niveaux — y compris `N_APEX = 0`, un Lewis
**vidé de tout apex** (zéro kill, zéro combat) — la survie médiane reste plantée à **5 ticks**, ≪ 120.

| `N_APEX` | 12 | 9 | 6 | 3 | 0 (vide) |
|---|---|---|---|---|---|
| survie médiane (ticks) | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| morts par **famine** (`energy≤0`) | 1245 | 1284 | 1399 | 1439 | 1497 |
| morts par **combat** (`hp≤0`) | 5 | 2 | 2 | 3 | 0 |
| **kills / agent** | 0.18 | 0.11 | 0.12 | 0.06 | 0.00 |

(R=4, n_eval=8, seed=194, commit `a4993f9`. Jonckheere-Terpstra z=−1.46, p(survie croît quand densité
décroît)=0.928 — **aucune** amélioration de la survie en réduisant la densité ; la tendance va même légèrement
dans l'autre sens.)

## Le mécanisme : le drain ne vient pas de l'environnement

> **Retirer ENTIÈREMENT les apex n'aide en rien.** À `N_APEX = 0`, les champions sont dans un monde sans
> menace (zéro apex à frapper → kills exactement 0.00, zéro combat), avec leurs 15 proies de forage intactes.
> Ils meurent quand même de FAMINE au tick 5.

Si le mur était la **dépense déclenchée par l'environnement** (spam de lancers/soins face aux apex), la survie
aurait dû remonter à mesure que la densité baisse. Elle ne bouge pas d'un tick. Le seul effet de la densité est
**diagnostique** et confirme le câblage : les kills décroissent proprement avec le nombre d'apex (0.18 → 0.00),
et la famine *monte* (1245 → 1497) — non parce que les agents vivent plus longtemps, mais parce qu'avec moins
d'apex moins d'agents meurent au combat, laissant **plus d'agents mourir de faim au même tick 5**.

Le mur est donc **intrinsèque** : le drain d'énergie (métabolisme de base × `phenotype_energy_drain`, coût du
brain `brain_cost`, et le soin compulsif −10 que les champions déclenchent **même sans menace**) dépasse l'apport
de forage **indépendamment de ce que le monde contient**. Ce n'est ni la létalité (090), ni le revenu (093), ni
la densité d'apex (094). C'est la **structure de coût interne du phénotype champion**, transplanté de stoneage
dans Lewis.

## Ce que la lignée a éliminé (et ce qui reste)

| EDR | Levier testé | Résultat |
|---|---|---|
| 090 | curriculum de **létalité** (rampe `leurre_frac`) | NÉGATIF PROFOND — pas de barreau survivable |
| 093 | **revenu** (`forage_payoff` ×16) | inerte — banqueroute avant de manger |
| **094** | **densité d'apex** (`N_APEX` 12→0) | **inerte — famine même dans un monde vide** |

Trois des quatre composantes de l'économie d'énergie de Lewis sont éliminées comme leviers. **Reste le tarif
intrinsèque** : le coût des actions chères (−10, hardcodé `world_1_stoneage.py:666`), le `brain_cost`, et le
métabolisme de base **relatifs à l'apport de forage**. Le prochain levier mesurable :

- **coût d'action** : paramétrer le −10 (heal/throw) et balayer — teste directement le tarif (exige de rendre
  le coût configurable dans `world_1_stoneage.py`, contrairement à `N_APEX` qui était déjà un knob propre) ;
- **brain_cost / métabolisme** vs `forage_payoff` : recalibrer le ratio dépense-intrinsèque / revenu pour *ce*
  phénotype, comme 085 l'avait fait pour stoneage.

Plus profondément, 094 suggère que le problème n'est peut-être pas un *paramètre* à régler mais le **répertoire
comportemental** des champions : ils dépensent (se soignent, calculent) à un rythme stoneage qui ne paie pas en
Lewis, et la mutation ne reforge pas ce répertoire en quelques générations (cohérent EDR 076, « la mutation est
un forgeron faible » ; et EDR 090, « adapter le substrat AVANT de durcir »).

## Honnêteté & méthode

- **Négatif propre, surdéterminé.** Le smoke réduit (n_eval=3, R=1, seed=21, niveaux 12/6/0) donne déjà MUR
  INTRINSÈQUE (survie 5 partout, kills 0.00 à 0). Le run gelé (R=4, n_eval=8, 5 niveaux, n≈1250-1500/niveau) le
  confirme. Rien ne franchit jamais le gate, à aucune densité.
- **Gate et branches pré-enregistrés.** Les trois branches (TROUVÉ à `N_APEX>0` / DÉGÉNÉRÉ seulement à 0 / MUR
  INTRINSÈQUE même à 0) ont été gelées avant données. La branche atteinte est la plus informative : elle
  **innocente l'environnement entier** et localise le levier suivant côté coût intrinsèque.
- **`N_APEX = 0` = vrai monde vide (correctif validé).** Le monde de Lewis respawn aléatoirement ~10 %/tick de
  Mammouth indépendamment de `N_APEX`. Pour que « densité 0 » signifie réellement « aucun apex », `_setup_critical`
  retire aussi Mammouth/Ours de `config.preys` quand `n_apex=0` (le respawn ne produit alors que des petites
  proies hp=1.0, jamais d'apex → `mammoth_kills` reste 0, confirmé empiriquement : kills 0.00). Correctif
  **strictement conditionnel à `n_apex=0`** → zéro impact sur 087/088/089/090/093 (tous à `n_apex>0`). Revu et
  validé (mécanisme tracé dans les chemins respawn/kill de `world_1_stoneage.py`).
- **Limitation connue (respawn).** Aux niveaux `N_APEX > 0`, le respawn ~10 %/tick fait dériver la densité
  effective d'apex à la hausse au fil du temps, tandis que `N_APEX = 0` est figé à zéro. C'est un confound
  **pré-existant** (présent aussi dans la baseline 093) et **négligeable ici** : les champions meurent de famine
  au tick 5, bien avant que le respawn n'accumule. Le verdict (survie plate à toutes densités, y compris 0) n'en
  dépend pas.
- **Bruit numérique noté.** Un `RuntimeWarning: overflow in cast` (`mamba_agent.py:422`, `surprise`) apparaît,
  dette numérique pré-existante de l'agent, sans effet sur la cause de mort ni le verdict.

## Variables d'expérience

`N_APEX` (balayé, **inerte**), **coût d'action** (−10, hardcodé — le tarif, prochain levier), `brain_cost`,
`base_metabolism` vs `forage_payoff` (ratio dépense-intrinsèque / revenu), et plus en amont le **répertoire
comportemental** des champions. Outils : `tools/lewis_survival_sweep.py` (généralisé : `main_apex`, param
`n_apex`, `_verdict_apex`), `tools/lewis_critical.py` (correctif `n_apex=0`), `src/seed_ai/exp_stats.py`.
Provenance : `results/lewis_apex_sweep_194.json` (R=4, n_eval=8, MUR INTRINSÈQUE). Lignée : 090→093→**094**
(091 = curriculum_transfer, 092 = dreaming, sessions parallèles).
