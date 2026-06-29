# tests/sandbox/test_mammoth_hp_knob.py
import pytest

from src.environments.config import WorldConfig


def test_mammoth_hp_default_is_100():
    """Non-régression : le défaut reste 100.0 (comportement historique)."""
    assert WorldConfig().mammoth_hp == 100.0


@pytest.mark.slow
def test_spawned_mammoth_uses_config_hp(monkeypatch):
    """Le Mammouth spawné lit config.mammoth_hp ; les autres proies sont inchangées."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.worlds.world_1_stoneage import Biosphere3D
    cfg = WorldConfig()
    cfg.mammoth_hp = 250.0
    world = Biosphere3D(config=cfg)   # __init__ appelle _spawn_preys() -> 1 Mammouth + 3 Lapins + ...
    mammoths = [p for p in world.preys if p["type"] == "Mammouth"]
    lapins = [p for p in world.preys if p["type"] == "Lapin"]
    assert mammoths and all(m["hp"] == 250.0 for m in mammoths)
    assert lapins and all(l["hp"] == 1.0 for l in lapins)  # Lapin inchangé (PreyConfig.hp=1.0)
