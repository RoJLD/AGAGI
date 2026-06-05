# 🧬 La Boîte à Outils Méso-scopique (Meso-NAS)

Si l'échelle `1_Micro_NAS.md` (Micro-NAS) manipule les atomes (additions, ReLU, poids individuels) et que `3_Macro_NAS.md` (Macro-NAS) manipule des organes complets (un Transformer, un Moteur Physique, un Routeur BGP), l'échelle **Méso-scopique (Meso-NAS)** est l'échelle des **Molécules** ou des **Motifs Cellulaires**.

L'évolution ne construit pas un œil en assemblant des atomes au hasard. Elle utilise des protéines pré-assemblées. Dans notre réseau, l'échelle Méso définit ces "motifs de conception" (Design Patterns neuronaux) réutilisables, constitués de plusieurs atomes.

## 1. 🔄 Les Motifs de Flux (Routage de base)
- `ResNet Bottleneck` : [Conv 1x1] $\rightarrow$ [Conv 3x3] $\rightarrow$ [Conv 1x1] $+$ [Skip Connection originale]. Compresse puis décompresse l'information.
- `Inception Motif` : Le signal d'entrée est copié et passe simultanément dans 4 chemins différents (par ex: atomes spatiaux, fréquentiels, denses), puis concaténé.
- `Feed-Forward Network (FFN) Motif` : [Linear Expansion] $\rightarrow$ [GELU] $\rightarrow$ [Linear Projection]. Typique des Transformers pour la non-linéarité post-attention.

## 2. 🚪 Les Motifs de Filtrage (Gating Mechanisms)
- `LSTM Forget Gate` : Un motif qui décide exactement quel pourcentage de la mémoire doit être effacé.
- `Squeeze-and-Excitation (SE) Block` : Écrase l'information globale d'un tenseur pour produire des poids, puis s'en sert pour re-multiplier et "exciter" les caractéristiques locales.

## 3. 🔍 Les Motifs d'Attention Locaux
- `QKV Projection Head` : Multiplie un vecteur par 3 matrices distinctes pour créer une Requête (Query), une Clé (Key) et une Valeur (Value).
- `Multi-Head Splitter` : Découpe un large tenseur en $h$ sous-tenseurs parallèles, forçant le modèle à prêter attention à $h$ choses différentes.

## 4. ⚖️ Les Motifs de Stabilisation Structurale
- `Pre-Norm Residual Cell` : Contrairement à la norme post-calcul, ce motif (GPT) garantit que les gradients profonds ne meurent jamais.
- `Gradient-Reversal Layer (GRL)` : Laisse passer l'information à l'aller, mais multiplie le gradient par $-1$ au retour (Adversarial Training).

---

# 🧪 RESEARCH TIER: Les Motifs de Pointe (Générés par les Sous-Agents)

## 5. 👁️ Motifs Spatiaux & Vision Complexe (CNN Expert)
- `Omni-Scale Gated Fusion Node` : Regarde l'information à l'échelle locale, régionale et globale en même temps et utilise une porte logique pour fusionner dynamiquement ces contextes.
- `Orthogonal Channel-Weave Module` : Sépare les canaux en groupes parfaitement orthogonaux pour les traiter séparément avant de les tisser via une matrice dense (tue la redondance).
- `Fractal Involution Cell` : Motif générant des noyaux de convolution fractals à travers différentes résolutions sans exploser le nombre de paramètres.
- `Hyper-Pyramid Cross-Attention Block` : Croise l'attention spatiale entre des chemins de résolutions très différentes, injectant les détails précis dans la carte sémantique floue.

## 6. ⏱️ Motifs Temporels & Séquentiels (Time-Series Expert)
- `Selective State-Routing Gated Cell (SSRGC)` : Intègre des espaces d'états (Mamba) avec un routage dynamique dirigeant la séquence vers des canaux de décroissance temporelle distincts.
- `Chunk-wise Retentive Meta-State (CRMS)` : Partitionne la séquence en blocs. Les dépendances internes utilisent l'attention, les dépendances temporelles utilisent une matrice d'état récurrente (RetNet).
- `Gradient-Driven Temporal State Layer` : La cellule temporelle met à jour ses propres poids locaux via une mini-descente de gradient au lieu d'une simple porte logique.
- `Frequency-Partitioned Decay Scan` : Les signaux à haute fréquence décroissent instantanément, tandis que les "ancrages" basse fréquence restent dans une mémoire lente.

## 7. 🕸️ Motifs Graphes & Topologie (GNN Expert)
- `Dynamic Edge-Conditioned Routing (DECR)` : Agrège les messages des voisins en fonction d'un plongement (embedding) appris directement sur l'arête reliant les nœuds.
- `Tensorized Attention Aggregation` : Un motif vectorisé qui bypass les boucles lentes de GNN classiques par de pures contractions tensorielles (massivement accéléré par GPU).
- `Multi-Resolution AnchorSAGE` : Échantillonne le voisinage dense local, tout en tirant quelques liens vers de lointains "nœuds ancres" (Hubs) pour éviter le sur-lissage.
- `Lattice-Grounded Message Passing` : Propage les messages KuzuDB via une grille de mémoire intermédiaire auditable, assurant une parfaite transparence du processus cognitif.

## 8. ⚡ Motifs d'Optimisation Matérielle (Hardware Expert)
- `SRAM-Fused Tensor Interleaving` : Fusionne projection, activation et normalisation en une seule molécule exécutée exclusivement en mémoire SRAM (L1) pour éviter les goulots d'étranglement de la VRAM.
- `Block-Cyclic Sparse Routing` : Distribue le routage des tokens via une disposition cyclique, maximisant l'usage de l'ALU et minimisant les collisions de cache L2.
- `Asynchronous Page-Locked KV Streaming` : Motif asynchrone qui pré-charge (DMA) les blocs de clés/valeurs (KV Cache) directement dans les cœurs Tensor, chevauchant le temps de calcul et d'IO mémoire.
- `Shift-Register Residuals` : Remplace la classique addition mathématique (Skip Connection) par un transfert de registre physique matériel pour court-circuiter totalement la hiérarchie mémoire.
