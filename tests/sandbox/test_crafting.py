"""
Tests for the crafting environment system.

Version: V13
"""

import pytest
from src.environments.crafting import attempt_combine, ITEM_REGISTRY, BLUEPRINTS

def test_attempt_combine_success():
    # Test order independence
    assert attempt_combine(["rock_small", "rock_medium"]) == "sparks"
    assert attempt_combine(["rock_medium", "rock_small"]) == "sparks"
    
    # Test exact match
    assert attempt_combine(["stick_long", "rock_medium", "stick_long"]) == "spear"

def test_attempt_combine_failure():
    # Invalid combinations
    assert attempt_combine(["rock_small"]) is None
    assert attempt_combine(["rock_large", "stick_long"]) is None
    
    # Empty list
    assert attempt_combine([]) is None

def test_item_registry():
    # Verify expected items exist
    assert "rock_small" in ITEM_REGISTRY
    assert ITEM_REGISTRY["rock_small"].poids == 0.5
    assert ITEM_REGISTRY["spear"].type == "spear"

def test_blueprints_pre_sorted():
    # Ensure keys are sorted in the blueprints
    for key in BLUEPRINTS.keys():
        assert tuple(sorted(key)) == key
