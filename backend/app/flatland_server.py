import asyncio
import time
import threading
from dataclasses import fields
from typing import Dict, Any

import numpy as np
from src.environments.config import WorldConfig
from src.swarm.consensus import WeightedConsensus
from src.swarm.hgt import HorizontalGeneTransfer, HGTConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent

# Clés whitelistées qui visent un champ IMBRIQUÉ de WorldConfig (et non un champ plat).
# La valeur est le chemin dotté à écrire. Ex. "mutation_rate" pilote le VRAI levier de mutation,
# imbriqué dans cfg.agent.mutation.weight_mutate_rate (cf. main_biosphere.py:221 qui fait
# exactement ce mapping). Un setattr plat attacherait un attribut MORT cfg.mutation_rate que rien
# ne lit -> piège à échec silencieux pour un framework A/B (intervention sans effet).
_NESTED_OVERRIDES = {
    "mutation_rate": "agent.mutation.weight_mutate_rate",
}

# Champs plats réels de WorldConfig (dataclass) : on n'autorise un setattr plat que sur eux,
# sinon setattr créerait un attribut fantôme silencieux.
_WORLDCONFIG_FIELDS = {f.name for f in fields(WorldConfig)}

# Overrides de config autorisés pour un run (la "variable d'intervention" de l'A/B). Spec §5.
WHITELIST = ({"active_exp_variable", "robust_hof_K", "base_metabolism",
              "forage_payoff", "size", "num_altars", "prey_mode"}
             | set(_NESTED_OVERRIDES))


def _apply_override(cfg, key, value):
    """Applique un override whitelisté sur la WorldConfig.

    - clé imbriquée (_NESTED_OVERRIDES) -> écrit le vrai champ imbriqué (ex. mutation_rate ->
      cfg.agent.mutation.weight_mutate_rate), pas un attribut plat mort.
    - clé plate -> doit être un champ RÉEL de WorldConfig (dataclasses.fields), sinon le setattr
      créerait un attribut fantôme que rien ne lit (échec silencieux).
    """
    path = _NESTED_OVERRIDES.get(key)
    if path is not None:
        target = cfg
        *parents, leaf = path.split(".")
        for attr in parents:
            target = getattr(target, attr)
        if not hasattr(target, leaf):
            raise ValueError(f"override imbrique invalide: {key} -> {path} (champ inexistant)")
        setattr(target, leaf, value)
        return
    if key not in _WORLDCONFIG_FIELDS:
        raise ValueError(
            f"override whiteliste mais absent de WorldConfig: {key} "
            f"(setattr plat creerait un attribut mort)")
    setattr(cfg, key, value)


class FlatlandServer:
    def __init__(self, config_overrides=None, pop_size=10, label=None):
        cfg = WorldConfig(size=32, num_altars=5, prey_mode="semi")
        for k, v in (config_overrides or {}).items():
            if k not in WHITELIST:
                raise ValueError(f"override de config non autorise: {k} (autorises: {sorted(WHITELIST)})")
            _apply_override(cfg, k, v)
        self.cfg = cfg
        self.label = label
        self.world = Biosphere3D(self.cfg)
        self.queue = None
        self.running = False
        self.loop = None
        self.era = 1                 # run ÉVOLUTIVE live : la pop descend du HoF, qui s'améliore par ère
        self.pop_size = pop_size
        self._seed_from_hof()

    def _seed_from_hof(self):
        """Peuple depuis le Hall of Fame (ancêtres évolués) ; fallback agents frais si indisponible."""
        try:
            from main_biosphere import init_primordial_soup
            genomes, _ = init_primordial_soup(num_agents=self.pop_size, config=self.cfg)
            for g in genomes:
                a = MambaAgent()
                a.from_genome(g)
                self.world.add_agent(a)
        except Exception:
            for _ in range(self.pop_size):
                self.world.add_agent(MambaAgent())

    def _save_and_advance(self):
        """À l'extinction : sauve les meilleurs au HoF (sélection → ère suivante), puis re-seed."""
        try:
            from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
            pool = list(getattr(self.world, "dead_agents", []))
            for cand in sorted(pool, key=calculate_life_score, reverse=True)[:5]:
                save_to_hall_of_fame(cand)
        except Exception:
            pass
        try:
            self.world.dead_agents = []
        except Exception:
            pass
        self.era += 1
        self._seed_from_hof()

    def extract_frame(self) -> Dict[str, Any]:
        agents = []
        for a in self.world.agents:
            agents.append({
                "x": int(a["x"]),
                "y": int(a["y"]),
                "hp": float(a["hp"]),
                "energy": float(a["energy"]),
                "inventory_size": len(a.get("inventory", [])),
                "last_action": int(a.get("last_action", -1))
            })
            
        preys = []
        for p in self.world.preys:
            preys.append({
                "x": int(p["x"]),
                "y": int(p["y"]),
                "type": p["type"],
                "hp": float(p.get("hp", 1.0)),
                "stunned": int(p.get("stunned", 0))
            })
            
        items = []
        for i in self.world.items:
            t = i["type"]
            if isinstance(t, dict):
                t = t.get("type", "unknown")
            items.append({
                "x": int(i["x"]),
                "y": int(i["y"]),
                "type": t
            })
            
        worms = []
        for w in self.world.worms:
            worms.append({
                "x": int(w["x"]),
                "y": int(w["y"])
            })
            
        altars = []
        for alt in self.world.altars:
            altars.append({
                "x": int(alt["x"]),
                "y": int(alt["y"])
            })

        agent_count = len(agents)
        total_energy = sum(a["energy"] for a in agents) if agent_count else 0.0
        total_hp = sum(a["hp"] for a in agents) if agent_count else 0.0
        prey_count = len(preys)
        item_count = len(items)
        altar_count = len(altars)
        energy_std = float(np.std([a["energy"] for a in agents])) if agent_count else 0.0
        hp_std = float(np.std([a["hp"] for a in agents])) if agent_count else 0.0

        positions = [(a["x"], a["y"]) for a in agents]
        pairs = 0
        shared_tiles = 0
        for i in range(agent_count):
            for j in range(i + 1, agent_count):
                pairs += 1
                if positions[i] == positions[j]:
                    shared_tiles += 1
        social_density = float(shared_tiles / pairs) if pairs else 0.0

        genome_distances = []
        for i in range(agent_count):
            for j in range(i + 1, agent_count):
                w1 = self.world.agents[i]["model"].genome.W
                w2 = self.world.agents[j]["model"].genome.W
                if w1.shape != w2.shape:
                    # Pad to match max dimension
                    max_dim = max(w1.shape[0], w2.shape[0])
                    w1_padded = np.zeros((max_dim, max_dim))
                    w2_padded = np.zeros((max_dim, max_dim))
                    w1_padded[:w1.shape[0], :w1.shape[1]] = w1
                    w2_padded[:w2.shape[0], :w2.shape[1]] = w2
                    genome_distances.append(float(np.linalg.norm(w1_padded - w2_padded)))
                else:
                    genome_distances.append(float(np.linalg.norm(w1 - w2)))
        genome_diversity = float(np.mean(genome_distances)) if genome_distances else 0.0

        return {
            "ticks": self.world.ticks,
            "size": self.world.size,
            "agents": agents,
            "preys": preys,
            "items": items,
            "worms": worms,
            "altars": altars,
            "terrain_type": self.world.terrain_type.tolist(),
            "geometry": self.world.geometry[0].tolist(),
            "summary": {
                "era": self.era,
                "agent_count": agent_count,
                "avg_energy": total_energy / agent_count if agent_count else 0.0,
                "avg_hp": total_hp / agent_count if agent_count else 0.0,
                "energy_std": energy_std,
                "hp_std": hp_std,
                "social_density": social_density,
                "genome_diversity": genome_diversity,
                "prey_count": prey_count,
                "item_count": item_count,
                "altar_count": altar_count,
            },
        }

    def _simulation_loop(self):
        last_frame_time = 0.0
        frame_interval = 1.0 / 30.0

        while self.running:
            self.world.step()
            
            # Extinction -> nouvelle ère évolutive (sauve les meilleurs, re-seed depuis le HoF)
            if len(self.world.agents) == 0:
                self._save_and_advance()

            now = time.time()
            if now - last_frame_time > frame_interval:
                frame = self.extract_frame()
                
                # Push to asyncio queue thread-safely
                def _push_to_queue(f):
                    try:
                        if self.queue.full():
                            self.queue.get_nowait()
                        self.queue.put_nowait(f)
                    except Exception:
                        pass

                self.loop.call_soon_threadsafe(_push_to_queue, frame)
                last_frame_time = now

    def start(self, loop=None):
        if not self.running:
            if loop is not None:
                self.loop = loop
            else:
                try:
                    self.loop = asyncio.get_running_loop()
                except RuntimeError:
                    try:
                        self.loop = asyncio.get_event_loop()
                    except RuntimeError:
                        self.loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self.loop)
            self.queue = asyncio.Queue(maxsize=1)
            self.running = True
            self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False

flatland_server = FlatlandServer(label="default")
