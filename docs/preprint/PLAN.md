# Preprint MÉTHODO — plan de rédaction (démarré le 2026-09-16, zéro run)

> Décision ADR-004 (acceptée le 2026-09-16) : « preprint MÉTHODO maintenant ». Ce plan est la première pièce
> (spec §3, ligne « semaine 4 : plan + figures depuis les records existants, zéro run »). Règle d'écriture : **chaque
> chiffre du preprint est RECOMPUTÉ depuis un artefact du dépôt** (record, JSON de résultats, sortie d'un cliquet) et
> cite sa source — jamais recopié de mémoire (E8). Les chiffres ci-dessous portent leur commande de recompute.

## Titre de travail

*Un dépôt de recherche qui se contredit lui-même : calibration des instruments, cliquets exécutables et
pré-inscription scellée pour une biosphère artificielle — 300 records, un biais systématique vers le négatif, et ce qu'il
a fallu pour le voir.*

## Thèse (une phrase)

Dans un programme empirique long (300 records, ~2 600 tests), les erreurs qui comptent ne sont pas des erreurs de calcul
mais des **affirmations produites en l'absence de mesure** — et elles ont une DIRECTION : le négatif. Trois mécanismes
exécutables (calibration à réponse connue, cliquets à baseline gelée avec leur propre test de mutation, pré-inscription
scellée à lecture calibrée) les rendent visibles ; le dépôt en est le cas d'étude, avec ses rétractations.

## Ce qui est publiable (objets, pas résultats de science)

| objet | où il vit | chiffre au 2026-09-16 | recompute |
|---|---|---|---|
| Graphe de records typés (EDR/ADR/SDR/REF), négatifs et rétractations gravés au même titre | `docs/EDR/` | **297 EDR** ; statuts : 98 legacy · 79 active · 67 accepted · 15 validated · **2 retracted** ; 132 avec `verdict:` dont **39 négatifs/indéterminés** | `ls docs/EDR/*.md | wc -l` ; `grep -h "^status:" docs/EDR/*.md | sort | uniq -c` |
| Cliquet de calibration des instruments (une fonction qui produit une affirmation doit avoir un cas à réponse connue) | `tools/check_instrument_calibration.py`, `tests/sandbox/test_instrument_calibration.py` | **234 détectés / 226 calibrés / 2 dettes nommées** (de 71/1 le 2026-07-21) | `python tools/check_instrument_calibration.py` |
| Registre des classes d'erreur, chacune avec garde `exécutable` et contre-exemple gelé | `docs/REF/REGISTRE_ERREURS.md` | **28 classes**, 23 exécutables (0 sans contre-exemple) | `python tools/check_guard_negative_cases.py` |
| Cliquets du hook pre-commit + **cliquet des cliquets** (mutation en mémoire) | `tools/hooks/pre-commit`, `tools/check_gate_mutation.py` | **17 portes** ; 15 mutées, **22/22 mutants tués** ; 4 défauts réels au premier tir (portes 1, 2, 6, 14) | `python tools/check_gate_mutation.py --report` |
| Pré-inscription scellée par hash, lecture calibrée AVANT toute cellule, familles de contrôles déclarées | `tools/preregister.py`, `docs/preregistrations/` | **58 règles scellées** | `ls docs/preregistrations/*.json | wc -l` |
| Marqueur de demande within-subject (ablation du sujet, jamais « un survivant existe ») avec plancher de bruit mesuré | `tools/demand_marker.py`, `tools/s2_demand_ablation.py` | validé sur 4 modalités ; plancher no-op **1,058 / 0,922** (champion à 0,991 : dedans) | `EDR-S2-002`, CLAUDE.md §calibration |

## Les cinq résultats de MÉTHODE (chacun : un record, un chiffre, une garde)

1. **Le biais est directionnel.** Sur ~40 instruments examinés en fermant la dette de calibration (2026-09-01),
   ~30 défauts réels, tous de la même forme : donnée absente → affirmation NÉGATIVE de fond (`PAS DE RUNG`,
   `AUTEL MORT`, `N_EMERGE_PAS`). Trois formes : entrée vide → verdict ; `nan` détecté puis avalé ; troncature
   silencieuse. *Source : CLAUDE.md §Calibration, mémoire `calibration-debt-closed-negative-bias`.*
2. **Un nul de capacité peut être un réglage (E19).** `EDR-RETAIN-COMPOSE-LR` : à protocole identique, seul `lr`
   change : 0,02 → 0,173 (verdict RETENTION, rétracté) ; 0,002 → 0,923 ; 0/144 de recouvrement. Récidive sur le mur
   D=2 (`EDR-LOCK-002` : 0,178 → 0,784) et sur l'apprenant legacy (`EDR-CALIB-LEGACY-LEARNER` : pas publié 0,04 →
   0,197 ; 0,001 → 0,449, 12/12). Garde : `assert_verdict_invariant_to_optimizer`, clause E19 dans chaque règle.
3. **Une dose non comptée fabrique un nul (E2 sous forme E19).** `EDR-CALIB-LEARNER` : trois records « le crédit
   n'apprend pas à froid » valaient quelques dizaines de mises à jour ; à dose non bornée, 12/12 seeds apprennent
   (+0,156). Garde : `count_learning_events`, dose publiée à côté de tout nul.
4. **L'instrument peut tuer le sujet (E28).** `max(0.0, nan)` vaut 0,0 : un World Model par agent qui diverge devenait
   une mort par tick — 18 265 résurrections/seed, ramenées à 139 par la garde à la source
   (`LEGACY-WM-GUARD-R1`). Le « fait » « les apprenants meurent 100× plus » était l'arithmétique du monde.
5. **Une partie des sorties EST l'entrée (E24).** Le champion de production déclare 64 entrées + 126 sorties dans
   172 nœuds : 18 logits d'action sont l'observation ; annuler `W[:num_inputs]` ne l'aveugle pas. Garde :
   `assert_no_io_overlap`, porte 17 sur le dépôt de génomes (378 sujets, 0,5 s).

## Figures (toutes depuis des artefacts existants — zéro run)

| # | figure | source |
|---|---|---|
| F1 | Chronologie du cliquet de calibration : détectés / calibrés / dette, 2026-07-21 → 2026-09-16 (71/1 → 105/104 → 234/226) | git log de `tools/instrument_calibration_baseline.json` + CLAUDE.md |
| F2 | Le biais directionnel : défauts par forme (vide → verdict ; nan avalé ; troncature) | `docs/REF/REGISTRE_ERREURS.md`, entrées P2.13-P2.15 du backlog |
| F3 | Bascule E19 : `learned` vs `lr` (RETAIN-COMPOSE-LR, LOCK-002, CALIB-LEGACY-LEARNER R2) | `results/*` cités par ces records |
| F4 | Dose vs nul : hit_last par bloc, six bras (CALIB-LEARNER v2) | `results/learner_calibration_v2.json` |
| F5 | E28 : résurrections avec/sans garde, cinq pas (LEGACY-LR-CURVE-R1 vs R2) | `results/legacy_lr_curve_r1.json`, `results/legacy_lr_curve_r2.json`, `results/legacy_wm_guard_r1.json` |
| F6 | Mutation des cliquets : portes × mutations × verdict TUÉE/SURVÉCUE | `python tools/check_gate_mutation.py --report` |
| F7 | Plancher de bruit du marqueur de demande : no-op exact vs contrastes publiés | `EDR-S2-002`, `EDR-S2-BLIND-CHAMPION` |

## Plan des sections

1. Contexte : un programme empirique de 300 records sur une biosphère artificielle ; pourquoi la plupart des résultats sont
   négatifs et pourquoi c'est un problème de MÉTHODE avant d'être un problème de science.
2. Trois mécanismes : calibration à réponse connue (no-op exact / prédiction / monotonie) ; cliquets à baseline gelée et
   leur test de mutation ; pré-inscription scellée à lecture calibrée, familles de contrôles.
3. Le registre des erreurs comme objet scientifique : 28 classes, occurrences datées, gardes.
4. Cinq cas (§ ci-dessus), chacun avec sa rétractation ou son bandeau.
5. Ce que ça coûte et ce que ça rend : 26 commits science / 78 méthodo depuis le 09-01 ; 7 revues adversariales,
   7 erreurs réelles ; suite de 2 589 tests en 36 min.
6. Limites : cas d'étude unique ; les cliquets sont lexicaux (faillibles sur 5 axes, mesurés) ; un cliquet qui
   n'est pas demandé par un run est un coût (ADR-004 (iii)).
7. Ce qui suit : le harnais (spec 2026-09-16) — Task/Learner sous contrat, demande générée, revue humaine.

## Ce qui manque avant rédaction (à faire, sans run)

- [ ] F1 : reconstruire la série depuis `git log -p -- tools/instrument_calibration_baseline.json` (script dans `tools/preprint/`).
- [ ] F2 : classer les ~30 défauts de P2.13-P2.15 par forme (lecture du backlog, tableau).
- [ ] F3-F5 : un script de figures qui lit UNIQUEMENT les JSON cités (aucune valeur en dur).
- [ ] Relire chaque chiffre du plan contre sa commande de recompute le jour de la rédaction (ils bougent).
- [ ] Cible : atelier open-endedness / ALIFE / GECCO (ADR-004 (i)) ; format court (8 pages) + annexe = le registre.
