# BACKLOG AGIseed — idées futures, aspirationnel, références

> Le « someday » du projet : visions, axes futurs, détails de design non encore planifiés. Les
> **roadmaps** court-terme sont scindées par domaine dans [`roadmap/`](roadmap/) (SCIENCE · NAS ·
> BACKEND · FRONTEND) ; l'**historique** scientifique est dans [`FIL_CONDUCTEUR.md`](FIL_CONDUCTEUR.md)
> + [`EDR/`](EDR/). Carte : [`README.md`](README.md). Ce fichier n'est ouvert que pour planifier loin.
>
> Le backlog **NAS** (moteur évolutif) vit dans [`roadmap/NAS.md`](roadmap/NAS.md) §2.

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
