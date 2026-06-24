from tools.dream_causal_probe import dose_response_verdict


def test_dose_response_benefique_when_survival_rises_with_K():
    per_arm = {"off": [0.10, 0.10, 0.10, 0.10, 0.10],
               1: [0.12, 0.12, 0.12, 0.12, 0.12],
               4: [0.16, 0.16, 0.16, 0.16, 0.16],
               8: [0.20, 0.20, 0.20, 0.20, 0.20]}     # K8/off = 2.0 partout
    v = dose_response_verdict(per_arm)
    assert v["verdict"] == "CAUSE_BENEFIQUE"
    assert v["ratio"] > 1.0 and v["ratios_par_K"]["8"] > v["ratios_par_K"]["1"]


def test_dose_response_nuisible_when_survival_falls_with_K():
    per_arm = {"off": [0.20]*5, 1: [0.18]*5, 4: [0.14]*5, 8: [0.10]*5}
    assert dose_response_verdict(per_arm)["verdict"] == "CAUSE_NUISIBLE"


def test_dose_response_neutre_when_flat():
    per_arm = {"off": [0.15]*5, 1: [0.15]*5, 4: [0.151]*5, 8: [0.149]*5}
    assert dose_response_verdict(per_arm)["verdict"] == "NEUTRE"
    assert dose_response_verdict({})["verdict"] == "NEUTRE"


import os
import pytest


@pytest.mark.slow
def test_run_causal_smoke_resets_flag(monkeypatch):
    """Smoke biosphère : 1 seed, ks=(1,) -> forme du retour ET FORCE_DREAM remis à None après."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from src.agents.mamba_agent import MambaBatchModel
    from tools.dream_causal_probe import run_causal
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_causal([0], "stoneage", num_agents=20, max_ticks=40, shared_db=db, ks=(1,))
    finally:
        async_logger.stop()
    assert MambaBatchModel.FORCE_DREAM is None          # reset garanti (try/finally)
    assert "verdict" in res and set(res["per_arm"]) == {"off", "1"}


import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dream_causal_probe as dc
    monkeypatch.setattr(dc, "run_causal", lambda *a, **k: {
        "ratio": 1.5, "sign_p": 0.05, "n_favorable": 5, "n": 5, "verdict": "CAUSE_BENEFIQUE",
        "ratios_par_K": {"1": 1.1, "4": 1.3, "8": 1.5},
        "per_arm": {"off": [0.1], "1": [0.11], "4": [0.13], "8": [0.15]},
        "config": {"target": "stoneage", "seeds": [0], "ks": [1, 4, 8]}})
    monkeypatch.setattr(dc.async_logger, "start", lambda: None)
    monkeypatch.setattr(dc.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dc, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DC_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dc.main()
    assert result["verdict"] == "CAUSE_BENEFIQUE"
    files = glob.glob(str(tmp_path / "results" / "dream_causal_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict"] == "CAUSE_BENEFIQUE"
    assert "commit" in data and "git_dirty" in data
