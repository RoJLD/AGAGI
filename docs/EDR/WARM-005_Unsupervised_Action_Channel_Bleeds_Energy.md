---
id: EDR-WARM-005
type: EDR
title: "Le plateau de survie du DAgger vient (pour moitié) d'un CANAL D'ACTION non supervisé bloqué ON qui saigne l'énergie — pas d'un déficit de décision (98.7 % correct)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER]
---

## Question
WARM-003/004 ont dépensé beaucoup d'effort à expliquer pourquoi le génome DAgger plafonne à ~35 ticks
(transfert ? couverture ? précision ? profondeur récurrente ?). Mais une donnée n'avait jamais été
regardée : **le génome décide-t-il seulement mal ?** Et si ses décisions sont bonnes, **où part l'énergie ?**

## Méthode & chaîne de mesures
Chaque étape a réfuté ou précisé la précédente (génome DAgger persisté, re-diagnostic ~2 min).

1. **Hypothèse « pipeline d'action »** (`measure_action_pipeline`) : le monde modifie les logits APRÈS le
   forward — consensus social (`world_1_stoneage.py:1225`) puis pénalité anti-répétition (:1288-89,
   `logits[last_action] -= 0.1`) avant l'argmax (:1291). L'accuracy mesurée par `_inworld_accuracy` porte
   sur les logits BRUTS, pas sur l'action exécutée.
   → **RÉFUTÉE** : acc brute 0.988 vs acc **exécutée 0.987** (écart 0.002 ; flips 0.2 %). Le mécanisme
   existe exactement comme prédit (100 % des flips sont anti-répétition ET cassent une décision correcte)
   mais il est **négligeable**.
2. **Contradiction** : 98.7 % d'actions correctes, mais énergie en déclin monotone (80 → 28 à t=40),
   morts à énergie ≈ 0, delta/tick médian −1.10 et **max observé +0.77** — le `cog_gain=+12` semblait ne
   jamais tomber.
3. **Isolation dans le monde lui-même** (sous-classe instrumentant `_resolve_biology`) : la récompense
   **se déclenche bien** — delta_bio **−0.11 si correct** vs **−12.27 si faux** (écart = 12 ✓). Mais même
   parfaitement correct, **le bilan est négatif**.
4. **Comparaison ORACLE vs génome**, même récompense, bilans opposés :
   | | match(action==correct_dir) | delta_bio si correct | survie médiane |
   |---|---|---|---|
   | Oracle | 1.000 | **+0.583** | 120 (plafond), 10/12 vivants |
   | Génome DAgger | 0.987 | **−0.107** | 48, 0 vivant |
5. **Cause localisée** : le génome a le canal `grab` (nœud 24) **bloqué à ON sur 100 % des ticks**
   (logit +0.855) ; l'oracle sort **des zéros partout** sauf la direction (grab 0.000, jamais >0).
   `imitate_episode_bptt` ne supervisait que `out[:, :8]` (les mouvements).

## Résultat CAUSAL (le cœur du record)
Ablation **within-subject** (même génome, grab forcé OFF au forward), **K=12 ères** :

| bras | survies médianes par ère | médiane |
|---|---|---|
| grab INTACT (ON) | 48,30,34,34,32,38,46,35,45,36,52,35 | **35** |
| grab ABLATÉ (OFF) | 77,67,80,62,80,54,60,73,72,88,78,69 | **72** |

**12/12 ères améliorées, sign_p = 0.5¹² = 0.00024, ratio ×2.06**, `delta_bio(correct)` −0.246 → −0.075.
(Garde-fou projet n≥12 respecté ; test within-subject, pas between.)

## Verdict
**`UNSUPERVISED_ACTION_CHANNEL_BLEEDS_ENERGY_HALVING_SURVIVAL`** — une part majeure du « plateau de
survie » attribué par WARM-003/004 à des causes cognitives (transfert, couverture, profondeur récurrente)
est en réalité causée par un **canal d'action non supervisé bloqué en position ON**, qui draine l'énergie
en continu. **Le génome décidait juste à 98.7 % depuis le début** ; il ne mourait pas d'un déficit
cognitif. C'est un défaut du **dispositif expérimental** (objectif d'imitation incomplet), pas une
propriété du substrat ni du mécanisme de crédit.

## Correctif livré et son statut de validation
`imitate_episode_bptt(aux_off_weight=…)` ajoute une BCE poussant `grab` (24) ET `rub` (25) vers OFF —
comme l'oracle. Défaut 0.0 = comportement inchangé (rétro-compatible, 32 tests verts).
- ✅ **Le correctif agit sur le canal** : entraînement bootstrap-oracle, grab passe de −0.032 à **−0.986**,
  et l'accuracy de mouvement ne se dégrade pas (0.874 → **0.898**).
- ❌ **PAS de validation bout-en-bout.** ⚠️ **Et le bras de contrôle n'a PAS reproduit la panne** : sans
  supervision, dans ce bootstrap court, le grab reste à −0.032 (OFF), alors que le génome DAgger de
  WARM-003 est à +0.855 (ON). Donc « canal non supervisé ⇒ dérive vers ON » est **INCOMPLET** : la dérive
  provient de quelque chose de spécifique à la **boucle DAgger** (6 rounds, agrégation on-policy), pas de
  la simple absence de supervision. **Origine de la dérive = OUVERTE.**

## Amendements aux records antérieurs
Les lectures de **SURVIE** de [[EDR-WARM-001]], [[EDR-WARM-003]] et [[EDR-WARM-004]] doivent être lues avec
ce facteur : une part ~×2 du déficit de survie est imputable au canal parasite, pas à la cognition. Restent
INTACTS : les verdicts du marqueur (`PERCEPTION_DEMANDED`, ablation-perception within-subject), le finding
de [[EDR-WARM-002]] (paysage de fitness plat de l'évolution), et l'accuracy de décision elle-même.
En particulier, la « dégradation avec la profondeur récurrente » de WARM-004 reste mesurée (10/10,
sign_p=0.001) — mais son lien causal avec la SURVIE est désormais confondu par ce canal.

## Portée & limites
- L'ablation causale porte sur UN génome (celui de WARM-003), seed 2026, K=12 ères within-subject.
- Le grab n'explique pas tout : 35 → 72 en le coupant, mais l'oracle est à ~120-200 et `delta_bio(correct)`
  reste −0.075 (vs +0.583 pour l'oracle) → d'autres termes comportementaux restent non identifiés.
- Trois runs de validation end-to-end ont été ABANDONNÉS (4 h projetées, 89 min sans jalon). Cause
  structurelle instructive : **quand la survie augmente, les épisodes s'allongent et TOUT le pipeline
  ralentit** (collecte, BPTT sur trajectoires longues, mesures de survie). Tout design futur doit borner
  le coût (plafonner `max_ticks` pour les traces, réserver K=12 au verdict final) au lieu de laisser le
  coût suivre le succès.

## Leviers suivants
1. **Trouver l'origine de la dérive du grab dans la boucle DAgger** (comparer le logit 24 round par round).
2. Valider bout-en-bout `aux_off_weight` à budget borné.
3. Identifier les termes résiduels du bilan énergétique (−0.075 vs +0.583).

Converge [[EDR-WARM-001]], [[EDR-WARM-002]], [[EDR-WARM-003]], [[EDR-WARM-004]] (qu'il amende),
[[within-subject-demand-marker]], [[power-evaporation-guardrail]], REF-DEMAND-MARKER.
