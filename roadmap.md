# Roadmap AGIseed : De l'Atome a la Civilisation

---

## Arbre Genealogique des Versions

```
V7 → V8 → V9_Mamba → V10_Language → V11_OpenEnded → V12_Metacognition
                                                         |
                                        V13_Cailloux → V14_Balistique → V15_Crafting_Feu (ACTIF)
                                                                             |
                                                                    V16_Language_Inventaire
```

## Architecture V15/V16 (Actuelle)

- **45 Entrées** : Lidar 6D, Position, Proie, Altar, Social, Langue, Prey Type, Surprise, Worm, Throw Feedback + Propriétés Physiques Objets (Poids, Tranchant, Friction, Comestibilité, Inflammabilité).
- **25 Sorties** : Mouvement 6D, Cognitif, Saut/Baisse, Grab, Throw, Rub (Crafting), Social 3, Visee 3D, Parole
- **Moteur** : Liquid Mamba BatchModel (Vectorisé) + TTC Adaptatif
- **Ecologie** : 9 proies + 5 vers de terre, proportionnelle, Feu, Crafting

---

## Les 7 Arcs de l'Evolution

| Arc | Theme | Experiences | Statut |
|---|---|---|---|
| 1 | **L'Animal** (Survie) | EXP 1-4 | TERMINÉ |
| 2 | **Le Primate** (Outils) | EXP 5-8 | TERMINÉ (V14) |
| 3 | **L'Homo Habilis** (Crafting) | EXP 9-12 | EN COURS (V15) |
| 4 | **L'Homo Sapiens** (Langage) | EXP 13-16 | EN DÉMARRAGE (V16) |
| 5 | **La Tribu** (Culture) | EXP 17-20 | A VENIR |
| 6 | **Le Penseur** (Raisonnement) | EXP 21-24 | A VENIR |
| 7 | **La Conscience** (Graal) | EXP 25-30 | A VENIR |

Voir `roadmap_experimentation.md` (artifact) pour le detail complet.

---

## Commandement 15 — Loi du Sociologue

> Chaque innovation = 1 variable. 30 Eres minimum. Analyse Sociologue. Valide ou Revert.

## Outils

| Outil | Chemin | Role |
|---|---|---|
| Sociologue | `tools/sociologist.py` | Rapport KuzuDB |
| Skinner Box | `tools/skinner_box.py` | Audit neuronal |
| Migration | `migrate_v10.py` | Chirurgie genetique |
| Tresor CLI | `treasure_cli.py` | Secrets d'Evolution |

---

## Brainstorming & Architecture Dev

- **Axe 1 : Unification Vectorisée de la Biosphère** : Fusionner `src/worlds/` et `src/environments/`. Repenser la `Biosphere3D` avec une tensorisation massive (NumPy) pour la stigmergie et la physique, supprimant les calculs agents individuels au profit de convolutions (Swarm NAS scalable).
- **Axe 2 : "Sandboxing" Architectural** : Étendre `metaprog/sandbox.py` pour valider les mutations de l'architecture entière (Meso/Macro NAS). Le superviseur génère le code, l'injecte dans la sandbox avec une SkinnerBox miniature et valide via tests unitaires avant intégration.
- **Axe 3 : Déclenchement Dynamique du "HGT" par la "Surprise"** : Lier la métrique de Surprise au Transfert Horizontal de Gènes (HGT). En cas de pic de surprise non résolu par le TTC, l'agent requête KuzuDB pour trouver l'agent le plus performant dans des états latents similaires (HCM) et initie un "synaptic copy".
- **Axe 4 : Visualisation "Live" via le Frontend** : Exposer les requêtes du Sociologist/HCM Analyzer via une API FastAPI. Le frontend React interroge cette API pour afficher en direct le flux de pensées des agents (Mermaid live) et la topologie du cerveau (React Flow/D3.js).
- **TensorWorld** : Extraire la carte du monde, les entités et l'inventaire sous forme de grandes matrices NumPy. Au lieu d'appeler `agent.forward(obs)` individuellement, nous utiliserions `batch_preds = MambaBatchModel.forward(batch_obs)` pour un batch complet.
- **Dreaming & MCTS (Métacognition)** : Utiliser notre Test-Time Compute (les micro-ticks adaptatifs de Mamba) non seulement pour le "grounding" sensoriel, mais pour simuler les N prochaines actions (Value Head) dans un état mental avant d'agir (similaire à MCTS).
- **KuzuDB Async Sink** : Créer un DataLoggerThread asynchrone qui écoute les événements de la simulation sans bloquer la boucle (Commandement 4) et alimente notre base graphe pour que l'agent Graph-RAG puisse l'analyser.

## Sprint immédiat — Développement

- [x] Couverture E2E WebSocket du streaming `flatland_server` + validation backend
- [x] Ajout de métriques de simulation (`avg_energy`, `avg_hp`, `prey_count`, `item_count`, `altar_count`) dans le payload WebSocket
- [x] Audit des métriques de robustesse/généralisation côté simulation (`energy_std`, `hp_std`, `social_density`, `genome_diversity`)
- [x] Intégration concrète `swarm` / `consensus` / `HGT` dans l’orchestre de simulation
- [ ] Liaison `graph_rag` / KuzuDB dans la boucle de supervisor pour tuning adaptatif
