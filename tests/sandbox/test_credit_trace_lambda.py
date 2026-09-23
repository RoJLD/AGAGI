"""P4.11 (ADR-005 item 1) — trace d'éligibilité TD(λ) de `TorchPopulationModel._td_update`
(`backend_torch.py::_td_update_trace`), confrontée à des réponses CONNUES, 0 simulation de monde.

Ordre voulu par la revue (c9, cond. iv) : le CONTRÔLE POSITIF d'abord — ΔW EXACT prédit par la formule à λ=0,9
sur deux ticks (c'est lui qui calibre l'instrument) ; puis le no-op à λ=0 (bit-identique à HEAD), le chemin
trace forcé à λ→0 (allclose, PAS bit-identique : deux backwards au lieu d'un), la décroissance (γλ)^k, lr=0
(dW=0, la trace avance quand même), les refus explicites et l'adaptateur du compteur (restauré en finally).
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

torch = pytest.importorskip("torch")

from src.agents.backend_torch import _GAMMA, _VALUE_NODE, TorchPopulationModel as T  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402

B, TICKS = 3, 3
_FLAGS = ("CREDIT_TRACE_LAMBDA", "CREDIT_TRACE_BYPASS_OPTIMIZER", "CONDITION_GATE", "ANTISAT", "BILINEAR")


@pytest.fixture
def flags():
    saved = {k: getattr(T, k) for k in _FLAGS}
    yield
    for k, v in saved.items():
        setattr(T, k, v)


def _pop(seed, lr=0.04):
    np.random.seed(seed)
    torch.manual_seed(seed)
    return T([MambaAgent() for _ in range(B)], lr=lr)          # même constructeur que make_population(backend="torch")


def _params(pop):
    return [q for grp in pop.opt.param_groups for q in grp["params"]]


def _obs(seed, t, pop):
    return np.random.RandomState(1000 * seed + t).uniform(-1, 1, (B, pop.I)).astype(np.float32)


def _acts(t):
    return [{"move": (t + i) % 8, "grab": (t + i) % 2, "rub": 0} for i in range(B)]


def _run(seed, lam, ticks=TICKS, lr=0.04, rewards=None, bypass=False):
    """Boucle forward/learn par pas, comme le monde le fait ; rend (W final, pop)."""
    T.CREDIT_TRACE_LAMBDA = float(lam)
    T.CREDIT_TRACE_BYPASS_OPTIMIZER = bool(bypass)
    pop = _pop(seed, lr=lr)
    for t in range(ticks):
        pop.forward(_obs(seed, t, pop))
        r = np.full(B, 0.5 if rewards is None else rewards[t], dtype=np.float32)
        pop.learn(r, _acts(t))
    return pop.W.detach().cpu().numpy().copy(), pop


def _run_all_params(seed, lam, lr=0.04):
    W, pop = _run(seed, lam, lr=lr)
    return [q.detach().cpu().numpy().copy() for q in _params(pop)], pop


def _predicted_trace_update(seed, lam, lr=0.04):
    """La FORMULE scellée, recomputée hors du modèle : traces accumulantes sur les transitions 0 et 1
    (la transition t est mise à jour à l'appel learn de t+1 : deux mises à jour sur trois ticks)."""
    T.CREDIT_TRACE_LAMBDA = 0.0                     # un modèle témoin, jamais mis à jour par la trace
    pop = _pop(seed, lr=lr)
    noms = ["W", "U", "V", "W_bl"] if T.BILINEAR else ["W"]   # l'ordre de l'optimiseur (backend_torch.__init__)
    P0 = [getattr(pop, n).detach().clone() for n in noms]
    e_a = [None] * len(noms)
    e_v = [None] * len(noms)
    P_pred = [q.clone() for q in P0]
    trans, H = [], torch.zeros((B, pop.N))
    for s in range(TICKS):
        # forward du tick s : avec les paramètres COURANTS (après s-1 mises à jour), état H du tick précédent
        obs, H_in = torch.tensor(_obs(seed, s, pop)), H
        for n, q in zip(noms, P_pred):
            setattr(pop, n, q.clone())
        with torch.no_grad():
            H = pop._step(obs, H_in)
        if s == 0:
            trans.append({"obs": obs, "H_in": H_in, "act": _acts(s)})
            continue
        # learn du tick s : mise à jour de la transition s-1, V(s') lu sur l'état que forward vient de produire
        prev = trans[s - 1]
        P = [q.clone().requires_grad_(True) for q in P_pred]
        for n, q in zip(noms, P):
            setattr(pop, n, q)                      # le modèle porte P_pred pour recalculer le graphe
        H_new = pop._step(prev["obs"], prev["H_in"])
        out = H_new[:, pop.N - pop.O:pop.N]
        v = out[:, _VALUE_NODE]
        v_next = H[:, pop.N - pop.O + _VALUE_NODE]
        target = 0.5 + _GAMMA * v_next
        delta = (target - v).detach()
        idx = torch.arange(B)
        moves = torch.tensor([a["move"] for a in prev["act"]])
        logp = torch.log_softmax(out[:, :8], dim=1)[idx, moves]
        grab = torch.tensor([float(a["grab"]) for a in prev["act"]])
        rub = torch.tensor([float(a["rub"]) for a in prev["act"]])
        F = torch.nn.functional
        logp = logp - F.binary_cross_entropy_with_logits(out[:, 24], grab, reduction="none")
        logp = logp - F.binary_cross_entropy_with_logits(out[:, 25], rub, reduction="none")
        g_a = torch.autograd.grad(logp.sum(), P, retain_graph=True)
        g_v = torch.autograd.grad(v.sum(), P)
        for i in range(len(P)):
            e_a[i] = g_a[i] if e_a[i] is None else _GAMMA * lam * e_a[i] + g_a[i]
            e_v[i] = g_v[i] if e_v[i] is None else _GAMMA * lam * e_v[i] + g_v[i]
            forme = (-1,) + (1,) * (P[i].dim() - 1)
            P_pred[i] = (P_pred[i] + lr * (delta.view(forme) * e_a[i]
                                           - (v - target).detach().view(forme) * e_v[i]) / B).detach()
        trans.append({"obs": obs, "H_in": H_in, "act": _acts(s)})
    return [q.numpy() for q in P0], [q.numpy() for q in P_pred]


def test_CONTROLE_POSITIF_delta_W_is_EXACTLY_the_sealed_formula_at_lambda_0_9_over_two_updates(flags):
    T.BILINEAR = False
    P0, P_pred = _predicted_trace_update(7, 0.9)
    P_mes, pop = _run_all_params(7, 0.9)
    assert len(P_mes) == len(P_pred) == 1 and pop.trace_updates == TICKS - 1 and np.abs(P_mes[0] - P0[0]).sum() > 0.0
    np.testing.assert_allclose(P_mes[0], P_pred[0], rtol=0, atol=1e-6)
    # et la formule n'est pas dégénérée : à λ=0,5 elle prédit AUTRE chose (la trace agit)
    _, P_pred_05 = _predicted_trace_update(7, 0.5)
    assert np.abs(P_pred_05[0] - P_pred[0]).max() > 1e-7


def test_CONTROLE_POSITIF_holds_under_BILINEAR_for_all_four_traced_parameters(flags):
    # le substrat du pilote TD par pas (contrôle positif BPTT bilinéaire 0,923) : W, U, V, W_bl sont tous tracés
    T.BILINEAR = True
    P0, P_pred = _predicted_trace_update(8, 0.9)
    P_mes, pop = _run_all_params(8, 0.9)
    assert len(P_mes) == len(P_pred) == 4 and len(pop.e_a) == 4
    for i in range(4):
        assert np.abs(P_mes[i] - P0[i]).sum() > 0.0, f"paramètre {i} jamais mis à jour"
        np.testing.assert_allclose(P_mes[i], P_pred[i], rtol=0, atol=1e-6)


def test_lambda_zero_is_BIT_IDENTICAL_to_the_original_TD0_path(flags):
    T.CREDIT_TRACE_LAMBDA = 0.0
    a, pa = _run(3, 0.0)
    b, pb = _run(3, 0.0)
    assert np.array_equal(a, b) and pa.trace_updates == 0 and pa.e_a is None
    # le dictionnaire de classe n'a pas bougé : 0.0 = défaut
    assert T.__dict__["CREDIT_TRACE_LAMBDA"] == 0.0 and T.__dict__["CREDIT_TRACE_BYPASS_OPTIMIZER"] is False


def test_trace_path_forced_at_vanishing_lambda_matches_TD0_closely_but_is_declared_NOT_bit_identical(flags):
    # λ→0+ : e = g à chaque pas -> même ΔW que TD(0) sous SGD, obtenu par DEUX backwards au lieu d'un
    a, _ = _run(5, 0.0)
    b, pb = _run(5, 1e-12)
    assert pb.trace_updates == TICKS - 1
    np.testing.assert_allclose(a, b, rtol=0, atol=1e-6)


def test_trace_decays_as_gamma_lambda_to_the_k_when_gradients_vanish(flags):
    T.CREDIT_TRACE_LAMBDA = 0.9
    pop = _pop(11)
    e0 = torch.ones((B, pop.N, pop.N))
    e = e0
    for k in range(1, 4):
        e = pop._trace_step(e, torch.zeros_like(e0), _GAMMA * 0.9)
        assert torch.allclose(e, e0 * (_GAMMA * 0.9) ** k)


def test_lr_zero_leaves_W_untouched_while_the_trace_still_advances(flags):
    W0 = _pop(13).W.detach().cpu().numpy().copy()
    W, pop = _run(13, 0.9, lr=0.0)
    assert np.array_equal(W, W0) and pop.trace_updates == TICKS - 1 and float(pop.e_a[0].abs().sum()) > 0.0


def test_refusals_are_explicit_gate_bilinear_and_non_sgd_optimizer(flags):
    T.CREDIT_TRACE_LAMBDA = 0.9
    pop = _pop(17)
    assert pop._trace_refusals() == []
    T.ANTISAT = 0.1
    assert any("gate" in r for r in pop._trace_refusals())
    T.ANTISAT = 0.0
    pop.opt = torch.optim.Adam([pop.W], lr=0.01)
    raisons = pop._trace_refusals()
    assert len(raisons) == 1 and "Adam" in raisons[0]
    T.CREDIT_TRACE_BYPASS_OPTIMIZER = True
    assert pop._trace_refusals() == []                  # contournement DEMANDÉ, pas silencieux
    T.CREDIT_TRACE_BYPASS_OPTIMIZER = False
    with pytest.raises(NotImplementedError, match="Adam"):
        pop.forward(_obs(17, 0, pop)); pop.learn(np.zeros(B), _acts(0))
        pop.forward(_obs(17, 1, pop)); pop.learn(np.zeros(B), _acts(1))


def test_reset_traces_is_an_option_counted_never_a_default(flags):
    _, pop = _run(19, 0.9)
    assert pop.trace_resets == 0
    n = pop.reset_traces(mask=[True, False, False])
    assert n == 1 and pop.trace_resets == 1
    assert float(pop.e_a[0][0].abs().sum()) == 0.0 and float(pop.e_a[0][1].abs().sum()) > 0.0
    assert pop.reset_traces() == B and float(pop.e_a[0].abs().sum()) == 0.0
    vierge = _pop(19)
    assert vierge.reset_traces() == 0 and vierge.trace_resets == 1     # l'appel est compté, rien à remettre


def test_counter_adapter_sets_and_restores_the_flags_and_publishes_them(flags):
    from tools.learning_events import count_learning_events
    T.CREDIT_TRACE_LAMBDA = 0.0
    with count_learning_events(trace_lambda=0.9) as ev:
        assert T.CREDIT_TRACE_LAMBDA == 0.9 and T.CREDIT_TRACE_BYPASS_OPTIMIZER is False
        _, pop = _run(23, T.CREDIT_TRACE_LAMBDA)
    assert T.CREDIT_TRACE_LAMBDA == 0.0
    s = ev.summary()
    assert s["trace_lambda"] == 0.9 and s["trace_updates"] == TICKS - 1 and s["trace_resets"] == 0
    with count_learning_events() as ev2:                 # None = drapeau intact, publié None
        pass
    assert ev2.summary()["trace_lambda"] is None and T.CREDIT_TRACE_LAMBDA == 0.0
