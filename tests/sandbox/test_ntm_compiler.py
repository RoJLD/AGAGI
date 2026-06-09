import sys
import os
import pytest
import numpy as np

# Adjust PYTHONPATH to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from src.metaprog.ntm_compiler import NTMProgramCompiler
from src.agents.mamba_agent import MambaAgent

def test_ntm_compiler_normal():
    # 1. Create a dummy agent
    agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
    agents = [agent]
    
    # 2. Setup NTM memory array: shape (1, 10, 5)
    # Slot 0: src=0.1 (maps to int(0.1*100)=10), dst=0.2 (maps to int(0.2*100)=20), weight=0.5 (scaled *5=2.5), unused=0.0, enable=1.0 (enabled)
    ntm_memory = np.zeros((1, 10, 5), dtype=np.float32)
    ntm_memory[0, 0] = [0.1, 0.2, 0.5, 0.0, 1.0]
    
    # Connection weights matrix
    W_batch = np.zeros((1, 96, 96), dtype=np.float32)
    
    # Compile and apply
    W_batch = NTMProgramCompiler.compile_and_apply(ntm_memory, W_batch, agents)
    
    # Assert weight applied at W_batch[0, 10, 20]
    assert W_batch[0, 10, 20] == 2.5

def test_ntm_compiler_bounds():
    agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
    agents = [agent]
    
    # Index larger than num_nodes (96)
    # Slot 0: src=1.5 (maps to 150 -> clipped to 95), dst=0.5 (maps to 50), weight=0.8, unused=0.0, enable=1.0
    ntm_memory = np.zeros((1, 10, 5), dtype=np.float32)
    ntm_memory[0, 0] = [1.5, 0.5, 0.8, 0.0, 1.0]
    
    W_batch = np.zeros((1, 96, 96), dtype=np.float32)
    W_batch = NTMProgramCompiler.compile_and_apply(ntm_memory, W_batch, agents)
    
    # Assert weight applied to clipped index 95 instead of throwing index error
    assert W_batch[0, 95, 50] == 4.0

def test_ntm_compiler_disabled():
    agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
    agents = [agent]
    
    # Slot 0 is disabled (enable <= 0.0)
    ntm_memory = np.zeros((1, 10, 5), dtype=np.float32)
    ntm_memory[0, 0] = [0.1, 0.2, 0.5, 0.0, -0.1]
    
    W_batch = np.zeros((1, 96, 96), dtype=np.float32)
    W_batch = NTMProgramCompiler.compile_and_apply(ntm_memory, W_batch, agents)
    
    # Assert weight NOT applied
    assert W_batch[0, 10, 20] == 0.0

def test_ntm_compiler_numerical_stability():
    agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
    agents = [agent]
    
    # Slot contains NaN and Inf
    ntm_memory = np.zeros((1, 10, 5), dtype=np.float32)
    ntm_memory[0, 0] = [np.nan, np.inf, np.nan, np.inf, np.nan]
    
    W_batch = np.zeros((1, 96, 96), dtype=np.float32)
    
    # Should not crash, and should return unchanged W_batch (or safe modifications)
    try:
        W_batch = NTMProgramCompiler.compile_and_apply(ntm_memory, W_batch, agents)
        assert True
    except Exception as e:
        pytest.fail(f"NTMProgramCompiler crashed on NaN/Inf: {e}")
