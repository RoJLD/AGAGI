# -*- coding: utf-8 -*-
"""E19 (occ. lr/B, 2026-09-16) — sous torch in-world, le pas EFFECTIF par agent est lr / B.

`TorchPopulationModel` porte un W (B, N, N) — un jeu de poids DISJOINT par agent — mais `_td_update`
moyenne actor_loss et critic_loss sur B (`backend_torch.py:219-221`) et optimise par SGD (`:117`),
où le 1/B ne s'annule pas (il s'annulerait sous Adam). Donc chaque agent reçoit lr/B : « 0,04 » à
B = 12 vaut 0,0033 par agent, et `count_learning_events` posait `LR_ACTOR = lr` legacy ↔ SGD lr torch
comme ÉQUIVALENTS (`learning_events.py:189-192`). Aucun record ne le disait ; CALIB-LEGACY comparait
« legacy 0,004 » à « torch 0,04 » = 0,0033.

Calibration par PRÉDICTION (pas par lecture) : le MÊME agent, dans une population de 1 et dans une
population de 12 copies, sous la MÊME transition, doit bouger EXACTEMENT 12× moins à B = 12. Le
contrôle qui peut échouer : si quelqu'un passe la perte en `.sum()` ou l'optimiseur en Adam, le ratio
n'est plus B et ce test le dit — et `effective_lr_per_agent` devrait alors être réécrit avec lui.
"""
import copy
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

torch = pytest.importorskip("torch")

from src.agents.mamba_agent import MambaAgent  # noqa: E402
from src.agents.backend_torch import TorchPopulationModel  # noqa: E402
from tools.cognitive_demand_inworld import _pinned_substrate  # noqa: E402

_LR = 0.04
_ACT = {"move": 3, "grab": 0, "rub": 0}


def _clones(seed, B):
    """B copies PROFONDES du même agent : W identique, donc δ et gradient identiques par agent."""
    np.random.seed(seed)
    a0 = MambaAgent()
    return [copy.deepcopy(a0) for _ in range(B)]


def _one_update(B, seed=0, lr=_LR):
    """Une population de B clones, DEUX ticks (le premier learn est différé) : rend ΔW de l'agent 0."""
    agents = _clones(seed, B)
    with _pinned_substrate():
        pop = TorchPopulationModel(agents, lr=lr)
    obs0 = np.random.RandomState(7).uniform(-1.0, 1.0, pop.I).astype(np.float32)
    obs = np.tile(obs0, (B, 1))                      # la MÊME observation pour chaque clone
    W_before = pop.W.detach().clone()[0]
    for _ in range(2):
        pop.forward(obs)
        pop.learn(np.full(B, 1.0, dtype=np.float32), [dict(_ACT) for _ in range(B)])
    return (pop.W.detach()[0] - W_before), pop


def test_le_pas_par_agent_est_lr_sur_B():
    """Prédiction : ΔW(B=1) == 12 · ΔW(B=12) composante par composante.

    Tolérance absolue 5e-7 : mesuré en écrivant ce test, les composantes de ΔW(B=12) valent quelques
    ulp float32 de W (~7e-9 à 1,5e-8 chacun), donc leur ratio individuel oscille entre 11,0 et 12,8
    alors que le ratio des sommes vaut 12,000 — la quantification, pas la prédiction. Un `.sum()` à
    la place du `.mean()` (ratio 1) laisserait des écarts ~1e-5 à 1e-3 : trois ordres au-dessus."""
    dW1, _ = _one_update(1)
    dW12, _ = _one_update(12)
    assert float(dW1.abs().sum()) > 0.0, "contrôle : l'update bouge W (sinon le ratio ne mesure rien)"
    assert torch.allclose(dW1, 12.0 * dW12, rtol=1e-3, atol=5e-7)


def test_le_ratio_n_est_PAS_1_le_controle_peut_echouer():
    """Le test précédent ne vaut que si la prémisse inverse est fausse : à ratio 1, allclose(dW1, dW12)
    passerait. On vérifie explicitement que les deux pas DIFFÈRENT d'un facteur mesurable."""
    dW1, _ = _one_update(1)
    dW12, _ = _one_update(12)
    ratio = float(dW1.abs().sum() / dW12.abs().sum())
    assert ratio == pytest.approx(12.0, rel=1e-4)


def test_effective_lr_per_agent_est_publie_et_vaut_lr_sur_B():
    _, pop1 = _one_update(1)
    _, pop12 = _one_update(12)
    assert pop1.effective_lr_per_agent == pytest.approx(_LR)
    assert pop12.effective_lr_per_agent == pytest.approx(_LR / 12.0)


def test_le_learn_publie_lr_effectif_dans_le_bloc_learning():
    """`count_learning_events().summary()` publie `lr_effective_per_agent` à côté de `lr` : le lecteur
    d'un record voit les DEUX, jamais le seul nominal. None tant qu'aucune population n'a appris."""
    from tools.learning_events import count_learning_events
    agents = _clones(0, 12)
    with _pinned_substrate(), count_learning_events(lr=_LR) as ev:
        pop = TorchPopulationModel(agents)
        obs = np.tile(np.random.RandomState(7).uniform(-1.0, 1.0, pop.I).astype(np.float32), (12, 1))
        assert ev.summary()["lr_effective_per_agent"] is None
        for _ in range(2):
            pop.forward(obs)
            pop.learn(np.full(12, 1.0, dtype=np.float32), [dict(_ACT) for _ in range(12)])
    s = ev.summary()
    assert s["lr"] == pytest.approx(_LR)
    assert s["lr_effective_per_agent"] == pytest.approx(_LR / 12.0)
    assert s["lr_effective_unit"] == "torch: lr/B (SGD, perte moyennée sur B, W disjoint par agent)"
