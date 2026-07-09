"""Tests du substrat legacy-core (MambaCoreBatchModel) — EDR-134 suite (bras de contrôle).

PURS (pas de biosphère) : vérifient que l'ablation d'organes est bien un no-op côté legacy,
pour que le bras legacy-core isole la RÈGLE D'APPRENTISSAGE du CONFOUND D'ORGANES.
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.agents.mamba_agent import MambaAgent, MambaBatchModel, MambaCoreBatchModel


def _cohort(n=2):
    return [MambaAgent() for _ in range(n)]


def _obs(agents):
    return np.zeros((len(agents), agents[0].genome.num_inputs), dtype=np.float32)


def test_core_flags_are_set():
    assert MambaCoreBatchModel.ABLATE_THRESHOLDS is True
    assert MambaCoreBatchModel.ABLATE_ROUTER is True
    assert MambaCoreBatchModel.ABLATE_NTM is True
    assert MambaCoreBatchModel.ABLATE_ATTENTION is True
    assert MambaCoreBatchModel.FORCE_DREAM == "off"


def test_base_flags_untouched():
    # non-régressif : la classe de base reste organes-ON par défaut.
    assert MambaBatchModel.ABLATE_NTM is False
    assert MambaBatchModel.ABLATE_ATTENTION is False
    assert MambaBatchModel.ABLATE_ROUTER is False
    assert MambaBatchModel.ABLATE_THRESHOLDS is False
    assert MambaBatchModel.FORCE_DREAM is None


def _wire_ntm(agents):
    """Pose un slot NTM qui câblerait W[0->2]=+5.0 via compile_and_apply (enable>0)."""
    for a in agents:
        mem = np.zeros((10, 5), dtype=np.float32)
        mem[0] = [0.0, 0.02, 1.0, 0.0, 1.0]  # src_idx=0, dst_idx=2, weight=5.0, enable>0
        a.ntm_memory = mem


def test_ntm_selfwiring_active_on_base():
    agents = _cohort()
    _wire_ntm(agents)
    m = MambaBatchModel(agents)
    m.forward(_obs(agents))
    # le self-wiring NTM a écrit la synapse (0->2) à ~5.0
    assert abs(m.W_batch[0][0, 2] - 5.0) < 1e-4


def test_ntm_selfwiring_ablated_on_core():
    agents = _cohort()
    _wire_ntm(agents)
    w0 = float(agents[0].genome.W[0, 2])  # valeur initiale (aucune écriture NTM attendue)
    m = MambaCoreBatchModel(agents)
    m.forward(_obs(agents))
    assert abs(m.W_batch[0][0, 2] - w0) < 1e-6      # inchangé
    assert abs(m.W_batch[0][0, 2] - 5.0) > 1e-3     # PAS la synapse NTM


def test_core_forward_runs_and_shapes_ok():
    agents = _cohort(3)
    m = MambaCoreBatchModel(agents)
    preds, spent = m.forward(_obs(agents))
    assert preds.shape == (3, agents[0].genome.num_outputs)
    assert spent.shape == (3,)


def test_core_inherits_actor_critic_td():
    # même règle d'apprentissage numpy que la base : le point du bras (organes constants).
    assert MambaCoreBatchModel.compute_policy_gradient is MambaBatchModel.compute_policy_gradient
