"""
main_curriculum.py — Point d'entrée ontogénétique (cf. docs/EDR/008_Developmental_Curriculum.md).

Enchaîne les worlds par portes de maîtrise via le CurriculumRunner, au lieu de
tourner N ères dans un monde fixe (main_biosphere.py). Le champion d'un monde
maîtrisé est snapshotté dans KuzuDB puis réimporté dans le monde suivant
(init_primordial_soup(import_agent_id=...)).

Usage :
    python main_curriculum.py
    KEEP_MEMORY=1 python main_curriculum.py    # transporte aussi la mémoire NTM
"""
import os
import json
import time
import logging
from typing import Optional, List, Dict

from src.curriculum.runner import (
    CurriculumRunner, WorldStage, GraduationConfig, EraResult,
)
from src.curriculum.competence import competence_for
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_2_agricultural import AgriculturalWorld
from src.worlds.world_3_industrial import IndustrialWorld
from src.environments.config import WorldConfig
from src.agents.mamba_agent import MambaAgent
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.persistence import calculate_life_score
from main_biosphere import init_primordial_soup

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("AGIseed.Curriculum.Main")

# Mondes canoniques (même interface add_agent(model)). world_0_soup est legacy
# (son add_agent prend un genome) -> exclu de la ladder pour l'instant.
WORLD_FACTORY = {
    "stoneage": Biosphere3D,
    "agricultural": AgriculturalWorld,
    "industrial": IndustrialWorld,
}

# Ladder développementale par défaut (EDR 008 §Échelle de Développement).
DEFAULT_LADDER = ["stoneage", "agricultural", "industrial"]


def _emit_champion_snapshot(champ: Dict, tick: int) -> None:
    """Snapshot SYNCHRONE du connectome du champion : garantit qu'il est écrit
    en base avant que le monde suivant ne tente de le réimporter (anti-race)."""
    model = champ["model"]
    async_logger.emit_sync("COGNITIVE_SNAPSHOT", {
        "agent_id": champ["id"][:8],
        "tick": int(tick),
        "ntm_memory": json.dumps(model.ntm_memory.tolist() if hasattr(model, "ntm_memory") else []),
        "attention_mask": json.dumps(model.attention_mask.tolist() if hasattr(model, "attention_mask") else []),
        "w_connectome": json.dumps(model.genome.W.tolist()),
    }, timeout=15.0)


def make_run_era_fn(shared_db, config: WorldConfig, num_agents: int = 60, max_ticks: int = 400):
    """Fabrique le callback run_era_fn injecté dans le CurriculumRunner.

    Une "ère" = une vie→extinction (ou max_ticks) dans un monde, avec :
      - genèse depuis le champion hérité (import_agent_id) si fourni,
      - calcul de la compétence du monde (competence.py),
      - snapshot du champion pour la promotion vers le monde suivant.
    """
    def run_era_fn(world_type: str, import_agent_id: Optional[str], keep_mem: int) -> EraResult:
        env = WORLD_FACTORY[world_type](config)

        genomes, imported_ntm = init_primordial_soup(
            num_agents=num_agents,
            import_agent_id=import_agent_id,
            keep_memory=bool(keep_mem),
            shared_db=shared_db,
            config=config,
        )
        for g in genomes:
            agent = MambaAgent()
            agent.from_genome(g)
            if imported_ntm is not None:
                agent.ntm_memory = imported_ntm.copy()
            env.add_agent(agent, energy=50.0)

        env.current_era = 1
        t = 0
        while len(env.agents) > 0 and t < max_ticks:
            env.step()
            t += 1

        # Stats sur tous (survivants + morts) — cf. base_world.run_era.
        all_agents = env.agents + env.dead_agents
        agent_stats = [{
            "age": a.get("age", 0),
            "energy": a.get("energy", 0.0),
            "preys_eaten": a.get("preys_eaten", 0),
            "altars_solved": a.get("altars_solved", 0),
            "total_dreams": a.get("total_dreams", 0),
        } for a in all_agents]

        competence = competence_for(world_type)(agent_stats)

        champion_id = None
        if all_agents:
            champ = max(all_agents, key=calculate_life_score)
            champion_id = champ["id"][:8]
            try:
                _emit_champion_snapshot(champ, env.ticks)
            except Exception as e:  # noqa: BLE001 — la promotion ne doit pas tuer le run
                logger.warning("Snapshot champion échoué (%s) : promotion sans transfert.", e)

        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()

        logger.info(
            "   · %-12s | ticks=%-4d | n=%-3d | C=%.3f | champ=%s",
            world_type, t, len(all_agents), competence, champion_id,
        )
        return EraResult(
            competence=competence,
            champion_agent_id=champion_id,
            raw_stats={"n": len(all_agents), "ticks": t},
        )

    return run_era_fn


def _acquire_shared_db():
    """Attend que le worker async_logger ait initialisé KuzuDB."""
    for _ in range(50):
        db = async_logger.get_db()
        if db is not None:
            return db
        time.sleep(0.1)
    return None


def run_curriculum(
    ladder: Optional[List[str]] = None,
    keep_memory: Optional[bool] = None,
    grad_cfg: Optional[GraduationConfig] = None,
    num_agents: int = 60,
    max_ticks: int = 400,
    manage_logger: bool = True,
) -> List[Dict]:
    """Lance le curriculum complet et renvoie le transcript développemental.

    manage_logger=False : suppose que async_logger est déjà démarré (utile pour
    le harnais Ratio de Transfert qui enchaîne plusieurs runs sans cycler la DB).
    """
    ladder = ladder or DEFAULT_LADDER
    if keep_memory is None:
        keep_memory = os.getenv("KEEP_MEMORY", "0") == "1"

    if manage_logger:
        async_logger.start()
    shared_db = _acquire_shared_db()
    if shared_db is None:
        logger.error("KuzuDB indisponible — abandon.")
        if manage_logger:
            async_logger.stop()
        return []

    config = WorldConfig()
    run_era_fn = make_run_era_fn(shared_db, config, num_agents=num_agents, max_ticks=max_ticks)
    stages = [WorldStage(w) for w in ladder]

    logger.info("🧬 Curriculum développemental : %s (keep_memory=%s)",
                " → ".join(ladder), keep_memory)
    transcript = CurriculumRunner(stages, run_era_fn, grad_cfg=grad_cfg,
                                  keep_memory=keep_memory).run()

    logger.info("✅ Curriculum terminé. Transcript développemental :")
    for row in transcript:
        logger.info("   %s", row)

    os.makedirs("results", exist_ok=True)
    out = "results/curriculum_transcript.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2)
    logger.info("📄 Transcript écrit dans %s", out)

    if manage_logger:
        async_logger.stop()
    return transcript


if __name__ == "__main__":
    run_curriculum()
