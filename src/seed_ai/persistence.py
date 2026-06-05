import os
import pickle
import numpy as np
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

HALL_OF_FAME_PATH = "data/hall_of_fame.pkl"
AGENT_STATE_DIR = "data/agent_states/"
HOF_VERSION = 2

@dataclass
class AgentSnapshot:
    score: float
    genome: Any
    stats: Dict[str, Any]
    state_path: Optional[str] = None

def calculate_life_score(agent) -> float:
    return (agent["age"] * 0.1) + (agent["preys_eaten"] * 50.0) + (agent["altars_solved"] * 20.0)

def save_agent_state(agent, path: str) -> str:
    """Sauvegarde état complet d'un MambaAgent en .npz."""
    state = {
        'H_prev': agent.H_prev,
        'H_history': agent.H_history,
        'H_potentials': agent.H_potentials,
        'surprise': np.array([agent.surprise]),
        'attention_mask': agent.attention_mask,
        'explicit_memory': agent.explicit_memory,
        'genome_W': agent.genome.W,
        'genome_num_inputs': agent.genome.num_inputs,
        'genome_num_outputs': agent.genome.num_outputs,
        'genome_mutation_genes': agent.genome.mutation_genes,
    }
    npz_path = path if path.endswith('.npz') else f"{path}.npz"
    os.makedirs(os.path.dirname(npz_path) if os.path.dirname(npz_path) else '.', exist_ok=True)
    np.savez(npz_path, **state)
    return npz_path

def load_agent_state(agent, path: str) -> bool:
    """Charge l'état dans un MambaAgent depuis .npz."""
    try:
        data = np.load(path)
        agent.H_prev = data['H_prev'].astype(np.float32) if 'H_prev' in data else agent.H_prev
        agent.H_history = data['H_history'].astype(np.float32) if 'H_history' in data else agent.H_history
        agent.H_potentials = data['H_potentials'].astype(np.float32) if 'H_potentials' in data else agent.H_potentials
        agent.surprise = float(data['surprise'][0]) if 'surprise' in data else 0.0
        agent.attention_mask = data['attention_mask'].astype(np.float32) if 'attention_mask' in data else agent.attention_mask
        agent.explicit_memory = data['explicit_memory'].astype(np.float32) if 'explicit_memory' in data else agent.explicit_memory
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load agent state: {e}")
        return False

def save_to_hall_of_fame(agent) -> Optional[str]:
    """Sauvegarde agent + état dans HoF."""
    os.makedirs(os.path.dirname(HALL_OF_FAME_PATH), exist_ok=True)
    score = calculate_life_score(agent)
    if score < 1.0:
        return None

    version, hof = load_hall_of_fame()
    import copy
    stats = {"age": agent["age"], "preys_eaten": agent["preys_eaten"], "altars_solved": agent["altars_solved"], "score": score}
    genome = agent["model"].genome if "model" in agent else agent["genome"]
    agent_id = f"{score}_{agent['age']}_{len(hof)}"

    state_path = None
    if "model" in agent and hasattr(agent["model"], 'H_prev'):
        state_dir = os.path.join(AGENT_STATE_DIR, "hall_of_fame")
        os.makedirs(state_dir, exist_ok=True)
        state_path = os.path.join(state_dir, f"{agent_id}.npz")
        save_agent_state(agent["model"], state_path)

    hof.append(AgentSnapshot(score=score, genome=copy.deepcopy(genome), stats=stats, state_path=state_path))
    hof.sort(key=lambda x: getattr(x, 'score', x[0] if isinstance(x, tuple) else 0), reverse=True)
    hof = hof[:10]

    with open(HALL_OF_FAME_PATH, "wb") as f:
        pickle.dump({'version': HOF_VERSION, 'entries': hof}, f)
    return state_path

def load_hall_of_fame() -> Tuple[int, list]:
    """Charge HoF. Returns (version, entries)."""
    if os.path.exists(HALL_OF_FAME_PATH):
        try:
            with open(HALL_OF_FAME_PATH, "rb") as f:
                loaded = pickle.load(f)
                if isinstance(loaded, dict) and 'version' in loaded:
                    return loaded['version'], loaded.get('entries', [])
                elif isinstance(loaded, list):
                    return 1, loaded
        except:
            pass
    return 1, []

def save_epoch_state(agents: list, epoch: int, save_dir: str = "data/epoch_states/") -> dict:
    """Sauvegarde état de tous les agents à la fin d'une ère."""
    os.makedirs(save_dir, exist_ok=True)
    saved_paths = {}
    for i, agent in enumerate(agents):
        path = os.path.join(save_dir, f"epoch_{epoch}_agent_{i}.npz")
        save_agent_state(agent, path)
        saved_paths[f"epoch_{epoch}_agent_{i}"] = path
    import json
    with open(os.path.join(save_dir, f"epoch_{epoch}_meta.json"), 'w') as f:
        json.dump({'epoch': epoch, 'num_agents': len(agents), 'state_files': saved_paths}, f)
    return saved_paths

def load_epoch_state(epoch: int, save_dir: str = "data/epoch_states/") -> list:
    """Charge état de tous les agents d'une ère."""
    from src.agents.mamba_agent import MambaAgent
    meta_path = os.path.join(save_dir, f"epoch_{epoch}_meta.json")
    if not os.path.exists(meta_path):
        return []
    import json
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    loaded = []
    for agent_id, path in meta['state_files'].items():
        if os.path.exists(path):
            a = MambaAgent()
            if load_agent_state(a, path):
                loaded.append(a)
    return loaded

def migrate_old_hall_of_fame() -> bool:
    """Migre ancien HoF (v1) vers nouveau format (v2)."""
    if not os.path.exists(HALL_OF_FAME_PATH):
        return False
    try:
        with open(HALL_OF_FAME_PATH, "rb") as f:
            loaded = pickle.load(f)
    except:
        return False
    if isinstance(loaded, dict) and loaded.get('version', 1) >= 2:
        return False
    if isinstance(loaded, list):
        new_entries = []
        for old in loaded:
            if isinstance(old, tuple) and len(old) >= 3:
                new_entries.append(AgentSnapshot(score=old[0], genome=old[1], stats=old[2], state_path=None))
        import shutil
        shutil.copy2(HALL_OF_FAME_PATH, f"{HALL_OF_FAME_PATH}.backup_v1")
        with open(HALL_OF_FAME_PATH, "wb") as f:
            pickle.dump({'version': HOF_VERSION, 'entries': new_entries}, f)
        print(f"[MIGRATION] HoF migrated to v{HOF_VERSION}")
        return True
    return False
