from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import logging
from ..services.kuzu_service import kuzu_service

router = APIRouter()
log = logging.getLogger(__name__)

@router.get("/strategy_tree")
def get_strategy_tree():
    """
    Returns data formatted for a Dendrogram (Tree) and a Sankey Diagram.
    It queries KuzuDB to find correlations between Worlds, Species Traits, and Results.
    """
    from src.graph_rag.experiment_tracker import ExperimentGraph
    
    tracker = None
    try:
        tracker = ExperimentGraph(kuzu_service.db_path, read_only=True)
        # We query the Experiments that ran in a World and created a Species, and yielded a Result
        query = """
        MATCH (w:WorldVersion)<-[:RAN_IN_WORLD]-(e:Experiment)-[:YIELDED_RESULT]->(r:Result),
              (e)-[:CREATED_SPECIES]->(s:Species)
        OPTIONAL MATCH (e)-[:HAS_HYPERPARAMETERS]->(h:Hyperparameters)
        RETURN w.name, s.traits, h.params, AVG(r.max_score) as avg_fitness, COUNT(e) as run_count
        """
        res = tracker.conn.execute(query)
        
        has_results = False
        world_dict = {}
        sankey_nodes_set = set()
        sankey_links = []
        
        while res.has_next():
            has_results = True
            row = res.get_next()
            world_name = row[0]
            traits_str = row[1]
            hp_str = row[2]
            avg_fitness = row[3]
            run_count = row[4]
            
            try:
                traits = json.loads(traits_str)
            except:
                traits = [traits_str] if traits_str else ["Unknown"]
                
            # Parse Hyperparameters
            hp_label = "Mutation_Normal"
            if hp_str:
                try:
                    hp_data = json.loads(hp_str)
                    mut_rate = hp_data.get("mutation_rate", 0.05)
                    if mut_rate > 0.1:
                        hp_label = "High_Mutation"
                    elif mut_rate < 0.05:
                        hp_label = "Low_Mutation"
                except:
                    pass
                
            # Use the first trait or combination for simplicity in Sankey
            trait_label = "+".join(traits) if traits else "Tabula_Rasa"
            
            # Build Tree Data (Keep Tree Macro)
            if world_name not in world_dict:
                world_dict[world_name] = []
            
            world_dict[world_name].append({
                "name": trait_label,
                "fitness": round(avg_fitness, 2),
                "runs": run_count
            })
            
            # Build Sankey Data (Include Hyperparameters)
            sankey_nodes_set.add((world_name, "World"))
            sankey_nodes_set.add((trait_label, "Trait"))
            sankey_nodes_set.add((hp_label, "Hyperparameters"))
            
            outcome_label = "High Survival" if avg_fitness > 50 else "Low Survival"
            sankey_nodes_set.add((outcome_label, "Outcome"))
            
            sankey_links.append({"source": world_name, "target": trait_label, "value": run_count})
            sankey_links.append({"source": trait_label, "target": hp_label, "value": run_count})
            sankey_links.append({"source": hp_label, "target": outcome_label, "value": run_count})

        if has_results:
            tree_data = {
                "name": "AGIseed Base",
                "children": [
                    {"name": w, "children": children} for w, children in world_dict.items()
                ]
            }
            sankey_data = {
                "nodes": [{"id": name, "group": grp} for name, grp in sankey_nodes_set],
                "links": sankey_links
            }
            return {"tree": tree_data, "sankey": sankey_data, "source": "live"}

        # DB sans donnée de stratégie : état vide HONNÊTE (plus de mock fantôme). Le frontend
        # distingue "pas encore de run" (empty) de vrai (live) via `source`.
        return {"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "empty"}
    except Exception as e:
        log.error(f"Strategy Tree Error: {e}")
        return {"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "error"}
    finally:
        if tracker:
            if hasattr(tracker, 'conn'): del tracker.conn
            if hasattr(tracker, 'db'): del tracker.db
            del tracker
