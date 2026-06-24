import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.agents.mamba_agent import MambaAgent


def test_from_genome_default_flattens_historical():
    # Comportement historique (non-régression) : aplatit à 172 nœuds.
    g = MambaAgent(num_nodes=320).genome
    assert g.num_nodes == 320
    a = MambaAgent()
    a.from_genome(g)
    assert a.genome.num_nodes == 172


def test_from_genome_preserve_dims_keeps_architecture():
    # preserve_dims=True : garde l'architecture réelle du génome.
    g = MambaAgent(num_nodes=320).genome
    b = MambaAgent()
    b.from_genome(g, preserve_dims=True)
    assert b.genome.num_nodes == 320
    assert b.genome.num_inputs == g.num_inputs
    assert b.genome.num_outputs == g.num_outputs
