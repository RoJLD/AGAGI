"""
tests/test_autotelic_curriculum_conductor.py — Validation du Curriculum Autotélique.
Vérifie la détection de maîtrise (Top) et le déclenchement de la complexification conjointe des mondes.
"""
import pytest
from src.worlds.autotelic_curriculum_conductor import AutotelicCurriculumConductor, AutotelicConfig


def test_autotelic_conductor_initialization():
    cfg = AutotelicConfig(mastery_threshold=0.85)
    conductor = AutotelicCurriculumConductor(cfg)
    assert conductor.complexity_level == 1
    assert conductor.consecutive_mastery_count == 0


def test_coevolution_scaling_trigger():
    cfg = AutotelicConfig(mastery_threshold=0.80, min_eras_before_scaling=2, difficulty_multiplier=1.2)
    conductor = AutotelicCurriculumConductor(cfg)

    # 1. Éra avec métriques modestes -> Pas d'élévation
    metrics_low = {"survival_rate": 0.5, "econ_volume": 5.0, "symbolic_acc": 0.4}
    res_1 = conductor.step_curriculum_cycle(metrics_low)
    assert res_1["is_top_level"] is False
    assert res_1["scaling_info"]["scaling_applied"] is False

    # 2. Deux ères consécutives au sommet -> Déclenchement de l'élévation
    metrics_top = {"survival_rate": 0.95, "econ_volume": 25.0, "symbolic_acc": 0.95}
    res_2 = conductor.step_curriculum_cycle(metrics_top)
    assert res_2["is_top_level"] is True
    assert res_2["scaling_info"]["scaling_applied"] is False

    res_3 = conductor.step_curriculum_cycle(metrics_top)
    assert res_3["is_top_level"] is True
    assert res_3["scaling_info"]["scaling_applied"] is True
    assert conductor.complexity_level == 2
    assert conductor.world_coevo.coevo_config.prey_base_speed > 1.0
