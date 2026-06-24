from tools.dream_distress_probe import dream_rate


def test_dream_rate_known_values():
    assert dream_rate({"age": 10, "total_dreams": 5}) == 0.5
    assert dream_rate({"age": 200, "total_dreams": 10}) == 0.05
    assert dream_rate({"age": 0, "total_dreams": 0}) == 0.0      # max(age,1) -> pas de div par zero
    assert dream_rate({"age": 0, "total_dreams": 3}) == 3.0      # age 0 -> denominateur 1
