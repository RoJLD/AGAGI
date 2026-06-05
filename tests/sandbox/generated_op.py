import numpy as np

def new_activation(x: np.ndarray) -> np.ndarray:
    """
    Auto-generated Swish activation function.
    Formula: x * sigmoid(x)
    """
    # Safe sigmoid to avoid overflow
    sigmoid = np.where(x >= 0, 
                       1 / (1 + np.exp(-x)), 
                       np.exp(x) / (1 + np.exp(x)))
    return x * sigmoid
