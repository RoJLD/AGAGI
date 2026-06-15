"""
src/agents/baseline_models.py — Baselines "bêtes" du benchmark S2, drop-in de MambaBatchModel.

Même interface que MambaBatchModel (forward -> (logits, compute_spent) ; compute_policy_gradient
no-op), injectés via env.batch_model_cls (seam, world_1:949). Écrivent surprise=0 sur les agents
(sinon step() relit des valeurs gelées -> coût cérébral/curiosité = artefacts, blocker panel).
RandomGenome n'est PAS ici : c'est un MambaAgent à poids aléatoires qui passe par MambaBatchModel.
Spec §5/§11.
"""
import numpy as np


class BaselineBatchModel:
    """Base : interface minimale du batch model. Les sous-classes fournissent _logits(batch_obs)."""

    def __init__(self, agents, world_model=None):
        self.agents = agents
        self.B = len(agents)
        self.O = max((a.genome.num_outputs for a in agents), default=0)
        self.world_model = world_model      # ignoré (pas de surprise) — accepté pour l'interface

    def _logits(self, batch_obs):
        raise NotImplementedError

    def forward(self, batch_obs, env_surprise_batch=None):
        if self.B == 0:
            return np.array([]), np.array([])
        logits = self._logits(batch_obs)
        # Contrôle propre : pas de World Model -> surprise = 0 (sinon valeurs gelées relues par step()).
        for a in self.agents:
            a.surprise = 0.0
            a.surprise_momentum = 0.0
        compute_spent = np.zeros(self.B, dtype=np.float32)      # aucun rêve
        return logits, compute_spent

    def compute_policy_gradient(self, rewards_batch, actions_batch=None):
        return                                                  # no-op : poids figés


class RandomActionBatchModel(BaselineBatchModel):
    """Zéro politique : logits aléatoires à chaque tick, tirés du flux global np.random (déjà seedé
    aux frontières par le Harness -> appariement préservé, JAMAIS un RNG privé)."""

    def _logits(self, batch_obs):
        return np.random.randn(self.B, self.O).astype(np.float32)


# Indices d'observation (world_1.get_batch_observations, l.505) et d'action (world_1 step, l.1246-1249).
OBS_DIR = slice(0, 4)        # [dn, ds, de, dw] -> proie au Nord/Sud/Est/Ouest
MOVE_SLOT = [0, 1, 2, 3]     # action 0=N(ny-1) 1=S(ny+1) 2=E(nx+1) 3=W(nx-1)
GRAB_LOGIT = 24              # do_grab = logits[24]


class ReflexBatchModel(BaselineBatchModel):
    """Poursuite : va vers la proie la plus proche (direction lue dans l'obs), tente de grab chaque
    tick. Heuristique non-cognitive = borne basse "réflexe". prudent=True -> variante (Task 10)."""

    def __init__(self, agents, world_model=None, prudent=False):
        super().__init__(agents, world_model)
        self.prudent = prudent

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        dirs = batch_obs[:, OBS_DIR]                     # (B, 4) = dn,ds,de,dw
        best = np.argmax(dirs, axis=1)                   # 0..3 -> N,S,E,W
        for i in range(self.B):
            logits[i, MOVE_SLOT[best[i]]] = 1.0          # argmax(logits[:8]) = direction vers la proie
            logits[i, GRAB_LOGIT] = 1.0                  # toujours tenter de ramasser
        return logits
