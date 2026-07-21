---
id: EDR-WARM-008
type: EDR
title: "`aux_off_weight` annule bien le grab in-world (4/4 seeds) mais le gain de survie est MESURÉ NUL, le canal « libre » est fonctionnellement PORTEUR chez certains agents, et le correctif est INTERDIT hors craft_level=0"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Levier 2 de [[EDR-WARM-005]] : valider `aux_off_weight` bout-en-bout. WARM-005 n'avait démontré son
correctif que **sur la trajectoire oracle** (logit grab −0.032 → −0.986) — or [[EDR-WARM-007]] a montré que
cette sonde a un mode d'échec réel en in-world. Le maillon d'entrée (le correctif change-t-il le
COMPORTEMENT ?) n'avait jamais été mesuré avec le bon instrument.

## Méthode
4 seeds × 2 bras (`aux_off_weight` ∈ {0.0, 1.0}), **même init** (`seed_at(seed,1)`), mêmes données,
1500 epochs de bootstrap oracle ; seule la perte diffère. Par agent : `gi` = taux de grab **exécuté
in-world** (prédicteur validé par WARM-007) et `move_acc` (canal supervisé).
Périmètre assumé et déclaré : **la survie n'était pas mesurée**, elle était INFÉRÉE de la chaîne causale
de WARM-007 (grab → taxe de portage → survie). **Cette inférence a été réfutée en revue** (infra).

## Ce qui TIENT
* **Le correctif change bien le comportement in-world** : `gi` médian 0.690 → **0.000** ; 0/48 agents
  au-dessus de 0.5 ; parmi les **39 paires où le contrôle grabbe, 39/39 réduites et 37 à ZÉRO exact**
  (les 9 autres avaient déjà `gi = 0` — réduction impossible par construction, à ne pas compter comme
  succès). 4/4 seeds à `gi` médian nul. Logit grab +0.141 → −0.986, reproduisant exactement WARM-005.
* Répliqué indépendamment en revue (ré-entraînement complet, 12/12 valeurs de contrôle identiques au
  chiffre près) : le pipeline est déterministe.
* `gi = 0` n'est PAS un artefact de mort précoce (piste écartée : les cohortes aux_off vivent aussi
  longtemps ou plus). La manipulation est mécaniquement parfaite : poids porté 0.53-1.87 → **0.000 exact**,
  puits `carry` 40.8-143.2 → **0.00**.

## Ce qui TOMBE
1. **Le gain de survie INFÉRÉ est RÉFUTÉ — il est mesuré NUL.** Seed 2026, apparié par agent : survie
   médiane **18 → 19 ticks, 6 améliorés / 6 dégradés, ratio médian = 1.000**. Mécanisme : dans cette
   population **bootstrap-oracle**, la taxe de portage ne pèse que **2.4-9.5 % du métabolisme** (carry
   40-143 vs métabolisme 1180-1765) — retirer un puits à ~5 % ne sauve pas un agent qui meurt de
   métabolisme. Le ×2.06 de WARM-005 venait d'un génome **DAgger à inventaire lourd**.
   **⇒ L'inférence causale de WARM-007 ne TRAVERSE PAS les populations.** C'est le résultat principal de
   ce record, et il invalide le raccourci que j'avais explicitement assumé pour économiser ~7 h.
2. **« Sans coût sur la compétence de mouvement » est un EFFET DE PLAFOND.** 32/48 contrôles sont déjà à
   `move_acc = 1.000` et ne *peuvent* pas bouger. Sur les 16 agents où la métrique est mobile :
   **sd(Δ) = 0.293**, étendue −0.429 à +0.695. Intervention à HAUTE VARIANCE, pas neutre. Le « 42
   inchangés » mesure la saturation d'une métrique, pas l'innocuité du correctif.
3. **Pseudo-réplication — leçon de WARM-007 non appliquée par moi.** Les 12 agents sont évalués dans le
   **même monde** (`seed_at(seed, 0)` dans `measure_inworld_grab_rate`) ; WARM-007 prescrivait
   `seed_at(seed*1000+agent, i)`. n indépendant = **4 seeds** → sign_p = 0.0625, **sous le garde-fou n≥12**.
   Le « 39/39 » n'est donc pas un résultat à n=39.
4. **Le banc ne peut PAS détecter le dommage qu'il devrait chercher.** `cognitive_demand=True` coupe TOUS
   les revenus d'inventaire (fruit +20, ver, trésor — `world_1_stoneage:743-745`) en laissant la taxe de
   portage active, avec `forage_payoff=0` et `craft_level=0`. **L'inventaire y est un coût pur par
   construction** : « grab nuit » y est quasi-tautologique. Et la moitié `rub` du correctif y est testée
   à effet ZÉRO (sans inventaire, rub n'a aucune conséquence observable).

   > 🔒 **BORNE DE PORTÉE — vérifiée empiriquement, et plus profonde que le flag.** Tentative de bras
   > `cognitive_demand=False` (WARM-009, **run NUL et non publié comme record**) : les 24 génomes y
   > survivent **6.0-7.2 ticks SANS EXCEPTION** (contre 6-124 en régime cognitif), c.-à-d. tous au
   > plancher de famine. Cause identifiée : le monde **n'engendre AUCUN item de type `Fruit`** —
   > inventaire de départ mesuré = `stick ×2, stick_short ×3, stick_long ×1, rock ×18`. Or le revenu
   > +20 exige `item_type == "Fruit"` (`world:746-749`). **Le bras était donc structurellement INCAPABLE
   > de montrer que grabber paie** — image en miroir du contrôle tautologique du §2 : là un bras qui ne
   > pouvait pas échouer, ici un bras qui ne pouvait pas réussir. Basculer le flag retire le revenu
   > cognitif sans en activer aucun autre. (Le drain mesuré est de ~12.5/tick dans LES DEUX régimes alors
   > que `base_metabolism = 0.75` : le flag manipulé n'est même pas le terme dominant du bilan.)
   >
   > **Conséquence pour [[EDR-WARM-005]], [[EDR-WARM-007]] et ce record : « le grab nuit » n'est établi
   > que dans un monde où grabber n'a AUCUN avantage possible — et c'est le seul monde que le banc
   > implémente.** La validité externe reste OUVERTE et ne peut pas être tranchée ici.
5. **Validité externe nulle sur les runners réels** : tous posent `explore_eps = 0.15-0.2`
   (`curriculum_craft.py`, `ablation.py`, `arm_nas.py`…), où le monde tire `force_grab`/`force_rub`
   ~8-10 % des ticks **indépendamment du logit** (ε-greedy EDR-019). Le correctif y serait contourné.

## Découverte : le canal « libre » est fonctionnellement PORTEUR chez certains agents
Contre-exemple `seed2026/ag04` — celui qui payait la plus lourde taxe (143.2) est celui qui **perd** le
plus : survie 18 → 13, `move_acc` **0.886 → 0.457**.
Hypothèse testée : ce coût viendrait du **gradient résiduel** de la BCE saturant le tronc. `BCE(x,0)` a son
optimum en −∞, **inatteignable** sous `tanh` : à la borne il reste un gradient de **0.269** et une perte
irréductible de **0.627** pour la paire, exercée en permanence sur les nœuds **88/89 d'un récurrent
172×172 pleinement connecté** (`backend_torch:104-113`) — pas des readouts. Or le monde ne teste que
`logit > 0` (`world_1_stoneage:1513`) : l'objectif est un **changement de signe**, pas −∞.
**Correctif implémenté** (charnière à marge, gradient exactement nul sous −margin) **et RÉFUTÉ sur sa
cible** : `ag04` passe **0.886 → 0.457, identique au millième près**. La variance globale baisse
(sd 0.293 → **0.206**) mais la charnière zéroie **moins bien** (10/12 vs 12/12 à zéro exact, marge 0.2
insuffisante). **Aucun vainqueur déclaré — arbitrage ouvert.**
> Interprétation restante, NON TESTÉE : chez certains agents le canal libre est **recruté** dans le calcul
> du mouvement (il est une unité récurrente, pas une sortie inerte). Le conflit serait alors
> **fonctionnel, pas optimisationnel** — et aucune reformulation de la perte auxiliaire ne l'éviterait.
> Prédiction falsifiable : le coût devrait corréler au poids de W entrant/sortant du nœud 88 chez ag04.

## 🛑 Interdiction de généraliser (le point le plus opérationnel)
Chaîne vérifiée dans le code — activer `aux_off_weight > 0` **casserait l'axe craft ET l'axe torch-throw** :
* `try_craft_spear` (`src/environments/stone_economy.py:103`) : `if craft_level >= 1 and not do_rub` → **gate DUR** ;
* feu/Spark (`world_1_stoneage:1507`) : `elif do_rub and len(inv) >= 2` → gate dur ;
* grab OFF → inventaire vide → craft impossible **même à L0** ;
* **contagion silencieuse** : sans rub, pas de Spear, donc `_throw_kill_tool`
  (`world_1_stoneage:1455,1482`) ne se déclenche jamais → le KPI de l'arc **EDR-172→178 tombe à 0 sans
  lever d'erreur**.

Le défaut `0.0` protège le code EXISTANT, **pas le prochain appelant**. D'où une **garde runtime**
livrée : `assert_aux_off_safe(env)` refuse `craft_level != 0`, `torch_throw_gate` actif, et
`explore_eps > 0`. Documentée aussi dans le docstring de `imitate_episode_bptt`.

## Correction à [[EDR-WARM-007]] (et à ma propre justification de ce banc)
J'y ai écrit que la sonde sur trajectoire oracle « **classe les agents à l'envers** ». **Sur-généralisation
de 3 cas.** Mesuré : `spearman(oracle, in-world) = +0.819`, **0 faux-POSITIF, 3 faux-NÉGATIFS**. C'est un
mode d'échec **unilatéral** (la sonde oracle rate des grabbers, elle n'en invente pas), pas une inversion.
La sonde reste un mauvais prédicteur pour classer, mais l'énoncé était faux — troisième occurrence dans cet
arc de la même faute : généraliser depuis un petit échantillon de cas saillants.

## Verdict
**`AUX_OFF_ZEROES_THE_CHANNEL_BUT_BUYS_NO_SURVIVAL_HERE__AND_IS_FORBIDDEN_OUTSIDE_CRAFT0`** — le correctif
fait ce qu'il prétend sur le canal, ne rapporte **rien** en survie dans cette population, coûte une
perturbation à haute variance dont un cas majeur résiste à toute reformulation de la perte, et **ne doit
pas être promu** hors du régime `craft_level=0 / torch_throw_gate=off / explore_eps=0`.

## Portée & limites
* n indépendant = **4 seeds** (sign_p = 0.0625) : sous le garde-fou n≥12 du projet. Aucun verdict POSITIF
  ne devrait en être tiré, conformément à [[power-evaporation-guardrail]].
* Survie mesurée sur **1 seed** (2026) en revue — nulle, mais à répliquer avant d'en faire une loi.
* Population bootstrap-oracle uniquement (pas de DAgger) : c'est précisément ce qui produit l'inventaire
  léger dont la taxe est marginale.

## Leviers suivants
1. Si l'on veut le gain de survie : le **mesurer** sur ≥12 seeds avec mondes par agent
   (`seed_at(seed*1000+agent, i)`), sur une population **DAgger** (inventaire lourd), pas bootstrap.
2. Tester l'hypothèse du **canal porteur** (corrélation coût ↔ poids de W autour du nœud 88).
3. Un bras `cognitive_demand=False` : vérifier que supprimer le grab ne détruit pas le revenu-fruit (+20),
   que ce banc annule par construction.

Converge [[EDR-WARM-005]] (dont il valide le canal mais réfute la portée), [[EDR-WARM-007]] (qu'il corrige
sur la sonde oracle et dont il borne l'inférence), [[power-evaporation-guardrail]],
[[unit-of-analysis-population-vs-replicate]], [[pseudo-replication-12-agents]], REF-DEMAND-MARKER.
