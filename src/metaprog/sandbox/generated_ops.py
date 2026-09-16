import numpy as np

def custom_activation(x):
    # Swish activation : f(x) = x * sigmoid(x)
    # Excellente pour contrer la disparition du gradient tout en gardant une non-linéarité
    return x * (1.0 / (1.0 + np.exp(-x)))
