---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-096
type: EDR
title: "Autel mort confirmé, apex atteint par COOPÉRATION (pas par l'outil) — le funnel conflait deux pathways"
status: legacy
gate: G2
---

# EDR 096 : Autel mort confirmé, apex atteint par COOPÉRATION (pas par l'outil) — le funnel conflait deux pathways

## Contexte

EDR 095 a réfuté l'organe MCTS comme levier d'exploration (forcer le rêve réduit la survie). Le mur
restant = couche 2 (autels/outils), goulot EDR 014. Barreau 0 : sonde observationnelle
`tools/altar_tool_funnel_probe.py` (livrée subagent-driven, 3 tâches TDD, tous tests verts). Au sweet
spot (0.25/3.0), sur stoneage, 8 seeds, 40 agents, 300 ticks : (1) l'autel est-il structurellement
mort ? (2) où les agents décrochent-ils dans le funnel outil (craft → usage mammouth) ?

## Constat — verdict nu trompeur, décomposition révélatrice

Run réel `results/altar_tool_funnel_0.json` (commit `ac1ba48`, 882 agents poolés) :

| métrique | valeur |
|---|---|
| `verdict_autel` | **AUTEL_MORT** (`altars_solved_max = 0` sur 882 agents) |
| `verdict_funnel` (nu) | `GAP_ACQUISITION` ← **ARTEFACT, voir ci-dessous** |
| `frac_hunt` (preys_eaten≥1) | 0.505 |
| `frac_craft` (spears_crafted≥1) | **0.016** (16 lances / 882 agents) |
| `frac_apex` (mammoth_kills≥1) | **0.217** (232 crédits mammouth) |

Décomposition par seed cohérente : `frac_craft` ∈ [0.000, 0.028], `frac_apex` ∈ [0.108, 0.294]
sur les 8 seeds. **`frac_apex` >> `frac_craft` partout.**

## Cause-racine — le funnel conflait deux pathways disjoints

`frac_apex > frac_craft` est **logiquement impossible** si tuer le mammouth exigeait une lance craftée.
Lecture du moteur (`world_1_stoneage.py:685-723`) :

1. **`mammoth_kills` est crédité au GROUPE** (récompense de pack, EDR 028, `:715-718`) : à la mort d'un
   mammouth, CHAQUE agent du pack attaquant reçoit `mammoth_kills += 1`. Ce n'est pas « cet agent a
   utilisé un outil », c'est « cet agent était dans le pack ».
2. **Le mammouth meurt par dégâts cumulés à mains nues** (`:706` « dégâts cumulés one-shotent » ;
   `weapon_damage` = 10 sans lance, 50 avec, `:685-686`). Un pack de N agents à mains nues délivre 10N
   cumulés → tue un mammouth (hp ≥ 50) SANS aucune lance, dès que `coop_reward` est actif (défaut True,
   `:708`).

Donc `frac_apex=0.217` mesure la **chasse coopérative à mains nues**, pas l'usage d'outil. Mon funnel
(`spears_crafted` → `mammoth_kills`) traitait `mammoth_kills` comme un proxy d'usage d'outil : **faux**.
Le label `GAP_ACQUISITION` (déclenché parce que `frac_craft < eps`) est un artefact d'instrument :
l'apex n'est pas gaté par le craft. (5ᵉ artefact de mesure exposé par la décomposition, après
EDR 092/093/094/095 ; ici c'est la **non-monotonie** `apex >> craft` + la lecture du mécanisme qui
l'ont tué, pas le gate vert.)

## Signification — l'apex est VIVANT, le « goulot couche-2 » est un artefact de métrique morte

Reframe du mur EDR 014 :

- **L'autel est structurellement mort** (confirmé empiriquement, `altar_max=0` sur 882 agents). Or
  `stoneage_competence` pondère `altars_solved` (≡0) à **0.6** (`src/curriculum/competence.py:45-58`)
  → la « couche-2 » s'effondre à `0.4 × chasse` pour une raison de **code mort**, pas de comportement.
- **L'apex-prédation est VIVANTE** : 21,7 % des agents participent à un kill de mammouth (récompense
  dure, coopérative, riposte 50). Le substrat n'est donc PAS « exploration-mort » — les agents
  atteignent des récompenses difficiles, mais **par coopération**, en **contournant** le pathway
  outil.
- **Le pathway craft-outil est froid** (`frac_craft=0.016`) mais **non bloquant** : la coopération
  offre une route moins chère vers la même récompense apex. Le craft est vestigial, pas un goulot.

Le « goulot d'exploration couche-2 » était donc en grande partie un **artefact de la métrique de
compétence** (0.6 sur une variable morte), pas une incapacité du substrat. C'est cohérent avec
[[world-floor-survivability-gate]] couche 2 — mais la cause est une métrique morte + un pathway outil
contourné, pas un mur d'exploration intrinsèque.

## Statut

- Barreau 0 livré ; sonde opérationnelle. **`verdict_funnel` non fiable tel quel** (conflation
  coop-crédit / usage-outil) — NE PAS le citer nu. La décomposition (`frac_craft` vs `frac_apex`) +
  la lecture du mécanisme sont le vrai résultat.
- **Prochain — deux voies :**
  1. **Réparer la métrique de compétence** (cheap, fort levier) : cesser de pondérer `altars_solved`
     (mort) à 0.6 ; re-pondérer la couche-2 sur un signal VIVANT (`mammoth_kills`/`big_kills` coopératif,
     ou `spears_crafted` si on veut spécifiquement l'outil). Débloque le curriculum (gradation au-delà
     de la chasse triviale).
  2. **Étudier le pathway outil proprement** (barreau 1) : métrique « kill mammouth AVEC lance »
     (gater par `holds_spear` à l'instant du coup), pour savoir si l'outil est inutile (coop suffit) ou
     juste sous-appris. Décide si « auto-craft » (levier II) a un intérêt.

## Variables d'expérience

Pondération couche-2 (autel mort vs mammouth coop vs spears), `coop_reward` (ablation → l'outil
redevient-il nécessaire ?), `big_kills` (nb réel de mammouths vs crédits de pack), métrique d'usage
d'outil gatée par `holds_spear`, `eps` du funnel (sans objet ici : le problème est la conflation, pas
le seuil).
