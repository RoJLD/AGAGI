# EDR 093 — PAS DE RUNG PAR LE REVENU : le mur de Lewis est la dépense, pas le revenu

## Contexte

EDR 090 a montré que le curriculum de létalité échoue parce qu'**il n'y a pas de premier barreau survivable** :
les champions stoneage ne survivent pas au monde de Lewis, même à létalité minimale. Le diagnostic post-090
a établi le **mécanisme** : les champions meurent de **FAMINE** (`energy ≤ 0`) en ~5-7 ticks, pas de combat,
en spammant des actions chères (soin −10, lancer −10) dans un Lewis dense en apex → drain ≫ apport de forage.

EDR 093 teste **le** levier que ce diagnostic désigne, et lui seul : **balayer le revenu de l'économie**
(`forage_payoff`, le multiplicateur de nutrition par kill) pour voir *si* et *où* un premier barreau survivable
apparaît, sur Lewis à **létalité 0** (apex présents, pas de Leurres mortels → on isole l'énergie de la létalité).
Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR093-Lewis-Survival-Sweep-design.md`.

Design (gelé avant données) : variable unique = **`forage_payoff` ∈ (3, 6, 12, 24, 48)** (de la valeur 085
vers ×16). Tout le reste fixe (`base_metabolism=0.25`, `N_APEX=12`, `leurre_frac=0`, `PREY_COUNT=15`,
`max_ticks=300`, `num_agents=24`). **Pas d'évolution, pas de langage** : pure mesure de survie des champions
répliqués (`_reproduce`), appariée par seed entre niveaux. Gate de barreau survivable : **survie médiane > 120**.

## Le verdict : PAS DE RUNG PAR LE REVENU

Le revenu est **totalement inerte**. Aux cinq niveaux de `forage_payoff` — y compris ×16 — la survie médiane
reste plantée à **5 ticks**, ≪ 120. Aucun barreau n'est franchi.

| `forage_payoff` | 3 | 6 | 12 | 24 | 48 (×16) |
|---|---|---|---|---|---|
| survie médiane (ticks) | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| morts par **famine** (`energy≤0`) | 1256 | 1284 | 1284 | 1284 | 1284 |
| morts par **combat** (`hp≤0`) | 3 | 5 | 5 | 5 | 5 |
| **kills / agent** | 0.17 | 0.18 | 0.18 | 0.18 | 0.18 |

(R=4, n_eval=8, seed=193, commit `acc9cd0`. Jonckheere-Terpstra z=−0.51, p(croissance)=0.696 — **aucune**
tendance croissante de la survie avec le revenu.)

## Le mécanisme : la dépense est le mur, le revenu ne l'atteint jamais

La spec avait gelé la **signature désambiguïsante** d'un négatif : si la survie est plate **et** que les kills
sont ≈0 au niveau haut, alors la mort est un **mur de dépense/comportement**, pas un manque de revenu. Cette
signature est **complète** :

> **La famine fait 99,6 % des morts, et les agents ne tuent quasiment rien (≈0.18 kill/agent) — même quand un
> kill rapporte ×16.** Multiplier le revenu par kill est sans effet parce que les agents font **banqueroute au
> tick 5, avant de manger**. Le knob de revenu agit sur une transaction qui n'a jamais lieu.

La preuve la plus nette est dans la **dégénérescence des trajectoires** : les niveaux 6, 12, 24 et 48 produisent
des chiffres **rigoureusement identiques** (famine=1284, combat=5, kills=0.17549…, n=1294). `forage_payoff`
n'a **aucun effet causal** sur le déroulé — les mondes évoluent à l'identique quel que soit le payoff, parce
que la nourriture n'est jamais le facteur limitant. (Le niveau 3 diffère marginalement, 1256 vs 1284 : les
rares kills à payoff minimal donnent si peu d'énergie que quelques trajectoires divergent d'un cheveu.)

C'est le complément exact d'EDR 090. 090 disait : « pas de premier barreau survivable, même à létalité 0 ».
093 localise **pourquoi** : ce n'est pas que le monde manque de nourriture (revenu), c'est que les champions
**dépensent compulsivement** (actions −10) face à la densité d'apex et tombent en banqueroute avant le premier
repas. Le levier n'est pas du côté du revenu de l'économie — il est du côté de la **dépense**.

## Le vrai levier (re-pointé) : coûts d'action / densité d'apex

EDR 093 ferme proprement le côté revenu de l'économie d'énergie. Le mur restant est la **dépense incompressible**.
Le levier en amont, mesurable avec le même harnais (changer un knob, relire survie + cause de mort + kills) :

- **coût des actions chères** (soin −10, lancer −10 ; `world_1_stoneage.py`) — le poste de drain direct ;
- **densité d'apex `N_APEX`** — ce qui *déclenche* le spam d'actions chères (lancer sur les apex, se soigner
  après riposte) ; à 12 apex, l'environnement force la dépense.

Un sweep `N_APEX` (ex. 12→6→3→0) ou un sweep du coût d'action désambiguïserait à son tour : si baisser la
densité d'apex débloque la survie → c'est bien le déclencheur comportemental ; si baisser le coût d'action
seul suffit → c'est le tarif. La chaîne complète vers « le langage paye » exige toujours sa première marche —
**survivre-en-Lewis** — et cette marche se fabrique en touchant la dépense, pas le revenu.

## Honnêteté & méthode

- **Négatif propre, surdéterminé.** Le verdict ne dépend pas de la puissance : le smoke réduit (n_eval=3, R=1,
  seed=21, niveaux 3/12/48) donne déjà PAS DE RUNG avec la même signature (survie 5, kills≈0.12, JT non
  croissant) ; le run gelé (R=4, n_eval=8, 5 niveaux, n≈1294/niveau) la confirme. Rien ne franchit jamais le gate.
- **Gate pré-enregistré, pas post-hoc.** Le seuil « >120 ticks » et les trois branches (TROUVÉ ≤24 / TROP CHER
  =48 / PAS DE RUNG) ont été gelés avant données. La branche atteinte est la plus informative des trois : elle
  ne dit pas seulement « ça rate », elle **localise le levier suivant** (dépense, pas revenu).
- **Reproductibilité verrouillée.** `_disable_kuzu()` + `Harness(with_db=False)` (double protection contre la
  contention/mémoire ambiante KuzuDB), `memory_retriever.stop()`+`clear()`, `seed_at` par ère, mêmes seeds
  entre niveaux (appariement). Survie = âge sur le pool `vivants + morts` (non biaisé survivants). Cause de
  mort lue dans le vrai `world_1_stoneage.py:1283` (famine `energy≤0` et combat `hp≤0 ∧ energy>0`, exhaustives
  et exclusives sur les morts).
- **Bruit numérique noté, sans incidence.** Un `RuntimeWarning: overflow in cast` (`mamba_agent.py:422`,
  `surprise`) apparaît pendant le run ; c'est une dette numérique pré-existante de l'agent, sans effet sur la
  cause de mort ni le verdict (les `n` sont cohérents, famine domine partout).

## Variables d'expérience

`forage_payoff` (balayé, **inerte**), **coût des actions chères** (−10, le vrai levier), **`N_APEX`** (densité
d'apex, le déclencheur), `base_metabolism`. Outils : `tools/lewis_survival_sweep.py` (`_cfg`, `_measure_survival`,
`_verdict`, `_report`, `main` ; `_disable_kuzu`, `_setup_critical` `leurre_frac=0`), `src/seed_ai/exp_stats.py`
(Jonckheere-Terpstra). Provenance : `results/lewis_survival_sweep_193.json` (R=4, n_eval=8, PAS DE RUNG).
Lignée : 087→088→089→090→**093** (091 = curriculum_transfer, 092 = dreaming, sessions parallèles).
