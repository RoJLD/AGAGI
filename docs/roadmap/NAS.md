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
| **D2** KWTA sparsité | no-op | ✅ **EFFICACE** : sparsifier le hidden AMÉLIORE la compétence (+47 %, keep=0.3, sign_p=0.070). Régularisation. |
| **A2** MAP-Elites | NEUTRE (cov 3.6/32) | NEUTRE (cov **4/32**) — les descripteurs ne s'étalent pas (taille seedée à 1 bin + add_node lent ; palier effondré, EDR 096) |

**Leçon affinée** : le fix débloque l'**architecture** (D2 gagne) mais A2 (diversité comportementale) a
besoin de **descripteurs qui varient** (seeder des tailles diverses OU réparer le répertoire moyens→ends).
**Reste** : (a) merger/itérer ; (b) basculer `preserve_dims=True` en défaut (coordination // + comparatif
powered) ; (c) re-mesurer A2 avec seeds de tailles variées ; (d) D1 (sélection sparsité) re-testable.

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
