# Article 010 : Arc 6 & EXP-11 — Métacognition Épisodique, Consolidation Nocturne Collective et Débiaisement Isocalorique

**Auteurs :** Équipe de Recherche AGIseed  
**Date :** 2026-10-10  
**Statut :** Validé empiriquement & Certifié dans KuzuDB  
**Identifiant Graphe :** `art_010_arc6_reve_episodique_metacognition`

---

## 1. Contexte & Problématique : Le Saut Métacognitif

Après la révolution néolithique (Monde 2) et l'âge métallurgique (Monde 3), la complexité des tâches in-world impose à la biosphère de surmonter deux limites critiques du connectome Mamba :
1. **L'oubli catastrophique et le coût d'apprentissage en ligne** : Les agents périssent rapidement s'ils tentent d'ajuster leurs politiques par gradient pendant les phases critiques d'action réactive diurne.
2. **Le couplage parasite poids-métabolisme** : Dans l'architecture historique, la norme des poids synaptiques $W$ influençait directement le métabolisme de base, confondant progrès cognitif et survie par économie corporelle.

L'**Arc 6 (EXP-11)** apporte une solution d'inspiration neurobiologique : la séparation du temps d'action (le jour) et du temps de consolidation mnésique (la nuit), couplée à un modèle de soi métacognitif et à une isolation métabolique stricte.

---

## 2. Piliers Architecturaux de l'Arc 6

### 2.1 Le Modèle de Soi Métacognitif (`SelfModel`)
- Un réseau dédié prédit avant chaque action :
  - Le **coût énergétique effectif** $\hat{c}(s, a)$.
  - La **probabilité de succès** $\hat{p}(s, a)$ de la tâche envisagée.
- La divergence entre prédiction et réalité produit un signal d'erreur de prédiction (surprise métacognitive) qui module l'attention et le budget de planification (Test-Time Compute).

### 2.2 Replay Épisodique Nocturne & Osmose au Foyer
- Durant la phase diurne, les transitions vécues $(s, a, r, s')$ sont emmagasinées dans un tampon épisodique borné (`EpisodicMemoryBuffer`).
- Durant la nuit, les agents se rassemblent au coin du feu (EXP-9). Deux mécanismes opèrent :
  - **Replay Hippocampique individuel** : Réactivation des trajectoires de haute surprise pour consolider les représentations internes.
  - **Osmose Sociale au Coin du Feu** : Partage d'épisodes saillants entre pairs à proximité immédiate du feu de camp, accélérant la diffusion des innovations réussies sans supervision externe.

### 2.3 Vectorisation Collective Swarm (Commandement 3)
- Remplacement des boucles Python individuelles par un moteur matriciel NumPy global (`SelfModel.learn_batch`, `consolidate_population_batch`).
- L'ensemble de la colonie consolide ses mémoires en un lot de tenseurs unique, garantissant une exécution sub-seconde à l'échelle de milliers de transitions.

### 2.4 Débiaisement Métabolique Isocalorique
- Phénotype `isocaloric=True` neutralisant tout artefact métabolique de $W$ :
  - `phenotype_energy_drain = 1.3` fixe.
  - `hp_bonus = 0.0`, `inv_capacity = 3`.
- Isole rigoureusement la politique neuronale des effets de bord corporels, permettant une mesure pure de l'intelligence in-world.

---

## 3. Résultats Empiriques & Validation

- **Convergence du modèle de soi :** Décroissance exponentielle de l'erreur MSE sur les coûts énergétiques et gain de calibration sur les probabilités de succès.
- **Survie accrue sous cycles jour/nuit :** La colonie utilisant la consolidation collective nocturne démontre une résilience supérieure face aux fluctuations écologiques.
- **Auditabilité :** Intégration complète dans le Dashboard (contrôles interactifs et badges de statut temps réel).
