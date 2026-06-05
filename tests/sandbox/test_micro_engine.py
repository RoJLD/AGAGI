import numpy as np
import sys
import os

# Ensure src module is visible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.seed_ai.network import MicroEngine, MicroEngineConfig

def test_micro_engine_xor():
    """
    Validates that the MicroEngine can compute the non-linear XOR function
    using hardcoded weights (which will later be evolved by Phase 2).
    """
    engine = MicroEngine(MicroEngineConfig(max_nodes=10))
    
    # 0, 1: Inputs
    # 2, 3: Hidden layer
    # 4: Output
    engine.add_node(0, operation=0, is_input=True) # Input A
    engine.add_node(1, operation=0, is_input=True) # Input B
    
    # Hidden nodes use ReLU (op=1)
    engine.add_node(2, operation=1) 
    engine.add_node(3, operation=1)
    
    # Output node uses Sigmoid (op=2)
    engine.add_node(4, operation=2, is_output=True)
    
    # Set weights to solve XOR
    # Node 2 acts as OR: ReLU(A + B)
    engine.set_weight(0, 2, 1.0)
    engine.set_weight(1, 2, 1.0)
    engine.set_bias(2, 0.0)
    
    # Node 3 acts as AND: ReLU(A + B - 1.0)
    engine.set_weight(0, 3, 1.0)
    engine.set_weight(1, 3, 1.0)
    engine.set_bias(3, -1.0)
    
    # Node 4 takes OR (Node 2) and subtracts 2*AND (Node 3)
    # Sigmoid(OR - 2*AND - 0.5)
    engine.set_weight(2, 4, 1.0)
    engine.set_weight(3, 4, -2.0)
    engine.set_bias(4, -0.5)
    
    # Test cases
    cases = [
        ([0.0, 0.0], 0.0),
        ([0.0, 1.0], 1.0),
        ([1.0, 0.0], 1.0),
        ([1.0, 1.0], 0.0)
    ]
    
    for inputs, expected in cases:
        out = engine.forward(inputs, iterations=3)
        assert len(out) == 1

        prediction = 1.0 if out[0] > 0.5 else 0.0
        assert prediction == expected, f"Failed XOR for {inputs}. Expected {expected}, got {out[0]}"

def test_micro_engine_backward():
    """Validates that gradient descent allows MicroEngine to learn AND gate."""
    engine = MicroEngine(MicroEngineConfig(max_nodes=5))
    
    engine.add_node(0, operation=0, is_input=True) 
    engine.add_node(1, operation=0, is_input=True) 
    engine.add_node(2, operation=2, is_output=True) # Sigmoid output
    
    # Random small weights
    engine.set_weight(0, 2, 0.1)
    engine.set_weight(1, 2, -0.1)
    engine.set_bias(2, 0.0)
    
    cases = [
        ([0.0, 0.0], [0.0]),
        ([0.0, 1.0], [0.0]),
        ([1.0, 0.0], [0.0]),
        ([1.0, 1.0], [1.0])
    ]
    
    for epoch in range(100):
        total_loss = 0
        for inputs, targets in cases:
            loss = engine.backward(inputs, targets, learning_rate=0.5, iterations=1)
            total_loss += loss
            
        if total_loss < 0.05:
            break
            
    # Final check
    out = engine.forward([1.0, 1.0], iterations=1)
    assert out[0] > 0.5, f"Failed to learn AND. Expected >0.5, got {out[0]}"
