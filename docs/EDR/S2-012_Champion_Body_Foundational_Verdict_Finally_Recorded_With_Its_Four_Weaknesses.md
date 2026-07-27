---
id: EDR-S2-012
type: EDR
title: "champion_body : le verdict FONDATEUR « la survie vient du CORPS, pas de la cognition » enfin gravé — direction confirmée, mais « 5/5 mondes » en vaut 4 et le volet fitness tombe à 2/5 sous la correction du dépôt"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-DEMAND-MARKER, REF-EXPERIMENT-PREFLIGHT]
foundational: true
---

## Question
Le finding `champion_body` porte le verdict le plus structurant du dépôt — *la survie in-world vient
ENTIÈREMENT du corps évolué, RIEN de la cognition* — et il n'avait **aucun record**. `grep champion_body
docs/EDR/` : 0 occurrence. Il vivait dans un seul markdown de travail
(`docs/superpowers/specs/2026-07-15-s2-cognition-vs-body-FINDING.md`).

C'est sur lui que reposent la §2 de `SPECIFICATION_10ANS.md`, l'explication du « proxy 9 / in-world 0 »,
et — depuis [[EDR-AUDIT-001]] — le maintien de S2-006 après correction de sa dérivation. Un verdict
fondateur non gravé, non calibré, et cité comme filet de sécurité par un autre record : il fallait le
graver, avec ce qu'il vaut.

## Méthode (l'instrument, tel qu'il est)
`tools/s2_cognition_body.py::cognition_body_study` — grille 2×2 sur 5 mondes, K=12 ères, 20 agents,
200 ticks, seed 2026, RAG off :

| cellule | génome | politique |
|---|---|---|
| `champion` | champion (HoF) | réseau du champion |
| **`champion_body`** | **champion (HoF)** | **actions ALÉATOIRES** (`RandomActionBatchModel`) |
| `random_genome` | frais | réseau frais |
| `random_action` | frais | actions aléatoires |

Verdict par `src/seed_ai/s2_stats.py::verdict_cognition_body` : `BODY` ssi l'effet `body`
(`champion_body` vs `random_action`) est significatif ET `cliff ≥ 0.33`, ET que l'effet `policy`
(`champion` vs `champion_body`) ne l'est pas.

## Résultats (survie médiane, tels que publiés)

| monde | verdict | `champion` | `champion_body` | `random_*` | δ corps (p) | δ politique (p, Holm) |
|---|---|---|---|---|---|---|
| soup | BODY | 26 | 35 | 6 | +0.94 (0.0025) | −0.31 (0.067) |
| stoneage | BODY | 22 | 25 | 6 | +0.87 (0.0025) | −0.12 (0.89) |
| agricultural | BODY | 24 | 25 | 6 | +0.96 (0.0025) | −0.11 (0.89) |
| industrial | BODY | 22 | 25 | 6 | +0.87 (0.0025) | −0.12 (0.89) |
| famine | BODY | 22 | 25 | 6 | +0.87 (0.0025) | −0.13 (0.89) |

**La direction tient** : `champion_body` — le génome du champion piloté **au hasard** — survit ~4× le
plancher et **bat le champion complet** sur 5 cellules sur 5. La politique est survival-négative partout.

## Ce que ce record CONFIRME comme solide
* **Valeurs ABSOLUES publiées** (les 4 cellules, survie et life_score) — contrairement à S2-009, épinglé
  par [[EDR-AUDIT-001]] pour n'avoir publié que des ratios.
* **Unité de réplication correcte pour le p** : Wilcoxon signé sur les **médianes PAR ÈRE** (12 valeurs),
  pas sur les agents. Vérifié dans `_compare` (`s2_stats.py:140-149`). Pas de pseudo-réplication.
* **Design PRÉ-ENREGISTRÉ** (`docs/superpowers/specs/2026-07-15-s2-cognition-vs-body-design.md`), seuils
  gelés d'avance, issue alternative COGNITION nommée avant le run. C'est rare dans ce dépôt (classe E11).
* **Contrôle négatif présent** (`random_action`) et 4 tests calibrant la **fonction de verdict** sur
  distributions synthétiques.
* Sur `life_score`, l'effet politique est **négatif SIGNÉ**, pas nul — un effet signé est plus robuste
  qu'une absence d'effet.

## Ce qui est PLUS FAIBLE qu'annoncé — quatre points, tous re-vérifiés par sonde propre

**1. « BODY unanime 5/5 mondes » en vaut au plus 4.** `IndustrialWorld` est
`class IndustrialWorld(Biosphere3D)` avec un unique compteur `pollution` incrémenté tous les 10 ticks et
**jamais lu par la biologie** ; sa propre docstring dit « *Clone de Biosphere3D pour l'instant* ». Or
`stoneage` **est** `Biosphere3D`. Les deux lignes du tableau sont d'ailleurs **identiques au chiffre
près** (22/25/6, δ +0.87, −0.12) — ce qui corrobore. **L'unanimité compte deux fois la même simulation.**

**2. Le volet `life_score` ne survit pas à la correction que le dépôt applique à l'autre moitié.**
`s2_cognition_body.py` applique Holm aux p de `policy` **pour la survie seulement** ; la branche
`life_score` imprime les p **bruts**. Appliqué avec la fonction `holm` du dépôt aux p publiés
`[0.009, 0.038, 0.007, 0.038, 0.025]` → **`[0.036, 0.076, 0.035, 0.076, 0.075]`, soit 2 mondes sur 5**.
L'affirmation « politique fitness-NÉGATIVE et significative partout » devient **2/5**.

**3. `p = 0.0025` est le PLANCHER du test, pas une force.** Vérifié avec `wilcoxon_signed_rank` du dépôt :
à n=12 avec séparation parfaite, `W=78, p=0.00253` — la plus petite valeur atteignable. Elle apparaît
**10 fois sur 10** (5 mondes × 2 métriques). Le test n'est pas dégénéré (10/12 rend 0.0455, 8/12 rend
0.327), mais **la statistique est SATURÉE** : elle ne gradue plus rien entre « fort » et « écrasant ».

**4. Le bras qui PRODUIT le verdict est BETWEEN-subject.** Le contraste `policy` est bien within-subject
(même génome, politique détruite) — c'est la moitié propre. Mais `body`, celui qui déclenche `BODY`,
compare `champion_body` à `random_action` : **génome champion contre génomes frais**, deux populations.
C'est le design que S2-001 a identifié comme générateur de faux positifs. Et le bras champion repose sur
**UN SEUL génome** cloné 20× et réutilisé sur les 12 ères : le n effectif sur « le corps » est **1**.
S'y ajoute que `random_action = random_genome = 6 exactement sur les 5 mondes` — un témoin constant à
travers des mondes hétérogènes est la signature d'un **plancher de métrique**, et l'effet « corps » est
mesuré contre lui.

**Corollaire mécanique à ne pas perdre** : le « phénotype métabolique » se réduit à des **normes L1 de 10
lignes de `W`** (`mamba_agent.py:53-55` : `hp_bonus = Σ|W[0:5]| × 10`, `inv_capacity = Σ|W[5:10]|`).
L'hypothèse alternative « *les poids évolués ont simplement une norme plus grande* » n'est donc pas
écartée par ce design.

## Verdict
**`BODY_DIRECTION_CONFIRMED__INSTRUMENT_VALIDATED__MAGNITUDE_CLAIMS_OVERSTATED`** — le finding est
**gravé, sa direction tient, et son instrument est désormais VALIDÉ** : le corps évolué porte la survie,
la politique du champion est survival-négative, et le contrôle positif (ci-dessous) montre que
`verdict_cognition_body` rend bien `COGNITION` quand la cognition paie. Mais trois de ses formulations
les plus citées sont plus faibles que leur énoncé : *« 5/5 mondes »* → 4, *« fitness-négative
significative partout »* → 2/5, *« p=0.0025 »* → plancher de test.

**Ce qui change par rapport à WARM-002 et S2-006** : leur moitié nulle n'avait aucun contrôle positif —
celle-ci en a un, exécuté, qui passe. Le nul de `champion_body` est donc **interprétable**, ce que les
leurs n'étaient pas. C'est la différence entre « on n'a rien vu » et « on aurait vu s'il y avait eu ».

## Conséquences — dont une qui me concerne
* ⚠️ **Correction d'une affirmation que J'AI écrite le même jour.** Les bandeaux posés sur
  [[EDR-S2-006]] et dans [[EDR-AUDIT-001]] disent que la conclusion large de S2 « a un appui INDÉPENDANT :
  l'arc cognition-vs-corps, verdict BODY unanime 5/5 ». **Cet appui est réel mais plus faible que je ne
  l'ai écrit** : 4 mondes et non 5, et sa moitié « la cognition n'apporte rien » souffre du même défaut
  (nul sans contrôle positif) que la dérivation qu'il était censé rattraper. Les deux bandeaux sont
  amendés. *Un filet de sécurité qu'on n'a pas vérifié n'en est pas un.*
* **Aucun artefact de run** : `cognition_body_study` imprime et retourne, ne sauvegarde rien (contraste :
  `run_s2` produit `results/s2_demand_2026.json`). **Les chiffres publiés ne sont re-dérivables d'aucun
  fichier stocké** — ils ont été recopiés d'un stdout. Non publiés non plus : les IC bootstrap de Cliff,
  le corroborant d'interaction `inter_cmp`, `censored_frac`, et l'identité du champion utilisé.
* ✅ **LE CONTRÔLE POSITIF MANQUANT A ÉTÉ FAIT, ET IL PASSE** (même jour, P2.11). Grille 2×2 dans le
  régime `cognitive_demand` calibré (P2.10), cellule `champion` remplacée par une politique DONT ON SAIT
  qu'elle utilise sa cognition — l'oracle — et **génomes tous FRAIS** (donc aucun avantage corporel à
  créditer) :

  | cellule | survie médiane |
  |---|---|
  | cognition (oracle) | **200.0** |
  | corps (actions random) | 7.0 |
  | random_genome | 7.0 |
  | random_action | 7.0 |

  **Verdict rendu : `COGNITION`** (`policy` p=0.0025 cliff=1.000 ; `body` p=1 cliff=0.000).
  **Conséquence directe et importante : le verdict BODY de `champion_body` n'est PAS une incapacité
  d'instrument.** La moitié NULLE du finding — « la cognition n'apporte rien » — dispose enfin d'un
  contrôle positif in-world montrant que l'instrument l'aurait détectée si elle avait été là. C'est
  précisément ce qui manquait à WARM-002 et à S2-006.
  ⚠️ Ce contrôle ne corrige **aucun** des quatre affaiblissements ci-dessus : il établit la CAPACITÉ de
  l'instrument, pas l'amplitude des affirmations.
  ⚠️ **Il confirme au passage le point 3** : même sur un contraste 200 contre 7, `p = 0.002526` (plancher
  du test) et `cliff = 1.000` (plafond de l'effet). **Les deux statistiques saturent** — elles ne
  gradueront jamais rien, ici pas plus qu'ailleurs.
  Premier instrument de `src/` calibré ; cliquet **80 détectés, 6 calibrés**.

## Leçons (registre des erreurs)
* **E14, deuxième angle mort du cliquet, trouvé par ce record** : `scan_instruments` ne parcourait que
  `tools/*.py`. `verdict_cognition_body` vit dans `src/seed_ai/s2_stats.py` — l'instrument qui produit le
  verdict fondateur était donc **invisible sur deux comptes** : ni calibré, ni compté comme dette.
  Scan étendu à `src/seed_ai` → **80 instruments détectés, 5 calibrés**. L'heuristique était faillible sur
  DEUX axes le même jour : *ce qu'elle cherche* (motif de nommage) et *où elle le cherche*.
* **Un « 5/5 » se vérifie en lisant les mondes**, pas en comptant les lignes d'un tableau. Deux entrées
  peuvent être la même simulation.
* **Une correction de multiplicité appliquée à une moitié d'étude et pas à l'autre** est un choix
  d'analyse post-hoc (E11) — ici il change le verdict d'un volet entier.

Converge [[EDR-S2-006]], [[EDR-S2-003]], [[EDR-AUDIT-001]], [[EDR-WARM-010]],
[[s2-world-demand-thread]], [[within-subject-demand-marker]].
