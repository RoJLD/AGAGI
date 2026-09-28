"""P4.19 (a) — sham « δ DÉCALÉ d'un épisode » de la pièce eligibility_trace (`backend_torch.py::
CREDIT_TRACE_DELTA_SHAM`, `_td_update_trace_sham`), confronté à des réponses CONNUES, 0 simulation de monde.

Ordre : la FORMULE d'abord, à réponse connue sur des tenseurs posés (Δθ = lr/B·[δ·(g_a+g_v) + δ̃·γλ·(e_a+e_v)]) ;
puis le mode `identite` (δ̃ := δ) égal au chemin trace de P4.11 à l'arrondi près ; le mode `decale` qui OMET le porté au
1er épisode (compté) puis prend le δ du MÊME rang à l'épisode précédent ; le défaut None intact ; les REFUS, testés à
leur EMPLACEMENT (constructeur, première mise à jour).
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

torch = pytest.importorskip("torch")

from src.agents.backend_torch import _GAMMA, TorchPopulationModel as T  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402

B = 3
_FLAGS = ("CREDIT_TRACE_LAMBDA", "CREDIT_TRACE_BYPASS_OPTIMIZER", "CREDIT_TRACE_DELTA_SHAM", "CONDITION_GATE",
          "ANTISAT", "BILINEAR")


@pytest.fixture
def flags():
    saved = {k: getattr(T, k) for k in _FLAGS}
    T.BILINEAR = False
    yield
    for k, v in saved.items():
        setattr(T, k, v)


def _pop(seed, lam=0.9, sham=None, lr=0.04):
    T.CREDIT_TRACE_LAMBDA = float(lam)
    T.CREDIT_TRACE_DELTA_SHAM = sham
    np.random.seed(seed)
    torch.manual_seed(seed)
    return T([MambaAgent() for _ in range(B)], lr=lr)


def _obs(seed, ep, t, pop):
    return np.random.RandomState(10007 * seed + 101 * ep + t).uniform(-1, 1, (B, pop.I)).astype(np.float32)


def _acts(ep, t):
    return [{"move": (3 * ep + t + i) % 8, "grab": (ep + i) % 2, "rub": 0} for i in range(B)]


def _episodes(pop, seed, n_ep, reset=True):
    """Épisodes de DEUX pas, comme le pilote TD-STEP (D = 1) : learn au pas 1 (transition 0, rang 0), puis la mise à
    jour terminale (transition 1, rang 1, bootstrap 0) -- `tools/td_step_pilot.py::_flush_terminal`."""
    for ep in range(n_ep):
        pop.H = torch.zeros((B, pop.N))
        pop._prev = None
        if reset:
            pop.reset_traces()
        for t in range(2):
            pop.forward(_obs(seed, ep, t, pop))
            r = np.zeros(B, np.float32) if t == 0 else np.array([1.0, -1.0, 1.0][:B], np.float32)
            pop.learn(r, _acts(ep, t))
        pop._td_update(pop._prev, torch.zeros(B))
        pop._prev = None
    return pop


# ---------------------------------------------------------------------------------------------------- la formule


def _formule(sham, d_tilde_connu):
    torch.manual_seed(3)
    pop = _pop(1, sham=sham)
    q = pop.W
    ga, gv = torch.randn_like(q), torch.randn_like(q)
    ea, ev = torch.randn_like(q), torch.randn_like(q)
    delta = torch.tensor([0.5, -1.25, 2.0])
    pop.e_a, pop.e_v = [ea.clone()], [ev.clone()]
    pop._rang = 1
    pop._delta_prec = {1: d_tilde_connu.clone()} if d_tilde_connu is not None else {}
    avant = q.detach().clone()
    z = torch.zeros(B)
    pop._td_update_trace_sham([q], (ga,), (gv,), _GAMMA * 0.9, 0.04, z, z, z, delta)
    return pop, avant, q.detach().clone(), (ga, gv, ea, ev, delta)


def test_FORMULE_the_carried_term_receives_the_previous_episode_delta_and_the_TD0_term_keeps_its_own(flags):
    d_tilde = torch.tensor([-3.0, 0.25, 1.5])
    pop, avant, apres, (ga, gv, ea, ev, delta) = _formule("decale", d_tilde)
    gl, f = _GAMMA * 0.9, (-1, 1, 1)
    attendu = avant + 0.04 * (delta.view(f) * (ga + gv) + d_tilde.view(f) * gl * (ea + ev)) / B
    torch.testing.assert_close(apres, attendu, rtol=0, atol=1e-6)
    torch.testing.assert_close(pop.e_a[0], gl * ea + ga, rtol=0, atol=1e-7)   # la trace avance comme en P4.11
    assert torch.equal(pop._delta_cour[1], delta) and pop._rang == 2           # le δ VRAI, empilé APRÈS
    contre = float((0.04 * delta.view(f) * gl * (ea + ev) / B).abs().sum())
    appli = float((0.04 * d_tilde.view(f) * gl * (ea + ev) / B).abs().sum())
    assert pop.chemin_porte_contrefactuel == pytest.approx(contre, rel=1e-5)
    assert pop.chemin_porte_applique == pytest.approx(appli, rel=1e-5) and pop.sham_omis == 0


def test_FORMULE_identite_is_the_trace_formula_and_an_empty_buffer_OMITS_the_carried_term_counted(flags):
    pop, avant, apres, (ga, gv, ea, ev, delta) = _formule("identite", None)
    gl, f = _GAMMA * 0.9, (-1, 1, 1)
    trace = avant + 0.04 * (delta.view(f) * (gl * ea + ga) + delta.view(f) * (gl * ev + gv)) / B
    torch.testing.assert_close(apres, trace, rtol=0, atol=1e-6)               # P4.11 : δ·e_a − (V−cible)·e_v
    pop, avant, apres, (ga, gv, ea, ev, delta) = _formule("decale", None)     # tampon VIDE (1er épisode)
    torch.testing.assert_close(apres, avant + 0.04 * delta.view(f) * (ga + gv) / B, rtol=0, atol=1e-6)
    assert pop.sham_omis == B and pop.chemin_porte_applique == 0.0 and pop.chemin_porte_contrefactuel > 0.0


# ---------------------------------------------------------------------------------------------------- en épisodes


def test_identite_mode_equals_the_P4_11_trace_path_over_episodes_allclose_not_bit_exact(flags):
    W_trace = _episodes(_pop(5, sham=None), 5, 3).W.detach().clone()
    pop = _episodes(_pop(5, sham="identite"), 5, 3)
    torch.testing.assert_close(pop.W.detach(), W_trace, rtol=0, atol=1e-5)
    assert pop.trace_updates == 6 and pop.sham_omis == 0
    assert pop.chemin_porte_applique == pytest.approx(pop.chemin_porte_contrefactuel, rel=1e-9)


def test_decale_omits_only_in_the_first_episode_and_moves_W_away_from_the_trace(flags):
    W_trace = _episodes(_pop(5, sham=None), 5, 3).W.detach().clone()
    pop = _episodes(_pop(5, sham="decale"), 5, 3)
    assert pop.sham_omis == B                                                  # un par agent, au seul 1er épisode
    assert pop.chemin_porte_applique > 0.0 and pop.chemin_td0 > 0.0
    assert float((pop.W.detach() - W_trace).abs().max()) > 1e-6               # le sham CHANGE quelque chose
    assert set(pop._delta_cour) == {0, 1} and set(pop._delta_prec) == {0, 1}


def test_the_TD_STEP_pilot_pins_the_sham_OFF_and_restores_it(flags, monkeypatch):
    """λ > 0 et reset par épisode réunissent dans le pilote les deux conditions du sham : un drapeau resté posé
    rejouerait R1/R2 shamés EN SILENCE. Observable : le chemin sham n'est JAMAIS pris (espion), et le drapeau est
    restauré. ⚠️ Comparer l'accuracy ne discriminait pas : à 3 épisodes et 8 exemples d'éval, le mutant sans pin rend
    la MÊME accuracy (0,375) -- mesuré avant d'écrire ce témoin, un contrôle qui ne pouvait pas échouer."""
    from tools.td_step_pilot import _train_eval_td_step
    appels = []
    vrai = T._td_update_trace_sham
    monkeypatch.setattr(T, "_td_update_trace_sham", lambda self, *a: appels.append(1) or vrai(self, *a))
    T.CREDIT_TRACE_DELTA_SHAM = "decale"
    _train_eval_td_step(0, 0.9, 3, 4, 4, 0.04, eval_batches=2)
    assert appels == [] and T.CREDIT_TRACE_DELTA_SHAM == "decale"            # épinglé PENDANT, restauré APRÈS
    pop = _episodes(_pop(5, sham="decale"), 5, 1)                              # l'espion VOIT le chemin quand il est pris
    assert len(appels) == 2 and pop.trace_updates == 2


def test_default_None_leaves_every_sham_counter_at_zero(flags):
    pop = _episodes(_pop(5, sham=None), 5, 2)
    assert (pop.sham_omis, pop.chemin_porte_applique, pop.chemin_porte_contrefactuel, pop.chemin_td0) == (0, 0.0, 0.0,
                                                                                                          0.0)
    assert pop._rang is None and pop._delta_cour == {} and pop.trace_updates == 4


# ---------------------------------------------------------------------------------------------------- les refus


def test_REFUSALS_sit_at_the_constructor_before_any_episode(flags):
    with pytest.raises(ValueError, match="λ = 0"):
        _pop(1, lam=0.0, sham="decale")                                        # le bras vaudrait TD(0) en silence
    with pytest.raises(ValueError, match="vocabulaire"):
        _pop(1, sham="permute")


def test_REFUSALS_a_mask_reset_and_an_update_without_reset_under_the_sham(flags):
    pop = _pop(1, sham="decale")
    with pytest.raises(ValueError, match="masque"):
        pop.reset_traces(mask=np.array([True, False, True]))
    pop = _pop(1, sham="decale")
    with pytest.raises(RuntimeError, match="sans reset_traces"):
        _episodes(pop, 1, 1, reset=False)


def test_REFUSAL_the_guard_is_rechecked_at_each_update_after_a_flag_change(flags):
    pop = _pop(1, sham="decale")
    T.CREDIT_TRACE_LAMBDA = 0.0                                                # changé APRÈS la construction
    with pytest.raises(ValueError, match="λ = 0"):
        _episodes(pop, 1, 1)
