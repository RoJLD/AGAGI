# EDR 002 : Architecture Multi-Mémoire (Cognitive Layers)

## Contexte
La chasse d'une proie mouvante (Predator-Prey) requiert de l'anticipation. Un réseau de type DAG statique ne possède pas la dimension temporelle nécessaire pour percevoir la vitesse ou se souvenir des espaces explorés.

## Décision
Implémentation de 5 couches de mémoire distinctes fusionnées dans l'évaluation RL :
1. **Short-Term (RNN)** : Injection de `H_prev` (avec decay).
2. **Episodic (KuzuDB)** : Neurones-Greffiers (Phase 6).
3. **Spatial (Stigmergie)** : `pheromone_map` dans le GridWorld.
4. **Topological (Cognitive Map)** : Injection des coordonnées absolues (X, Y).
5. **Attention (KV Cache)** : Moyenne temporelle glissante sur l'historique récent `H_history`.

## Conséquences
- Le nombre d'Inputs du génome augmente à 8 (Phase V3).
- Émergence de stratégies de coupe de trajectoire (Anticipation).
- Risque potentiel de surcharge cognitive, motivant la future "Méta-Cognition des Mémoires".
