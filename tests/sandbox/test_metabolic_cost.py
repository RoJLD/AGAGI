import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.environments.config import WorldConfig


def test_metabolic_cost_coef_defaults_to_zero():
    # Non-régression : par défaut, aucun coût métabolique (comportement historique).
    config = WorldConfig()
    assert config.metabolic_cost_coef == 0.0
