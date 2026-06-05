import asyncio
import time
import threading
from typing import Dict, Any

import numpy as np
from src.environments.config import WorldConfig
from src.swarm.consensus import WeightedConsensus
from src.swarm.hgt import HorizontalGeneTransfer, HGTConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent

class FlatlandServer:
    def __init__(self):
        self.world = Biosphere3D(WorldConfig(size=32, num_altars=5, prey_mode="semi"))
        self.queue = asyncio.Queue(maxsize=1)
        self.running = False
        self.loop = asyncio.get_event_loop()
        
        # Spawn 10 agents
        for _ in range(10):
            agent = MambaAgent()
            self.world.add_agent(agent)

    def extract_frame(self) -> Dict[str, Any]:
        agents = []
        for a in self.world.agents:
            agents.append({
                "x": a["x"],
                "y": a["y"],
                "hp": a["hp"],
                "energy": a["energy"],
                "inventory_size": len(a.get("inventory", [])),
                "last_action": a.get("last_action", -1)
            })
            
        preys = []
        for p in self.world.preys:
            preys.append({
                "x": p["x"],
                "y": p["y"],
                "type": p["type"],
                "hp": p.get("hp", 1.0),
                "stunned": p.get("stunned", 0)
            })
            
        items = []
        for i in self.world.items:
            t = i["type"]
            if isinstance(t, dict):
                t = t.get("type", "unknown")
            items.append({
                "x": i["x"],
                "y": i["y"],
                "type": t
            })
            
        worms = []
        for w in self.world.worms:
            worms.append({
                "x": w["x"],
                "y": w["y"]
            })
            
        altars = []
        for alt in self.world.altars:
            altars.append({
                "x": alt["x"],
                "y": alt["y"]
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
            
            # Restart if everyone dies
            if len(self.world.agents) == 0:
                for _ in range(10):
                    self.world.add_agent(MambaAgent())

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

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False

flatland_server = FlatlandServer()
