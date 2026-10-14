"""Bails sur RESSOURCES NOMMÉES exclusives.

Inspiré de `cmex_crypto.batch.lease` (Quant-lab) — dont on reprend l'injectabilité (`now`, `leases_dir`,
testable sans horloge murale ni chemin fixe), la robustesse au crash (`read_all` ignore les fichiers
partiels) et l'idempotence de `release`.

⚠️ ÉCART DE CONCEPTION ASSUMÉ : Quant-lab gouverne par **cap de concurrence** (un nombre de slots).
AGAGI a une contrainte de nature différente — **KuzuDB est une ressource EXCLUSIVE nommée**. Deux
simulations de monde ne peuvent pas coexister quel que soit le nombre de cœurs, alors qu'une simulation
et un run de tests purs le peuvent. Un cap global à 1 serait donc à la fois trop strict (il sérialiserait
des jobs indépendants) et mal ciblé (il ne dit pas POURQUOI). D'où : **un bail par ressource nommée**,
`runs/leases/<resource>.json` — l'exclusivité est garantie par le nom de fichier lui-même.

PREUVE DU BESOIN (mesurée le 2026-07-21, pas supposée) : deux sondes monde lancées concurremment se sont
disputé le lock KuzuDB -> mesure CONTAMINÉE (« 3/6 génomes diffèrent », à refaire) et suite de tests en
timeout. Règle violée **2×** dans la journée alors qu'elle est documentée de longue date : classe **E10**
du registre des erreurs — *toute règle documentée sans application exécutable finit violée*.

IDENTITÉ ANTI-RÉUTILISATION DE PID : un bail mémorise `pid` ET `proc_create_time`. Après un crash, le PID
peut avoir été réattribué à un processus étranger ; comparer aussi l'instant de création évite de traiter
un innocent comme le détenteur du bail — et évite surtout de le TUER.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

DEFAULT_LEASES_DIR = Path("runs/leases")
DEFAULT_TTL_S = 1800.0          # 30 min : les runs de ce dépôt sont longs (cf. CLAUDE.md §Coût des runs)


class ResourceBusy(RuntimeError):
    """La ressource est détenue par un bail VIVANT. Ne PAS contourner : c'est ce verrou qui empêche la
    contention KuzuDB, dont la conséquence mesurée est une mesure silencieusement contaminée."""


@dataclass
class Lease:
    resource: str
    pid: int
    proc_create_time: float
    owner: str
    created: float
    ttl_s: float
    expires_at: float
    last_heartbeat: float


_REPO_ROOT: Optional[Path] = None


def _repo_root(cwd: Optional[Path] = None) -> Path:
    """P2.69 (i), 2026-09-15 — la racine du DÉPÔT, pas du worktree. Avant : `runs/leases` relatif au cwd,
    donc un worktree (`.claude/worktrees/...`) ne voyait pas le bail tenu dans l'arbre principal — pendant
    le run P4.9, 503 tests simulant un monde ont TOURNÉ dans un worktree (sautés dans l'arbre principal) ;
    la charge machine est partagée (E12 sur tout coût mesuré pendant). `git rev-parse --git-common-dir`
    rend le `.git` COMMUN à tous les worktrees : son parent est l'arbre principal. Sans git (ou hors dépôt) :
    le cwd, comme avant. Mis en cache par processus (`_reset_repo_root_cache()` pour les tests)."""
    global _REPO_ROOT
    if _REPO_ROOT is not None and cwd is None:
        return _REPO_ROOT
    base = Path(cwd) if cwd is not None else Path.cwd()
    root = base
    try:
        import subprocess
        out = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=str(base), capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            common = Path(out.stdout.strip())
            if not common.is_absolute():
                common = base / common
            root = common.resolve().parent
    except Exception:                               # noqa: BLE001 — git absent : racine = cwd, comme avant
        root = base
    if cwd is None:
        _REPO_ROOT = root
    return root


def _reset_repo_root_cache() -> None:
    global _REPO_ROOT
    _REPO_ROOT = None


def _dir(leases_dir: Optional[Path]) -> Path:
    if leases_dir is not None:
        return Path(leases_dir)
    return _repo_root() / DEFAULT_LEASES_DIR


def _path(resource: str, leases_dir: Optional[Path]) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in resource)
    return _dir(leases_dir) / f"{safe}.json"


def _write(lease: Lease, leases_dir: Optional[Path]) -> None:
    d = _dir(leases_dir)
    d.mkdir(parents=True, exist_ok=True)
    _path(lease.resource, leases_dir).write_text(json.dumps(asdict(lease)), encoding="utf-8")


_STILL_ACTIVE = 259                        # GetExitCodeProcess : le processus n'a pas fini
_EPOCH_FILETIME_S = 11644473600.0          # 1601-01-01 -> 1970-01-01, en secondes (convention de psutil)


def _identite_windows(pid: int):
    """Existence et instant de création par l'API Windows (ctypes), SANS psutil : même source que psutil (le FILETIME
    de création), donc des instants comparables à 1 s près."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(0x1000, False, int(pid))         # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        err = ctypes.get_last_error()
        if err == 87:                                    # ERROR_INVALID_PARAMETER : aucun processus de ce PID
            return "absent", None
        if err == 5:                                     # ERROR_ACCESS_DENIED : il EXISTE, on ne peut pas le lire
            return "present", None
        return "inconnu", None
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
            return "inconnu", None
        if code.value != _STILL_ACTIVE:
            return "absent", None                        # fini : la poignée survit au processus
        t = [wintypes.FILETIME() for _ in range(4)]
        if not k32.GetProcessTimes(h, *(ctypes.byref(x) for x in t)):
            return "present", None
        ft = (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime
        return "present", ft / 1e7 - _EPOCH_FILETIME_S
    finally:
        k32.CloseHandle(h)


def _identite_posix(pid: int):
    """Existence par `os.kill(pid, 0)`, instant de création par /proc (Linux, formule de psutil) quand il existe."""
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return "absent", None
    except PermissionError:
        return "present", None
    except Exception:                                    # noqa: BLE001 — ni oui ni non : on ne sait pas
        return "inconnu", None
    try:
        with open(f"/proc/{int(pid)}/stat", encoding="utf-8", errors="replace") as fh:
            champs = fh.read().rsplit(")", 1)[1].split()
        with open("/proc/stat", encoding="utf-8") as fh:
            btime = next(float(l.split()[1]) for l in fh if l.startswith("btime"))
        return "present", float(champs[19]) / os.sysconf("SC_CLK_TCK") + btime
    except Exception:                                    # noqa: BLE001 — pas de /proc : l'existence seule
        return "present", None


def identite(pid: int):
    """P2.171 (2026-10-13) — (« absent » | « present » | « inconnu », instant de création ou None). TROIS états : « je
    ne sais pas » n'est ni « absent » ni « présent ». Avant, `proc_create_time` rendait None AUSSI quand psutil manquait,
    et `is_holder_alive` lisait ce None comme « mort » : sous un Python sans psutil (le 3.14 du PATH de la batcave depuis
    le 30/09), le doctor a affiché ORPHELIN le bail VIVANT du run d'E34 (mesuré par Master 2 le 13/10), et un `--kill` l'aurait
    réapé, un `acquire` l'aurait PRIS — l'exclusion de kuzu cassée en silence. Les docstrings promettaient un mode
    « dégradé à l'existence du PID » que le code n'avait pas. Ordre : psutil ; sinon l'API du système (ctypes sous
    Windows, os.kill + /proc sous POSIX) ; sinon « inconnu »."""
    try:
        import psutil
    except Exception:                                    # noqa: BLE001 — absent ou bloqué : l'API du système
        psutil = None
    if psutil is not None:
        try:
            return "present", float(psutil.Process(int(pid)).create_time())
        except psutil.NoSuchProcess:
            return "absent", None
        except Exception:                                # noqa: BLE001 — AccessDenied, zombie : l'API du système tranche
            pass
    try:
        return _identite_windows(pid) if os.name == "nt" else _identite_posix(pid)
    except Exception:                                    # noqa: BLE001
        return "inconnu", None


def proc_create_time(pid: int) -> Optional[float]:
    """Instant de création du processus, ou None s'il n'existe pas OU s'il est illisible — pour TROIS états, lire
    `identite` (P2.171). Sans psutil, l'API du système le fournit (ctypes sous Windows, /proc sous Linux)."""
    return identite(pid)[1]


def holder_status(lease: Lease) -> str:
    """« vivant » | « mort » | « indetermine » (P2.171). Le sens prudent est « vivant tant qu'on ne sait pas » : un
    détenteur INDÉTERMINÉ n'est jamais repris par `acquire`, jamais réapé par le doctor. Un PID réattribué après crash
    (même PID, AUTRE instant de création) est mort ; présent sans identité lisible alors que le bail en porte une :
    indéterminé (le PID a pu être réattribué, on ne peut pas le prouver)."""
    etat, ct = identite(lease.pid)
    if etat == "absent":
        return "mort"
    if etat == "inconnu":
        return "indetermine"
    if ct is not None and lease.proc_create_time:
        return "mort" if abs(ct - lease.proc_create_time) > 1.0 else "vivant"
    if lease.proc_create_time:
        return "indetermine"
    return "vivant"                                      # bail sans identité (écrit sans elle) : la présence suffit


def is_holder_alive(lease: Lease) -> bool:
    """Le détenteur tourne-t-il ENCORE, et est-ce bien LUI ? Un PID réattribué après crash ne doit pas
    être pris pour le détenteur (ni, a fortiori, être tué par le doctor). INDÉTERMINÉ compte pour VIVANT (P2.171)."""
    return holder_status(lease) != "mort"


def is_expired(lease: Lease, *, now: Optional[float] = None) -> bool:
    t = time.time() if now is None else now
    return t > lease.expires_at


def is_live(lease: Lease, *, now: Optional[float] = None) -> bool:
    """VIVANT = non expiré ET détenteur réellement en vie. Les deux conditions sont nécessaires : un
    processus wedgé garde son PID mais laisse expirer son bail ; un crash laisse un bail non expiré
    derrière un PID mort."""
    return (not is_expired(lease, now=now)) and is_holder_alive(lease)


def read(resource: str, *, leases_dir: Optional[Path] = None) -> Optional[Lease]:
    p = _path(resource, leases_dir)
    try:
        return Lease(**json.loads(p.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, TypeError, OSError, ValueError):
        return None                        # fichier absent ou partiel (crash) -> pas de bail


def read_all(*, leases_dir: Optional[Path] = None) -> list[Lease]:
    d = _dir(leases_dir)
    out: list[Lease] = []
    if not d.exists():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            out.append(Lease(**json.loads(f.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, TypeError, OSError, ValueError):
            continue                       # robuste au crash : on ignore, on ne lève pas
    return out


def acquire(resource, owner="", ttl_s=DEFAULT_TTL_S, pid=None, *, now=None, leases_dir=None) -> Lease:
    """Prend la ressource, ou lève `ResourceBusy` si un bail VIVANT la détient.

    Un bail mort (expiré, ou dont le détenteur a disparu / a été remplacé par un PID réutilisé) est
    récupéré silencieusement : c'est ce qui rend le mécanisme crash-recoverable sans intervention."""
    t = time.time() if now is None else now
    pid = os.getpid() if pid is None else int(pid)
    current = read(resource, leases_dir=leases_dir)
    if current is not None and is_live(current, now=t) and current.pid != pid:
        raise ResourceBusy(
            f"ressource « {resource} » détenue par pid={current.pid} (owner={current.owner!r}, "
            f"expire dans {current.expires_at - t:.0f}s). NE PAS contourner : la contention produit "
            "des mesures silencieusement contaminées (E10).")
    lease = Lease(resource=resource, pid=pid, proc_create_time=proc_create_time(pid) or 0.0,
                  owner=owner, created=t, ttl_s=ttl_s, expires_at=t + ttl_s, last_heartbeat=t)
    _write(lease, leases_dir)
    return lease


def heartbeat(lease: Lease, *, now=None, ttl_s=None, leases_dir=None) -> Lease:
    """Renouvelle le bail. Un job long DOIT battre, sinon son bail expire et le doctor peut le réaper."""
    t = time.time() if now is None else now
    lease.ttl_s = lease.ttl_s if ttl_s is None else ttl_s
    lease.last_heartbeat = t
    lease.expires_at = t + lease.ttl_s
    _write(lease, leases_dir)
    return lease


def release(lease: Lease, *, leases_dir: Optional[Path] = None) -> None:
    """Libère (sortie propre). Idempotent."""
    _path(lease.resource, leases_dir).unlink(missing_ok=True)
