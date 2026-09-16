"""Instantané des SOURCES du tableau PM — lecture seule, une fonction par source.

Chaque lecteur rend `None` quand sa source est indisponible (répertoire absent, git muet, psutil manquant) :
jamais une valeur par défaut. `board.compute` transforme chaque `None` en ligne `AVEUGLE SUR <source>` —
une source absente ne doit pas ressembler à une source saine (porte 14). Aucune écriture, aucun bail,
aucun monde : cette couche est CPU pur.
"""
import glob
import json
import os
import re
import subprocess
import time

from src import paths

REGISTRY_DIR_DEFAULT = os.path.join(os.path.expanduser("~"), ".claude", "sessions")
# Une ligne de commande de simulation : runners du monde, sondes, balayages, calibrations.
SIM_MARKERS = ("evo_runs", "_run.py", "probe", "sweep", "calibration", "s2_", "learner")
_DELETIONS = re.compile(r"(\d+) deletions?\(-\)")
_INSERTIONS = re.compile(r"(\d+) insertions?\(\+\)")


def norm(p):
    """Chemin comparable entre registre, worktrees et bulletins : absolu, casse normalisée, slashs avant."""
    return os.path.normcase(os.path.abspath(p)).replace("\\", "/").rstrip("/")


def _psutil():
    try:
        import psutil
        return psutil
    except Exception:                                   # noqa: BLE001 — dégradé déclaré : None
        return None


def _git(repo_root, *args, timeout=20):
    try:
        out = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, encoding="utf-8",
                             errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _ms(v):
    return (float(v) / 1000.0) if v else None


def read_registry(registry_dir=None):
    d = registry_dir or REGISTRY_DIR_DEFAULT
    if not os.path.isdir(d):
        return None
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                r = json.load(fh)
        except (OSError, ValueError):
            out.append({"illisible": os.path.basename(f)})
            continue
        if not isinstance(r, dict):
            out.append({"illisible": os.path.basename(f)})
            continue
        out.append({"pid": r.get("pid"), "session_id": r.get("sessionId"), "name": r.get("name"),
                    "cwd": r.get("cwd"), "kind": r.get("kind"),
                    "started_at": _ms(r.get("startedAt")), "updated_at": _ms(r.get("updatedAt"))})
    return out


def read_bulletins(sessions_dir=None):
    d = sessions_dir or paths.sessions_dir()
    if not os.path.isdir(d):
        return None
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                b = json.load(fh)
        except (OSError, ValueError):
            out.append({"illisible": os.path.basename(f)})
            continue
        if not isinstance(b, dict):
            out.append({"illisible": os.path.basename(f)})
            continue
        out.append(b)
    return out


def read_worktrees(repo_root):
    txt = _git(repo_root, "worktree", "list", "--porcelain")
    if txt is None:
        return None
    merged = _git(repo_root, "branch", "--merged", "main", "--format=%(refname:short)")
    fusionnees = set(merged.split()) if merged is not None else None
    out, cur = [], {}
    for ligne in txt.splitlines() + [""]:
        if not ligne:
            if cur:
                out.append(cur)
                cur = {}
            continue
        cle, _, val = ligne.partition(" ")
        if cle == "worktree":
            cur = {"path": norm(val), "branch": None, "head": None}
        elif cle == "HEAD":
            cur["head"] = val
        elif cle == "branch":
            cur["branch"] = val.replace("refs/heads/", "")
    for w in out:
        w["merged"] = (w["branch"] in fusionnees) if (fusionnees is not None and w["branch"]) else None
        t = _git(repo_root, "log", "-1", "--format=%ct", w["head"]) if w["head"] else None
        w["head_time"] = float(t.strip()) if t and t.strip().isdigit() else None
    return out


def _amputations(repo_root, sha):
    """Fichiers du commit dont le compte d'ENTITÉ (tools/check_amputation.compter) tombe à 0 ou sous la moitié."""
    from tools.check_amputation import compter
    noms = _git(repo_root, "show", "--name-only", "--format=", sha)
    res = []
    for rel in (noms or "").split():
        avant, apres = _git(repo_root, "show", f"{sha}^:{rel}"), _git(repo_root, "show", f"{sha}:{rel}")
        if avant is None or apres is None:
            continue
        a, b = compter(rel, avant), compter(rel, apres)
        if a is None or b is None:
            continue
        if a > 0 and (b == 0 or b < a / 2):
            res.append({"chemin": rel, "avant": a, "apres": b})
    return res


def read_recent_commits(repo_root, since="24 hours ago", amputation_seuil=100):
    txt = _git(repo_root, "log", "--all", f"--since={since}", "--format=%x1e%H%x1f%s", "--shortstat")
    if txt is None:
        return None
    out = []
    for bloc in txt.split("\x1e"):
        bloc = bloc.strip()
        if not bloc:
            continue
        tete, _, reste = bloc.partition("\n")
        sha, _, sujet = tete.partition("\x1f")
        ins, dele = _INSERTIONS.search(reste), _DELETIONS.search(reste)
        c = {"sha": sha[:10], "sujet": sujet.strip(), "insertions": int(ins.group(1)) if ins else 0,
             "deletions": int(dele.group(1)) if dele else 0, "amputations": []}
        if c["deletions"] >= amputation_seuil:
            c["amputations"] = _amputations(repo_root, sha)
        out.append(c)
    return out


def read_leases(leases_dir=None):
    try:
        from tools.jobs import doctor as D
        from tools.jobs import lease as L
    except ImportError:
        return None
    cls = D.classify_leases(leases_dir=leases_dir)

    def _d(lz, vivant):
        return {"resource": lz.resource, "pid": lz.pid, "owner": lz.owner, "created": lz.created,
                "expires_at": lz.expires_at, "ttl_s": lz.ttl_s, "vivant": vivant,
                "detenteur_vivant": L.is_holder_alive(lz)}
    return {"live": [_d(x, True) for x in cls["live"]], "dead": [_d(x, False) for x in cls["dead"]]}


def read_processes():
    if _psutil() is None:
        return None
    from tools.jobs import doctor as D
    procs = D.project_processes()
    for p in procs:
        p["simulation"] = any(m in p["cmd"] for m in SIM_MARKERS)
    return procs


def read_cpu_5min():
    ps = _psutil()
    if ps is None:
        return None
    try:
        return 100.0 * ps.getloadavg()[1] / float(ps.cpu_count() or 1)
    except (OSError, AttributeError):
        return None


def read_backlog_paths(repo_root):
    p = os.path.join(repo_root, "docs", "roadmap", "PRIORITES_ET_DETTES.md")
    try:
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
    except OSError:
        return None
    from tools.check_backlog_freshness import _BACKTICK_PATH, _TETE
    tete = re.compile(_TETE)
    out, courants = {}, []
    for ligne in txt.splitlines():
        m = tete.match(ligne.strip())
        if m:
            courants = [p.strip() for p in m.group(1).split("/")]
            for p in courants:
                out.setdefault(p, set())
            continue
        if courants:
            for c in _BACKTICK_PATH.findall(ligne):
                if "/" in c:
                    for p in courants:
                        out[p].add(c)
    return {k: sorted(v) for k, v in out.items()}


def snapshot(repo_root, *, registry_dir=None, sessions_dir=None, leases_dir=None, now=None,
             since="24 hours ago"):
    return {"now": time.time() if now is None else float(now), "repo_root": norm(repo_root),
            "psutil": _psutil() is not None,
            "registry": read_registry(registry_dir), "bulletins": read_bulletins(sessions_dir),
            "worktrees": read_worktrees(repo_root), "commits": read_recent_commits(repo_root, since),
            "leases": read_leases(leases_dir), "processes": read_processes(),
            "cpu_5min_pct": read_cpu_5min(), "backlog_paths": read_backlog_paths(repo_root)}
