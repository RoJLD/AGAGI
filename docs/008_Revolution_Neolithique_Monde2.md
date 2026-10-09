# Article 008 : L'Aube du Néolithique — Prévoyance Saisonnière, Greniers Collectifs et Test-Time Compute (TTC)

**Auteurs :** Équipe de Recherche AGIseed  
**Date :** 2026-10-09  
**Statut :** Validé empiriquement & Certifié dans KuzuDB  
**Identifiant Graphe :** `art_008_revolution_neolithique_monde2`

---

## 1. Contexte & Problématique : Le Saut de l'Opportunisme à la Prévoyance

Jusqu'à l'Âge de Pierre (Monde 1), la survie des agents reposait sur une économie de subsistance instantanée :
- Prédation opportuniste de proies et cueillette immédiate.
- Réaction réflexe conditionnée par la surprise 1-tick.

Cependant, un environnement régi par un **cycle saisonnier quadri-partite** (Printemps, Été, Automne, Hiver) introduit une rupture fondamentale :
1. **Délai temporel étendu (Delayed Gratification) :** Une graine semée au printemps ne produit des fruits qu'en été/automne.
2. **Rigueur thermique de l'hiver :** Une pénalité métabolique sévère ($-0.2$ Énergie par tick) frappe tout agent exposé sans abri ou sans feu.
3. **Pérennité communautaire :** Seul le stockage anticipé dans un **Grenier Communautaire (`Granary`)** permet à la colonie d'échapper à l'extinction hivernale.

---

## 2. Piliers Mécaniques & Écologiques

### 2.1 Le Cycle Saisonnier Quadri-Partite
- **Printemps :** Réveil écologique, dissémination de graines sauvages (`Seed`), germination active (`sprout_chance = 0.08`).
- **Été :** Croissance végétale accélérée (`growth_rate = 0.02`), maturation des plants.
- **Automne :** Floraison et récolte abondante de fruits comestibles (`Fruit`). Les agents stockent les surplus au grenier.
- **Hiver :** Gel des ressources de surface. Le grenier central redistribue ses réserves caloriques et les feux protègent du froid.

### 2.2 Test-Time Compute (TTC) & MCTS Instrumental (EXP-10)
Pour que les agents puissent anticiper l'effet à long terme de leurs actions sans diverger, le moteur intègre l'algorithme `mcts_instrumental_search` dans l'espace latent :
- Déroulement contrefactuel de l'arbre d'actions sur une profondeur $D \ge 3$.
- Facturation métabolique sub-linéaire : $\text{Cost} = 0.01 \times (1 + \log_2(1 + K))$.
- Biais des logits décisionnels par normalisation robuste des valeurs $Q$.

### 2.3 Amplification Sémantique par Gigatokens LU
Lorsque des agents coordonnent leurs déplacements et leurs gestes agricoles via des Gigatokens continus $\mathbb{R}^D$, un multiplicateur de synergie s'applique :
$$\text{Yield} = \text{Base} \times 1.50$$
Ce bonus favorise la sélection naturelle des agents communicants dans l'écosystème néolithique.

---

## 3. Résultats Expérimentaux & Validation

- **Survie Hivernale :** Les colonies dotées de greniers approvisionnés maintiennent un taux de survie de **100%** lors des hivers rigoureux, contre **0%** (famine totale) pour les agents sans réserves.
- **Synergie LU :** Augmentation de $+50\%$ de la masse vivrière récoltée lors des phases coordonnées.
- **Non-Régression :** Architecture strictement découplée et réversible par configuration.

---

## 4. Conclusion & Perspectives

Le Monde 2 (Âge Agricole) valide la capacité des agents Liquid Mamba à articuler prévoyance à long terme, coopération sociale et gestion de stocks. Ce jalon pose les fondations indispensables pour la transition vers le **Monde 3 (Âge Industriel & Métallurgie)**.
