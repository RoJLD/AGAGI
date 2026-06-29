# tests/sandbox/test_tool_gate_calibration.py
from tools.tool_gate_calibration import gate_diagnostic


def test_control_hp_bare_hands_still_kills():
    """hp=100 (contrôle) : un pack mains-nues réaliste tue encore (reproduit l'actuel)."""
    d = gate_diagnostic(mammoth_hp=100.0, pack_size=5)
    assert d["bare_kills"] is True
    assert d["gate_valid"] is False


def test_gate_hp_blocks_bare_hands_but_not_spear():
    """hp=250 (gate) : le pack mains-nues échoue, le pack-lance réussit."""
    d = gate_diagnostic(mammoth_hp=250.0, pack_size=5)
    assert d["bare_kills"] is False
    assert d["spear_kills"] is True
    assert d["gate_valid"] is True


def test_break_pack_size_reported():
    """Le gate à hp=250 cède pour un pack mains-nues assez grand ; on le rapporte honnêtement.
    survivable_ticks=floor(100/50)=2 ; bare livre 2*P*10 ; casse ssi 20*P >= 250 -> P >= 13."""
    d = gate_diagnostic(mammoth_hp=250.0, pack_size=5)
    assert d["break_pack_size"] == 13
