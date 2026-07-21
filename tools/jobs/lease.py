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


def _dir(leases_dir: Optional[Path]) -> Path:
    return Path(leases_dir) if leases_dir is not None else DEFAULT_LEASES_DIR


def _path(resource: str, leases_dir: Optional[Path]) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in resource)
    return _dir(leases_dir) / f"{safe}.json"


def _write(lease: Lease, leases_dir: Optional[Path]) -> None:
    d = _dir(leases_dir)
    d.mkdir(parents=True, exist_ok=True)
    _path(lease.resource, leases_dir).write_text(json.dumps(asdict(lease)), encoding="utf-8")


def proc_create_time(pid: int) -> Optional[float]:
    """Instant de création du processus, ou None s'il n'existe pas. Sans psutil -> None (dégradé :
    l'identité se réduit alors à l'existence du PID)."""
    try:
        import psutil
    except Exception:
        return None
    try:
        return float(psutil.Process(pid).create_time())
    except Exception:
        return None


def is_holder_alive(lease: Lease) -> bool:
    """Le détenteur tourne-t-il ENCORE, et est-ce bien LUI ? Un PID réattribué après crash ne doit pas
    être pris pour le détenteur (ni, a fortiori, être tué par le doctor)."""
    ct = proc_create_time(lease.pid)
    if ct is None:
        return False
    if lease.proc_create_time and abs(ct - lease.proc_create_time) > 1.0:
        return False                       # même PID, AUTRE processus -> le détenteur est mort
    return True


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
