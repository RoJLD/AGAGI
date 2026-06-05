import shutil
import subprocess
from pathlib import Path

import pytest


def test_frontend_build() -> None:
    npm_exec = shutil.which("npm") or shutil.which("npm.cmd")
    if npm_exec is None:
        pytest.skip("npm is not installed in the current environment")

    root = Path(__file__).resolve().parents[1] / "frontend"
    subprocess.run([npm_exec, "install"], cwd=root, check=True)
    subprocess.run([npm_exec, "run", "build"], cwd=root, check=True)
