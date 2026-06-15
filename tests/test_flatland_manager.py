# tests/test_flatland_manager.py
import pytest
from backend.app.flatland_server import FlatlandServer


def test_server_applies_whitelisted_override():
    s = FlatlandServer(config_overrides={"size": 16, "num_altars": 2}, pop_size=2, label="t")
    assert s.cfg.size == 16 and s.cfg.num_altars == 2
    assert s.label == "t" and s.pop_size == 2


def test_server_rejects_unknown_override():
    with pytest.raises(ValueError):
        FlatlandServer(config_overrides={"evil_key": 1}, pop_size=2)


def test_server_default_config_unchanged():
    s = FlatlandServer(pop_size=2)
    assert s.cfg.size == 32 and s.cfg.num_altars == 5 and s.cfg.prey_mode == "semi"
    assert s.label is None
