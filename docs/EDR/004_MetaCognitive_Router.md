# EDR 004 : Méta-Cognition Pure NumPy (Routeur de Mémoires)

## Contexte
Avec l'ajout de 5 mémoires biologiques (V3), le réseau risque la surcharge cognitive. L'agent doit développer la capacité de choisir "quelle mémoire écouter" en fonction du contexte, simulant ainsi l'Introspection et l'Attention.

## Décision (V5)
- Ajout d'une matrice `W_router` (num_inputs x 3) au Génome.
- Ce routeur effectue une opération `Softmax` sur les capteurs (Senses) pour produire un vecteur d'Attention $R$.
- $R$ module les flux mémoriels :
  - $R_0$ : Poids accordé à la Mémoire de Travail ($H_{prev}$).
  - $R_1$ : Poids accordé au KV Cache ($H_{attention}$).
  - $R_2$ : Poids accordé à la Mémoire Spatiale (Phéromones).
- C'est l'implémentation algorithmique du concept de "Mixture of Experts" (MoE) et d'un "Gating Network".
- L'évolution de cette capacité se fait de façon purement endogène (mutations NumPy) sans l'intervention du LLM (repoussé à la V8).

## Conséquences
- Séparation conceptuelle stricte entre *Perception* (Sens bruts toujours reçus) et *Cognition* (Mémoires modulées).
- Permet aux agents de survivre dans des environnements trompeurs (ex: si la piste de phéromones est un piège, le routeur apprendra à muter pour ignorer l'odeur).
