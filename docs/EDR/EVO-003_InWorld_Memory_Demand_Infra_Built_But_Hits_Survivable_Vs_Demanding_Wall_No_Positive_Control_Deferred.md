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

## Mesure dense TENTÉE — invalidée par son PROPRE contrôle positif (3ᵉ mur)
La sonde de rencontre CONTRÔLÉE a été bâtie (`_approach_rate` : 1 agent + 1 apex STATIQUE à dist 2, lire
approche/fuite ; env réutilisé ; occlusion `hide_on_approach` + ablation). Résultat brut : engage ≈ 0 pour
Mammouth ET Leurre, tous modes -> tentant de conclure « champions RÉACTIFS-seuls, pas de navigation par type,
la discrimination roaming (0.80-1.00) était un artefact de MOUVEMENT (apex mobiles) ». **MAIS le contrôle
positif de la sonde l'a RÉFUTÉE** : `agent_moved = 0.00` dans tous les essais — l'agent isolé **ne bouge
JAMAIS** (env minimal -> obs dégénérée -> politique no-move) ; avec apex MOBILE, engage=1.00 seulement parce
que l'apex vient SUR l'agent figé, pas par navigation. Donc engage≈0 est un ARTEFACT d'agent figé, PAS une
absence de navigation. Sans ce contrôle positif, une fausse conclusion « réactif-seul / pas de mémoire »
aurait été gravée (la leçon [[EDR-AUDIT-001]] : ne pas conclure d'une mesure non contrôlée). **3ᵉ mur
distinct** (après délai-1 non-contraignant et corps-insuffisant-plancher) : l'agent ISOLÉ fige -> une sonde
hors-contexte ne préserve pas le comportement normal. Le verdict mémoire in-world reste genuinement NON établi.

## Mesure dense IN-CONTEXTE réalisée — densité RÉSOLUE, mais convergence « réactif, pas navigateur »
`probe_navigation_incontext` : env NORMAL (`_setup_lewis`, N_APEX apex, contexte complet), apex FIGÉS
(cibles de décision, pas de confond mouvement) ; à chaque tick, pour chaque agent dans la zone d'un apex, on
lit approche/fuite. **Densité RÉSOLUE** (n = 160-361 agent-ticks/type vs 5-10 kills en roaming) — le problème
de sparsité est corrigé. `moved_frac` (contrôle positif de la sonde) = **0.06** : l'agent n'est plus TOTALEMENT
figé (vs 0.00 en isolé) mais reste **passif face à un apex STATIQUE**. Résultat, 3 modes identiques :
approche ≈ 0.07 pour Mammouth ET Leurre -> **disc ≈ 0**. (Fix au passage : `_disable_kuzu` neutralise désormais
aussi `AsyncMemoryRetriever.start` — le retriever tournait pendant toutes les mesures ; sans effet ici
— `in_mem=0`, cache vide — le résultat est bit-identique retriever ON/OFF, mais le thread/leak est supprimé.)

**Convergence de TOUTES les sondes** (roaming, isolée, in-contexte) : les champions in-world sont des
FOURRAGEURS RÉACTIFS — ils engagent l'apex qui devient adjacent (mobile) mais ne NAVIGUENT pas vers un apex
statique par type ; `INTACT ≡ VISIBLE ≡ ABLATE` partout. La survie in-world ne sélectionne PAS de cognition
d'apex par type : elle est résolue réactivement. C'est une confirmation directe de [[EDR-S2-012]] (« la survie
n'a aucun contenu cognitif ») pour la modalité apex/mémoire, et l'explication concrète de « in-world 0 ».

## Dernière marche RÉALISÉE (discrimination réactive) — même mur : champions QUASI-STATIONNAIRES
Protocole : deux apex à mobilité IDENTIQUE (`apex_speed=0.5`, pas de confond mouvement) qui s'approchent des
agents in-contexte -> l'agent devrait FUIR le Leurre / ENGAGER le Mammouth. Résultat : `moved_frac` reste
**0.06** (les apex qui foncent sur l'agent ne le font PAS bouger davantage), disc ≈ +0.02 (chance),
visible ≡ memory ≡ ablate. **Cause racine enfin nette** : les champions sont QUASI-STATIONNAIRES — ils bougent
~6 % des ticks près d'un apex, même sous un apex qui les charge ; ils survivent en laissant la nourriture venir
à eux. Toute discrimination qu'ils auraient vivrait dans la décision d'ATTAQUE (nœud immobile), PAS dans le
mouvement — et les métriques COMPORTEMENTALES (mouvement ; kills qui exigent un pack) ne peuvent PAS l'extraire
d'un agent immobile. **~6 angles de mesure (roaming/isolé/in-contexte × statique/mobile), tous défaits par la
même near-stationarité.**

## Verdict de méthode (ce qui EST établi)
Toujours PAS de verdict « mémoire in-world oui/non » — et surtout PAS de CONTRÔLE POSITIF propre (aucune sonde
comportementale ne montre un champion qui discrimine par type). Mais le POURQUOI est borné : le comportement
des champions (near-stationarité réactive) défait toute métrique comportementale de discrimination. La vraie
dernière marche n'est donc PAS comportementale mais l'**inspection directe du logit d'ATTAQUE** : présenter au
champion une obs in-contexte réaliste où il est adjacent à un Mammouth vs un Leurre (sous occlusion + ablation)
et lire si son logit d'attaque diffère par type — dense (chaque obs = 1 décision), immunisé contre l'immobilité.
⚠️ défi connu (le frozen-agent montre qu'une obs ISOLÉE est dégénérée -> il faut une obs de contexte réel).
Le substrat EST capable ([[EDR-EVO-002]], 8/8), l'infra est prête. Effort dédié.

Converge [[EDR-EVO-002]], [[EDR-S2-012]], [[EDR-090]], [[EDR-INFRA-001]], REF-EXPERIMENT-PREFLIGHT.
