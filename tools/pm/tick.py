"""Le tick de la session PM — la partie DÉTERMINISTE (spec §3.3) :

    python -m tools.pm.tick [--owner <name>] [--pid <pid de la session Claude>]

1. bail `pm` porté par le PID de la session Claude (unicité : un autre PM VIVANT -> exit 2, rien d'écrit) ;
2. tableau (BOARD.json / BOARD.md) ; 3. diff des alertes contre le journal, append ; 4. compteurs ;
5. un DIGEST pour la session PM : ce qui demande un jugement (message ciblé, investigation, cliquet à inscrire).
La session PM ne tient aucun état en contexte : tout est relu d'ici à chaque tick.
"""
import argparse
import json
import os
import sys
import time

from src import paths
from tools.jobs import lease as L
from tools.pm import alerts as AL
from tools.pm import roles_counts as RC
from tools.pm.board import CECITE_FICHIERS, TTL_PM_S, compute, render_md  # TTL_PM_S : défini au TABLEAU, seuil de péremption
from tools.pm.bulletin import session_id_courant
from tools.pm.snapshot import ancrer_data_root, read_registry, snapshot


def prendre_bail_pm(owner, pid, *, leases_dir=None, ttl_s=TTL_PM_S):
    cur = L.read("pm", leases_dir=leases_dir)
    if cur is not None and L.is_live(cur) and cur.pid != pid:
        return {"ok": False, "detenteur": f"{cur.owner or '?'} (pid={cur.pid}, expire dans {cur.expires_at - time.time():.0f} s)"}
    try:
        L.acquire("pm", owner=owner, ttl_s=ttl_s, pid=pid, leases_dir=leases_dir)
    except L.ResourceBusy:
        cur = L.read("pm", leases_dir=leases_dir)
        return {"ok": False, "detenteur": f"{cur.owner or '?'} (pid={cur.pid}, expire dans {cur.expires_at - time.time():.0f} s)"
                if cur else "inconnu (bail pris entre la lecture et l'acquisition)"}
    return {"ok": True, "detenteur": None}


def _identite(registry_dir):
    """(name, pid) de la session Claude qui lance le tick, via le registre natif ; (None, None) si inconnu."""
    sid = session_id_courant(registry_dir)
    for r in (read_registry(registry_dir) or []):
        if sid and r.get("session_id") == sid:
            return r.get("name"), r.get("pid")
    return None, None


def digest(board, d, counts, illisibles=0):
    L_ = [f"[PM] AVEUGLE SUR {a}" for a in board["aveugle"]]
    # Deux aveuglements étaient DÉTECTÉS par la couche du dessous puis AVALÉS ici : le journal des
    # alertes compte ses lignes illisibles (`AL.charger.illisibles`) et `fichiers_modifies` rend None
    # quand git est muet. Sans ces deux lignes, le digest affichait des compteurs incomplets
    # exactement comme des compteurs complets.
    if illisibles:
        L_.append(f"[PM] journal des alertes : {illisibles} ligne(s) illisible(s)")
    if counts.get("fichiers_disponibles") is False:
        L_.append("[PM] AVEUGLE SUR git (fichiers modifiés non mesurés)")
    c = board["charge_connue"]
    L_.append(f"[PM] charge connue : sims={c['sims_en_vol']} cpu={c['cpu_pct']} bails={c['bails_vivants']}")
    L_.append(f"[PM] {CECITE_FICHIERS}")                # une A1 absente ne prouve rien sur ce que Bash a réécrit
    for a in d["nouvelles"]:
        L_.append(f"[PM] NOUVELLE {a['cle']} ({a['gravite']}) — {a['message']} -> décider : message ciblé / investigation / note")
    for a in d["repetees"]:
        L_.append(f"[PM] REPETEE {a['cle']} — {a['message']} -> inscrire le cliquet manquant au backlog (deux fois = promu)")
    # une clé suivie se lit avec son MESSAGE : les clés A7/A8 sont des session_id, illisibles seules
    msg = {l["cle"]: l.get("message") for l in d["lignes"] if l.get("statut") == "suivie"}
    for k in d["disparues"]:
        L_.append(f"[PM] suivie {k}" + (f" — {msg[k]}" if msg.get(k) else ""))
    ca = counts["alertes"]
    L_.append(f"[PM] compteurs : émises {ca['emises']} · suivies 48 h {ca['suivies_48h']} · fausses/ignorées "
              f"{ca['fausses_ou_ignorees']} · répétées {ca['repetees']} · ouvertes {ca['ouvertes']} ; "
              f"fichiers {counts['fichiers']} ; science/méthodo = {counts['ratio_science_methodo']}")
    if not d["nouvelles"] and not d["repetees"] and not d["disparues"]:
        L_.append("[PM] rien de nouveau (noop)")
    return "\n".join(L_)


def main(argv=None):
    ancrer_data_root()                                  # AVANT tout paths.* : le tableau du PM vit dans le dépôt COMMUN
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--owner", default=None)
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--registry-dir", default=None)
    ap.add_argument("--sessions-dir", default=None)
    ap.add_argument("--leases-dir", default=None)
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    name, pid = _identite(args.registry_dir)
    owner, pid = args.owner or name or "pm-inconnu", args.pid or pid or os.getpid()
    bail = prendre_bail_pm(owner, pid, leases_dir=args.leases_dir)
    if not bail["ok"]:
        print(f"[PM] REFUS : un PM VIVANT tient déjà le bail pm : {bail['detenteur']}. Cette session ne prend pas le rôle.")
        return 2
    now = time.time()
    board = compute(snapshot(args.repo_root, registry_dir=args.registry_dir, sessions_dir=args.sessions_dir,
                             leases_dir=args.leases_dir, now=now))
    os.makedirs(paths.pm_dir(), exist_ok=True)
    with open(paths.pm_dir("BOARD.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=1, default=str)
    with open(paths.pm_dir("BOARD.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(board))
    journal = AL.charger(paths.pm_dir("alerts.jsonl"))
    illisibles = AL.charger.illisibles                  # capturé TOUT DE SUITE : un autre `charger` le remettrait à 0
    d = AL.diff(board, journal, now)
    AL.ajouter(paths.pm_dir("alerts.jsonl"), d["lignes"])
    counts = RC.compute_counts(journal + d["lignes"], RC.fichiers_modifies(args.repo_root, now=now), now)
    with open(paths.pm_dir("ROLES_COUNTS.json"), "w", encoding="utf-8") as fh:
        json.dump(counts, fh, ensure_ascii=False, indent=1)
    print(digest(board, d, counts, illisibles=illisibles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
