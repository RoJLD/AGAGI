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

P3.4 (2026-09-15) — le MÊME compteur couvre l'apprenant LEGACY (`MambaBatchModel.compute_policy_gradient`,
Actor-Critic TD(0) numpy, chemin actif pendant tout l'arc EVO, appelé à chaque tick quand
`use_torch_inworld=False`). Le monde RECRÉE ce modèle à chaque tick (`_get_batch_model`) : W vit dans
`agent.genome.W`, la transition différée dans `agent._td` — d'où un patch de CLASSE, et un ΔW mesuré sur
les génomes avant/après chaque appel. Compteurs : `legacy_calls` / `legacy_updates` (W a bougé) ;
`dW_abs_sum` cumule les deux familles. Variantes : `td_enabled=False` saute l'appel (raison `td_disabled`,
comme pour torch) ; `reward_scale` multiplie les récompenses ; `lr` pose `LR_ACTOR = lr` et garde le
RATIO publié du critic (`LR_CRITIC = lr × 0.05/0.04`) — `lr=0` est donc le même code à pas nul.
⚠️ Mesuré le 2026-09-15 en l'écrivant : à `lr=0`, W BOUGE QUAND MÊME (299/300 ticks hors monde, 283/2000
in-world) — pas le clip, le COMPILATEUR NTM (`NTMProgramCompiler.compile_and_apply`, appelé dans `forward`,
écrit des synapses dans `W_batch` depuis les slots mémoire ; `compute_policy_gradient` persiste ce `W_batch`
dans `genome.W`). `ABLATE_NTM=True` → 0/300. `legacy_updates` compte donc « W a bougé », gradient OU
auto-câblage : sur le chemin de l'arc EVO, W a DEUX auteurs, et seul le second survit à un pas nul. Le
plafond de l'incapable se MESURE (0,123 = chance à n=1), il ne se suppose pas « W figé ».

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
        self.legacy_calls = 0
        self.legacy_updates = 0
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
            "legacy_calls": int(self.legacy_calls),
            "legacy_updates": int(self.legacy_updates),
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


def _snapshot_genomes(model):
    """Legacy : W est PERSISTÉ dans `agent.genome.W` (le modèle est recréé à chaque tick)."""
    return [np.array(a.genome.W, dtype=np.float32, copy=True) for a in model.agents]


def _delta_genomes(model, w0):
    tot = 0.0
    for a, w in zip(model.agents, w0):
        W1 = np.asarray(a.genome.W, dtype=np.float32)
        if W1.shape == w.shape:
            tot += float(np.abs(W1 - w).sum())
        else:                                   # topologie changee entre deux ticks : tout compte
            tot += float(np.abs(W1).sum() + np.abs(w).sum())
    return tot


@contextlib.contextmanager
def count_learning_events(reward_scale=1.0, td_enabled=True, lr=None):
    """Compte les événements d'apprentissage de TOUTE population torch construite ou entraînée dans le
    bloc, et applique les variantes déclarées. Patch de CLASSE, restauré en `finally` (exception comprise)."""
    from src.agents.backend_torch import TorchPopulationModel as _TPM
    from src.agents.mamba_agent import MambaBatchModel as _MBM
    from src.graph_rag.async_logger import logger as _logger   # même objet que `world_1_stoneage.logger`

    ev = LearningEvents(reward_scale=reward_scale, td_enabled=td_enabled, lr=lr)
    orig_learn = _TPM.learn
    orig_episode = _TPM.learn_episode
    orig_init = _TPM.__init__
    orig_legacy = _MBM.compute_policy_gradient
    orig_lr_actor, orig_lr_critic = _MBM.LR_ACTOR, _MBM.LR_CRITIC
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

    def compute_policy_gradient(self, rewards_batch, actions_batch=None):
        ev.legacy_calls += 1
        if not ev.td_enabled:
            ev._skip("td_disabled")
            return None
        w0 = _snapshot_genomes(self)
        out = orig_legacy(self, _scaled(rewards_batch, ev.reward_scale), actions_batch)
        d = _delta_genomes(self, w0)
        if d > 0.0:
            ev.legacy_updates += 1
            ev.dW_abs_sum += d
        return out

    def emit(*args, **kwargs):
        name = args[0] if args else kwargs.get("event_type", kwargs.get("name"))
        if name == "TORCH_EPISODE_SKIP":
            payload = args[1] if len(args) > 1 else (kwargs.get("payload") or kwargs.get("data") or {})
            ev._skip((payload or {}).get("reason", "?"))
        return orig_emit(*args, **kwargs)

    _TPM.learn = learn
    _TPM.learn_episode = learn_episode
    _MBM.compute_policy_gradient = compute_policy_gradient
    if ev.lr is not None:
        _TPM.__init__ = __init__
        _MBM.LR_ACTOR = ev.lr
        _MBM.LR_CRITIC = ev.lr * (orig_lr_critic / orig_lr_actor) if orig_lr_actor else ev.lr
    _logger.emit = emit
    try:
        yield ev
    finally:
        _TPM.learn = orig_learn
        _TPM.learn_episode = orig_episode
        _TPM.__init__ = orig_init
        _MBM.compute_policy_gradient = orig_legacy
        _MBM.LR_ACTOR, _MBM.LR_CRITIC = orig_lr_actor, orig_lr_critic
        if had_emit:
            _logger.emit = orig_emit
        else:
            del _logger.emit
