---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-091
type: EDR
title: "Le transfert curriculum est au plancher (goulot d'exploration) ; re-métricisation sur la survie"
status: legacy
gate: G1
---

# EDR 091 : Le transfert curriculum est au plancher (goulot d'exploration) ; re-métricisation sur la survie

## Contexte

Dev #3 a livré un harnais de **Ratio de Transfert** (`tools/curriculum_transfer.py`) : le curriculum
développemental (stoneage → agricultural → industrial, champion promu d'un monde au suivant)
transfère-t-il mieux qu'un tabula-rasa, à budget compute égal ? Verrou repro prouvé. Avant le run à
l'échelle, un **prérequis** (frontière scientifique #2) : la cible produit-elle une compétence
**non-plancher** ? Sinon le ratio compare bruit/bruit.

On a écrit une sonde décomposée (`tools/target_competence_probe.py`) qui mesure la grandeur exacte
du dénominateur (`final_competence` d'une ère sur la cible) à l'échelle réelle, décomposée en signaux
bruts (autels, âge, proies, rêves), en soupe fraîche ET avec le champion HoF.

## Résultat 1 — la ladder entière est au PLANCHER (sonde, K=8, 40 agents, 400 ticks)

Au défaut d'énergie (`base_metabolism=1.0`, `forage_payoff=1.0` = régime historique LÉTAL) :

| cible | médiane C (tabula) | médiane C (champion HoF) | autels (tous) | âge médian | extinction |
|---|---|---|---|---|---|
| stoneage | 0.000 | 0.000 | **0** | 12-20 | t≈50 |
| agricultural | 0.030 | 0.042 | **0** | 11-20 | t≈50 |
| industrial | 0.028 | 0.035 | **0** | 12-20 | t≈50 |

L'avantage du champion est **~0.005-0.01**, dans le bruit. Lancer le run de transfert aurait produit
un **NEUTRE garanti** (bruit/bruit) — du théâtre évité pour ~32 ères courtes.

## Résultat 2 — blocage à DEUX couches, isolées par re-sonde à différentes énergies

**Couche 1 — survie : résoluble (EDR 085).** Au sweet spot (`base_metabolism=0.25`,
`forage_payoff=3`), la survie quadruple : âge max 60 → **209**, population 40 → **140**, extinction
repoussée à t≈200. La compétence industrial **double** (0.035 → 0.068).

**Couche 2 — signal d'autel/outil : le vrai mur (EDR 014).** Même à vie longue (200 ticks),
**ZÉRO autel résolu** par qui que ce soit (frais ou champion), `total_dreams=0` (organe MCTS
dormant). C'est le **goulot d'exploration** : HoF historique = altars_solved 0 / craft jamais sur
5877 agents ; l'évolution est coincée dans l'optimum local « manger ~5 proies ». La mécanique d'autel
(`src/environments/biosphere.py:510-522`) est SAINE (cellule 3D exacte + signe XOR → +20 énergie)
mais exige une recherche dirigée d'autel qu'aucun connectome ne possède.

> La compétence par-monde pondère les autels à 0.6 (`compose`). Couche 2 non franchie → `compose=0`
> → compétence plafonne à `0.4·persist` (~0.07), sous le seuil. **Activer l'énergie ne suffit pas.**

## Réparation — re-métriciser le transfert sur la SURVIE

Le signal d'autel est nul, mais la **survie** a un gradient réel au sweet spot (champion 163-227 vs
frais 44, EDR 085). On mesure donc le transfert sur la dimension où le monde discrimine RÉELLEMENT :

- `survival_competence` (médiane d'âge / réf) ajoutée à `src/curriculum/competence.py`.
- `make_run_era_fn(..., competence_fn=...)` : injection optionnelle (défaut = métrique par-monde,
  **prod curriculum intacte**).
- `run_transfer_experiment(..., metric='survival', base_metabolism=0.25, forage_payoff=3)` par défaut.

Justifié, pas du déplacement de poteaux : les `*_competence` sont explicitement marquées
« PROVISOIRE » dans le code, et mesurer le transfert sur un signal **plat à zéro** est invalide par
construction. On ne change pas le seuil pour gagner ; on change la dimension pour qu'elle ait un
gradient mesurable.

## Résultat 3 — verdict du transfert re-métricisé

L'import du champion reseed **toute** la population (`main_biosphere.py:52-74`, clones + mutation),
donc le bras curriculum = population descendante du champion vs tabula = frais. La médiane est une
agrégation juste (pas de lavage par un agent unique).

La compétence est **non-plancher (~0.13, pas 0.03)** → l'instrument **discrimine** à nouveau.

**Run appairé 5 seeds (sweet spot, max_eras=10, 40 agents, 400 ticks, quiet-log)** :

| seed | C_curr | C_tabula | T | ratio |
|---|---|---|---|---|
| 0 | 0.220 | 0.115 | 30 | **1.913** |
| 1 | 0.125 | 0.155 | 30 | 0.806 |
| 2 | 0.085 | 0.155 | 30 | 0.548 |
| 3 | 0.095 | 0.135 | 30 | 0.704 |
| 4 | 0.087 | 0.160 | 30 | 0.547 |

> **VERDICT = NUIT** | médiane ratio **0.704** | favorables **1/5** | **sign_p = 0.375**.

**4/5 seeds : le curriculum NUIT** à la survie sur la cible (~30 % pire), seed 0 étant un outlier
opposé (1.913) à forte variance. Un pilote 2-seed (ratios 1.000 / 0.556) ET seed 0 seul auraient
donné le **signe opposé** de l'effet — leçon de puissance brutale.

## Signification

> **Transfert NÉGATIF, pas absence de transfert.** Deux causes plausibles, non démêlées ici :
> (1) **sur-spécialisation** — un champion forgé à travers stoneage/agricultural est mal-adapté à
> industrial (interférence : son connectome contraint l'exploration du nouveau paysage de fitness,
> là où la soupe fraîche l'explore sans biais) ; (2) **budget égal ≠ pratique égale sur la cible** —
> à 30 ères de budget, le bras tabula les concentre **toutes** sur la cible, le curriculum n'en passe
> que 10 (20 ailleurs). *La pratique directe concentrée bat la pratique étalée + transfert.*
> L'instrument est valide et **mesure** (passé de « NEUTRE forcé par plancher » à « NUIT mesuré ») ;
> le verdict est directionnel mais **sous-puissant** (sign_p=0.375, n=5).

## Honnêteté

- **Non significatif à n=5** (sign_p=0.375) : la tendance (4/5, médiane 0.704) est nette mais ce
  n'est PAS un résultat publiable seul. Pour conclure : ≥ ~12 seeds (cf. K_FLOOR S2) ou un effet
  plus net. Falsifiable.
- « Budget égal » = ères totales égales, PAS ères-sur-cible égales (confond transfert et
  concentration). Un design plus propre fixerait les ères-sur-cible des deux bras → variable d'exp.
- La médiane d'âge peut sous-estimer un transfert porté par l'élite ; ici l'import reseed toute la
  population (comparaison médiane-vs-médiane équitable), donc objection levée.
- Sweet spot 0.25/3 = variable d'expérience (Commandement 15), repris d'EDR 085.

## Statut

- Sonde de plancher décomposée livrée (`tools/target_competence_probe.py`), modes tabula/champion,
  knobs énergie. Diagnostic 2-couches établi.
- Transfert re-métricisé sur la survie (prod intacte), 9/9 tests verts. Verdict 5-seed : **NUIT
  directionnel (médiane 0.704, 4/5), sous-puissant** — transfert négatif probable.
- Infra : crash KuzuDB natif (segfault sur jeton de langage non-UTF8 `SOCIAL_ENCOUNTER`, EXIT=139 à
  seed 2) corrigé — sanitizer `_safe_kuzu_str` + mode `AGISEED_QUIET_LOG` (drop événements
  volumineux headless → crash-free + ~10× plus rapide). Re-run propre EXIT=0.
- **Prochain front : briser le goulot d'exploration (EDR 014), prérequis commun au transfert ET au
  RSI Dev #2.** Et, pour le transfert lui-même : design « ères-sur-cible égales » + puissance ≥12.

## Variables d'expérience

Métrique de compétence (survie vs par-monde vs futur signal d'outil), agrégation (médiane vs
élite/censurée), `base_metabolism × forage_payoff`, leviers d'exploration EDR 014 (WorldModel
par-agent, nouveauté count-based amplifiée, auto-craft chaîne-courte, curriculum de sous-compétences).
