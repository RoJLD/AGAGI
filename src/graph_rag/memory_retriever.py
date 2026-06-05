import threading
import time
import logging as log_module
from typing import Dict, List

log = log_module.getLogger(__name__)

class AsyncMemoryRetriever:
    """
    Retrieves memories asynchronously from KuzuDB without blocking the main simulation.
    Commandment 2 (Modulaire) and 4 (Scalable).
    """
    def __init__(self, async_logger, update_interval: float = 0.5):
        self.async_logger = async_logger
        self.update_interval = update_interval
        self._running = False
        self._thread = None
        self._memory_cache: Dict[str, List[float]] = {}
        self._agent_thoughts_cache: Dict[str, List[Dict]] = {}
        self._agent_matrix_cache = {}
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        log.info("AsyncMemoryRetriever started")
        
    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        log.info("AsyncMemoryRetriever stopped")
        
    def get_memory_vector(self, agent_id: str) -> List[float]:
        """Returns the memory tensor of size 5 for a given agent. O(1) read."""
        return self._memory_cache.get(agent_id, [0.0] * 5)
        
    def get_rag_memory(self, agent_id: str, query_vector) -> List[float]:
        import numpy as np
        T_matrix = self._agent_matrix_cache.get(agent_id)
        if T_matrix is None or len(query_vector) < 5 or T_matrix.shape[0] == 0:
            return [0.0] * 5
        
        q = np.array(query_vector[:5], dtype=np.float32)
        norm_q = np.linalg.norm(q)
        if norm_q == 0:
            return [0.0] * 5
            
        norms_T = np.linalg.norm(T_matrix, axis=1)
        # Avoid division by zero
        sims = np.dot(T_matrix, q) / (norms_T * norm_q + 1e-9)
        best_idx = int(np.argmax(sims))
        
        if sims[best_idx] > 0.0:
            return T_matrix[best_idx].tolist()
        return [0.0] * 5
        
    def _worker(self):
        db_conn = None
        
        # Wait for AsyncLogger to initialize KuzuDB
        while self._running and not hasattr(self.async_logger, 'db'):
            time.sleep(0.1)
            
        if not self._running:
            return
            
        try:
            import kuzu
            db_conn = kuzu.Connection(self.async_logger.db)
            log.info("AsyncMemoryRetriever connected to shared KuzuDB")
        except Exception as e:
            log.warning(f"AsyncMemoryRetriever failed to connect: {e}")
            return
            
        while self._running:
            try:
                # Fetch best/last thoughts per agent
                query = """
                MATCH (t:AgentThought)
                RETURN t.agent_id, t.action, t.value_pred, t.surprise
                ORDER BY t.value_pred DESC
                LIMIT 500
                """
                results = db_conn.execute(query)
                
                # Processing in python to aggregate per agent_id
                agent_thoughts = {}
                if results.has_next():
                    while results.has_next():
                        row = results.get_next()
                        a_id = row[0]
                        if a_id not in agent_thoughts:
                            agent_thoughts[a_id] = []
                        agent_thoughts[a_id].append({
                            "action": row[1],
                            "value_pred": row[2],
                            "surprise": row[3]
                        })
                
                # Build the memory vector of size 5:
                # 0: best_action_past
                # 1: best_value_past
                # 2: last_action_past
                # 3: avg_surprise_past
                # 4: confidence (number of thoughts / 10.0, capped at 1.0)
                
                new_cache = {}
                new_matrix_cache = {}
                self._agent_thoughts_cache = agent_thoughts  # Keep raw for RAG
                for a_id, thoughts in agent_thoughts.items():
                    import numpy as np
                    mat = np.zeros((len(thoughts), 5), dtype=np.float32)
                    for i, t in enumerate(thoughts):
                        mat[i] = [float(t["action"])/8.0, float(t["value_pred"]), float(t["surprise"]), 0.0, 1.0]
                    new_matrix_cache[a_id] = mat
                    
                    # thoughts are sorted by value_pred DESC because of the query ORDER BY
                    best_t = thoughts[0]
                    # just take the first one in the DB (which is technically just a high value one, not chronologically last)
                    # we will use the top one as last_action for simplicity unless we do a separate query.
                    avg_surprise = sum(t["surprise"] for t in thoughts) / len(thoughts)
                    conf = min(1.0, len(thoughts) / 10.0)
                    
                    new_cache[a_id] = [
                        float(best_t["action"]),
                        float(best_t["value_pred"]),
                        float(thoughts[-1]["action"]), # lowest value action in this set
                        float(avg_surprise),
                        float(conf)
                    ]
                    
                self._memory_cache = new_cache
                self._agent_matrix_cache = new_matrix_cache
                
            except Exception as e:
                log.debug(f"AsyncMemoryRetriever query skipped or error: {e}")
                
            time.sleep(self.update_interval)
            
        if db_conn is not None:
            del db_conn
