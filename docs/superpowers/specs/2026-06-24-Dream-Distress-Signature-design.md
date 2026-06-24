# Design — Signature de détresse du dreaming (Phase 1-A, corrélationnel)

Date : 2026-06-24
Suite d'EDR 093 : trancher le paradoxe Q2a (les agents qui rêvent font PIRE). Approche **1-A**
(corrélationnel, cheap, sans toucher le moteur). **Diagnostic d'abord.**

## Contexte

EDR 093 (sonde de dreaming, barreau 0) : la population *portant* l'organe MCTS survit ~9% mieux
(q2b 1.087) MAIS les agents qui *rêvent effectivement* ont une compétence-survie PLUS BASSE que les
non-rêveurs de la même population (q2a −0.040). Le dreaming est **auto-sélectionné** : `do_dream` est
un logit décidé par l'agent (`mamba_agent.py:492`), gated par
`has_mcts & do_dream>0.1 & surprise_momentum>0.05` (`:496-504`). Donc « les rêveurs font pire » peut
signifier soit « rêver nuit » (cause), soit « les agents en détresse choisissent de rêver » (corrélat).

Plan global (3 phases, validé) : **1-A** signature de détresse corrélationnelle (CE design) →
**1-B** (hook moteur d'émission au rêve) seulement si 1-A ambigu → **2** intervention causale
(`force_dream` gated, ON/OFF forcé à organe constant). Phase 1-A oriente ; **seule la Phase 2
tranche causalement**.

## Question (Phase 1-A)

Les rêves se concentrent-ils chez les agents **proches de la mort** (signature de détresse :
le rêve corrèle à la mort imminente) ? Si oui → l'hypothèse « corrélat de détresse » est plausible
et la Phase 2 (causale) est justifiée. Si non (les long-vivants rêvent autant ou plus) → le dreaming
n'est pas un signal de détresse, autre explication à chercher.

## Architecture

`tools/dream_distress_probe.py`, dans le moule de `tools/dreaming_probe.py` (déterministe, apparié
seedé, provenance Harness, quiet-log). **Réutilise `run_era_organ`** (livrée, EDR 092) avec
`organ_fraction=1.0` → population entièrement organe-ON ; renvoie par agent (tous, vivants + morts)
`{age, total_dreams, has_organ}`.

Logique : par seed, une ère organe-ON au sweet spot → on calcule le **taux de rêve** par agent et on
compare les **court-vivants** aux **long-vivants**.

## Composants & interfaces (helpers PURS, testables sans biosphère)

- `dream_rate(agent: dict) -> float` = `total_dreams / max(age, 1)` (taux ajusté à l'exposition ;
  age 0 → dénominateur 1 → 0.0 si pas de rêve).
- `distress_split(stats: list[dict], age_floor: int = 10) -> dict` : filtre `age >= age_floor`
  (écarte l'artefact petit-âge : un agent mort à 2 ticks avec 1 rêve aurait un taux 0.5 trompeur),
  split par **âge médian** du sous-ensemble filtré, renvoie
  `{rate_short, rate_long, delta, n_short, n_long}` où `rate_*` = médiane de `dream_rate` du groupe
  et `delta = rate_short − rate_long` (>0 = court-vivants rêvent plus = détresse).
- `distress_verdict(deltas: list[float], delta_eps: float = 0.0) -> dict` : agrège sur seeds →
  `{median_delta, n_favorable, sign_p, verdict}`. `n_favorable` = nombre de `delta > 0` (tous) ;
  `sign_p = _sign_test_p(#(delta>0 parmi delta≠0), #(delta≠0))` (pattern `compute_transfer_verdict`,
  réutilisé de `tools.curriculum_transfer`, évite `k>n` — cf. revue finale EDR 092). `verdict` ∈
  {`DETRESSE` (median_delta > delta_eps ET sign_p < 0.1), `BENEFIQUE` (median_delta < −delta_eps ET
  sign_p < 0.1), `NEUTRE` sinon}.
- `run_distress(seeds, target, num_agents, max_ticks, shared_db) -> dict` : par seed, `run_era_organ`
  (organ_fraction=1.0, sweet 0.25/3) → `distress_split` → collecte `delta` ; renvoie verdict +
  per-seed.
- `main()` : env knobs `DD_TARGET`/`DD_SEEDS`/`DD_NUM_AGENTS`/`DD_MAX_TICKS` ; pose
  `AGISEED_QUIET_LOG=1` AVANT `async_logger.start()` ; provenance via `Harness.save`.

## Garde-fous anti-théâtre

- **Corrélationnel et ORIENTANT, pas définitif** : le design l'affirme ; la Phase 2 (causale) tranche.
  Le verdict `DETRESSE` ne prouve PAS que le rêve nuit — il motive l'intervention causale.
- Confondants signalés et traités : (a) **artefact petit-âge** → filtre `age >= age_floor` ;
  (b) **exposition** → ratio `dreams/age`. Confondant résiduel (les deux groupes diffèrent par
  d'autres traits) → assumé, c'est pourquoi la Phase 2 existe.
- Décomposition rapportée (rate_short/long, n_short/long, per-seed `delta`), jamais le label nu.
- Seeds appariés, déterministe (memory_retriever neutralisé via `run_era_organ`), provenance ledger.
- Sous-puissance signalée (n petit → `sign_p` rapporté).

## Hors périmètre (YAGNI)

- Phase 1-B (hook moteur d'émission au rêve) : seulement si 1-A est ambigu (NEUTRE non concluant).
- Phase 2 (intervention causale `force_dream`) : conçue après le résultat de 1-A.
- Aucune modification de `src/` : la sonde réutilise `run_era_organ`, n'observe pas ne modifie pas
  le moteur.

## Tests

- `dream_rate` : `{age:10,total_dreams:5}` → 0.5 ; `{age:0,total_dreams:0}` → 0.0 ;
  `{age:200,total_dreams:10}` → 0.05.
- `distress_split` : population synthétique où les court-vivants rêvent plus → `delta > 0` ; filtre
  `age_floor` écarte un agent âge 2 ; groupes vides → 0.0 sans crash.
- `distress_verdict` : 3 cas (DETRESSE / BENEFIQUE / NEUTRE) sur deltas synthétiques + sign_p.
- `main` provenance : monkeypatch `run_distress` + async_logger + `_acquire_shared_db`, vérifie
  fichier `results/dream_distress_*.json` avec `verdict`, `commit`, `git_dirty` ; isole la fuite
  d'env (`monkeypatch.setenv("AGISEED_QUIET_LOG","0")` avant `main()`, cf. leçon EDR 093).
