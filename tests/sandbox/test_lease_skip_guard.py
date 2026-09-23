"""P2.82 (2026-09-23) — un skip levé au MAUVAIS NIVEAU devient un verdict.

Mesuré par la suite de nuit du PM sous le bail `kuzu` de P4.16, reproduit (4 failed en 2,7 s) : (a) un test qui
prend `hold("kuzu")` LUI-MÊME sans porter d'indice de monde n'est pas sauté par la garde de collecte et
`ResourceBusy` devient FAIL ; (b) le `Skipped` du filet runtime levé DANS une app ASGI est rendu
« RuntimeError: No response returned » par Starlette = FAIL. Deux gardes, chacune avec son contre-exemple :
la PRISE de bail par un test sous détenteur étranger devient un skip nommant le détenteur (hook
`pytest_runtest_call` de `tests/conftest.py`) ; les tests backend qui servent un monde prennent la fixture
`sans_bail_etranger` (le skip se décide dans le test, jamais dans le code servi).

⚠️ Ces contre-exemples ne rougissent QUE bail tenu (classe E12 côté tests : une suite lancée machine au repos ne
les voit jamais). Ils s'exécutent donc sous le détenteur présent s'il y en a un, sinon sous un DÉTENTEUR FACTICE
lancé par le test lui-même (sous-processus qui tient `kuzu` 120 s) ; si ni l'un ni l'autre n'est mesurable, le
cas est SKIPPED avec sa raison — jamais un vert fabriqué.
"""
import importlib.util
import os
import subprocess
import sys
import time

import pytest

_LEASE_GUARD_EXEMPT = True          # ce fichier TESTE la garde : il ne doit pas être sauté par elle

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CONFTEST = os.path.join(_ROOT, "tests", "conftest.py")


def _conftest():
    """Le module conftest tel que pytest l'a chargé (fixtures et hooks vivants) — jamais une seconde copie."""
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f and os.path.abspath(f) == os.path.abspath(_CONFTEST):
            return m
    spec = importlib.util.spec_from_file_location("agagi_tests_conftest", _CONFTEST)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _drive(gen, exc):
    """Fait jouer à un hook wrapper (générateur) l'exception que pluggy lui lancerait au `yield`."""
    next(gen)
    try:
        gen.throw(exc)
    except StopIteration:
        return None


# --------------------------------------------------------------------------------------------------
# 1. La garde à la PRISE : ResourceBusy pendant l'appel du test -> Skipped nommant le détenteur.
# --------------------------------------------------------------------------------------------------


def test_ResourceBusy_raised_by_a_test_becomes_a_SKIP_naming_the_holder():
    from tools.jobs.lease import ResourceBusy
    c = _conftest()
    msg = "kuzu : détenue par pid=4242 owner='run-etranger' (bail vivant)"
    with pytest.raises(pytest.skip.Exception) as ei:
        _drive(c.pytest_runtest_call(item=None), ResourceBusy(msg))
    assert "run-etranger" in str(ei.value) and "4242" in str(ei.value)


def test_any_OTHER_exception_passes_through_the_guard_unchanged():
    """Spécificité : la garde ne convertit que ResourceBusy — un vrai échec reste un échec."""
    c = _conftest()
    with pytest.raises(ValueError):
        _drive(c.pytest_runtest_call(item=None), ValueError("un vrai rouge"))


# --------------------------------------------------------------------------------------------------
# 2. Bout en bout, sous détenteur (présent ou factice) : SKIPPED, jamais FAILED.
# --------------------------------------------------------------------------------------------------


@pytest.fixture
def detenteur_etranger(tmp_path):
    """Garantit un détenteur ÉTRANGER de `kuzu` pendant le test : celui qui existe, sinon un factice
    (sous-processus enfant, 120 s, cwd = racine pour le même dossier de bails). Sans détenteur mesurable
    -> SKIP explicite, jamais un vert fabriqué."""
    c = _conftest()
    if c._foreign_kuzu_holder():
        yield "present"
        return
    script = tmp_path / "fake_holder.py"
    script.write_text(
        "import sys, time\nsys.path.insert(0, %r)\nfrom tools.jobs.run import hold\n"
        "with hold('kuzu', owner='fake-holder-p282', ttl_s=120):\n    time.sleep(120)\n" % _ROOT, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(script)], cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 15.0
        while time.time() < deadline and not c._foreign_kuzu_holder():
            if proc.poll() is not None:
                break
            time.sleep(0.5)
        if not c._foreign_kuzu_holder():
            pytest.skip("bail libre et détenteur factice non visible par le doctor : contrôle non mesurable")
        yield "factice"
    finally:
        proc.kill()
        proc.wait(timeout=10)


def _nested_pytest(target, k=None):
    cmd = [sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider", "-rs"]
    if k:
        cmd += ["-k", k]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=600)
    lines = [l for l in r.stdout.split("\n") if l.strip()]
    return r.returncode, (lines[-1] if lines else "") + "\n" + r.stdout[-3000:]


def test_a_test_that_takes_the_lease_itself_is_SKIPPED_not_FAILED_end_to_end(detenteur_etranger):
    """(a) `test_s2_ablation_real_path.py` prend `hold("kuzu")` à la l.74, sans indice de monde : avant la
    garde, ResourceBusy = FAILED ; avec, SKIPPED nommant le détenteur."""
    code, out = _nested_pytest("tests/sandbox/test_s2_ablation_real_path.py", k="AVEUGLE")
    assert "failed" not in out.split("\n")[0], out
    assert "1 skipped" in out.split("\n")[0] and code == 0, out


def test_backend_tests_serving_a_world_are_SKIPPED_not_FAILED_under_a_foreign_holder(detenteur_etranger):
    """(b) `test_flatland_runs_crud` construit un monde DANS l'app ASGI : le Skipped du filet runtime
    traversait Starlette (RuntimeError = FAILED) ; la fixture `sans_bail_etranger` décide le skip AVANT."""
    code, out = _nested_pytest("tests/test_backend.py", k="test_flatland_runs_crud or test_ws_flatland_run_id_streams_frames")
    assert "failed" not in out.split("\n")[0], out
    assert "2 skipped" in out.split("\n")[0] and code == 0, out


# --------------------------------------------------------------------------------------------------
# 3. La fixture au repos ne saute PAS (spécificité), et saute sous détenteur (réponse connue, sans monde).
# --------------------------------------------------------------------------------------------------


def test_sans_bail_etranger_decision_skips_only_when_a_foreign_holder_exists(monkeypatch):
    """La DÉCISION de la fixture, calibrée sans monde : au repos elle ne fait rien (spécificité), sous
    détenteur elle saute en le nommant."""
    c = _conftest()
    monkeypatch.setattr(c, "_foreign_kuzu_holder", lambda: None)
    c._skip_si_bail_etranger()                                          # au repos : rien
    monkeypatch.setattr(c, "_foreign_kuzu_holder", lambda: "run-etranger (pid=4242)")
    with pytest.raises(pytest.skip.Exception) as ei:
        c._skip_si_bail_etranger()
    assert "run-etranger" in str(ei.value)


def test_the_fixture_is_wired_to_the_decision(request, monkeypatch):
    """La fixture EXISTE et appelle la décision (une fixture absente était le RED de départ)."""
    c = _conftest()
    monkeypatch.setattr(c, "_foreign_kuzu_holder", lambda: None)
    assert request.getfixturevalue("sans_bail_etranger") is None
