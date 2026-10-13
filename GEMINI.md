# GEMINI.md — Instructions Persistantes pour Agents IA (AGIseed)

Ce fichier est lu automatiquement par tout agent IA travaillant sur ce projet.
Il contient les regles NON-NEGOCIABLES du projet AGIseed.

---

## Commandement 15 : Protocole d'Innovation Unitaire (PIU) — "La Loi du Sociologue"

> **"Chaque innovation provoque une regression temporaire. N'introduis JAMAIS plus d'UNE variable experimentale entre deux versions de la simulation."**

### Procedure Obligatoire :
1. **Baseline** : Faire tourner la version actuelle pendant **30 Eres minimum**. Enregistrer les metriques dans KuzuDB.
2. **Intervention** : Introduire **UNE SEULE** modification.
3. **Observation** : Faire tourner la nouvelle version pendant **30 Eres minimum**.
4. **Analyse** : Executer `tools/sociologist.py` pour comparer Avant/Apres.
5. **Decision** : Score moyen >= Baseline → VALIDE. Sinon → REVERT.

### Exception :
Les corrections de bugs (famine, crashes, encodage) ne comptent PAS comme des innovations.

---

## Commandement 16 : Journalisation Scientifique (Articles)

**"Toute découverte, observation ou conclusion majeure issue des expérimentations doit être impérativement consignée sous forme d'article dans le graphe de connaissances (KuzuDB)."**

### Procédure :
1. Chaque nouvelle dynamique ou validation d'hypothèse doit faire l'objet d'un "Article".
2. L'article est stocké en tant que nœud `Article` dans KuzuDB.
3. Ces articles alimentent directement l'onglet "Articles" du Dashboard pour l'apprentissage et le suivi.

---

## Commandement 14 : Validation par Simulation

Ne jamais construire de "cathedrale de code" sans valider les fondations.
Avant d'ajouter une nouvelle mecanique, l'agent DOIT s'assurer que la precedente fonctionne.

---

## Architecture Cognitive Actuelle (V15/V16)

- **Entrees** : 45 (Lidar 6D, Position, Proie, Altar, Social, Langue, Surprise, Worm, Throw Feedback, Propriétés Physiques)
- **Sorties** : 25 (Mouvement 6D, Cognitif, Saut, Grab, Throw, Rub, Social 3, Visee 3D, Parole 4)
- **Moteur** : Liquid Mamba BatchModel (ODE continu, Vectorisé)
- **Memoire** : H_prev, KuzuDB Async Sink
- **Metacognition** : Signal de Surprise, Feedback Lancer, TTC Adaptatif, Feedback Inventaire Plein
- **Ecologie** : Proies, Vers, Crafting (Friction, Étincelle, Feu)
- **Outils** : Skinner Box, Sociologue KuzuDB, Migration Chirurgicale

---

## Backlog d'Experiences (Ordre de Priorite)
Voir `roadmap.md` pour le detail complet.
1. EXP-7 : Outils & Crafting par Friction (V15) — EN COURS
2. EXP-8 : Limites d'Inventaire & Émergence Vocale (V16) — EN COURS
3. EXP-9 : Maîtrise du Feu et Regroupement Social
4. EXP-10 : Test-Time Compute Adaptatif (MCTS Avancé)
