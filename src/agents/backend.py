"""Abstraction de backend neuronal — ADR-003.

Frontière = POPULATION batchée (pas l'agent unique). Couture canonique :
`make_population(agents) -> PopulationModel` exposant `forward` / `learn` / `extract`.
La topologie évolutive reste en espace-génome (numpy) ; un backend ne voit qu'une
population déjà matérialisée. Le write-back Baldwin (poids appris -> génome) est
réalisé EN PLACE par le backend dans les agents — `extract` ne fait que les exposer.

Backends :
- "legacy" : wrapper STRICTEMENT non-régressif du `MambaBatchModel` numpy existant.
- "torch"  : à venir (Axe 1 du plan de migration, REF-LTC-2021). Lève NotImplementedError.

Réf : docs/ADR/003_backend_abstraction.md ; docs/superpowers/specs/2026-06-29-SOTA-Migration-design.md.
"""
from abc import ABC, abstractmethod


class PopulationModel(ABC):
    """Contrat d'un backend de population. Une instance enveloppe une liste d'agents
    (mémoire durable) + l'état batché transitoire du backend."""

    @abstractmethod
    def forward(self, batch_obs, env_surprise_batch=None):
        """(B, I) -> (preds, compute_spent). Synchronise l'état dans les agents."""

    @abstractmethod
    def learn(self, rewards_batch, actions_batch=None):
        """Apprentissage intra-vie ; réécrit les poids appris dans les génomes (in place)."""

    @abstractmethod
    def extract(self):
        """Retourne les agents (génomes déjà mis à jour en place par forward/learn)."""


class LegacyPopulationModel(PopulationModel):
    """Backend numpy de référence : délègue au `MambaBatchModel` existant, sans rien
    changer au comportement (non-régression mesurée contre l'appel direct)."""

    backend = "legacy"

    def __init__(self, agents, world_model=None):
        from src.agents.mamba_agent import MambaBatchModel
        self.agents = agents
        self._model = MambaBatchModel(agents, world_model=world_model)
        self.B = self._model.B

    def forward(self, batch_obs, env_surprise_batch=None):
        return self._model.forward(batch_obs, env_surprise_batch)

    def learn(self, rewards_batch, actions_batch=None):
        return self._model.compute_policy_gradient(rewards_batch, actions_batch)

    def extract(self):
        return self.agents


def make_population(agents, backend="legacy", world_model=None):
    """Matérialise une population sous le backend choisi. Défaut `legacy` (non-régressif).
    `torch` chargé paresseusement (dépendance optionnelle, requirements-torch.txt).
    `backend` inconnu -> NotImplementedError (le seam est prêt : ADR-003)."""
    if backend == "legacy":
        return LegacyPopulationModel(agents, world_model=world_model)
    if backend == "torch":
        from src.agents.backend_torch import TorchPopulationModel
        return TorchPopulationModel(agents, world_model=world_model)
    raise NotImplementedError(
        f"backend '{backend}' non disponible (ADR-003) ; disponibles: ['legacy', 'torch']"
    )
