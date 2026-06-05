import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..services.sandbox_service import sandbox_service

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

router = APIRouter()

class StartRequest(BaseModel):
    script_name: str
    enable_supervisor: bool = False
    run_migration: bool = False
    run_sociologist: bool = False
    world_type: str = "stoneage"
    import_agent_id: Optional[str] = None
    keep_memory: bool = False
    resource_limit: int = 4
    batch_size: int = 0
    
    # Nouvelles surcharges (Idée B)
    mutation_rate: float | None = None
    seed: int | None = None
    
    # Nouvelles analyses post-mortem (Idée A)
    run_linguist: bool = False
    run_metacognition: bool = False
    run_dream_analyzer: bool = False

@router.get("/status")
def get_status():
    status = sandbox_service.get_status()
    scripts = sandbox_service.get_available_scripts()
    return {
        **status,
        "available_scripts": scripts
    }

@router.post("/start")
def start_sandbox(req: StartRequest):
    return sandbox_service.start({
        "script_name": req.script_name,
        "enable_supervisor": req.enable_supervisor,
        "run_migration": req.run_migration,
        "run_sociologist": req.run_sociologist,
        "world_type": req.world_type,
        "import_agent_id": req.import_agent_id,
        "keep_memory": req.keep_memory,
        "mutation_rate": req.mutation_rate,
        "seed": req.seed,
        "run_linguist": req.run_linguist,
        "run_metacognition": req.run_metacognition,
        "run_dream_analyzer": req.run_dream_analyzer
    })

@router.post("/stop")
def stop_sandbox():
    return sandbox_service.stop()

@router.delete("/curriculum_state")
def reset_curriculum_state():
    import os
    import time
    state_file = os.path.join(PROJECT_ROOT, "data", "curriculum_state.json")
    if os.path.exists(state_file):
        try:
            timestamp = int(time.time())
            archive_file = os.path.join(PROJECT_ROOT, "data", f"curriculum_state_archive_{timestamp}.json")
            os.rename(state_file, archive_file)
            return {"status": "success", "message": "Curriculum state archivé et réinitialisé."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "success", "message": "No state file found."}

@router.get("/logs")
def get_logs():
    return {"logs": sandbox_service.get_logs()}

@router.get("/telemetry")
def get_telemetry():
    telemetry_data = []
    try:
        import os
        csv_path = os.path.join(PROJECT_ROOT, "results", "metacognition_logs.csv")
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Skip header and take last 50 lines
                for line in lines[-50:]:
                    if "era,tick" in line: continue
                    parts = line.strip().split(",")
                    if len(parts) >= 5:
                        telemetry_data.append({
                            "era": int(parts[0]),
                            "tick": int(parts[1]),
                            "mean_energy": float(parts[2]),
                            "mean_surprise": float(parts[3]),
                            "mean_doubt": float(parts[4])
                        })
    except Exception as e:
        print(f"Erreur lecture télémétrie: {e}")
    return {"data": telemetry_data}

class ActionRequest(BaseModel):
    action: str

@router.post("/action")
def post_action(req: ActionRequest):
    import json
    import os
    action_data = {"action": req.action, "timestamp": __import__("time").time()}
    try:
        # Append to interventions.json
        file_path = os.path.join(PROJECT_ROOT, "data", "interventions.json")
        interventions = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    interventions = json.load(f)
            except Exception:
                pass
        interventions.append(action_data)
        os.makedirs(os.path.join(PROJECT_ROOT, "data"), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(interventions, f)
        return {"status": "success", "message": f"Action {req.action} ajoutée."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/state")
def get_state():
    import json
    import os
    try:
        state_path = os.path.join(PROJECT_ROOT, "data", "state.json")
        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"size": 0, "agents": [], "items": [], "preys": [], "trees": []}

@router.get("/article")
def get_latest_article():
    import kuzu
    db_path = os.path.join(PROJECT_ROOT, "data", "experiment_graph.db")
    try:
        db = kuzu.Database(db_path, read_only=True)
        conn = kuzu.Connection(db)
        results = conn.execute("MATCH (a:Article) RETURN a.title, a.content, a.timestamp ORDER BY a.timestamp DESC LIMIT 1")
        if results.has_next():
            row = results.get_next()
            return {"title": row[0], "content": row[1], "timestamp": row[2]}
    except Exception as e:
        pass
    finally:
        if 'conn' in locals(): del conn
        if 'db' in locals(): del db
        
    return {"title": "En attente du Superviseur Ollama...", "content": "Aucun article publié pour l'instant. Cochez 'Superviseur IA' pour lancer la rédaction automatique.", "timestamp": 0}
