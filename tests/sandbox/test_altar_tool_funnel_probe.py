# tests/sandbox/test_altar_tool_funnel_probe.py
import glob
import json

import pytest

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


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.altar_tool_funnel_probe as af
    monkeypatch.setattr(af, "run_era_funnel",
                        lambda *a, **k: [{"age": 12, "preys_eaten": 2, "spears_crafted": 1,
                                          "mammoth_kills": 0, "altars_solved": 0}])
    monkeypatch.setattr(af.async_logger, "start", lambda: None)
    monkeypatch.setattr(af.async_logger, "stop", lambda: None)
    monkeypatch.setattr(af, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("AF_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = af.main()
    assert result["verdict_funnel"] == "GAP_USAGE"      # craft=1.0, apex=0.0
    assert result["verdict_autel"] == "AUTEL_MORT"
    files = glob.glob(str(tmp_path / "results" / "altar_tool_funnel_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict_funnel"] == "GAP_USAGE"
    assert "commit" in data and "git_dirty" in data


@pytest.mark.slow
def test_run_era_funnel_smoke_all_agents_altar_dead(monkeypatch):
    """Smoke biosphère : 1 seed, ticks courts. Vérifie les 5 champs, la couverture vivants+morts,
    ET que l'autel est mort en conditions réelles (altars_solved jamais >0)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.altar_tool_funnel_probe import run_era_funnel
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        agents = run_era_funnel(0, 0.25, 3.0, num_agents=20, max_ticks=40, shared_db=db)
    finally:
        async_logger.stop()
    assert len(agents) >= 1
    a0 = agents[0]
    assert set(a0) == {"age", "preys_eaten", "spears_crafted", "mammoth_kills", "altars_solved"}
    assert max(a["altars_solved"] for a in agents) == 0   # autel mort, confirmé empiriquement
