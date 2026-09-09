import os
import pickle
import numpy as np
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from src import paths

# ⚠️ `HOF_PATH` PRIME sur la racine, et ce n'est pas un detail : EVO-003 s'en sert pour imposer
# une tabula rasa (cf. tools/evo_memory_inworld.py). L'ignorer changerait SILENCIEUSEMENT le
# sujet d'un bras de mesure. Sans elle, le chemin vient de `src/paths.py` -- donc d'une racine
# configurable (AGAGI_DATA_ROOT), ce qui rend le NAS possible sans toucher a ce fichier.
HALL_OF_FAME_PATH = os.environ.get("HOF_PATH") or paths.hall_of_fame()
AGENT_STATE_DIR = paths.agent_states() + os.sep
HOF_VERSION = 2

@dataclass
class AgentSnapshot:
    score: float
    genome: Any
    stats: Dict[str, Any]
    state_path: Optional[str] = None

# EDR 056 : poids de la distinction référentielle dans la fitness. 0 = OFF (la propagation par
# fitness a backfiré : métrique bruitée à faible compte). Conservé comme seam (cf. EDR 056).
REF_FITNESS_WEIGHT = 0.0

# EDR 060/063 : SPÉCIATION du HoF (protège l'innovation immature, mur EDR 058). False = top-N global
# classique (défaut, inchangé). MODE : "size" (par taille d'archi, NAS) | "token" (par token d'apex
# dominant, langage). HOF_MAX = taille du HoF.
SPECIATE = False
SPECIATE_MODE = "size"
HOF_MAX = 10


def _speciation_key(snapshot):
    """Clé de niche d'un AgentSnapshot selon SPECIATE_MODE."""
    if SPECIATE_MODE == "token":
        return snapshot.stats.get("apex_token", -1) if getattr(snapshot, "stats", None) else -1
    return getattr(getattr(snapshot, "genome", None), "num_nodes", 0)

def calculate_life_score(agent) -> float:
    # EDR 016/017 : le craft entre dans la fitness (poids fort) pour que la selection
    # saisisse les crafteurs maintenant que le HoF est persiste -> le craft peut evoluer.
    # EDR 028 : l'apex-kill (chasse coopérative au Mammouth, bout de la chaîne) pèse fort
    # -> la sélection saisit le chasseur-coopératif pour que la chaîne devienne DOMINANTE.
    # EDR 056 : fitness alignée sur le langage — TENTÉE puis DÉSACTIVÉE. Mettre la distinction
    # référentielle dans la fitness a BACKFIRÉ (métrique bruitée à faible compte -> propage des
    # agents à distinction FORTUITE, dégrade la population). Poids 0 = off (réversion propre).
    return ((agent["age"] * 0.1) + (agent["preys_eaten"] * 50.0)
            + (agent["altars_solved"] * 20.0) + (agent.get("spears_crafted", 0) * 300.0)
            + (agent.get("mammoth_kills", 0) * 400.0)
            + (agent.get("_ref_distinction", 0.0) * REF_FITNESS_WEIGHT))

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

def save_to_hall_of_fame(agent, score=None) -> Optional[str]:
    """Sauvegarde agent + état dans HoF. `score` optionnel : si fourni (ex. score ROBUSTE moyenné sur
    K ères, EDR 079), il remplace le life_score d'une seule ère (bruité) pour la sélection/le cliquet."""
    os.makedirs(os.path.dirname(HALL_OF_FAME_PATH), exist_ok=True)
    if score is None:
        score = calculate_life_score(agent)
    if score < 1.0:
        return None

    version, hof = load_hall_of_fame()
    import copy
    stats = {"age": agent["age"], "preys_eaten": agent["preys_eaten"], "altars_solved": agent["altars_solved"], "spears_crafted": agent.get("spears_crafted", 0), "mammoth_kills": agent.get("mammoth_kills", 0), "score": score, "apex_token": agent.get("_apex_token", -1)}
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
    if SPECIATE:
        # Spéciation par TAILLE d'architecture (EDR 060) : réserver une niche au meilleur de chaque
        # taille -> protège l'innovation immature (un 173-nœuds n'est plus écrasé par les 172 rodés ;
        # il garde un siège et peut MÛRIR). Puis compléter par le top global. (Mur EDR 058.)
        seen, reserved_idx = set(), []
        for idx, e in enumerate(hof):
            n = _speciation_key(e)                  # niche par taille (NAS) ou token (langage)
            if n not in seen:
                seen.add(n)
                reserved_idx.append(idx)
        reserved = [hof[i] for i in reserved_idx]
        rest = [hof[i] for i in range(len(hof)) if i not in set(reserved_idx)]
        hof = (reserved + rest)[:HOF_MAX]
    else:
        hof = hof[:HOF_MAX]

    with open(HALL_OF_FAME_PATH, "wb") as f:
        pickle.dump({'version': HOF_VERSION, 'entries': hof}, f)
    return state_path

def load_hall_of_fame() -> Tuple[int, list]:
    """Charge HoF. Returns (version, entries).

    ⚠️ CORRIGE le 2026-09-08. L'implementation precedente avalait TOUTE exception (`except: pass`) et
    rendait `(1, [])` : un fichier ABSENT (cas legitime, pas encore d'evolution), un fichier
    CORROMPU, et un HoF reellement VIDE devenaient INDISCERNABLES. Consequence mesuree le jour meme :
    `HOF_PATH` etant repointe vers un chemin inexistant par un import (cf. `tools/evo_memory_inworld`),
    `load_champion_genome` annoncait « HoF vide : evoluer d'abord » -- un diagnostic FAUX, qui envoie
    chercher le probleme a l'oppose de sa cause. Et `tools/arm_nas` en tirait la MESURE `(0, 0)`.

    Contrat desormais : fichier absent -> `(1, [])`, silencieusement, c'est le cas nominal du depot
    neuf. Fichier PRESENT mais illisible -> l'exception REMONTE, avec le chemin. On ne fabrique pas
    un « vide » depuis une panne."""
    # (Le format pickle est PRE-EXISTANT et l'artefact est un fichier LOCAL du depot, produit par
    # `save_hall_of_fame` ; ce correctif ne change que la gestion d'exception, pas la
    # deserialisation. Migrer le format serait une autre tache, a inscrire au backlog.)
    if not os.path.exists(HALL_OF_FAME_PATH):
        return 1, []
    try:
        with open(HALL_OF_FAME_PATH, "rb") as f:
            loaded = pickle.load(f)
    except Exception as e:
        raise RuntimeError(
            "Hall of Fame ILLISIBLE : %s (%s: %s). Ce n'est PAS un HoF vide -- ne pas le lire comme "
            "tel. Verifier HOF_PATH (une variable d'environnement, que certains modules posent A "
            "L'IMPORT) et l'integrite du fichier." % (HALL_OF_FAME_PATH, type(e).__name__, e)) from e
    if isinstance(loaded, dict) and 'version' in loaded:
        return loaded['version'], loaded.get('entries', [])
    if isinstance(loaded, list):
        return 1, loaded
    raise RuntimeError(
        "Hall of Fame de forme INATTENDUE (%s) dans %s : ni dict versionne, ni liste. Rendre « vide » "
        "ici masquerait une corruption silencieuse." % (type(loaded).__name__, HALL_OF_FAME_PATH))

def save_epoch_state(agents: list, epoch: int, save_dir: str = None) -> dict:
    """Sauvegarde état de tous les agents à la fin d'une ère."""
    # Resolu A L'APPEL et non a l'import : une racine posee par un runner APRES
    # l'import doit etre entendue (le defaut fige a l'import est la classe E5).
    save_dir = save_dir if save_dir is not None else paths.epoch_states() + os.sep
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

def load_epoch_state(epoch: int, save_dir: str = None) -> list:
    """Charge état de tous les agents d'une ère."""
    # Resolu A L'APPEL et non a l'import : une racine posee par un runner APRES
    # l'import doit etre entendue (le defaut fige a l'import est la classe E5).
    save_dir = save_dir if save_dir is not None else paths.epoch_states() + os.sep
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
