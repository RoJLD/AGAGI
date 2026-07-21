---
id: EDR-WARM-007
type: EDR
title: "Le grab nuit RÉELLEMENT à la survie (causalité bidirectionnelle) mais le mécanisme est la TAXE DE PORTAGE cumulative, pas le coût du geste — et AUCUNE dose-réponse n'est établie : mon contrôle négatif était tautologique et mon sign_p invalide (pseudo-réplication, n indépendant = 2)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
Levier 1 issu de [[EDR-WARM-006]] : quelle est l'INCIDENCE du canal `grab` né-ON, et l'ablation causale de
[[EDR-WARM-005]] (survie ×2.06 sur UN génome retenu par l'index `agents[0]`) généralise-t-elle ?

## Méthode
24 génomes (2 seeds × 12 agents, DAgger 3000 epochs), ablation **within-subject** `grab_off` (canal 24
forcé sous le seuil d'exécution du monde, `world_1_stoneage:1513`), K=6 ères appariées par agent.
Prédicteur `gi` = taux de grab **réellement exécuté in-world**, compté DANS le bras intact sur les mêmes
ères. Génomes persistés (`results/warm007_genomes/`), entraînement vérifié **déterministe**
(`repro_delta = 0.0` exact sur 24 génomes) → toute réanalyse ultérieure est gratuite.

### Bug d'instrumentation trouvé en revue (et son contrôle)
`TorchPopulationModel.forward` renvoie une **VUE** de `self.H` (`backend_torch` ~L144 :
`logits = H_new[:, N-O:N]` puis `.cpu().numpy()` partage le storage). La 1re passe écrivait
`logits[:, 24] = -1.0` **dans l'état récurrent**, épinglant le neurone 88 à chaque tick — une seconde
intervention dont l'amplitude `|h₂₄ − (−1)|` était **colinéaire au prédicteur même de la conclusion**.
Corrigé (`_DecoupledTorchPop` / `_GrabOffTorchPop`, découplage appliqué aux DEUX bras), 3 tests de
non-régression dont un no-op EXACT.
> **Contrôle sham décisif** : clamper à −1.0 le nœud **20** — que le monde ne lit JAMAIS (grep exhaustif :
> seuls 0-15 et 24-28 sont lus) — **dans la vue**, donc en reproduisant exactement la voie d'aliasing sans
> conséquence d'action : ratios **1.035 / 1.077 / 0.968**. La perturbation d'état seule ne produit RIEN.
> Le bug était réel mais **inerte** : il a mal contrôlé la 1re passe, il ne l'a pas générée.
> **Le découplage est d'ailleurs INUTILE** : bras production vs découplé **bit-à-bit identiques** sur
> 2026/0 ; l'effet réplique en production (×4.44 / 1.68 / 1.13 vs ×5.14 / 2.24 / 1.13 découplé — le
> découplage GONFLE l'ampleur de 10-33 %, donc le chiffre à retenir est celui de production).

## Résultat — la causalité TIENT, établie bidirectionnellement
* **Sens 1 (retirer)** : `grab_off` augmente la survie chez les agents qui grabbent (production, 3 génomes :
  **×1.13 à ×4.44**).
* **Sens 2 (ajouter) — le contrôle qui compte** : forcer `logits[24] = +1.0` chez les 8 agents qui ne
  grabbaient pas **dégrade 8/8**, 45/48 ères, ratios 0.40–0.98, **sign_p = 0.0078**. Ce bras ne dépend
  d'aucune mesure de `gi` et remplace le contrôle négatif défectueux (cf. infra).

### Mécanisme identifié — ce n'est PAS le coût du geste
Le grab coûte un one-shot de **−1.0** (`world_1_stoneage:1526`). Le vrai puits est la **taxe de portage**
(`world_1_stoneage:738-739`) :
```python
carry_weight = sum(i.get("weight", 1.0) ... for i in agent["inventory"])
agent["energy"] -= carry_weight * 0.5      # à CHAQUE tick, à VIE
```
Instrumenté sur 7/6 : **1.66 énergie/agent-tick**, soit 11.6 % de la dépense brute — mais la marge nette
n'est que ~3/tick, donc le portage mange **~55 % de la marge de survie**. Sous `grab_off` : `carry = 0.000`
et `mean_inv = 0.000` exactement. Le titre correct est **taxe de portage cumulative**, pas « canal d'action
qui saigne l'énergie ». Corollaire : l'ampleur doit croître avec la durée de vie de base — c'est observé
(ρ = −0.83, p = 0.010, entre dégradation force-ON et durée de vie).

## Résultats NÉGATIFS (dont deux réfutent mes propres conclusions intermédiaires)
1. **AUCUNE dose-réponse au taux de grab n'est établie.** La corrélation apparente
   (`spearman(ratio, gi) = +0.731` sur n=24) est **entièrement portée par le contraste zéro/non-zéro** :
   **intra-répondeurs, ρ = +0.094 (p = 0.73)**. Pire, les trois `gi` les plus élevés (1.000, 0.998, 0.998)
   ont les ratios les plus **faibles** (1.13, 1.09, 1.22). Mesurer la vraie dose (intégrale de portage)
   ne sauve pas : reste n.s.
2. **Mon « contrôle négatif » était TAUTOLOGIQUE.** Les 8 agents `gi < 0.01` sont EXACTEMENT les 8 à
   `carry_per_tick = 0.000`, et **6/8 rendent des tableaux intact/ablé bit-identiques**. Clamper une action
   qui ne s'exécute jamais est un no-op *par construction* : ce test **ne pouvait pas échouer**. C'est un
   contrôle de déterminisme d'implémentation, pas un contrôle causal ; le `wins 2/48` n'a aucune valeur
   probante. Le vrai contrôle est la manipulation INVERSE (force-ON, supra).
3. **« Non explicable par la survie de base » est INVERSÉ.** Le `corr = −0.014` publié en cours de route est
   un artefact du groupe tautologique (ratio ≡ 1.0 sur toute la gamme de survie 8→82). Intra-répondeurs :
   **ρ = +0.506 (p = 0.043)**. Le mécanisme cumulatif le PRÉDIT — l'effet plancher MASQUE la dose-réponse,
   il ne la réfute pas.
4. **`sign_p = 1.5e-05` est INVALIDE — pseudo-réplication.** Les 12 agents d'un seed partagent la
   trajectoire oracle, l'augmentation DAgger issue du **seul `agents[0]`**, l'optimiseur, **et les 6 mêmes
   mondes** (`seed_at(seed, i)`), avec 12 clones interagissant par consensus social. Corrélation
   inter-agents des log-ratios par ère : **+0.345 (2026) / +0.309 (seed 7)**. **n indépendant = 2**, pas 16.
5. **Censure et instabilité** : bootstrap 5000× → **4 des 16 « répondeurs » ont un IC95 contenant 1.0**
   (« 16/16 améliorés » → 12/16) ; 7/4, 7/6, 7/9 touchent le plafond `max_ticks = 200` dans le bras ablaté
   (2, 2 et **5** ères sur 6) → 7/9 n'est pas interprétable, les grands ratios sont **censurés à droite**.
6. **Spécificité partielle** : clamper `rub` (25) donne 1.03 / 1.18 / 1.00 contre 4.44 / 1.68 / 1.13 pour
   grab. L'effet est grab-dominé, mais 2026/5 à 1.18 montre que « canal libre OFF » n'est pas strictement
   inerte hors grab.

## Verdict
**`GRAB_HARMS_VIA_CARRY_TAX__NO_DOSE_RESPONSE__N_INDEPENDENT_IS_2`** — bloquer le grab augmente la survie,
et le forcer la dégrade (8/8, sign_p = 0.0078) : la causalité est établie **bidirectionnellement** et
réplique en production. Le mécanisme est la **taxe de portage cumulative** (`carry_weight × 0.5`/tick), pas
le coût du geste. Mais **aucune dose-réponse au taux de grab n'est établie**, le contrôle négatif de la 1re
passe était sans valeur, et le design ne porte que **2 réplicats indépendants**.

## Amendements
**À [[EDR-WARM-005]]** : le phénomène est réel et réplique, mais (i) son **mécanisme** est la taxe de
portage, pas le coût du canal ; (ii) son chiffre **×2.06 n'est PAS répliqué** — ces génomes font 3000 epochs
contre 18 000, la médiane des répondeurs est 1.69, elle-même gonflée de 10-33 % par le découplage ;
(iii) son ablation utilisait le même idiome bugué (aliasing), donc son attribution mécaniste n'avait jamais
été isolée — elle l'est ici, mais pour d'autres génomes.

**À [[EDR-WARM-006]]** : sa conclusion « le canal libre est distribué par l'INITIALISATION, pas par
l'entraînement » est **RÉFUTÉE** — |final − birth| médian = **0.557**, plusieurs agents traversent OFF↔ON
(seed 7/6 : −0.716 → +0.433). WARM-006 avait généralisé depuis `agents[0]`, **exactement l'erreur qu'il
reprochait à WARM-005** : cet agent est saturé au plafond de tanh, donc le seul qui ne PEUT pas bouger.
Ce qui tient de WARM-006 : il n'y a pas eu de dérive **chez l'agent 0** (Δ = −0.011, reproduit), et
l'erreur d'unité d'analyse qu'il documente.

## Corrections apportées par [[EDR-WARM-008]]
* 🛑 **« la sonde oracle CLASSE LES AGENTS À L'ENVERS » est une SUR-GÉNÉRALISATION** (énoncé plus haut à
  partir de 3 cas saillants). Mesuré sur les mêmes données : `spearman(oracle, in-world) = +0.819`, avec
  **0 faux-POSITIF et 3 faux-NÉGATIFS**. C'est un mode d'échec **UNILATÉRAL** — la sonde oracle *rate* des
  grabbers, elle n'en *invente* pas. Elle reste inadaptée pour classer, mais l'inversion annoncée est
  fausse. Troisième occurrence dans cet arc de la même faute : généraliser depuis un petit échantillon.
* 🔒 **BORNE DE PORTÉE : « le grab nuit » n'est établi que dans un monde où grabber n'a AUCUN avantage
  possible.** Le banc engendre `stick ×2, stick_short ×3, stick_long ×1, rock ×18` et **AUCUN `Fruit`** —
  or le revenu +20 exige `item_type == "Fruit"` (`world:746-749`). L'inventaire y est donc un **coût pur
  par construction**, et « grab nuit » quasi-tautologique. Une tentative de bras `cognitive_demand=False`
  (WARM-009, run NUL) place les 24 génomes à **6.0-7.2 ticks sans exception** (plancher de famine) : le
  bras était structurellement INCAPABLE de montrer l'inverse. **La validité externe reste OUVERTE.**
* ⚠️ **La chaîne causale de ce record NE TRAVERSE PAS les populations.** WARM-008 a mesuré le gain de
  survie d'une suppression du grab sur une population **bootstrap-oracle** : **NUL** (ratio 1.000, 6
  améliorés / 6 dégradés). Cause : la taxe de portage n'y pèse que **2.4-9.5 % du métabolisme**, contre le
  génome **DAgger à inventaire lourd** étudié ici. Le mécanisme est réel ; son AMPLEUR dépend entièrement
  du poids porté, donc de la population. Ne pas inférer un gain de survie hors des populations mesurées.

## Portée & limites
* **n indépendant = 2 seeds** pour l'analyse PAR AGENT menée ici. ⚠️ **Portée corrigée après audit** :
  j'avais annoncé que ce défaut touchait tout le dépôt — **c'est faux**. `ablation_verdict` documente son
  entrée comme « survies appariées par **ère/seed** » et tous les bancs agrègent d'abord les agents
  (`era_survival.append(np.median(ages))`), soit une valeur par ère, chaque ère tirant un monde distinct.
  **L'unité de réplication du projet est l'ère/le seed — l'idiome est SAIN.** Le défaut est local à
  l'analyse par agent de ce record. Cf. [[pseudo-replication-12-agents]] (alerte rétractée).
* Ratios **bornes inférieures** pour les agents censurés à `max_ticks = 200`.
* La dose-réponse n'est pas réfutée, elle n'est **pas établie** : le plancher la masque et le design manque
  de puissance intra-répondeurs.

## Leviers suivants
1. ~~Chantier pseudo-réplication transversal~~ — **AUDIT FAIT, SANS OBJET** : l'idiome du projet réplique
   sur l'ère/le seed, pas sur l'agent. Cf. [[pseudo-replication-12-agents]] (alerte rétractée).
2. Panel correctif si l'on veut le chiffre : 4 bras (intact / grab_off / **sham_node20** / **force_grab_on**)
   en forward PRODUCTION, `max_ticks ≥ 600` pour dé-censurer, ≥6 seeds à entraînement DAgger séparé et
   mondes d'évaluation par agent (`seed_at(seed*1000+agent, i)`), dose = intégrale de portage,
   test pré-enregistré intra-répondeurs.
3. Levier 2 de WARM-005 : valider `aux_off_weight` bout-en-bout à budget borné.

## Leçons méthodologiques (transférables)
* **Un contrôle négatif qui ne peut pas échouer n'est pas un contrôle.** Si l'ablation porte sur une action
  que le sujet n'exécute pas, le no-op est analytique. Le contrôle informatif est la manipulation
  **inverse** (forcer l'action chez ceux qui ne la font pas).
* **Un contrôle sham doit reproduire la VOIE de l'artefact suspecté**, pas seulement « ne rien faire » :
  ici, clamper un nœud non lu *via la même vue aliasée* est ce qui a prouvé que le bug était inerte.
* **Vérifier l'aliasing mémoire avant de déclarer une ablation propre.** Argmax et ε-greedy avaient été
  vérifiés ; `np.shares_memory` ne l'avait pas été.

Converge [[EDR-WARM-005]] et [[EDR-WARM-006]] (qu'il amende tous deux), [[power-evaporation-guardrail]],
[[unit-of-analysis-population-vs-replicate]], [[pseudo-replication-12-agents]], REF-DEMAND-MARKER.
