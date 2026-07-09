# BACKLOG AGIseed — idées futures, aspirationnel, références

> Le « someday » du projet : visions, axes futurs, détails de design non encore planifiés. Les
> **roadmaps** court-terme sont scindées par domaine dans [`roadmap/`](roadmap/) (SCIENCE · NAS ·
> BACKEND · FRONTEND) ; l'**historique** scientifique est dans [`FIL_CONDUCTEUR.md`](FIL_CONDUCTEUR.md)
> + [`EDR/`](EDR/). Carte : [`README.md`](README.md). Ce fichier n'est ouvert que pour planifier loin.
>
> Le backlog **NAS** (moteur évolutif) vit dans [`roadmap/NAS.md`](roadmap/NAS.md) §2.

---

## 2026-07-02 — Brainstorm « Aller plus loin » : intégration torch in-world + 4 axes

> Cadre après clôture de la **carte valeur torch** (parité 140/141 · mémoire BPTT 145 · binding
> `learn_episode` 158/159). Reste explicite du fil G1 = **intégration boucle biosphère**. Les 4 axes
> ci-dessous sont hiérarchisés ; l'axe 1 est le chemin critique choisi (session 2026-07-02).

### Hypothèse unificatrice (H-unif) — le pari scientifique
**Rétention craft (127), spécialisation world-spécifique (156/157) et binding means→ends (126-159)
sont le MÊME verrou : le crédit conditionnel.** Le craft « atteint mais non retenu » (127) est
structurellement du *marginal-raising* (126) : l'agent essaie le craft mais n'apprend pas à crafter
*quand ça paie*. La recette **gate + crédit épisodique** (158/159, `learn_episode`, +0.298) est le
1er levier qui casse ce motif en isolation. **Prédiction falsifiable** : porter `learn_episode`
in-world (axe 1) doit *racheter* 127/156/157 sans nouveau mécanisme. Si faux → verrous distincts,
appris via EDR bon marché. Test = axe 3.

### Contrainte d'archi découverte (décisive)
Le `batch_model` est **transitoire** — [`world_1_stoneage.py:992`](roadmap/../../src/worlds/world_1_stoneage.py)
le ré-instancie *à chaque tick*. L'état durable (H, poids) vit dans les agents (`a["model"]`). Donc
le **buffer de trajectoire de `learn_episode` ne peut vivre sur le batch_model** (jeté/tick) : il doit
être porté par le **monde** (ring-buffer `self._torch_traj` de K ticks) et le `pop` torch doit
**persister entre ticks** (hissé hors de la boucle par-tick, backend torch seulement ; legacy
inchangé). Le banc 158/159 masquait ce point (là `pop` persiste sur tout l'épisode).

### Axe 1 — Intégration torch in-world (CHEMIN CRITIQUE)

> **CRANS 0-1 LIVRÉS 2026-07-02** (subagent-driven, 6 tâches TDD + fix I1 ; 10 tests verts ; review final
> Opus = PRÊT À MERGER ; commits path-scopés `b5e91db`→`74295af`, NON poussés). `Biosphere3D.use_torch_inworld`
> (opt-in OFF, legacy non-régressif prouvé) fait tourner `learn_episode` in-boucle : pop torch persistant,
> buffer glissant K, crédit épisodique **aligné par identité d'agent** (rogne aux vivants — benchmark_mode
> fige la repro mais PAS la mortalité). Banc `tools/torch_inworld_ab.py`. Garde : `use_torch_inworld` EXIGE
> `benchmark_mode`. Détail : mémoire `torch-inworld-integration-plan`, ledger `.superpowers/sdd/progress.md`.
>
> **VERDICT A/B SURVIE = NEUTRE (powered, 12 seeds appariés)** : régime very_soft (sweet spot EDR-085),
> métrique **AUC de survie** (le monde est létal aux frais → survie finale = plancher structurel EDR-090,
> l'AUC discrimine). median_diff +0.017 (<bande), 7/12, sign_p 0.55 ; le signal 6-seeds (+0.033) a fondu
> sous puissance. Établit la **NON-RÉGRESSION in-world** (torch ne dégrade pas la survie) MAIS **la survie
> n'est pas le KPI du binding** — `learn_episode` porte la composition, pas la survie brute. Prochain
> instrument = brancher une DEMANDE DE COMPOSITION in-world (pont vers EDR-161). À formaliser en EDR.
>
> **RESTE crans 2-4** : gate (`CONDITION_GATE`/`GATE_TARGET`), antisat, gate mult + mesure binding in-world
> P(Y|X). ⚠️ **Bloqueur cran 2** : le rebuild du pop sur mortalité RÉINITIALISE `w_gate`/`b_gate` → éroderait
> l'accumulation du gate → persister le gate à travers rebuild AVANT d'allumer le gate in-world.

**Historique de la reco (2026-07-02, avant livraison) :**
Reco couture (**approuvée 2026-07-02**) : faire passer la boucle biosphère par `make_population`
(ADR-003, dette payée — aujourd'hui seuls tools/tests l'utilisent), buffer épisodique porté par le
monde, `pop` torch persistant. Opt-in **`USE_TORCH_INWORLD`** (défaut off, legacy strictement
non-régressif). **Définition d'épisode** = fenêtre glissante K ticks (reco : c'est le régime exact
où 158/159 ont livré ; garde `learn()` TD en //; K devient variable EDR propre). Alternatives
écartées : vie de l'agent (crédit trop dilué, mémoire O(vie)) ; segments événementiels (détection à
câbler). **Progression flag-par-flag** (Commandement 15, 1 variable) : (0) `USE_TORCH_INWORLD` à
parité forward — déjà prouvé hors-boucle 140/141 ; (1) `learn_episode` seul ; (2) +gate ; (3)
+antisat ; (4) +gate multiplicatif EDR-160 (en vol). Chaque cran = 1 EDR powered avec banc in-world.

### Axe 2 — Lancer `transfer_ratio` à l'échelle (en //, background)
Instrument `tools/curriculum_transfer.py` **livré mais jamais lancé**. C'est le KPI (X2) dont
dépendent RSI (#2) et NAS. Design bon marché (outil prêt), coût = compute. Verrou = budget mono-machine
(garde-fou SCIENCE.md : profiling/parallélisme/early-stopping AVANT). À orchestrer en tâche de fond
pendant l'axe 1.

### Axe 3 — Verrous 2e génération (test de H-unif)
Une fois `learn_episode` in-world (axe 1) : **rejouer EDR-127 (rétention craft) et EDR-156/157
(spécialisation) sous crédit épisodique**. Bancs `tools/tool_gate_calibration.py`,
`tools/cross_world_transfer.py`, `tools/famine_harshness_probe.py` existants. Si H-unif tient →
craft retenu + spécialisation émergente sans nouveau mécanisme = validation la plus élégante du fil.

### Axe 4 — G4 (anticipation) / G2 (composition)
- **G4** : depth-1 g linéaire RÉFUTÉ (135, `planner-depth1-refuted`) MAIS `world_model.predict()`
  jamais branché (dreaming = random-shooting latent, SCIENCE.md #3). Leviers vierges : g **bilinéaire**
  OU brancher le vrai world model dans le planning. Banc `tools/anticipation_bench.py`.
- **G2** : outil « émergence de chaîne non récompensée » **à créer** (table des portes,
  `FIL_DIRECTEUR_AGI.md`). Germe = `tools/substrate_ab_compositional.py`.

---

## L'Axe Ontogénétique — Curriculum Développemental (2ᵉ Échelle de Temps)

> **Deux axes du temps, orthogonaux.** Les 7 Arcs décrivent la *phylogénèse* (ce que le **système** gagne, version après version). Cette section décrit l'*ontogénèse* : ce qu'un **cerveau individuel** doit maîtriser, et dans quel ordre, avant de changer de monde.

| Axe | Échelle | Mécanisme | Granularité |
|---|---|---|---|
| **Phylogénèse** (les Arcs) | Inter-ères, V7→V16+ | Sélection, Hall of Fame, HGT | La population |
| **Ontogénèse** (ce curriculum) | Inter-mondes, soup→industrial | Maîtrise + transfert du connectome | L'individu |

> **État** : les worlds ne sont *pas* chaînés — on tourne 30 ères dans un seul monde. Le transfert de cerveau existe (import KuzuDB + neuro-chirurgie, `IMPORT_AGENT_ID`/`KEEP_MEMORY`). Ce curriculum en ferait un **pipeline développemental**.

### 1. L'Échelle de Développement

| Monde | Stade (analogie) | Compétences à « maxxer » | KPI de maîtrise |
|---|---|---|---|
| **0 — Soup** | Sensorimoteur / réflexes | Homéostasie, approche/évitement | Survie médiane, énergie stable |
| **1 — Stoneage** | Causalité / objet | Usage d'outils, permanence de l'objet | Taux d'usage d'outils, crafting |
| **2 — Agricultural** | Planification | Gratification différée (semer→récolter) | Horizon de planification, stock |
| **3 — Industrial** | Abstraction / composition | Division du travail, composition d'outils | Coopération, chaînes de production |
| **Gym cognitif** | Opérations formelles | Logique, calcul, jeux | Taux de résolution de puzzle |

### 1bis. Deuxième axe : la complexité du craft (orthogonal)

Leçon de l'EDR 017 : la chaîne de craft empile trop de gates *d'un coup* → inémergeable. D'où la complexification **par paliers**, un gate à la fois.

| Niveau craft | Mécanique | Gate ajouté |
|---|---|---|
| **L0** | auto-craft (tenir tranchant+manche → lance) | collecter 2 ingrédients |
| **L1** | + action de craft (`rub`) | le geste |
| **L2** | + recette positionnelle (inventaire 0,1) | l'ordre |
| **L3+** | recettes multi-étapes (rock→sharp_rock→spear) | la composition |
| **LN** *(très loin)* | craft **3D** : forces, orientation, sens | la physique de l'outil |

L'agent vit dans un **espace développemental 2D** : `Monde × Craft`. Détail : `docs/EDR/018`.

### 2. Mécanisme de Graduation (Mastery Gates)
*   **Métriques de compétence** : au-delà de l'énergie, un *bulletin de notes* par monde — KPI ingérés par l'`AdaptiveTuner`.
*   **Critère de graduation = détection de plateau** : compétence médiane qui plafonne sur K ères → la population « diplôme » (« Observateur de Famine Cognitive » réorienté).
*   **Protocole de transfert** : import neuro-chirurgical du connectome + carry-over NTM (déjà implémenté).
*   **Politique de progression** : linéaire / adaptative (le Supervisor choisit le monde) / branchante (espèces spécialisées).
*   **⚠️ Tension** : « maxxer les stats » peut *entrener* (overfitting) et ralentir le transfert. Le seuil de graduation = **variable d'expérience** (Commandement 15).

### 3. Le Relicat de Cerveau (Persistance & Croissance)
*   **Un cerveau qui grandit** : connectome + NTM persistant traverse les mondes et **ajoute des neurones** (neuro-chirurgie + `add_node`). Enjeu du **Connectome Élastique**.
*   **Anti-oubli catastrophique** : *périodes critiques* (geler les sous-réseaux précoces), *rehearsal interleaved* (rejouer les mondes anciens), *réseaux progressifs* (modules neufs, anciens gelés).

### 4. Le Gym Cognitif (Jeux Abstraits)
Environnements d'intelligence pure (**portes logiques, calcul, échecs, Go**) décorrélés de la survie. Statuts : **(A) Embarqué** (puzzle = artefact, l'Altar existe déjà), **(B) Rêvé** (MCTS/Dreaming, l'agent joue « dans sa tête »), **(C) Gym séparé** (`BaseWorld` symboliques). Cas spécial **portes logiques** : banc du `ntm_compiler.py` (Self-Wiring). ⚠️ Risque *savant désincarné* → usage en accélérateur/benchmark, jamais substrat primaire.

### 5. Récompense Scaffold (« Cheatcode ») — à tester *contre* le pur intrinsèque
*   **Hypothèse** : récompense explicite forte *tôt* → annealing jusqu'à ce que l'intrinsèque prenne le relais.
*   **Shaping de Skinner** : dense tôt, sparse tard (`tools/skinner_box.py` existe).
*   **Impulsion = pic phasique** : récompenser *l'acte d'apprendre* (rollout MCTS qui prédit bien, HGT réussi) — dopamine de l'insight.
*   **Reframe** : l'évolution EST le cheatcode (prior compressé). Variante : **évoluer la fonction de récompense** comme un gène.

---

## 🗺️ Dimensions d'Expérimentation (carte de référence)

Toute expérience se situe dans **4 familles** de dimensions orthogonales.

| Famille | Axes | Instrument | Statut |
|---|---|---|---|
| **A. Temps** | Ontogénèse (Actor-Critic TD), Phylogénèse (HoF) | apprentissage TD / sélection | ✅ réparé (`016/020/023/024`) |
| **B. Développemental** | Monde, Craft, Difficulté | `CurriculumRunner`, drivers 2D | ✅ Craft+Difficulté ; Monde à étoffer (`025/026/027`) |
| **C. Méta-évolution** | Arcs, NAS architecture | metaprog / sandbox (RSI) | ⏳ frontière |
| **D. Mécanismes** | intrinsèques, scaffolds, gènes | **ablation + ontologie** | ✅ instrument livré (`031/032`) |

> L'ablation (D) mesure *« utile à l'expert ? »* ; le curriculum (B) répond *« utile à l'émergence ? »* (`EDR 032`).

---

## Brainstorming & Architecture Dev

- **Axe 1 : Unification Vectorisée de la Biosphère** : fusionner `src/worlds/` et `src/environments/` ; `Biosphere3D` à tensorisation massive (convolutions pour stigmergie/physique, Swarm NAS scalable).
- **Axe 2 : Sandboxing Architectural** : étendre `metaprog/sandbox.py` pour valider les mutations d'architecture entière (Meso/Macro NAS) avec SkinnerBox miniature + tests unitaires.
- **Axe 3 : HGT déclenché par la Surprise** : pic de surprise non résolu → requête KuzuDB pour l'agent le plus performant dans des états latents similaires → « synaptic copy ».
- **Axe 4 : Visualisation Live via le Frontend** : API FastAPI → React (flux de pensées Mermaid live, topologie cerveau React Flow/D3). *(Partiellement livré : dashboard EDR + biosphère live — cf. roadmap § Dev.)*
- **TensorWorld** : carte/entités/inventaire en grandes matrices NumPy ; `MambaBatchModel.forward(batch_obs)` au lieu d'appels individuels.
- **Dreaming & MCTS** : utiliser le TTC (micro-ticks Mamba) pour simuler les N prochaines actions (Value Head) avant d'agir.
- **KuzuDB Async Sink** : DataLoggerThread asynchrone non bloquant *(livré : `async_logger`).*

---

## ⚡ Solutions issues des Audits Cognitifs & Physiques

- **Solution 1 — Registre Physique Dynamique** : éviter les propriétés d'objets codées en dur ; dictionnaire d'items persistant lié à KuzuDB, propriétés calculées par interpolation vectorielle pour les combinaisons inconnues.
- **Solution 2 — Connectome Élastique** : supprimer les dimensions fixes des modèles batch (Dynamic Tensor Padding + masques d'activation élastiques) pour ajouter entrées/sorties sans rompre les tenseurs.

---

## 🚀 Évolution de l'Autonomie : Code & No-Code

- **2.1.A Autonomie en Code (Métaprog LLM)** : Observateur de Famine Cognitive (surveille KuzuDB) → génération de modules/activations dans `generated_op.py` → sandboxing (tests unitaires + timeout). *(Sandbox livrée EDR 035 ; #8 armé EDR 065-069.)*
- **2.1.B Autonomie No-Code (Self-Wiring)** : NTM Program Compiler (zones mémoire NTM → règles d'activation/routage) ; Cognitive Graph-RAG (requêtes Cypher subconscientes pour rappeler les « pensées des ancêtres »).
- **2.2 Axes AGI** : boucle fermée de métaprog active (le code s'auto-optimise) ; bac à sable de crafting émergent ; réflexivité épistémique (connectomes ↔ KuzuDB).

---

## 📈 Améliorations et Extensions Futures

### 1. Richesse de l'Agentique

> **Audit grounded 2026-06-30** (`AUDIT_MEMOIRE_INTELLIGENCE.md`) : backlog priorisé P0→P4 mémoire + typologie d'intelligence. Les items ci-dessous y sont re-cadrés sur le code réel (récup KuzuDB = 5 scalaires top-500 global ≠ épisodique ; ToM = MORTE ; connectome plat sans isolation de gradient).

*   **Mémoire Hiérarchique et Associative** : court terme (tampons sensoriels, mémoire de travail) + long terme (KuzuDB sémantique/épisodique) + buffer d'expérience.
*   **Modélisation d'Autrui (Theory of Mind Light)** : inférer intentions/croyances/buts d'autrui — fondamental pour les Arcs sociaux.
*   **Apprentissage Multimodal et Imitatif** : apprendre par observation/imitation, ou instructions simplifiées (dès que le langage émerge).
*   **Boucles de Réflexion et Auto-Correction** : analyser ses erreurs passées (KuzuDB), identifier les causes, ajuster ses stratégies ou son « code ».

### 2. Auto-Amélioration (Métaprog & HGT)
*   **Critères d'évaluation de code auto-généré plus riches** : perf CPU/GPU, efficacité énergétique, robustesse, généralisation.
*   **Co-évolution des Architectures d'Agents** : « espèces » spécialisées (explorateur, bâtisseur, défenseur).
*   **Transfert culturel non-génétique** : recettes/techniques/fragments de langage transmis par imitation/enseignement/stigmergie.

### 3. Outils d'Analyse & Visualisation
*   **Sociologue Prédictif** : patterns prédictifs, anticipation des divergences/effondrements.
*   **Visualisation des Hypothèses & Justifications** : afficher hypothèses, simulations MCTS, justifications inférées.
*   **Cartographie Évolutive 3D** : relations agents↔artefacts↔ressources↔environnement dans le temps.

### 4. Vers une Intelligence Réellement Innée (« pas dit mais trouvé »)

- **4.1. Émergence des fonctions de récompense** : supprimer les récompenses fixes au profit de signaux intrinsèques (curiosité, minimisation d'erreur de prédiction). La Surprise est le point de départ ; étendre vers du *predictive coding* / *curiosity-driven learning*. **L'idéal manifeste.**
- **4.2. Auto-conception d'expériences** : l'agent génère ses **hypothèses** + des **mini-expériences** (mentales ou micro-sandboxes) → méthode scientifique rudimentaire.
- **4.3. Évolution des stratégies d'évolution (méta-méta-prog)** : les agents proposent des améliorations aux *mécanismes* d'évolution (HGT, critères de sélection). KuzuDB = la « génétique » des algos d'évolution.
- **4.4. Langage de spécification intérieur (pré-verbal)** : représentations symboliques internes (protoconcepts) avant tout langage externe ; factoriser les observations en concepts discrets.
- **4.5. Gestion émergente des ressources computationnelles** : méta-contrôleur appris qui module le budget TTC, la profondeur MCTS, la fréquence de métaprog selon l'état interne — une « économie cognitive ».

---

## 🔭 Référence lointaine — MiroFish (synthèse possible, Arc 5+)

[MiroFish](https://github.com/666ghj/MiroFish) (`C:\Users\robla\VScode_Project\MiroFish`) : moteur d'**intelligence d'essaim LLM** — monde parallèle haute-fidélité, milliers d'agents à personnalités/mémoire/évolution sociale → émergence collective & prédiction. **Inverse paradigmatique d'AGIseed** : agents-LLM *top-down* (intelligence donnée) vs connectomes évolués *bottom-up* (intelligence trouvée).

**Positionnement** (lointain, Arc 5) : *réutiliser* son infra (monde parallèle, orchestration, UI/prédiction) comme substrat d'application pour des agents AGIseed matures ; ou *s'inspirer* de son modèle social. ⚠️ Pas avant que la coopération émergée (EDR 028) mûrisse.

---

## Backlog (idées différées)

- **Table de craft spatiale (façon Minecraft)** : remplacer la recette unique (`rub` → lance) par une **grille 3×3** où la *disposition* définit la recette (*shaped crafting*) → arbre technologique compositionnel, pressure la planification spatiale. Progression : **3×3 → n×n → n×n×n** (craft volumétrique 3D). Après validation de la boucle moyens→fins par l'évolution.

---

## Solidification G0 (porte FRANCHIE par EDR 112, raffinements différés)

> G0 est **validée** (`SDR-G0`, stoneage/soup EXIGE). Ces items renforcent la *carte de validité* mais
> ne bloquent pas G1. Design : `superpowers/specs/2026-06-29-G0-World-Demand-Benchmark-design.md`.

- **Monde Lewis dans le benchmark de validité** : porter `tools/s2_demand.py` sur la config létale Lewis
  (`_setup_critical`, cf. `tools/lewis_critical.py`) — le régime DUR (EDR 110). Mesurer si Lewis EXIGE ou
  est au plancher pour les deux bras.
- **Garde-fou INCONCLUSIF au plancher létal** : ajouter à `s2_verdict` un verdict INCONCLUSIF quand
  champion ET baseline sont sous un `FLOOR_AGE` (régime létal → pas de discrimination), distinct de
  FACTICE. Crucial pour Lewis (EDR 110).
- **Trancher industrial vs stoneage** : EDR 112 montre des chiffres *byte-identiques* → `IndustrialWorld`
  délègue probablement à `Biosphere3D`. Confirmer (le verdict EXIGE d'industrial n'est pas indépendant).
- **Re-régler agricultural (VOID)** : la cohérence life_score a échoué (life_p=0.092) → instrument
  indécis ; comprendre pourquoi (monde immature ? métrique inadaptée ?).
- **`s2_demand._print_table` Windows-safe** : plante sur stdout cp1252 à l'impression de « Cliff δ »
  (U+03B4). Contourné par `PYTHONIOENCODING=utf-8` ; corriger le print (ASCII ou encodage explicite).
