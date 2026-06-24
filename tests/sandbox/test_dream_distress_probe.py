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
    assert distress_verdict([0.3, 0.4, 0.35, 0.3, 0.32])["verdict"] == "DETRESSE"
    # long-vivants revent plus -> BENEFIQUE
    assert distress_verdict([-0.3, -0.4, -0.35, -0.3, -0.32])["verdict"] == "BENEFIQUE"
    # mixte / centre sur 0 -> NEUTRE
    assert distress_verdict([0.1, -0.1, 0.05, -0.05])["verdict"] == "NEUTRE"
    assert distress_verdict([])["verdict"] == "NEUTRE"


def test_distress_verdict_reports_fields():
    v = distress_verdict([0.3, 0.4, 0.35, 0.3, 0.32])
    assert v["n_favorable"] == 5 and "sign_p" in v and v["median_delta"] > 0


def test_distress_verdict_zero_delta_removes_power():
    """Un delta nul est retiré du test de signe : k=4/n=4 -> sign_p=0.125 > 0.1 -> NEUTRE
    malgre une mediane positive (verrouille la frontiere 0.1 qui declenche la Phase 2)."""
    v = distress_verdict([0.3, 0.4, 0.35, 0.32, 0.0])
    assert v["median_delta"] > 0
    assert v["sign_p"] > 0.1
    assert v["verdict"] == "NEUTRE"


import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dream_distress_probe as dd
    monkeypatch.setattr(dd, "run_distress", lambda *a, **k: {
        "median_delta": 0.3, "n_favorable": 3, "sign_p": 0.05, "verdict": "DETRESSE",
        "per_seed": [{"seed": 0, "rate_short": 0.5, "rate_long": 0.2, "delta": 0.3,
                      "n_short": 5, "n_long": 5}],
        "config": {"target": "stoneage", "seeds": [0]}})
    monkeypatch.setattr(dd.async_logger, "start", lambda: None)
    monkeypatch.setattr(dd.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dd, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DD_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests de la session, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dd.main()
    assert result["verdict"] == "DETRESSE"
    files = glob.glob(str(tmp_path / "results" / "dream_distress_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict"] == "DETRESSE"
    assert "commit" in data and "git_dirty" in data
