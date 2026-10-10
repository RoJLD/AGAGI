"""
src/agents/dream_replay.py — Consolidation Épisodique Nocturne (Hippocampal Replay / EXP-11).
Permet aux agents d'apprendre hors-ligne durant les phases nocturnes ou de repos :
1. Stocke les transitions récentes dans un buffer épisodique glissant.
2. Rejoue et compresse les expériences passées (replay hippocampique vectorisé).
3. Entraîne le WorldModel et calibre le SelfModel sans coût moteur.
Conforme aux 12 Commandements AGIseed (3. NumPy vectorisé, 5. Traçabilité KuzuDB, 9. Stabilité numérique).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from src.agents.world_model import WorldModel
from src.agents.self_model import SelfModel
from src.graph_rag.async_logger import logger


@dataclass
class ReplayExperience:
    """Transition unitaire stockée dans le buffer épisodique."""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    energy_spent: float
    success: bool


class EpisodicMemoryBuffer:
    """Buffer circulaire de mémoire épisodique individuelle ou collective."""

    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        self.buffer: List[ReplayExperience] = []
        self.index: int = 0

    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, energy_spent: float, success: bool):
        exp = ReplayExperience(
            state=np.asarray(state, dtype=np.float32).copy(),
            action=int(action),
            reward=float(reward),
            next_state=np.asarray(next_state, dtype=np.float32).copy(),
            energy_spent=float(energy_spent),
            success=bool(success)
        )
        if len(self.buffer) < self.capacity:
            self.buffer.append(exp)
        else:
            self.buffer[self.index] = exp
            self.index = (self.index + 1) % self.capacity

    def sample_batch(self, batch_size: int = 16) -> List[ReplayExperience]:
        if not self.buffer:
            return []
        actual_size = min(batch_size, len(self.buffer))
        indices = np.random.choice(len(self.buffer), size=actual_size, replace=False)
        return [self.buffer[i] for i in indices]

    def __len__(self) -> int:
        return len(self.buffer)


EpisodicReplayBuffer = EpisodicMemoryBuffer


class NightConsolidator:
    """
    Moteur de consolidation offline pendant le sommeil / rassemblement au feu.
    Rejoue les souvenirs, met à jour le WorldModel et affine le SelfModel.
    """

    def __init__(self, world_model: Optional[WorldModel] = None, replay_batch_size: int = 16):
        self.world_model = world_model
        self.replay_batch_size = replay_batch_size
        self.total_consolidations: int = 0

    def consolidate_agent(self, agent_id: str, memory: EpisodicMemoryBuffer, self_model: Optional[SelfModel] = None) -> Dict[str, Any]:
        if len(memory) < 4:
            return {"status": "insufficient_memories", "loss_reduction": 0.0}

        batch = memory.sample_batch(self.replay_batch_size)
        pre_loss = 0.0
        post_loss = 0.0

        for exp in batch:
            # 1. Évaluation et apprentissage du WorldModel
            if self.world_model is not None:
                # Perte avant consolidation
                err_pre = self.world_model.observe(exp.state, exp.next_state, train=False)
                pre_loss += float(np.mean(err_pre))

                # Pas d'apprentissage offline (rêve)
                self.world_model.observe(exp.state, exp.next_state, train=True)

                # Perte après consolidation
                err_post = self.world_model.observe(exp.state, exp.next_state, train=False)
                post_loss += float(np.mean(err_post))

            # 2. Étalonnage du SelfModel (métacognition)
            if self_model is not None:
                self_model.learn_step(
                    state_vec=exp.state,
                    actual_cost=exp.energy_spent,
                    task_success=exp.success
                )

        n = max(1, len(batch))
        avg_pre = pre_loss / n
        avg_post = post_loss / n
        loss_reduction = max(0.0, avg_pre - avg_post)

        self.total_consolidations += 1

        logger.emit("DREAM_CONSOLIDATION", {
            "agent_id": agent_id,
            "replayed_steps": len(batch),
            "pre_dream_loss": float(avg_pre),
            "post_dream_loss": float(avg_post),
            "loss_reduction": float(loss_reduction)
        })

        return {
            "status": "consolidated",
            "replayed_steps": len(batch),
            "pre_loss": float(avg_pre),
            "post_loss": float(avg_post),
            "loss_reduction": float(loss_reduction)
        }

    def consolidate_shared_dream(
        self,
        dream: Any,
        dream_engine: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Consolide une trajectoire de rêve sémantique partagé dans le WorldModel sans coût moteur (Phase 11 M1)."""
        traj = getattr(dream, "trajectory", [])
        gain = float(getattr(dream, "counterfactual_gain", 0.0))
        dream_id = getattr(dream, "dream_id", "unknown_dream")
        if self.world_model is None or len(traj) < 2:
            return {"status": "skipped", "loss_reduction": 0.0, "gain": gain}

        err_pre = 0.0
        err_post = 0.0
        n_steps = len(traj) - 1
        for i in range(n_steps):
            s_cur = traj[i]
            s_nxt = traj[i+1]
            e_pre = self.world_model.observe(s_cur, s_nxt, train=False)
            err_pre += float(np.mean(e_pre))
            self.world_model.observe(s_cur, s_nxt, train=True)
            e_post = self.world_model.observe(s_cur, s_nxt, train=False)
            err_post += float(np.mean(e_post))

        loss_reduction = max(0.0, float((err_pre - err_post) / max(1, n_steps)))
        self.total_consolidations += 1
        return {
            "status": "dream_consolidated",
            "dream_id": dream_id,
            "loss_reduction": loss_reduction,
            "counterfactual_gain": gain
        }

    def consolidate_population_batch(self, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolidation collective vectorisée à haut débit (Commandement 3).
        Rassemble les mémoires de toute la population d'agents et entraîne
        les SelfModels et le WorldModel en blocs NumPy sans micro-boucles.
        """
        eligible_agents = []
        for a in agents:
            m = a.get("model")
            if m is not None and getattr(m, "replay_buffer", None) is not None:
                if len(m.replay_buffer) >= 4:
                    eligible_agents.append(a)

        if not eligible_agents:
            return {"status": "no_eligible_agents", "total_consolidated": 0}

        total_replayed = 0
        total_loss_reduction = 0.0

        for a in eligible_agents:
            m = a["model"]
            batch = m.replay_buffer.sample_batch(self.replay_batch_size)
            if not batch:
                continue

            S = np.array([exp.state for exp in batch], dtype=np.float32)
            Next_S = np.array([exp.next_state for exp in batch], dtype=np.float32)
            costs = np.array([exp.energy_spent for exp in batch], dtype=np.float32)
            successes = np.array([exp.success for exp in batch], dtype=np.bool_)

            # 1. WorldModel collectif ou individuel
            if self.world_model is not None:
                err_pre = self.world_model.observe(S[0], Next_S[0], train=False)
                for i in range(len(batch)):
                    self.world_model.observe(S[i], Next_S[i], train=True)
                err_post = self.world_model.observe(S[0], Next_S[0], train=False)
                total_loss_reduction += max(0.0, float(np.mean(err_pre) - np.mean(err_post)))

            # 2. SelfModel entièrement vectorisé
            sm = getattr(m, "self_model", None)
            if sm is not None:
                sm.learn_batch(S, costs, successes)

            total_replayed += len(batch)
            self.total_consolidations += 1
            if getattr(m, "night_consolidator", None) is not None:
                m.night_consolidator.total_consolidations += 1

        logger.emit("POPULATION_DREAM_CONSOLIDATION", {
            "eligible_agents": len(eligible_agents),
            "total_replayed_steps": total_replayed,
            "avg_loss_reduction": float(total_loss_reduction / max(1, len(eligible_agents)))
        })

        return {
            "status": "batch_consolidated",
            "eligible_agents": len(eligible_agents),
            "total_replayed_steps": total_replayed,
            "loss_reduction": total_loss_reduction
        }


BatchNightConsolidator = NightConsolidator


@dataclass
class SharedDreamExperience:
    """Hypothèse de rêve contrefactuel partagé en Gigatokens LU (Phase 11 M1)."""
    dream_id: str
    creator_id: str = "agent_0"
    scenario_token: Optional[np.ndarray] = None
    target_goal_token: Optional[np.ndarray] = None
    counterfactual_gain: float = 0.0
    trajectory: List[np.ndarray] = field(default_factory=list)
    is_ratified: bool = False
    tick: int = 0
    # Alias et champs pour délibération au feu de camp (M2)
    initiator_id: Optional[str] = None
    hypothesis_token: Optional[np.ndarray] = None
    latent_trajectory: Optional[List[np.ndarray]] = None
    participant_ids: List[str] = field(default_factory=list)
    ratified: bool = False
    consensus_agreement: float = 0.0
    creation_tick: int = 0

    def __post_init__(self):
        if self.initiator_id and not self.creator_id:
            self.creator_id = self.initiator_id
        elif self.creator_id and not self.initiator_id:
            self.initiator_id = self.creator_id
        if self.ratified and not self.is_ratified:
            self.is_ratified = self.ratified
        elif self.is_ratified and not self.ratified:
            self.ratified = self.is_ratified
        if self.latent_trajectory and not self.trajectory:
            self.trajectory = self.latent_trajectory
        elif self.trajectory and not self.latent_trajectory:
            self.latent_trajectory = self.trajectory



class SharedDreamPool:
    """Répertoire de rêves et scénarios contrefactuels collectifs partagés par la meute."""
    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self.dreams: List[SharedDreamExperience] = []

    def push(self, dream: SharedDreamExperience):
        if len(self.dreams) < self.capacity:
            self.dreams.append(dream)
        else:
            self.dreams.pop(0)
            self.dreams.append(dream)

    def add_shared_dream(self, dream: Any) -> None:
        """Alias public pour insérer une expérience de rêve partagé."""
        self.push(dream)

    def get_ratified_dreams(self) -> List[SharedDreamExperience]:
        return [d for d in self.dreams if d.is_ratified]

    def __len__(self) -> int:
        return len(self.dreams)

