import numpy as np
import pytest
import importlib.util
import os

def test_generated_mutation():
    # Load the generated file
    file_path = os.path.join(os.path.dirname(__file__), "generated_ops.py")
    if not os.path.exists(file_path):
        pytest.skip("No generated_ops.py found")
        
    spec = importlib.util.spec_from_file_location("generated_ops", file_path)
    generated_ops = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generated_ops)
    
    assert hasattr(generated_ops, "custom_activation"), "custom_activation function not found"
    
    # Test with random numpy array
    x = np.random.randn(100, 100).astype(np.float32)
    
    try:
        y = generated_ops.custom_activation(x)
    except Exception as e:
        pytest.fail(f"Activation function crashed: {e}")
        
    assert y.shape == x.shape, "Shape mismatch"
    assert not np.any(np.isnan(y)), "NaN detected in output"
    assert not np.any(np.isinf(y)), "Inf detected in output"
