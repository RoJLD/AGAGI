"""P2.82 (2026-09-23) — un skip levé au MAUVAIS NIVEAU devient un verdict.

Mesuré par la suite de nuit du PM sous le bail `kuzu` de P4.16, reproduit (4 failed en 2,7 s) : (a) un test qui
prend `hold("kuzu")` LUI-MÊME sans porter d'indice de monde n'est pas sauté par la garde de collecte et
`ResourceBusy` devient FAIL ; (b) le `Skipped` du filet runtime levé DANS une app ASGI est rendu
« RuntimeError: No response returned » par Starlette = FAIL. Deux gardes, chacune avec son contre-exemple :
la PRISE de bail par un test sous détenteur étranger devient un skip nommant le détenteur (hook
`pytest_runtest_call` de `tests/conftest.py`) ; les tests backend qui servent un monde prennent la fixture
`sans_bail_etranger` (le skip se décide dans le test, jamais dans le code servi).

⚠️ Ces contre-exemples ne rougissent QUE bail tenu (classe E12 côté tests : une suite lancée machine au repos ne
les voit jamais). Ils s'exécutent donc sous un DÉTENTEUR FACTICE lancé par le test lui-même (sous-processus qui
tient `kuzu` 120 s). ⚠️ P2.165 (2026-10-13) : ce factice tenait le VRAI bail, dans le dossier commun à toute la
flotte — il sautait les tests de monde des autres sessions et pouvait refuser un vrai run. Il tient désormais un bail
PRIVÉ (`tmp_path`), et les sessions imbriquées y sont redirigées ; le détenteur réel éventuel n'est plus consulté.
Le dossier étant le nôtre, un factice invisible ÉCHOUE — jamais un vert fabriqué, jamais un saut non plus.
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


# P2.165 (2026-10-13) — le détenteur factice tient un bail PRIVÉ, jamais celui de la flotte. Avant, il prenait
# `hold("kuzu")` dans `runs/leases` de l'arbre PRINCIPAL (commun à tous les worktrees, P2.69 i) : pendant ses 120 s,
# les tests de monde de TOUTE autre session étaient sautés (lisibles comme des verts, face E4) et un vrai run qui
# prenait `kuzu` recevait ResourceBusy ; tué par la fixture, il laissait un bail ORPHELIN (mesuré le 2026-09-29 :
# `kuzu.json`, pid 3660, réapé par `doctor --kill`). Le dossier privé vit sous `tmp_path` ; la session imbriquée y est
# redirigée par le greffon ci-dessous, et CE processus par monkeypatch — même code de garde, autre répertoire.
_GREFFON_BAILS_PRIVES = '''"""Greffon pytest de test_lease_skip_guard.py (P2.165) : redirige le dossier de bails vers AGAGI_TEST_BAILS_PRIVES."""
import os
from pathlib import Path

from tools.jobs import lease as _lease

_lease.DEFAULT_LEASES_DIR = Path(os.environ["AGAGI_TEST_BAILS_PRIVES"])
'''


def _session_privee(tmp_path, prive):
    """Les arguments et l'environnement d'une session pytest imbriquée dont les bails vivent dans `prive`."""
    greffons = tmp_path / "greffons"
    greffons.mkdir(exist_ok=True)
    (greffons / "bails_prives_p2165.py").write_text(_GREFFON_BAILS_PRIVES, encoding="utf-8")
    pp = os.pathsep.join([str(greffons)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else []))
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=pp, AGAGI_TEST_BAILS_PRIVES=str(prive))
    return ["-p", "bails_prives_p2165"], env


@pytest.fixture
def detenteur_etranger(tmp_path, monkeypatch):
    """Un détenteur ÉTRANGER de `kuzu` pendant le test, dans un dossier de bails PRIVÉ (P2.165) : un sous-processus
    enfant qui le tient 120 s. Le dossier étant le nôtre, un factice invisible est un DÉFAUT du dispositif : il
    ÉCHOUE, il ne saute pas. Rend le dossier, le propriétaire, le pid et la session imbriquée qui les voit."""
    from types import SimpleNamespace
    from tools.jobs import lease
    c = _conftest()
    prive = tmp_path / "bails_prives"
    prive.mkdir()
    owner = f"fake-holder-p282-{os.getpid()}-{int(time.time() * 1000) % 10**6}"
    script = tmp_path / "fake_holder.py"
    script.write_text(
        "import sys, time\nsys.path.insert(0, %r)\nfrom tools.jobs.run import hold\n"
        "with hold('kuzu', owner=%r, ttl_s=120, leases_dir=%r):\n    time.sleep(120)\n" % (_ROOT, owner, str(prive)),
        encoding="utf-8")
    commun = lease._dir(None)                                      # celui de la FLOTTE, résolu AVANT la redirection
    monkeypatch.setattr(lease, "DEFAULT_LEASES_DIR", prive)        # CE processus lit le dossier privé
    journal = tmp_path / "fake_holder.err"
    with open(journal, "wb") as err:
        proc = subprocess.Popen([sys.executable, str(script)], cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=err)
    try:
        deadline = time.time() + 15.0
        while time.time() < deadline and not c._foreign_kuzu_holder():
            if proc.poll() is not None:
                break
            time.sleep(0.5)
        assert c._foreign_kuzu_holder(), ("détenteur factice invisible dans SON dossier de bails (code "
                                          f"{proc.poll()}) : {journal.read_text(encoding='utf-8', errors='replace')[-800:]}")
        args, env = _session_privee(tmp_path, prive)
        yield SimpleNamespace(prive=prive, commun=commun, owner=owner, pid=proc.pid, args=args, env=env)
    finally:
        proc.kill()
        proc.wait(timeout=10)


def _nested_pytest(target, k=None, bail=None, extra=()):
    """Une session pytest imbriquée ; sous `bail` (la fixture), ses bails vivent dans le dossier privé."""
    cmd = [sys.executable, "-m", "pytest", target, "-q", "-p", "no:cacheprovider", "-rs", *extra]
    if k:
        cmd += ["-k", k]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if bail is not None:
        cmd += bail.args
        env = bail.env
    r = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=600)
    lines = [l for l in r.stdout.split("\n") if l.strip()]
    return r.returncode, (lines[-1] if lines else "") + "\n" + r.stdout[-3000:] + r.stderr[-1500:]


def test_P2_165_le_detenteur_factice_tient_SON_bail_et_JAMAIS_celui_de_la_flotte(detenteur_etranger):
    """Contrôle positif PUIS spécificité, pendant que le factice tient : le bail est dans le dossier privé (sinon
    « absent du commun » ne prouverait rien), et le dossier de la flotte ne porte ni son propriétaire ni son pid."""
    from tools.jobs import lease
    b = detenteur_etranger
    prives = lease.read_all(leases_dir=b.prive)
    assert any(l.owner == b.owner and l.pid == b.pid for l in prives), [(l.owner, l.pid) for l in prives]
    assert b.commun != b.prive and b.commun.name == "leases", (b.commun, b.prive)   # le commun est bien l'autre
    communs = lease.read_all(leases_dir=b.commun)
    assert not any(l.owner == b.owner or l.pid == b.pid for l in communs), \
        f"le factice a écrit dans le dossier de la FLOTTE {b.commun} : {[(l.owner, l.pid) for l in communs]}"


def test_a_test_that_takes_the_lease_itself_is_SKIPPED_not_FAILED_end_to_end(detenteur_etranger):
    """(a) `test_s2_ablation_real_path.py` prend `hold("kuzu")` à la l.74, sans indice de monde : avant la
    garde, ResourceBusy = FAILED ; avec, SKIPPED nommant le détenteur. Depuis P2.165 : le détenteur est dans le
    dossier PRIVÉ, et la raison du saut doit nommer CE détenteur-là."""
    code, out = _nested_pytest("tests/sandbox/test_s2_ablation_real_path.py", k="AVEUGLE", bail=detenteur_etranger)
    assert "failed" not in out.split("\n")[0], out
    assert "1 skipped" in out.split("\n")[0] and code == 0, out
    assert detenteur_etranger.owner in out, out


def test_backend_tests_serving_a_world_are_SKIPPED_not_FAILED_under_a_foreign_holder(detenteur_etranger):
    """(b) `test_flatland_runs_crud` construit un monde DANS l'app ASGI : le Skipped du filet runtime
    traversait Starlette (RuntimeError = FAILED) ; la fixture `sans_bail_etranger` décide le skip AVANT."""
    code, out = _nested_pytest("tests/test_backend.py", k="test_flatland_runs_crud or test_ws_flatland_run_id_streams_frames",
                               bail=detenteur_etranger)
    assert "failed" not in out.split("\n")[0], out
    assert "2 skipped" in out.split("\n")[0] and code == 0, out
    assert detenteur_etranger.owner in out, out


_SONDE_FILET = '''"""Greffon pytest de test_lease_skip_guard.py (P2.165) : le constructeur de Biosphere3D, au début et à la FIN de
la session — c'est lui qui décide si un test de monde lancé après le fichier testé est sauté."""
import json
import os

_ETAT = {}


def pytest_sessionstart(session):
    from src.worlds.world_1_stoneage import Biosphere3D
    _ETAT["vierge"] = Biosphere3D.__init__


def pytest_sessionfinish(session, exitstatus):
    from src.worlds.world_1_stoneage import Biosphere3D
    f = Biosphere3D.__init__
    with open(os.environ["SONDE_FILET_P2165"], "w", encoding="utf-8") as fh:
        json.dump({"vierge": f is _ETAT.get("vierge"), "filet": bool(getattr(f, "_lease_net", False)),
                   "qualname": getattr(f, "__qualname__", "?")}, fh)
'''


def test_P2_165_test_lease_guard_ne_laisse_PAS_le_FILET_arme_apres_lui_en_session_reelle(tmp_path):
    """La fuite de P2.113 (d), mesurée en session RÉELLE : `tests/sandbox/test_lease_guard.py` lancé par pytest, avec
    son vrai conftest, sous un dossier de bails privé et VIDE (aucun détenteur réel ne peut armer le filet
    légitimement). À la fin de la session, `Biosphere3D.__init__` doit être celui du début : sinon tout test de monde
    collecté après ce fichier est SAUTÉ, et dans une app ASGI il devient le rouge « pid=4242 » de test_backend."""
    import json
    prive = tmp_path / "bails_vides"
    prive.mkdir()
    args, env = _session_privee(tmp_path, prive)
    (tmp_path / "greffons" / "sonde_filet_p2165.py").write_text(_SONDE_FILET, encoding="utf-8")
    sortie = tmp_path / "filet.json"
    env = dict(env, SONDE_FILET_P2165=str(sortie))
    cmd = [sys.executable, "-m", "pytest", "tests/sandbox/test_lease_guard.py", "-q", "-p", "no:cacheprovider",
           *args, "-p", "sonde_filet_p2165"]
    r = subprocess.run(cmd, cwd=_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                       timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-1500:]
    vu = json.loads(sortie.read_text(encoding="utf-8"))
    assert vu["vierge"] and not vu["filet"], f"filet laissé armé après test_lease_guard.py : {vu}"


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
