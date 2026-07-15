import math
import statistics
from tools.demand_marker import ablation_verdict


def test_collapse_gives_demanded():
    intact = [200.0] * 12
    ablated = [40.0] * 12                      # effondrement 5x
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "X_DEMANDED"
    assert v["collapse"] is True
    assert math.isclose(v["ratio"], 5.0, rel_tol=1e-6)
    assert v["n"] == 12


def test_flat_gives_decoy():
    intact = [200.0] * 12
    ablated = [195.0] * 12                      # plat -> ratio ~1.03 < 1.3
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "X_DECOY"
    assert v["decoy"] is True


def test_n_floor_blocks_positive():
    intact = [200.0] * 5                         # n=5 < 12
    ablated = [40.0] * 5                          # effondrement franc MAIS sous-puissance
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "INCONCLUSIVE"        # garde-fou : pas de POSITIF sous n<12
    assert v["collapse"] is True                  # l'effet est là...
    assert v["n"] == 5                            # ...mais n insuffisant


def test_ratio_matches_legacy_proxy_formula():
    # non-régression : ablation_verdict doit reproduire EXACTEMENT le calcul historique
    # du proxy S2-001 : within = median(intact) / max(median(ablated), 1e-9)
    intact = [10.0, 30.0, 50.0, 70.0]            # median 40
    ablated = [5.0, 15.0, 25.0, 35.0]            # median 20
    legacy = statistics.median(intact) / max(statistics.median(ablated), 1e-9)
    v = ablation_verdict(intact, ablated)
    assert math.isclose(v["ratio"], legacy, rel_tol=1e-12)


def test_corroborant_passthrough():
    v = ablation_verdict([200.0] * 12, [40.0] * 12, weight_on_x=0.87)
    assert v["corroborant"] == 0.87
    v2 = ablation_verdict([200.0] * 12, [40.0] * 12)
    assert v2["corroborant"] is None
