---
id: EDR-RETAIN-COMPOSE-LR
type: EDR
title: "Le mur retain+compose était un ARTEFACT DE PAS D'APPRENTISSAGE — à lr=0.002 le 2-tick appris passe de 0.173 à 0.923 (n=12, séparation totale 0/144)"
status: active
verdict: RETAIN_COMPOSE_WALL_IS_A_LEARNING_RATE_ARTIFACT
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-RETAIN-COMPOSE]
---

## Question

[[EDR-RETAIN-COMPOSE]] a livré le verdict `RETENTION` sur la foi d'un `learned = 0.173` (2 pas :
encode(key) → use(q), rétention APPRISE) face à un `oracle = 0.971` (key injecté par fiat en état) et un
`same_tick = 0.969` (opérandes co-présents). Ce record avait lui-même NOMMÉ la direction qui le menaçait :
« un `learned` sous-évalué par artefact (le nul `learned` ≤ bar serait un plancher de plomberie, pas de
rétention) : ce risque n'est PAS couvert par ce contrôle de plateau — il repose sur le résultat BILINEAR
antérieur ». Or l'appui BILINEAR est CIRCULAIRE : sonde sœur, même Adam, même `n_agents=16`, même `lr=0.02`
(`tools/bilinear_composition_probe.py:163`, `:115`).

**Question mesurée ici** : le nul `learned` est-il une propriété du SUBSTRAT, ou une propriété du PAS
D'APPRENTISSAGE ?

## Méthode

**Même fonction, même calibration, une seule variable changée.** Appel de la fonction CALIBRÉE
`run_retain_compose_diagnostic_probe` (`tools/retain_compose_diagnostic_probe.py:101`) — aucun code de sonde
modifié, aucune ré-implémentation — à `episodes=600`, `n_agents=16`, `K=6`, `eval_batches=40` (défaut),
`conditions=("same_tick","oracle","learned")`, `bar=1/K+0.15=0.3167`, **12 seeds** (0-11), aux deux points
`lr ∈ {0.02, 0.002}` (une décade). Pur torch CPU, `torch.set_num_threads(1)`, FOREGROUND, aucun bail `kuzu`,
aucun monde. Runtime mesuré : **337.2 s** (lr=0.02) + **344.5 s** (lr=0.002).

Le bras `lr=0.02` est une **réplication directe** du record rétracté : s'il ne reproduisait pas ses chiffres,
la comparaison ne vaudrait rien.

## Résultat

**Médianes n=12, par point de `lr` :**

| lr | same_tick | oracle | learned | `gap_verdict` rendu par la sonde |
|---|---|---|---|---|
| **0.02** (le record rétracté) | 0.969 | 0.971 | **0.173** | `RETENTION` |
| **0.002** | 0.937 | 0.945 | **0.923** | `INCONCLUSIVE` |

Le bras `lr=0.02` **reproduit le record au chiffre près** (record : same_tick 0.969 / oracle 0.971 /
learned 0.173).

**Séparation par-seed sur `learned` — TOTALE** : `min(lr=0.002) = 0.897 > max(lr=0.02) = 0.192`,
**0/144 chevauchement** (12 × 12 paires) ; **12/12** seeds au-dessus de `bar=0.3167` à lr=0.002, **0/12** à
lr=0.02 → test de signe **p = 2⁻¹² ≈ 2.4e-4**. L'écart `learned`↔`oracle` passe de **0.798 à 0.022** : à
lr=0.002, apprendre la rétention coûte 2.2 points d'accuracy face à la recevoir par fiat.

**Toutes les valeurs par seed, INLINÉES** (⚠️ `results/retain_compose_lr_replication.json` n'est PAS
versionné — `.gitignore:14` ignore `results/` ; sans cette inline, la preuve disparaît au premier clone).
Ordre = seeds 0 → 11.

`lr = 0.02` :

| condition | valeurs par seed (0→11) | médiane |
|---|---|---|
| same_tick | 0.984, 0.966, 0.959, 0.972, 0.948, 0.953, 0.964, 0.956, 0.980, 0.975, 0.975, 0.978 | 0.969 |
| oracle | 0.972, 0.964, 0.978, 0.980, 0.969, 0.980, 0.969, 0.970, 0.978, 0.970, 0.970, 0.981 | 0.971 |
| **learned** | 0.192, 0.175, 0.188, 0.173, 0.166, 0.172, 0.169, 0.166, 0.184, 0.145, 0.181, 0.150 | **0.173** |

`lr = 0.002` :

| condition | valeurs par seed (0→11) | médiane |
|---|---|---|
| same_tick | 0.922, 0.941, 0.930, 0.939, 0.950, 0.969, 0.936, 0.938, 0.927, 0.925, 0.947, 0.930 | 0.937 |
| oracle | 0.953, 0.947, 0.906, 0.970, 0.931, 0.948, 0.938, 0.923, 0.942, 0.952, 0.948, 0.934 | 0.945 |
| **learned** | 0.933, 0.928, 0.897, 0.953, 0.917, 0.964, 0.900, 0.914, 0.906, 0.905, 0.941, 0.939 | **0.923** |

Triées, les 24 valeurs `learned` : lr=0.02 → [0.145, 0.150, 0.166, 0.166, 0.169, 0.172, 0.173, 0.175,
0.181, 0.184, 0.188, 0.192] ; lr=0.002 → [0.897, 0.900, 0.905, 0.906, 0.914, 0.917, 0.928, 0.933, 0.939,
0.941, 0.953, 0.964].

## Cause racine — `n_agents` n'est pas un minibatch

`_train_eval_condition` construit UNE population de `n_agents=16`
(`tools/retain_compose_diagnostic_probe.py:77`) et fait `F.cross_entropy(logits, tgt)` sur les 16 lignes
(`:86`). Mais **chaque agent porte ses PROPRES `W/U/V/W_bl`** (`src/agents/backend_torch.py:85-86` et
`:113-115`) : les 16 lignes ne partagent aucun paramètre. Chaque jeu de paramètres reçoit donc
**exactement 1 exemple par pas d'optimisation** — le batch effectif est **1**, pas 16 — sous
`torch.optim.Adam(..., lr=lr)` avec `lr=0.02` par défaut (`:80`, signature `:101`).

Ce que ce pas discrimine :

- `same_tick` (`:51-52`) et `oracle` (`:53-58`) sont des problèmes à **UN SEUL `_step`**, bien
  conditionnés : ils tolèrent le pas (et même : ils tolèrent MIEUX 0.02 que 0.002, cf. Portée).
- `learned` (`:59-61`) enchaîne **DEUX `_step`** avec BPTT et doit coordonner l'encodeur (pas 1) et le
  compositeur (pas 2) à travers le carry : à batch effectif 1 et lr=0.02, il diverge.

Le réglage avait été validé **IMPLICITEMENT sur les conditions faciles**, puis appliqué à la condition qui
PORTE le verdict. Le verdict mesurait le réglage, pas le substrat.

## Pourquoi la calibration était aveugle

La sonde était déclarée calibrée (`"run_retain_compose_diagnostic_probe": ["*"]`,
`tests/sandbox/test_instrument_calibration.py:163`) et le cliquet
(`tools/check_instrument_calibration.py`) ne signalait rien. Mais ses **deux** contrôles —
`test_retain_compose_same_tick_composes` (`:1658`, positif) et
`test_retain_compose_decorrelated_oracle_is_floor` (`:1668`, négatif/plancher) — sont TOUS DEUX des
conditions à **UN SEUL `_step`**.

**Par construction, aucun ne POUVAIT voir une pathologie propre au régime 2-pas.** La batterie rendait un
`OK` parfaitement VALIDE dans son régime et sans portée hors de lui. C'est le point méthodologique de ce
record : *un contrôle positif dans le régime FACILE ne calibre pas le régime DUR* ; la couverture d'un
instrument doit être déclarée **par RÉGIME**, pas par fonction.

## Portée (bornée)

Ce record RETIRE un verdict ; il n'en installe pas un symétrique à sa place.

- **`lr=0.002` rend `INCONCLUSIVE`, pas `SOLVED`.** La règle de la sonde (`:112-117`) exige
  `same_tick > bar ET oracle > bar ET learned ≤ bar` pour dire `RETENTION` ; à lr=0.002 aucune branche ne
  se ferme. **Ceci ne prouve PAS que le 2-tick soit « résolu » en général** — il est mesuré appris à 0.923
  sur CE proxy (`(q+key)%K`, K=6, rang 16, `episodes=600`, supervision directe par `_step`), pas en
  émergence, pas in-world, pas à un autre délai que D=1.
- **Aucun `lr` n'est optimal pour toutes les conditions — et c'est précisément le point.** À budget égal,
  baisser le pas DÉGRADE les conditions 1-pas : `same_tick` 0.969 → 0.937 et `oracle` 0.971 → 0.945
  (légèrement sous-entraînées à `episodes=600`). Il n'existe donc pas de « bon réglage » à figer : quand
  deux bras d'un verdict n'ont pas la même difficulté d'OPTIMISATION, le réglage n'est pas une nuisance,
  c'est un **FACTEUR** — et il doit être balayé, pas choisi.
- **Ce qui est établi ici est NÉGATIF** : le nul `learned` de [[EDR-RETAIN-COMPOSE]] ne supporte pas le
  verdict `RETENTION`. H1 (« rétention apprise ») ne tient plus. H2 (« lecture d'état ») n'a jamais été
  réfutée et ne l'est pas davantage ici — elle redevient simplement non testée.
- **Corroborants NON RÉPLIQUÉS** (une seule passe d'agent, hors du run n=12 ci-dessus ; à re-mesurer avant
  toute citation comme fait) : (a) le key est linéairement décodable à **1.000** depuis l'état porté
  `H1[:, 59:]` **dès l'init**, réseau non entraîné — il était TOUJOURS retenu ; (b) une **chirurgie
  constructive** des poids résout le 2-pas à **0.969**, ≈ oracle — la capacité est prouvée PAR
  CONSTRUCTION ; (c) ré-entraîner cette solution construite à `lr=0.02` la **DÉTRUIT** (0.977 → 0.272),
  alors qu'à `lr=0.002` elle tient (0.981). Les trois pointent dans le même sens que le fait n=12, mais
  aucun n'a le statut de mesure répliquée.
- **Dette de barre, héritée, mesurée sur la sonde sœur et NON RÉPLIQUÉE** : `bar = 1/K + 0.15 = 0.3167`
  (`tools/retain_compose_diagnostic_probe.py:108`, `tools/bilinear_composition_probe.py:174`) est
  **0.072 SOUS** le plafond structurel du substrat PLAIN mesuré en forme close (**0.3889**, optimisation
  directe plein-batch des 36 paires, 8 restarts ; contrôle positif du même optimiseur sur une table libre
  non séparable : 1.000). Un substrat prouvablement incapable de composer PEUT donc franchir cette barre.
  Cela ne touche pas le résultat ci-dessus (la bascule mesurée est de 0.173 à 0.923, sept fois la largeur
  de la zone douteuse), mais toute sonde utilisant cette barre hérite du défaut.
- **Un seul substrat, un seul proxy, deux points de `lr`** — pas un balayage. Rien ici ne dit où est
  l'optimum, seulement que le verdict BASCULE entre 0.02 et 0.002.

## Contamination héritée — à RE-MESURER, pas à conclure

Le même régime (`n_agents=16` non-minibatch, Adam, `lr ≥ 0.02`, conditions à 2 pas) porte d'autres
conclusions actives. **Aucune n'est rétractée ici** : propager un signe par raisonnement au lieu de le
mesurer est exactement la classe E8 du registre.

- `tools/bilinear_composition_probe.py:163` — mêmes `lr=0.02` et `n_agents=16`, même Adam (`:115`). La
  conclusion SECONDAIRE de [[EDR-BILINEAR]] (« le confond dominant du nul de la Tâche 2 était la
  RÉTENTION », bilinéaire 0.178 sous plain 0.218, condition `same_tick=False, credit_mode="supervised"`)
  a été **RE-MESURÉE sur sa propre sonde**, n=12, dans cette même passe — pas inférée par analogie
  (contre-exemple gelé `test_bilinear_composition_null_under_retention_is_lr_dependent`) : à `lr=0.02`
  bilinéaire **0.1789** sous plain 0.2180, `unlocked=False` (reproduit le nul du 2026-08-03 au chiffre
  près) ; à `lr=0.002` bilinéaire **0.3797** > bar, `unlocked=True` ; séparation par-seed TOTALE
  (max 0.2016 < min 0.3500, **0/144**, 12/12). **La clause n'est donc PAS établie** — elle mesurait le
  réglage. ⚠️ Mais 0.3797 est loin du 0.932 du régime 1-pas et à peine au-dessus d'une barre douteuse :
  cela ne dit PAS que le 2-pas soit résolu. Le résultat PRINCIPAL de ce record (`same_tick`, un seul
  `_step`, plain 0.271 vs bilinéaire 0.932) est hors du régime suspect et reste INTACT.
- [[EDR-LANG-MEMORY]] — tâche D=2 (donc 2 pas) déclarée à `K=6, n_agents=16, lr ∈ {0.02, 0.05}` (`:116`),
  soit le même batch effectif 1 avec DEUX pas tous deux ≥ 0.02. Son verdict NÉGATIF a servi à REFUSER de
  graver l'arête `language→memory` du graphe AGI-Taxonomy. **À re-mesurer à lr=0.002 avant toute
  annotation de verdict** ; si le négatif tombe, c'est une arête du graphe qui se rouvre — un record à part
  entière, pas une note en marge.

## Ce que ça débloque

La prescription du record rétracté (« construire un mécanisme de rétention apprise : porte d'oubli,
registre ») est **SANS OBJET** : le substrat actuel retient déjà (décodabilité 1.000 dès l'init,
corroborant non répliqué) et apprend le 2-tick à 0.923 au bon pas. Le sous-projet suivant n'est pas un
nouveau mécanisme, c'est un **audit de réglage** du stock de conclusions de l'arc
BILINEAR / LANG-MEMORY / MEM-PERCEPTION / RETAIN-COMPOSE, tous mesurés à `lr=0.02`.

Cf. [[EDR-RETAIN-COMPOSE]] (rétracté), [[EDR-BILINEAR]] (clause secondaire suspecte),
[[EDR-LANG-MEMORY]] (régime suspect, à re-mesurer).
