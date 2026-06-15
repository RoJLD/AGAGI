# tests/test_flatland_manager.py
import pytest
from backend.app.flatland_server import FlatlandServer


def test_server_applies_whitelisted_override():
    s = FlatlandServer(config_overrides={"size": 16, "num_altars": 2}, pop_size=2, label="t")
    assert s.cfg.size == 16 and s.cfg.num_altars == 2
    assert s.label == "t" and s.pop_size == 2


def test_server_rejects_unknown_override():
    with pytest.raises(ValueError):
        FlatlandServer(config_overrides={"evil_key": 1}, pop_size=2)


def test_mutation_rate_override_drives_real_nested_knob():
    """Régression: mutation_rate doit piloter le VRAI levier imbriqué
    (cfg.agent.mutation.weight_mutate_rate), pas créer un attribut plat mort.
    Sans ce mapping l'A/B exécuterait une évolution identique entre baseline et
    traitement (intervention sans effet, échec silencieux)."""
    s = FlatlandServer(config_overrides={"mutation_rate": 0.99}, pop_size=2)
    assert s.cfg.agent.mutation.weight_mutate_rate == 0.99
    # pas d'attribut plat fantôme
    assert not hasattr(s.cfg, "mutation_rate")
    # baseline inchangée (non-régression)
    base = FlatlandServer(pop_size=2)
    assert base.cfg.agent.mutation.weight_mutate_rate == 0.8


def test_server_default_config_unchanged():
    s = FlatlandServer(pop_size=2)
    assert s.cfg.size == 32 and s.cfg.num_altars == 5 and s.cfg.prey_mode == "semi"
    assert s.label is None


from backend.app.flatland_server import FlatlandManager, RunCapExceeded


def _mgr():
    return FlatlandManager(FlatlandServer(label="default", pop_size=2))


def test_manager_create_get_list():
    mgr = _mgr()
    rid = mgr.create_run(config_overrides={"size": 16}, pop_size=2, label="exp")
    assert mgr.get_run(rid).cfg.size == 16
    runs = mgr.list_runs()
    assert any(r["run_id"] == rid and r["label"] == "exp" and r["status"] == "idle" for r in runs)
    assert any(r["run_id"] == "default" for r in runs)


def test_manager_stop_run_and_default_preserved():
    mgr = _mgr()
    rid = mgr.create_run(pop_size=2)
    assert mgr.stop_run(rid) is True
    assert mgr.get_run(rid) is None
    assert mgr.stop_run("default") is False        # default non supprimable (legacy)
    assert mgr.stop_run("inconnu") is False


def test_manager_cap_enforced():
    mgr = _mgr()                                   # default = 1 run, cap = 4
    for _ in range(3):
        mgr.create_run(pop_size=2)
    with pytest.raises(RunCapExceeded):
        mgr.create_run(pop_size=2)
