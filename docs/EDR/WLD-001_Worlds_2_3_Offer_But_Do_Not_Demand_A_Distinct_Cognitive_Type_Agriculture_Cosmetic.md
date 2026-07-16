---
id: EDR-WLD-001
type: EDR
title: Les mondes 2/3 OFFRENT mais n'EXIGENT pas un type cognitif distinct — l'agriculture est cosmétique, l'industrie est du stoneage déguisé
status: accepted
gate: G0
verdict: AGRICULTURE_COSMETIC
---

# EDR-WLD-001 : « Chaque monde exige un type » est ASPIRATIONNEL pour les mondes 2/3

> Territoire WLD. Instrument de demande (analogue au mur du craft, EDR 125/CRAFT-001). Banc
> `tools/agricultural_demand_probe.py` (tooling-only, `git diff src/` VIDE).

## Question

La taxonomie AGI postule que « chaque monde exige un type cognitif distinct » (world 1 survie, world 2
agriculture/prévoyance saisonnière, world 3 industrie/coopération). Est-ce réel ou aspirationnel pour les
mondes 2/3 ?

## Faits statiques (world 3 industriel)

`src/worlds/world_3_industrial.py` = **18 lignes**, sous-classe pure de `Biosphere3D`, ajoute
`self.pollution += 0.01` tous les 10 ticks — mais `pollution` n'est **JAMAIS lue** (aucune conséquence sur
les agents, la survie, la fitness). → **world 3 = stoneage déguisé**, zéro demande distincte (vérifié par
test : seul override comportemental = `step`, qui n'ajoute que le compteur mort).

## Méthode (world 2 agricole)

World 2 offre une chaîne agricole : ramasser une `Seed` → la LÂCHER (action DROP=8) → `Planted_Seed` →
(printemps) `Plant` → (été/automne) `Fruit` (nourriture). + hiver rude (−0.2 énergie/tick sauf près d'un
`Fire`). Type distinct = **prévoyance saisonnière**. **Clé** : `Planted_Seed` n'existe QUE si un agent a
ramassé PUIS lâché une Seed → `max(Planted_Seed) > 0` = **preuve directe** de comportement agricole.

Cohorte-champion (évolué en stoneage) dans `AgriculturalWorld`, **famine neutralisée** (base_metabolism=0.0
→ les agents vivent jusqu'aux saisons ; retire le plancher qui masquerait la demande), 250 ticks (spring→
winter→spring), K=5 seeds, capture par tick de la saison + comptes d'items + survie.

## Résultat (K=5)

| chaîne | max Seed | **max Planted_Seed** | max Plant | max Fruit |
|---|---|---|---|---|
| valeur | 30 | **0** | 0 | 0 |

- **Aucune plantation** sur les 5 seeds — le champion ne lâche jamais de graine, malgré 30 graines
  disponibles et un temps illimité. La chaîne agricole est **totalement inerte**.
- Hiver : survie 0.875 (le froid tue 12.5 % **incidemment**), `Fire` max = 0 → le champion ne fait jamais
  de feu non plus (demande hivernale également non satisfaite).
- Verdict **AGRICULTURE_COSMETIC** (reproduit en calibration n=2).

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : le champion n'exhibe **aucun** comportement agricole (Planted_Seed=0) même avec opportunité
  maximale (graines + temps + zéro famine). World 3 est structurellement du stoneage (pollution morte).
- **INTERPRÉTATION** : « chaque monde exige un type » est **ASPIRATIONNEL pour les mondes 2/3**. Le monde
  OFFRE une structure (saisons, chaîne agricole) mais ne l'EXIGE/l'obtient pas : le champion stoneage n'a
  pas de comportement de plantation, et la chaîne reste inerte. **Même pattern que le mur du craft** (offert,
  non retenu, EDR 125/127/CRAFT-001) et le plancher-monde (mécanique = code mort, world-floor gate).
- **Argument temporel (renforce)** : même si le champion plantait, la chaîne (sprout 5 %/tick au printemps
  PUIS ~100 ticks de croissance → Fruit) dépasse la durée de vie des agents à tout régime SOUS PRESSION
  (~20-80 ticks) → le payoff agricole est **temporellement inatteignable** hors famine neutralisée. La
  demande est cosmétique dans les deux sens (non-exploitée ET trop lente pour payer).
- **CONVERGE** avec la thèse de session : le monde OFFRE, l'agent ne CONVERTIT pas (opportunité présente,
  comportement absent) → le levier est le substrat/crédit (le champion ne peut pas APPRENDRE à cultiver),
  pas l'ajout de mécaniques-monde.

## Portée / Bornage

1. base_metabolism=0.0 retire la **pression de survie** → pas d'incitation à cultiver ; mais `max_planted=0`
   montre l'absence de comportement agricole SPONTANÉ même avec opportunité maximale (borne conservatrice :
   sous pression ce serait pire, cf. argument temporel).
2. Champion unique (HoF #1), cohorte fixe (benchmark_mode). L'agriculture pourrait émerger d'une évolution
   IN world 2 — non testé (le champion vient de stoneage). La question « le monde POURRAIT-il exiger » reste
   ouverte ; « le monde exige-t-il ACTUELLEMENT du champion » = NON.
3. Instrument de comportement (planting/fruit/fire), pas de fitness. Le volet « planter PAIE-t-il » n'est pas
   mesurable tant que planter n'arrive pas (max_planted=0).

## Suite

- **Décision-relevant** : construire des KPI cognitifs pour les mondes 2/3 est **prématuré** — les mécaniques
  existantes ne sont même pas exercées. Le levier (comme partout) est le substrat/crédit, pas plus de monde.
- Si l'axe mondes 2/3 est repris : (a) réparer world 3 (pollution morte → conséquence réelle), (b) accélérer
  la chaîne agricole (fruit < durée de vie) OU évoluer un champion IN world 2, (c) rendre l'hiver létal sous
  un régime survivable pour créer une vraie demande de feu/réserve.

Lignée : converge [[world-floor-survivability-gate]] (mécanique = code mort) + [[intelligence-typing-flat-connectome]]
(taxonomie surtout docs) + le mur du craft [[world-floor-survivability-gate]]. Étend [[s2-world-demand-thread]]
(le monde exige la SURVIE — mais pas de type distinct au-delà, pour 2/3).
