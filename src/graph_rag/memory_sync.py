import numpy as np
import logging
import uuid
from src.seed_ai.network import MicroEngine
from src.graph_rag.database import KuzuDatabase

logger = logging.getLogger("AGIseed.MemorySync")

class MemorySyncer:
    """
    Synchronizes memory between the fast synchronous NumPy MicroEngine
    and the persistent Graph-RAG (KuzuDB).
    Complies with Commandment 2 (Separation) and 4 (Scalability/Batching).
    """
    def __init__(self, db: KuzuDatabase, engine: MicroEngine):
        self.db = db
        self.engine = engine
        self._bootstrap_memory_schema()
        
    def _bootstrap_memory_schema(self):
        """Ensures the Souvenir table exists in KuzuDB."""
        try:
            self.db.execute_cypher("CREATE NODE TABLE Souvenir (id STRING, node_id INT64, activation DOUBLE, state DOUBLE[], PRIMARY KEY (id))")
            logger.info("Created 'Souvenir' table in KuzuDB.")
        except RuntimeError as e:
            if "already exists" not in str(e).lower():
                logger.error(f"Error creating Souvenir table: {e}")
                raise
                
    def sync(self):
        """
        Synchronizes memory asynchronously/in batches.
        1. Vides le memory_buffer du MicroEngine et l'écrit dans KuzuDB.
        2. Récupère des souvenirs et peuple le memory_cache pour les Neurones-Sonde.
        """
        # --- WRITE PHASE (Neurones-Greffiers) ---
        if self.engine.memory_buffer:
            logger.info(f"Syncing {len(self.engine.memory_buffer)} memories to KuzuDB in batch.")
            
            # Parametrized batch insertion
            for node_id, activation, state_vector in self.engine.memory_buffer:
                mem_id = str(uuid.uuid4())
                query = """
                CREATE (s:Souvenir {id: $id, node_id: $node_id, activation: $activation, state: $state})
                """
                params = {
                    "id": mem_id,
                    "node_id": node_id,
                    "activation": activation,
                    "state": state_vector.tolist()
                }
                self.db.execute_cypher(query, params)
                
            # Clear the buffer
            self.engine.memory_buffer.clear()
            
        # --- READ PHASE (Neurones-Sondes) ---
        read_nodes = np.where(self.engine.operations == 4)[0]
        if len(read_nodes) > 0:
            logger.info(f"Fetching memory for {len(read_nodes)} Neurone-Sondes...")
            for node_id in read_nodes:
                # Fetch most recent or strongest memory for this node_id
                query = """
                MATCH (s:Souvenir)
                WHERE s.node_id = $node_id
                RETURN s.activation AS act
                LIMIT 1
                """
                res = self.db.execute_cypher(query, {"node_id": int(node_id)})
                if res and len(res) > 0:
                    self.engine.memory_cache[node_id] = res[0][0]
                else:
                    self.engine.memory_cache[node_id] = 0.0
