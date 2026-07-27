"""Hygiène des jobs : état des bails et des processus du projet.

⚠️ DESTRUCTIF ET PEU RÉVERSIBLE : tuer un processus peut détruire des heures de calcul, et l'arbre de
travail est PARTAGÉ entre sessions parallèles. D'où trois garde-fous NON négociables :
  1. **`--report` est le défaut** ; tuer exige `--kill` explicite.
  2. **Jamais** le processus courant ni ses ancêtres (on ne se scie pas la branche).
  3. **Jamais** un bail dont le détenteur est VIVANT — même expiré : un bail périmé sur un processus qui
     tourne encore signale un heartbeat manquant, pas un orphelin. On le SIGNALE, on ne le tue pas.

⚠️ Ce module a été motivé par un diagnostic que la MESURE a réfuté le même jour : j'avais attribué une
panne de fork à des « processus orphelins probables » — mesure faite : **zéro orphelin, 18 Go libres**.
La panne était une défaillance de fork Cygwin/MSYS. Le reaping d'orphelins n'est donc PAS le besoin
dominant d'AGAGI (contrairement à Quant-lab, dont le `doctor.py` répond à un incident réel de famine
mémoire) : ici il sert surtout de FILET pour les bails laissés par un crash. Conserver cette note évite
de re-justifier l'outil par un besoin supposé.

Usage :
  python -m tools.jobs.doctor              # état : bails + processus du projet (exit 0)
  python -m tools.jobs.doctor --kill       # réape les bails MORTS et leurs processus, si tant est
  python -m tools.jobs.doctor --kill --older-min 60
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.jobs import lease as _lease           # noqa: E402
from tools.jobs.run import kill_tree             # noqa: E402

PROJECT_MARKERS = ("AGAGI",)


def _protected_pids():
    """Le processus courant et TOUS ses ancêtres : jamais candidats."""
    pids = {os.getpid()}
    try:
        import psutil
        for p in psutil.Process(os.getpid()).parents():
            pids.add(p.pid)
    except Exception:
        pass
    return pids


def project_processes(older_min: float = 0.0):
    """Processus python dont la ligne de commande référence le projet, hors protégés."""
    try:
        import psutil
    except Exception:
        return []
    prot, now, out = _protected_pids(), time.time(), []
    for p in psutil.process_iter(["pid", "name", "create_time", "cmdline", "memory_info"]):
        try:
            i = p.info
            if i["pid"] in prot or not i["name"] or "python" not in i["name"].lower():
                continue
            cl = " ".join(i["cmdline"] or "")
            if not any(m in cl for m in PROJECT_MARKERS):
                continue
            age = (now - i["create_time"]) / 60.0
            if age < older_min:
                continue
            rss = (i["memory_info"].rss / 2 ** 20) if i["memory_info"] else 0.0
            out.append({"pid": i["pid"], "age_min": age, "rss_mb": rss, "cmd": cl[:100]})
        except Exception:
            continue
    return sorted(out, key=lambda r: -r["age_min"])


def classify_leases(*, leases_dir=None, now=None):
    """{vivants, morts} — un bail MORT est expiré OU son détenteur a disparu (PID absent, ou réutilisé
    par un autre processus, détecté via `proc_create_time`)."""
    live, dead = [], []
    for lz in _lease.read_all(leases_dir=leases_dir):
        (live if _lease.is_live(lz, now=now) else dead).append(lz)
    return {"live": live, "dead": dead}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kill", action="store_true", help="Réape les bails MORTS (destructif).")
    ap.add_argument("--older-min", type=float, default=0.0, help="Ne considérer que les procs plus vieux.")
    args = ap.parse_args(argv)

    cls = classify_leases()
    procs = project_processes(args.older_min)

    print(f"bails : {len(cls['live'])} vivant(s), {len(cls['dead'])} mort(s)")
    for lz in cls["live"]:
        print(f"  VIVANT  {lz.resource:<12} pid={lz.pid:<7} owner={lz.owner!r}")
    for lz in cls["dead"]:
        raison = "détenteur disparu" if not _lease.is_holder_alive(lz) else "TTL expiré (heartbeat manquant)"
        print(f"  MORT    {lz.resource:<12} pid={lz.pid:<7} owner={lz.owner!r}  [{raison}]")

    print(f"\nprocessus python du projet (hors moi et mes ancêtres) : {len(procs)}")
    for p in procs[:15]:
        print(f"  pid={p['pid']:<7} age={p['age_min']:6.1f}min rss={p['rss_mb']:7.0f}Mo  {p['cmd']}")

    if not args.kill:
        if cls["dead"] or procs:
            print("\n(lecture seule — `--kill` pour réaper les bails MORTS)")
        return 0

    n_l = n_p = 0
    for lz in cls["dead"]:
        if _lease.is_holder_alive(lz):
            print(f"  REFUS  {lz.resource} : détenteur VIVANT malgré un TTL expiré -> heartbeat manquant, "
                  "pas un orphelin. Signalé, non tué.")
            continue
        _lease.release(lz)
        n_l += 1
        if lz.pid not in _protected_pids():
            n_p += kill_tree(lz.pid)
    print(f"\nréapés : {n_l} bail(s), {n_p} processus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
