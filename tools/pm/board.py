"""Tableau PM — `compute(snap)` est PUR : un instantané (tools/pm/snapshot.py) -> sessions, alertes A1-A8,
charge connue, aveuglements. Seul `main` écrit (BOARD.json, BOARD.md sous paths.pm_dir()) : le PM en est
l'unique writer ; le hook SessionStart ne fait que LIRE le JSON en cache.

Une source absente ne produit jamais « 0 alerte » : elle produit une ligne AVEUGLE SUR <source> en tête du
tableau et supprime les alertes qui en dépendent (porte 14 appliquée au tableau lui-même).
"""
import argparse
import json
import os
import re
import sys
import time

from src import paths
from tools.pm.bulletin import texte_age
from tools.pm.snapshot import ancrer_data_root, norm, snapshot

SEUILS = {"suppressions": 500, "cpu_pct": 80.0, "sims_max": 1, "worktree_jours": 7,
          "sans_claim_h": 1.0, "heartbeat_h": 2.0}
# Le bail `pm` est renouvelé à CHAQUE tick (tools/pm/tick.py), pour TTL_PM_S. Un tableau plus vieux que ce TTL
# n'a donc été suivi d'AUCUN tick pendant toute la durée du bail : par la définition même du système, le rôle PM
# est VACANT. La péremption du tableau lu au démarrage est ce seuil-là, et pas une valeur de plus à choisir :
# le skill /pm se réveille toutes les 1200-1800 s, donc 2 h = au moins quatre ticks manqués d'affilée — une
# panne, pas une gigue. Défini ICI (le tableau le relit), importé par le tick : une seule source.
TTL_PM_S = 7200.0
PEREMPTION_S = TTL_PM_S
# CÉCITÉ DÉCLARÉE (défaut 4, 2026-09-24). `files_touched` n'est alimenté QUE par le hook PostToolUse des outils
# d'ÉDITION (matcher Edit|Write|MultiEdit|NotebookEdit dans .claude/settings.json) : un script Python lancé par
# Bash qui réécrit un fichier n'y laisse AUCUNE trace — mesuré : une session qui venait de réécrire le backlog par
# script n'apparaissait pas. Une liste qui ne voit qu'une partie des écritures ressemble à une liste complète ;
# le tableau le DIT partout où il présente ces fichiers (A1 et les P-items inférés en dépendent). Ce n'est PAS une
# ligne AVEUGLE SUR : une limite déclarée n'est pas une source absente, et y entrer gonflerait le compte à chaque tick.
# P2.118 (2026-09-26) : un hook PostToolUse `Bash` COMPTE désormais les commandes qui peuvent écrire
# (`bash_ecritures_possibles`) ; il ne les NOMME pas — la cécité sur les NOMS demeure, elle est chiffrée.
CECITE_FICHIERS = ("fichiers en vol = vus par les hooks des outils d'édition (Edit/Write/MultiEdit/NotebookEdit) "
                   "SEULEMENT : un script lancé par Bash qui réécrit un fichier n'y laisse aucun NOM — il est "
                   "seulement COMPTÉ (écritures Bash possibles, jamais nommées) ; A1 et les P-items inférés ne "
                   "voient pas ces écritures")


def _h(sec):
    return sec / 3600.0


_ABSOLU = re.compile(r"^(?:[A-Za-z]:/|/)")


def _absolu(f):
    """Un chemin de `files_touched` déjà ABSOLU : le bulletin le garde tel quel quand le fichier n'est pas sous le
    cwd de la session (la mémoire de projet de Claude, un autre worktree), ou quand aucun cwd n'est connu. PURE."""
    return bool(_ABSOLU.match(f))


def _nom(s):
    return s.get("name") or s.get("session_id") or "?"


def _sessions(snap):
    """Sessions DU DÉPÔT : registre natif dont le cwd est la racine ou un worktree, joint aux bulletins.

    Rend `(sessions VIVANTES, noms des MORTES, états de vie observés)`. Le registre natif n'efface pas
    l'entrée d'une session terminée : sans le filtre `alive`, le tableau opposait des fantômes à des
    vivants (A1, A6) et comptait des sessions qui n'existent plus.

    `compute` tient l'invariant « norm des deux côtés » elle-même : `repo_root` et chaque `w["path"]`
    sont re-normalisés ici, sans supposer que le snapshot les a déjà normalisés (un registre natif
    peut écrire un `cwd` à BACKSLASHES sur Windows)."""
    racines = {norm(snap["repo_root"])} | {norm(w["path"]) for w in (snap.get("worktrees") or [])}
    bull = {b.get("session_id"): b for b in (snap.get("bulletins") or []) if b.get("session_id")}
    out, mortes, vies = [], [], []
    for r in (snap.get("registry") or []):
        if "illisible" in r or not r.get("cwd"):
            continue
        cwd = norm(r["cwd"])
        if not any(cwd == x or cwd.startswith(x + "/") for x in racines):
            continue
        vies.append(r.get("alive"))
        if r.get("alive") is False:
            mortes.append(r.get("name") or r.get("session_id") or "?")
            continue
        b = bull.get(r.get("session_id"), {})
        out.append({"name": r.get("name"), "session_id": r.get("session_id"), "pid": r.get("pid"), "cwd": cwd,
                    "started_at": r.get("started_at"), "branch": b.get("branch"),
                    "claims": list(b.get("claims") or []), "claims_inferes": [],
                    "files_touched": list(b.get("files_touched") or []),
                    # dernier contact par fichier et dernière écriture du bulletin (défaut 3) : absents d'un
                    # bulletin légataire, ils restent absents — {} et None, jamais une date inventée
                    "files_touched_at": dict(b.get("files_touched_at") or {}), "updated_at": b.get("updated_at"),
                    # P2.118 : un COMPTE de commandes Bash qui peuvent avoir écrit, jamais leurs textes ni des noms ;
                    # None = jamais compté (hook absent ou aucun marqueur), jamais un 0 fabriqué
                    "bash_ecritures_possibles": b.get("bash_ecritures_possibles"),
                    "heartbeat_at": b.get("heartbeat_at"), "bulletin": bool(b)})
    return out, mortes, vies


def _inferer_claims(sessions, backlog_paths, backlog_ok):
    if not backlog_ok:
        return
    for s in sessions:
        touches = set(s["files_touched"])
        s["claims_inferes"] = sorted(p for p, chemins in backlog_paths.items() if touches & set(chemins))


def _alertes(snap, sessions, now, backlog_ok):
    A, aveugle = [], []

    def add(id_, cle, gravite, message, preuve):
        A.append({"id": id_, "cle": f"{id_}:{cle}", "gravite": gravite, "message": message, "preuve": preuve})

    if snap.get("registry") is None:
        aveugle.append("registre natif (~/.claude/sessions)")
    if snap.get("bulletins") is None:
        aveugle.append("bulletins de session (paths.sessions_dir)")
    else:                                                       # A1 — un fichier, deux sessions vivantes
        # Clé = cwd + chemin RELATIF. Deux sessions travaillant dans deux worktreeS différents sur
        # `src/paths.py` éditent DEUX fichiers distincts : les apparier était un faux positif — et
        # c'est le cas NORMAL de ce dépôt, qui multiplie les worktrees.
        # ⚠️ P2.119 (2026-09-26) : un chemin déjà ABSOLU est une clé À LUI SEUL, appariée SANS le cwd. Le coller derrière
        # le cwd fabriquait « <racine>/c:/users/… » et un lieu FAUX (« dans <racine> ») pour un fichier hors de l'arbre —
        # la mémoire de projet de Claude —, et la clé (cwd, f) séparait ce qui est le MÊME fichier pour deux sessions de
        # worktrees différents : l'alerte vraie à cwd égal, et l'angle mort exactement inverse dès que les cwd diffèrent.
        par_fichier = {}
        for s in sessions:
            for f in s["files_touched"]:
                e = par_fichier.setdefault((None, f) if _absolu(f) else (s["cwd"], f), {"noms": set(), "cwds": set()})
                e["noms"].add(_nom(s))
                e["cwds"].add(s["cwd"])
        for (cwd, f), e in sorted(par_fichier.items(), key=lambda kv: (kv[0][0] or "", kv[0][1])):
            noms = e["noms"]
            if len(noms) < 2:
                continue
            if cwd is None:
                add("A1", f, "alerte",
                    f"{f} (chemin absolu, hors de l'arbre de la session : partagé par toutes les sessions) touché par "
                    f"{len(noms)} sessions vivantes : {', '.join(sorted(noms))}",
                    {"fichier": f, "cwds": sorted(c for c in e["cwds"] if c), "sessions": sorted(noms)})
            else:
                add("A1", f"{cwd}/{f}", "alerte",
                    f"{f} touché par {len(noms)} sessions vivantes dans {cwd} : {', '.join(sorted(noms))}",
                    {"fichier": f, "cwds": [cwd], "sessions": sorted(noms)})

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
            # VERROUILLÉ = gardé DÉLIBÉRÉMENT (git refuse de le supprimer) : le signaler chaque tick
            # est du bruit qu'aucune action n'éteint.
            if w["path"] == snap["repo_root"] or w["path"] in cwds or w.get("locked"):
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
    cpu = snap.get("cpu_pct")
    if cpu is not None and cpu > SEUILS["cpu_pct"]:
        add("A5", "cpu", "alerte", f"charge CPU instantanée (1 s) = {cpu:.0f} % > {SEUILS['cpu_pct']:.0f} %",
            {"cpu_pct": cpu})

    hooks = snap.get("hook_errors")                             # A9 — un hook qui échoue DEUX fois (spec §5)
    if hooks is None:
        aveugle.append("journal des hooks (hook_errors.log)")
    else:
        for ev, n in sorted(hooks.items()):
            if n >= 2:
                add("A9", f"hook:{ev}", "alerte",
                    f"le hook {ev} a échoué {n} fois en 24 h : la cause est dans hook_errors.log "
                    f"(un hook sort 0 quoi qu'il arrive — son échec ne se voit NULLE PART ailleurs)",
                    {"event": ev, "erreurs": n})

    par_claim = {}                                              # A6 — même P-item
    for s in sessions:
        for c in s["claims"]:
            par_claim.setdefault(c, set()).add(_nom(s))
    for c, noms in sorted(par_claim.items()):
        if len(noms) >= 2:
            add("A6", c, "alerte", f"{c} revendiqué par {', '.join(sorted(noms))}", {"p_item": c, "sessions": sorted(noms)})

    # A7 / A8 — informations (A7 dépend de `backlog_ok`). Clé = `session_id`, JAMAIS le nom : le journal suit
    # une alerte par sa clé, et un nom CHANGE (redémarrage de la flotte du 2026-09-24 : agagi-52 -> agagi-00,
    # agagi-aa -> agagi-2f…). Clé par nom, un renommage marquait l'alerte « suivie » (journal : « suivie
    # A7:agagi-52 ») et en émettait une « nouvelle » sous l'autre nom — un suivi FABRIQUÉ, compté dans
    # suivies_48h. Le nom reste dans le message et la preuve : c'est lui qu'on lit, pas lui qu'on suit.
    # (Une session sans bulletin est sautée : quand on arrive ici, `session_id` a servi à la jointure, il existe.)
    for s in sessions:
        if not s["bulletin"]:
            continue
        sid, qui = s["session_id"], {"session": _nom(s), "session_id": s["session_id"]}
        age_h = _h(now - s["started_at"]) if s.get("started_at") else None
        if age_h is not None and age_h > SEUILS["sans_claim_h"] and not s["claims"] and not s["claims_inferes"] and backlog_ok:
            add("A7", sid, "info", f"{_nom(s)} active depuis {age_h:.1f} h sans P-item revendiqué ni inféré", qui)
        hb = s.get("heartbeat_at")
        if hb is not None and _h(now - hb) > SEUILS["heartbeat_h"]:
            add("A8", sid, "info", f"{_nom(s)} : heartbeat vieux de {_h(now - hb):.1f} h, PID vivant", qui)
    return A, aveugle


def compute(snap, now=None):
    now = float(snap.get("now")) if now is None else float(now)
    backlog_ok = snap.get("backlog_paths") is not None          # prédicat UNIQUE : A7 et l'inférence le partagent
    sessions, mortes, vies = _sessions(snap)
    _inferer_claims(sessions, snap.get("backlog_paths"), backlog_ok)
    alertes, aveugle = _alertes(snap, sessions, now, backlog_ok)
    if not backlog_ok:
        aveugle.append("backlog (chemins cités par les entrées)")
    if vies and all(v is None for v in vies):
        aveugle.append("vie des sessions (psutil absent)")
    n_ill = sum(1 for r in (snap.get("registry") or []) if "illisible" in r)
    if n_ill:                                                   # DÉTECTÉ par le lecteur, et jusqu'ici AVALÉ ici
        aveugle.append(f"{n_ill} entrée(s) de registre illisible(s)")
    n_bul = sum(1 for b in (snap.get("bulletins") or []) if "illisible" in b or not b.get("session_id"))
    if n_bul:
        aveugle.append(f"{n_bul} bulletin(s) sans session_id ou illisible(s)")
    sans_bulletin = [_nom(s) for s in sessions if not s["bulletin"]]
    if sans_bulletin:
        # Une session sans bulletin n'a NI fichiers en vol NI claims NI heartbeat : A1, A6, A7 et A8
        # sont muettes sur elle. Zéro alerte y ressemble à « rien à signaler ».
        aveugle.append(f"bulletin absent pour {len(sans_bulletin)} session(s) : {', '.join(sans_bulletin)}")
    procs, leases = snap.get("processes"), snap.get("leases")
    charge = {"sims_en_vol": (sum(1 for p in procs if p.get("simulation")) if procs is not None else None),
              "cpu_pct": snap.get("cpu_pct"),
              "bails_vivants": ([l["resource"] for l in leases["live"]] if leases is not None else None)}
    return {"generated_at": now, "repo_root": snap["repo_root"], "aveugle": aveugle, "sessions": sessions,
            "sessions_mortes": mortes, "alertes": alertes, "charge_connue": charge,
            "worktrees": snap.get("worktrees"), "bails": leases}


def _bash_non_nommees(s):
    """« +2 écriture(s) Bash non nommée(s) », ou « » si rien n'a été compté (None = jamais compté : rien à dire)."""
    k = int(s.get("bash_ecritures_possibles") or 0)
    return f"+{k} écriture(s) Bash non nommée(s)" if k else ""


def _fichiers_en_vol(s):
    """Cellule du tableau : « 3 » ou « 3 (+2 écriture(s) Bash non nommée(s)) » — le compte P2.118 voyage à côté de la
    liste, jamais dedans."""
    b = _bash_non_nommees(s)
    return f"{len(s['files_touched'])}" + (f" ({b})" if b else "")


def render_md(board):
    L = ["# Tableau PM", f"généré : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(board['generated_at']))}"]
    for a in board["aveugle"]:
        L.append(f"AVEUGLE SUR {a}")
    c = board["charge_connue"]
    L += ["", "## Charge connue",
          f"simulations en vol : {c['sims_en_vol']} · CPU instantané (1 s) : {c['cpu_pct']} % · bails vivants : {c['bails_vivants']}",
          "", "## Sessions", "| session | branche | P-items | inférés | fichiers en vol | heartbeat |", "| --- | --- | --- | --- | --- | --- |"]
    for s in board["sessions"]:
        hb = f"{_h(board['generated_at'] - s['heartbeat_at']):.1f} h" if s.get("heartbeat_at") else "—"
        L.append(f"| {_nom(s)} | {s.get('branch') or '—'} | {', '.join(s['claims']) or '—'} | "
                 f"{', '.join(s['claims_inferes']) or '—'} | {_fichiers_en_vol(s)} | {hb} |")
    L.append(f"\n{CECITE_FICHIERS}")
    if board.get("sessions_mortes"):
        L.append(f"\nsessions MORTES écartées du tableau (PID disparu, entrée encore au registre) : "
                 f"{', '.join(board['sessions_mortes'])}")
    L += ["", f"## Alertes ({len(board['alertes'])})"]
    for a in board["alertes"]:
        L.append(f"- [{a['gravite']}] {a['cle']} — {a['message']}")
    L += ["", "## Worktrees"]
    for w in (board.get("worktrees") or []):
        L.append(f"- {w['path']} ({w.get('branch')}) fusionné={w.get('merged')}")
    return "\n".join(L) + "\n"


def summary(board, max_lines=25, age_s=None, source_age=None):
    """Ce qu'une session lit à sa naissance : l'ÂGE du tableau, aveuglements, charge, qui est sur quoi, alertes.

    L'âge est publié en TÊTE, toujours : un résumé en cache sans âge fait passer du périmé pour du courant.
    `age_s=None` s'imprime « âge INCONNU » — jamais un silence. Au-delà de PEREMPTION_S, le hook de démarrage
    n'appelle pas ce résumé comme courant (bulletin.resume_tableau)."""
    age = f"âge {texte_age(age_s)}" + (f" ({source_age})" if source_age else "")
    L = [f"[PM] tableau du {time.strftime('%Y-%m-%d %H:%M', time.localtime(board['generated_at']))} — {age}, "
         f"périmé au-delà de {texte_age(PEREMPTION_S)} — {len(board['sessions'])} sessions AGAGI"]
    L += [f"[PM] AVEUGLE SUR {a}" for a in board["aveugle"]]
    c = board["charge_connue"]
    L.append(f"[PM] charge : sims={c['sims_en_vol']} cpu={c['cpu_pct']} bails={c['bails_vivants']}")
    if board.get("sessions_mortes"):
        L.append(f"[PM] sessions MORTES écartées : {', '.join(board['sessions_mortes'])}")
    for s in board["sessions"]:
        L.append(f"[PM] {_nom(s)} : {', '.join(s['claims'] or s['claims_inferes']) or 'sans P-item'} — {len(s['files_touched'])} fichiers en vol"
                 + (f", {_bash_non_nommees(s)}" if _bash_non_nommees(s) else ""))
    L.append(f"[PM] {CECITE_FICHIERS}")
    for a in board["alertes"]:
        L.append(f"[PM] {a['gravite'].upper()} {a['cle']} — {a['message']}")
    if len(L) > max_lines:
        L = L[:max_lines - 1] + [f"[PM] … {len(L) - max_lines + 1} lignes de plus dans BOARD.md"]
    return "\n".join(L)


def main(argv=None):
    ancrer_data_root()                                  # AVANT tout appel à paths.* : un worktree écrirait son PROPRE tableau
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
    print(md if args.stdout else summary(board, age_s=0.0, source_age="calculé à l'instant"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
