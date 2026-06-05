import pytest
import numpy as np
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import Genome

def test_mamba_agent_v17_dimensions():
    # Test initialization
    agent = MambaAgent(num_inputs=45, num_outputs=65, num_nodes=96)
    
    assert agent.genome.num_inputs == 45
    assert agent.genome.num_outputs == 65
    assert agent.genome.num_nodes == 96
    
    # Test internal state shapes
    assert agent.attention_mask.shape == (45,)
    assert agent.explicit_memory.shape == (2,)
    
    # Test forward pass with dummy observation
    # observation size must be 43 since explicit memory is 2 and total inputs is 45
    obs = np.random.randn(43).astype(np.float32)
    
    try:
        logits = agent.forward(obs)
    except Exception as e:
        pytest.fail(f"Forward pass failed with exception: {e}")
        
    assert logits.shape == (65,)
    
    # Check that attention mask and explicit memory are correctly extracted
    # attention mask should be updated to size 45
    assert agent.attention_mask.shape == (45,)
    # explicit memory should be updated to size 2
    assert agent.explicit_memory.shape == (2,)

def test_mamba_agent_from_genome():
    # Test the upgrade functionality from old genome
    old_genome = Genome(
        W=np.random.randn(96, 96).astype(np.float32) * 0.1,
        num_inputs=38,
        num_outputs=65
    )
    
    agent = MambaAgent(num_inputs=45, num_outputs=65, num_nodes=96)
    agent.from_genome(old_genome)
    
    # Should be upgraded to 45
    assert agent.genome.num_inputs == 45
    assert agent.genome.num_outputs == 65
    assert agent.attention_mask.shape == (45,)
    assert agent.explicit_memory.shape == (2,)
