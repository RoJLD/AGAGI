import numpy as np

from src.seed_ai.s2_stats import verdict_cognition_body


def _cond(center, n=12, spread=4.0):
    era = list(np.linspace(center - spread, center + spread, n))
    pooled = list(np.linspace(center - spread, center + spread, 4 * n))
    return {"survival": pooled, "era_survival": era, "life_score": pooled, "era_life": era}


def test_verdict_cognition():
    # C(45) >> B(12) ; B(12) ~ R(12) -> la POLITIQUE porte la survie -> COGNITION
    r = verdict_cognition_body(_cond(45), _cond(12), _cond(20), _cond(12))
    assert r["verdict"] == "COGNITION"
    assert r["policy_sig"] and not r["body_sig"]


def test_verdict_body():
    # C(45) ~ B(44) ; B(44) >> R(12) -> le CORPS/genome porte la survie -> BODY
    r = verdict_cognition_body(_cond(45), _cond(44), _cond(20), _cond(12))
    assert r["verdict"] == "BODY"
    assert r["body_sig"] and not r["policy_sig"]


def test_verdict_both():
    # C(45) >> B(28) >> R(12) -> corps ET politique -> BOTH
    r = verdict_cognition_body(_cond(45), _cond(28), _cond(20), _cond(12))
    assert r["verdict"] == "BOTH"
    assert r["policy_sig"] and r["body_sig"]


def test_verdict_neither():
    # C(20) ~ B(20) ~ R(20) -> aucun -> NEITHER
    r = verdict_cognition_body(_cond(20), _cond(20), _cond(20), _cond(20))
    assert r["verdict"] == "NEITHER"


def test_verdict_metric_life_score():
    # metric="life_score" utilise era_life/life_score ; ici life=survie synthetique -> meme verdict COGNITION
    r = verdict_cognition_body(_cond(45), _cond(12), _cond(20), _cond(12), metric="life_score")
    assert r["metric"] == "life_score"
    assert r["verdict"] == "COGNITION"


from tools.s2_cognition_body import cognition_body_study, CELLS


def test_cells_registered():
    assert set(CELLS) == {"champion", "champion_body", "random_genome", "random_action"}
    assert CELLS["champion"]["fresh_genome"] is False
    assert CELLS["champion_body"]["fresh_genome"] is False           # MÊME génome champion
    from src.agents.baseline_models import RandomActionBatchModel
    assert CELLS["champion_body"]["batch_model_cls"] is RandomActionBatchModel
    assert CELLS["champion"]["batch_model_cls"] is None              # moteur normal


def test_study_contract_with_stub():
    # stub run_fn : evite la biosphere. Rend une survie par cellule -> verdict structurel.
    surv = {"champion": _cond(45), "champion_body": _cond(12),
            "random_genome": _cond(20), "random_action": _cond(12)}
    def stub_run(world_cls, batch_model_cls, genome, seed, num_agents, max_ticks, n_eras):
        # associe la cellule par (batch_model_cls, genome is None)
        from src.agents.baseline_models import RandomActionBatchModel
        rnd = batch_model_cls is RandomActionBatchModel
        champ = genome is not None
        key = ("champion" if (champ and not rnd) else "champion_body" if (champ and rnd)
               else "random_genome" if (not champ and not rnd) else "random_action")
        return surv[key]
    rep = cognition_body_study(worlds=["stoneage"], seed=1, K=2, num_agents=4, max_ticks=10,
                               run_fn=stub_run, champion_genome="dummy")
    w = rep["worlds"]["stoneage"]
    assert w["verdict"] in {"COGNITION", "BODY", "BOTH", "NEITHER"}
    assert w["verdict"] == "COGNITION"                              # C(45)>>B(12), B(12)~R(12)
    assert set(w["survivals"]) == set(CELLS)
