from tools.dream_distress_probe import dream_rate, distress_split


def test_dream_rate_known_values():
    assert dream_rate({"age": 10, "total_dreams": 5}) == 0.5
    assert dream_rate({"age": 200, "total_dreams": 10}) == 0.05
    assert dream_rate({"age": 0, "total_dreams": 0}) == 0.0      # max(age,1) -> pas de div par zero
    assert dream_rate({"age": 0, "total_dreams": 3}) == 3.0      # age 0 -> denominateur 1


def test_distress_split_short_dream_more():
    """Court-vivants rêvent plus (taux haut) -> delta > 0 = signature de détresse."""
    stats = [
        {"age": 20, "total_dreams": 10},   # court (sous mediane), taux 0.5
        {"age": 25, "total_dreams": 12},   # court, taux 0.48
        {"age": 100, "total_dreams": 5},   # long, taux 0.05
        {"age": 120, "total_dreams": 6},   # long, taux 0.05
    ]
    out = distress_split(stats)
    assert out["n_short"] == 2 and out["n_long"] == 2
    assert out["rate_short"] > out["rate_long"]
    assert out["delta"] > 0


def test_distress_split_age_floor_excludes_tiny():
    """Le filtre age_floor écarte l'artefact petit-âge (mort à 2 ticks avec 1 rêve = taux 0.5)."""
    stats = [
        {"age": 2, "total_dreams": 1},     # ECARTE (age < 10)
        {"age": 50, "total_dreams": 5},
        {"age": 150, "total_dreams": 3},
    ]
    out = distress_split(stats, age_floor=10)
    assert out["n_short"] + out["n_long"] == 2     # l'agent age 2 est exclu


def test_distress_split_empty_no_crash():
    out = distress_split([], age_floor=10)
    assert out["rate_short"] == 0.0 and out["rate_long"] == 0.0 and out["delta"] == 0.0
    assert out["n_short"] == 0 and out["n_long"] == 0


from tools.dream_distress_probe import distress_verdict


def test_distress_verdict_three_cases():
    # court-vivants revent nettement plus, tous du meme cote -> DETRESSE (sign_p bas)
    assert distress_verdict([0.3, 0.4, 0.35, 0.3])["verdict"] == "DETRESSE"
    # long-vivants revent plus -> BENEFIQUE
    assert distress_verdict([-0.3, -0.4, -0.35, -0.3])["verdict"] == "BENEFIQUE"
    # mixte / centre sur 0 -> NEUTRE
    assert distress_verdict([0.1, -0.1, 0.05, -0.05])["verdict"] == "NEUTRE"
    assert distress_verdict([])["verdict"] == "NEUTRE"


def test_distress_verdict_reports_fields():
    v = distress_verdict([0.3, 0.4, 0.35, 0.3])
    assert v["n_favorable"] == 4 and "sign_p" in v and v["median_delta"] > 0
