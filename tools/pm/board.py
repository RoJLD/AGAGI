"""Tableau PM — `compute(snap)` est PUR : un instantané (tools/pm/snapshot.py) -> sessions, alertes A1-A8,
charge connue, aveuglements. Seul `main` écrit (BOARD.json, BOARD.md sous paths.pm_dir()) : le PM en est
l'unique writer ; le hook SessionStart ne fait que LIRE le JSON en cache.

Une source absente ne produit jamais « 0 alerte » : elle produit une ligne AVEUGLE SUR <source> en tête du
tableau et supprime les alertes qui en dépendent (porte 14 appliquée au tableau lui-même).
"""
import argparse
import json
import os
import sys
import time

from src import paths
from tools.pm.snapshot import norm, snapshot

SEUILS = {"suppressions": 500, "cpu_pct": 80.0, "sims_max": 1, "worktree_jours": 7,
          "sans_claim_h": 1.0, "heartbeat_h": 2.0}


def _h(sec):
    return sec / 3600.0


def _nom(s):
    return s.get("name") or s.get("session_id") or "?"


def _sessions(snap):
    """Sessions DU DÉPÔT : registre natif dont le cwd est la racine ou un worktree, joint aux bulletins.

    `compute` tient l'invariant « norm des deux côtés » elle-même : `repo_root` et chaque `w["path"]`
    sont re-normalisés ici, sans supposer que le snapshot les a déjà normalisés (un registre natif
    peut écrire un `cwd` à BACKSLASHES sur Windows)."""
    racines = {norm(snap["repo_root"])} | {norm(w["path"]) for w in (snap.get("worktrees") or [])}
    bull = {b.get("session_id"): b for b in (snap.get("bulletins") or []) if b.get("session_id")}
    out = []
    for r in (snap.get("registry") or []):
        if "illisible" in r or not r.get("cwd"):
            continue
        cwd = norm(r["cwd"])
        if not any(cwd == x or cwd.startswith(x + "/") for x in racines):
            continue
        b = bull.get(r.get("session_id"), {})
        out.append({"name": r.get("name"), "session_id": r.get("session_id"), "pid": r.get("pid"), "cwd": cwd,
                    "started_at": r.get("started_at"), "branch": b.get("branch"),
                    "claims": list(b.get("claims") or []), "claims_inferes": [],
                    "files_touched": list(b.get("files_touched") or []),
                    "heartbeat_at": b.get("heartbeat_at"), "bulletin": bool(b)})
    return out


def _inferer_claims(sessions, backlog_paths):
    if backlog_paths is None:
        return
    for s in sessions:
        touches = set(s["files_touched"])
        s["claims_inferes"] = sorted(p for p, chemins in backlog_paths.items() if touches & set(chemins))


def _alertes(snap, sessions, now):
    A, aveugle = [], []

    def add(id_, cle, gravite, message, preuve):
        A.append({"id": id_, "cle": f"{id_}:{cle}", "gravite": gravite, "message": message, "preuve": preuve})

    if snap.get("registry") is None:
        aveugle.append("registre natif (~/.claude/sessions)")
    if snap.get("bulletins") is None:
        aveugle.append("bulletins de session (paths.sessions_dir)")
    else:                                                       # A1 — un fichier, deux sessions vivantes
        par_fichier = {}
        for s in sessions:
            for f in s["files_touched"]:
                par_fichier.setdefault(f, set()).add(_nom(s))
        for f, noms in sorted(par_fichier.items()):
            if len(noms) >= 2:
                add("A1", f, "alerte", f"{f} touché par {len(noms)} sessions vivantes : {', '.join(sorted(noms))}",
                    {"fichier": f, "sessions": sorted(noms)})

    leases = snap.get("leases")                                 # A2 — bails
    if leases is None:
        aveugle.append("bails (tools/jobs)")
    elif not snap.get("psutil"):
        aveugle.append("identité des détenteurs de bail (psutil absent)")
    else:
        for lz in leases["dead"]:
            if lz["detenteur_vivant"]:
                add("A2", lz["resource"], "info",
                    f"bail {lz['resource']} : TTL expiré, détenteur VIVANT (heartbeat manquant ; owner={lz['owner']!r}, pid={lz['pid']})", lz)
            else:
                add("A2", lz["resource"], "alerte",
                    f"bail {lz['resource']} ORPHELIN : détenteur mort (owner={lz['owner']!r}, pid={lz['pid']})", lz)

    wts = snap.get("worktrees")                                 # A3 — worktrees sans session
    if wts is None:
        aveugle.append("worktrees (git)")
    else:
        cwds = {s["cwd"] for s in sessions}
        for w in wts:
            if w["path"] == snap["repo_root"] or w["path"] in cwds:
                continue
            vieux = w.get("head_time") is not None and (now - w["head_time"]) > SEUILS["worktree_jours"] * 86400
            if w.get("merged") or vieux:
                raison = "branche fusionnée" if w.get("merged") else f"inactif > {SEUILS['worktree_jours']} j"
                add("A3", w["path"], "alerte", f"worktree sans session {w['path']} ({w.get('branch')}) : {raison}", w)

    commits = snap.get("commits")                               # A4 — grosse suppression / amputation (E22)
    if commits is None:
        aveugle.append("commits récents (git)")
    else:
        for c in commits:
            if c["deletions"] >= SEUILS["suppressions"] or c["amputations"]:
                add("A4", c["sha"], "alerte",
                    f"commit {c['sha']} : -{c['deletions']} lignes, {len(c['amputations'])} fichier(s) amputé(s) — {c['sujet'][:80]}", c)

    procs = snap.get("processes")                               # A5 — charge
    if procs is None:
        aveugle.append("processus (psutil)")
    sims = [p for p in (procs or []) if p.get("simulation")]
    if procs is not None and len(sims) > SEUILS["sims_max"]:
        add("A5", "sims", "alerte", f"{len(sims)} simulations en vol : pas une de plus (contention kuzu, coût contaminé E12)",
            {"pids": [p["pid"] for p in sims], "cmds": [p["cmd"] for p in sims]})
    cpu = snap.get("cpu_5min_pct")
    if cpu is not None and cpu > SEUILS["cpu_pct"]:
        add("A5", "cpu", "alerte", f"charge CPU 5 min = {cpu:.0f} % > {SEUILS['cpu_pct']:.0f} %", {"cpu_5min_pct": cpu})

    par_claim = {}                                              # A6 — même P-item
    for s in sessions:
        for c in s["claims"]:
            par_claim.setdefault(c, set()).add(_nom(s))
    for c, noms in sorted(par_claim.items()):
        if len(noms) >= 2:
            add("A6", c, "alerte", f"{c} revendiqué par {', '.join(sorted(noms))}", {"p_item": c, "sessions": sorted(noms)})

    backlog_ok = snap.get("backlog_paths") is not None          # A7 dépend de l'inférence : aveugle si backlog absent
    for s in sessions:                                          # A7 / A8 — informations
        if not s["bulletin"]:
            continue
        age_h = _h(now - s["started_at"]) if s.get("started_at") else None
        if age_h is not None and age_h > SEUILS["sans_claim_h"] and not s["claims"] and not s["claims_inferes"] and backlog_ok:
            add("A7", _nom(s), "info", f"{_nom(s)} active depuis {age_h:.1f} h sans P-item revendiqué ni inféré", {"session": _nom(s)})
        hb = s.get("heartbeat_at")
        if hb is not None and _h(now - hb) > SEUILS["heartbeat_h"]:
            add("A8", _nom(s), "info", f"{_nom(s)} : heartbeat vieux de {_h(now - hb):.1f} h, PID vivant", {"session": _nom(s)})
    return A, aveugle


def compute(snap, now=None):
    now = float(snap.get("now")) if now is None else float(now)
    sessions = _sessions(snap)
    _inferer_claims(sessions, snap.get("backlog_paths"))
    alertes, aveugle = _alertes(snap, sessions, now)
    if snap.get("backlog_paths") is None:
        aveugle.append("backlog (chemins cités par les entrées)")
    procs, leases = snap.get("processes"), snap.get("leases")
    charge = {"sims_en_vol": (sum(1 for p in procs if p.get("simulation")) if procs is not None else None),
              "cpu_5min_pct": snap.get("cpu_5min_pct"),
              "bails_vivants": ([l["resource"] for l in leases["live"]] if leases is not None else None)}
    return {"generated_at": now, "repo_root": snap["repo_root"], "aveugle": aveugle, "sessions": sessions,
            "alertes": alertes, "charge_connue": charge, "worktrees": snap.get("worktrees"), "bails": leases}


def render_md(board):
    L = ["# Tableau PM", f"généré : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(board['generated_at']))}"]
    for a in board["aveugle"]:
        L.append(f"AVEUGLE SUR {a}")
    c = board["charge_connue"]
    L += ["", "## Charge connue",
          f"simulations en vol : {c['sims_en_vol']} · CPU 5 min : {c['cpu_5min_pct']} % · bails vivants : {c['bails_vivants']}",
          "", "## Sessions", "| session | branche | P-items | inférés | fichiers en vol | heartbeat |", "| --- | --- | --- | --- | --- | --- |"]
    for s in board["sessions"]:
        hb = f"{_h(board['generated_at'] - s['heartbeat_at']):.1f} h" if s.get("heartbeat_at") else "—"
        L.append(f"| {_nom(s)} | {s.get('branch') or '—'} | {', '.join(s['claims']) or '—'} | "
                 f"{', '.join(s['claims_inferes']) or '—'} | {len(s['files_touched'])} | {hb} |")
    L += ["", f"## Alertes ({len(board['alertes'])})"]
    for a in board["alertes"]:
        L.append(f"- [{a['gravite']}] {a['cle']} — {a['message']}")
    L += ["", "## Worktrees"]
    for w in (board.get("worktrees") or []):
        L.append(f"- {w['path']} ({w.get('branch')}) fusionné={w.get('merged')}")
    return "\n".join(L) + "\n"


def summary(board, max_lines=25):
    """Ce qu'une session lit à sa naissance : aveuglements, charge, qui est sur quoi, alertes."""
    L = [f"[PM] tableau du {time.strftime('%Y-%m-%d %H:%M', time.localtime(board['generated_at']))} — {len(board['sessions'])} sessions AGAGI"]
    L += [f"[PM] AVEUGLE SUR {a}" for a in board["aveugle"]]
    c = board["charge_connue"]
    L.append(f"[PM] charge : sims={c['sims_en_vol']} cpu5={c['cpu_5min_pct']} bails={c['bails_vivants']}")
    for s in board["sessions"]:
        L.append(f"[PM] {_nom(s)} : {', '.join(s['claims'] or s['claims_inferes']) or 'sans P-item'} — {len(s['files_touched'])} fichiers en vol")
    for a in board["alertes"]:
        L.append(f"[PM] {a['gravite'].upper()} {a['cle']} — {a['message']}")
    if len(L) > max_lines:
        L = L[:max_lines - 1] + [f"[PM] … {len(L) - max_lines + 1} lignes de plus dans BOARD.md"]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--registry-dir", default=None)
    ap.add_argument("--sessions-dir", default=None)
    ap.add_argument("--stdout", action="store_true", help="imprime le markdown au lieu du résumé")
    args = ap.parse_args(argv)
    board = compute(snapshot(args.repo_root, registry_dir=args.registry_dir, sessions_dir=args.sessions_dir))
    os.makedirs(paths.pm_dir(), exist_ok=True)
    with open(paths.pm_dir("BOARD.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(board)
    with open(paths.pm_dir("BOARD.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md if args.stdout else summary(board))
    return 0


if __name__ == "__main__":
    sys.exit(main())
