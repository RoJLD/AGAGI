---
id: EDR-WARM-006
type: EDR
title: "Il n'y a JAMAIS eu de dérive du canal grab : l'agent persisté est NÉ saturé ON (1/12) — le « OFF → ON » de WARM-005 est une erreur d'unité d'analyse (moyenne-de-population à t=0 vs réplicat-unique à t=fin)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Levier 1 de [[EDR-WARM-005]] : d'où vient la dérive du canal d'action non supervisé `grab` (nœud 24),
qui passe de OFF à ON et saigne l'énergie ? WARM-005 avait laissé l'origine **OUVERTE** en constatant que
son bras de contrôle (bootstrap court) ne reproduisait pas la panne, et avait conclu que la dérive
« provient de quelque chose de spécifique à la boucle DAgger ».

## Méthode — un discriminateur qui s'est révélé sans objet
Le levier tel que formulé (« comparer le logit 24 round par round ») **confond deux causes** : le round 0
fait déjà 3000 pas de gradient sur données oracle pures, et les rounds suivants ajoutent À LA FOIS des
données on-policy ET des pas de gradient. Discriminateur construit (`run_grab_drift_diagnostic`) :

* `_probe_free_channels` — sonde SANS gradient sur trajectoire de référence FIXE, échantillonnée tous les
  250 epochs, donc **plusieurs points DANS le round 0**, avant toute donnée on-policy ;
* bras de contrôle `oracle_only` — **même nombre total d'epochs (18 000)**, dataset qui ne grandit jamais.
  C'est le contrôle que WARM-005 n'avait pas : le sien était COURT, or la durée était la variable suspecte.

Trace obtenue (seed 2026, 18 000 epochs, `results/warm006_grab_drift.json`) : le grab fait une **excursion
transitoire** (+0.099 vers 750 epochs, reproductible ; sous seed 7 le pic se déplace à +0.201 vers 300),
puis retombe et se stabilise à **−0.007 / on_frac 0.505** avec `move_acc` 1.000. Le génome DAgger persisté,
sondé avec la MÊME sonde, est à **+0.946 / on_frac 1.000**. Lecture immédiate — et FAUSSE : « à durée
appariée l'oracle-only ne dérive pas, donc ce sont les données on-policy ».

## Résultat — la question se dissout
Sonde **PAR AGENT** (le point que la lecture ci-dessus manquait) :

| | grab agent 0 | on_frac agent 0 |
|---|---|---|
| **Naissance (0 pas de gradient)** | **+0.9626** | **1.000** |
| Après 18 000 epochs de DAgger | +0.9517 | 1.000 |
| **Δ (fin − naissance)** | **−0.011** | 0.000 |

L'agent persisté est **né saturé ON** et n'a jamais bougé — il a même dérivé *marginalement vers OFF*.
Distribution du grab à la naissance sur les 12 agents (seed 2026) :
`[+0.963, −0.768, −0.801, −0.536, +0.237, −0.606, −0.733, −0.034, +0.502, −0.051, −0.253, −0.856]`,
soit **1 seul saturé sur 12**, et c'est celui que `agents[0].genome` persiste.

> **Erreur d'unité d'analyse** : le « OFF → ON » opposait la **moyenne des 12 agents à t=0** (−0.2447) au
> **réplicat unique agent 0 à t=fin** (+0.95). `self.W` est de forme (B, N, N) — les poids sont **par
> agent** — donc les 12 agents divergent, et leur moyenne n'est pas comparable à l'un d'eux.
> **H_durée et H_données répondaient toutes deux à une question qui ne se pose pas.**

> 🛑 **AMENDÉ PAR [[EDR-WARM-007]] — ce record a commis À SON TOUR l'erreur qu'il dénonce.** La conclusion
> « le canal libre est distribué par l'INITIALISATION, pas par l'entraînement » (ci-dessous, section
> Corollaires et Leçon) est **RÉFUTÉE** : sur les 24 agents de WARM-007, **|final − birth| médian = 0.557**
> et plusieurs agents TRAVERSENT (seed 7 agent 6 : −0.716 → +0.433 ; seed 2026 agent 5 : −0.606 → +0.674).
> Le canal est **plastique**. L'agent 0 ne bougeait pas parce qu'il est **saturé au plafond de tanh** —
> c'est le seul des 12 qui ne PEUT pas bouger, et c'est celui depuis lequel ce record a généralisé.
> La moyenne de population du bras oracle_only restait à −0.007 **parce que les dérives individuelles
> s'annulent**, pas parce qu'il n'y en avait pas — troisième instance de la même erreur d'unité d'analyse.
> **CE QUI TIENT** : il n'y a pas eu de dérive **chez l'agent 0** (Δ = −0.011, reproduit deux fois), et
> l'erreur d'unité d'analyse que ce record documente reste le garde-fou principal du fil.
> ⚠️ Les affirmations ci-dessous sur l'INCIDENCE (« 1 saturé /12 », « 0 à 5 /12 selon le seed ») restent
> valides — elles portent sur la NAISSANCE, que WARM-007 ne conteste pas.

## Corollaires établis par la revue adversariale
* **L'effet ne généralise pas — il tient à l'index `agents[0]`.** État final `oracle_only` seed 2026,
  on_frac par agent : `[1.0, 0.6, 0.2, 0.057, 0.286, 0.743, 0.171, 0.486, 0.8, 0.857, 0.0, 0.0]`. En
  persistant l'agent 3, WARM-005 aurait mesuré on_frac ≈ 0.06 et le phénomène n'aurait jamais existé.
  **Sous seed 7, le même index `agents[0]` va de −0.558 à −0.944 (saturé OFF)** — le phénomène s'inverse.
* **L'init du canal libre est arbitraire** : sweep 6 seeds (0 pas de gradient), moyenne d'init entre
  **−0.648 et +0.361**, agents saturés `|grab| > 0.9` entre **0 et 5 sur 12**. Le canal libre est distribué
  sur toute la plage de tanh dès la naissance — ce qui est attendu : aucun terme de la perte ne le contraint.
* **Au niveau population, H_données n'est pas établie non plus.** Bras `dagger` apparié lancé (2000 epochs,
  init identique) : différence appariée `dagger − oracle_only` = **moyenne +0.221, 8/12 positifs,
  sign_p = 0.388** → **non concluant** sous le garde-fou [[power-evaporation-guardrail]]. La dispersion
  inter-agents (σ ≈ 0.53) écrase l'effet.
* **Négatifs de contrôle qui TIENNENT** : l'indice 24 est vérifié de bout en bout (sonde → `forward()` →
  `world_1_stoneage.py:1513-1518`, même colonne et même seuil que le monde) ; pas de confond RNG
  (`imitate_episode_bptt` est déterministe, `_collect_onpolicy_trajectory` se re-seede) ; pas d'aliasing de
  génome (`from_genome` fait un `deepcopy`) ; le transitoire à 750 epochs est un phénomène d'apprentissage
  réel (il suit `move_acc`), pas un artefact de sonde.

## Verdict
**`NO_DRIFT_EXISTED__UNIT_OF_ANALYSIS_ARTEFACT`** — le récit d'origine de WARM-005 (« la boucle DAgger a
poussé le canal libre vers ON ») est **RÉFUTÉ**. Le canal était ON dès l'initialisation, par tirage, chez
1 agent sur 12. Aucun mécanisme d'entraînement n'a besoin d'être invoqué.

## Amendements à WARM-005
**TOMBE** : (i) le récit d'origine ; (ii) la **généralité** du phénomène — le résultat repose sur un agent
choisi par index arbitraire, qui se trouve être le seul des 12 né saturé sous ce seed ; (iii) le levier 1,
qui est CLOS comme sans objet.

**TIENT** : l'ablation causale elle-même (grab forcé OFF → survie ×2.06, within-subject, 12/12 ères,
sign_p = 0.00024) n'est pas attaquée — elle reste valide **pour cet agent**. Un canal libre né ON *saigne
réellement* l'énergie. Ce qui n'a jamais été mesuré, c'est son **incidence** : la fraction d'agents
concernés (0 à 5 sur 12 selon le seed) et donc la part du plateau de survie qu'il explique en moyenne.

## Portée & limites
* La sonde mesure sur la trajectoire oracle, **tronquée à la première mort** — T = 35 ticks sous seed 2026
  mais T = 131 sous seed 7. Le `move_acc = 1.000` à 18 000 epochs porte sur 420 échantillons et relève très
  probablement de la **mémorisation** (l'accuracy on-policy de WARM-003 était ~0.73). La sonde est un
  instrument de *canal libre*, pas de compétence.
* Taille/diversité du dataset et caractère on-policy restent **non séparables** dans le bras `dagger`
  (le dataset passe de 1 à 6 trajectoires en même temps qu'il devient on-policy). Sans objet ici puisque
  la question se dissout, mais à retenir si le bras est réutilisé.
* Coût : le contrôle 18 000 epochs a pris **110 min**. Le run apparié à 2 bras (3,7 h) initialement prévu a
  été **annulé** par la revue — il aurait mesuré un non-phénomène avec une grande précision.

## Leçon méthodologique (transférable)
**Un canal non contraint par la perte est distribué par l'initialisation, pas par l'entraînement.** Avant
d'attribuer la valeur d'un paramètre libre à une dynamique d'apprentissage, mesurer sa valeur **à la
naissance, sur le même réplicat**. Et ne jamais comparer une **statistique de population** à un **réplicat
individuel** : c'est le cousin temporel du faux-positif between-subject de [[s2-world-demand-thread]]
(S2-001), transposé de l'axe des sujets à l'axe du temps.

Corollaire opérationnel pour ce dépôt : `agents[0].genome` est un **échantillon de taille 1** tiré d'une
population de 12 réplicats divergents. Tout résultat persisté par cet index doit être requalifié en
« un agent » et non « le génome », ou répliqué sur ≥6 agents.

## Leviers suivants
1. **Mesurer l'INCIDENCE du canal-né-ON** et refaire l'ablation WARM-005 sur ≥6 agents (et ≥2 seeds) →
   convertit un résultat n=1 en distribution, et chiffre la part réelle du plateau de survie.
2. Valider bout-en-bout `aux_off_weight` à budget borné — **renforcé** par ce record : forcer les canaux
   libres vers OFF supprime une source de variance d'initialisation, indépendamment de toute dérive.
3. Identifier les termes résiduels du bilan énergétique (−0.075 vs +0.583 pour l'oracle).

Converge [[EDR-WARM-005]] (qu'il amende), [[EDR-WARM-003]], [[EDR-WARM-004]],
[[power-evaporation-guardrail]], [[within-subject-demand-marker]], REF-DEMAND-MARKER.
