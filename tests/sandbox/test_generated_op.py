import numpy as np
import pytest
from generated_op import new_activation

def test_new_activation():
    x = np.array([-1.0, 0.0, 1.0])
    result = new_activation(x)
    assert result.shape == x.shape
    assert not np.isnan(result).any()
    assert not np.isinf(result).any()
