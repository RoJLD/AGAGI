"""Bulletin d'UNE session, écrit par SES hooks — jamais de mémoire (E10 : une règle documentée est violée).

    python -m tools.pm.bulletin start|tool|stop|end     # appelé par .claude/settings.json, JSON du hook sur stdin
    python -m tools.pm.bulletin claim P4.9 [--session <id>]   # revendication volontaire d'un P-item

Le bulletin vit dans paths.sessions_dir("<session_id>.json"). Un hook sort TOUJOURS 0 : une erreur s'écrit dans
paths.pm_dir("hook_errors.log"), jamais dans la session. `start` imprime le résumé de BOARD.json en cache (jamais
recomputé ici : le hook doit rester sous la seconde) — c'est le PULL de la spec §3.1.

⚠️ Un résumé en CACHE a un âge, et il le PUBLIE (défaut mesuré le 2026-09-24) : le démarrage imprimait un
tableau vieux de ~31 h sans dire son âge, et annonçait « AVEUGLE SUR bulletin absent pour agagi-11, b0, d7,
c9 » alors que ces bulletins existaient. Une donnée PÉRIMÉE présentée comme courante FABRIQUE une alerte à
chaque démarrage. Au-delà de `PEREMPTION_S`, le démarrage dit PÉRIMÉ et ne réimprime pas les alertes.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback

from src import paths
from tools.pm.snapshot import REGISTRY_DIR_DEFAULT, ancrer_data_root, norm, read_registry

EVENTS = ("start", "tool", "stop", "end")
PLAFOND_FICHIERS = 200
REGISTRY_DIR = REGISTRY_DIR_DEFAULT              # monkeypatchable par les tests
MAX_JOURNAL_O = 1_000_000                        # au-delà : on garde la QUEUE
GARDE_JOURNAL_O = 200_000
TOLERANCE_FUTUR_S = 60.0                         # un tableau daté de PLUS d'une minute dans le futur est incohérent
_horloge = time.time                             # monkeypatchable : aucun test ne lit l'horloge du jour


def _vide(session_id):
    # `name` et `pid` viennent du REGISTRE natif, relu à chaque écriture ; `identite` dit l'état de la
    # dernière lecture ("registre", "absente du registre", "registre indisponible", "registre partiellement
    # illisible") et `identite_at` QUAND nom et pid y ont été lus pour la dernière fois — un `pid` à null
    # n'est jamais laissé passer pour une valeur sans que `identite` dise pourquoi.
    return {"session_id": session_id, "name": None, "pid": None, "identite": None, "identite_at": None,
            "noms_precedents": [], "cwd": None, "branch": None, "worktree": None,
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
        # le payload SessionStart ne porte PAS de pid (mesuré : null dans tous les bulletins) : il vient du
        # registre natif, dans `resoudre_identite`, comme le nom
        b["branch"], b["worktree"] = branche_fn(cwd)
    elif event == "tool":
        b["last_tool_at"] = now
        if b.get("cwd") is None and cwd:
            # cwd découvert tardivement (start manqué ou sans cwd) : fixé DÈS CE tool, pour lui et tous les suivants
            b["cwd"] = norm(cwd)
        fp = (payload.get("tool_input") or {}).get("file_path")
        if fp:
            rel = norm(fp)
            base = b.get("cwd")
            if base and rel.startswith(base + "/"):
                rel = rel[len(base) + 1:]
            # aucun cwd connu (ni bulletin ni payload) : chemin ABSOLU gardé tel quel -- valeur honnête, jamais laissé tomber
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


def identite_depuis_registre(session_id, registry_dir=None):
    """{"statut", "name", "pid"} de la session d'après le registre natif — relu, jamais mémorisé.

    Le nom n'est PAS une identité : au redémarrage de la flotte du 2026-09-24, TOUS les noms ont changé
    (agagi-11 -> agagi-e4, agagi-52 -> agagi-00, agagi-b0 -> looper…), et un nom se change aussi EN COURS de
    session (`looper` : nameSource=user, 103 s après le démarrage). Seul `session_id` est stable.

    Une session reprise laisse au registre l'entrée de son ANCIEN pid, même `sessionId` : on prend la plus
    RÉCENTE (`started_at`), jamais la première rencontrée — l'ordre du glob est celui des pids, et l'ancien
    pid peut trier devant. Sans mesure de vie (`avec_vie=False`) : psutil coûtait ~70 ms par outil.

    Une ABSENCE n'est affirmée que sur un registre lu en ENTIER : si une entrée est illisible, la session y
    est peut-être — le statut le dit, et `resoudre_identite` garde alors le dernier nom lu."""
    reg = read_registry(registry_dir or REGISTRY_DIR, avec_vie=False)
    if reg is None:
        return {"statut": "registre indisponible", "name": None, "pid": None}
    cands = [r for r in reg if "illisible" not in r and r.get("session_id") == session_id]
    if cands:
        r = max(cands, key=lambda x: x.get("started_at") or float("-inf"))
        return {"statut": "registre", "name": r.get("name"), "pid": r.get("pid")}
    if any("illisible" in r for r in reg):
        return {"statut": "registre partiellement illisible", "name": None, "pid": None}
    return {"statut": "absente du registre", "name": None, "pid": None}


def resoudre_identite(bul, ident, now):
    """PUR : applique une lecture du registre au bulletin.

    - lue : `name`/`pid` REMPLACÉS (jamais gelés à la première écriture — le défaut corrigé ici) ;
    - absente d'un registre lu en entier : `name`/`pid` remis à None, et `identite` dit pourquoi ;
    - registre indisponible ou partiellement illisible : `name`/`pid` GARDÉS, `identite_at` dit de quand ils datent.
    Un nom remplacé passe dans `noms_precedents` (10 derniers) : c'est lui qui permet de relire un vieux message
    ou une vieille alerte adressés à un nom que plus personne ne porte."""
    b = dict(bul)
    precedent = b.get("name")
    if ident["statut"] == "registre":
        b["name"], b["pid"], b["identite_at"] = ident["name"], ident["pid"], now
    elif ident["statut"] == "absente du registre":
        b["name"], b["pid"], b["identite_at"] = None, None, now
    b["identite"] = ident["statut"]
    if precedent and precedent != b.get("name"):
        b["noms_precedents"] = [n for n in (b.get("noms_precedents") or []) if n != precedent][-9:] + [precedent]
    return b


def nom_depuis_registre(session_id, registry_dir=None):
    return identite_depuis_registre(session_id, registry_dir)["name"]


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


RELANCER = ("[PM] relancer — une passe : python -m tools.pm.board (15-18 s ; tableau seul, ni journal ni bail) · "
            "en continu : /pm en boucle (/loop) dans UNE session dédiée")


def age_tableau(board, chemin, now):
    """(âge en s, source de l'âge) du tableau en cache ; (None, None) si rien ne le date.

    Source PRÉFÉRÉE : `generated_at`, l'instant où le tick a MESURÉ la flotte — c'est l'âge des DONNÉES, et il
    voyage avec le contenu. Le mtime date l'ÉCRITURE du fichier : une copie, une restauration ou un script qui
    réécrit un vieux tableau le rajeunit sans rajeunir ce qu'il décrit — exactement la faute corrigée ici (du
    périmé présenté comme courant). Le mtime n'est donc qu'un REPLI, dit comme tel : le fichier est écrit APRÈS
    la mesure, l'âge qu'il donne est une borne BASSE de l'âge des données."""
    g = board.get("generated_at") if isinstance(board, dict) else None
    if isinstance(g, (int, float)) and not isinstance(g, bool):
        return now - float(g), "generated_at"
    try:
        return now - os.path.getmtime(chemin), "mtime du fichier, generated_at absent : borne BASSE"
    except OSError:
        return None, None


def texte_age(age_s):
    """Lisible par un humain chaque matin : minutes sous 90 min, heures au-delà."""
    if age_s is None:
        return "âge INCONNU"
    if abs(age_s) < 90 * 60:
        return f"{age_s / 60:.0f} min"
    return f"{age_s / 3600:.1f} h"


def perime(board, chemin, age_s, source, seuil_s):
    """Ce que le démarrage imprime À LA PLACE des alertes quand le tableau n'est pas courant. Appelée
    APRÈS un `summary` réussi : les trois listes comptées ci-dessous y ont donc été lues sans erreur."""
    n_al, n_av, n_se = len(board["alertes"]), len(board["aveugle"]), len(board["sessions"])
    archive = os.path.join(os.path.dirname(chemin), "BOARD.md").replace("\\", "/")
    if age_s is None:
        tete = "[PM] TABLEAU D'ÂGE INCONNU : ni generated_at ni mtime lisibles — rien ne permet de le dire courant."
    elif age_s < 0:
        tete = (f"[PM] TABLEAU DATÉ DU FUTUR de {texte_age(-age_s)} ({source}) : horloge changée ou fichier "
                f"réécrit à la main — rien ne permet de le dire courant.")
    else:
        tete = (f"[PM] TABLEAU PÉRIMÉ : mesuré il y a {texte_age(age_s)} ({source}). Seuil {texte_age(seuil_s)} = TTL "
                f"du bail pm : au-delà, aucun tick n'a renouvelé ce bail — le tick NE TOURNE PAS.")
    return "\n".join([tete,
                      f"[PM] ses {n_al} alerte(s), {n_av} aveuglement(s) et {n_se} session(s) décrivent CETTE "
                      f"heure-là : NON réimprimés comme courants (archive : {archive}).",
                      RELANCER])


def resume_tableau(pm_dir=None, now=None):
    """Résumé du tableau en cache, TOUJOURS daté ; PÉRIMÉ (sans ses alertes) au-delà de `board.PEREMPTION_S`.

    ⚠️ Ne JAMAIS corriger la péremption en recalculant ici : `snapshot()` coûte 15 à 18 s, un hook de
    démarrage doit rester sous la seconde. Le remède est que le tick tourne ; le démarrage, lui, DIT qu'il
    ne tourne pas."""
    p = os.path.join(pm_dir or paths.pm_dir(), "BOARD.json")
    now = _horloge() if now is None else float(now)
    try:
        with open(p, encoding="utf-8") as fh:
            board = json.load(fh)
    except (OSError, ValueError):
        return "[PM] tableau absent : lancer python -m tools.pm.board (ou la session PM n'a pas encore tourné)"
    from tools.pm.board import PEREMPTION_S, summary
    age_s, source = age_tableau(board, p, now)
    try:
        corps = summary(board, age_s=age_s, source_age=source)
    except (KeyError, TypeError, AttributeError) as exc:
        return (f"[PM] tableau illisible ({type(exc).__name__}: {exc}) — âge {texte_age(age_s)} ({source}) : "
                f"relancer python -m tools.pm.board")
    if age_s is None or age_s < -TOLERANCE_FUTUR_S or age_s > PEREMPTION_S:
        return perime(board, p, age_s, source, PEREMPTION_S)
    return corps


def _rotation(p, max_o=None, garde_o=None):
    """Un hook cassé écrit ~2 ko à CHAQUE outil : sans rotation, le journal grossit sans borne dans
    `data/` et finit par coûter plus cher à lire qu'il ne rapporte. On garde la QUEUE — les échecs
    récents sont les seuls que `read_hook_errors` regarde (fenêtre 24 h). Écriture tmp + `os.replace`,
    comme le bulletin : jamais de fichier à moitié réécrit.

    Les plafonds sont résolus à l'APPEL, pas figés en valeurs par défaut : une valeur par défaut
    capturée à la définition rend la constante de module immuable, donc le mécanisme intestable."""
    max_o = MAX_JOURNAL_O if max_o is None else max_o
    garde_o = GARDE_JOURNAL_O if garde_o is None else garde_o
    try:
        if os.path.getsize(p) <= max_o:
            return
        with open(p, "rb") as fh:
            fh.seek(-garde_o, os.SEEK_END)
            queue = fh.read()
        tmp = p + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(queue)
        os.replace(tmp, p)
    except OSError:
        pass                                            # rotation impossible : on écrit quand même l'échec


def _journal(event, exc):
    try:
        os.makedirs(paths.pm_dir(), exist_ok=True)
        if os.path.exists(paths.pm_dir("hook_errors.log")):
            _rotation(paths.pm_dir("hook_errors.log"))
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
    now = _horloge()
    bul = appliquer(event, payload, charger(sid), now=now, branche_fn=branche_git)
    # à CHAQUE écriture, pas seulement la première : le nom était gelé au premier hook (`if name is None`),
    # et le tableau adressait ses alertes à des noms morts. Coût mesuré : ~2 ms (registre sans psutil).
    bul = resoudre_identite(bul, identite_depuis_registre(sid), now)
    ecrire(bul)
    if event == "start":
        print(resume_tableau(now=now))


def _claim(p_item, session):
    sid = session or session_id_courant()
    if not sid:
        print("[PM] claim ignoré : session introuvable (passer --session <id> ; le registre natif ne connaît pas ce processus)")
        return
    bul = dict(_vide(sid), **charger(sid))
    if p_item not in bul["claims"]:
        bul["claims"].append(p_item)
    bul = resoudre_identite(bul, identite_depuis_registre(sid), _horloge())
    ecrire(bul)
    print(f"[PM] {bul.get('name') or sid} revendique {', '.join(bul['claims'])}")


def main(argv=None):
    ancrer_data_root()                                  # AVANT tout paths.* : sinon un worktree tient SON propre data/
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("event", choices=EVENTS + ("claim",))
    ap.add_argument("p_item", nargs="?", default=None)
    ap.add_argument("--session", default=None)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:                           # argv mal formé (event inconnu, positionnel manquant) : un hook
        if exc.code not in (0, None):                   # sort TOUJOURS 0 -- argparse a déjà imprimé l'usage sur stderr
            _journal("argv", exc)                       # `--help` sort 0 : ce n'est PAS un échec, ne pas le journaliser
        return 0
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
