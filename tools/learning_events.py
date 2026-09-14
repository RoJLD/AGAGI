"""P1.6 — la DOSE de crédit de l'apprenant in-world se COMPTE, et ses variantes se DÉCLARENT.

Pourquoi ce module existe (backlog, bloc « 🧭 2026-09-14 », fait neuf n° 1) : les nuls « le crédit
in-world n'apprend pas à froid » (S2-009 §crédit, S2-010, S2-011) ont été publiés sans que personne ne
compte combien de mises à jour l'apprenant avait reçues. Le chemin réel est un Actor-Critic TD(0) appelé
À CHAQUE TICK (`src/worlds/world_1_stoneage.py:1717` → `TorchPopulationModel.learn`) plus un crédit
épisodique tous les `torch_episode_k` ticks (`_maybe_learn_episode` → `learn_episode`), sur des agents
qui meurent à 7-9 ticks : la dose réelle se comptait en dizaines de mises à jour par agent. Un nul à
cette dose n'est pas un nul de capacité — c'est la classe E19 (réglage validé sur le cas facile) sous la
forme E2 (bras qui ne peut pas réussir), et rien ne le disait.

`count_learning_events` est un context manager posé sur la CLASSE du backend torch (le monde construit
et RECONSTRUIT la population à chaque mort, `Biosphere3D._get_batch_model` ; un patch d'instance ne
survivrait pas à la reconstruction) et RESTAURÉ en `finally`. Il publie :

    td_calls / td_updates          appels à `learn` / ceux qui ont réellement mis à jour W
    episode_calls / episode_updates   idem pour `learn_episode`
    skips                          raisons de saut du crédit épisodique émises par le monde
                                   (`TORCH_EPISODE_SKIP`) et `td_disabled` quand le TD est coupé
    dW_abs_sum                     Σ|ΔW| cumulée sur toutes les mises à jour (W seul : U/V/W_bl du
                                   bilinéaire ne sont pas comptés)

et trois VARIANTES d'apprenant, toutes BIT-IDENTIQUES par défaut (prouvé par
`tests/sandbox/test_learning_events.py`) :

    reward_scale   multiplie les récompenses vues par `learn` ET `learn_episode` (1.0 = passe l'objet
                   d'origine, sans conversion)
    td_enabled     False = `learn` rend None sans toucher W (le chemin épisodique reste actif)
    lr             None = défaut du backend ; sinon injecté à la construction de la population

⚠️ Pas de valeur DÉDUITE : tout ce que ce module publie est compté au moment où l'événement a lieu.
Un apprenant dont on n'a pas compté la dose n'a pas de contrôle positif.
"""
import contextlib

import numpy as np


class LearningEvents:
    """Compteurs d'un `with count_learning_events(...) as ev`. Publiable tel quel (`summary()`)."""

    def __init__(self, reward_scale=1.0, td_enabled=True, lr=None):
        self.reward_scale = float(reward_scale)
        self.td_enabled = bool(td_enabled)
        self.lr = None if lr is None else float(lr)
        self.td_calls = 0
        self.td_updates = 0
        self.episode_calls = 0
        self.episode_updates = 0
        self.skips = {}
        self.dW_abs_sum = 0.0

    def _skip(self, reason):
        self.skips[reason] = self.skips.get(reason, 0) + 1

    def summary(self):
        return {
            "td_calls": int(self.td_calls),
            "td_updates": int(self.td_updates),
            "episode_calls": int(self.episode_calls),
            "episode_updates": int(self.episode_updates),
            "skips": dict(self.skips),
            "dW_abs_sum": float(self.dW_abs_sum),
            "reward_scale": self.reward_scale,
            "td_enabled": self.td_enabled,
            "lr": self.lr,
        }


def _scaled(rewards, scale):
    """scale == 1.0 -> l'objet d'ORIGINE, sans conversion (bit-identité du chemin par défaut)."""
    if scale == 1.0:
        return rewards
    return np.asarray(rewards, dtype=np.float32) * np.float32(scale)


def _snapshot_W(model):
    W = getattr(model, "W", None)
    return None if W is None else W.detach().clone()


def _delta_W(model, w0):
    if w0 is None:
        return 0.0
    return float((model.W.detach() - w0).abs().sum().item())


@contextlib.contextmanager
def count_learning_events(reward_scale=1.0, td_enabled=True, lr=None):
    """Compte les événements d'apprentissage de TOUTE population torch construite ou entraînée dans le
    bloc, et applique les variantes déclarées. Patch de CLASSE, restauré en `finally` (exception comprise)."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    from src.graph_rag.async_logger import logger as _logger   # même objet que `world_1_stoneage.logger`

    ev = LearningEvents(reward_scale=reward_scale, td_enabled=td_enabled, lr=lr)
    orig_learn = _TPM.learn
    orig_episode = _TPM.learn_episode
    orig_init = _TPM.__init__
    had_emit = "emit" in _logger.__dict__
    orig_emit = _logger.emit

    def learn(self, rewards_batch, actions_batch=None):
        ev.td_calls += 1
        if not ev.td_enabled:
            ev._skip("td_disabled")
            return None
        w0 = _snapshot_W(self)
        out = orig_learn(self, _scaled(rewards_batch, ev.reward_scale), actions_batch)
        if out is not None:
            ev.td_updates += 1
            ev.dW_abs_sum += _delta_W(self, w0)
        return out

    def learn_episode(self, obs_seq, actions_seq, rewards, gamma=1.0, gate_last_only=True):
        ev.episode_calls += 1
        w0 = _snapshot_W(self)
        out = orig_episode(self, obs_seq, actions_seq, _scaled(rewards, ev.reward_scale),
                           gamma=gamma, gate_last_only=gate_last_only)
        if out is not None:
            ev.episode_updates += 1
            ev.dW_abs_sum += _delta_W(self, w0)
        return out

    def __init__(self, agents, world_model=None, lr=0.04, device="cpu"):
        return orig_init(self, agents, world_model=world_model,
                         lr=(ev.lr if ev.lr is not None else lr), device=device)

    def emit(*args, **kwargs):
        name = args[0] if args else kwargs.get("event_type", kwargs.get("name"))
        if name == "TORCH_EPISODE_SKIP":
            payload = args[1] if len(args) > 1 else (kwargs.get("payload") or kwargs.get("data") or {})
            ev._skip((payload or {}).get("reason", "?"))
        return orig_emit(*args, **kwargs)

    _TPM.learn = learn
    _TPM.learn_episode = learn_episode
    if ev.lr is not None:
        _TPM.__init__ = __init__
    _logger.emit = emit
    try:
        yield ev
    finally:
        _TPM.learn = orig_learn
        _TPM.learn_episode = orig_episode
        _TPM.__init__ = orig_init
        if had_emit:
            _logger.emit = orig_emit
        else:
            del _logger.emit
