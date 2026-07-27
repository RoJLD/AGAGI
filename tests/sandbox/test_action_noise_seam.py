"""Calibration du levier ACTION_NOISE (EDR-DREAM-004) sur reponse CONNUE.

Contrôle de LOCUS pour DREAM-003. Le bruit de reve perturbe l'etat cache H (PORTE au tick suivant) ;
ce seam perturbe les logits d'ACTION (TRANSITOIRE, non porte), chez les memes porteurs d'organe. Trois
formes du depot :
  - no-op EXACT (specificite)   : a sigma=0, l'action est identique a tirage RNG pres (le seam est mort).
  - specificite inverse         : a sigma>0, l'action bouge (le seam est LU).
  - specificite de POPULATION   : SEULS les porteurs d'organe sont perturbes -- un non-porteur voit ses
                                  logits d'action INCHANGES meme a sigma>0 (sinon le contraste avec le
                                  bruit de reve, lui aussi gate sur l'organe, serait confondu).

Motivation (identique a DREAM_NOISE) : un flag non calibre ne se contente pas d'echouer, il PRODUIT un
resultat. Un bras de controle dont l'injection ne s'applique pas renverrait "le bruit d'action ne
reproduit pas l'effet" -- exactement la conclusion qu'on cherche a tester -- pour la mauvaise raison
(l'intervention ne s'est jamais appliquee). C'est le piege `intervention_verified` de DREAM-002, ici
attrape en amont par une assertion sur l'ENTREE perturbee.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent, MambaBatchModel


@pytest.fixture(autouse=True)
def _restore_flags():
    saved = (MambaBatchModel.ACTION_NOISE, MambaBatchModel.FORCE_DREAM)
    yield
    MambaBatchModel.ACTION_NOISE, MambaBatchModel.FORCE_DREAM = saved


def _agent(organ_on):
    a = MambaAgent()
    a.genome.organ_genes = np.array([bool(organ_on), False])
    return a


def _action_logits(agent, obs, sigma, rng_seed):
    """Les 8 logits de deplacement (preds[:, :8]), a amplitude et graine imposees.

    COPIE explicite : `forward` renvoie une VUE de l'etat (avertissement CLAUDE.md, origine de
    l'aliasing WARM-007). Comparer deux vues d'un meme buffer donnerait une egalite triviale."""
    MambaBatchModel.ACTION_NOISE = sigma
    MambaBatchModel.FORCE_DREAM = "off"          # isoler le bruit d'ACTION du bruit de reve
    np.random.seed(rng_seed)
    m = MambaBatchModel([agent.clone()])
    preds, _ = m.forward(obs.copy())
    A = min(MambaBatchModel.PLAN_A, preds.shape[1])
    return np.array(preds[0, :A], dtype=np.float64, copy=True)


def test_default_is_off():
    """Defaut 0.0 -> le seam est inerte, prod strictement inchangee."""
    assert MambaBatchModel.ACTION_NOISE == 0.0


def test_sigma_zero_is_exactly_deterministic():
    """no-op EXACT : a sigma=0, aucun tirage n'est consomme par le seam -> deux graines != -> identique."""
    np.random.seed(0)
    a = _agent(True)
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    assert np.array_equal(_action_logits(a, obs, 0.0, 1), _action_logits(a, obs, 0.0, 7))


def test_sigma_positive_perturbs_the_action_of_a_carrier():
    """Specificite : chez un porteur d'organe, sigma>0 change les logits d'action (le seam est LU)."""
    np.random.seed(0)
    a = _agent(True)
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    assert not np.array_equal(_action_logits(a, obs, 1.0, 1), _action_logits(a, obs, 1.0, 7))


def test_non_carrier_is_untouched_even_at_high_sigma():
    """Specificite de POPULATION : un NON-porteur n'est jamais perturbe. Sans ca, le bras de controle
    toucherait une population differente de celle du reve, et le contraste porte-vs-transitoire serait
    confondu par 'qui est perturbe' au lieu de 'ou'."""
    np.random.seed(0)
    a = _agent(False)                    # PAS d'organe
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    assert np.array_equal(_action_logits(a, obs, 5.0, 1), _action_logits(a, obs, 5.0, 7))


def test_perturbation_grows_with_amplitude():
    """Monotonie : l'ecart aux logits d'action SANS bruit croit avec sigma. Mediane sur graines RNG
    pour ne pas dependre d'une realisation gaussienne unique."""
    np.random.seed(0)
    a = _agent(True)
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    ref = _action_logits(a, obs, 0.0, 1)
    ecarts = [float(np.median([np.linalg.norm(_action_logits(a, obs, s, r) - ref) for r in range(7)]))
              for s in (0.25, 1.0, 4.0)]
    assert ecarts == sorted(ecarts), f"non monotone : {ecarts}"
    assert ecarts[0] > 0.0
