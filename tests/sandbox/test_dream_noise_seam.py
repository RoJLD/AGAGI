"""Calibration du levier DREAM_NOISE (EDR-DREAM-003) sur reponse CONNUE.

Trois formes du depot (cf. CLAUDE.md / tests/sandbox/test_instrument_calibration.py) :
  - no-op EXACT (specificite) : a sigma=0 la seule source de hasard de la boucle de reve disparait
    -> deux tirages RNG differents donnent le MEME resultat.
  - specificite inverse       : a sigma>0 ils different (sinon le flag serait mort et toute l'echelle
    d'amplitude mesurerait la meme chose sans le dire).
  - monotonie (direction)     : l'ecart a la trajectoire sans bruit CROIT avec sigma.

Motivation : un flag non calibre ne se contente pas d'echouer, il PRODUIT un resultat. Une echelle de
dose dont le flag n'est pas lu renvoie un plateau parfaitement plat -- qui se lit comme un resultat
negatif propre ("l'amplitude n'a pas d'effet") alors que rien n'a ete manipule.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import numpy as np
import pytest

from src.agents.mamba_agent import MambaAgent, MambaBatchModel

K = 8


@pytest.fixture(autouse=True)
def _restore_flags():
    """Les flags sont des attributs de CLASSE : les restaurer sinon ils fuient vers les autres tests."""
    saved = (MambaBatchModel.FORCE_DREAM, MambaBatchModel.DREAM_SHAM, MambaBatchModel.DREAM_NOISE)
    yield
    (MambaBatchModel.FORCE_DREAM, MambaBatchModel.DREAM_SHAM,
     MambaBatchModel.DREAM_NOISE) = saved


def _dreamer():
    a = MambaAgent()
    a.genome.organ_genes = np.array([True, False])   # organe MCTS ON -> l'agent reve
    return a


def _forward(agent, obs, sigma, rng_seed):
    """Un forward isole, a amplitude et graine RNG imposees. Renvoie une COPIE des logits.

    La copie n'est pas cosmetique : `forward` renvoie des VUES de l'etat recurrent (avertissement
    explicite de CLAUDE.md, et l'origine du bug d'aliasing d'EDR-WARM-007). Comparer deux vues d'un
    meme buffer reutilise donnerait une egalite triviale -- exactement le faux no-op qu'on teste.
    """
    MambaBatchModel.FORCE_DREAM = K
    MambaBatchModel.DREAM_SHAM = False               # selection argmax = deterministe
    MambaBatchModel.DREAM_NOISE = sigma
    np.random.seed(rng_seed)
    m = MambaBatchModel([agent.clone()])
    preds, _ = m.forward(obs.copy())
    return np.array(preds, dtype=np.float64, copy=True)


def test_default_amplitude_is_historical_value():
    """Defaut = valeur qui etait en dur -> la prod est inchangee par l'ajout du seam."""
    assert MambaBatchModel.DREAM_NOISE == 0.05


def test_sigma_zero_is_exactly_deterministic():
    """no-op EXACT : a sigma=0, le bruit est la SEULE source de hasard de la boucle de reve."""
    np.random.seed(0)
    a = _dreamer()
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    assert np.array_equal(_forward(a, obs, 0.0, 1), _forward(a, obs, 0.0, 999))


def test_sigma_positive_is_stochastic():
    """Specificite : le flag est LU. Sans cette assertion, une echelle de dose muette renverrait un
    plateau plat qu'on lirait comme "l'amplitude n'a pas d'effet"."""
    np.random.seed(0)
    a = _dreamer()
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    assert not np.array_equal(_forward(a, obs, 0.05, 1), _forward(a, obs, 0.05, 999))


def test_divergence_grows_with_amplitude():
    """Monotonie : l'ecart a la trajectoire SANS bruit croit avec sigma.

    Mediane sur plusieurs graines RNG -- une seule realisation d'un tirage gaussien peut inverser
    deux doses voisines par pur hasard, et un test qui echoue une fois sur dix est un test qu'on
    finit par ignorer.
    """
    np.random.seed(0)
    a = _dreamer()
    obs = np.random.randn(1, a.genome.num_inputs).astype(np.float32)
    ref = _forward(a, obs, 0.0, 1)
    ecarts = [float(np.median([np.linalg.norm(_forward(a, obs, s, r) - ref) for r in range(7)]))
              for s in (0.0125, 0.05, 0.2, 0.8)]
    assert ecarts == sorted(ecarts), f"non monotone : {ecarts}"
    assert ecarts[0] > 0.0
