---
id: EDR-EVO-003
type: EDR
title: "Pont in-world de la demande de mémoire : infra bâtie (MemoryDemandBiosphere, occlusion dist-2 + ablation within-subject) mais tout régime bute sur la tension SURVIVABLE↔EXIGEANT (mur S2/EDR-090) — PAS de contrôle positif → résultat DIFFÉRÉ, non un verdict"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-002]
---

## Question
[[EDR-EVO-002]] a montré HORS-MONDE qu'un objectif à rappel différé fait ÉVOLUER un substrat qui maîtrise la
mémoire (1.00 sur 8/8). Le pont : la demande de mémoire survit-elle à l'embarquement dans le VRAI monde (le
gap « proxy 9 / in-world 0 ») ? Ce record documente **ce qui a été bâti, le mur rencontré, et pourquoi je
NE CONCLUS PAS** — la rigueur de l'arc (un nul sans contrôle positif est un artefact, cf. [[EDR-AUDIT-001]],
WARM-002, [[EDR-090]]) l'interdit.

## Ce qui a été bâti (infra réutilisable, `tools/evo_memory_inworld.py`)
- **Évolution in-world auto-contenue** : soupe FRAÎCHE aux dims du monde -> ères -> sélection élitiste par
  `life_score` en mémoire -> reséminage (élites + enfants mutés). Aucune écriture du HoF global (pas de
  contamination inter-sessions), `_disable_kuzu()` en tête (repro + vitesse + pas de retriever ambiant,
  corrige [[EDR-INFRA-001]]). Débit ~3.3 s/ère (30 agents, 120 ticks). VALIDÉE.
- **`MemoryDemandBiosphere`** (sous-classe, sans réécrire `get_batch_observations`) : le type d'apex
  (Mammouth récompense / Leurre piège) est révélé à **distance 2** et **CACHÉ dans la fenêtre d'attaque**
  (dist≤1) -> l'agent doit RETENIR le type vu de loin pour décider l'attaque de près. C'est une VRAIE demande
  de rappel différé (délai ≥ 1 tick, non contournable au contact), là où `transient_apex` (EDR 058/062) est
  un délai-0 : il révèle le type À l'adjacence = la fenêtre d'attaque, donc décidable sans mémoire (vérifié :
  benchmark ON≡OFF byte-identique).
- **Ablation within-subject calibrée** (marqueur S2-005/MEM-001) : `ablate_memory` révèle un type ALÉATOIRE
  à dist 2 -> mémoire portée DÉCORRÉLÉE. Canal vérifié VIVANT (l'ablation change le nombre de rencontres).

## Le mur (trois régimes, une tension fondamentale)
| régime | demande de mémoire ? | survie | discrimination |
|---|---|---|---|
| `transient_apex` (délai-0) | NON (décidable au contact) | ~18 ticks | ON ≡ OFF byte-identique |
| apex denses + corps insuffisant | faible | ~18 ticks | disc 0.75 mais ON ≡ OFF (pas mémoire-basée) |
| **MemoryDemandBiosphere (dist-2)** | OUI (réelle) | **~13 ticks (plancher)** | disc ≈ 0.50 (chance) INTACT / ABLATÉ / CONTRÔLE — insensible |

Le régime qui EXIGE vraiment la mémoire (dist-2 + pression corps) **affame** la survie (~13 ticks, plancher
[[EDR-090]]) AVANT que la mémoire puisse être sélectionnée ; le régime SURVIVABLE (délai-0, corps suffisant)
ne fait pas mordre la demande. C'est la tension **survivable ↔ exigeant** — précisément le problème ouvert
central du dépôt ([[EDR-S2-012]] : la survie n'a aucun contenu cognitif ; [[EDR-090]] : pas de premier
barreau survivable).

## Pourquoi je NE CONCLUS PAS (la rigueur de l'arc)
Le smoke (dist-2) donne disc ≈ chance, insensible à l'ablation → tentant de lire « le pont échoue / le corps
court-circuite ». **Interdit** : il manque le **CONTRÔLE POSITIF** (générateur A du pré-vol) — AUCUN régime
in-world n'a été montré où la mémoire PAIE démontrablement. Sans lui, le nul est INDISTINGUABLE de « le
régime plafonne avant que la mémoire évolue » (plancher EDR-090) ou de « 12 ères ≪ les 40 générations qu'a
exigées le proxy » (sous-entraînement). Un nul non contrôlé a déjà fabriqué des conclusions dans cet arc
(AUDIT-001) ; on ne recommence pas. **Statut : smoke NON concluant, résultat DIFFÉRÉ.**

## Ce qui est établi malgré tout
- L'infra d'un pont in-world existe et est bon marché ; la brique manquante n'est pas technique.
- Le verrou n'est PAS « l'évolution ne peut pas bâtir la mémoire » ([[EDR-EVO-002]] le réfute : elle le fait,
  8/8) ni « le substrat en est incapable ». Le verrou est de **construire un objectif de survie qui exige la
  mémoire SANS s'effondrer** — la prescription non résolue de [[EDR-090]] (« adapter le substrat / trouver un
  barreau survivable AVANT de durcir »).

## Campagne du barreau survivable (étape 2) — contrôle positif PARTIEL trouvé
Décision utilisateur « 1 puis 2 » : chercher un régime où la mémoire d'apex PAIE. Campagne de smokes
(1-3 seeds, exploratoire, sous-puissance assumée) qui a **resserré** le gap :

- **Levier décisif = STAKES, pas corps insuffisant.** Rendre le Leurre LÉTAL (`LEURRE_DAMAGE=100` : attaquer
  un Leurre = mort) sur-pondère l'apex dans une survie sinon dominée par le foraging, SANS affamer (évite le
  plancher EDR-090). C'est ce qui débloque la sélection pour la discrimination.
- **Contrôle positif PARTIEL établi** (réfute « le corps ne peut pas discriminer in-world ») : sous Leurre
  létal + type VISIBLE, l'évolution in-world discrimine **disc 0.80-1.00** (2 seeds) — la discrimination
  d'apex EST sélectionnable in-world.
- **Mais l'étape MÉMOIRE ne se franchit pas dans ce budget** : sous Leurre létal + occlusion dist-2 (mémoire
  requise, 22 ères, 3 seeds), disc INTACT = 0.25 / 0.75 / 0.20, et INTACT ≡ VISIBLE sur 2/3 seeds (le champion
  n'utilise pas le type même visible) ; un seul seed montre un signal mémoire faible (0.75 -> 0.57 sous
  ablation). Évoluer SOUS occlusion dégrade même la discrimination visible -> l'occlusion est plus dure à
  franchir qu'à apprendre la discrimination nue.
- **Verrou résiduel = MESURE ÉPARSE** : 5-10 rencontres d'apex par champion (30 agents × 200 ticks) -> chaque
  disc repose sur trop peu d'événements pour un verdict. La navigation imparfaite + la mort rapide rendent les
  kills rares.

Bilan raffiné : le gap in-world se resserre de « rien ne marche » à **(a) l'étape MÉMOIRE spécifiquement**
(la discrimination visible, elle, s'évolue) **et (b) la sparsité de la mesure par kills**.

## Suite (frontière dédiée — mesure DENSE)
Le pont robuste exige, AVANT tout verdict : une **mesure dense** de la décision d'apex (rencontres
CONTRÔLÉES — spawn d'un apex adjacent + occlusion + lecture de l'action attaque/fuite — au lieu de compter
des kills rares en roaming libre), + plus de seeds/ères. Avec la discrimination visible comme contrôle
positif (acquis) et l'ablation within-subject comme marqueur causal (bâti), il ne manque que la densité de
mesure. C'est un effort dédié, pas un add-on de session.

Converge [[EDR-EVO-002]], [[EDR-S2-012]], [[EDR-090]], [[EDR-INFRA-001]], REF-EXPERIMENT-PREFLIGHT.
