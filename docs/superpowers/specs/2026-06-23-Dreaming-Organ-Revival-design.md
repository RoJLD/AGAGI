# Design — Réveil de l'organe de planification par l'énergie (sonde de dreaming)

Date : 2026-06-23
Étape 4 (attaque du goulot d'exploration, EDR 014), approche A. **Diagnostic d'abord.**

## Contexte

EDR 091 a établi que la compétence-cible du curriculum est bloquée à deux couches : (1) survie,
résolue par le sweet spot énergie (EDR 085, `base_metabolism=0.25`/`forage_payoff=3` → survie ×4) ;
(2) **signal d'autel/outil NUL** même à vie longue = le goulot d'exploration d'EDR 014, le mur
central non résolu. Sur 5877 agents historiques : `altars_solved=0`, `total_dreams=0` —
**l'organe de planification (MCTS/dreaming) est 100 % dormant.**

Insight diagnostic (cette session) : le dreaming est gated par
`has_mcts (organ_genes[0]) & do_dream_logit>0.1 & surprise_momentum>0.05`
(`src/agents/mamba_agent.py:501-505`), **mais porter l'organe MCTS coûte `+0.5` de drain
énergétique/tick** (`mamba_agent.py:42-43`). Hypothèse : en régime létal (défaut historique,
extinction ~50 ticks), tout porteur de l'organe meurt plus vite → l'évolution **sélectionne CONTRE**
l'organe. Au sweet spot (survie ×4), l'organe pourrait redevenir abordable. Pont testable
EDR 085 ↔ EDR 014.

Fait de substrat (confirmé) : `Genome.organ_genes = [enable_mcts, enable_symbolic_memory]`, défaut
`[False, False]` (`src/seed_ai/mutation.py:28,41`). L'organe n'apparaît que par mutation
(flip aléatoire, `mutation.py:273-274`). Donc la prévalence part de ~0 ; mesurer la pression de
sélection exige de **semer** l'organe à une fraction connue, pas d'attendre la mutation.

## Objectif — une échelle de succès (4 barreaux)

L'utilisateur veut les quatre critères, dans l'ordre de dépendance ; on monte tant que ça paye :

0. **Diagnostic** : pourquoi l'exploration/le dreaming échoue (CE livrable).
1. **L'organe dreaming s'active et paye** (`total_dreams>0` stable ET les rêveurs font mieux).
2. **La compétence-autels quitte le plancher** (`industrial_competence` > 0.15).
3. **Craft/autels per-capita ↑ robuste multi-seed** (au-dessus du plateau historique).

Les barreaux 1-3 ne se conçoivent qu'APRÈS le résultat du barreau 0 (ils dépendent de ce qu'il
révèle). **Périmètre de CE design : barreau 0 uniquement.**

## Architecture — sonde de dreaming (barreau 0)

`tools/dreaming_probe.py`, dans l'esprit de `tools/target_competence_probe.py` (déterministe,
appariée seedée, provenance Harness, quiet-log). Deux questions ORTHOGONALES, deux mesures — pour
ne jamais confondre « l'organe disparaît » et « l'organe est inutile ».

### Q1 — l'organe SURVIT-il à la sélection ? (pression énergétique)

Mesure la pression de sélection sur l'organe selon le régime énergétique.

- Pour K seeds, à **deux régimes** (sweet `0.25/3` vs létal `1.0/1.0`) : initialiser une population
  où **la moitié porte `organ_genes[0]=True`** (l'autre False), via `init_primordial_soup` puis
  `genome.organ_genes[0] = (i < n/2)`.
- Faire tourner UNE ère (jusqu'à extinction ou `max_ticks`). Signal primaire = **mortalité
  différentielle** : si l'organe (`+0.5` drain) tue plus vite, les survivants en porteront moins.
  (La reproduction intra-ère du biosphere amplifie le signal mais n'est pas requise pour le lire.)
- Mesurer la **prévalence de l'organe parmi les SURVIVANTS** à la fin : `frac_surv = #(organ_genes[0]
  vivants) / #vivants`, comparée à `frac_init = 0.5`. (Rapporter aussi la prévalence sur survivants+
  morts, secondaire.)
- **Lecture** : `Δprev = frac_surv − 0.5`. Au létal on attend `Δprev < 0` (organe purgé par
  surmortalité) ; au sweet spot `Δprev ≳ 0` (organe toléré). L'écart `pressure = Δprev_sweet −
  Δprev_lethal` = la pression énergétique nette sur l'organe.

### Q2 — l'organe PAYE-t-il quand il est présent ?

Isole le bénéfice de l'organe de sa survie. Au **sweet spot** (sinon Q1 le tue avant de voir Q2).

- (a) **Intra-population, forcé-ON** : initialiser TOUTE la population avec `organ_genes[0]=True`,
  faire tourner l'ère, puis comparer survie/compétence des agents ayant **réellement rêvé**
  (`total_dreams>0`) vs ceux n'ayant pas rêvé. Mesure : médianes appariées, delta.
- (b) **Apparié ON vs OFF** : deux ères au même seed, l'une toute-ON, l'autre toute-OFF ; comparer
  la compétence (survie) de population. Mesure : ratio C_on / C_off par seed → médiane + signe.

### Sortie

Verdict structuré (provenance ledger via `Harness.save`) :
```
{ "q1": {"delta_prev_sweet": ..., "delta_prev_lethal": ..., "pressure": sweet−lethal},
  "q2a": {"dreamers_competence": ..., "nondreamers_competence": ..., "delta": ...,
          "total_dreams_seen": ...},
  "q2b": {"median_ratio_on_off": ..., "n_favorable": ..., "sign_p": ...},
  "verdict": "SURVIT_ET_PAYE" | "SURVIT_PAS_PAYE" | "PAYE_PAS_SURVIT" | "MORT",
  "per_seed": [...], "config": {...} }
```

### Logique de gate (l'échelle)

| Q1 survit | Q2 paye | Verdict | Action (barreau suivant) |
|---|---|---|---|
| non | non | MORT | organe mort sur ce substrat → escalade levier I (nouveauté) / II (auto-craft) |
| oui | non | SURVIT_PAS_PAYE | organe présent mais inutile (World Model faible / surprise saturée) → réparer la planification |
| non | oui | PAYE_PAS_SURVIT | myopie de sélection → scaffold léger (protéger/semer l'organe) |
| oui | oui | SURVIT_ET_PAYE | **monter** : concevoir barreaux 1-3 (le dreaming ravivé fait-il résoudre des autels ?) |

## Composants & interfaces

- `tools/dreaming_probe.py` — orchestration + `main()` (env knobs), réutilise :
  `SeedManager.seed_boundary`, `Harness.save`, `async_logger` (+ `AGISEED_QUIET_LOG`),
  `_prepare_world(deterministic=True)`, `init_primordial_soup`, `MambaAgent`,
  `survival_competence`. Énergie via `WorldConfig.base_metabolism/forage_payoff`.
- Helper pur `organ_prevalence(agents) -> float` (fraction portant `organ_genes[0]`), testable
  sans biosphère.
- Helper pur `q2_split(stats) -> (comp_dreamers, comp_nondreamers, delta)` sur les stats d'agents
  (incluant `total_dreams`), testable sans biosphère.
- Fonctions de verdict pures (réutiliser `_sign_test_p` de `curriculum_transfer` ou le ré-exposer).

Knobs env : `DP_MODE` (q1|q2|both, défaut both), `DP_SEEDS`, `DP_K`, `DP_NUM_AGENTS`,
`DP_MAX_TICKS`, `DP_METAB`/`DP_PAYOFF` (sweet par défaut ; q1 balaie sweet+létal).

## Garde-fous anti-théâtre

- **Séparation forcé-ON vs évolué** : Q1 (sélection) et Q2 (bénéfice) mesurés séparément — ne jamais
  conclure « l'organe aide » à partir d'une corrélation prévalence↔succès confondue.
- Seeds **appariés**, déterministe (memory_retriever stop+clear, verrou repro Dev #3), provenance.
- **Rapporter la décomposition** (prévalence, nb de rêves, delta rêveurs/non-rêveurs), jamais un
  scalaire nu. Si `total_dreams_seen == 0` même forcé-ON, le dreaming est bloqué en AVAL de l'organe
  (do_dream_logit ou surprise) — résultat distinct et précieux.
- Verdict **falsifiable** : seuils explicites, sous-puissance signalée (n petit → sign_p rapporté).

## Hors périmètre (YAGNI)

- Barreaux 1-3 (réparation effective : scaffold organe, World Model par-agent, curriculum de
  sous-compétences) — conçus seulement après le verdict du barreau 0.
- Toute modification du moteur (mutation, énergie, mamba_agent) : la sonde n'**observe**, ne répare
  pas. Si elle doit forcer `organ_genes`, c'est sur des génomes locaux, pas un changement de prod.

## Tests

- `organ_prevalence` : fractions connues (tout-ON=1.0, tout-OFF=0.0, moitié=0.5, liste vide=0.0).
- `q2_split` : rêveurs/non-rêveurs séparés correctement, delta signé, cas zéro-rêveur.
- Verdict : table de gate (les 4 cas → 4 verdicts) sur entrées synthétiques.
- Smoke biosphère minimal (1 seed, max_ticks court) hors CI (marqué sandbox).
