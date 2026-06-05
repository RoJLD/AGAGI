# ⚛️ La Boîte à Outils Atomique (Micro-NAS)

Si le fichier `3_Macro_NAS.md` décrit les "organes" (Macro-NAS) que notre AGI peut utiliser, ce fichier `1_Micro_NAS.md` décrit l'**ADN** et les **cellules de base** (Micro-NAS). 

À ce niveau microscopique, l'algorithme génétique ne manipule pas de "réseaux", mais de pures opérations mathématiques, des synapses individuelles, et des lois de la physique computationnelle. C'est à partir de ces atomes que les blocs Macro-NAS sont eux-mêmes construits.

## 1. 🧮 Opérations Mathématiques et Tensorielles (Le calcul pur)
- `MatMul (Multiplication Matricielle)` : L'atome fondamental du Deep Learning. Projette un vecteur dans un nouvel espace.
- `Element-wise Add/Mul` : Addition ou multiplication point-par-point entre deux vecteurs (fusion simple).
- `DotProduct (Produit Scalaire)` : Mesure la similarité ou l'alignement géométrique entre deux concepts.
- `Einsum (Einstein Summation)` : La notation atomique permettant de créer n'importe quelle contraction tensorielle complexe.
- `Kronecker Product` : Multiplie deux espaces vectoriels pour créer un espace d'états massivement intriqué.

## 2. 🌊 Opérations Fréquentielles (Traitement du Signal)
- `Fast Fourier Transform (FFT)` : Bascule un tenseur du domaine spatial/temporel au domaine des fréquences (idéal pour capturer des motifs globaux instantanément).
- `Wavelet Transform (Ondelettes)` : Permet d'analyser des signaux à différentes échelles de résolution.
- `Convolution Kernel (1D/2D/3D)` : Un filtre glissant qui extrait des motifs invariants par translation.

## 3. ⚡ Fonctions d'Activation (Création de non-linéarité)
Sans ces atomes, le réseau ne serait qu'une immense fonction linéaire (incapable d'apprendre la complexité du monde).
- `ReLU / LeakyReLU` : Les atomes classiques par morceaux (si négatif, alors 0). Simples et rapides.
- `GELU / Swish` : Les atomes lisses et continus, très utilisés dans les Transformers modernes.
- `Sine / Cosine (Activation Périodique)` : Permet au réseau de comprendre des fréquences, des cycles et des signaux continus (ex: réseaux SIREN).
- `Softmax / Sparsemax` : Convertit un vecteur brut en un atome de "probabilité" (dont la somme fait 1).
- `Heaviside Step Function` : Une activation brutale (0 ou 1), fondation des réseaux de neurones à impulsions (Spiking).

## 4. 🚪 Mécanismes de Filtrage (Gating)
- `Gated Linear Unit (GLU)` : Une porte logique multiplicative qui permet au réseau de choisir dynamiquement quelles informations laisser passer.
- `Sigmoid Gate` : La valve classique (0 à 1) utilisée dans la mémoire des LSTM pour décider d'oublier ou de retenir une donnée.

## 5. 🕸️ Topologies de Connexion (Les Synapses)
Comment l'information voyage d'un point A à un point B.
- `Dense Link` : Connexion où chaque neurone A parle à tous les neurones B.
- `Sparse Link` : Connexion économique où un neurone ne parle qu'à une poignée de voisins (topologie éparse).
- `Residual/Skip Connection` : L'information court-circuite le traitement et s'additionne directement à la sortie (contourne la disparition du gradient).
- `Recurrent Link` : Le neurone se renvoie son propre état au pas de temps suivant (atome de la mémoire temporelle).

## 6. ⚖️ Opérateurs de Stabilisation & Normalisation
Atomes nécessaires pour empêcher le réseau de s'effondrer mathématiquement (explosion des valeurs).
- `LayerNorm / RMSNorm` : Centre et réduit les vecteurs pour garder les signaux dans des proportions acceptables (moyenne 0, variance 1).
- `Spectral Normalization` : Punit la plus grande valeur singulière d'une matrice de poids (Lipschitz continuity) pour une stabilité absolue (très utilisé dans les GANs).
- `Gradient Clipping` : Règle qui plafonne mathématiquement la taille d'une mise à jour (coupe les pics de gradient).

## 7. 📐 Atomes d'Évaluation (Fonctions de Perte & Distances)
Comment la cellule mesure son erreur.
- `Kullback-Leibler Divergence (KL)` : Mesure l'entropie relative entre deux distributions de probabilité.
- `Wasserstein Distance` : La distance issue du transport optimal, ultra-stable pour évaluer deux distributions déconnectées.
- `InfoNCE (Contrastive Loss)` : Pousse les concepts similaires à s'attirer dans l'espace mathématique et les concepts différents à se repousser violemment.

## 8. 🎲 Régularisation & Bruit (Entropie contrôlée)
- `Dropout` : Désactive aléatoirement des neurones entiers à chaque passage pour forcer l'adaptation.
- `DropConnect` : Coupe des connexions synaptiques individuelles plutôt que des neurones entiers.
- `Gaussian Noise Injection` : Ajoute une perturbation continue (bruit blanc) aux tenseurs pour forcer le modèle à généraliser.

## 9. 🧬 Règles de Mise à Jour (Optimiseurs & Plasticité)
C'est la manière dont le "poids" d'une connexion change après une expérience.
- `Hebbian Update` : *"Cells that fire together, wire together"*. L'atome d'apprentissage biologique local, sans calcul d'erreur globale.
- `AdamW / L-BFGS` : Atomes mathématiques calculant le gradient avec inertie (momentum) ou courbure du second ordre.
- `SAM (Sharpness-Aware Minimization)` : Cherche des minimums d'erreur "plats" plutôt que "pointus", rendant l'architecture beaucoup plus tolérante aux mutations.
- `Weight Decay (L2 Penalty)` : L'atome qui "ronge" lentement le poids d'une synapse à chaque étape pour éviter les valeurs extrêmes.

## 10. 🌱 Atomes de Naissance (Initialisation)
- `Xavier / Kaiming Initialization` : Les règles mathématiques pures qui définissent la variance avec laquelle les poids naissent au temps T=0 pour éviter l'explosion de l'activation.
- `Orthogonal Initialization` : Force les matrices de poids à être parfaitement orthogonales dès le départ, préservant l'énergie des vecteurs qui les traversent.

## 11. 📏 Précision & Types de Données (La matière première)
La taille physique de l'information dans la mémoire de l'ordinateur.
- `FP32 / FP16 / BF16` : Les atomes flottants standards (haute précision, forte consommation).
- `INT8 / INT4` : Des atomes quantifiés en nombres entiers (perte de nuances, mais ultra-rapides et légers).
- `Binary (-1, +1) / Ternary (-1, 0, +1)` : La forme la plus compressée possible. Le réseau devient un gigantesque circuit logique booléen.
