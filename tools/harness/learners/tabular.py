"""
tools/harness/learners/tabular.py — Learner de VÉRITÉ-TERRAIN : une table de comptes sur la clé de l'observation
cumulée. Il calibre le runner et la lecture (cellule tabulaire, secondes, zéro torch) : `table` est nécessaire
par construction (sans elle, logits constants -> chance), `decoy` est un paramètre JAMAIS lu que L4 doit REFUSER.

Fix round 1 (revue, 2026-09-16) : la clé hachait TOUTE la ligne d'observation (`np.flatnonzero` plein-ligne).
Sous `inject_distractor_slot` (contrôle de spécificité must_bite=False, oracle reste à 1.0), le bit du slot
distracteur — jamais actif à l'entraînement — changeait la clé vers une entrée jamais peuplée de la table :
logits nuls, chute à la chance. Un artefact de HACHAGE, pas une lecture du canal decoy — le runner aurait lu
X_DECOY comme INCONCLUSIVE_SPECIFICITY sur le learner de vérité-terrain lui-même. Fix : `self.seen_cols`
mémorise les colonnes VUES à l'entraînement ; `act` ne hache que celles-là (une colonne inédite est ignorée),
`learn` continue de hacher la ligne ENTIÈRE (elle vient de rendre ces colonnes « vues », juste avant).
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
        self.seen_cols = set()                            # colonnes actives VUES en apprentissage
        self._dose = Dose(unit="count_updates")
        self.decoy = 0.0 if without.get("decoy") else 1.0   # jamais lu : la « pièce » vacue

    @staticmethod
    def _cols(obs_t):
        return [np.flatnonzero(row).tolist() for row in np.asarray(obs_t)]

    @staticmethod
    def _keys(obs_t, history):
        """Clé BRUTE (toutes les colonnes actives), utilisée par `learn` pour indexer la table : au moment
        où elle est appelée, `seen_cols` vient déjà d'être étendu à ces mêmes colonnes (cf. `learn`), donc
        filtrer ici ne changerait rien — la version brute est gardée pour ne pas dupliquer le filtrage."""
        cols = [tuple(c) for c in _TabularInstance._cols(obs_t)]
        return [h + (c,) for h, c in zip(history, cols)]

    def _keys_seen(self, obs_t, history):
        """Clé FILTRÉE (colonnes actives ∩ `seen_cols`), utilisée par `act`. Une colonne jamais active à
        l'entraînement (ex. le slot distracteur sous `inject_distractor_slot`) est IGNORÉE plutôt que de
        faire diverger la clé vers une entrée jamais peuplée -- c'est le fix round 1."""
        cols = [tuple(c for c in row_cols if c in self.seen_cols) for row_cols in self._cols(obs_t)]
        return [h + (c,) for h, c in zip(history, cols)]

    def init_state(self):
        return None

    def act(self, obs_t, state):
        n = np.asarray(obs_t).shape[0]
        history = state if state is not None else [() for _ in range(n)]
        keys = self._keys_seen(obs_t, history)
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
        # `no_table` (without={"table": True}) ne désactive QUE la lecture dans `act` : `learn` continue
        # de peupler `self.table`/`self.seen_cols` sous ce régime, À DESSEIN -- la DOSE (calls/updates/
        # dparam_abs_sum) reste appariée entre l'intact et la variante « sans » (Piece.dose_matched).
        # `seen_cols` grandit AVANT la construction des clés de CET appel : les colonnes actives de
        # l'épisode sont donc déjà « vues » quand `_keys` les hache ici (fix round 1, cf. module docstring).
        for obs_t in ep.obs_seq:
            for row in np.asarray(obs_t):
                self.seen_cols.update(np.flatnonzero(row).tolist())
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
    name, family = "tabular", "tabular"
    max_K = 64  # borne (L0) sur K : ne contraint pas la table (dict, fan-out illimité en clés) -- juste
                # la largeur (K,) de chaque ligne de comptes ; pas structurellement nécessaire, garde-fou.
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
