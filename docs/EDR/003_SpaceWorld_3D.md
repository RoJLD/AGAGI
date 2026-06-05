# EDR 003 : Simulateur Volumétrique 3D (SpaceWorld)

## Contexte
La navigation 2D a été résolue. Pour prouver la robustesse de l'évolution NAS et préparer l'IA à des tâches complexes du monde réel (drones, robotique), le modèle doit percevoir et naviguer dans un espace volumétrique 3D (X, Y, Z).

## Décision
- Création de `src/environments/spaceworld.py`.
- Passage des capteurs de distances de 4 à 6 (+Z, -Z).
- Extension de la Carte Cognitive Absolue de 2 à 3 axes (AbsX, AbsY, AbsZ).
- Extension des actions motrices de 4 à 6 (Avancer, Reculer, Gauche, Droite, Monter, Descendre).
- Total Inputs : 11. Total Outputs : 6.

## Conséquences
- L'espace de recherche topologique de la matrice $W$ explose. 
- Les premières générations seront extrêmement inefficaces (mouvements browniens dans un cube).
- Nécessitera une forte pression évolutive et potentiellement l'intervention de la "Méta-Cognition des Mémoires" (EDR à venir) si l'évolution stagne.
