# tests/sandbox/test_altar_tool_funnel_probe.py
from tools.altar_tool_funnel_probe import funnel_verdict


def _ag(preys=0, spears=0, mammoth=0, altars=0, age=10):
    return {"preys_eaten": preys, "spears_crafted": spears, "mammoth_kills": mammoth,
            "altars_solved": altars, "age": age}


def test_funnel_gap_acquisition_when_no_craft():
    # 5 agents chassent mais aucun ne crafte -> frac_craft=0 < eps
    per_seed = {0: [_ag(preys=3) for _ in range(5)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_funnel"] == "GAP_ACQUISITION"
    assert v["verdict_autel"] == "AUTEL_MORT"
    assert v["frac_hunt"] == 1.0 and v["frac_craft"] == 0.0 and v["frac_apex"] == 0.0


def test_funnel_gap_usage_when_craft_but_no_mammoth():
    # 5 agents craftent (frac_craft=1.0) mais aucun ne tue le mammouth
    per_seed = {0: [_ag(preys=3, spears=2) for _ in range(5)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_funnel"] == "GAP_USAGE"
    assert v["frac_craft"] == 1.0 and v["frac_apex"] == 0.0
    assert v["total_spears"] == 10


def test_funnel_pathway_vivant_when_mammoth_killed():
    # au moins un agent tue le mammouth -> frac_apex > eps
    per_seed = {0: [_ag(preys=3, spears=2, mammoth=1)] + [_ag(preys=1) for _ in range(4)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_funnel"] == "PATHWAY_VIVANT"
    assert v["frac_apex"] == 0.2 and v["total_mammoth_kills"] == 1


def test_autel_vivant_when_any_solved():
    per_seed = {0: [_ag(altars=1)] + [_ag() for _ in range(4)]}
    v = funnel_verdict(per_seed)
    assert v["verdict_autel"] == "AUTEL_VIVANT" and v["altars_solved_max"] == 1


def test_funnel_empty_no_crash():
    v = funnel_verdict({})
    assert v["n_agents"] == 0 and v["verdict_autel"] == "AUTEL_MORT"
    assert v["verdict_funnel"] == "GAP_ACQUISITION" and v["par_seed"] == {}


def test_par_seed_carries_decomposition():
    per_seed = {0: [_ag(preys=2, spears=1)], 1: [_ag(preys=2, mammoth=1, spears=1)]}
    v = funnel_verdict(per_seed)
    assert set(v["par_seed"]) == {"0", "1"}
    assert v["par_seed"]["1"]["frac_apex"] == 1.0 and v["par_seed"]["0"]["frac_apex"] == 0.0
