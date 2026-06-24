# EDR 098 — PAS LE BRAIN_COST : le mur intrinsèque de Lewis n'est pas le `brain_cost` surprise-amplifié

## Contexte

EDR 094 a établi que la survie en Lewis est **indépendante de l'environnement** (MUR INTRINSÈQUE : famine au
tick 5 même à `N_APEX=0`). L'exploration post-094 a réfuté la prémisse heal-spam (soin gardé par `hp<100`,
inactif sans combat) et désigné le **`brain_cost`** par tick — `ttc_base_cost × (1+log2(1+compute)) ×
surprise_scale`, `surprise_scale = 1 + surprise × ttc_surprise_scale` — amplifié par la surprise (un
`RuntimeWarning: overflow` sur la surprise apparaît à chaque run). EDR 098 teste cette hypothèse : balayer
`ttc_surprise_scale` à `N_APEX=0` (monde vide), en instrumentant `surprise_momentum`.
Pré-enregistrement : `docs/superpowers/specs/2026-06-24-EDR098-Intrinsic-Drain-Surprise-Sweep-design.md`.

Design (gelé) : variable unique = **`ttc_surprise_scale ∈ (1.0, 0.5, 0.25, 0.0)`**, tout le reste fixe
(`N_APEX=0`, `forage_payoff=3`, `base_metabolism=0.25`, `leurre_frac=0`, `max_ticks=300`, `num_agents=24`).
Verdict 3 branches : TARIF=SURPRISE (un scale franchit le gate) / OVERFLOW=RACINE (aucun + surprise non-finie) /
PAS LE BRAIN_COST (aucun + surprise finie).

## Le verdict : PAS LE BRAIN_COST (substantiellement)

Le `brain_cost` surprise-amplifié **n'est pas** le mur. Découpler le `brain_cost` de la surprise (de
`scale=1.0` à `scale=0.0`) **ne change rien** à la survie.

| `ttc_surprise_scale` | 1.0 | 0.5 | 0.25 | 0.0 |
|---|---|---|---|---|
| survie médiane (ticks) | 5.0 | 5.0 | 5.0 | 5.0 |
| mean_surprise (finie) | 0.427 | 0.428 | 0.428 | 0.427 |
| frac_nonfinite | 0.000000 | 0.000000 | 0.000391 | 0.000391 |
| famine | 1643 | 1644 | 1646 | 1645 |

(R=4, n_eval=8, seed=198, commit `b4a578f`. Jonckheere-Terpstra z=0.012, **p(croissance)=0.495** — survie
rigoureusement plate, pur hasard.)

## Le mécanisme : la surprise est clampée — le brain_cost ne peut pas être le drain

Deux faits du code rendent l'hypothèse **structurellement** intenable, indépendamment des données :

1. **La surprise est clampée à [0,1]** (`mamba_agent.py:442`, `surprise = np.clip(surprise, 0.0, 1.0)`) AVANT
   l'EMA. Donc `surprise_momentum ∈ [0,1]`, et `surprise_scale = 1 + surprise × ttc_surprise_scale ∈ [1, 2]`.
   Le `brain_cost` est **au plus doublé** par la surprise — jamais explosé. Avec `ttc_base_cost = 0.01`, le
   `brain_cost` reste ~0.01-0.2/tick, **deux ordres de grandeur sous** le drain de ~13-16/tick. La surprise
   mesurée (~0.43) confirme : elle n'est même pas saturée.
2. Le `RuntimeWarning: overflow encountered in cast` (`err` du world_model casté en float32) est **capé par le
   clip** : un `inf` devient 1.0. L'overflow brut ne se propage donc PAS au `brain_cost`.

Les données confirment la structure : survie plate à toutes les scales (p=0.495), `brain_cost` découplé
(`scale=0`) sans effet. **Le drain de ~13-16/tick est ailleurs** — ni la létalité (090), ni le revenu (093), ni
la densité d'apex (094), ni le `brain_cost` surprise-amplifié (098).

## Le verdict gelé littéral (OVERFLOW=RACINE) est un artefact de la règle

Le harnais a retourné **OVERFLOW=RACINE**, pas PAS LE BRAIN_COST. C'est un **défaut de la règle
pré-enregistrée**, diagnostiqué (Phase 1 systematic-debugging) :

> La règle `aucun franchit + any(frac_nonfinite > 0) → OVERFLOW` est déclenchée par une fraction de **0.000391**
> de surprise non-finie aux scales 0.25 et 0.0 (arrondie à `0.00` à l'affichage). Le diagnostic localise la
> cause : **un seul agent**, dans **un seul seed** (202), dont la `surprise_momentum` devient NaN au **tick 33**.

Ce NaN est du **bruit**, pas un signal :
- **1 agent sur ~1645** (sub-0.05%).
- **Tick 33** alors que la médiane de survie est **5** : c'est un **survivant aberrant** (6× la médiane), pas un
  mort de famine. Le mur (famine tick 5, toute la population) n'a aucun lien avec ce NaN tardif.
- **Pourquoi seulement aux scales basses ?** Appariement : à `scale=1.0/0.5` ce même agent (seed 202) a un
  `brain_cost` marginalement plus haut → meurt avant le tick 33 → n'atteint jamais l'état NaN. À `scale` bas il
  survit assez longtemps pour l'atteindre. Le NaN apparaît au scale bas **parce que l'agent y survit plus
  longtemps**, pas par une instabilité dépendante du scale.
- Source : `err` du world_model (`world_model.observe_batch`) devient NaN pour cet agent ; le clip préserve le
  NaN (`clip(nan)=nan`) ; l'EMA le propage (`surprise_momentum`). Edge-case numérique du world_model (écho
  lointain de l'instabilité connectome EDR 086, corrigée par clamps ±30 / [-5,5] ; un chemin résiduel subsiste).

La condition **intentionnelle** de la branche OVERFLOW (spec §3 : « `scale=0` donne `1+inf×0=nan` → le
découplage est confondu par l'overflow ») n'est **pas** remplie : le découplage marche proprement (survie 5.0 à
`scale=0`, surprise bulk finie ~0.43). La règle a tiré sur une technicité (`any` trop sensible à 1 outlier),
pas sur le phénomène qu'elle visait. **La lecture substantielle est PAS LE BRAIN_COST.**

## Le vrai levier (re-pointé) : décomposer le drain de ~13-16/tick

EDR 098 ferme le `brain_cost` surprise-amplifié. Le drain intrinsèque de ~13-16/tick au tick 5 reste
**non identifié**. EDR 099 doit le **décomposer** directement (instrumenter le bilan énergétique par poste/tick
à `N_APEX=0`) plutôt que de continuer à deviner. Postes candidats restants (`world_1_stoneage.py` step) :
- **throw** (−10/−5, `:1122`) si les agents lancent dans le vide avec inventaire ;
- **métabolisme/terrain/carry** cumulés (chacun petit, mais combinés ?) ;
- un poste non encore inventorié dans le step.

Une décomposition par poste tranchera. (Note : le NaN du world_model est un edge-case mineur réel, candidat à
un clamp défensif — mais c'est de la dette numérique, **pas** le mur, et il ne doit pas détourner EDR 099.)

## Honnêteté & méthode

- **Pré-enregistrement respecté, défaut de règle exposé par les données.** Le verdict gelé (OVERFLOW) est
  rapporté tel quel, puis disséqué : le diagnostic montre qu'il est déclenché par 1 outlier, pas par le
  phénomène visé. La discipline de gel a fait son travail (empêcher le post-hoc) ; l'honnêteté exige de ne pas
  présenter « overflow = racine du mur » alors que c'est faux. Leçon de méthode : une règle `any(frac>0)` sur un
  grand échantillon est trop sensible — un seuil (ex. `frac > 1%`) ou une médiane aurait évité l'artefact.
- **Négatif propre, surdéterminé.** Le smoke (n_eval=3, R=1, scales 1.0/0.25/0.0) donne déjà survie plate +
  surprise ~0.4 finie + PAS LE BRAIN_COST. Le run gelé (R=4, n_eval=8, 4 niveaux, n≈1645/niveau) le confirme,
  avec JT p=0.495.
- **Reproductibilité.** `_disable_kuzu()` + `Harness(with_db=False)` ; `memory_retriever.stop()`+`clear()` ;
  `seed_at` par ère ; mêmes seeds entre niveaux (appariement strict — c'est l'appariement qui révèle le NaN au
  scale bas). Outil config-only : aucune modification du code de production.
- **Diagnostic reproductible.** Le NaN se rejoue exactement (seed=202, scale=0.0, tick 33, 1 agent).

## Variables d'expérience

`ttc_surprise_scale` (balayé, **inerte**), et — prochain levier — **décomposition du drain** (throw `:1122`,
métabolisme/terrain/carry, postes du step). Dette notée : clamp défensif de `surprise_momentum`/`err` world_model
(edge-case NaN tardif). Outils : `tools/lewis_survival_sweep.py` (`main_surprise`, `collect_surprise`,
`_verdict_surprise`), `src/seed_ai/exp_stats.py`. Provenance : `results/lewis_surprise_sweep_198.json`
(R=4, n_eval=8, verdict gelé OVERFLOW=RACINE = artefact ; lecture substantielle PAS LE BRAIN_COST).
Lignée : 090→093→094→**098**.
