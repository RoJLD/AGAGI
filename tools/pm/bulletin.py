"""Bulletin d'UNE session, écrit par SES hooks — jamais de mémoire (E10 : une règle documentée est violée).

    python -m tools.pm.bulletin start|tool|stop|end     # appelé par .claude/settings.json, JSON du hook sur stdin
    python -m tools.pm.bulletin claim P4.9 [--session <id>]   # revendication volontaire d'un P-item

Le bulletin vit dans paths.sessions_dir("<session_id>.json"). Un hook sort TOUJOURS 0 : une erreur s'écrit dans
paths.pm_dir("hook_errors.log"), jamais dans la session. `start` imprime le résumé de BOARD.json en cache (jamais
recomputé ici : le hook doit rester sous la seconde) — c'est le PULL de la spec §3.1.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback

from src import paths
from tools.pm.snapshot import REGISTRY_DIR_DEFAULT, norm, read_registry

EVENTS = ("start", "tool", "stop", "end")
PLAFOND_FICHIERS = 200
REGISTRY_DIR = REGISTRY_DIR_DEFAULT              # monkeypatchable par les tests


def _vide(session_id):
    return {"session_id": session_id, "name": None, "pid": None, "cwd": None, "branch": None, "worktree": None,
            "started_at": None, "heartbeat_at": None, "ended_at": None, "claims": [], "files_touched": [],
            "last_tool_at": None}


def charger(session_id, sessions_dir=None):
    p = os.path.join(sessions_dir or paths.sessions_dir(), f"{session_id}.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def ecrire(bul, sessions_dir=None):
    d = sessions_dir or paths.sessions_dir()
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{bul['session_id']}.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(bul, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def branche_git(cwd):
    """(branche, racine du worktree) via git, ou (None, None) hors dépôt / git muet."""
    try:
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True,
                           encoding="utf-8", timeout=5)
        w = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True,
                           encoding="utf-8", timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None, None
    return (b.stdout.strip() if b.returncode == 0 else None), (norm(w.stdout.strip()) if w.returncode == 0 else None)


def appliquer(event, payload, bul, *, now, branche_fn):
    """PUR : applique un événement de hook au bulletin. `branche_fn(cwd) -> (branche, worktree)` est injecté."""
    sid = payload.get("session_id") or bul.get("session_id")
    b = dict(_vide(sid), **bul)
    cwd = payload.get("cwd") or b.get("cwd")
    if event == "start":
        b["started_at"] = now
        b["cwd"] = norm(cwd) if cwd else None
        b["pid"] = payload.get("pid")
        b["branch"], b["worktree"] = branche_fn(cwd)
    elif event == "tool":
        b["last_tool_at"] = now
        fp = (payload.get("tool_input") or {}).get("file_path")
        if fp:
            rel = norm(fp)
            base = b.get("cwd") or (norm(cwd) if cwd else None)
            if base and rel.startswith(base + "/"):
                rel = rel[len(base) + 1:]
            files = [f for f in b["files_touched"] if f != rel] + [rel]
            b["files_touched"] = files[-PLAFOND_FICHIERS:]
    elif event == "stop":
        b["heartbeat_at"] = now
        br, wt = branche_fn(cwd)
        if br:
            b["branch"], b["worktree"] = br, wt
    elif event == "end":
        b["ended_at"] = now
    return b


def nom_depuis_registre(session_id, registry_dir=None):
    for r in (read_registry(registry_dir or REGISTRY_DIR) or []):
        if r.get("session_id") == session_id:
            return r.get("name")
    return None


def session_id_courant(registry_dir=None):
    """Hors hook (sous-commande claim) : le premier ancêtre du processus courant présent au registre."""
    reg = {r.get("pid"): r.get("session_id") for r in (read_registry(registry_dir or REGISTRY_DIR) or []) if r.get("pid")}
    try:
        import psutil
        p = psutil.Process(os.getpid())
        for anc in [p] + p.parents():
            if anc.pid in reg:
                return reg[anc.pid]
    except Exception:                                   # noqa: BLE001 — psutil absent ou processus disparu : inconnu
        return None
    return None


def resume_tableau(pm_dir=None):
    p = os.path.join(pm_dir or paths.pm_dir(), "BOARD.json")
    try:
        with open(p, encoding="utf-8") as fh:
            board = json.load(fh)
    except (OSError, ValueError):
        return "[PM] tableau absent : lancer python -m tools.pm.board (ou la session PM n'a pas encore tourné)"
    from tools.pm.board import summary
    return summary(board)


def _journal(event, exc):
    try:
        os.makedirs(paths.pm_dir(), exist_ok=True)
        with open(paths.pm_dir("hook_errors.log"), "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {event} {type(exc).__name__}: {exc}\n")
            fh.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-2000:] + "\n")
    except OSError:
        pass                                            # le journal lui-même est indisponible : rien ne doit remonter


def _hook(event):
    payload = json.loads(sys.stdin.read() or "{}")
    sid = payload.get("session_id")
    if not sid:
        raise ValueError("hook sans session_id")
    bul = appliquer(event, payload, charger(sid), now=time.time(), branche_fn=branche_git)
    if bul.get("name") is None:
        bul["name"] = nom_depuis_registre(sid)
    ecrire(bul)
    if event == "start":
        print(resume_tableau())


def _claim(p_item, session):
    sid = session or session_id_courant()
    if not sid:
        print("[PM] claim ignoré : session introuvable (passer --session <id> ; le registre natif ne connaît pas ce processus)")
        return
    bul = dict(_vide(sid), **charger(sid))
    if p_item not in bul["claims"]:
        bul["claims"].append(p_item)
    if bul.get("name") is None:
        bul["name"] = nom_depuis_registre(sid)
    ecrire(bul)
    print(f"[PM] {bul.get('name') or sid} revendique {', '.join(bul['claims'])}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("event", choices=EVENTS + ("claim",))
    ap.add_argument("p_item", nargs="?", default=None)
    ap.add_argument("--session", default=None)
    args = ap.parse_args(argv)
    try:                                                # Windows : stdout cp1252 -> les accents du résumé lèveraient
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        if args.event == "claim":
            if not args.p_item:
                raise ValueError("claim exige un P-item (ex. P4.9)")
            _claim(args.p_item, args.session)
        else:
            _hook(args.event)
    except Exception as exc:                            # noqa: BLE001 — un hook ne bloque JAMAIS la session
        _journal(args.event, exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
