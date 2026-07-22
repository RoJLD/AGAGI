"""Calibration du masque de groupe de nœuds du rêve (EDR-DREAM-006).

DREAM-006 localise QUEL registre de l'état porté (entrées / cachés / sorties) le bruit doit toucher pour
débloquer la reproduction. Le verdict n'a de sens QUE si le bruit reste dans le groupe déclaré : si les
groupes ne partitionnent pas exactement les nœuds réels, le bruit fuit et l'effet est attribué au mauvais
registre. On teste donc le masque au POINT D'INJECTION (le couplage par W rend « seuls ces nœuds ont
changé » intestable après un forward).

Formes du dépôt :
  - no-op EXACT : group="all" -> None (pas de restriction, prod inchangée).
  - PARTITION   : input/hidden/output sont disjoints ET leur union = TOUS les nœuds réels mappés.
  - spécificité : chaque groupe marque exactement le bon nombre de nœuds (I, H, O) aux bonnes positions.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import numpy as np

from src.agents.mamba_agent import MambaAgent, MambaBatchModel, _dream_node_group_mask


def _batch(n=4, seed=0):
    np.random.seed(seed)
    agents = [MambaAgent() for _ in range(n)]
    m = MambaBatchModel(agents)
    return m


def test_all_is_noop_none():
    """group='all' -> None : aucune restriction, chemin historique intact."""
    m = _batch()
    assert _dream_node_group_mask(m.agents, m.mappings, m.max_N, "all") is None


def test_unknown_group_raises():
    """Un groupe inconnu doit LEVER, pas masquer silencieusement tout à zéro (= bruit éteint muet)."""
    m = _batch()
    try:
        _dream_node_group_mask(m.agents, m.mappings, m.max_N, "midbrain")
        assert False, "un groupe inconnu aurait dû lever ValueError"
    except ValueError:
        pass


def test_groups_partition_real_nodes_exactly():
    """PARTITION : input/hidden/output disjoints, et leur union = TOUS les nœuds réels mappés (pas le
    padding). Une fuite ou un recouvrement attribuerait l'effet de DREAM-006 au mauvais registre."""
    m = _batch()
    mi = _dream_node_group_mask(m.agents, m.mappings, m.max_N, "input")
    mh = _dream_node_group_mask(m.agents, m.mappings, m.max_N, "hidden")
    mo = _dream_node_group_mask(m.agents, m.mappings, m.max_N, "output")
    for i, a in enumerate(m.agents):
        # disjoints : aucun nœud dans deux groupes
        assert np.all(mi[i] + mh[i] + mo[i] <= 1.0), f"agent {i} : groupes non disjoints"
        # union = exactement les nœuds réels (positions mappées), pas le padding
        real = np.zeros(m.max_N, dtype=np.float32)
        real[m.mappings[i][:a.genome.num_nodes]] = 1.0
        assert np.array_equal(mi[i] + mh[i] + mo[i], real), f"agent {i} : union != nœuds réels"


def test_group_sizes_match_genome_counts():
    """Spécificité : chaque groupe marque exactement I / H / O nœuds (comptes du génome)."""
    m = _batch()
    for i, a in enumerate(m.agents):
        I_i, O_i, N_i = a.genome.num_inputs, a.genome.num_outputs, a.genome.num_nodes
        mi = _dream_node_group_mask(m.agents, m.mappings, m.max_N, "input")[i]
        mh = _dream_node_group_mask(m.agents, m.mappings, m.max_N, "hidden")[i]
        mo = _dream_node_group_mask(m.agents, m.mappings, m.max_N, "output")[i]
        assert int(mi.sum()) == I_i
        assert int(mo.sum()) == O_i
        assert int(mh.sum()) == N_i - I_i - O_i


def test_seam_default_is_all():
    """Le flag par défaut est 'all' -> prod strictement inchangée par l'ajout du seam."""
    assert MambaBatchModel.DREAM_NOISE_GROUP == "all"
