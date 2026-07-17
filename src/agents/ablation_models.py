"""src/agents/ablation_models.py — ablation within-subject pour le benchmark S2.

ObsAblatedMambaBatchModel : drop-in de MambaBatchModel (injecté via env.batch_model_cls) qui déroule
le VRAI champion (même génome, même moteur) mais sur une obs DÉCORRÉLÉE de l'état propre (row-shuffle
par tick). C'est le témoin CAUSAL within-subject de « le monde exige la perception » (S2-001) : si la
survie du champion s'effondre à obs ablée, la perception est causalement porteuse. Additif, ne touche
pas mamba_agent/backend_torch/world_1.
"""
import numpy as np

from src.agents.mamba_agent import MambaBatchModel


class ObsAblatedMambaBatchModel:
    """Enveloppe un MambaBatchModel réel ; permute les lignes de batch_obs (agent i reçoit l'obs RÉELLE
    d'un autre) AVANT le forward -> décorrèle perception↔état propre en préservant EXACTEMENT la
    distribution marginale. Shuffle tiré du flux np.random SEEDÉ global (comme les baselines : appariement
    et déterminisme préservés, jamais un RNG privé). NE zéro-fixe PAS surprise : tout le pipeline perceptif
    réel du champion tourne, simplement nourri d'obs décorrélée."""

    def __init__(self, agents, world_model=None):
        self._inner = MambaBatchModel(agents, world_model=world_model)
        self.agents = agents

    def forward(self, batch_obs, env_surprise_batch=None):
        B = batch_obs.shape[0]
        if B == 0:
            return self._inner.forward(batch_obs, env_surprise_batch)
        perm = np.random.permutation(B)                  # décorrèle obs↔agent (flux seedé global)
        # NB : seul batch_obs est permuté. env_surprise_batch (aligné agent i) est transmis tel quel ; inoffensif
        # tant que MambaBatchModel.forward l'ignore. S'il devient actif un jour, le permuter avec la MÊME perm.
        return self._inner.forward(batch_obs[perm], env_surprise_batch)

    def compute_policy_gradient(self, *args, **kwargs):
        return self._inner.compute_policy_gradient(*args, **kwargs)   # champion figé -> no-op délégué
