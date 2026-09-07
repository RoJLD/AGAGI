---
id: REF-DEMAND-MARKER
type: REF
title: "Témoin causal de demande — ablation within-subject de la capacité X"
status: active
adopt_for: [S2-001, LANG-006, G1-001, MEM-001, EDR-S2-002, EDR-S2-003, EDR-S2-004, EDR-S2-005, EDR-S2-006, EDR-S2-007, EDR-S2-008, EDR-S2-009, EDR-S2-010, EDR-S2-011, EDR-S2-012, EDR-S2-013, EDR-WARM-001, EDR-WARM-002, EDR-WARM-003, EDR-WARM-004, EDR-WARM-005, EDR-WARM-006, EDR-WARM-007, EDR-WARM-008, EDR-WARM-010, EDR-LANG-PERCEPTION, EDR-MEM-PERCEPTION, EDR-LANG-MEMORY, EDR-LANG-MEMORY-EDGE, EDR-LANG-MEMORY-EDGE-BIS, EDR-DELAYED-COORD, EDR-BILINEAR, EDR-RETAIN-COMPOSE, EDR-AUDIT-001, EDR-DREAM-001, EDR-EVO-002, EDR-EVO-005, CALIB-SP3]
---

## Énoncé
Le témoin CAUSAL de « la capacité X est-elle exigée / paie-t-elle » = **ablation WITHIN-subject de X**
sur le MÊME sujet (intact vs X neutralisé), PAS « un agent équipé de X réussit » (between-subject, qui
FAUX-POSITIVE : un survivant compétent peut exister dans un monde qui n'exige pas X).

## Prédiction validée (vérité-terrain)
- BETWEEN faux-positive sur les mondes TRIVIAUX (un survivant existe sans que X soit porteur).
- WITHIN tranche juste : effondrement SSI X est causalement porteur.
- ⚠️ **CE QUE LE MARQUEUR MESURE (corrigé le 2026-09-07, [[EDR-S6-FALLBACK-RATE]])** : une propriété
  du **SUJET, pas du MONDE**. L'ablation dit si CETTE politique a un repli survivable sans X — deux
  politiques également survivantes dans le MÊME monde rendent des verdicts opposés selon leur seule
  init. Mesuré : dans une cellule où le corps SUFFIT (donc X n'est pas nécessaire), l'ablation mord sur
  **8 seeds sur 12** dès que l'init n'est plus nulle, contre **0/12** à init nulle. Un `X_DECOY` ne dit
  donc PAS « le monde n'exige pas X » : il dit « ce sujet a un repli ». Corollaire pratique : publier
  l'init (ou la provenance du sujet) fait partie du verdict.
- ⚠️ **Le barreau `zero` produit des FAUX NÉGATIFS** (même record, 5 seeds mesurés) : obs à zéro rend la
  politique CONSTANTE ; si son action par défaut est le corps, le sujet survit au plafond et le barreau
  lit 1.00 pendant que `permuted` effondre 2,9× à 7,1×. **Préférer `permuted`** (obs réelle d'un autre
  tick : même distribution, information détruite) et publier les trois barreaux.
- **Condition de LISIBILITÉ (E14, [[EDR-AUDIT-001]])** : un within ≈ 1.0 n'est un NUL que si le bras
  intact est AU-DESSUS du plancher no-capacité de SON régime, déclaré par `floor=`. Sous le plancher,
  l'instrument rend `INCONCLUSIVE_DEGENERATE` — « illisible ici », PAS « pas de demande ». Mesuré en
  production sur soup ([[EDR-S2-013]] : intact 29.25 < plancher 32.0). ⚠️ Un plancher ne s'IMPORTE
  jamais d'un autre régime (E8) : `_floor_for` rend `None` hors de son point de mesure.
- Corroborant FAIBLE et ASYMÉTRIQUE : |W| → 0.000 quand X ne paie pas (S2-001), mais |W| élevé N'IMPLIQUE PAS la demande ([[EDR-S2-005]] : 0.909 en cellule NEUTRE). L'ablation prime ; |W| ne tranche JAMAIS seul.

## Implémentation de référence
`tools/demand_marker.py::ablation_verdict(intact, ablated, floor=, ceiling=,
intervention_verified=)` — ratio d'effondrement, garde-fou n<12 (bloque les TROIS verdicts), verdicts
`X_DEMANDED` / `X_DECOY` / `INCONCLUSIVE_INVERTED` (l'ablation AMÉLIORE ≥ 1.3× : un effet massif de
signe INVERSE n'est pas une inertie, E3) / `INCONCLUSIVE_DEGENERATE` (bras au plancher ou plafond
DÉCLARÉ, garde E14).

Gardes sœurs, toutes CALIBRÉES (`tests/sandbox/test_instrument_calibration.py`) :
`src/seed_ai/s2_stats.py::verdict_within_subject` + `s2_degeneracy` (arc S2 in-world) ;
`tools/language_memory_demand_probe.py::alias_guard_verdict` (SURGICAL / DEGENERATE_CONTROL — ablation
de SUBSTRAT, où `functional_aliasing='n/a'` est INTERDIT) ; `tools/check_agi_taxonomy.py` (porte du
graphe : `X_DEMANDED` + n≥12 + `specificity_control` **toujours** + aliasing + `coord_intact ≥
emergence_bar`).

## Modalités couvertes
| Modalité | Record | Ablation | Résultat |
|---|---|---|---|
| perception (proxy) | S2-001 | obs décorrélée | within tranche, between faux-positif |
| perception (in-world) | EDR-S2-002 + **EDR-S2-013** | permutation batch_obs, 5 mondes ; planchers clones-du-champion (`PLANCHER_NOPERC`) | within ≈ 1.0, mais **PERCEPTION_DECOY sur 4/5 mondes SEULEMENT** (au plus 3 indépendants : stoneage = industrial, S2-012) ; **soup ILLISIBLE** (`INCONCLUSIVE_DEGENERATE`, intact 29.25 < plancher 32.0 — la politique du champion vaut MOINS que le hasard à corps égal). Between 4.7-5.2× reste un faux-positif là où la ligne est lisible. |
| perception (ladder) | EDR-S2-003 | échelle permuted/noise/zero, 3 mondes | survie PERCEPTION-NEUTRE (même obs NULLE < 1.5×) ; PAS open-loop (comportement obs-dépendant 29% via contrefactuel //) |
| recette cognitive | EDR-S2-004 | grille corps×devise, sim survie | SENSIBLE SSI corps INSUFFISANT ET cognition payée en énergie (ratio ~10×, \|W\|0.93) ; sinon NEUTRE (\|W\|0.000) |
| recette mémoire | EDR-S2-005 | ablation mémoire, grille corps×rappel×devise | SENSIBLE SSI corps INSUFFISANT ET rappel DIFFÉRÉ ET énergie (ratio ~10×) ; **\|W\| faux-positive (0.909 neutre) → préférer l'ablation** |
| anticipation (MODULE) | EDR-S2-007 | ablation de MODULE (forward-model→identité) | SENSIBLE SSI corps INSUFFISANT ET dynamique (shift≠0) ET énergie (ratio ~16×) ; 1er jalon ablation-CALCUL (G4) |
| composition (MODULE) | EDR-S2-008 | ablation de MODULE (plan means→0), chaîne means→ends | SENSIBLE SSI corps INSUFFISANT ET chaîne≥2 ET énergie (ratio ~8×) ; 2e jalon ablation-CALCUL (G2) |
| **recette IN-WORLD** | EDR-S2-009 | flag cognitive_demand stoneage, oracle intact/ablé (par-agent) | **ON=PERCEPTION_DEMANDED (ratio 21×), OFF=NEUTRE → recette S2-006 RÉALISÉE in-world, flip S2-003.** ⚠️ signal GLOBAL défait l'ablation-permutation → canal PAR-AGENT requis |
| corps vs cognition (in-world) | EDR-S2-012 | grille 2×2 génome×politique, `RandomActionBatchModel`, 5 mondes K=12 | **BODY sur 4/5 mondes** (pas 5 : stoneage = industrial) ; la politique du champion est survival-négative ; le contrôle positif de `verdict_cognition_body` PASSE — le nul est donc INTERPRÉTABLE, ce que WARM-002 n'avait pas. « fitness-négative partout » → 2/5. Chiffres non re-dérivables (aucun artefact stocké). |
| canal parasite — amendements | EDR-WARM-006 → 007 → 008 | réanalyse de 24 génomes persistés, ablation `grab_off` within, manipulation INVERSE | 006 : pas de dérive (erreur d'unité d'analyse) ; 007 : causalité bidirectionnelle mais mécanisme = TAXE DE PORTAGE, `sign_p` pseudo-répliqué (n=2) ; 008 : `aux_off_weight` annule le grab (4/4) mais gain de survie NUL → un canal « libre » peut être fonctionnellement PORTEUR, et la chaîne causale ne traverse pas les populations. |
| paysage de fitness | EDR-WARM-010 | dose-réponse compétence partielle → survie, 12/12 ères par marche | **NON plat** (9 → 200, 22×, monotone) : le MÉCANISME de WARM-002 est réfuté, son échec empirique tient. Fournit le plancher 9.0 — mais sur agents FRAIS : il SOUS-GARDE, cf. S2-013 (clones du champion : 21.75-32.0). |
| **arêtes du graphe AGI-Taxonomy** | EDR-LANG-PERCEPTION, EDR-MEM-PERCEPTION, **EDR-LANG-MEMORY-EDGE-BIS** | ce marqueur EST le critère d'entrée (`tools/check_agi_taxonomy.py`) | 3 arêtes établies <!-- count:aretes_taxonomy=3 --> : language→perception 2.115, memory→perception 3.934 (ablation d'ENTRÉE), **language→memory 4.97 — première par ablation de SUBSTRAT**, et première REFUSÉE puis rouverte (la V1 a été bloquée par la garde d'alias : contrôle saturé au plafond). ⚠️ Portée : D=0 ; à D=2 la référence n'apprend pas ([[EDR-LOCK-001]]). |
| optim. imitation (in-world) | EDR-WARM-001 | génome imité par BPTT (forward torch), intact/ablé K=12 | **marqueur BASCULE PERCEPTION_DEMANDED dès acc_enseignant≈0.99 (ratio 1.6→2.1) MAIS survie plafonne 15 (oracle 200) à acc_enseignant 1.000 → dissociation : perception causale ✓, survie ✗. Mécanisme MESURÉ : acc on-policy plafonne 0.73 = transfert (dérive état récurrent), PAS covariate-shift des obs.** Usage : le marqueur mesure « utilise X », PAS « survit grâce à X » |
| optim. évolution (in-world) | EDR-WARM-002 | meilleur génome évolué W-only (forward mamba), intact/ablé K=12 | ratio ≈ 1.0 — ⚠️ **DÉGÉNÉRÉ, PAS NUL** : bras intact à 5.0-7.2 ticks, SOUS le plancher 9.0 mesuré (EDR-WARM-010). L'ancienne lecture « paysage de fitness PLAT » est réfutée ; `ablation_verdict` rendrait aujourd'hui `INCONCLUSIVE_DEGENERATE` |
| canal d'action parasite | EDR-WARM-005 | ablation within-subject d'un CANAL D'ACTION (grab force OFF), K=12 | **survie x2.06 (12/12 eres, sign_p=0.00024)** : un canal non supervise bloque ON saignait l'energie -> une part majeure du deficit de SURVIE de WARM-001/003/004 n'etait PAS cognitive (decision deja correcte a 98.7%). ⚠️ Lecon : avant d'expliquer un deficit de survie par la cognition, verifier le BILAN ENERGETIQUE et les canaux d'action NON SUPERVISES |
| diagnostic profondeur récurrente | EDR-WARM-004 | accuracy BINNÉE (tick / énergie), replay torch avec `reset_h_every` | **dégradation hors fenêtre entraînée SOLIDE (10/10 agents, sign_p=0.001, Δ médian 0.21) MAIS ce n'est ni couverture ni précision** : axe énergie COLINÉAIRE au tick (effet nul/inversé à tick contrôlé) ; signature MONO-CLASSE = frontière de décision dégradée par la PROFONDEUR RÉCURRENTE. ⚠️ **2 pièges d'instrument** : (1) deux axes corrélés donnent des magnitudes concordantes qu'on lit à tort comme corroboration (= double comptage) ; (2) un replay à H CONTINU ne reproduit pas l'in-world (où H est remis à 0 à chaque mort) → 0.112 d'artefact sur états identiques |
| optim. DAgger (in-world) | EDR-WARM-003 | génome DAgger on-policy (forward torch), intact/ablé K=12 | **ratio 5.04 PERCEPTION_DEMANDED (le plus fort de l'arc)** : DAgger lève la métrique acc_on-policy 0.73→0.99 (fenêtre survivable), survie 15→35 (×2.3), marqueur ×2.4 — MAIS survie < oracle, mécanisme résiduel OUVERT (couverture vs précision, `_inworld_accuracy` tronquée). ⚠️ Usage : cette acc est pré-mortem, pas l'horizon-tâche |
| communication | LANG-006 | canal coupé | MI 1.04 vs 0.000 |
| généralisation | G1-001 | θ ablaté | Δ0.83 causal |
| mémoire | MEM-001 | mémoire remise à 0 | effondre 6-8× |
