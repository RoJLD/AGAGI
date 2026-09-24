# tests/sandbox/test_harness_learner.py
"""Contrat Learner (spec §2.1) : L0-L7. Le learner jouet est une table de comptes en numpy pur ; chaque cas
casse UNE clause et vérifie que la garde la nomme."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_learner import (  # noqa: E402
    Dose,
    Piece,
    _states_differ,
    assert_learner_contract,
    run_episode,
)
from src.seed_ai.harness_task import Ablation, DemandDeclaration, Episode  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402
from tests.sandbox.test_harness_task import ToyParity, ToyParityT2  # noqa: E402


class _CounterInstance:
    def __init__(self, K, obs_dim, lr, learning, without, aliased=False, dead=False):
        self.K, self.lr, self.learning, self.without = K, float(lr), learning, dict(without)
        self.table = np.zeros((obs_dim, K), dtype=np.float64)
        self.bias = np.zeros(K, dtype=np.float64) + (0.0 if without.get("bias") else 0.01)
        self._dose = Dose(unit="count_updates")
        self.aliased, self.dead = aliased, dead
        self._state_buf = np.zeros((1, K), dtype=np.float32)

    def init_state(self):
        return None

    def act(self, obs_t, state):
        logits = obs_t.astype(np.float64) @ self.table + self.bias
        if self.without.get("table"):
            logits = np.zeros_like(logits) + self.bias
        out = logits.astype(np.float32)
        if self.aliased:
            self._state_buf = out
            return out, self._state_buf      # la sortie EST l'état : L5 doit lever
        return np.array(out, copy=True), state

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        self._dose.episodes_seen += ep.n
        if not self.learning or self.dead:
            self._dose.dparam_abs_sum = (self._dose.dparam_abs_sum or 0.0)
            return self._dose
        before = self.table.copy()
        rows = ep.obs_seq[-1] > 0
        for i in range(ep.n):
            self.table[rows[i], ep.target[i]] += self.lr
        d = float(np.abs(self.table - before).sum())
        self._dose.updates += int(d > 0)
        self._dose.dparam_abs_sum = (self._dose.dparam_abs_sum or 0.0) + d
        return self._dose

    def ablate_state(self, state, name):
        return state

    def state_dict(self):
        return {"table": self.table.copy()}

    def dose(self):
        return self._dose

    def close(self):
        pass


class CounterLearner:
    name, family, max_K = "counter", "toy", 64
    entry_task = "toy_parity"

    def __init__(self, vacuous_piece=False, aliased=False, dead=False, reference_learns=False, one_lr=False,
                 supports_state_reset=False):
        self.pieces = (Piece("table", "test", "aucun", "aucune", None, "parity", {"table": True}, True, None, "absent"),
                       Piece("bias", "test", "aucun", "aucune", None, "parity", {"bias": True}, True, None, "absent"))
        if vacuous_piece:
            self.pieces += (Piece("decoy", "test", "aucun", "aucune", None, "parity", {"decoy": True}, True, None, "absent"),)
        self.aliased, self.dead, self.reference_learns, self.one_lr = aliased, dead, reference_learns, one_lr
        # (L8) B3 : déclarer le support d'une ablation d'état SANS que `ablate_state` la fasse mordre --
        # `_CounterInstance.ablate_state` (ci-dessus) est un NO-OP littéral (`return state`), exactement
        # le contre-exemple gelé de STATE_ABLATION_BITES ci-dessous.
        self.supported_state_ablations = frozenset({"state_reset"}) if supports_state_reset else frozenset()

    def sweep(self):
        return [{"lr": 1.0}] if self.one_lr else [{"lr": 1.0}, {"lr": 0.5}]

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        learning = (not reference) or self.reference_learns
        return _CounterInstance(K, obs_dim, hyper["lr"], learning, without or {}, aliased=self.aliased, dead=self.dead)


def test_counter_learner_passes_L0_to_L7():
    out = assert_learner_contract(CounterLearner(), ToyParity(), seed=0)
    assert out["n_pieces"] == 2 and out["reference_dparam"] == 0.0


def test_L0_refuses_K_above_max_K():
    task = ToyParity()
    task.K = 65
    with pytest.raises(PreflightError, match="max_K"):
        assert_learner_contract(CounterLearner(), task)


def test_L2_refuses_a_reference_that_learns():
    with pytest.raises(PreflightError, match="REFERENCE_LEARNS"):
        assert_learner_contract(CounterLearner(reference_learns=True), ToyParity())


def test_L3_refuses_a_dead_learner():
    with pytest.raises(PreflightError, match="DEAD_LEARNER"):
        assert_learner_contract(CounterLearner(dead=True), ToyParity())


def test_L4_refuses_a_vacuous_piece():
    with pytest.raises(PreflightError, match="VACUOUS_PIECE.*decoy"):
        assert_learner_contract(CounterLearner(vacuous_piece=True), ToyParity())


def test_L5_refuses_logits_that_alias_the_state():
    # NB : le message réel de tools.experiment_preflight.assert_no_aliasing dit "ALIASÉE" (FR), jamais
    # littéralement "shares_memory" ni "aliasing" (EN) -- le brief d'origine visait le mauvais mot ;
    # "(?i)alias" matche la forme réelle sans figer un mot précis.
    with pytest.raises(PreflightError, match="(?i)alias"):
        assert_learner_contract(CounterLearner(aliased=True), ToyParity())


def test_L7_refuses_a_single_sweep_point():
    with pytest.raises(PreflightError, match="sweep"):
        assert_learner_contract(CounterLearner(one_lr=True), ToyParity())


def test_L8_refuses_a_state_ablation_whose_ablate_state_is_a_no_op():
    # B3 (revue finale de branche, 2026-09-24) : `_CounterInstance.ablate_state` est un NO-OP littéral
    # (`return state`) -- un learner qui DÉCLARE supporter "state_reset" (L0 passe) sans que
    # `ablate_state` change quoi que ce soit doit être refusé EN TÊTE, avant qu'aucune cellule ne tourne.
    with pytest.raises(PreflightError, match="STATE_ABLATION_BITES"):
        assert_learner_contract(CounterLearner(supports_state_reset=True), ToyParityT2())


def test_L8_states_differ_calibration_on_the_POPULATED_branch():
    # Mineur relevé par la re-revue de branche (2026-09-24) : le cas gelé ci-dessus a un `init_state()`
    # qui rend None, donc `state_a` est None et (L8) ne compare que None contre None -- la branche
    # `np.array_equal` de `_states_differ` (harness_learner.py:115-116), celle qui juge un état RÉEL,
    # n'avait AUCUN cas. Le code y était déjà correct (vérifié par sonde indépendante) ; c'était la
    # DÉCLARATION de couverture qui était optimiste. Les DEUX issues, sur la branche peuplée :
    peuple = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    assert _states_differ(peuple, peuple.copy()) is False        # même valeur, objet différent
    change = peuple.copy()
    change[1, 1] = 0.0                                           # UNE cellule
    assert _states_differ(peuple, change) is True
    # le cas DÉGÉNÉRÉ que la docstring de (L8) nomme, et la raison de comparer `state_a` et non
    # `init_state()` : pour un substrat dont l'init rend des zéros, `zeros_like` ne mord jamais.
    zeros = np.zeros((2, 2), dtype=np.float64)
    assert _states_differ(zeros, np.zeros_like(zeros)) is False
    # None contre un tableau peuplé DIFFÈRE (un `ablate_state` qui rend None mord bien)
    assert _states_differ(peuple, None) is True
    assert _states_differ(None, peuple) is True


class _PopulatedStateInstance:
    """Instance jouet à état porté réellement PEUPLÉ (accumulation de obs_t, donc non nul dès le pas 0),
    dont `ablate_state` est un NO-OP littéral. Sert le cas (L8) sur la branche `np.array_equal` :
    contrairement à `_CounterInstance`, `state_a` n'est PAS None quand (L8) le compare."""

    def __init__(self, K, obs_dim):
        self.K, self.obs_dim = K, obs_dim
        self._dose = Dose(unit="count_updates")
        self.ablate_seen = []        # ce que (L8) a RÉELLEMENT comparé -- vérifié par le test

    def init_state(self):
        return np.zeros(self.obs_dim, dtype=np.float64)

    def act(self, obs_t, state):
        carried = self.init_state() if state is None else state
        new_state = carried + obs_t.astype(np.float64).sum(axis=0)   # PEUPLÉ : obs_t n'est pas nul
        logits = np.zeros((obs_t.shape[0], self.K), dtype=np.float32)
        return logits, new_state

    def ablate_state(self, state, name):
        self.ablate_seen.append(None if state is None else np.array(state, copy=True))
        return state                                              # NO-OP : (L8) doit refuser

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        return self._dose

    def state_dict(self):
        return {}

    def dose(self):
        return self._dose

    def close(self):
        pass


class _PopulatedStateLearner(CounterLearner):
    """`CounterLearner` dont `build` rend une instance à état PEUPLÉ (cf. `_PopulatedStateInstance`)."""

    def __init__(self):
        super().__init__(supports_state_reset=True)
        self.built = []

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        inst = _PopulatedStateInstance(K, obs_dim)
        self.built.append(inst)
        return inst


def test_L8_refuses_a_no_op_on_a_POPULATED_state():
    # Même refus que le cas gelé, mais par la branche `np.array_equal` et non par None-contre-None :
    # l'état comparé porte la somme des observations du dernier pas, `ablate_state` le rend tel quel.
    learner = _PopulatedStateLearner()
    with pytest.raises(PreflightError, match="STATE_ABLATION_BITES"):
        assert_learner_contract(learner, ToyParityT2())
    # Et on PROUVE que le refus vient bien de la branche peuplée : sans cette assertion, un état resté
    # None donnerait le MÊME refus (None contre None ne diffère pas non plus) et le cas passerait pour
    # la mauvaise raison -- c'est exactement le défaut que la re-revue a relevé sur le cas gelé.
    vus = [s for inst in learner.built for s in inst.ablate_seen]
    assert vus, "(L8) n'a appelé ablate_state sur aucune instance"
    assert all(s is not None and hasattr(s, "shape") for s in vus)
    assert any(np.abs(s).sum() > 0.0 for s in vus), "l'état comparé par (L8) était nul, donc dégénéré"


def test_run_episode_scores_with_the_task_verifier():
    task = ToyParity()
    inst = CounterLearner().build(0, 8, task.obs_dim, task.K, {"lr": 1.0})
    ep = task.episodes(np.random.RandomState(0), 8)
    actions, hits = run_episode(inst, ep, task)
    assert actions.shape == (8,) and hits.shape == (8,) and set(np.unique(hits)) <= {0.0, 1.0}


class _StatefulInstance:
    """Learner jouet à ÉTAT RÉCURRENT (T=2) : `act` ADDITIONNE obs_t à l'état porté puis rend
    `état @ W` comme logits ; `ablate_state("state_reset")` le REMET À None. Sert à distinguer, dans
    `run_episode`, le pas où l'ablation d'ÉTAT est appliquée — revue fix-round-1 (2026-09-16) :
    `run_episode` compare S1 ; le nouveau case le compare (finding : la branche
    `if ablate is not None and t == last: ...` de run_episode n'avait AUCUN cas)."""
    def __init__(self, K, obs_dim):
        self.K, self.obs_dim = K, obs_dim
        # colonne 0 lit UNIQUEMENT l'indice 0 (poids fort), colonne 1 lit UNIQUEMENT l'indice 3
        # (poids plus faible) : la classe gagnante DEPEND de QUEL indice est porté par l'état au
        # moment du dernier pas -- pas seulement de sa norme. Dimensionné sur obs_dim (>= 4) : les
        # colonnes au-delà de 3 (ex. la colonne 4 "inutilisée" de ToyParityT2) restent à poids nul.
        self.W = np.zeros((obs_dim, 2), dtype=np.float64)
        self.W[0, 0] = 10.0
        self.W[3, 1] = 5.0
        self.act_calls = 0
        self.ablate_log = []   # [(act_calls avant cet appel, snapshot de l'état recu)]

    def init_state(self):
        return None

    def act(self, obs_t, state):
        carried = np.zeros_like(obs_t, dtype=np.float64) if state is None else state
        new_state = carried + obs_t.astype(np.float64)
        self.act_calls += 1
        logits = new_state @ self.W
        return np.array(logits, dtype=np.float32, copy=True), new_state

    def ablate_state(self, state, name):
        self.ablate_log.append((self.act_calls, None if state is None else np.array(state, copy=True)))
        return None if name == "state_reset" else state

    def learn(self, ep, actions, hits):
        return Dose()

    def state_dict(self):
        return {}

    def dose(self):
        return Dose()

    def close(self):
        pass


def test_run_episode_applies_ablate_only_before_the_last_step():
    # Episode T=2 CONSTRUIT A LA MAIN (deterministe, pas de RNG) : obs0 porte UNIQUEMENT l'indice 0,
    # obs1 UNIQUEMENT l'indice 3. `_StatefulInstance` accumule l'etat au fil des pas. Intact : l'etat
    # au pas de reponse porte obs0+obs1 -> logits [10, 5] -> classe 0 pour tout le lot. Ablate
    # "state_reset" AVANT le dernier pas remet l'etat a None -> le pas de reponse ne voit QUE obs1 ->
    # logits [0, 5] -> classe 1 pour tout le lot : les deux bras DIVERGENT completement, sans aleatoire.
    task = ToyParityT2()
    n = 4
    obs0 = np.zeros((n, task.obs_dim), dtype=np.float32)
    obs0[:, 0] = 1.0
    obs1 = np.zeros((n, task.obs_dim), dtype=np.float32)
    obs1[:, 3] = 1.0
    mask0 = np.zeros(n, dtype=np.float32)
    mask1 = np.ones(n, dtype=np.float32)
    target = np.zeros(n, dtype=np.int64)
    ep = Episode((obs0, obs1), target, (mask0, mask1), {})

    inst_intact = _StatefulInstance(task.K, task.obs_dim)
    actions_intact, _ = run_episode(inst_intact, ep, task)
    assert np.array_equal(actions_intact, np.zeros(n, dtype=np.int64))
    assert inst_intact.ablate_log == []                       # jamais appelé sans `ablate=`

    inst_ablated = _StatefulInstance(task.K, task.obs_dim)
    actions_ablated, _ = run_episode(inst_ablated, ep, task, ablate="state_reset")
    assert np.array_equal(actions_ablated, np.ones(n, dtype=np.int64))
    assert not np.array_equal(actions_intact, actions_ablated)

    # Appliqué UNE SEULE fois, et juste AVANT le DERNIER pas de réponse : au moment de l'appel,
    # exactement 1 `act()` a déjà eu lieu (le pas 0), et l'état reçu ne porte QUE obs0 (pas encore obs1).
    assert len(inst_ablated.ablate_log) == 1
    act_calls_before, state_seen = inst_ablated.ablate_log[0]
    assert act_calls_before == 1
    assert np.array_equal(state_seen, obs0.astype(np.float64))


def test_L4_pieces_kwarg_scopes_which_pieces_must_be_non_vacuous():
    # Décision 2 (controller) : `pieces=["table"]` ne juge QUE la pièce "table" (non vacuous) et passe,
    # alors que le défaut (toutes les pièces, dont le decoy jamais lu) refuse VACUOUS_PIECE sur "decoy".
    learner = CounterLearner(vacuous_piece=True)
    out = assert_learner_contract(learner, ToyParity(), pieces=["table"])
    assert out["n_pieces"] == 3
    with pytest.raises(PreflightError, match="VACUOUS_PIECE.*decoy"):
        assert_learner_contract(learner, ToyParity())
