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

## Suite (l'effort dédié : le barreau survivable = le contrôle positif)
Prochaine étape (décision utilisateur « 1 puis 2 ») : établir un CONTRÔLE POSITIF in-world — un régime où la
mémoire d'apex PAIE démontrablement (discrimination mémoire-basée, ablation-sensible, au-dessus du plancher).
Leviers : desserrer la pression corps jusqu'au sweet-spot survie (EDR-085) tout en gardant l'occlusion dist-2 ;
augmenter les ères ; récompenser explicitement la bonne discrimination (Mammouth vs Leurre) en énergie pour
sur-pondérer l'apex dans une survie autrement dominée par le foraging. SANS ce contrôle positif, aucun verdict
in-world n'est interprétable.

Converge [[EDR-EVO-002]], [[EDR-S2-012]], [[EDR-090]], [[EDR-INFRA-001]], REF-EXPERIMENT-PREFLIGHT.
