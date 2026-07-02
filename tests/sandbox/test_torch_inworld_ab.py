from tools.substrate_ab import compute_ab_verdict


def test_verdict_pure_on_synthetic_rows():
    rows = [{"diff": 0.1}, {"diff": 0.2}, {"diff": 0.15}]   # torch > legacy
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE"
    assert v["n"] == 3


def test_run_arm_smoke():
    # leger : ~2.4 s/step -> 4 ticks. Verifie la STRUCTURE du retour, pas le contenu du verdict.
    from tools.torch_inworld_ab import run_arm
    r = run_arm(use_torch=False, seed=0, ticks=4, n_agents=8)
    assert "survival" in r and r["ticks"] == 4 and 0.0 <= r["survival"] <= 1.0
