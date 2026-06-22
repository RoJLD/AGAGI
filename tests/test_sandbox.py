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
    # Un script inexistant n'est pas dans la whitelist -> rejete avant la garde isfile (durcissement C4)
    res = svc.start({"script_name": "__does_not_exist__.py"})
    assert res["status"] == "error" and "autoris" in res["message"].lower()


def test_logs_deque_roundtrip():
    svc = SandboxService()
    assert svc.get_logs() == []
    svc._logs.append("ligne 1")
    assert svc.get_logs() == ["ligne 1"]


def test_available_scripts_lists_python_files():
    svc = SandboxService()
    scripts = svc.get_available_scripts()
    assert isinstance(scripts, list) and any(s.endswith(".py") for s in scripts)


def test_is_allowed_script_accepts_known_rejects_traversal():
    svc = SandboxService()
    assert svc._is_allowed_script("main_biosphere.py") is True
    assert svc._is_allowed_script("../../evil.py") is False
    assert svc._is_allowed_script("__inconnu__.py") is False
    assert svc._is_allowed_script("main_biosphere.txt") is False
    assert svc._is_allowed_script("") is False


def test_start_rejects_unauthorized_script_without_launching():
    svc = SandboxService()
    res = svc.start({"script_name": "../../x.py"})
    assert res["status"] == "error" and "autoris" in res["message"].lower()
    assert svc.get_status()["running"] is False
