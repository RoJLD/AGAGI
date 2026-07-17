import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.agents.backend import make_population
from src.agents.backend_torch import TorchPopulationModel


def _gated_pop(n=4, seed=0):
    np.random.seed(seed)
    import torch; torch.manual_seed(seed)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True
    TorchPopulationModel.GATE_TARGET = 4        # USE
    try:
        pop = make_population([MambaAgent() for _ in range(n)], backend="torch")
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved
    return pop


def test_inherit_gate_copies_values():
    import torch
    from tools.torch_gate_persist_ab import inherit_gate
    old = _gated_pop(seed=0)
    with torch.no_grad():
        old.w_gate += 3.0                        # rend le gate distinct de l'init
        old.b_gate -= 1.5
    new = _gated_pop(seed=1)
    ok = inherit_gate(new, old)
    assert ok is True
    assert torch.allclose(new.w_gate.data, old.w_gate.data)
    assert torch.allclose(new.b_gate.data, old.b_gate.data)


def test_inherit_gate_noop_when_gate_absent():
    from tools.torch_gate_persist_ab import inherit_gate
    old = _gated_pop(seed=0)
    plain = make_population([MambaAgent() for _ in range(4)], backend="torch")  # gate OFF -> w_gate None
    assert inherit_gate(plain, old) is False     # cible sans gate -> no-op
    assert inherit_gate(old, plain) is False      # source sans gate -> no-op


def test_run_arm_smoke_persist_and_reset():
    from tools.torch_gate_persist_ab import run_arm
    r_p = run_arm(persist=True, episodes=40, rebuild_every=20, n_agents=16, seed=0)
    r_r = run_arm(persist=False, episodes=40, rebuild_every=20, n_agents=16, seed=0)
    for r in (r_p, r_r):
        assert set(["persist", "comp_rate", "n_rebuilds"]).issubset(r)
        assert 0.0 <= r["comp_rate"] <= 1.0
    assert r_p["n_rebuilds"] == r_r["n_rebuilds"] == 1     # 40/20 - 1 rebuild a l'episode 20


def test_verdict_pure_persist_better():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": 0.10}, {"diff": 0.08}, {"diff": 0.12}]   # persist - reset > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 3


def test_rebuild_asymmetry_gate_lost_unless_inherited():
    """Preuve directe de l'asymetrie du rebuild : un pas de learn_episode fait diverger le gate (w_gate)
    ET ecrit un W neuf dans le genome. Au rebuild : W SURVIT toujours (relu du genome par le nouveau pop)
    mais le gate est PERDU (RESET, neuf ~ 0) sauf carry-over explicite (PERSIST, inherit_gate)."""
    import numpy as np, torch
    from tools.torch_gate_persist_ab import _new_gated_pop, inherit_gate
    from tools.compositional_world_probe import _energy, _softmax_np, CRAFT, USE, _MOVE
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    np.random.seed(0); torch.manual_seed(0)
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = True; TorchPopulationModel.ANTISAT = 6.0; TorchPopulationModel.GATE_TARGET = USE
    try:
        n = 8
        agents = [MambaAgent() for _ in range(n)]
        pop = _new_gated_pop(agents, lr=0.05)
        W_before = np.asarray(agents[0].genome.W, dtype=np.float32).copy()

        # un episode minimal (2 pas, structure de run_arm) pour faire bouger W (genome) ET w_gate
        rng = np.random.RandomState(1)
        I = pop.I
        obs_a = (rng.randn(n, I) * 0.5).astype(np.float32)
        obs_b = (rng.randn(n, I) * 0.5).astype(np.float32)

        def _sample(preds):
            p = _softmax_np(np.asarray(preds)[:, :_MOVE])
            return np.array([rng.choice(_MOVE, p=pi) for pi in p])

        pop.H = torch.zeros((n, pop.N))
        preds1, _ = pop.forward(obs_a)
        move1 = _sample(preds1)
        did_x = (move1 == CRAFT)
        act1 = [{"move": int(m), "grab": 0, "rub": 0} for m in move1]
        preds2, _ = pop.forward(obs_b)
        move2 = _sample(preds2)
        act2 = [{"move": int(m), "grab": 0, "rub": 0} for m in move2]
        energy = np.array([_energy(int(move2[i]), bool(did_x[i]), 1.0) for i in range(n)], dtype=np.float32)
        pop.learn_episode([obs_a, obs_b], [act1, act2], energy - energy.mean(), gate_last_only=False)

        W_after = np.asarray(agents[0].genome.W, dtype=np.float32).copy()
        assert not np.allclose(W_after, W_before)       # W a change (learn_episode ecrit dans le genome)
        with torch.no_grad():
            pop.w_gate += 2.0                           # simule un gate appris fortement (distinct de 0)

        # RESET : rebuild sans inherit -> gate neuf ~ 0, mais W (genome, deja mis a jour) survit
        reset_pop = _new_gated_pop(agents, lr=0.05)
        assert float(reset_pop.w_gate.abs().sum()) < 1e-6
        assert np.allclose(reset_pop.W.detach().numpy()[0], W_after)

        # PERSIST : rebuild + inherit -> gate porte (identique au pop appris)
        persist_pop = _new_gated_pop(agents, lr=0.05)
        assert inherit_gate(persist_pop, pop) is True
        assert torch.allclose(persist_pop.w_gate.data, pop.w_gate.data)
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.ANTISAT, TorchPopulationModel.GATE_TARGET) = saved
