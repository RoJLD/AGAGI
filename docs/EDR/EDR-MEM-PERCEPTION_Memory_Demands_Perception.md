---
id: EDR-MEM-PERCEPTION
type: EDR
title: "Deuxième arête MESURÉE du graphe AGI-Taxonomy : la mémoire APPRISE demande la perception au rappel (DELAYED X_DEMANDED, ratio 3.93, n=12) — contrôle de spécificité PASSE après correction du confond d'entraînement du bras PRESENT (leurre découplé, ratio 0.98, inerte)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
SP-2 a gravé la 1ère arête (`language→perception`). Deuxième arête candidate : « memory demands perception » ?
La rétention APPRISE route-t-elle causalement par la perception ? On l'établit sur un proxy torch de rappel
différé (delayed-match-to-sample, sonde `tools/memory_perception_demand_probe.py`), par ablation d'ENTRÉE
within-subject à l'ENCODAGE (`derange_rows` sur le one-hot d'indice, in-distribution).

## Méthode
Delayed-match torch (MambaAgent, mémoire = état récurrent PORTÉ ; `learn_episode`, crédit du rappel).
Deux conditions : DELAYED (obs de test = zéros → il faut la rétention) ; PRESENT (contrôle de demande, obs de
test = vue directe BRUITÉE de l'indice, `flip_p`). `ablation_verdict` (floor=1/K), n=12 seeds,
`intervention_verified=True`. Sonde calibrée (memory oracle → effondre ; aléatoire → inerte,
`test_mp_oracle_memory_makes_perception_demanded` / `test_mp_random_memory_is_inert_no_false_demand`).

## Itération 1 : NULL apparent — spécificité en échec

Le premier run n=12 (K=6, D=2, lr=0.02, episodes=1200, n_agents=16, 372.5 s) donnait **DELAYED X_DEMANDED**
(ratio 3.934, intacte médiane 0.6547, ablée médiane 0.1664, 12/12 seeds séparés — signal net) mais
**`specificity_control` ÉCHOUAIT** : PRESENT collapsait LUI AUSSI sous ablation de l'encodage (verdict
X_DEMANDED au lieu de X_DECOY, ratio 4.329, exploré sur 15 configurations D/lr/flip_p/episodes sans jamais
approcher `decoy_ceiling=1.3`). Par construction du gate, l'arête n'était PAS gravée (cf. version précédente
de ce record, commit `d9da610`).

**Revue adversariale — cause identifiée (H1, confond d'entraînement, pas H2 fuite de substrat)** : dans le
design initial de la sonde, l'encodage PRESENT portait `cues` — LA MÊME information que la réponse — la
seule différence entre PRESENT et DELAYED étant la vue de test. Pendant l'entraînement, l'ablation n'existe
JAMAIS (elle n'intervient qu'à l'éval), donc le gradient n'a aucune raison de ne pas router via l'encodage
(source PARFAITE et disponible dès le premier tick) même quand la vue de test bruitée suffirait seule.
**Preuve quantitative (le smoking gun)** : à flip_p=0.3, la vue de test bruitée SEULE plafonne l'exactitude
atteignable à `(1-flip_p) + flip_p/K = 0.7 + 0.3/6 = 0.75` (proba de ne pas flipper + proba résiduelle de
deviner juste après flip). Or `present_intact` mesuré = **0.7609**, qui EXCÈDE ce plafond — impossible si
l'agent n'utilisait QUE la vue de test ; il exploitait nécessairement l'encodage retenu. Confirmé à un autre
point : à D=0/flip_p=0.2/episodes=3000, `present_intact` = **1.000** contre un plafond `(1-0.2)+0.2/6=0.833`
— écart encore plus net. Le contrôle PRESENT ne testait donc pas la spécificité de la mémoire ; il testait
un raccourci d'entraînement que l'ablation, en dérangeant CE raccourci, effondrait légitimement — ce n'est
pas une fuite structurelle du substrat récurrent, c'est un défaut de DESIGN du contrôle.

## Itération 2 : correctif — leurre PRESENT découplé de la réponse

**Correctif appliqué à `_seq_inputs`** (`tools/memory_perception_demand_probe.py`, commit `fa4b99b`) : en
PRESENT, l'indice ENCODÉ n'est plus `cues` mais un LEURRE aléatoire indépendant (`rng.randint(0, K, ...)`),
non corrélé à la réponse. La vue de TEST reste inchangée (vue bruitée de `cues`, `flip_p`). DELAYED est
INCHANGÉ (encode toujours `cues`, seule source d'information disponible). Avec l'encodage PRESENT rendu
non-informatif, le gradient d'entraînement n'a plus aucune raison de router par ce canal : l'agent apprend
à lire directement la vue de test → déranger l'encodage devient (en théorie) INERTE — exactement ce qu'un
contrôle de spécificité propre doit démontrer.

**Vérifications de non-régression** (avant le run n=12) : `pytest tests/test_memory_perception_probe.py -q`
(smoke de forme, 1 passed) ; `pytest tests/sandbox/test_instrument_calibration.py -k "mp_oracle or mp_random"
-q` (2 passed — les gardes de calibration bypassent l'agent et n'assertent QUE sur `delayed`, donc
insensibles au changement de PRESENT) ; `check_instrument_calibration.py` (0 nouveaux instruments non
calibrés). Smoke 3 seeds du correctif : `present` ratio chute de 4.329 (ancien) à **0.965** (nouveau, ≈1 =
inerte), confirmant la direction attendue avant d'engager le run n=12.

## Résultat (run n=12, mêmes hyperparamètres que l'itération 1 : K=6, D=2, lr=0.02, episodes=1200,
n_agents=16, provenance réelle `run_memory_perception_demand_probe`, `results/mem_perception_edge_accuracies.json`)

**DELAYED : X_DEMANDED**, ratio **3.934** (inchangé — DELAYED n'a pas été modifié par le correctif), n=12.
`delayed_intact` médiane **0.6547** (>> seuil vivant 1/K+0.15≈0.3167), `delayed_ablated` médiane **0.1664**
(≈ hasard 1/K=0.1667). Séparation **12/12 seeds** (intacte > ablée sur chaque seed, aucun recouvrement).

**PRESENT (contrôle de spécificité, leurre découplé) : X_DECOY, ratio 0.984 — INERTE.** `present_alive` =
True (médiane intacte 0.4844, dans la fenêtre vivante ]0.2167, 0.9[ — pas un plancher/plafond dégénéré,
en-dessous du plafond théorique 0.75 attendu pour une lecture parfaite de la vue de test seule, cohérent
avec un apprentissage imparfait mais suffisant pour rester VIVANT). `present_ablated` médiane 0.4922 —
QUASI IDENTIQUE à `present_intact` (0.4844), confirmant que déranger l'encodage-leurre ne change RIEN à la
performance : séparation intacte>ablée sur seulement 6/12 seeds (≈ hasard de comparaison, pas de collapse
systématique — signature attendue d'un bras INERTE, à comparer aux 12/12 systématiques de DELAYED).
`specificity_control = "pass"`. `functional_aliasing = "n/a"`.

**Gate d'ajout de l'arête** : `delayed==X_DEMANDED` ✓ ET `specificity_control=="pass"` ✓ ET `delayed_intact`
médiane (0.6547) > seuil (0.3167) ✓ → **AND global VRAI** → arête `memory → perception` GRAVÉE dans
`data/agi_taxonomy/demands.json` (2e arête, aux côtés de SP-2 `language→perception`).

## Interprétation
La mémoire APPRISE (état récurrent porté encode→délai→test) demande causalement la perception : déranger
la perception à l'encodage effondre le rappel différé (DELAYED) mais est SANS EFFET quand la réponse est
directement observable au test (PRESENT, une fois le contrôle débarrassé de son raccourci d'entraînement).
Le résultat négatif de l'itération 1 n'était donc pas un signal de fuite structurelle du substrat récurrent
(H2) — c'était un artefact du DESIGN du contrôle (H1), maintenant réfuté par construction : le même substrat
récurrent, la même ablation, le même mécanisme d'entraînement, produisent un contrôle PROPRE dès que
l'information exploitable par le raccourci est retirée du canal ablaté.

## Portée (bornée)
Proxy hors-monde (delayed-match), pas la biosphère. Mémoire = état récurrent APPRIS (pas la mémoire
tautologique de l'intégrateur numpy MEM-001, écartée à dessein). Coût borné (smoke 3 seeds + run n=12
plafonné, aucun run individuel > ~7 min mesuré). N'a modifié QUE `_seq_inputs` (le canal d'encodage
PRESENT) — DELAYED, le mécanisme d'ablation (`derange_rows`), la sonde oracle/random, et
`check_agi_taxonomy.py` sont inchangés. Accuracies réelles n=12 persistées dans
`results/mem_perception_edge_accuracies.json` (régénérées, appel direct et bloquant à
`run_memory_perception_demand_probe`, pas un pilote maison).

## Ce que ça débloque
Deuxième arête MESURÉE du graphe AGI-Taxonomy, et cas d'école méthodologique : un `specificity_control` qui
échoue n'est pas automatiquement une fuite de substrat (H2) — il peut être un artefact du DESIGN du contrôle
lui-même (H1, ici : l'encodage du bras de contrôle portait la réponse). La distinction se tranche par calcul
de PLAFOND théorique (ce qu'une lecture parfaite de la seule vue de test peut atteindre) contre la valeur
MESURÉE : un dépassement du plafond est la preuve directe d'un raccourci d'entraînement exploité, indépendante
de toute inspection de poids. Le correctif — découpler la cue encodée de la réponse dans le bras de contrôle
— est réutilisable pour toute future arête de mémoire construite sur ce même patron delayed-match.
Cf. `docs/superpowers/specs/2026-07-28-memory-perception-demand-edge-design.md`.
