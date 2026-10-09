"""
LU (Langage Ultime) & DSL Optimization Engine for AGIseed.

This module implements the dual-level cognitive pipeline described in LU theory:
1. Front-End / Translator: Bi-directional mapping between Natural Language / Intent
   and canonical Symbolic Graph ASTs (LU DSL).
2. Macro-Tokenizer / Gigatoken Vectorizer: Compiles LU ASTs into dense high-density
   vector states.
3. Subquadratic Vector Engine: Executes state-space transformations on LU graphs in O(N)
   time using NumPy tensorized operations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import re
import numpy as np
from typing import Dict, List, Tuple, Optional, Any


@dataclass
class LUConfig:
    """Hyper-parameters for the LU DSL Engine (Commandment 1: Flexible)."""
    vector_dim: int = 64
    max_macro_tokens: int = 1000
    sparsity_lambda: float = 0.01
    canonical_delimiter: str = "->"
    enable_gigatokens: bool = True
    seed: int = 42


@dataclass
class LUNode:
    """Represents a symbolic node in the LU AST graph."""
    id: str
    category: str  # e.g., 'CONCEPT', 'ACTION', 'CONTEXT', 'STATE'
    label: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[np.ndarray] = None


@dataclass
class LUGraph:
    """Canonical Graph AST representation of LU (Bijection 1 Intent <-> 1 Graph)."""
    nodes: Dict[str, LUNode] = field(default_factory=dict)
    edges: List[Tuple[str, str, str]] = field(default_factory=list)  # (source_id, relation, target_id)

    def to_dsl_string(self) -> str:
        """Serializes the graph into canonical LU DSL format."""
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.id)
        node_strs = [f"@{n.category}:{n.label}[{n.id}]" for n in sorted_nodes]
        
        sorted_edges = sorted(self.edges, key=lambda e: (e[0], e[1], e[2]))
        edge_strs = [f"({src})-[{rel}]->({tgt})" for src, rel, tgt in sorted_edges]
        
        return " ; ".join(node_strs) + (" EDGES: " + " ; ".join(edge_strs) if edge_strs else "")


class LUCompiler:
    """
    Compiles text/DSL into canonical LUGraph ASTs and high-density Gigatoken vectors.
    """
    def __init__(self, config: Optional[LUConfig] = None):
        self.config = config or LUConfig()
        np.random.seed(self.config.seed)
        self.vocabulary_vectors: Dict[str, np.ndarray] = {}

    def _get_or_create_vector(self, symbol: str) -> np.ndarray:
        """Generates or retrieves a deterministic dense vector embedding for a symbol."""
        if symbol not in self.vocabulary_vectors:
            # Deterministic pseudo-random generation based on symbol hash
            hash_seed = abs(hash(symbol)) % (2**32)
            rng = np.random.default_rng(hash_seed)
            vec = rng.normal(0, 1.0 / np.sqrt(self.config.vector_dim), size=(self.config.vector_dim,))
            self.vocabulary_vectors[symbol] = vec / (np.linalg.norm(vec) + 1e-9)
        return self.vocabulary_vectors[symbol]

    def parse_dsl(self, dsl_str: str) -> LUGraph:
        """
        Parses an LU DSL string into a canonical LUGraph AST.
        Format: @CATEGORY:label[id] ; ... EDGES: (src)-[rel]->(tgt) ; ...
        """
        graph = LUGraph()
        if not dsl_str.strip():
            return graph

        if "EDGES:" in dsl_str:
            parts = dsl_str.split("EDGES:", 1)
            node_part = parts[0].strip()
            edge_part = parts[1].strip()
        else:
            node_part = dsl_str.strip()
            edge_part = ""

        # Parse nodes: @CATEGORY:label[id]
        node_pattern = re.compile(r"@([A-Z_]+):([^\[]+)\[([^\]]+)\]")
        for match in node_pattern.finditer(node_part):
            cat, label, node_id = match.groups()
            vec = self._get_or_create_vector(f"{cat}:{label}")
            graph.nodes[node_id] = LUNode(
                id=node_id,
                category=cat,
                label=label.strip(),
                vector=vec
            )

        # Parse edges: (src)-[rel]->(tgt)
        edge_pattern = re.compile(r"\(([^)]+)\)-\[([^\]]+)\]->\(([^)]+)\)")
        for match in edge_pattern.finditer(edge_part):
            src, rel, tgt = match.groups()
            if src in graph.nodes and tgt in graph.nodes:
                graph.edges.append((src, rel, tgt.strip()))

        return graph

    def compile_to_gigatoken(self, graph: LUGraph) -> np.ndarray:
        """
        Compresses an LU AST LUGraph into a single Gigatoken Vector (High-density representation).
        Vectorized pooling & relation tensor projection (Commandment 3: Vectorization).
        """
        if not graph.nodes:
            return np.zeros(self.config.vector_dim, dtype=np.float64)

        node_vecs = []
        for node in graph.nodes.values():
            if node.vector is None:
                node.vector = self._get_or_create_vector(f"{node.category}:{node.label}")
            node_vecs.append(node.vector)

        # Base node pooling (mean vector)
        gigatoken = np.mean(node_vecs, axis=0)

        # Edge relation shifts
        for src_id, rel, tgt_id in graph.edges:
            src_v = graph.nodes[src_id].vector
            tgt_v = graph.nodes[tgt_id].vector
            rel_v = self._get_or_create_vector(f"REL:{rel}")
            # Non-linear tensorized interaction: Hadamard product + relation shift
            interaction = (src_v * tgt_v) + rel_v
            gigatoken += 0.5 * interaction

        # Normalization (Commandment 9: Numerical Stability)
        norm = np.linalg.norm(gigatoken)
        if norm > 1e-9:
            gigatoken = gigatoken / norm

        return gigatoken


class LUVectorExecutor:
    """
    Linear O(N) Subquadratic Execution Engine for LU Gigatokens & Graphs.
    Replaces traditional O(N^2) sequence attention with state-space linear transformations.
    """
    def __init__(self, config: Optional[LUConfig] = None):
        self.config = config or LUConfig()
        # Initialize subquadratic linear state transition matrix (W_state)
        rng = np.random.default_rng(self.config.seed)
        self.W_state = rng.orthogonal_matrix(self.config.vector_dim) if hasattr(rng, 'orthogonal_matrix') else np.eye(self.config.vector_dim)

    def execute_step(self, current_state: np.ndarray, gigatoken_input: np.ndarray) -> np.ndarray:
        """
        Executes one state propagation step: State_next = tanh(W_state @ State + Gigatoken).
        Linear complexity O(D^2) relative to vector dimension D, O(1) relative to sequence length.
        """
        # Ensure dimensions match
        if current_state.shape[0] != self.config.vector_dim:
            raise ValueError(f"State dim {current_state.shape[0]} does not match config {self.config.vector_dim}")
        
        # Subquadratic linear propagation (Vectorized NumPy)
        net = np.matmul(self.W_state, current_state) + gigatoken_input
        next_state = np.tanh(net)

        # Guard against NaN/Inf (Commandment 9)
        if np.isnan(next_state).any() or np.isinf(next_state).any():
            next_state = np.nan_to_num(next_state, nan=0.0, posinf=1.0, neginf=-1.0)

        return next_state


class LUFrontEndBridge:
    """
    Front-End Sémantique: Translates Natural Language intent into canonical LU DSL format.
    Serves as the interface between raw human prompts and the compressed LU Back-End.
    """
    def __init__(self, compiler: Optional[LUCompiler] = None):
        self.compiler = compiler or LUCompiler()

    def translate_nl_to_lu(self, text: str) -> str:
        """
        Rule-based & keyword-derived semantic translator converting NL to canonical LU DSL.
        Example: "AGIseed executes SwarmNAS under HighPerformance"
        -> @AGENT:AGIseed[n1] ; @TARGET:SwarmNAS[n2] ; @CONTEXT:HighPerformance[n3] EDGES: (n1)-[EXECUTE]->(n2) ; (n1)-[WITH_CONTEXT]->(n3)
        """
        words = text.strip().split()
        if not words:
            return ""

        # Heuristic concept filtering: capital words or key nouns
        stopwords = {"under", "with", "over", "the", "and", "or", "a", "an", "in", "on", "at", "for", "to", "executes", "runs"}
        concepts = [w.strip(".,!?") for w in words if w.istitle() or (len(w) > 4 and w.lower() not in stopwords)]
        if not concepts:
            concepts = ["Task"]

        nodes = []
        edges = []

        # Build canonical nodes
        for idx, concept in enumerate(concepts[:5], start=1):
            category = "CONCEPT"
            if idx == 1:
                category = "AGENT"
            elif idx == 2:
                category = "TARGET"
            else:
                category = "CONTEXT"
            nodes.append(f"@{category}:{concept}[n{idx}]")

        # Build canonical edge relations
        if len(nodes) >= 2:
            edges.append("(n1)-[EXECUTE]->(n2)")
        if len(nodes) >= 3:
            edges.append("(n1)-[WITH_CONTEXT]->(n3)")

        node_str = " ; ".join(nodes)
        edge_str = " ; ".join(edges)

        return f"{node_str}" + (f" EDGES: {edge_str}" if edge_str else "")

    def translate_lu_to_summary(self, graph: LUGraph) -> str:
        """Translates LU Graph AST back into a human-readable high-density summary."""
        if not graph.nodes:
            return "LU Graph: Empty"
        
        node_summaries = [f"{n.category}({n.label})" for n in graph.nodes.values()]
        edge_summaries = [f"{src}->[{rel}]->{tgt}" for src, rel, tgt in graph.edges]

        return f"LU Summary: [{', '.join(node_summaries)}] | Relations: [{', '.join(edge_summaries)}]"
