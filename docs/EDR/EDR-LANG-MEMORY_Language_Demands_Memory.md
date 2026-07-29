---
id: EDR-LANG-MEMORY
type: EDR
title: "NÉGATIF/NON-MESURABLE : « language demands memory » — la capacité langage (composition (q+key)%K) n'émerge pas de façon fiable sur ce substrat, l'arête n'est PAS gravée (instrument calibré, garde d'aliasing prouvée sensible, antécédent absent)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER, REF-AGI-TAXONOMY]
---

## Question
Troisième arête candidate du graphe AGI-Taxonomy : « language demands memory » ? Un agent qui doit
appliquer un code appris — LANG = `(q+key)%K`, où `key` est encodé puis DOIT être retenu via l'état
récurrent `H` PORTÉ (encode → délai → quête) — a-t-il besoin causalement de la mémoire ? C'est la
1ʳᵉ arête candidate du graphe à demander une ablation **SUBSTRAT** (reset de `H`) plutôt qu'une ablation
d'ENTRÉE : les deux arêtes précédentes (`language→perception`, `memory→perception`) dérangeaient l'ENTRÉE,
donc `functional_aliasing='n/a'` leur suffisait. Ici le garde CALIB-ALIAS `functional_aliasing` DOIT être
MESURÉ (`pass`/`fail`), jamais `n/a`.

## Méthode
Sonde `tools/language_memory_demand_probe.py` (livrée + calibrée Tâche 1, commit `fb783e8` ; leviers
diagnostiques Tâche 2, `train_control`/`weight_decay`, commit `ff64849`). Un MÊME agent (`MambaAgent`,
tête d'action à 8 logits partagée) apprend deux capacités distinguées par les slots actifs de
l'observation : LANG = `(q+key)%K` (nécessite `key` retenu par `H`) ; CONTROL = copier `c`
(feedforward, 1 tick, indépendant de la mémoire — contrôle de spécificité pour l'ablation substrat).
Ablation = reset de `H` à l'usage. Verdict LANG via `ablation_verdict` (floor=1/K). Verdict CONTROL via
le garde `functional_aliasing` (leakage entre `control_intact`/`control_ablated` : `SURGICAL` si
`leakage<=tol` et la réponse de LANG à l'ablation est réelle, `VACUOUS_ABLATION` si LANG ne bouge pas,
`FUNCTIONAL_LEAK` si CONTROL bouge aussi).

**Calibration (Tâche 1, 3 cas, `pytest tests/sandbox/test_instrument_calibration.py -k "lm_oracle or
lm_random or lm_leaky"` → 3 passed)** :
- `memory_mode="oracle"` (rétention parfaite par fiat) → `verdict=X_DEMANDED`. PASS.
- `memory_mode="random"` (guess décorrélé) → `verdict!=X_DEMANDED`. PASS.
- `control_mode="leaky"` (CONTROL forcé de dépendre du `key` retenu au lieu de `c`) →
  `functional_aliasing="fail"`, `alias_verdict="FUNCTIONAL_LEAK"`. PASS — **le garde est prouvé
  SENSIBLE** : une fuite réelle est bien détectée, première fois qu'il est exercé sur une vraie ablation
  SUBSTRAT (les deux arêtes précédentes ne l'ont jamais exercé, `n/a` par construction).

L'instrument est donc SAIN sur les deux versants (oracle→positif, aléatoire→inerte, fuite→détectée). Ce
qui suit n'est PAS un défaut de l'instrument — c'est l'absence de l'ANTÉCÉDENT mesuré (la capacité LANG
elle-même) sur ce substrat, dans les budgets explorés.

## Résultat — LANG ne franchit pas le seuil d'émergence au réglage de la spec (D=2)

Seuil d'émergence retenu (cf. précédent LANG-PERCEPTION/MEM-PERCEPTION) : `1/K+0.15≈0.317` (K=6), pas le
simple plancher de hasard `1/K≈0.167`.

**D=2 (vraie rétention sur 2 ticks de délai, réglage de la spec) : NUL PROPRE sous tous les leviers
essayés, jusqu'à 15000 épisodes** — sweep complet en Tâche 2 :

| levier | episodes | seeds | `lang_intact` médiane | franchit 0.317 ? |
|---|---|---|---|---|
| baseline (`train_control=True`, `wd=0`) | 1200 | 0,1,2 | 0.166 | non |
| `train_control=False` (isole l'interférence de tête partagée) | 1200 | 0,1,2 | 0.197 | non |
| `train_control=False`, `weight_decay=1e-2` | 3000→15000 | 0,1,2 | 0.159→0.172 | non (5 seeds distincts, plat) |
| `train_control=False`, `weight_decay=1e-3` | 3000→15000 | 0 | 0.161→0.167 | non |

Aucune tendance ascendante même à ×12.5 le budget Tâche 1. `weight_decay` (recherche de grokking) ne
débloque rien à `D=2` ; retirer CONTROL de l'entraînement (`train_control=False`) aide modestement
(0.166→0.197) mais reste très en dessous du seuil.

**D=0 (query immédiatement après l'encodage — `H` porte quand même `key` sur 1 pas récurrent, l'ablation
mord toujours) : signal MARGINAL, reproductible mais fragile.** `train_control=False, weight_decay=0,
episodes=3000` : `lang_intact` = [0.308, 0.316, 0.327, 0.328, 0.336, 0.348] sur 6 seeds indépendants
(0-2 puis réplication 3-5), **médiane 0.328**, bande étroite — 6/6 seeds franchissent ou approchent le
seuil, la première config du diagnostic à le faire de façon reproductible sur plusieurs seeds plutôt qu'en
un point isolé. `weight_decay=1e-3` à ce même réglage NUIT (médiane retombe à 0.156, au plancher).

**Aucune config ne tient les deux jambes de la mesure simultanément (§ci-dessous), et D=0 est une version
affaiblie de la question posée** (rétention sur 1 pas récurrent encode→quête consécutifs, pas un vrai
délai) — ce n'est donc pas retenu comme mesure de l'arête `language→memory` telle que spécifiée.

### Pourquoi le garde à deux capacités ne peut pas être appliqué proprement ici
Le config gagnant à D=0 (`train_control=False`) **n'entraîne jamais CONTROL** : `control_intact` et
`control_ablated` restent tous deux proches du hasard (poids jamais entraînés sur cette tête), donc
`functional_aliasing="pass"` y est **vide de sens** — une différence quasi nulle entre deux mesures de
hasard est garantie par construction, pas une preuve de chirurgie. À l'inverse, la seule config où CONTROL
apprend réellement et reste chirurgical (`train_control=True`, D=0 : CONTROL sature à 1.0, leakage=0.0)
fait retomber LANG à médiane 0.280, avec seulement 1/3 seeds au-dessus du seuil au lieu de 6/6. **Aucune
config testée ne donne, simultanément, un LANG fiable ET un CONTROL entraîné-donc-probant** — condition
nécessaire pour un verdict n=12 défendable sur les deux dimensions à la fois (X_DEMANDED sur LANG,
`functional_aliasing` mesuré et non-vacueux sur CONTROL).

## Isolation — la difficulté est représentationnelle, pas un problème de crédit ou de budget

- **REINFORCE tronqué (`learn_episode`) ET BPTT réel (`learn_episode_bptt(truncate=False)`)** échouent de
  façon équivalente (D=1 : 0.205 vs médiane REINFORCE comparable ; D=2 : 0.167) — ce n'est pas un artefact
  du crédit 1-pas tronqué.
- **Imitation SUPERVISÉE + BPTT** (`imitate_episode_bptt`, masquée sur le dernier pas — élimine toute
  question de crédit RL) échoue AUSSI **à D=2** (0.202 à lr=0.02/1200 épisodes) — le même D que REINFORCE
  tronqué et BPTT réel ci-dessus (D=2 : 0.167) : les **trois** méthodes de crédit échouent ensemble,
  proprement, au réglage de la spec. C'est sur ce triplet D=2 que repose l'argument d'isolation : la
  composition `(q+key)%K` de deux one-hot injectés à des ticks séparés reste dure à représenter/apprendre
  pour ce substrat même sous supervision directe. → **le problème n'est pas l'assignation de crédit, il
  est représentationnel** (le substrat contractif ne compose pas facilement deux entrées one-hot injectées
  à des ticks différents).
  (Le chiffre D=0 de cette même méthode supervisée, 0.216 à lr=0.05/3000 épisodes, n'est PAS retenu comme
  preuve confirmatoire : lr et régime différents du sweep D=0 principal — et EN TENSION avec le fait que
  le RL seul APPREND déjà à D=0 [`train_control=False`, médiane 0.328, § résultat ci-dessus] : une
  supervision qui sous-performe le RL au même D est l'inverse de ce qu'annoncerait un mur
  représentationnel propre. Point confondu, mentionné ici pour mémoire, non porteur de l'argument.)
- **Contrôle de sanité (le harnais fonctionne)** : une tâche de pur RAPPEL (`_carry` puis test vide,
  cible=`key`, SANS combinaison) apprend vite et bien avec exactement la même mécanique
  (D=1/ep=600→acc=0.880 ; D=1/ep=1200→0.903 ; D=2/ep=1200→0.564). La rétention seule n'est pas le
  problème — l'échec est spécifique à la fonction de COMBINAISON `(q+key)`, pas à la mécanique
  d'entraînement/éval, ni à la rétention per se.
- **Les leviers prescrits par la revue adversariale ont été essayés, pas juste évoqués** : isoler
  l'interférence de tête partagée (`train_control=False`) et chercher un régime de grokking
  (`weight_decay` × budget ×12.5) sont les deux voies les plus économiques pour distinguer « pas assez
  d'épisodes/interférence » de « le substrat n'y arrive pas ». Aucune ne débloque D=2 ; seule la
  suppression du délai (D=0) bouge l'aiguille, et seulement partiellement.

## Portée (bornée)
- Un seul substrat (`MambaAgent`/`TorchPopulationModel`, tête d'action 8 logits partagée), un seul proxy
  (application de code à un opérande retenu, `(q+key)%K`), K=6, n_agents=16, lr∈{0.02,0.05}, jusqu'à 15000
  épisodes, D∈{0,1,2}.
- Les leviers essayés sont bornés : `train_control`, `weight_decay`, budget, D, méthode de crédit
  (REINFORCE tronqué / BPTT / supervisé). Non essayés : architecture différente (tête bilinéaire — cf.
  précédent `planner-depth1-refuted`/PLAN-001, où une interaction bilinéaire a débloqué la composition
  qu'un modèle affine ne pouvait pas apprendre), tâche à rythme observable (cf. EDR-202 KCHAIN), n_agents
  plus grand, curriculum D croissant.
- Aucun run n=12 n'a été lancé (`n_floor=12` de `demand_marker.ablation_verdict` bloque tout verdict
  positif sous n=6 — `INCONCLUSIVE` même avec `ratio>=1.5`/`collapse=True`). Ce n'était pas l'objectif :
  ce diagnostic (n=3-6 par config) visait à établir si l'antécédent existe, pas à trancher un verdict.
  Coût borné : aucun run individuel n'a dépassé ~44 min (sous forte contention machine partagée), torch CPU
  pur, foreground, sans bail `kuzu`, sans monde.

## Ce que ça débloque
- **La méthodologie du graphe se comporte correctement** : elle REFUSE de graver « language demands
  memory » quand l'antécédent (une capacité langage compositionnelle vivante) n'existe pas sur le
  substrat. Écrire `functional_aliasing='n/a'` aurait été malhonnête pour une ablation SUBSTRAT (le
  validateur `check_agi_taxonomy.py` exige `pass` ou `n/a`+`specificity_control` — aucune des deux
  conditions n'est honnêtement satisfaite ici) ; forcer un run n=12 sur une config bancale (LANG non fiable
  OU CONTROL non probant) aurait produit un chiffre sans base. `data/agi_taxonomy/demands.json` reste
  inchangé (2 arêtes : `language→perception`, `memory→perception`) — **aucune arête gravée par ce
  travail**.
- **L'instrument reste livré et prêt** : calibration (oracle/aléatoire/leaky) verte, garde
  `functional_aliasing` prouvé SENSIBLE sur une vraie ablation substrat (1ʳᵉ fois dans ce graphe). Si un
  futur substrat/architecture fait émerger LANG de façon fiable ET entraînable en même temps que CONTROL,
  la sonde peut mesurer l'arête sans modification.
- **Reconnexion à la thèse centrale du dépôt** : le verrou observé ici — composer/lier deux entrées reçues
  à des ticks séparés (`(q+key)`) — est le même type de verrou que celui documenté dans
  `planner-depth1-refuted` (PLAN-001/003 : un modèle AFFINE ne compose pas, un terme bilinéaire débloque)
  et dans `sota-gap-substrate`/`decisive-substrate-thesis-test` (le verrou est le MÉCANISME DE CRÉDIT/le
  MODÈLE, pas la capacité brute du substrat). Ce nul n'est donc pas isolé : il est cohérent avec le
  diagnostic transversal du dépôt sur la composition/binding, et pointe vers deux directions futures
  explicites et non explorées ici — une tête bilinéaire (précédent direct PLAN-001), ou une tâche fournissant
  un rythme observable pendant l'entraînement (précédent EDR-202 KCHAIN) — plutôt que vers plus
  d'épisodes ou un réglage plus fin du même modèle affine.

Cf. `.superpowers/sdd/2026-07-28-language-memory-demand-edge/task-1-report.md`,
`.superpowers/sdd/2026-07-28-language-memory-demand-edge/task-2-report.md` — artefacts SDD
**session-locaux, non trackés dans git** (`.superpowers/sdd/.gitignore`) : ces deux chemins sont morts
pour un lecteur du dépôt seul. Les chiffres qu'ils contiennent sont préservés dans le fichier committé
`results/lang_memory_diagnostic.json` (résumé des configs et verdicts de ce diagnostic — source de
vérité committée).
