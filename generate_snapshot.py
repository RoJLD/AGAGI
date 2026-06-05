import os
from src.worlds.world_1_stoneage import Biosphere3D
from src.environments.config import WorldConfig
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig, Genome
import numpy as np

config = WorldConfig()
env = Biosphere3D(config=config)

mut_config = MutationConfig()
num_inputs = config.agent.num_inputs
num_outputs = config.agent.num_outputs
N = num_inputs + num_outputs + 5
W = np.zeros((N, N))
mut_genes = np.array([0.1, 0.1, 0.1, 0.1, 0.1, 3.0])
W_router = np.random.normal(0, 2.0, size=(num_inputs, 3))
bytecode = np.array([0, 1, 2, 4, 3], dtype=int)
thresholds = np.random.rand(N) * 0.2

for i in range(10):
    g = Genome(W.copy(), num_inputs, num_outputs, mut_genes, W_router, bytecode, thresholds)
    agent = MambaAgent()
    agent.from_genome(g)
    env.add_agent(agent, energy=50.0)

# Init DB
from src.graph_rag.async_logger import logger
logger.start()

import time
time.sleep(2) # let db init

agent_id = env.agents[0]["id"][:8]
print(f"Agent ID to trace: {agent_id}")

for tick in range(21):
    env.step()
    if tick % 10 == 0:
        best = env.agents[0]
        import json
        logger.emit("COGNITIVE_SNAPSHOT", {
            "agent_id": best["id"][:8],
            "tick": tick,
            "ntm_memory": json.dumps(best["model"].ntm_memory.tolist() if hasattr(best["model"], "ntm_memory") else []),
            "attention_mask": json.dumps(best["model"].attention_mask.tolist() if hasattr(best["model"], "attention_mask") else []),
            "w_connectome": json.dumps(best["model"].genome.W.tolist())
        })

logger.stop()
print("Done generating snapshot")
