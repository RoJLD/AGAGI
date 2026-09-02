---
id: SDR-G2
type: SDR
title: L'agent compose-t-il
status: open
gate: G2
motivates: [EDR-S2-008, EDR-BILINEAR, EDR-RETAIN-COMPOSE, EDR-RETAIN-COMPOSE-LR, EDR-117, EDR-119, EDR-120, EDR-122, EDR-126, EDR-127, EDR-128, EDR-129, EDR-131, EDR-132, EDR-133, EDR-136, EDR-146, EDR-147, EDR-148, EDR-149, EDR-158, EDR-159, EDR-160, EDR-161, EDR-LOCK-001]
---
# SDR-G2 — Composition (l'agent enchaîne means→ends)

**Hypothèse falsifiable** : un agent peut CONDITIONNER une action terminale (« ends ») sur une
précondition qu'il a lui-même accomplie (« means ») — binding P(Y|X) ≫ P(Y|¬X) — et cette capacité
peut ÉMERGER sous le seul signal du monde, sans que la structure ou la réponse lui soit fournie.
La porte se juge à DEUX niveaux qui ne se confondent pas : le proxy dit ce que le substrat SAIT
faire quand on route le crédit ; le fort dit ce qui ÉMERGE quand on ne le route pas. Confondre les
deux serait mentir sur ce qui manque.

*(Porte re-scellée le 2026-09-02 — elle était un FANTÔME : `motivates: []`, critère narratif ;
cartographie T1. Draft par panel adversarial, 2 fatales corrigées avant gravure.)*

## Niveau 1 — G2-proxy (CAPACITÉ, crédit supervisé/épisodique) : **FRANCHI**

KPI : `binding_gap = P(Y | X accompli) − P(Y | ¬X)`, mesuré en fin d'entraînement, `hit_end`
co-rapporté (un gap par SUPPRESSION coûteuse n'est pas du binding : bras gate-seule d'EDR-136,
hit 0.477).

**Critère exécutable** (les deux issues atteignables, démontrées dans les MÊMES runs) :
- POSITIF : `binding_gap_end > 0.30` — le seuil est le `bind_thresh=0.30` du banc
  (`tools/substrate_ab_compositional.py:585` et suiv.), CELUI qui a produit les comptes cités —
  ET `hit_end` préservé ET contrôle positif `oracle` (gap 1.000) ET contrôle négatif `none`
  (gap ~0.07-0.09, jamais > 0.2) dans le même protocole. Atteint : EDR-129 (7/10),
  **EDR-136 (10/10, gate + anti-saturation, P(Y|X) 0.85-0.99, P(Y|¬X)→0.016, dose-réponse à
  optimum)**, porté en substrat prod par EDR-158/159 (+0.298 ; gate auto-scopé +0.232).
- NÉGATIF atteignable, démontré : `none+pen6` 0/10 (EDR-136) ; chemin TD différé +0.000
  (EDR-148) ; BPTT dégrade le gate (EDR-146/147).
- Le verdict inter-bras passe par `compute_ab_verdict` (`tools/substrate_ab.py`, CALIBRÉ, garde
  `sign_p` — ne pas modifier). ⚠️ **Deux grandeurs à ne pas confondre** : le plafond structurel
  0.3889 (P2.15) est une ACCURACY de tâche du plain (et la barre `1/K+0.15` est 0.072 dessous —
  dette de seuil ouverte) ; le 0.30 ci-dessus est un GAP de probabilités conditionnelles —
  incommensurables. Le « plafond » pertinent du gap est le bras `none` (~0.07-0.09) et le mode
  suppression (couvert par la clause `hit_end`).
- Étage représentationnel : `run_bilinear_composition_probe` (`tools/bilinear_composition_probe.py`,
  CALIBRÉ — `same_tick:positive` / `two_step:lr_artifact` / `recall:noop`) — séparation totale
  plain/bilinéaire 0/144 (EDR-BILINEAR).
- **Garde E19 obligatoire** : tout futur verdict NUL en régime 2-pas passe
  `assert_verdict_invariant_to_optimizer` (CALIBRÉ) — née de la rétractation EDR-RETAIN-COMPOSE
  (le « mur de rétention » était un artefact de lr : 0.173→0.923).

**✅ Dette d'instrument LEVÉE le 2026-09-02, le jour même de son constat** — les 10 orchestrateurs
du banc (`compare_curriculum`, `compare_curriculum_fade`, `compare_gate_modes`, les 5 `sweep_gate_*`
/ `sweep_y_saturation` / `sweep_overtraining_stability` / `sweep_binding_penalty`,
`probe_collapse_predictors`) étaient invisibles au cliquet (6ᵉ angle mort : les verbes
`compare_`/`sweep_`/`probe_` en TÊTE de nom n'étaient couverts que précédés de `run_`). Détecteur
élargi (+22 fonctions, coût compté avant application) et banc CALIBRÉ par **injection à dose
connue** : chaque verdict de cette porte est confronté à une réponse connue, branches NÉGATIVES
incluses (`BINDING_FORCED`/`SUPPRESSION`/`SIGNAL_INSUFFICIENT` · `GATE_BINDS`/`GATE_COLLAPSES`/
`GATE_INTERMITTENT` · `ANTISAT_RESCUES`/`NEUTRAL`/`INEFFECTIVE` — ces deux derniers ne disent PAS la
même chose et le test les sépare · `RECIPE_ROBUST`/`BINDING_EROSION` · gardes `WARMUP_FAILED` et
`FADE_INEFFECTIVE` qui priment sur les chiffres aval). Le cliquet reste STRICT (139 détectés / 138
calibrés / 0 dette). **Les runs proxy de niveau 1 sont DÉBLOQUÉS.**

## Niveau 2 — G2-fort (ÉMERGENCE in-loop, non supervisée) : **NON FRANCHI — c'est le mur EDR-LOCK-001**

La demande existe : la survie in-world EXIGE la composition (EDR-S2-008, ablation de MODULE,
ratio 8.45 dans la cellule corps-insuffisant + chaîne ≥ 2 + devise-énergie ; 3 cellules contrôle
à 1.00). Ce qui manque est l'ÉMERGENCE de la capacité sous ce signal.

KPI : `comp_rate` (taux de séquences means→ends complétées) du bras SANS capacité fournie (sans
gate, sans curriculum ciblé, sans oracle), sous sweep de demande `d` — instrument d'EDR-161
(`compositional_world_probe.py`). ⚠️ **Le niveau 2 reste BLOQUÉ, lui** : son producteur `run_world` appartient à la famille `run_\w+` générique, NON couverte par le détecteur — l'élargir ajouterait +56 fonctions non calibrées (chiffré au backlog). Avant tout run de niveau 2 : calibrer `run_world` (injection à dose connue sur son agrégation `adv`).

**Critère exécutable** :
- POSITIF : `comp_rate` du bras nu à d ≥ 1 SÉPARÉ du bras nu à d = 0, apparié par seed, jugé par
  `compute_ab_verdict` (garde `sign_p`) — pas un « décollage » à l'œil.
- NÉGATIF : pas de séparation — l'issue MESURÉE aujourd'hui (OFF plat ~0.03, EDR-161).
- Les deux issues atteignables par construction : le bras capacité-fournie MONTE sur le même
  instrument (comp_rate ON 0.01→0.17, EDR-161) — l'instrument SAIT voir la montée.
- **Garde anti-négatif-fabriqué (obligatoire pour tout run futur)** : le bras ON est CO-EXÉCUTÉ
  dans le même run (`assert_positive_control`) — dans un dépôt au biais négatif mesuré, un OFF
  plat sans ON-qui-monte co-mesuré est ininterprétable ; le contrôle positif historique d'EDR-161
  ne protège pas un run de 2027.

**État du mur** ([[EDR-LOCK-001]]) : « écriture apprise » ≡ « émergence composée » ≡ « régime de
recherche » = un seul verrou. Prédiction falsifiable : un levier qui perce l'un perce les autres
(warm-start = candidat, loi transversale).

## Règle de statut

`status: validated` ne sera posé QUE sur franchissement de **G2-fort** (un EDR `status: validated`
portant `tests: [SDR-G2]` et satisfaisant le critère du niveau 2). Le proxy est le PLANCHER gravé
de la porte, pas sa validation : EDR-136 est déjà `status: validated` et teste cette SDR — le
graphe PERMETTRAIT de la valider ; ce serait mentir sur ce qui manque.

## Accrétion (horodatée)

- **2026-06/07 (117→126)** : élimination — ni la taille (119), ni la mémoire (120, AUC 0.90) ;
  binding ABSENT en mesure directe (126). *(Ids 126 ET 129 : collisions légataires baselinées —
  deux fichiers chacun ; les entrées `motivates` visent les fichiers compositionnels.)*
- **2026-07 (128→136)** : premier levier positif = gate structurel (129, 7/10) ; queue = bassin
  d'optim précoce (131/132/133) ; **recette 10/10 = gate + anti-saturation (136)**. Réfutés :
  signal seul (128), warm-start seul (132), readout additif non-linéaire (133).
- **2026-07/08 (146→149)** : BPTT n'aide pas et dégrade le gate ; TD prod ne porte pas la recette ;
  robuste au sur-entraînement.
- **2026-08-03 (EDR-BILINEAR)** : mur REPRÉSENTATIONNEL levé — plain 0.271 vs bilinéaire 0.932,
  0/144 ; plafond plain 0.3889 en forme close.
- **2026-08-04 (EDR-RETAIN-COMPOSE, rétracté par -LR)** : verdict RETENTION RETIRÉ (artefact de
  lr) ; fonde E19.
- **2026-08 (158/159/160/161)** : migration prod livrée ; gate auto-scopé depuis H ; l'additif
  reste la primitive ; **la capacité PAIE sous demande (adv +0.009→+0.212)**.
- **2026-08 (EDR-S2-008)** : le monde EXIGE la composition (ratio 8.45).
- **2026-09-02** : porte re-scellée ; critère proxy/fort ci-dessus ; proxy FRANCHI, fort OUVERT.
  EDR-127 (craft atteint, non retenu) rattaché : matière G2, record toléré sans frontmatter.
