import numpy as np
from src.seed_ai.mutation import Genome, MutationConfig, apply_mutations
from src.seed_ai.evolution import crossover

def test_genome_mutation_genes():
    g = Genome(np.zeros((2, 2)), 1, 1)
    assert g.mutation_genes is not None
    assert len(g.mutation_genes) == 5
    assert g.mutation_genes[0] == 0.8
    
    g2 = g.clone()
    assert np.array_equal(g.mutation_genes, g2.mutation_genes)
    g2.mutation_genes[0] = 0.5
    assert g.mutation_genes[0] == 0.8  # Ensure deep copy

def test_crossover_mutation_genes():
    g1 = Genome(np.zeros((2, 2)), 1, 1)
    g1.mutation_genes = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    
    g2 = Genome(np.zeros((2, 2)), 1, 1)
    g2.mutation_genes = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
    
    child = crossover(g1, g2, 10.0, 5.0)
    
    # Child should have a mix of 0.0 and 1.0
    assert all(val in [0.0, 1.0] for val in child.mutation_genes)

def test_apply_mutations_meta():
    config = MutationConfig(meta_mutate_rate=1.0, meta_mutate_power=0.5)
    g = Genome(np.zeros((2, 2)), 1, 1)
    original_genes = g.mutation_genes.copy()
    
    mutated = apply_mutations(g, config)
    
    # Since meta_mutate_rate is 1.0, genes should have mutated
    assert not np.array_equal(original_genes, mutated.mutation_genes)
    # Check clipping
    assert 0.0 <= mutated.mutation_genes[0] <= 1.0
    assert mutated.mutation_genes[1] >= 0.01
