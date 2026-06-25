# Roadmap NAS — Neural Architecture Search (axe Scientifique)

> **Domaine** : le moteur évolutif lui-même (génotype → phénotype → sélection). C'est l'axe science
> qui cherche *la structure* de l'AGIseed, par opposition aux capacités cognitives (langage, planning).
> **Vision** : `0_Taxonomy_Evolution.md` + `1..4_*_NAS.md` (Micro/Meso/Macro/Meta) à la racine.
> **Horizon court-terme** ci-dessous ; **someday** → `docs/BACKLOG.md` (§NAS).
>
> Métrique-reine (X2) : une innovation NAS est *bonne* si elle **transfère mieux**
> (`tools/curriculum_transfer.py`, verdict TRANSFÈRE/NEUTRE/NUIT) — *validité avant éclat*.

---

## 0. Vision vs réalité (l'écart)

La vision déclare un NAS **fractal à 4 échelles** où un algo génétique génère/mute/détruit à chaque
échelle. Le moteur **réel** (`src/seed_ai/`, `src/agents/mamba_agent.py`) est, en pratique, un
**Micro-NAS** : on évolue un connectome plat (matrice d'adjacence `W`, topologie variable) avec
2 toggles Macro (`organ_genes`) et 2 motifs Meso bolt-on (skip, gate). Le **Meta-NAS (essaim,
économie de compute, HGT, consensus) est quasi absent** — c'est l'écart le plus large.

---

## 1. Re-audit génotype → phénotype (2026-06-24) — TABLE DE VÉRITÉ

> ⚠️ **Ce re-audit REMPLACE les claims périmés de `docs/SCAN_GLOBAL.md`** sur les « gènes morts ».
> Le SCAN n'avait audité que `rl_evolution.recurrent_forward` (chemin legacy) ; la **production**
> tourne sur `MambaBatchModel.forward`. Trois claims du SCAN tombent, une nouvelle dette apparaît.

| Gène | Forward **prod** (`MambaBatchModel`) | Forward legacy (`rl_evolution`) | Lu par la mutation | Verdict |
|---|---|---|---|---|
| `W` (+ topologie) | ✓ `mamba_agent.py:440` | ✓ | substrat | **ACTIF** |
| `thresholds` | ✓ `:446` | ✗ | étendu `add_node` `mutation.py:267` | **ACTIF** (EDR 031) |
| `W_router` | ✓ `:438` | ✗ | ✓ `mutation.py:121` | **ACTIF** (EDR 031) |
| `organ_genes[0]` MCTS | ✓ `:497` | ✓ `rl_evolution.py:41` | toggle `mutation.py:273` | **ACTIF** |
| `organ_genes[1]` attention QKV | ✓ `:450` | ✗ | toggle | **ACTIF** (prod uniquement) |
| `mutation_genes[0]` weight-rate | — | — | ✓ `mutation.py:110` | **ACTIF** |
| `mutation_genes[1]` weight-power | — | — | ✓ `mutation.py:111` | **ACTIF** |
| `mutation_genes[4]` prune-rate | — | — | ✓ `mutation.py:134` | **ACTIF** |
| `mutation_genes[5]` T_micro_ticks | ✓ MCTS | ✓ `rl_evolution.py:45` | clip `:249` | **ACTIF** |
| `mutation_genes[2]` add_node-rate | — | — | ✗ (`config` `mutation.py:263`) | **MORT** — auto-tuné, jamais lu |
| `mutation_genes[3]` add_conn-rate | — | — | ✗ (`config` `:268`) + write gated `:294` | **MORT** — auto-tuné, jamais lu |
| `bytecode` | ✗ | ✗ | compile-boost **gated off** `:280` | **MORT en prod** (vivant: banc `evolution.py:57`) |
| `memory_cache` | ✗ | ✗ | `clone()` force `None` `:52` | **INERTE** — jamais écrit |

### Findings structurants
1. **Deux forwards divergents** : `MambaBatchModel.forward` (prod : thresholds + router + attention +
   world_model) ≠ `rl_evolution.recurrent_forward[_batch]` (legacy : ignore thresholds/router/attention).
   Tout outil/banc qui évolue via `recurrent_forward` sélectionne un **phénotype différent de la prod**.
2. **Auto-tuning partiellement illusoire** : `mutation_genes[2]/[3]` (taux de croissance topologique)
   sont mutés et hérités mais **jamais consultés** — `apply_mutations` gate `add_node`/`add_connection`
   sur le `MutationConfig` global. Seuls `[0],[1],[4],[5]` sont réellement auto-tunés.
3. **`bytecode` mort en prod** : son unique canal (compile-boost de `add_connection_rate`) est gated
   derrière `ACTIVE_EXP_VARIABLE=="METAPROG"` (off par défaut). En run normal : pur bruit de copie.
4. **`memory_cache` vestigial** : `clone()` le remet à `None` à chaque reproduction.
5. **`world_model=None` par défaut** dans `MambaBatchModel.__init__` ; doit être injecté par le monde
   (câblé dans `world_1_stoneage` selon SCAN ; **à re-vérifier par monde de prod**).

### Décision (suite du re-audit) : par gène, élaguer / câbler / laisser
- `mutation_genes[2],[3]` → **trancher** : soit les *câbler* (faire lire `genome.mutation_genes[2]/[3]`
  par `apply_mutations` au lieu du config → vraie auto-adaptation des taux de croissance, façon EDR 031),
  soit les *retirer* de l'auto-mutation (réduire la dérive). 🔬 Tester par X2.
- `bytecode` → **trancher** : *câbler* dans le forward batch (le décodeur per-node existe
  `evolution.py:57-66`, à porter) = finir la Vague 1 ; ou *élaguer* du génome de prod.
- `memory_cache` → **élaguer** (inerte sans ambiguïté) — non-régression attendue.
- **Réconcilier les deux forwards** (dette transverse) : `recurrent_forward` devrait refléter les
  câblages EDR 031, sinon les bancs mentent sur le phénotype.

---

## 2. Backlog NAS — propositions (brainstorm 2026-06-24)

Scoré **Impact / Effort / Risque**. ⭐ = trajectoire recommandée vers le fractal sans big-bang.

### Axe A — Optimiser le moteur existant (encodage direct `W`)
- **A1. Hygiène génotype-phénotype** *(M / F / F)* — sur la base de la table §1 : élaguer l'inerte
  (`memory_cache`), trancher `bytecode`/`mutation_genes[2,3]` (câbler vs retirer), réconcilier les
  deux forwards. *(= Phase 0, cf. §3.)*
- **A2. Quality-Diversity / MAP-Elites** — ⚠️ **MESURÉ, NON VALIDÉ (2026-06-24, PR #44)**. Archive
  taille_réseau × palier comportemental, comparée au HoF top-5 (8 seeds, budget égal, apparié,
  `tools/map_elites_compare.py`). **QD ≈ HoF** : median_ratio 0.946, n_fav 3/8, **sign_p=0.727 (non
  significatif)**. Diagnostic-clé : **`coverage = 3.6 cellules / 32`** → l'espace comportemental est
  quasi vide (palier collapse sur survie/forage, taille statique) → **rien à diversifier**. Câblage
  prod NON effectué. *(Idée : dé-bruitage par niche + diversité anti-plateau EDR 075-081.)*
- **A3. Fitness intrinsèque (curiosité)** *(Fort / F / dépend WM)* — fitness = surprise résolue
  (erreur WM qui baisse) au lieu du `life_score` injecté. Open-endedness. Pré-requis : WM branché.
- **A4. Parcimonie réelle dans la boucle vivante** *(M / F)* — le `life_score` live n'a **aucune**
  pénalité de coût structurel (parcimonie seulement dans `evolution.py`, hors biosphère). Pénaliser
  le coût FLOP/énergie du connectome → pression NAS vers l'efficacité. → **variante bio-inspirée plus
  naturelle : D1 (coût métabolique d'activation)** ci-dessous.

### Axe B — Encodage compositionnel (réaliser la vision fractale)
- **B3. Bibliothèque de motifs évolués (KuzuDB)** ⭐ *(Fort / M / M)* — pont incrémental A→B. KuzuDB
  stocke les sous-graphes performants (motifs Meso / organes Macro) ; un nouvel opérateur de mutation
  **insère un motif de la bibliothèque** au lieu d'un seul nœud. Compositionnalité **sans** réécrire
  le décodeur. Exploite l'infra graphe déjà là.
- **B1. Encodage développemental** *(Très fort / Élevé / Élevé)* — le génome devient une séquence d'ops
  Meso/Macro (« insère bottleneck », « réplique ce module ×3 ») au lieu d'une matrice plate.
  Réutilisation, régularité, scaling sous-quadratique. Aligne le code sur les docs Meso/Macro.
- **B2. Encodage indirect CPPN/HyperNEAT** *(Fort / Élevé / Élevé)* — `W` généré par une petite
  fonction sur les coordonnées des neurones. Génome compact, exploite symétrie. Moins auditable que B1.

### Axe C — Meta-NAS (l'essaim, l'écart le plus large)
- **C1. Économie de compute (enchères)** ⭐ *(Fort / M)* — déjà amorcé (le MCTS coûte
  `+0.5 energy_drain`, `mamba_agent.py:42`). Généraliser → marché où les organismes paient en énergie
  pour TTC/dreaming. Sélectionne l'allocation efficiente du calcul (répond à l'angle-mort budget compute).
- **C2. HGT — transfert horizontal de gènes** *(M / M)* — échange de sous-graphes entre champions
  **en cours de vie** via `SwarmTransceiver`/KuzuDB. Le crossover topologique existe déjà.
- **C3. Co-évolution symbiotique** *(M / Élevé)* — fusion permanente de deux organismes qui s'appellent
  souvent. Substrat de l'Arc 5 (Tribu/Culture).

### Axe D — Bio-inspiration insecte (efficacité énergétique & hétérogénéité)
> Source : fiche « Bio-inspiration pour le NAS » (système nerveux des insectes). **Isomorphisme clé** :
> la contrainte énergétique stricte de l'insecte ≡ l'**économie métabolique** de la biosphère AGIseed
> (les organismes meurent de famine — cf. mémoire *mur Lewis*). La fitness « précision / nb d'activations »
> de la fiche n'est donc pas une pénalité à injecter mais une **sélection naturelle** si le coût de calcul
> devient métabolique : l'efficacité *trouvée, pas donnée*.

- **D1. Coût métabolique d'activation** — ❌ **RÉFUTÉ (mesure powered, 2026-06-24)**. Implémenté
  (PR #35) + mesuré (`tools/metabolic_cost_sweep.py`, 8 seeds × coefs {0,0.01,0.03,0.1} × 15 ères,
  banc stoneage sweet-spot). **Fait robuste : `mean_active` reste PLAT (~152/172 nœuds) à tous les
  coefs**, même 0.1 (drain ~15/tick qui coupe la survie 26→8). Le coût métabolique **ne sparsifie
  pas** les connectomes — il ne fait que **starver** (coef 0.1 → NUIT, sign_p=0.008). La sélection ne
  peut pas réduire le nombre de nœuds actifs → `brain_cost` n'est PAS un levier sélectionnable
  (corrobore le mur Lewis intrinsèque + EDR 098). **Garder `metabolic_cost_coef=0.0` (off).**
  *(Idée d'origine : rendre `energy_drain` dépendant des nœuds actifs ; bio §3 fitness.)*
- **D2. Codage clairsemé / KWTA** ⭐ *(Fort / Faible)* — **le pivot après l'échec de D1**. D1 a montré
  que la sélection **ne produit PAS** de sparsité (mean_active plat). Réponse : **l'IMPOSER
  structurellement** — k-winners-take-all : ne garder que le top 1-2 % des activations de `H`, zéro
  ailleurs (force `mean_active` ↓ par construction, pas par sélection). Évite le chevauchement mémoire.
  Micro, peu coûteux. = sparse coding des corps pédonculés (mushroom bodies). Question : la sparsité
  imposée **dégrade-t-elle** la compétence, ou est-elle neutre/bénéfique (≥ efficience) ? *(Bio : §2.C.)*
- **D3. Nœuds typés (hétérogénéité)** ⭐ *(Fort / Moyen)* — gène de **TYPE par nœud** pilotant fan-in/out,
  activation, **portée d'axone** (global vs local) et coût : *unipolaire* (calcul local rapide, edge),
  *bipolaire* (feedforward linéaire), *multipolaire/pyramidal* (hub intégratif, attention globale),
  *anaxonique* (modulation locale, pas de propagation longue). Rompt l'homogénéité actuelle (tous tanh
  dans `W`). Inclut les **neurones géants/hubs** (multipolaire = hub critique au milieu de couches
  légères). Enrichit l'espace Micro/Meso — la contribution signature de la fiche. *(Bio : §1 + §2.B.)*
- **D4. Ganglions décentralisés (modularité asynchrone)** *(Fort / Élevé)* — sous-graphes périphériques
  autonomes (réflexe, haute fréquence) + graphe central stratégique (basse fréquence). **Généralise** le
  réflexe/penseur existant (`organ_genes[0]` MCTS, `rl_evolution.py:41`) à la modularité **spatiale**.
  Macro+Meta. *(Bio : §2.A.)*
- **D5. SNN + STDP (plasticité locale, pivot)** *(Fort / Élevé)* — exploiter le substrat spiking **déjà
  là** (`thresholds`, câblé EDR 031, cf. §1) : activation à impulsions + apprentissage local STDP
  (spike-timing) → élimine la rétropropagation. Gène de **règle d'apprentissage** Micro. Aligné sur le
  finding « thresholds vivants » du re-audit. *(Bio : §2.D.)*

**Séquence Axe D** *(révisée après réfutation de D1)* : ~~D1~~ ❌ → **D2 (KWTA, imposer la sparsité)**
= prochain candidat → D3 (expressivité, nœuds typés) → D4 / D5 (pivots architecturaux).
**Leçon D1** : ne pas espérer que la *sélection* produise une propriété structurelle (sparsité) — la
mesurer d'abord, et si elle n'émerge pas, l'**imposer** (D2) plutôt que la *récompenser* (D1).

### Transversal — méthode & RSI
- **X1. Le NAS comme cible de la RSI** — la boucle LLM (`src/metaprog/rsi_loop.py`, débranchée) propose
  de nouveaux **opérateurs de mutation / motifs Meso**, en s'inspirant des docs Micro/Meso. Recherche
  d'*architecture de la recherche*. Après durcissement sandbox OS (cf. roadmap BACKEND, garde-fous).
- **X2. Transfer-ratio = métrique-reine** *(à poser tôt)* — `tools/curriculum_transfer.py` +
  `tools/transfer_ratio.py` deviennent le **critère d'acceptation** de toute innovation NAS.

### ⚠️ MÉTA-LEÇON (2026-06-24) — confondue par un bug de harnais, puis CORRIGÉE
**Cause réelle des échecs D1/D2/A2 = bug `from_genome`** (hardcode 64/126/172, hidden=−18, jette
l'architecture ; cf. mémoire keystone). Les 3 axes étaient mesurés sur des agents aplatis, PAS sur le
substrat évolué. **Fix gaté `preserve_dims` livré (PR #49)** → re-mesures *non-confondues* :

| Axe | Avant fix (confondu) | **Après fix (powered 8 seeds, vrai substrat 200n)** |
|---|---|---|
| **D2** KWTA sparsité (imposée) | no-op | ✅ **EFFICACE** : sparsifier le hidden AMÉLIORE la compétence (+47 %, keep=0.3, sign_p=0.070). Régularisation. |
| **D1** coût métab. (sparsité sélectionnée) | réfuté | ❌ **TOUJOURS RÉFUTÉ** : `mean_active` PLAT (176–180) à tous les coefs → la taxe ne crée aucune pression de sparsité. +13 % compétence à coef 0.001 NON significatif (sign_p 0.727) ; coef 0.01 effondre la survie. |
| **A2** MAP-Elites (graines 1 taille) | NEUTRE (cov 3.6/32) | NEUTRE (cov **4/32**) — descripteurs plats (taille à 1 bin) |
| **A2 v2** MAP-Elites (graines étalées) | — | **coverage RÉSOLUE 4→~24/32** ; mais QD ne bat pas HoF (median_ratio 0.853, sign_p 0.727). Limiteur résiduel = répertoire comportemental (axe palier, EDR 096), pas la recherche. |

**Leçon affinée (mise à jour 2026-06-24, post-followups)** :
- **Sparsité = imposer, jamais sélectionner** : D2 (masque KWTA) gagne +47 %, D1 (taxe de fitness) est INERTE même sur vrai substrat. Une taxe d'activation ne sparsifie pas — elle entre seulement en conflit avec la survie. Le bon levier est structurel (D2), pas sélectif (D1). **Axe D clos : D2 retenu, D1 abandonné.**
- **A2 = la coverage était un artefact de seeding, pas une limite de la méthode** : étaler les tailles de graine (`MEC_SEED_SPREAD`) restaure la coverage (4→24/32). La vraie question (QD bat-il HoF ?) est désormais mesurée proprement : **non** (0.853, NS). Le verrou n'est plus les descripteurs mais le **répertoire comportemental peu profond** du monde (axe palier effondré, EDR 096). A2 restera neutre tant que le monde n'offre pas de stratégies distinctes utiles → renvoie à la couche 2 du monde au plancher (REFRAME métrique), pas à la recherche NAS.
**Non-régression `preserve_dims` (powered 8 seeds, graine par défaut 172, coef 0)** : compétence OFF vs ON **statistiquement indistinguable** (moy. 409.8 vs 407.3, median_ratio 1.069, n_fav 5/8, sign_p 0.727). → Basculer le défaut ne régresse PAS la compétence de base. **Décision (2026-06-24) : garder GATÉ (défaut OFF) pour l'instant** ; la bascule deviendra une PR dédiée après coordination des sessions parallèles (le geste active la croissance topologique : add_node persiste, réseaux grossissent, cap soft 256, compute↑ — c'est le changement *voulu*, pas une régression).
**Reste** : (a) merger/itérer ; (b) **bascule `preserve_dims=True` par défaut** — mesure verte, en attente de coordination // (PR dédiée).

### Séquençage recommandé (révisé)
- **Phase 0 — Re-audit + hygiène** : §1 livré.
- ~~Phase 1 efficacité/diversité~~ : D1 réfuté, D2 no-op, A2 non validé — **bloqués par le substrat** (voir méta-leçon).
- **Phase SUBSTRAT (nouvelle priorité)** : vraie couche cachée + répertoire comportemental vivant. PUIS re-mesurer A2 (coverage devrait monter) et D-axes.
- **Phase 1 — Recherche + efficacité bio** : A2 (MAP-Elites) + **D1/D2 (coût métabolique + KWTA)**
  — parcimonie bio-inspirée qui attaque le mur énergétique Lewis (remplace A4).
- **Phase 2 — Compositionnalité & hétérogénéité** : B3 (bibliothèque de motifs) + **D3 (nœuds typés)**.
- **Phase 3 — Essaim/saut** : C1 (économie de compute) + **D4 (ganglions)** → B1 (développemental) /
  **D5 (SNN+STDP)** / X1 (RSI propose motifs).

---

## 3. Phase 0 — Re-audit d'abord (EN COURS)

**Décision (2026-06-24)** : le prémisse initial « 2 gènes morts à élaguer » était **réfuté** par la
vérification (thresholds/router vivants). On re-audite proprement AVANT d'élaguer/câbler. + poser X2.

**Livré** : table de vérité §1 (génotype→phénotype, evidence file:line, prod vs legacy vs mutation).

**Reste de Phase 0** :
1. **Poser X2** : documenter `curriculum_transfer`/`transfer_ratio` comme gate d'acceptation NAS ;
   l'invoquer comme baseline avant toute tranche A1.
2. **Trancher les 4 gènes inertes/morts** (par X2, 1 variable à la fois, multi-seed apparié) :
   - `memory_cache` → élaguer (non-régression attendue : prouve l'inertie).
   - `bytecode` → câbler (porter le décodeur per-node dans le forward batch) **ou** élaguer du génome prod.
   - `mutation_genes[2],[3]` → câbler (vraie auto-adaptation des taux de croissance) **ou** retirer.
3. **Réconcilier les deux forwards** (`recurrent_forward` ↔ `MambaBatchModel`) — dette transverse qui
   fausse tout banc évoluant sur le chemin legacy.

> **Discipline** (Commandement 15) : 1 variable par expérience, ≥ ce que la puissance exige,
> verdict par X2 (transfer-ratio appariée), valide ou revert. Élaguer/câbler un gène = **1 variable**.

---

## 4. Audit substrat (2026-06-25) — espace de conception & backlog par axe

Audit *grounded* (3 explorations, evidence file:line). **Constat dominant** : le piège récurrent du
projet n'est PAS « il manque des types » mais **« l'infrastructure existe sans être fonctionnelle/
sélectionnée »** (NTM, RAG, dreaming, self-attention, goal/predictor heads : bâtis, presque jamais
câblés au comportement ni sélectionnés). Cf. EDR 010 (« le monde n'exige pas l'intelligence »).

**Légende** : 🟢 vivant & câblé · 🟡 infra présente mais stubbée/non sélectionnée · 🔴 mort (muté/déclaré, jamais lu) · ⚪ absent.

**Stratégie retenue (robla, 2026-06-25)** : **activer l'existant stubbé → ajouter les primitives manquantes → diagnostiquer**, avec **diagnostic APRÈS CHAQUE activation** (pas en bloc — leçon du confond `from_genome` sur D1/D2/A2). Chaque item = activation/ajout + son **test de sélection**.

### Axe 1 — Types d'unités / neurones
- 🟢 Vivants : unité Liquid-Mamba rate-based (tanh, constante de temps/nœud via `sigmoid(diag W)`), seuils par nœud, neuromodulation par gain (`W_router`), sparsité imposée KWTA (D2, +47%).
- ⚪ **À ajouter (backlog)** : inhibition explicite / types E-I (Dale) → recoupe **D3 (nœuds typés)** ; spiking (reset/réfractaire/ISI) + STDP → recoupe **D5 (SNN+STDP)** ; calcul dendritique/compartiments ; plasticité homéostatique ; gap junctions.

### Axe 2 — Mémoires
- 🟢 Vivants : mémoire de travail (`H` récurrent), world-model prédictif par agent (`Wp`→surprise, RND).
- 🟡 **À activer (backlog, priorité)** : **mémoire NTM** (têtes read/write câblées mais `explicit_memory` jamais utilisée en entrée / jamais apprise → toujours `[0,0,0,0,0]`) ; **lecture épisodique RAG** (KuzuDB écrit mais lu seulement si `active_exp_variable=="RAG"`, jamais en prod ; ⚠️ risque non-repro mémoire ambiante).
- 🔴 **À trancher** : `memory_cache`, `H_history`, `bytecode` (procédurale) — déclarés, jamais relus (cf. §3 Phase 0).
- ⚪ **À ajouter** : mémoire sémantique (faits/concepts), associative (Hopfield), consolidation/replay hors-ligne *utile*, oubli actif (decay/reset).

### Axe 3 — Plasticité / modulation / organes
- 🟢 Vivants : Actor-Critic TD(0) + crédit d'action (apprentissage intra-vie prouvé, craft 18 vs 0, EDR 020), masque d'attention appris, tête référentielle (langage, EDR 074), `W_router`, `thresholds`.
- 🟡 **À activer (backlog)** : ~~dreaming → planificateur~~ → **TESTÉ : depth-1 RÉFUTÉ** (banc équitable, PLAN_PERD ; voir sous-projet ci-dessous) — reste depth-k/g bilinéaire ; self-attention QKV (organe quasi jamais sélectionné) ; `goal_vector`/`predictor_head`/`value_head` hors-dreaming (extraits, pas de boucle de feedback).
- ⚪ **À ajouter** : plasticité locale Hebbian/STDP (complément du TD) ; neuromodulation fonctionnelle (gating par canal, modulation du learning-rate) ; méta-apprentissage (lr appris) ; contrôle hiérarchique réel (manager→worker, options ; `goal_vector` est orphelin) ; imagination dirigée (= le planificateur ci-dessous).

### Sous-projet Dreaming → Planificateur (latent Dreamer-lite) — depth-1 RÉFUTÉ (2026-06-25)
**Statut : LIVRÉ (gaté OFF) + depth-1 réfuté par banc équitable → depth-k différé.**
Spec `docs/superpowers/specs/2026-06-25-dreaming-planner-design.md`, plan `docs/superpowers/plans/2026-06-25-dreaming-planner.md`.
Implémenté (SDD, Tasks 1-6, tout gaté `MambaBatchModel.PLAN_BIAS=0.0` défaut → **non-régressif**) :
anticipation conditionnée par l'action `g(H,a)→H'` (apprise en ligne par agent), rollout profondeur-1
sur les actions, scoré par la `value_head`, **biais** sur les logits de politique ; + banc d'anticipation
équitable réutilisable (`tools/anticipation_bench.py` : danger télégraphié, gap temporel, respawn,
danger-avoidance rate).
**VERDICT (banc équitable, g convergé mean|G|>0) : `PLAN_PERD`** (median_ratio 0.714@1000 / 0.391@1500
steps, n_fav 3/8) — le lookahead depth-1 + `g` linéaire **NUIT** (perturbe la politique réactive), cohérent
avec le dreaming nuisible (EDR 095). La méthode a évité un run powered stoneage sur un mécanisme réfuté.
**Backlog (futur cycle)** : depth-k (déroulé multi-pas), `g` bilinéaire state-dépendante — seules pistes
restantes pour rendre l'anticipation utile ; à brainstormer séparément.

### Sous-projet ACTIF — Rêve = entraînement offline (Dyna value-augmentation) (2026-06-25)
**Recadrage post-réfutation** : le depth-1 a échoué en MÉLANGEANT rêve et pensée (biais d'imagination
sur l'action en direct). Principe corrigé (Dreamer) : **modes séparés** — la pensée agit en ligne
(inchangée), le rêve entraîne la value head HORS-LIGNE via `g`. Spec
`docs/superpowers/specs/2026-06-25-dream-offline-training-design.md`.
**De-risqué** : une **sonde de fidélité de `g`** (étape A, go/no-go) mesure si `g` bat la baseline
naïve en prédiction 1-pas AVANT de bâtir Dyna ; sinon → escalader `g` bilinéaire d'abord.
Composants (gatés `PLAN_DYNA=0.0` défaut, non-régressif) : sonde A · reward head `r̂` (réutilise
`predictor_head` inutilisé) · replay buffer per-agent · boucle Dyna offline (value head SEULE, aucun
biais d'action). Validation : sonde A → bench Dyna → ablation stoneage.

**ÉTAT Phase A (sonde de fidélité de `g`) — LIVRÉE (`tools/g_fidelity_probe.py`), GO CONDITIONNEL :**
Trois mesures : zéro-obs → G_FIDELE (artefact trivial) ; random-obs → G_INUTILE (artefact : obs
synthétiques **sévèrent** le lien action→obs-suivante, `g` ne peut prédire par construction) ;
**env à conséquences réelles (grille banc) → G_FIDELE FIABLE** (median_ratio 0.357 = 2.8×, 82 % fav,
sign_p 0, 3 colonnes `G` entraînées). **Leçon** : `g` linéaire EST exploitable QUAND l'action influence
réellement l'obs suivante. ⚠️ **CAVEAT (revue opus) : la grille 1-D éparse est le cas le PLUS FAVORABLE
à un `g` linéaire état-indépendant** (bouger = décalage one-hot déterministe) → ne prouve PAS la fidélité
sur obs riches stoneage (même geste → ΔH différents selon contexte = besoin `g` bilinéaire). Et c'est
l'env où `g` a échoué comme biais (depth-1). **PROCHAIN PAS avant de bâtir Dyna : mesurer la fidélité de
`g` sur obs riches/stoneage** ; si ça tient → GO Dyna ; sinon → escalader **`g` bilinéaire** (`H'=H_rec+W_a·H`)
d'abord (branche la moins chère où se tromper, cf. Risk 1 du spec).

### Backlog différé (NAS Axe 3, futurs cycles brainstorm)
- **Dreamer complet** : actor-critic en imagination (entraîner aussi la politique) — après fiabilisation de `g`.
- **Dyna+ / organe MÉDITATION-consolidation** : mixer le replay du vécu RÉEL (consolidation, mode cognitif
  absent) avec l'imagination — fusionne deux directions. *Mode « méditation » = découplé + activité réduite,
  distinct du rêve ; recoupe consolidation/replay (Axe 2) + homéostasie (Axe 1).*
- **depth-k** planificateur + **`g` bilinéaire** state-dépendante (aussi cible d'escalade si sonde A échoue).
- **Outil EDR multi-lentilles** : à la clôture d'un run EDR, générer des interprétations
  anthropologue/éthologue/biologiste/neuroscientifique du comportement (sous-agents à lentilles) pour
  « chercher plus loin ». Cycle d'OUTILLAGE d'analyse, orthogonal au substrat — brainstorm séparé.
