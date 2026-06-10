"""Sandbox sécurisée (EDR 035) : le gate AST rejette le dangereux, accepte le sûr."""
from src.metaprog.secure_sandbox import validate_code, run_sandboxed

SAFE = "import numpy as np\n\ndef new_activation(x):\n    return np.tanh(x)\n"


def test_accepts_safe_numpy():
    ok, reason = validate_code(SAFE)
    assert ok, reason


def test_rejects_dangerous_imports():
    for bad in ("import os", "import subprocess", "from os import system",
                "import socket", "import shutil", "import importlib"):
        ok, _ = validate_code(bad + "\n")
        assert not ok, f"devrait rejeter: {bad}"


def test_rejects_capability_calls():
    for bad in ("exec('x')", "eval('1')", "__import__('os')",
                "open('f','w')", "getattr(x,'y')", "compile('1','','eval')"):
        ok, _ = validate_code(bad + "\n")
        assert not ok, f"devrait rejeter: {bad}"


def test_rejects_dunder_escape():
    # Évasion classique : ().__class__.__bases__[0].__subclasses__()
    ok, _ = validate_code("y = ().__class__.__bases__\n")
    assert not ok


def test_run_sandboxed_safe_passes():
    test_code = ("import numpy as np\n"
                 "assert new_activation(np.zeros(3)).shape == (3,)\n"
                 "print('ok')\n")
    ok, reason = run_sandboxed(SAFE, test_code)
    assert ok, reason


def test_run_sandboxed_blocks_malicious_before_exec():
    evil = ("import os\n"
            "os.system('echo pwned')\n"
            "def new_activation(x):\n    return x\n")
    ok, reason = run_sandboxed(evil, "print('x')\n")
    assert not ok and "AST gate" in reason   # bloqué AVANT toute exécution
