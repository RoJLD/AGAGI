# tests/sandbox/test_curriculum_transfer.py
from tools.curriculum_transfer import compute_transfer_verdict, _sign_test_p
from src.curriculum.runner import EraResult, GraduationConfig
from tools.curriculum_transfer import run_transfer_experiment


def test_sign_test_p_extremes():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1          # tous du même côté -> significatif
    assert _sign_test_p(3, 6) == 1.0         # 50/50 -> p=1
    assert 0.0 <= _sign_test_p(4, 5) <= 1.0


def test_verdict_transfere_when_ratios_above_one():
    v = compute_transfer_verdict([1.5, 1.4, 1.6, 1.3, 1.5])
    assert v["verdict"] == "TRANSFERE"
    assert v["n_favorable"] == 5 and v["n"] == 5
    assert v["median_ratio"] > 1.0


def test_verdict_nuit_when_ratios_below_one():
    v = compute_transfer_verdict([0.5, 0.6, 0.4, 0.5])
    assert v["verdict"] == "NUIT"


def test_verdict_neutre_in_band_or_mixed():
    assert compute_transfer_verdict([1.01, 0.99, 1.02, 0.98])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["sign_p"] == 1.0


def test_two_arms_equal_budget_and_pairing():
    """fake run_era_fn : compétence haute SI un ancêtre est hérité (bras curriculum atteint la cible
    avec transfert), basse sinon (bras tabula-rasa part de zéro). -> ratio > 1, TRANSFERE."""
    seen = []

    def fake(world_type, import_id, keep_mem):
        seen.append((world_type, import_id))
        comp = 0.8 if import_id is not None else 0.4
        return EraResult(competence=comp, champion_agent_id="champ1234")

    res = run_transfer_experiment(
        [0], ladder=["w_easy", "w_target"], target="w_target",
        grad_cfg=GraduationConfig(max_eras=2), run_era_fn=fake, manage_logger=False,
    )
    row = res["per_seed"][0]
    assert row["seed"] == 0
    assert row["C_curr"] == 0.8 and row["C_tabula"] == 0.4
    assert row["ratio"] == 0.8 / 0.4
    # budget égal : le bras tabula-rasa a tourné EXACTEMENT total_eras ères sur la cible.
    # Il est le SEUL à exécuter la cible sans ancêtre hérité (imp is None) : dans le bras
    # curriculum, le stage cible hérite toujours du champion promu (imp == "champ1234").
    tabula_calls = [w for (w, imp) in seen if imp is None and w == "w_target"]
    assert len(tabula_calls) == row["total_eras"]
    assert all(w == "w_target" for w in tabula_calls)
    assert res["verdict"] == "TRANSFERE"


def test_experiment_handles_zero_tabula_competence():
    def fake(world_type, import_id, keep_mem):
        comp = 0.5 if import_id is not None else 0.0   # tabula -> 0 -> pas de div par zéro
        return EraResult(competence=comp, champion_agent_id="c")
    res = run_transfer_experiment([7], ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1), run_era_fn=fake,
                                  manage_logger=False)
    assert res["per_seed"][0]["ratio"] < 1e9   # borné (max(C_tabula, 1e-6))


import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.curriculum_transfer as ct
    monkeypatch.setattr(ct, "run_transfer_experiment", lambda *a, **k: {
        "n": 1, "median_ratio": 2.0, "n_favorable": 1, "sign_p": 1.0, "verdict": "TRANSFERE",
        "per_seed": [{"seed": 0, "C_curr": 0.8, "C_tabula": 0.4, "total_eras": 2, "ratio": 2.0}],
        "config": {"ladder": ["a", "b"], "target": "b"}})
    monkeypatch.setenv("CT_SEEDS", "0")
    ct.main()
    files = glob.glob(str(tmp_path / "results" / "curriculum_transfer_*.json"))
    assert files, "fichier de provenance non écrit"
    data = json.loads(open(files[0], encoding="utf-8").read())
    assert data["data"]["verdict"] == "TRANSFERE"          # le résultat est sous data["data"]
    assert "commit" in data and "git_dirty" in data        # provenance ledger (Harness.save)
    assert data["seed"] == 0
