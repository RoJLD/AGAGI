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


def test_n_floor_blocks_decoy():
    intact = [200.0] * 5                          # n=5 < 12
    ablated = [195.0] * 5                          # plat -> ratio ~1.03 <= 1.3 (decoy)
    v = ablation_verdict(intact, ablated)
    assert v["verdict"] == "INCONCLUSIVE"         # garde-fou : pas de NUL non plus sous n<12
    assert v["decoy"] is True                      # l'effet nul est là...
    assert v["n"] == 5                             # ...mais n insuffisant


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


# ---------------------------------------------------------------------------------------------------
# GARDE DE DÉGÉNÉRESCENCE (armée le 2026-07-21). Chaque cas rejoue une conclusion RÉELLE que l'absence
# de cette garde a produite — si un test tombe, la garde ne protège plus contre l'erreur qu'il encode.
# ---------------------------------------------------------------------------------------------------

def test_identical_arms_cannot_yield_a_null_verdict():
    """EDR-S2-007, cellule `shift0` : `_model_matrix(0,K)` est la matrice IDENTITÉ, donc les deux bras
    sont le MÊME calcul bit à bit — et le ratio 1.00 était publié comme condition de nécessité."""
    arm = [30.0, 28.0, 31.0] * 5
    v = ablation_verdict(arm, list(arm))
    assert v["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert v["degenerate"] and "IDENTIQUES" in v["why"]


def test_frozen_policy_cells_are_caught_by_the_identity_rule():
    """EDR-S2-004 : `fit_policy` part de `W = zeros` et n'accepte qu'en `sc > best` STRICT ; quand
    `score(W=0)` atteint déjà le cap, W ne quitte jamais l'init -> politique CONSTANTE, donc survie
    DÉTERMINISTE et identique sur tous les barreaux d'ablation. Mesuré : 3 cellules sur 4 ont
    |W| = 0.0000 exact, et le record présentait ce zéro comme un corroborant indépendant.

    Ce cas n'a PAS besoin d'une règle « variance nulle » dédiée — une telle règle sur-bloque, car un
    positif entièrement censuré est lui aussi constant (cf. test suivant)."""
    v = ablation_verdict([300.0] * 24, [300.0] * 24)
    assert v["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert "IDENTIQUES" in v["why"]


def test_declared_floor_blocks_the_warm002_verdict():
    """EDR-WARM-002 : bras intact à 5.0-7.2 ticks, plancher no-perception RÉEL 9.0 (mesuré par
    WARM-010) -> ratio 1.00 lu comme « paysage de fitness PLAT ». Avec le plancher déclaré, ce verdict
    devient impossible."""
    intact, ablated = [7.2] * 12, [7.0] * 12
    assert ablation_verdict(intact, ablated)["verdict"] == "X_DECOY"          # sans plancher : l'ancien nul
    v = ablation_verdict(intact, ablated, floor=9.0)
    assert v["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert "PLANCHER" in v["why"]


def test_a_censored_positive_is_kept_not_discarded():
    """LE CONTRÔLE QUI ÉVITE LA SUR-CORRECTION. Un bras intact au plafond avec un bras ablaté bas est
    un effet RÉEL, simplement sous-estimé (ratio = borne inférieure). La garde ne doit PAS le jeter,
    sinon elle détruirait la cellule positive de S2-007 (16.23) et l'oracle de S2-009 (21.05)."""
    v = ablation_verdict([200.0] * 12, [9.0] * 12, ceiling=200.0)
    assert v["verdict"] == "X_DEMANDED", "un positif censuré reste un positif"
    assert v["censored"] is True and v["degenerate"] is False


def test_a_healthy_null_is_still_a_null():
    """SPÉCIFICITÉ : sans dégénérescence, un vrai leurre doit rester X_DECOY. Sans ce bras, la garde
    pourrait tout convertir en INCONCLUSIVE et paraître « sûre » en ne mesurant plus rien."""
    v = ablation_verdict([30.0, 28.0, 31.0] * 4, [29.0, 27.0, 30.0] * 4, floor=9.0, ceiling=200.0)
    assert v["verdict"] == "X_DECOY" and v["degenerate"] is False
