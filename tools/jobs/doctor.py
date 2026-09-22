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


def _works_in_project(p) -> bool:
    """Le processus travaille-t-il DANS le dépôt ? — lu sur son `cwd`, pas sur sa ligne de commande.

    E4 (occ. doctor, 2026-09-22) : `PROJECT_MARKERS` cherche le nom du projet dans la LIGNE DE COMMANDE,
    or la forme canonique prescrite par CLAUDE.md — `python -m tools.…` lancé depuis la racine — ne le
    porte pas. Un run RÉEL de six jours (pid 54476, `-m tools.evo_runs.s2_blind_champion_bis --decomp`,
    623 Mo) était donc rapporté comme « 0 processus du projet ». Les worktrees vivent SOUS la racine :
    un run en worktree est bien du projet. Inaccessible (droits, processus disparu) -> False, jamais une
    exception qui viderait l'inventaire."""
    try:
        cwd = p.cwd()
    except Exception:
        return False
    if not cwd:
        return False
    try:
        racine = os.path.realpath(_ROOT)
        return os.path.commonpath([os.path.realpath(cwd), racine]) == racine
    except Exception:                     # disques différents sous Windows -> commonpath lève
        return False


def project_processes(older_min: float = 0.0):
    """Processus python du projet, hors protégés : ligne de commande marquée OU cwd DANS le dépôt."""
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
            if not (any(m in cl for m in PROJECT_MARKERS) or _works_in_project(p)):
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
    """{live, expired_alive, orphan, dead} — TROIS états, parce que « pas vivant » en recouvrait deux
    que rien ne distinguait dans le rapport (E4, occ. doctor du 2026-09-22) :

      * `live`          : non expiré ET détenteur en vie ;
      * `expired_alive` : TTL dépassé mais le détenteur TOURNE (heartbeat manquant — machine en veille,
                          run très long). **Ce n'est pas un orphelin** : il ne se réape pas ;
      * `orphan`        : détenteur disparu (PID absent ou réattribué, via `proc_create_time`).

    `dead` reste l'UNION des deux derniers : les appelants existants (dont `--kill`, qui refuse déjà de
    tuer un détenteur vivant) gardent leur sémantique."""
    live, expired_alive, orphan = [], [], []
    for lz in _lease.read_all(leases_dir=leases_dir):
        if _lease.is_live(lz, now=now):
            live.append(lz)
        elif _lease.is_holder_alive(lz):
            expired_alive.append(lz)
        else:
            orphan.append(lz)
    return {"live": live, "expired_alive": expired_alive, "orphan": orphan,
            "dead": expired_alive + orphan}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kill", action="store_true", help="Réape les bails MORTS (destructif).")
    ap.add_argument("--older-min", type=float, default=0.0, help="Ne considérer que les procs plus vieux.")
    args = ap.parse_args(argv)

    cls = classify_leases()
    procs = project_processes(args.older_min)

    print(f"bails : {len(cls['live'])} vivant(s), {len(cls['expired_alive'])} expiré(s) à détenteur "
          f"VIVANT, {len(cls['orphan'])} orphelin(s)")
    for lz in cls["live"]:
        print(f"  VIVANT   {lz.resource:<12} pid={lz.pid:<7} owner={lz.owner!r}")
    for lz in cls["expired_alive"]:
        print(f"  EXPIRÉ   {lz.resource:<12} pid={lz.pid:<7} owner={lz.owner!r}  "
              "[détenteur VIVANT — heartbeat manquant, PAS un orphelin : ne pas réaper]")
    for lz in cls["orphan"]:
        print(f"  ORPHELIN {lz.resource:<12} pid={lz.pid:<7} owner={lz.owner!r}  [détenteur disparu]")

    print(f"\nprocessus python du projet (hors moi et mes ancêtres) : {len(procs)}")
    for p in procs[:15]:
        print(f"  pid={p['pid']:<7} age={p['age_min']:6.1f}min rss={p['rss_mb']:7.0f}Mo  {p['cmd']}")

    if not args.kill:
        if cls["dead"] or procs:
            print("\n(lecture seule — `--kill` ne réape que les ORPHELINS)")
        return 0

    n_l = n_p = 0
    for lz in cls["expired_alive"]:
        print(f"  REFUS  {lz.resource} : détenteur VIVANT malgré un TTL expiré -> heartbeat manquant, "
              "pas un orphelin. Signalé, non tué.")
    for lz in cls["orphan"]:
        if _lease.is_holder_alive(lz):       # course : il a pu revivre entre la lecture et ici
            print(f"  REFUS  {lz.resource} : détenteur redevenu VIVANT depuis la lecture. Non tué.")
            continue
        _lease.release(lz)
        n_l += 1
        if lz.pid not in _protected_pids():
            n_p += kill_tree(lz.pid)
    print(f"\nréapés : {n_l} bail(s), {n_p} processus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
