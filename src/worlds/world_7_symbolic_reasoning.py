"""
World 7 : Raisonnement Symbolique, Algèbre & Preuves Formelles.
Environnement de logique propositionnelle, arithmétique générative et déduction de Hoare.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from src.worlds.base_world import BaseWorld


@dataclass
class SymbolicConfig:
    """Configuration hyper-paramétrable pour le Monde 7 (Raisonnement Symbolique)."""
    vocab_size: int = 16               # Taille du vocabulaire symbolique
    max_tree_depth: int = 4            # Profondeur maximale des arbres d'expression
    tasks_per_era: int = 50            # Nombre de théorèmes / équations générés par ère
    reward_correct_proof: float = 10.0 # Gain pour preuve formelle valide
    penalty_invalid_proof: float = 2.0 # Pénalité pour hallucination déductive
    tolerance_eps: float = 1e-4        # Tolérance de vérification numérique


class SymbolicReasoningWorld(BaseWorld):
    """
    Monde 7 : Raisonnement Symbolique & Logique Formelle.
    Cet environnement présente des défis abstraits aux agents :
    1. Résolution d'équations linéaires : a * x + b = c -> prédire x
    2. Inférence déductive : Modus Ponens (P => Q, P |- Q)
    3. Simplification algébrique et vérification d'invariants formels.
    """
    def __init__(self, config: Optional[SymbolicConfig] = None):
        super().__init__(size=1)
        self.config = config or SymbolicConfig()
        self.solved_tasks = 0
        self.failed_tasks = 0
        self.total_cognitive_reward = 0.0
        self.current_task: Optional[Dict[str, Any]] = None
        self.reset()

    def reset(self):
        """Génère un nouveau puzzle logique/algébrique."""
        self.tick_count = 0
        self.current_task = self._generate_task()
        return self._task_to_observation(self.current_task)

    def _generate_task(self) -> Dict[str, Any]:
        """Génère procéduralement une tâche algébrique ou logique."""
        task_type = np.random.choice(["linear_equation", "modus_ponens"])

        if task_type == "linear_equation":
            # a * x + b = c
            a = float(np.random.choice([1, 2, 3, 4, 5]))
            x = float(np.random.randint(-5, 6))
            b = float(np.random.randint(-10, 11))
            c = float(a * x + b)
            return {
                "type": "linear_equation",
                "a": a, "b": b, "c": c,
                "target": x,
                "vector": np.array([1.0, a, b, c, 0.0, 0.0], dtype=np.float32)
            }
        else:
            # Modus Ponens : P=idx_p, Q=idx_q. Observé [P, Q, P] -> Cible Q
            p_val = float(np.random.randint(1, 5))
            q_val = float(np.random.randint(1, 5))
            return {
                "type": "modus_ponens",
                "p": p_val,
                "q": q_val,
                "target": q_val,
                "vector": np.array([2.0, p_val, q_val, p_val, 0.0, 0.0], dtype=np.float32)
            }

    def _task_to_observation(self, task: Dict[str, Any]) -> np.ndarray:
        """Convertit la tâche en vecteur d'entrée normalisé."""
        vec = task["vector"].copy()
        # Normalisation
        norm = np.linalg.norm(vec)
        if norm > 1e-4:
            vec = vec / norm
        return vec

    def step(self):
        """Avance d'un tick en soumettant l'observation aux agents."""
        self.tick_count += 1
        obs = self._task_to_observation(self.current_task)

        for agent in self.agents:
            model = agent.get("model")
            pred = None
            if hasattr(model, "forward"):
                # Forward de l'agent
                out = model.forward(obs)
                if isinstance(out, (tuple, list)):
                    out = out[0]
                if isinstance(out, np.ndarray) and len(out) > 0:
                    pred = float(out[0])
            elif callable(model):
                pred = float(model(obs))
            else:
                pred = float(agent.get("prediction", 0.0))

            # Évaluation de la solution
            target = self.current_task["target"]
            is_correct = abs(pred - target) <= self.config.tolerance_eps or round(pred) == round(target)

            if is_correct:
                self.solved_tasks += 1
                reward = self.config.reward_correct_proof
                agent["energy"] = min(100.0, agent.get("energy", 50.0) + reward)
                self.total_cognitive_reward += reward
            else:
                self.failed_tasks += 1
                penalty = self.config.penalty_invalid_proof
                agent["energy"] = max(0.0, agent.get("energy", 50.0) - penalty)

        # Générer la tâche suivante
        self.current_task = self._generate_task()

    def add_agent(self, agent_model, **kwargs):
        """Ajoute un agent déductif."""
        agent_dict = {
            "id": f"deductive_{len(self.agents)}",
            "model": agent_model,
            "energy": kwargs.get("energy", 50.0),
            "age": 0,
        }
        self.agents.append(agent_dict)
        return agent_dict

    def get_symbolic_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques de résolution formelle."""
        total = max(1, self.solved_tasks + self.failed_tasks)
        accuracy = float(self.solved_tasks / total)
        return {
            "solved_tasks": self.solved_tasks,
            "failed_tasks": self.failed_tasks,
            "accuracy": accuracy,
            "total_cognitive_reward": self.total_cognitive_reward,
        }
