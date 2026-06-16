# tests/test_sandbox.py
from backend.app.services.sandbox_service import SandboxService


def test_status_idle_when_nothing_running():
    svc = SandboxService()
    st = svc.get_status()
    assert st["running"] is False and st["pid"] is None


def test_stop_when_idle_is_graceful():
    svc = SandboxService()
    res = svc.stop()
    assert res["status"] == "success"
    assert res["message"] == "Aucune expérimentation en cours"


def test_start_without_script_errors():
    svc = SandboxService()
    res = svc.start({})
    assert res["status"] == "error" and "script principal" in res["message"]


def test_start_missing_script_errors():
    svc = SandboxService()
    res = svc.start({"script_name": "__does_not_exist__.py"})
    assert res["status"] == "error" and "introuvable" in res["message"]


def test_logs_deque_roundtrip():
    svc = SandboxService()
    assert svc.get_logs() == []
    svc._logs.append("ligne 1")
    assert svc.get_logs() == ["ligne 1"]


def test_available_scripts_lists_python_files():
    svc = SandboxService()
    scripts = svc.get_available_scripts()
    assert isinstance(scripts, list) and any(s.endswith(".py") for s in scripts)
