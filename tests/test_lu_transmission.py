"""
Unit tests for LU Transmission Protocol.
Commandment 7: Validation Rigoureuse.
"""

import pytest
import numpy as np
from src.metaprog.lu_transmission import LUTransmissionProtocol, LUHumanTranslator

def test_transmission_informatique():
    vec = np.array([0.5, -0.5, 1.0], dtype=np.float32)
    b = LUTransmissionProtocol.transmit_informatique(vec)
    assert isinstance(b, bytes)
    assert len(b) > 0
    # Can we deserialize it?
    import io
    reconstructed = np.load(io.BytesIO(b))
    assert reconstructed.shape == (3,)
    # Float16 conversion implies slight precision loss, but it should be close
    np.testing.assert_allclose(reconstructed, vec, atol=1e-3)

def test_transmission_sonore():
    vec = np.random.randn(64)
    audio = LUTransmissionProtocol.transmit_sonore(vec)
    assert audio.shape == (16000,) # 1 second at 16kHz
    assert np.max(np.abs(audio)) <= 1.0 + 1e-5 # Normalized

def test_transmission_visuelle():
    vec = np.random.randn(64)
    img = LUTransmissionProtocol.transmit_visuel(vec, grid_size=8)
    assert img.shape == (8, 8)
    assert img.dtype == np.uint8
    assert np.max(img) <= 255
    assert np.min(img) >= 0

def test_human_translator():
    vec = np.array([1.0, 0.0, 0.0])
    res_fr = LUHumanTranslator.decode_to_human(vec, "FR")
    assert "LLM-FR" in res_fr
    assert "1.0000" in res_fr
