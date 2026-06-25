import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.agents.mamba_agent import MambaAgent


def test_from_genome_default_preserves_architecture():
    # DÉFAUT (depuis la bascule) : garde l'architecture réelle du génome (topologie évoluée préservée).
    g = MambaAgent(num_nodes=320).genome
    assert g.num_nodes == 320
    a = MambaAgent()
    a.from_genome(g)                                   # défaut = preserve_dims=True
    assert a.genome.num_nodes == 320
    assert a.genome.num_inputs == g.num_inputs
    assert a.genome.num_outputs == g.num_outputs


def test_from_genome_explicit_off_flattens_historical():
    # Escape-hatch : l'ancien comportement (aplatir à 172) reste atteignable via preserve_dims=False.
    g = MambaAgent(num_nodes=320).genome
    a = MambaAgent()
    a.from_genome(g, preserve_dims=False)
    assert a.genome.num_nodes == 172


def test_from_genome_preserve_dims_keeps_architecture():
    # preserve_dims=True explicite == défaut : garde l'architecture réelle du génome.
    g = MambaAgent(num_nodes=320).genome
    b = MambaAgent()
    b.from_genome(g, preserve_dims=True)
    assert b.genome.num_nodes == 320
    assert b.genome.num_inputs == g.num_inputs
    assert b.genome.num_outputs == g.num_outputs
