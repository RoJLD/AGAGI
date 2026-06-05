# 🧠 Cognitive Toolbox (Macro-NAS)

This document lists the foundational neural modules ("Lego blocks") available to the evolutionary genetic algorithm (Macro-NAS). The Seed AI will pick, wire, and mutate these blocks to assemble complex cognitive architectures dynamically.

## 1. Perception & Embedding (Inputs)
- `TextEmbedder`: Converts discrete tokens (words) into continuous vectors.
- `PatchEmbedder`: Converts image/grid patches into vectors (Vision Transformer style).
- `GraphNodeEmbedder`: Extracts continuous representations from a KuzuDB node and its immediate edges.

## 2. Routing & Attention (Contextualization)
- `SelfAttentionBlock`: The heart of a Transformer. Allows elements in a sequence to look at each other.
- `CrossAttentionBlock`: Aligns two different sequences (e.g., matching a query with a graph).
- `SparseAttentionBlock`: Lightweight self-attention for handling extremely long sequences.

## 3. Transformations & Processing (Reasoning)
- `DenseBlock` (MLP / Feed Forward): Standard multi-layer perceptron.
- `MoEBlock` (Mixture of Experts): Routes inputs to one of N specialized sub-networks.
- `Conv1DBlock`: Fast, local pattern matching.
- `GraphConvolutionBlock (GCN/GAT)`: Message passing directly on the KuzuDB graph structure.

## 4. Control Flow & Dynamic Computation
- `ConditionalRouter (If/Else)`: Routes a vector to Block A or Block B based on a threshold.
- `AdaptiveLoopBlock (ACT)`: Feeds the output back into itself $N$ times until confidence is high.

## 5. Abstraction & World Models (JEPA-Style)
- `LatentPredictor`: Predicts the next state $S_{t+1}$ entirely in the latent space.
- `ContrastiveAligner`: Forces representations from two different modalities to align.

## 6. Swarm & Memory (HGT / Persistence)
- `StatefulMemoryCell` (LSTM/GRU style): Retains a hidden state vector across multiple passes.
- `LatticeMemoryWriter`: Explicitly writes a vector to KuzuDB as a new node/edge.
- `LatticeMemoryReader`: Retrieves the $k$-nearest neighbors from KuzuDB.
- `SwarmTransceiver`: Broadcasts a latent vector to the shared KuzuDB channel.

## 7. Outputs & Decisions
- `LogitDecoder`: Converts a latent vector back into probabilities for discrete vocabulary words.
- `ActionSelector`: Converts a vector into a policy for Reinforcement Learning.

---

# 🧬 RESEARCH TIER: Evolutionary Future Toolbox

The following blocks are highly experimental modules synthesized by specialized AI researchers. The genetic algorithm may unlock these blocks for hyper-advanced generations.

## 8. Bio-Inspiration & Neuroscience
- `Astrocyte-Mediated Metaplasticity`: A glial-inspired control layer that dynamically modulates learning rates of neighboring assemblies.
- `Dendritic Non-Linear Integration`: Multi-compartmental tree structures where individual dendritic branches perform localized non-linear computations.
- `Neuromodulatory Global Routing`: A systemic broadcast system (like dopamine) that dynamically shifts the network's operational mode (exploration/exploitation).
- `Hippocampal Replay & Sleep Consolidation`: Records episodic experiences in a fast buffer, replaying them iteratively during offline 'sleep' phases.
- `Neurogenesis & Pruning Cycles`: Dynamically spawns new neurons in active sub-networks and aggressively prunes dormant connections.
- `Ephaptic Coupling & Field Effects`: Adjacent neural modules influence each other's activation states without direct synaptic connections via simulated "electric fields".
- `Homeostatic Synaptic Scaling`: Normalizes incoming synaptic drives to a fixed set-point over long timescales to prevent catastrophic forgetting.

## 9. Physics, Thermodynamics & Chaos Theory
- `StrangeAttractorRouter`: A chaotic MoE router mapping embeddings to a fractal state space (Lorenz attractors).
- `SuperpositionAttentionLayer`: Evaluates multiple orthogonal attention matrices simultaneously in a quantum-like superposition state.
- `ThermodynamicAnnealingBottleneck`: Injects temperature-dependent continuous noise that maximizes latent entropy during early processing, cooling into sparse representations.
- `NavierStokesLatentFlow`: Models the hidden states of tokens as a continuous fluid using neural ODEs.
- `HamiltonianEnergyMinimizer`: Preserves momentum and phase-space volume during forward passes via symplectic integration.
- `TensorNetworkEntangler`: Uses Matrix Product States (MPS) to efficiently model long-range entanglement between context tokens.
- `FractalRecursiveDiminisher`: A dynamic-depth block governed by scale invariance, applying the same weights at progressively finer resolutions.

## 10. Advanced Topology & Mathematics
- `Simplicial Message Passing Layer`: Utilizes simplicial complexes to capture higher-order, multi-way relationships (triangles, tetrahedrons) between concepts.
- `Hyperbolic Concept Embedder`: Maps hierarchical knowledge into a Poincaré ball with zero distortion.
- `Categorical Functor Bridge`: Employs structure-preserving maps to translate representations between disparate cognitive domains.
- `Ricci Flow Manifold Smoother`: Iteratively smooths the latent representation manifold to resolve topological singularities.
- `Sheaf-Theoretic Consensus Protocol`: Uses cellular sheaves to model local-to-global consensus among swarm micro-agents.
- `Hodge-Laplacian Attention Mechanism`: Generalizes standard attention by operating on $k$-forms of a cell complex.
- `Fibre Bundle Expert Router`: Treats the cognitive context as a base manifold and experts as attached fibers for topologically-consistent routing.

## 11. Information Theory & Data Science
- `Kolmogorov Description Minimizer`: Forces latent representations toward their algorithmic minimum (Kolmogorov complexity) as a sparsity penalty.
- `Shannon-Bode Mutual Information Bottleneck`: Maximizes predictive mutual information between input and output while bounding channel capacity.
- `Lempel-Ziv Temporal Dictionary`: Dynamically identifies and compresses recurring latent trajectories into dictionary pointers.
- `Nyquist-Adaptive Spectral Sampler`: Adjusts sampling rate of features based on spectral entropy to prevent aliasing.
- `Latent Turbo Coder`: An error-correction block injecting structured redundancy into the feature stream.
- `Rate-Distortion Quantizer`: Dynamically adjusts bit-precision on the fly based on the loss landscape.
- `Fisher Information Manifold Router`: Routes signals along paths of maximum information geometry.

## 12. Cutting-Edge Deep Learning (2025)
- `SelectiveStateSpaceCore`: An advanced state-space model (Mamba) for O(1) inference and infinite context processing.
- `KolmogorovArnoldLayer (KAN)`: Learnable B-spline functions on the edges for highly interpretable function approximation.
- `TestTimeReasoningLoop`: Allocates latent test-time compute to perform multi-step chain-of-thought verification before emitting output (o1/R1).
- `LiquidContinuousFluid`: Adapts its underlying differential equations on the fly (Liquid Neural Networks).
- `PredictiveLatentEmbedder`: A self-supervised JEPA block predicting missing segments in latent space.
- `SwarmMixtureOfExperts`: A hyper-routed MoE processed by an evolutionary swarm of specialized micro-experts.
- `SymbolicLatticeMemory`: A differentiable retrieval interface linked to Graph-RAG.

## 13. Distributed Systems & OS Algorithms (CS)
- `NeuralRaft Consensus Block`: Resolves contradictory outputs from competing subnetworks using a quorum-based voting mechanism.
- `BGP Cognitive Router`: Maintains "routing tables" of semantic domains to optimally route queries without broadcasting.
- `Epistemic Garbage Collector`: Adapts mark-and-sweep algorithms to prune dormant synaptic weights and obsolete knowledge.
- `Preemptive Cognitive Scheduler`: Assigns priority queues and compute time-slices to parallel reasoning tasks (context-switching).
- `MESI Memory Coherency Layer`: Ensures synchronization across distributed, localized KV-caches.
- `MapReduce Attention Distiller`: Scatters massive-context inputs into parallel sub-tasks (Map), then aggregates into a high-density vector (Reduce).

## 14. Evolutionary Genetics & Swarm Intelligence
- `HGT-Synaptic-Bridge`: Facilitates peer-to-peer exchange of learned subnetworks (Horizontal Gene Transfer).
- `Epigenetic-Neuromodulator`: Dynamic, environment-dependent masking of synaptic weights (like DNA methylation).
- `Stigmergic-Lattice-Router`: Employs a shared graph layer where agents deposit "digital pheromones" to bias future cognitive processes.
- `Swarm-Attention-Substrate`: Decentralized swarm of micro-agents that generate emergent global attention through local consensus.
- `Symbiotic-Co-Evolution-Module`: Pairs distinct architectural motifs in a mutualistic or competitive training dynamic.

## 15. Cognitive Psychology & Philosophy of Mind
- `GlobalWorkspaceBottleneck`: Enforces a limited-capacity working memory to synthesize a unified "conscious" monologue.
- `PhenomenalGroundingLatent`: Embeds tokens into a simulated multidimensional sensory-affective space (Qualia representation).
- `HeuristicSalienceRouter`: Implements System 1 processing by applying rapid attention masks based on human heuristics.
- `RecursiveTheoryOfMind`: A forward-pass simulation block evaluating recursive counterfactuals ("I think that they think").
- `SemanticCoherenceAnchor`: Projects outputs into an internal causal/logical world-model, penalizing statistically-correct but logically-flawed paths.

## 16. Neuromorphic Hardware & Quantum Chemistry
- `Memristive Langevin-Hopfield Attractor (MLHA)`: Resolves non-convex energy landscapes via stochastic gradient descent, simulating thermodynamic noise.
- `Allosteric Latent Logic Gate (ALLG)`: A routing block where a "ligand" tensor induces a conformational shift in the network's processing topology.
- `Ribosomal Tensor Assembler (RTA)`: Sequentially translates 1D token embeddings into 3D stable topological tensor structures.
- `Spiking Spin-Torque Oscillator (SSTO)`: Utilizes magnetic spin-torque transfer for analog, phase-coupled neural synchronization.

## 17. Embodied AI & Robotics
- `Differentiable Physics Simulator (DPS)`: Embeds an implicit 3D Newtonian physics engine directly into the latent pathway.
- `Sensorimotor Causality Transformer (SCT)`: Maps multimodal streams into causal graphs, grounding reasoning in action-reaction loops.
- `Intuitive Gravity-Kinematics Prior (IGKP)`: A neural module pre-wired with strong inductive biases for mass, gravity, and momentum.
- `Latent Affordance Grounding Engine (LAGE)`: Projects the physical 3D environment into a latent space evaluated strictly through actionable possibilities.

## 18. Cybersecurity & Game Theory Economics
- `FHE-Latent-Shield`: Processes latent representations under Fully Homomorphic Encryption, neutralizing white-box attacks.
- `zk-SNARK-Cognitive-Validator`: Forces mutated sub-networks to emit a zero-knowledge proof of their reasoning trajectory.
- `Nash-Equilibrium-Compute-Broker`: An internal micro-economy routing layer where sub-networks spend allocated tokens in Vickrey auctions to bid for GPU cycles.
- `Byzantine-Swarm-Aggregator`: Treats subnetworks as mutually suspicious actors, utilizing proof-of-stake slashing to penalize hallucinating nodes.

---

> [!NOTE]
> **Evolutionary Rule**: The Genetic Algorithm starts by connecting an `Embedder` directly to a `Decoder`. It is then free to insert any of the blocks above in the middle to maximize its *Fitness Score*. If it inserts an expensive block without a proportional gain in accuracy, the Parsimony Penalty ($\lambda \cdot Size$) will kill the organism.
