"""
src/metaprog/agent_vm_sandbox.py — Machine Virtuelle et Bac à Sable de Code Isolé (Arc 16 / Jalon M41).

Permet aux agents d'écrire, d'exécuter et d'auto-déboguer du code Python dans un
environnement isolé avec capture complète des entrées/sorties.

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): VMConfig entièrement paramétrable.
- Commandement 2 (Modulaire): Découplage strict entre la VM et le graphe cognitif.
- Commandement 6 (Sécurité & Isolation): Exécution en sous-processus isolé avec Timeout strict.
- Commandement 7 (Validation Rigoureuse): Rapports d'exécution typés ExecutionResult.
"""

from dataclasses import dataclass, field
import os
import sys
import tempfile
import shutil
import subprocess
import time
from typing import Optional, Dict, Any, List


@dataclass
class VMConfig:
    """Configuration de la Machine Virtuelle isolée."""
    timeout_seconds: float = 3.0
    max_output_chars: int = 10000
    python_executable: str = sys.executable
    memory_limit_mb: int = 256
    workdir_prefix: str = "agiseed_vm_"


@dataclass
class ExecutionResult:
    """Résultat complet d'une exécution de script dans la VM."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    timed_out: bool = False


class AgentVMSandbox:
    """
    Machine virtuelle d'exécution de code isolée pour agents auto-programmants.
    """

    def __init__(self, config: Optional[VMConfig] = None):
        self.config = config or VMConfig()
        self.workspace_dir = tempfile.mkdtemp(prefix=self.config.workdir_prefix)
        self._alive = True

    def is_alive(self) -> bool:
        return self._alive and os.path.exists(self.workspace_dir)

    def teardown(self):
        """Nettoie et supprime l'environnement virtuel."""
        if os.path.exists(self.workspace_dir):
            try:
                shutil.rmtree(self.workspace_dir)
            except Exception:
                pass
        self._alive = False

    def write_file(self, filename: str, content: str) -> str:
        """Écrit un fichier dans l'espace de travail virtuel."""
        file_path = os.path.join(self.workspace_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def read_file(self, filename: str) -> str:
        """Lit un fichier depuis l'espace de travail virtuel."""
        file_path = os.path.join(self.workspace_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self) -> List[str]:
        """Liste les fichiers présents dans la VM."""
        if not os.path.exists(self.workspace_dir):
            return []
        return os.listdir(self.workspace_dir)

    def execute_code(self, python_code: str, script_name: str = "solution.py") -> ExecutionResult:
        """
        Exécute un bloc de code Python dans un processus isolé avec timeout strict.
        """
        if not self._alive:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="VM_TERMINATED: La machine virtuelle n'est plus active.",
                duration_sec=0.0
            )

        script_path = self.write_file(script_name, python_code)
        cmd = [self.config.python_executable, "-I", "-S", "-u", script_path]

        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                timeout=self.config.timeout_seconds
            )
            duration = time.time() - t0
            stdout = proc.stdout[:self.config.max_output_chars].strip()
            stderr = proc.stderr[:self.config.max_output_chars].strip()
            success = (proc.returncode == 0)

            return ExecutionResult(
                success=success,
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_sec=round(duration, 4),
                timed_out=False
            )

        except subprocess.TimeoutExpired as e:
            duration = time.time() - t0
            return ExecutionResult(
                success=False,
                exit_code=-9,
                stdout="",
                stderr=f"TIMEOUT: Exécution interrompue après {self.config.timeout_seconds}s (Commandement 6).",
                duration_sec=round(duration, 4),
                timed_out=True
            )
        except Exception as e:
            duration = time.time() - t0
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"EXECUTION_ERROR: {str(e)}",
                duration_sec=round(duration, 4),
                timed_out=False
            )

    def __del__(self):
        self.teardown()
