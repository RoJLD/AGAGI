# EDR 010 : Audit Réel vs Théâtre — Diagnostic & Leviers AGI

## Contexte

Un scan multi-agents du repo (5 explorateurs parallèles : cœur cognitif, auto-modification/évolution, métacognition/supervisor, mondes/embodiment, intention-vs-réalité) a produit une image honnête de l'état réel, code à l'appui. Cet EDR fige ce diagnostic avant d'engager le moindre chantier, pour éviter de bâtir sur des illusions.

**Verdict en une phrase** : AGIseed a construit un *corps* et un *système nerveux* solides et largement réels, mais ni la **capacité de prédiction** (le cortex) ni un **monde qui exige l'intelligence**. Le projet confond systématiquement *avoir un gène* avec *exprimer une fonction*, et *avoir l'infrastructure* avec *avoir l'intelligence pour laquelle elle a été bâtie*.

## Constat — Réel vs Théâtre

### ✅ Réel et fonctionnel (les vrais actifs, à préserver)
- **Connectome récurrent liquide** : vraie dynamique ODE Liquid-Time-Constant, `H=(1-Δt)·H+Δt·tanh(Wx)`, Δt issu de la diagonale de W (`mamba_agent.py:344,365`).
- **Mémoire NTM persistante** : read cosinus+softmax, write erase/add, sérialisée (`mamba_agent.py:519-563`). Composant le plus abouti.
- **Double boucle d'apprentissage** : Hebbien intra-vie (policy gradient `advantage=reward−value`, appelé chaque step `world_1_stoneage.py:1018`) + évolution topologique inter-ères (vrai `np.insert` dans `add_node`, `mutation.py:54`). Vrai inner/outer loop.
- **HGT + consensus câblés dans le monde** : transfert de gènes par contact/surprise (`world_1_stoneage.py:619`), fusion de logits pondérée fitness (`:603`).
- **NTM self-wiring** : recâblage de W depuis les slots mémoire, appelé chaque forward (`mamba_agent.py:335`) — quoique scaling grossier.
- **KuzuDB** : schéma riche (~18 nœuds, ~25 relations), peuplé par l'AsyncLogger. **Skinner Box** : interprétabilité mécaniste réelle (top-5 neurones/scénario, persistés).
- **Boucle tuner→monde** fermée sur `mutation_rate` (`main_biosphere.py:190-192,298,350`).
- **Curriculum (EDR 008/009)** : la zone la mieux testée. **87 tests passent** au total.

### 🔴 Théâtre / aspirationnel (nom ronflant sur un stub)
- **"MCTS/dreaming"** : pas de planification — random-shooting dans l'espace latent (perturbation gaussienne + argmax value head), zéro arbre, zéro modèle du monde (`mamba_agent.py:439-469`).
- **"LLM de métaprogrammation"** : aucun LLM — renvoie une fonction **Swish codée en dur**, identique à chaque appel (`llm_operator.py:12`, `supervisor_coder.py:3`).
- **Boucle metaprog jamais branchée** : `analyze_metrics` (déclencheur famine→codegen) appelé **uniquement dans un test**. + bug de chemin : écrit `tests/sandbox/generated_op.py` (singulier), lit `src/metaprog/sandbox/generated_ops.py` (pluriel) → réinjection impossible.
- **Gènes fantômes** : `W_router`, `bytecode`, `thresholds` sont **mutés** (`mutation.py:120-163`) mais **jamais lus** en inférence (absents des deux `forward`). Pas de spiking, pas de routage. Ils diluent la pression de sélection.
- **Supervisor "LangGraph"** : graphe réel mais nœud décisionnel = **if/else** sur seuils (`supervisor.py:112-130`), aveu écrit `# Mock LLM Call` (`:82`). Seul appel LLM réel = rédaction d'article décorative (Ollama, échec silencieux).
- **"4 mondes gradués"** = 1 monde : world_0 (V13 legacy, incompatible) ≠ world_1 (V14, le vrai) ; world_2 = world_1 + saisons ; world_3 = world_1 **+ 2 lignes** de pollution jamais lues.
- **Crafting profond débranché** : l'arbre rock→axe→chest (`crafting.py`) ne tourne qu'en V13 legacy (`world_0_soup.py:476`). Le monde réel n'a qu'1 niveau : frottement→feu (`world_1_stoneage.py:915`).
- **Ontologie scientifique** (Hypothesis/Fact/Conclusion + SUPPORTS/CONTRADICTS) : **déclarée mais jamais peuplée**. Macro/Meta-NAS = catalogue doc de ~80 blocs inexistants. Arcs 5-7 = 0 ligne.
- **Sandbox metaprog** : `subprocess pytest` + timeout 5s, **sans isolation** (pas de restriction d'imports/mémoire/réseau) → vulnérable RCE dès qu'un vrai code est généré.
- **Observations partiellement bidon** : ~6-8 entrées sur 59 sont des `zeros` constants codés en dur (`world_1_stoneage.py:373-384`).

## Les 2 causes racines (couple indissociable)

**A. Le cerveau ne prédit pas.** Pas de world model → le dreaming ne rêve rien, la surprise n'est pas une vraie erreur de prédiction, la value head n'est jamais entraînée comme critic. Pas de prédiction = pas de planification, d'imagination, ni de curiosité.

**B. Le monde n'exige pas l'intelligence.** Énergie abondante (visite case +0.5, dopamine-surprise, alignement vocal +0.5, respawn infini), crafting profond débranché. **L'intelligence est subventionnée, pas instrumentale** : un réflexe « chasser le plus proche » suffit à survivre.

> Le couple : un cerveau prédictif est *inutile* dans un monde où les réflexes suffisent ; un monde exigeant est *inapprenable* sans cerveau prédictif. Les traiter séparément échouerait — ils doivent avancer ensemble.

## Décision (V18.0) — Principe directeur

**Soustraction et profondeur > addition.** Le repo a déjà *plus de mécanismes que de fonction*. On cesse d'ajouter des couches (NAS, économie d'essaim, modules de conscience) ; on fait **exprimer** les quelques vrais mécanismes, dans un monde qui les **exige**, mesuré **honnêtement**. La roadmap avait raison sur le QUOI (axes 4.1-4.5) ; l'écart est entièrement dans la profondeur d'exécution.

**Véhicule** : le `CurriculumRunner` (EDR 008/009) est la colonne vertébrale — on stage chaque levier comme un monde développemental à porte de maîtrise, et on mesure transfert/rétention pour ne pas se mentir.

## Leviers prioritaires

| # | Levier | Pourquoi (fondé sur le scan) | Coût |
|---|---|---|---|
| **1** | **World Model (keystone)** | Tête prédictive (le `predictor_head` existe, juste copié `mamba_agent.py:528`). Convertit 3 fausses choses en vraies : dreaming→imagination (MCTS sur états prédits), surprise→**curiosité réelle = récompense intrinsèque de l'axe 4.1 gratuite**, value head→vrai critic (TD). | Faible (scaffolding présent) |
| **2** | **Monde qui exige la cognition** | Rareté dure (hiver mortel, plafond de respawn, supprimer les bonus gratuits) + **brancher le crafting** + grosses proies intuables sans outil + coopération/langage **structurellement nécessaires** (pas payés +0.5). Rend l'intelligence instrumentale. | Moyen |
| **3** | **Tuer ou câbler les gènes fantômes** | Router/bytecode/thresholds mutés mais jamais lus → restaurer la pression de sélection. Câblés, ils apporteraient la **compositionnalité/modularité** absente. | Faible |
| **4** | **Vraie RSI (LLM réel)** | Remplacer le mock Swish par un vrai appel LLM (Claude) proposant des activations *contextuelles* + **fix bug de chemin** + **sandbox isolée**. Le pivot « graine d'AGI » vs sim évolutive classique. Infra hot-reload déjà présente. | Moyen (sécurité d'abord) |
| **5** | **Retourner la méthode sur soi (ablation)** | Appliquer le Ratio de transfert / « 1 variable, valide ou revert » aux **mécanismes du projet** : combien bougent réellement une métrique de capacité ? Pari : plusieurs (gènes fantômes, récompenses scriptées) sont neutres ou nuisibles. | Faible |

## Conséquences

- Le projet dispose d'un **état des lieux honnête** opposable : on sait ce qui marche, ce qui ment, et l'ordre des chantiers.
- Les leviers 1+2 (couple racine) sont prioritaires et **co-dépendants** : à instaurer ensemble via le curriculum.
- Le levier 4 reste bloqué tant que la sandbox n'est pas isolée (dette de sécurité).
- Risque : la tentation d'ajouter encore (Arcs 5-7, NAS Macro) doit être résistée tant que les vrais mécanismes ne s'expriment pas.

## Questions ouvertes

- World model : prédire l'observation brute t+1, ou un état latent (JEPA-style) moins coûteux ?
- Ablation : quelle métrique de « capacité » au-delà de l'énergie ? (les KPI de compétence du curriculum, EDR 008.)
- RSI : LLM local (Ollama, déjà câblé) ou API Claude pour la génération d'opérateurs ?
