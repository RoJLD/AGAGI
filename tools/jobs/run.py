"""Lancement de sous-processus gouverné : bail sur ressource + timeout -> kill de l'ARBRE.

Le kill d'ARBRE (et non du seul processus) répond à un danger documenté de longue date dans ce dépôt
(« ProcessPoolExecutor : tuer l'arbre entier, sinon orphelins ») qui n'avait **aucune implémentation** —
`grep psutil` sur `tools/` et `src/` ne rendait rien avant ce module. Classe **E10** du registre.

Séquence de terminaison (standard vérifié, cf. Quant-lab `2026-06-16-job-manager-sota-reference.md`) :
`children(recursive=True)` -> `terminate()` -> `wait(grace)` -> `kill()`. Terminer les enfants AVANT le
parent évite qu'ils soient reparentés et survivent.
"""
from __future__ import annotations

import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from tools.jobs import lease as _lease


@dataclass
class JobResult:
    name: str
    returncode: Optional[int]
    timed_out: bool
    duration_s: float
    stdout: str
    stderr: str


def kill_tree(pid: int, grace_s: float = 3.0) -> int:
    """Termine le processus ET toute sa descendance. Renvoie le nombre de processus tués.
    Idempotent et tolérant : un processus déjà mort n'est pas une erreur."""
    try:
        import psutil
    except Exception:
        return 0
    try:
        parent = psutil.Process(pid)
    except Exception:
        return 0
    try:
        procs = parent.children(recursive=True) + [parent]
    except Exception:
        procs = [parent]
    for p in procs:                                  # enfants d'abord : évite la reparentalisation
        try:
            p.terminate()
        except Exception:
            pass
    gone, alive = psutil.wait_procs(procs, timeout=grace_s)
    for p in alive:
        try:
            p.kill()
        except Exception:
            pass
    return len(procs)


@contextmanager
def hold(resource: str, owner: str = "", ttl_s: float = _lease.DEFAULT_TTL_S, *, leases_dir=None):
    """Détient une ressource nommée le temps du bloc, et la libère TOUJOURS (même sur exception).

        with hold("kuzu", owner="warm009-ablation"):
            ...  # une autre sim demandant "kuzu" lève ResourceBusy

    Lève `lease.ResourceBusy` si la ressource est prise par un détenteur VIVANT — échec bruyant préféré
    à une mesure silencieusement contaminée."""
    lz = _lease.acquire(resource, owner=owner, ttl_s=ttl_s, leases_dir=leases_dir)
    try:
        yield lz
    finally:
        _lease.release(lz, leases_dir=leases_dir)


def run(name: str, cmd: Sequence[str], *, resources: Sequence[str] = (), timeout_s: Optional[float] = None,
        cwd: Optional[Path] = None, ttl_s: float = _lease.DEFAULT_TTL_S, leases_dir=None) -> JobResult:
    """Lance `cmd` en tenant `resources`, avec `timeout_s` -> kill de l'arbre.

    Le TTL du bail est calé sur `timeout_s` quand il est fourni (marge ×2) : un job tué par timeout ne
    doit pas laisser derrière lui un bail qui bloquerait la ressource jusqu'à son expiration."""
    if timeout_s:
        ttl_s = max(ttl_s, timeout_s * 2.0)
    held = []
    t0 = time.time()
    try:
        for r in resources:
            held.append(_lease.acquire(r, owner=name, ttl_s=ttl_s, leases_dir=leases_dir))
        proc = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd) if cwd else None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace")
        try:
            out, err = proc.communicate(timeout=timeout_s)
            return JobResult(name, proc.returncode, False, time.time() - t0, out or "", err or "")
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            out, err = "", ""
            try:
                out, err = proc.communicate(timeout=5)
            except Exception:
                pass
            return JobResult(name, None, True, time.time() - t0, out or "", err or "")
    finally:
        for lz in held:
            _lease.release(lz, leases_dir=leases_dir)
