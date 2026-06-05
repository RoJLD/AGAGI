import json
import logging
from typing import List, Dict, Any

log = logging.getLogger(__name__)

class KuzuService:
    def __init__(self, db_path: str = None):
        import os
        if db_path is None:
            # Assuming this is run from project root or inside backend/app
            self.db_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "data", "kuzu_graph.db")
        else:
            self.db_path = db_path

    def get_timeline(self) -> Dict[str, Any]:
        """Fetch the evolutionary timeline from KuzuDB"""
        tracker = None
        try:
            from src.graph_rag.experiment_tracker import ExperimentGraph
            tracker = ExperimentGraph(self.db_path, read_only=True)
            nodes = []
            links = []
            
            # Fetch Experiments
            res = tracker.conn.execute("MATCH (e:Experiment) RETURN e.name, e.description")
            while res.has_next():
                row = res.get_next()
                nodes.append({"id": row[0], "label": row[0], "type": "Experiment", "desc": row[1]})
                
            # Fetch Derived_From Links
            res = tracker.conn.execute("MATCH (a:Experiment)-[:DERIVED_FROM]->(b:Experiment) RETURN a.name, b.name")
            while res.has_next():
                row = res.get_next()
                links.append({"source": row[0], "target": row[1], "type": "DERIVED_FROM"})
                
            # Fetch Species
            res = tracker.conn.execute("MATCH (s:Species) RETURN s.name, s.base_nodes")
            while res.has_next():
                row = res.get_next()
                nodes.append({"id": row[0], "label": row[0], "type": "Species", "nodes": row[1]})
                
            return {"nodes": nodes, "links": links}
        except Exception as e:
            log.error(f"Error getting timeline: {e}")
            return {"nodes": [], "links": []}
        finally:
            if tracker:
                if hasattr(tracker, 'conn'): del tracker.conn
                if hasattr(tracker, 'db'): del tracker.db
                del tracker
    def get_cognitive_snapshots(self, agent_id: str) -> List[Dict[str, Any]]:
        """Fetch NTM memory, Attention Mask, and Connectome for an agent"""
        tracker = None
        try:
            from src.graph_rag.experiment_tracker import ExperimentGraph
            tracker = ExperimentGraph(self.db_path, read_only=True)
            snapshots = []
            query = f"MATCH (c:CognitiveSnapshot) WHERE c.agent_id = '{agent_id}' RETURN c.tick, c.ntm_memory, c.attention_mask, c.w_connectome ORDER BY c.tick ASC"
            res = tracker.conn.execute(query)
            while res.has_next():
                row = res.get_next()
                tick = row[0]
                ntm_str = row[1]
                att_str = row[2]
                w_str = row[3]
                try:
                    ntm = json.loads(ntm_str) if ntm_str else []
                    att = json.loads(att_str) if att_str else []
                    w = json.loads(w_str) if w_str else []
                except:
                    ntm = []
                    att = []
                    w = []
                snapshots.append({
                    "tick": tick,
                    "ntm_memory": ntm,
                    "attention_mask": att,
                    "w_connectome": w
                })
            return snapshots
        except Exception as e:
            log.error(f"Error getting snapshots: {e}")
            return []
        finally:
            if tracker:
                if hasattr(tracker, 'conn'): del tracker.conn
                if hasattr(tracker, 'db'): del tracker.db
                del tracker

kuzu_service = KuzuService()
