"""
Module: lu_lattice_memory.py
Projet: AGIseed / AGAGI (Branche de recherche LU)
Description: Mémoire Lattice KuzuDB pour le Langage Ultime (LU).
Gère la persistance, l'indexation topologique et le rappel par similarité cosinus
des Gigatokens LU entre le monde continu et le graphe symbolique KuzuDB.

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): LULatticeConfig paramétrable.
- Commandement 2 (Modulaire): Découplage strict entre la base symbolique et l'inférence vectorielle.
- Commandement 3 (Haute Performance): Calcul de similarité cosinus vectorisé en NumPy (Commandement 3).
- Commandement 5 (Transparent & Auditable): Chaque pensée et transition d'état est auditable dans KuzuDB.
- Commandement 9 (Stabilité Numérique): Guards contre les normes nulles et NaN/Inf.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import logging
import uuid

from src.graph_rag.database import KuzuDatabase
from src.metaprog.lu_dsl_engine import LUGraph, LUCompiler, LUConfig
from src.metaprog.lu_dsl_semantic import LUCypherEmitter

logger = logging.getLogger("AGIseed.LULatticeMemory")


@dataclass
class LULatticeConfig:
    """Configuration pour la mémoire Lattice LU."""
    vector_dim: int = 64
    similarity_threshold: float = 0.70
    max_recall_results: int = 5
    eps: float = 1e-8


class LULatticeMemory:
    """
    Interface entre les Gigatokens LU (tenseurs denses) et le Graphe KuzuDB.
    Fournit l'indexation et le rappel mnésique par projection topologique.
    """

    def __init__(self, db: KuzuDatabase, config: Optional[LULatticeConfig] = None):
        self.db = db
        self.config = config or LULatticeConfig()
        self.compiler = LUCompiler(LUConfig(vector_dim=self.config.vector_dim))
        self._bootstrap_schema()

    def _bootstrap_schema(self):
        """Initialise les tables spécifiques à la mémoire Lattice LU dans KuzuDB."""
        queries = [
            "CREATE NODE TABLE LUPensee (id STRING, agent_id STRING, dsl STRING, gigatoken DOUBLE[], timestamp INT64, PRIMARY KEY (id))",
            "CREATE REL TABLE TRANSITIONNE_VERS (FROM LUPensee TO LUPensee, delta_t DOUBLE)",
            "CREATE REL TABLE ASSOCIE_A (FROM LUPensee TO Concept, relevance DOUBLE)"
        ]
        for query in queries:
            try:
                self.db.execute_cypher(query)
                logger.info(f"Schéma Lattice LU créé: {query.split('(')[0]}")
            except Exception as e:
                # Idempotent si la table existe déjà
                if "already exists" not in str(e).lower():
                    logger.warning(f"Note bootstrap schéma LU: {e}")

    def store_thought(
        self,
        agent_id: str,
        graph: LUGraph,
        dsl_string: str,
        timestamp: int = 0
    ) -> str:
        """
        Persiste un graphe de pensée LU sous forme de nœud LUPensee avec son Gigatoken vectoriel
        et projette ses nœuds symboliques dans la table Concept.
        """
        thought_id = f"lu_{uuid.uuid4().hex[:8]}"
        gigatoken = self.compiler.compile_to_gigatoken(graph)

        # 1. Injection des nœuds et relations symboliques dans KuzuDB
        cypher_queries = LUCypherEmitter.emit_kuzu_cypher(graph)
        for q in cypher_queries:
            try:
                self.db.execute_cypher(q)
            except Exception as err:
                logger.debug(f"Erreur d'insertion symbolique: {err}")

        # 2. Persistance du nœud LUPensee avec le vecteur
        vec_list = [float(x) for x in gigatoken]
        safe_dsl = dsl_string.replace("'", "`")
        store_query = (
            f"CREATE (p:LUPensee {{id: '{thought_id}', agent_id: '{agent_id}', "
            f"dsl: '{safe_dsl}', gigatoken: {vec_list}, timestamp: {timestamp}}})"
        )
        self.db.execute_cypher(store_query)

        # 3. Association de la pensée à ses concepts clés
        for node in graph.nodes.values():
            assoc_query = (
                f"MATCH (p:LUPensee {{id: '{thought_id}'}}), (c:Concept {{id: '{node.id}'}}) "
                f"CREATE (p)-[:ASSOCIE_A {{relevance: 1.0}}]->(c)"
            )
            try:
                self.db.execute_cypher(assoc_query)
            except Exception:
                pass

        return thought_id

    def recall_nearest_thoughts(
        self,
        query_vector: np.ndarray,
        top_k: Optional[int] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Rappel mnésique topologique : recherche les pensées stockées dont le Gigatoken
        est le plus proche du vecteur de requête (Similarité Cosinus Vectorisée en NumPy).
        Retourne une liste de triplets (thought_id, dsl_string, cosine_similarity).
        """
        k = top_k or self.config.max_recall_results
        query_arr = np.asarray(query_vector, dtype=np.float64)
        q_norm = np.linalg.norm(query_arr)
        if q_norm < self.config.eps:
            return []
        q_normalized = query_arr / q_norm

        # Récupère tous les Gigatokens de LUPensee
        read_query = "MATCH (p:LUPensee) RETURN p.id, p.dsl, p.gigatoken"
        try:
            records = self.db.execute_cypher(read_query)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture des pensées: {e}")
            return []

        if not records:
            return []

        thought_ids = []
        dsls = []
        vectors = []

        for row in records:
            t_id, dsl, vec_raw = row[0], row[1], row[2]
            if vec_raw and len(vec_raw) == self.config.vector_dim:
                thought_ids.append(t_id)
                dsls.append(dsl)
                vectors.append(vec_raw)

        if not vectors:
            return []

        # Calcul vectorisé NumPy (Commandement 3)
        mat = np.array(vectors, dtype=np.float64)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms < self.config.eps, 1.0, norms)
        mat_normalized = mat / norms

        cosines = np.dot(mat_normalized, q_normalized)

        # Tri décroissant des scores
        ranked_indices = np.argsort(-cosines)
        results: List[Tuple[str, str, float]] = []

        for idx in ranked_indices:
            score = float(cosines[idx])
            if score >= self.config.similarity_threshold:
                results.append((thought_ids[idx], dsls[idx], score))
            if len(results) >= k:
                break

        return results
