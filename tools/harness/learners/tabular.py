"""
tools/harness/learners/tabular.py — Learner de VÉRITÉ-TERRAIN : une table de comptes sur la clé de l'observation
cumulée. Il calibre le runner et la lecture (cellule tabulaire, secondes, zéro torch) : `table` est nécessaire
par construction (sans elle, logits constants -> chance), `decoy` est un paramètre JAMAIS lu que L4 doit REFUSER.
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness_learner import Dose, Piece  # noqa: E402


class _TabularInstance:
    def __init__(self, K, lr, learning, without):
        self.K, self.lr, self.learning = int(K), float(lr), bool(learning)
        self.no_table = bool(without.get("table", False))
        self.table = {}                                  # clé (tuple) -> np.ndarray (K,) comptes
        self._dose = Dose(unit="count_updates")
        self.decoy = 0.0 if without.get("decoy") else 1.0   # jamais lu : la « pièce » vacue

    @staticmethod
    def _keys(obs_t, history):
        cols = [tuple(np.flatnonzero(row).tolist()) for row in np.asarray(obs_t)]
        return [h + (c,) for h, c in zip(history, cols)]

    def init_state(self):
        return None

    def act(self, obs_t, state):
        n = np.asarray(obs_t).shape[0]
        history = state if state is not None else [() for _ in range(n)]
        keys = self._keys(obs_t, history)
        logits = np.zeros((n, self.K), dtype=np.float32)
        if not self.no_table:
            for i, k in enumerate(keys):
                c = self.table.get(k)
                if c is not None:
                    logits[i] = c
        return np.array(logits, copy=True), keys

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        self._dose.episodes_seen += ep.n
        if self._dose.dparam_abs_sum is None:
            self._dose.dparam_abs_sum = 0.0
        if not self.learning:
            return self._dose
        history = [() for _ in range(ep.n)]
        keys = None
        for obs_t in ep.obs_seq:
            keys = self._keys(obs_t, history)
            history = keys
        d = 0.0
        for k, t in zip(keys, np.asarray(ep.target)):
            row = self.table.setdefault(k, np.zeros(self.K, dtype=np.float32))
            row[int(t)] += self.lr
            d += self.lr
        self._dose.updates += int(d > 0.0)
        self._dose.dparam_abs_sum += d
        return self._dose

    def ablate_state(self, state, name):
        if name != "state_reset":
            raise KeyError(f"ablation d'état inconnue : {name!r}")
        return None if state is None else [() for _ in state]

    def state_dict(self):
        return {"table": {k: v.copy() for k, v in self.table.items()}}

    def dose(self):
        return self._dose

    def close(self):
        pass


class TabularLearner:
    name, family, max_K = "tabular", "tabular", 64
    entry_task = "composition_same_tick_K6 (par construction : 36 cles)"
    supported_state_ablations = frozenset({"state_reset"})

    def __init__(self, honest=False):
        table = Piece("table", "tools/harness/learners/tabular.py::_TabularInstance.table", "aucun", "aucune", None,
                      "composition", {"table": True}, True, None, "verite-terrain : necessaire par construction")
        decoy = Piece("decoy", "tools/harness/learners/tabular.py::_TabularInstance.decoy", "aucun", "aucune", None,
                      "composition", {"decoy": True}, True, None, "parametre JAMAIS lu : L4 doit le refuser")
        self.pieces = (table,) if honest else (table, decoy)

    def sweep(self):
        return [{"lr": 1.0}, {"lr": 0.5}]

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        return _TabularInstance(K, hyper["lr"], learning=not reference, without=without or {})
