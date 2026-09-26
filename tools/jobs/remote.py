# -*- coding: utf-8 -*-
"""Déport des runs AGAGI sur le cluster ELYSIUM (nœud nexus) — soumettre, attendre, rapatrier.

Livrable (3) de la session INFRA-NEXUS (2026-09-26). Doc opératoire : docs/REF/REF-DEPORT-NEXUS.md.

    python -m tools.jobs.remote executer --sha HEAD -- -m tools.evo_runs.<runner> <args>
    python -m tools.jobs.remote local    --sha HEAD -- -m tools.evo_runs.<runner> <args>   # même chemin, batcave
    python -m tools.jobs.remote image                                   # (re)construit l'image runner
    python -m tools.jobs.remote soumettre|attendre|rapatrier|installer|etat ...   # étapes une à une
    (--env CLE=VALEUR, répétable : la SEULE façon de passer une variable au runner, des deux côtés)

Ce qui voyage, et pourquoi ainsi :
  * le CODE au sha exact, comme DÉPÔT GIT SUPERFICIEL (profondeur 1, blobs du commit sans conversion de fin
    de ligne) poussé dans le pod par `kubectl exec` : n'importe quel commit LOCAL tourne (pas besoin qu'il
    soit poussé — seul l'intégrateur pousse), le pod n'a besoin ni de GitHub ni d'un jeton, et HEAD + arbre
    propre sont vérifiés DANS le pod avant exécution (tools/jobs/remote_entry.py). Un vrai `.git` parce que
    les runners tamponnent leur provenance par git (P2.68) ; pas `git archive`, qui sur la batcave applique
    `core.autocrlf=true` et livrerait des sources en CRLF. Aucun secret dans le dépôt : le seul identifiant
    est le kubeconfig de la batcave (~/.kube/config), hors dépôt. ⚠️ SEULS les fichiers SUIVIS au sha
    voyagent : une entrée non suivie (génome, HoF, base kuzu) n'existe pas dans le pod — la soumission la
    signale, elle ne peut pas savoir si le runner la lit.
  * l'ENVIRONNEMENT : rien d'implicite. Le pod n'a que celui de l'image ; `local` part d'un environnement
    système MINIMAL ; dans les deux cas, les `--env` déclarés sont ajoutés et publiés dans le MANIFEST.
    (Revue du 2026-09-26 : `SRA_SMOKE=1` exporté sur la batcave aurait lancé un run COMPLET sur nexus.)
  * les RÉSULTATS écrits en local dans le pod (emptyDir), puis TIRÉS par la batcave depuis le pod vivant,
    vérifiés fichier par fichier contre le MANIFEST (sha256), installés à leur chemin relatif (results/...).
    Jamais un fichier NON SUIVI ou MODIFIÉ n'est écrasé ; en cas de conflit, la sortie vérifiée est
    CONSERVÉE sous runs/deport/<job>/sortie_non_installee/ (rien n'est perdu), à installer ensuite.
    AUCUN montage NFS dans un pod de run : un montage `nfs:` en ligne est `hard`, un atlas à terre fige le pod
    puis le kubelet (incident ELYSIUM du 01/09), et ELYSIUM a rétrogradé atlas en cible de réplication
    copy-only (SIGIL-1764) ; il était éteint le 2026-09-26.
  * la LIMITE CPU lue dans le cgroup du pod (`/sys/fs/cgroup/cpu.max`), jamais `os.cpu_count()` (l'hôte).

nexus n'est PAS allumé en permanence : fenêtre 08:00-00:00 Europe/Paris, extinction IPMI DURE à minuit, et
robla l'éteint aussi par intermittence. Tout envoi vérifie que le nœud est Ready ET que le run tient avant
minuit, et REFUSE sinon, en nommant la voie d'allumage — sans l'appeler.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

_ICI = Path(__file__).resolve().parent
_ROOT = _ICI.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.grid_compare import cmp_continu  # noqa: E402
from tools.jobs import remote_entry as E  # noqa: E402

# ------------------------------------------------------------------------------------------ configuration
# AUCUNE adresse, aucun contexte, aucun nœud dans le dépôt (décision de robla, 2026-09-26 : le dépôt est PUBLIC, et
# le cluster comme le nœud peuvent changer). Lue dans les variables d'environnement, puis dans un fichier HORS dépôt
# (~/.agagi/deport.json, partagé par tous les worktrees de la machine ; chemin surchargeable par AGAGI_DEPORT_CONFIG).
# Une clé requise absente → Refus NOMMÉ avant tout effet, jamais une valeur devinée. Exemple sans adresse réelle :
# deploy/deport.example.json.
CONFIG_DEFAUT = os.path.join("~", ".agagi", "deport.json")
VARIABLES_CONFIG = {"contexte": "AGAGI_KUBE_CONTEXT", "registre": "AGAGI_REGISTRY", "noeud": "AGAGI_DEPORT_NOEUD",
                    "namespace": "AGAGI_DEPORT_NAMESPACE", "depot_image": "AGAGI_DEPORT_DEPOT_IMAGE",
                    "fenetre": "AGAGI_DEPORT_FENETRE", "allumage": "AGAGI_DEPORT_ALLUMAGE",
                    "ca_depuis": "AGAGI_DEPORT_CA_DEPUIS"}
# `fenetre` est REQUISE mais peut valoir null (nœud toujours allumé) : l'absence se DÉCLARE, elle ne se suppose pas.
CLES_REQUISES = ("contexte", "registre", "noeud", "namespace", "depot_image", "fenetre")
# Carte de propriété ELYSIUM (Σ-MANIFEST-MYCORHIZE, SIGIL-1762) : sans ces labels, un objet posé hors GitOps
# ELYSIUM apparaît comme zone d'ombre au sentinel gitops_orphan_paths (elysium-91, 2026-09-26).
LABELS_PROPRIETE = {"app.kubernetes.io/part-of": "agagi", "elysium.io/owner": "agagi",
                    "elysium.io/managed-by": "agagi", "elysium.io/source-repo": "RoJLD.AGAGI"}
RUNNER_DIR = "deploy/nexus/runner"
IMAGE_JSON = RUNNER_DIR + "/IMAGE.json"
FICHIERS_CONTEXTE = {"Dockerfile": f"{RUNNER_DIR}/Dockerfile", "constraints.txt": f"{RUNNER_DIR}/constraints.txt",
                     "requirements.txt": "requirements.txt", "build-job.yaml": f"{RUNNER_DIR}/build-job.yaml"}
# Plafond par conteneur = LimitRange `standard` du namespace (deploy/nexus/01-limitrange.yaml).
MAX_CPU, MAX_MEM_GI = 2.0, 4.0
JOURNAL_LOCAL = "runs/deport"          # runs/ est ignoré par git : journaux et MANIFEST des runs
MARGE_TRANSFERT_S = 1200               # préparation + tirage d'image + envoi des sources, borne haute
ATTENTE_MIN_S = 60
# Environnement de `local` : le strict nécessaire pour qu'un python tourne, RIEN de la session appelante.
_ENV_SYSTEME = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "TMPDIR",
                "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "HOME", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
                "PROGRAMFILES", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "OS", "USERNAME", "USER",
                "COMPUTERNAME", "LANG", "LC_ALL")
# Posées des DEUX côtés (l'image les pose par ENV, `local` ici) : même interprète, mêmes flux.
ENV_COMMUN = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
              "PYTHONUNBUFFERED": "1", "MPLBACKEND": "Agg"}


class Refus(RuntimeError):
    """Refus bruyant, AVANT tout effet : rien n'est créé, rien n'est écrit."""


def _fenetre_depuis_texte(v: str):
    """`aucune` (nœud toujours allumé, DÉCLARÉ) ou `fuseau,début_h,fin_h,marge_s` (ex. Europe/Paris,8,24,900)."""
    if v.strip().lower() == "aucune":
        return None
    parts = [x.strip() for x in v.split(",")]
    if len(parts) != 4:
        raise Refus(f"AGAGI_DEPORT_FENETRE attend « aucune » ou « fuseau,début_h,fin_h,marge_s », reçu {v!r}")
    return {"tz": parts[0], "debut_h": int(parts[1]), "fin_h": int(parts[2]), "marge_s": int(parts[3])}


def charger_config(env=None) -> dict:
    """La configuration du déport (cf. VARIABLES_CONFIG) : environnement d'abord, fichier hors dépôt ensuite.
    Refus NOMMÉ pour toute clé requise absente, pour un registre qui n'est pas « hôte:port », pour une fenêtre
    mal formée. Ne DEVINE rien : c'est ce qui garde l'adresse du cluster hors du dépôt."""
    env = os.environ if env is None else env
    chemin = Path(os.path.expanduser(env.get("AGAGI_DEPORT_CONFIG") or CONFIG_DEFAUT))
    fichier = {}
    if chemin.is_file():
        try:
            fichier = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise Refus(f"configuration du déport illisible ({chemin}) : {e}")
        if not isinstance(fichier, dict):
            raise Refus(f"configuration du déport ({chemin}) : un objet JSON est attendu")
    cfg, source = {}, {}
    for cle, var in VARIABLES_CONFIG.items():
        if env.get(var) not in (None, ""):
            cfg[cle] = _fenetre_depuis_texte(env[var]) if cle == "fenetre" else env[var]
            source[cle] = var
        elif cle in fichier:
            cfg[cle] = fichier[cle]
            source[cle] = str(chemin)
    manquantes = [c for c in CLES_REQUISES if c not in cfg or (cfg[c] in (None, "") and c != "fenetre")]
    if manquantes:
        raise Refus("configuration du déport incomplète : " + ", ".join(f"{c} ({VARIABLES_CONFIG[c]})" for c in manquantes)
                    + f" — à poser dans l'environnement ou dans {chemin} (modèle : deploy/deport.example.json). "
                    "Aucune valeur n'est devinée.")
    hote, sep, port = str(cfg["registre"]).rpartition(":")
    if not sep or not hote or not port.isdigit() or "/" in cfg["registre"]:
        raise Refus(f"registre attendu « hôte:port », reçu {cfg['registre']!r}")
    f = cfg["fenetre"]
    if f is not None and (not isinstance(f, dict) or set(f) != {"tz", "debut_h", "fin_h", "marge_s"}
                          or not 0 <= int(f["debut_h"]) < int(f["fin_h"]) <= 24):
        raise Refus(f"fenetre attendue null ou {{tz, debut_h, fin_h, marge_s}} avec 0 <= début < fin <= 24, reçu {f!r}")
    cfg["_source"] = source
    return cfg


def allumage(cfg: dict) -> str:
    return (f"nœud {cfg['noeud']} éteint ou indisponible. Voie d'allumage déclarée : "
            f"{cfg.get('allumage') or 'NON DÉCLARÉE (clé allumage)'} — geste humain, que cet outil ne fait JAMAIS "
            "lui-même. Sinon : `python -m tools.jobs.remote local`.")


# ------------------------------------------------------------------------------------------ git (local)
def _git(args, racine, entree=None, texte=True, verifier=True):
    """git sur le dépôt `racine`, environnement ISOLÉ de `GIT_*` et cible explicite (`-C`). Ce module ne
    juge jamais un INDEX de commit (il lit des COMMITS et l'état de l'arbre de destination), donc la face
    « hériter » de la règle de CLAUDE.md § Environnement ne s'applique pas ; un GIT_DIR hérité (hook,
    worktree — P2.121 famille 6) le ferait en revanche lire un autre dépôt que `racine`."""
    from tools._git_env import env_isole
    r = subprocess.run(["git", "-C", str(racine), *args], cwd=str(racine), capture_output=True, text=texte,
                       input=entree, env=env_isole())
    if verifier and r.returncode != 0:
        err = r.stderr if texte else r.stderr.decode("utf-8", "replace")
        raise Refus(f"git {' '.join(args)} : {err.strip()}")
    return r if not verifier else r.stdout


def racine_depot(cwd=None) -> Path:
    return Path(_git(["rev-parse", "--show-toplevel"], cwd or Path.cwd()).strip())


def sha_complet(sha: str, racine: Path) -> str:
    return _git(["rev-parse", "--verify", f"{sha}^{{commit}}"], racine).strip()


def preparer_source(sha: str, racine: Path) -> bytes:
    """tar.gz d'un dépôt SUPERFICIEL au commit `sha` : `git init` jetable, `fetch --depth 1` du sha depuis
    `racine`, checkout détaché SANS conversion de fin de ligne. Environnement isolé : le dépôt visé est le
    jetable, jamais celui de l'appelant (P2.121 famille 6)."""
    from tools._git_env import env_isole
    with tempfile.TemporaryDirectory(prefix="agagi-source-") as tmp:
        d = Path(tmp) / "src"
        for args in (["init", "-q", str(d)],
                     ["-C", str(d), "fetch", "-q", "--depth", "1", "--no-tags", str(racine), sha],
                     ["-C", str(d), "-c", "advice.detachedHead=false", "checkout", "-q", "--detach", "FETCH_HEAD"]):
            r = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "-c",
                                "init.defaultBranch=main", *args], capture_output=True, text=True, env=env_isole())
            if r.returncode != 0:
                raise Refus(f"préparation de la source au sha {sha[:8]} : git {args[-3:]} : {r.stderr.strip()}")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as tf:
            tf.add(str(d), arcname=".")
        return buf.getvalue()


def fichier_au_sha(sha: str, chemin: str, racine: Path) -> bytes:
    return _git(["show", f"{sha}:{chemin}"], racine, texte=False)


def _existe_au_sha(sha: str, chemin: str, racine: Path) -> bool:
    return _git(["cat-file", "-e", f"{sha}:{chemin}"], racine, verifier=False).returncode == 0


def entrees_non_suivies(racine: Path) -> list:
    """Entrées de `data/` présentes sur la batcave mais NON suivies (ignorées ou nouvelles) : elles n'existeront
    pas dans le pod. On ne sait pas si le runner les lit — on le DIT (revue 2026-09-26, I6 : un HoF absent
    se charge en liste vide, une base kuzu absente se crée vide)."""
    r = _git(["status", "--porcelain", "--ignored", "--untracked-files=normal", "--", "data"], racine,
             verifier=False)
    if r.returncode != 0:
        return [f"(git status illisible : {r.stderr.strip()[:120]})"]
    return sorted(l[3:] for l in r.stdout.splitlines() if l[:2] in ("??", "!!"))


# ------------------------------------------------------------------------------------------ fonctions pures
def valider_commande(commande: list) -> list:
    if commande[:1] == ["--"]:
        commande = commande[1:]
    if len(commande) < 2 or commande[0] != "-m" or not E._MODULE.match(commande[1]):
        raise Refus(f"commande attendue « -m <module> [args] » (python est implicite), reçu {commande!r}")
    return commande


def valider_env(paires) -> dict:
    """`--env CLE=VALEUR` → dict. Refuse ce qui déplacerait les écritures ou le code (mêmes règles que
    remote_entry), et les clés que le Job pose lui-même."""
    out = {}
    for p in paires or ():
        k, sep, v = p.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k):
            raise Refus(f"--env attend CLE=VALEUR : {p!r}")
        if E._ENV_INTERDITES.match(k) or k in ("AGAGI_IMAGE", "NODE_NAME", "HOME", "MPLCONFIGDIR"):
            raise Refus(f"--env {k} interdite (elle déplacerait les écritures, le code, ou la configuration du Job)")
        out[k] = v
    return out


def env_local(declare: dict, base: dict | None = None) -> dict:
    """Environnement MINIMAL de `local` : variables système + ENV_COMMUN + déclarées. Rien de la session
    appelante : ni ses `SRA_SMOKE`, ni ses `AGAGI_*_ROOT`, ni ses `GIT_*`."""
    base = os.environ if base is None else base
    out = {k: v for k, v in base.items() if k.upper() in _ENV_SYSTEME}
    out.update(ENV_COMMUN)
    out.update(declare)
    return out


def mem_en_gi(q: str) -> float:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(Mi|Gi)", q)
    if not m:
        raise Refus(f"quantité mémoire attendue en Mi ou Gi : {q!r}")
    return float(m.group(1)) / (1024.0 if m.group(2) == "Mi" else 1.0)


def valider_ressources(req_cpu: float, cpu: float, req_mem: str, mem: str) -> None:
    """Refuse AVANT soumission ce que la LimitRange refuserait APRÈS — un refus d'admission d'un pod de Job
    est SILENCIEUX (Job `0/1` sans pod : ELYSIUM image-ci README, Iron Rule 5)."""
    if not (0 < req_cpu <= cpu <= MAX_CPU):
        raise Refus(f"CPU : 0 < requête ({req_cpu}) <= limite ({cpu}) <= {MAX_CPU} (LimitRange standard)")
    if not (0 < mem_en_gi(req_mem) <= mem_en_gi(mem) <= MAX_MEM_GI):
        raise Refus(f"mémoire : 0 < requête ({req_mem}) <= limite ({mem}) <= {MAX_MEM_GI}Gi (LimitRange standard)")


def nom_job(commande: list, sha: str, suffixe: str | None = None) -> str:
    """Nom DNS-1123 ≤ 63 : agagi-<module court>-<sha7>-<aléa>. L'aléa rend deux soumissions identiques
    distinctes (un dépôt terminé ne se réécrit jamais)."""
    court = re.sub(r"[^a-z0-9]+", "-", commande[1].rsplit(".", 1)[-1].lower()).strip("-")[:30] or "run"
    return f"agagi-{court}-{sha[:7]}-{suffixe or secrets.token_hex(2)}"


def image_ref(info: dict, registre: str) -> str:
    """`registre/dépôt:tag@digest` : le tag pour l'humain (CNCE-3 exige un tag), le digest pour la machine. Le
    REGISTRE vient de la configuration, jamais d'IMAGE.json (qui est suivi : il ne porte que le chemin)."""
    return f"{registre}/{info['image']}:{info['tag']}@{info['digest']}"


def _secu_conteneur() -> dict:
    return {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True, "capabilities": {"drop": ["ALL"]}}


def fenetre_restante_s(fenetre, maintenant: _dt.datetime | None = None) -> float:
    """Secondes utilisables avant l'extinction du nœud (fin de sa fenêtre, marge déduite) ; 0 hors de la fenêtre ;
    l'infini si le nœud est DÉCLARÉ toujours allumé (fenetre = null). Pour nexus en 2026-09 : Europe/Paris,
    08:00-24:00, extinction IPMI DURE à minuit, sans drain (relevé par elysium-91). Fuseau illisible → refus."""
    if fenetre is None:
        return float("inf")
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(fenetre["tz"])
    except Exception as e:                                    # noqa: BLE001 — refus dit, pas avalé
        raise Refus(f"fuseau {fenetre.get('tz')!r} illisible ({e}) : la fenêtre du nœud ne peut pas être calculée")
    t = (maintenant or _dt.datetime.now(tz)).astimezone(tz)
    if t.hour < int(fenetre["debut_h"]) or t.hour >= int(fenetre["fin_h"]):
        return 0.0
    fin = t.replace(hour=0, minute=0, second=0, microsecond=0) + _dt.timedelta(hours=int(fenetre["fin_h"]))
    return max(0.0, (fin - t).total_seconds() - int(fenetre["marge_s"]))


def manifeste_job(*, nom, sha, image, commande, namespace, noeud, cpu=2.0, req_cpu=1.0, mem="4Gi", req_mem="1Gi",
                  attente_s=3600, deadline_s=2 * 3600, entry_sha256="", source_sha256="",
                  env_declare=None) -> dict:
    """Le Job d'UN run. Conformité ELYSIUM portée par construction (CNCE-1/3/5/8/11) et vérifiée par test.

    AUCUN volume NFS, par construction : un montage `nfs:` en ligne est `hard` (un pod ne peut pas le
    déclarer `soft`), et un atlas à terre FIGE alors le pod, puis le kubelet — incident ELYSIUM du 01/09 :
    WAL kine 8,9 Go, control-plane 3 h 50 à terre. La réplication vers atlas, si on la veut, se fait APRÈS
    le rapatriement, hors du run (atlas = cible copy-only, SIGIL-1764)."""
    valider_ressources(req_cpu, cpu, req_mem, mem)
    if attente_s < ATTENTE_MIN_S:
        raise Refus(f"--attente-s {attente_s} < {ATTENTE_MIN_S} s : la sortie serait perdue avant tout rapatriement")
    env_declare = dict(env_declare or {})
    labels = {**LABELS_PROPRIETE, "app.kubernetes.io/name": "agagi-run", "app.kubernetes.io/component": "run",
              "elysium.io/criticality": "disposable", "agagi.io/sha": sha[:40]}
    args = ["/xfer/remote_entry.py", "--source", "/xfer/source.tar.gz", "--sha", sha,
            "--source-sha256", source_sha256, "--work", "/work", "--out", "/out", "--job", nom, "--lieu", noeud,
            "--attendre-rapatriement", str(int(attente_s))]
    for k in sorted(env_declare):
        args += ["--env-declare", k]
    args += ["--", *commande]
    vols = [{"name": n, "emptyDir": {"sizeLimit": s}} for n, s in
            (("xfer", "256Mi"), ("work", "8Gi"), ("out", "4Gi"), ("tmp", "2Gi"))]
    # /dev/shm du runtime = 64 Mi : trop peu pour un runner multiprocess. Mémoire, donc compté dans la limite.
    vols.append({"name": "dshm", "emptyDir": {"medium": "Memory", "sizeLimit": "512Mi"}})
    montages = [{"name": "xfer", "mountPath": "/xfer", "readOnly": True}, {"name": "work", "mountPath": "/work"},
                {"name": "out", "mountPath": "/out"}, {"name": "tmp", "mountPath": "/tmp"},
                {"name": "dshm", "mountPath": "/dev/shm"}]
    env = ([{"name": "AGAGI_IMAGE", "value": image},
            {"name": "NODE_NAME", "valueFrom": {"fieldRef": {"fieldPath": "spec.nodeName"}}},
            {"name": "HOME", "value": "/tmp"}, {"name": "MPLCONFIGDIR", "value": "/tmp/mpl"}]
           + [{"name": k, "value": v} for k, v in sorted(ENV_COMMUN.items())]
           + [{"name": k, "value": v} for k, v in sorted(env_declare.items())])
    recevoir = ("i=0; while [ ! -f /xfer/.ready ]; do i=$((i+1)); if [ $i -gt 900 ]; then "
                "echo '[recevoir] FATAL: aucune source recue en 900 s'; exit 1; fi; sleep 1; done; "
                "echo '[recevoir] bundle recu'")
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": nom, "namespace": namespace, "labels": labels,
                     "annotations": {"agagi.io/sha": sha, "agagi.io/commande": json.dumps(commande),
                                     "agagi.io/env": json.dumps(env_declare, sort_keys=True),
                                     "agagi.io/entry-sha256": entry_sha256}},
        "spec": {
            "backoffLimit": 0,
            "activeDeadlineSeconds": int(deadline_s + attente_s + MARGE_TRANSFERT_S),
            "ttlSecondsAfterFinished": 86400,
            "template": {
                "metadata": {"labels": labels, "annotations": {"linkerd.io/inject": "disabled"}},
                "spec": {
                    "restartPolicy": "Never", "priorityClassName": "elysium-disposable",
                    "automountServiceAccountToken": False, "enableServiceLinks": False,
                    "nodeSelector": {"kubernetes.io/hostname": noeud},
                    "securityContext": {"runAsNonRoot": True, "runAsUser": 65534, "runAsGroup": 65534,
                                        "fsGroup": 65534, "seccompProfile": {"type": "RuntimeDefault"}},
                    "initContainers": [{
                        "name": "recevoir", "image": image, "command": ["sh", "-c", recevoir],
                        "resources": {"requests": {"cpu": "50m", "memory": "64Mi"},
                                      "limits": {"cpu": "200m", "memory": "128Mi"}},
                        "securityContext": _secu_conteneur(),
                        "volumeMounts": [{"name": "xfer", "mountPath": "/xfer"}]}],
                    "containers": [{
                        "name": "run", "image": image, "command": ["python"], "args": args, "env": env,
                        "resources": {"requests": {"cpu": str(req_cpu), "memory": req_mem},
                                      "limits": {"cpu": str(cpu), "memory": mem}},
                        "securityContext": _secu_conteneur(), "volumeMounts": montages}],
                    "volumes": vols}}}}


def paquet_de_transfert(archive_gz: bytes, entry: bytes) -> bytes:
    """tar (non compressé) : source.tar.gz, remote_entry.py, puis `.ready` EN DERNIER — `tar -x` écrit dans
    l'ordre de l'archive, donc `.ready` n'existe qu'une fois les deux autres fichiers complets."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for nom, donnees in (("source.tar.gz", archive_gz), ("remote_entry.py", entry), (".ready", b"")):
            ti = tarfile.TarInfo(nom)
            ti.size, ti.mode, ti.mtime = len(donnees), 0o644, 0
            tf.addfile(ti, io.BytesIO(donnees))
    return buf.getvalue()


# ------------------------------------------------------------------------------------------ rapatriement
def controler_sortie(sortie: Path, job: str, attendu: dict | None = None) -> dict:
    """La sortie d'un run est-elle INTÈGRE ? Rend le MANIFEST, ou refuse :

      * pas de MANIFEST (ou un REFUS.json) → run refusé, incomplet ou jamais terminé ;
      * schéma étranger, `returncode` non entier, listes absentes → MANIFEST illisible (jamais un succès) ;
      * sha / job / entrée différents de ce que la soumission a envoyé → ce n'est pas CE run ;
      * un fichier listé absent ou d'empreinte différente → transfert corrompu ;
      * un fichier présent et NON listé → refus de rapatrier ce qu'on ne sait pas d'où vient."""
    if (sortie / "REFUS.json").is_file():
        raise Refus(f"{job} : remote_entry a REFUSÉ avant exécution : {(sortie / 'REFUS.json').read_text('utf-8')}")
    mf = sortie / E.MANIFEST
    if not mf.is_file():
        raise Refus(f"{job} : pas de {E.MANIFEST} dans la sortie — run incomplet ou jamais terminé")
    m = json.loads(mf.read_text(encoding="utf-8"))
    rc = m.get("returncode")
    if (m.get("schema") != E.SCHEMA or not isinstance(rc, int) or isinstance(rc, bool)
            or not isinstance(m.get("sorties"), list) or not isinstance(m.get("fichiers"), dict)):
        raise Refus(f"{job} : MANIFEST de schéma inattendu ({m.get('schema')!r}) ou incomplet — jamais lu comme un succès")
    for cle, valeur in (attendu or {}).items():
        if valeur and m.get(cle) != valeur:
            raise Refus(f"{job} : MANIFEST {cle}={m.get(cle)!r}, la soumission attendait {valeur!r}")
    presents = E.empreinte(str(sortie))
    attendus = m["fichiers"]
    for rel, info in attendus.items():
        if presents.get(rel) != info.get("sha256"):
            raise Refus(f"{job} : {rel} absent ou d'empreinte différente du MANIFEST (transfert corrompu)")
    inattendus = sorted(set(presents) - set(attendus) - {E.MANIFEST, ".pret", ".rapatrie"})
    if inattendus:
        raise Refus(f"{job} : fichiers hors MANIFEST {inattendus[:5]} — refus de rapatrier l'inconnu")
    return m


def _remplacable(dest: Path, rel: str) -> bool:
    """Un fichier existant peut-il être remplacé SANS perte ? Seulement s'il est SUIVI par git et PROPRE dans
    `dest` (git en garde la version) ; non suivi, modifié, ou `dest` hors dépôt → non."""
    if _git(["ls-files", "--error-unmatch", "--", rel], dest, verifier=False).returncode != 0:
        return False
    st = _git(["status", "--porcelain", "--", rel], dest, verifier=False)
    return st.returncode == 0 and not st.stdout.strip()


def installer_sorties(sortie: Path, dest: Path, job: str, attendu: dict | None = None) -> dict:
    """Contrôle (controler_sortie) puis installe. TOUT OU RIEN, et JAMAIS DE PERTE :

      * une sortie absente de `dest` → copiée ; identique → laissée ;
      * différente mais suivie et propre dans `dest` → remplacée (git garde l'ancienne) ;
      * différente et non suivie ou modifiée → CONFLIT : rien n'est installé, la sortie vérifiée est
        conservée sous `dest/runs/deport/<job>/sortie_non_installee/` et le refus le dit.
    Journaux et MANIFEST vont sous `dest/runs/deport/<job>/`."""
    m = controler_sortie(sortie, job, attendu)
    attendus = m["fichiers"]
    conflits, identiques, a_copier = [], [], []
    for rel in m["sorties"]:
        cible = dest / rel
        if not cible.exists():
            a_copier.append(rel)
        elif E._sha256(str(cible)) == attendus[rel]["sha256"]:
            identiques.append(rel)
        elif _remplacable(dest, rel):
            a_copier.append(rel)
        else:
            conflits.append(rel)
    journal = dest / JOURNAL_LOCAL / job
    if conflits:
        garde = journal / "sortie_non_installee"
        if garde.exists():
            shutil.rmtree(garde)
        shutil.copytree(sortie, garde)
        raise Refus(f"{job} : {len(conflits)} sortie(s) existent déjà avec un contenu DIFFÉRENT, non suivi ou "
                    f"modifié {conflits[:5]} — rien n'est installé ; sortie VÉRIFIÉE conservée dans {garde} "
                    f"(python -m tools.jobs.remote installer {garde} --into <ailleurs>)")
    for rel in a_copier:
        E.ecrire_atomique((sortie / rel).read_bytes(), str(dest / rel))
    for rel in [r for r in attendus if r.startswith(E._JOURNAL + "/")] + [E.MANIFEST]:
        E.ecrire_atomique((sortie / rel).read_bytes(), str(journal / rel))
    return {"job": job, "copies": a_copier, "identiques": identiques, "journal": str(journal),
            "returncode": m["returncode"], "manifeste": m}


# ------------------------------------------------------------------------------------------ kubectl
class Kube:
    """kubectl, contexte et namespace FIXÉS par la configuration. Aucune écriture hors du namespace configuré."""

    def __init__(self, contexte, ns, binaire="kubectl"):
        self.base = [binaire, "--context", contexte]
        self.ns = ns

    @classmethod
    def depuis(cls, cfg: dict) -> "Kube":
        return cls(cfg["contexte"], cfg["namespace"])

    def brut(self, args, *, entree=None, ns=True, verifier=True, timeout=600) -> subprocess.CompletedProcess:
        cmd = self.base + (["-n", self.ns] if ns else []) + list(args)
        try:
            r = subprocess.run(cmd, input=entree, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise Refus(f"kubectl {' '.join(args[:3])} : pas de réponse en {timeout} s")
        if verifier and r.returncode != 0:
            raise Refus(f"kubectl {' '.join(args[:3])} : {r.stderr.decode('utf-8', 'replace').strip()}")
        return r

    def json(self, args, ns=True):
        return json.loads(self.brut(list(args) + ["-o", "json"], ns=ns).stdout)

    def creer(self, objet: dict):
        return self.brut(["create", "-f", "-"], entree=json.dumps(objet).encode("utf-8"))

    def supprimer_job(self, job):
        return self.brut(["delete", "job", job, "--wait=false"], verifier=False)

    def pod_du_job(self, job):
        pods = self.json(["get", "pods", "-l", f"job-name={job}"])["items"]
        return pods[-1] if pods else None

    def executer_dans(self, pod, conteneur, cmd, entree=None, timeout=600, verifier=True):
        return self.brut(["exec", "-i" if entree is not None else "-q", pod, "-c", conteneur, "--", *cmd],
                         entree=entree, timeout=timeout, verifier=verifier)

    def evenements(self, nom):
        try:
            evs = self.json(["get", "events", "--field-selector", f"involvedObject.name={nom}"])["items"]
        except Refus:
            return []
        return [f"{e.get('reason')}: {e.get('message')}" for e in evs]


def noeud_pret(kube: Kube, noeud: str):
    """(prêt, raison). Un nœud absent, NotReady ou non ordonnançable n'est PAS prêt."""
    try:
        n = kube.json(["get", "node", noeud], ns=False)
    except Refus as e:
        return False, f"nœud {noeud} illisible : {e}"
    if n["spec"].get("unschedulable"):
        return False, f"nœud {noeud} marqué non ordonnançable (cordon)"
    ready = [c for c in n["status"].get("conditions", []) if c["type"] == "Ready"]
    if not ready or ready[0]["status"] != "True":
        return False, f"nœud {noeud} NotReady ({ready[0].get('reason') if ready else 'sans condition'})"
    return True, "Ready"


def lire_image(racine: Path) -> dict:
    p = racine / IMAGE_JSON
    if not p.is_file():
        raise Refus(f"{IMAGE_JSON} absent : l'image runner n'est pas construite (python -m tools.jobs.remote image)")
    return json.loads(p.read_text(encoding="utf-8"))


def garde_image(info: dict, sha: str, racine: Path) -> str:
    """L'image est-elle celle des dépendances DU SHA ? Compare le CONTEXTE ENTIER (Dockerfile, contraintes,
    requirements, gabarit de build) quand le sha le porte ; sinon (sha antérieur au déport, ou branche qui ne
    l'a pas encore fusionné) seulement requirements.txt — et le DIT. Rend le mode de garde, lève si écart."""
    if all(_existe_au_sha(sha, c, racine) for c in FICHIERS_CONTEXTE.values()):
        h = contexte_image(sha, racine)["hash12"]
        if h != info.get("ctx_hash12"):
            raise Refus(f"le contexte d'image au sha {sha[:8]} ({h}) n'est pas celui de l'image {info.get('tag')} "
                        f"({info.get('ctx_hash12')}) : reconstruire, ou --image-divergente-ok en le disant")
        return "contexte-complet"
    req = hashlib.sha256(fichier_au_sha(sha, "requirements.txt", racine)).hexdigest()
    if req != info.get("requirements_sha256"):
        raise Refus(f"requirements.txt au sha {sha[:8]} diffère de celui de l'image {info.get('tag')} : "
                    "reconstruire l'image, ou --image-divergente-ok en le disant dans le record")
    return "requirements-seul (le sha ne porte pas deploy/nexus/runner : Dockerfile et contraintes NON comparés)"


# ------------------------------------------------------------------------------------------ étapes
def soumettre(commande, *, sha="HEAD", cpu=2.0, req_cpu=1.0, mem="4Gi", req_mem="1Gi",
              attente_s=3600, deadline_s=2 * 3600, image_divergente_ok=False,
              env=None, kube=None, racine=None, sortie=print, maintenant=None, cfg=None) -> str:
    cfg = cfg or charger_config()
    noeud = cfg["noeud"]
    racine = racine or racine_depot()
    kube = kube or Kube.depuis(cfg)
    commande = valider_commande(list(commande))
    env_declare = valider_env(env) if not isinstance(env, dict) else valider_env([f"{k}={v}" for k, v in env.items()])
    besoin = deadline_s + attente_s + MARGE_TRANSFERT_S
    reste = fenetre_restante_s(cfg["fenetre"], maintenant)
    if cmp_continu(besoin, reste, 0.0):                    # secondes : grandeur continue (porte 24)
        raise Refus(f"le run demande jusqu'à {besoin / 3600:.1f} h (deadline + fenêtre de rapatriement + marge) ; "
                    f"le nœud {noeud} s'éteint à la fin de sa fenêtre déclarée et il reste {reste / 3600:.1f} h "
                    "utilisables. Réduire --deadline-s / --attente-s, attendre l'ouverture de la fenêtre, ou `local`.")
    sha = sha_complet(sha, racine)
    info = lire_image(racine)
    mode_garde = "desactivee (--image-divergente-ok)" if image_divergente_ok else garde_image(info, sha, racine)
    pret, raison = noeud_pret(kube, noeud)
    if not pret:
        raise Refus(f"{raison}. {allumage(cfg)}")
    absentes = entrees_non_suivies(racine)
    if absentes:
        sortie(f"[remote] ⚠ {len(absentes)} entrée(s) de data/ NON suivies n'existeront PAS dans le pod "
               f"(si le runner les lit, il lira une absence) : {absentes[:8]}")
    archive = preparer_source(sha, racine)
    entry = (_ICI / "remote_entry.py").read_bytes()
    nom = nom_job(commande, sha)
    ref = image_ref(info, cfg["registre"])
    job = manifeste_job(nom=nom, sha=sha, image=ref, commande=commande, namespace=cfg["namespace"], cpu=cpu,
                        req_cpu=req_cpu,
                        mem=mem, req_mem=req_mem, noeud=noeud, attente_s=attente_s, deadline_s=deadline_s,
                        entry_sha256=hashlib.sha256(entry).hexdigest(),
                        source_sha256=hashlib.sha256(archive).hexdigest(), env_declare=env_declare)
    kube.creer(job)
    sortie(f"[remote] Job {nom} créé (sha {sha[:8]}, image {info['tag']}, garde d'image : {mode_garde})")
    try:
        pod = _attendre_recevoir(kube, nom, sortie)
        kube.executer_dans(pod, "recevoir", ["tar", "-x", "-C", "/xfer"], entree=paquet_de_transfert(archive, entry))
    except Refus:
        # Rien n'a tourné : un Job laissé en place démarrerait PLUS TARD sans sources et échouerait à 900 s.
        kube.supprimer_job(nom)
        raise
    sortie(f"[remote] sources envoyées ({len(archive)} o) au pod {pod}")
    j = racine / JOURNAL_LOCAL / nom
    j.mkdir(parents=True, exist_ok=True)
    (j / "soumission.json").write_text(json.dumps(
        {"job": nom, "sha": sha, "commande": commande, "env": env_declare, "image": image_ref(info, "<registre>"),
         "noeud": noeud,
         "garde_image": mode_garde, "entrees_non_suivies": absentes,
         "soumis_utc": _dt.datetime.now(_dt.timezone.utc).isoformat()}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return nom


_FATAL = ("FailedMount", "ErrImagePull", "ImagePullBackOff", "InvalidImageName", "FailedScheduling")


def _attendre_recevoir(kube: Kube, job: str, sortie, delai_s=900) -> str:
    """Attend que l'init `recevoir` tourne. Un pod absent après 30 s = refus d'admission SILENCIEUX (Kyverno)
    ou quota plein : on le dit avec les événements du Job. Une panne de tirage d'image est rapportée telle
    quelle. (L'appelant retire le Job : rien n'a tourné.)"""
    t0 = time.monotonic()
    while True:
        pod = kube.pod_du_job(job)
        age = time.monotonic() - t0
        if pod is None:
            evs = kube.evenements(job)
            quota = [e for e in evs if "exceeded quota" in e]
            if quota:
                raise Refus(f"{job} : quota du namespace plein ({quota[-1][:200]}) — attendre qu'un run finisse")
            if age > 30:
                raise Refus(f"aucun pod pour {job} après 30 s — refus d'admission ? {evs[-3:]}")
        else:
            nom = pod["metadata"]["name"]
            for st in pod.get("status", {}).get("initContainerStatuses", []):
                if st["name"] == "recevoir" and "running" in st.get("state", {}):
                    return nom
            fatals = [e for e in kube.evenements(nom) if e.split(":")[0] in _FATAL]
            if fatals and age > 90:
                raise Refus(f"pod {nom} bloqué : {fatals[-1]}")
        if age > delai_s:
            raise Refus(f"{job} : l'init « recevoir » ne tourne pas après {delai_s} s")
        time.sleep(3)


def lire_fin(job_obj: dict, pod: dict | None, noeud_pret_maintenant: bool) -> dict:
    """État d'un Job ÉCHOUÉ, déduit de ce qui est arrivé AU POD — jamais du seul état actuel du nœud (revue
    2026-09-26, I3 : un nexus éteint puis rallumé se lisait « echec »). Les preuves brutes sont rendues avec.
    En mode rapatriement, un échec du RUNNER n'arrive jamais ici : le pod attend qu'on le tire (état `pret`)."""
    st = (pod or {}).get("status", {})
    conds_pod = {c["type"]: c for c in st.get("conditions", [])}
    conds_job = {c["type"]: c for c in job_obj.get("status", {}).get("conditions", []) if c.get("status") == "True"}
    term = {}
    for c in st.get("containerStatuses", []) + st.get("initContainerStatuses", []):
        if "terminated" in c.get("state", {}):
            term[c["name"]] = c["state"]["terminated"]
    run = term.get("run", {})
    preuves = {"job_raison": (conds_job.get("Failed") or {}).get("reason"), "pod_raison": st.get("reason"),
               "perturbation": (conds_pod.get("DisruptionTarget") or {}).get("reason"),
               "run_code": run.get("exitCode"), "run_raison": run.get("reason"),
               "recevoir_code": (term.get("recevoir") or {}).get("exitCode"),
               "noeud_pret_maintenant": noeud_pret_maintenant}
    pert = preuves["perturbation"]
    if pod is None:
        etat = "pod_disparu"
    elif pert == "PreemptionByScheduler":
        etat = "preempte"
    elif pert in ("TerminationByKubelet", "DeletionByTaintManager") or st.get("reason") in ("NodeLost", "Terminated",
                                                                                           "NodeShutdown"):
        etat = "noeud_perdu"
    elif st.get("reason") == "Evicted" or pert == "EvictionByEvictionAPI":
        etat = "evince"
    elif preuves["job_raison"] == "DeadlineExceeded":
        etat = "delai_depasse"
    elif run.get("reason") == "OOMKilled":
        etat = "oom"
    elif run.get("exitCode") == E.REFUS:
        etat = "refus_entree"
    elif run.get("exitCode") == E.NON_RAPATRIE:
        etat = "non_rapatrie"
    elif preuves["recevoir_code"] not in (None, 0):
        etat = "sources_non_recues"
    elif not noeud_pret_maintenant:
        etat = "noeud_perdu"
    else:
        etat = "inconnu"
    return {"etat": etat, **preuves}


def attendre(job, *, kube=None, delai_s=8 * 3600, sortie=print, cfg=None) -> dict:
    """Attend la FIN du runner : `.pret` posé dans /out (rapatriable) ou Job terminé. États DISTINCTS :
    `pret`, `termine`, et pour un échec ceux de `lire_fin` (preempte, noeud_perdu, delai_depasse, oom,
    refus_entree, non_rapatrie, evince, pod_disparu, sources_non_recues, inconnu), ou `expire`."""
    cfg = cfg or charger_config()
    kube = kube or Kube.depuis(cfg)
    t0, dernier = time.monotonic(), None
    while time.monotonic() - t0 < delai_s:
        j = kube.json(["get", "job", job])
        conds = {c["type"] for c in j.get("status", {}).get("conditions", []) if c.get("status") == "True"}
        pod = kube.pod_du_job(job)
        if "Complete" in conds:
            return {"etat": "termine", "job": job}
        if "Failed" in conds:
            noeud = (pod or {}).get("spec", {}).get("nodeName") or cfg["noeud"]
            return {"job": job, **lire_fin(j, pod, noeud_pret(kube, noeud)[0])}
        if pod is not None and pod.get("status", {}).get("phase") == "Running":
            r = kube.executer_dans(pod["metadata"]["name"], "run", ["test", "-f", "/out/.pret"], timeout=60,
                                   verifier=False)
            if r.returncode == 0:
                return {"etat": "pret", "job": job, "pod": pod["metadata"]["name"]}
        phase = (pod or {}).get("status", {}).get("phase")
        if phase != dernier:
            sortie(f"[remote] {job} : pod {phase}")
            dernier = phase
        time.sleep(15)
    return {"etat": "expire", "job": job}


def rapatrier(job, *, into=None, kube=None, racine=None, sortie=print) -> dict:
    """Tire la sortie d'un run depuis son pod VIVANT, la CONTRÔLE contre son MANIFEST et contre la soumission
    (sha, job, entrée), l'installe, puis libère le pod (`.rapatrie`). Sortie intègre mais en conflit : elle
    est conservée localement et le pod est libéré quand même — la donnée est en sûreté, rien n'est perdu.
    Sortie corrompue : le pod n'est PAS libéré (on peut retirer tant que sa fenêtre court)."""
    kube = kube or Kube.depuis(charger_config())
    racine = racine or racine_depot()
    dest = Path(into) if into else racine
    j = kube.json(["get", "job", job])
    ann = j["metadata"].get("annotations", {})
    attendu = {"sha": ann.get("agagi.io/sha"), "job": job, "entry_sha256": ann.get("agagi.io/entry-sha256")}
    pod = kube.pod_du_job(job)
    if pod is None or pod.get("status", {}).get("phase") != "Running":
        raise Refus(f"{job} : pod absent ou terminé — sa sortie (emptyDir) est PERDUE ; relancer le run")
    nom_pod = pod["metadata"]["name"]
    brut = kube.executer_dans(nom_pod, "run", ["tar", "-c", "-C", "/out", "."], timeout=1800).stdout
    conflit = None
    with tempfile.TemporaryDirectory(prefix="agagi-rapatrie-") as tmp:
        with tarfile.open(fileobj=io.BytesIO(brut), mode="r:") as tf:
            tf.extractall(tmp, filter="data")
        controler_sortie(Path(tmp), job, attendu)          # corrompu → lève, pod NON libéré
        try:
            bilan = installer_sorties(Path(tmp), dest, job, attendu)
        except Refus as e:
            conflit = e                                    # sortie vérifiée conservée par installer_sorties
    r = kube.executer_dans(nom_pod, "run", ["touch", "/out/.rapatrie"], timeout=60, verifier=False)
    if r.returncode != 0:
        sortie(f"[remote] ⚠ {job} : sortie en sûreté sur la batcave, mais le pod n'a pas pu être libéré — il sortira "
               f"en {E.NON_RAPATRIE} à l'échéance ; ce n'est PAS une perte.")
    if conflit is not None:
        raise conflit
    if not bilan["manifeste"]["sorties"]:
        sortie(f"[remote] ⚠ {job} : AUCUNE sortie — le runner n'a rien écrit dans l'arbre (ou hors de l'arbre).")
    sortie(f"[remote] {job} rapatrié : {len(bilan['copies'])} copié(s), {len(bilan['identiques'])} identique(s), "
           f"rc runner = {bilan['returncode']} ; journal {bilan['journal']}")
    return bilan


def executer_local(commande, *, sha="HEAD", into=None, racine=None, sortie=print, bail_dir=None, env=None) -> dict:
    """Le MÊME chemin que le pod (dépôt au sha, remote_entry, empreintes, MANIFEST, installation), sur la
    batcave. Sert au témoin batcave/nexus et de repli quand nexus dort. Environnement MINIMAL (env_local) :
    rien de la session appelante n'atteint le runner, sauf les `--env` déclarés — comme dans le pod.
    La réussite se lit dans le MANIFEST, jamais au code du processus (un runner peut lui-même rendre 86)."""
    from tools.jobs.run import hold
    racine = racine or racine_depot()
    commande = valider_commande(list(commande))
    env_declare = valider_env([f"{k}={v}" for k, v in (env or {}).items()])
    sha = sha_complet(sha, racine)
    nom = nom_job(commande, sha, suffixe="local-" + secrets.token_hex(2))
    dest = Path(into) if into else racine
    with tempfile.TemporaryDirectory(prefix="agagi-local-") as tmp:
        t = Path(tmp)
        archive = preparer_source(sha, racine)
        (t / "source.tar.gz").write_bytes(archive)
        shutil.copyfile(_ICI / "remote_entry.py", t / "remote_entry.py")
        args = [sys.executable, str(t / "remote_entry.py"), "--source", str(t / "source.tar.gz"),
                "--sha", sha, "--source-sha256", hashlib.sha256(archive).hexdigest(),
                "--work", str(t / "work"), "--out", str(t / "out"), "--job", nom, "--lieu", "batcave"]
        for k in sorted(env_declare):
            args += ["--env-declare", k]
        # Le bail `kuzu` de la BATCAVE : le runner prendra aussi le sien, mais dans l'arbre extrait (invisible
        # au doctor) — sans celui-ci, un run local échapperait à la règle « un seul run lourd à la fois ».
        with hold("kuzu", owner=nom, ttl_s=6 * 3600, leases_dir=bail_dir):
            subprocess.run(args + ["--", *commande], env=env_local(env_declare))
        bilan = installer_sorties(t / "out", dest, nom, {"sha": sha, "job": nom})
    sortie(f"[remote] {nom} (local) : rc {bilan['returncode']}, {len(bilan['copies'])} sortie(s) copiée(s)")
    return bilan


# ------------------------------------------------------------------------------------------ image
def contexte_image(sha: str, racine: Path) -> dict:
    """Contexte de build LU AU SHA (jamais sur le disque partagé), gabarit du Job de build compris ; le tag
    est une empreinte de ce contexte : changer une contrainte change le tag."""
    fichiers = {n: fichier_au_sha(sha, c, racine) for n, c in FICHIERS_CONTEXTE.items()}
    h = hashlib.sha256()
    for n in sorted(fichiers):
        h.update(n.encode() + b"\0" + fichiers[n] + b"\0")
    m = re.search(rb"^FROM\s+python:(\d+\.\d+\.\d+)", fichiers["Dockerfile"], re.M)
    court = h.hexdigest()[:12]
    return {"fichiers": fichiers, "hash12": court, "tag": f"py{m.group(1).decode() if m else 'x'}-{court}",
            "requirements_sha256": hashlib.sha256(fichiers["requirements.txt"]).hexdigest()}


def construire_image(*, sha="HEAD", kube=None, racine=None, sortie=print, delai_s=2400, reconstruire=False,
                     cfg=None) -> dict:
    cfg = cfg or charger_config()
    racine = racine or racine_depot()
    kube = kube or Kube.depuis(cfg)
    sha = sha_complet(sha, racine)
    ctx = contexte_image(sha, racine)
    tag = ctx["tag"]
    if (racine / IMAGE_JSON).is_file():
        deja = lire_image(racine)
        if deja.get("ctx_hash12") == ctx["hash12"]:
            if not reconstruire:
                raise Refus(f"image {deja.get('tag')} déjà construite pour ce contexte ({image_ref(deja, cfg['registre'])}) ; "
                            "--reconstruire pour en pousser une NOUVELLE (tag suffixé, l'ancienne reste)")
            tag = f"{ctx['tag']}-r{secrets.token_hex(2)}"
    # durées en SECONDES : grandeur continue, déclarée à la porte 24 (pas un compte sur une grille)
    if cmp_continu(delai_s + MARGE_TRANSFERT_S, fenetre_restante_s(cfg["fenetre"]), 0.0):
        raise Refus(f"le build peut durer {delai_s / 60:.0f} min et le nœud {cfg['noeud']} s'éteint à la fin de sa "
                    "fenêtre déclarée : attendre son ouverture")
    pret, raison = noeud_pret(kube, cfg["noeud"])
    if not pret:
        raise Refus(f"{raison}. {allumage(cfg)}")
    if kube.brut(["get", "configmap", "registry-ca-bundle"], verifier=False).returncode != 0:
        if not cfg.get("ca_depuis"):
            raise Refus("ConfigMap registry-ca-bundle absente du namespace et clé ca_depuis (AGAGI_DEPORT_CA_DEPUIS) "
                        "non déclarée : impossible de savoir d'où copier la CA du registre")
        ca = kube.json(["get", "configmap", "registry-ca-bundle", "-n", cfg["ca_depuis"]], ns=False)["data"]["ca.crt"]
        kube.creer({"apiVersion": "v1", "kind": "ConfigMap",
                    "metadata": {"name": "registry-ca-bundle", "namespace": cfg["namespace"],
                                 "labels": LABELS_PROPRIETE},
                    "data": {"ca.crt": ca}})
        sortie(f"[remote] registry-ca-bundle copiée depuis {cfg['ca_depuis']} (CA publique du registre)")
    cm = f"agagi-runner-ctx-{ctx['hash12']}"
    if kube.brut(["get", "configmap", cm], verifier=False).returncode != 0:
        kube.creer({"apiVersion": "v1", "kind": "ConfigMap",
                    "metadata": {"name": cm, "namespace": cfg["namespace"], "labels": LABELS_PROPRIETE},
                    "data": {n: ctx["fichiers"][n].decode("utf-8")
                             for n in ("Dockerfile", "constraints.txt", "requirements.txt")}})
    job = f"agagi-build-{ctx['hash12']}-{secrets.token_hex(2)}"
    gabarit = ctx["fichiers"]["build-job.yaml"].decode("utf-8")
    yaml_job = rendre(gabarit, {"__JOB__": job, "__TAG__": tag, "__CTX_CM__": cm, "__NAMESPACE__": cfg["namespace"],
                                "__NOEUD__": cfg["noeud"], "__REGISTRE__": cfg["registre"],
                                "__DEPOT_IMAGE__": cfg["depot_image"],
                                "__CACHE_KANIKO__": cfg["depot_image"].rsplit("/", 1)[0] + "/_kaniko-cache"})
    kube.brut(["create", "-f", "-"], entree=yaml_job.encode("utf-8"))
    sortie(f"[remote] build {job} créé -> <registre>/{cfg['depot_image']}:{tag}")
    t0 = time.monotonic()
    while True:
        time.sleep(10)
        j = kube.json(["get", "job", job])
        conds = {c["type"] for c in j.get("status", {}).get("conditions", []) if c.get("status") == "True"}
        pod = kube.pod_du_job(job)
        if pod is None and time.monotonic() - t0 > 30:
            evs = kube.evenements(job)
            kube.supprimer_job(job)
            raise Refus(f"aucun pod pour {job} : refus d'admission ou quota ? {evs[-3:]} (Job retiré)")
        if "Failed" in conds or time.monotonic() - t0 > delai_s:
            logs = kube.brut(["logs", f"job/{job}", "-c", "kaniko", "--tail=40"], verifier=False).stdout
            raise Refus(f"build {job} en échec :\n{logs.decode('utf-8', 'replace')}")
        if "Complete" in conds:
            break
    st = [c for c in pod["status"]["containerStatuses"] if c["name"] == "kaniko"][0]
    digest = st["state"]["terminated"].get("message", "").strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise Refus(f"digest illisible dans le statut de {job} : {digest!r}")
    kube.brut(["delete", "configmap", cm], verifier=False)      # le quota compte les ConfigMaps
    info = {"image": cfg["depot_image"], "tag": tag, "digest": digest, "ctx_hash12": ctx["hash12"],
            "requirements_sha256": ctx["requirements_sha256"], "source_sha": sha, "job": job,
            "construit_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "duree_build_s": round(time.monotonic() - t0, 1)}
    E.ecrire_atomique((json.dumps(info, indent=2) + "\n").encode("utf-8"), str(racine / IMAGE_JSON))
    sortie(f"[remote] image {image_ref(info, '<registre>')} ; {IMAGE_JSON} écrit (à committer)")
    return info


# ------------------------------------------------------------------------------------------ gabarits
MANIFESTES_NAMESPACE = ("00-namespace.yaml", "01-limitrange.yaml", "02-networkpolicies.yaml", "03-resourcequota.yaml")


def rendre(gabarit: str, valeurs: dict) -> str:
    """Substitue les `__CLES__` d'un gabarit ; REFUSE s'il en reste une (un placeholder envoyé au cluster serait un
    nom invalide au mieux, un objet faux au pire)."""
    for k, v in valeurs.items():
        gabarit = gabarit.replace(k, str(v))
    restes = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", gabarit)))
    if restes:
        raise Refus(f"gabarit incomplet : {restes} non substitués")
    return gabarit


def rendre_manifestes(cfg: dict, racine: Path) -> str:
    """Les manifestes du namespace (deploy/nexus/00-03), rendus depuis la configuration. La NetworkPolicy ouvre le
    registre par ipBlock : il faut une ADRESSE IP, un nom d'hôte est refusé (il faudrait le résoudre, donc deviner)."""
    import ipaddress
    hote, _, port = cfg["registre"].rpartition(":")
    try:
        ip = ipaddress.ip_address(hote)
    except ValueError:
        raise Refus(f"registre {cfg['registre']!r} : la NetworkPolicy exige une adresse IP, pas un nom d'hôte")
    valeurs = {"__NAMESPACE__": cfg["namespace"], "__REGISTRE_IP__": str(ip), "__REGISTRE_PORT__": port}
    docs = [rendre((racine / "deploy" / "nexus" / f).read_text(encoding="utf-8"), valeurs) for f in MANIFESTES_NAMESPACE]
    return "\n---\n".join(d.strip("\n") for d in docs) + "\n"


# ------------------------------------------------------------------------------------------ surveillance
PENDING_MAX_S = 600


def lire_anomalies(jobs: dict, pods: dict, maintenant: float, ignorer=(), pending_max_s=PENDING_MAX_S) -> dict:
    """Anomalies d'un namespace de déport, lues sur `kubectl get jobs/pods -o json` : Job ÉCHOUÉ, conteneur
    OOMKilled, pod Pending depuis plus de `pending_max_s`. PURE (l'horloge est un argument).

    `ignorer` : motifs DÉCLARÉS (sous-chaînes de nom) dont les anomalies ne réveillent personne — elles ne sont pas
    jetées pour autant : elles sont rendues dans `ignorees`, comptées, et publiées à chaque ligne d'état (revue de
    Master 2, 2026-09-26 : une exclusion commode non comptée devient un angle mort silencieux, classe E32)."""
    import calendar
    anomalies, ignorees = [], []

    def noter(nom, texte):
        motif = next((m for m in ignorer if m and m in nom), None)
        (ignorees if motif else anomalies).append(texte + (f"  [ignorée : motif déclaré « {motif} »]" if motif else ""))

    for j in jobs.get("items", []):
        nom = j["metadata"]["name"]
        conds = {c["type"]: c for c in j.get("status", {}).get("conditions", []) if c.get("status") == "True"}
        if "Failed" in conds:
            noter(nom, f"JOB ÉCHOUÉ {nom} : {conds['Failed'].get('reason')} {conds['Failed'].get('message', '')[:120]}")
    for p in pods.get("items", []):
        nom, st = p["metadata"]["name"], p.get("status", {})
        for c in st.get("containerStatuses", []) + st.get("initContainerStatuses", []):
            t = c.get("state", {}).get("terminated") or c.get("lastState", {}).get("terminated") or {}
            if t.get("reason") == "OOMKilled":
                noter(nom, f"OOMKilled {nom}/{c['name']}")
        if st.get("phase") == "Pending":
            age = maintenant - calendar.timegm(_dt.datetime.strptime(p["metadata"]["creationTimestamp"],
                                                                     "%Y-%m-%dT%H:%M:%SZ").timetuple())
            if age > pending_max_s:
                noter(nom, f"PENDING depuis {age / 60:.0f} min {nom} (quota plein ? nœud ?)")
    actifs = sum(1 for j in jobs.get("items", []) if not {c["type"] for c in j.get("status", {}).get("conditions", [])
                                                          if c.get("status") == "True"} & {"Complete", "Failed"})
    return {"anomalies": anomalies, "ignorees": ignorees, "actifs": actifs}


def surveiller(*, duree_s=6 * 3600, pas_s=60, ignorer=(), kube=None, sortie=print) -> int:
    """LECTURE SEULE. Sonde le namespace toutes les `pas_s` secondes ; imprime une ligne d'état à chaque changement
    (Jobs actifs, quota, nombre d'anomalies IGNORÉES) ; rend 3 à la première anomalie non ignorée, 4 si le cluster
    est illisible, 0 à l'échéance. Ne relance, ne supprime, ne modifie RIEN."""
    kube = kube or Kube.depuis(charger_config())
    t0, dernier = time.monotonic(), None
    if ignorer:
        sortie(f"[surveiller] motifs ignorés DÉCLARÉS : {list(ignorer)} (comptés à chaque ligne)")
    while time.monotonic() - t0 < duree_s:
        try:
            jobs, pods = kube.json(["get", "jobs"]), kube.json(["get", "pods"])
            quota = kube.json(["get", "resourcequota"])
        except Refus as e:
            sortie(f"[surveiller] {time.strftime('%H:%M:%S')} cluster illisible : {e}")
            return 4
        r = lire_anomalies(jobs, pods, time.time(), ignorer)
        used = quota["items"][0]["status"].get("used", {}) if quota.get("items") else {}
        etat = (f"jobs actifs={r['actifs']} pods={used.get('pods')} req.cpu={used.get('requests.cpu')} "
                f"jobs={used.get('count/jobs.batch')} anomalies ignorées={len(r['ignorees'])}")
        if etat != dernier:
            sortie(f"[surveiller] {time.strftime('%H:%M:%S')} {etat}")
            dernier = etat
        if r["anomalies"]:
            for a in r["anomalies"]:
                sortie(f"[surveiller] {time.strftime('%H:%M:%S')} ANOMALIE {a}")
            return 3
        time.sleep(pas_s)
    sortie(f"[surveiller] {time.strftime('%H:%M:%S')} échéance atteinte, aucune anomalie non ignorée")
    return 0


# ------------------------------------------------------------------------------------------ témoin
VOLATILS_DEFAUT = ("elapsed_s",)
_SCALAIRE_JSON = rb'(?:-?Infinity|NaN|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|"(?:[^"\\]|\\.)*"|true|false|null)'


def ecarts_hors_volatils(a: bytes, b: bytes, volatils=VOLATILS_DEFAUT) -> list:
    """Lignes (numéro 1-based, contenu a, contenu b) où deux sorties diffèrent, une fois MASQUÉE la seule VALEUR
    des clés JSON déclarées volatiles (durée murale…). Liste vide = identiques OCTET POUR OCTET sur tout le reste,
    fins de ligne comprises. La liste des volatils est DÉCLARÉE avant de voir les deux côtés.

    Revue du 2026-09-26 (P5.2, E4) : la première version EXCUSAIT toute la ligne dès qu'une clé volatile
    l'ouvrait des deux côtés — une valeur posée après elle sur la même ligne devenait invisible, et le témoin
    unitaire n'exerçait pas ce chemin (sa ligne mixte commençait par une accolade). On masque la valeur, pas la
    ligne."""
    if not volatils:
        masquer = lambda ligne: ligne                                               # noqa: E731
    else:
        motif = re.compile(rb'("(?:' + b"|".join(re.escape(v.encode()) for v in volatils) + rb')"\s*:\s*)'
                           + _SCALAIRE_JSON)
        masquer = lambda ligne: motif.sub(rb"\1<volatil>", ligne)                    # noqa: E731
    la, lb = a.split(b"\n"), b.split(b"\n")
    if len(la) != len(lb):
        return [(0, f"{len(la)} lignes", f"{len(lb)} lignes")]
    return [(i + 1, x.decode("utf-8", "replace"), y.decode("utf-8", "replace"))
            for i, (x, y) in enumerate(zip(la, lb)) if masquer(x) != masquer(y)]


def _sans_hote(ref):
    """`hôte:port/chemin:tag@digest` → `chemin:tag@digest` : l'adresse d'un registre n'entre pas dans le dépôt."""
    if not ref:
        return ref
    tete, _, reste = ref.partition("/")
    return reste if reste and ("." in tete or ":" in tete) else ref


def agreger_temoin(tours: dict, sortie_rel: str, volatils=VOLATILS_DEFAUT) -> dict:
    """Agrège un témoin inter-machines : `tours` = {nom_tour: {côté: répertoire rapatrié (--into)}}. Pour chaque
    côté : la sortie du runner en OCTETS BRUTS (base64, donc à l'abri de core.autocrlf), son empreinte, son
    MANIFEST (hôte du registre retiré) ; pour chaque paire de côtés d'un tour : écarts sous la règle et écarts sans
    volatils (le contrôle que le comparateur voit une différence). Rien n'est jugé ici : on compte."""
    import base64
    import itertools
    doc = {"schema": "agagi-deport-temoin/2", "sortie": sortie_rel, "volatils": list(volatils), "tours": {}}
    for nom, cotes in tours.items():
        brut, t = {}, {"cotes": {}, "comparaisons_regle_declaree": {}, "controle_sans_volatils": {}}
        for cote, rep in cotes.items():
            rep = Path(rep)
            brut[cote] = (rep / sortie_rel).read_bytes()
            mfs = sorted((rep / JOURNAL_LOCAL).glob("*/" + E.MANIFEST))
            if len(mfs) != 1:
                raise Refus(f"{rep} : {len(mfs)} MANIFEST (un seul attendu)")
            m = json.loads(mfs[0].read_text(encoding="utf-8"))
            m["image"] = _sans_hote(m.get("image"))
            t["cotes"][cote] = {"manifeste": m, "sortie_sha256": hashlib.sha256(brut[cote]).hexdigest(),
                                "sortie_octets": len(brut[cote]), "sortie_CR": brut[cote].count(b"\r"),
                                "sortie_b64": base64.b64encode(brut[cote]).decode("ascii")}
        for x, y in itertools.combinations(sorted(cotes), 2):
            t["comparaisons_regle_declaree"][f"{x}~{y}"] = len(ecarts_hors_volatils(brut[x], brut[y], volatils))
            t["controle_sans_volatils"][f"{x}~{y}"] = len(ecarts_hors_volatils(brut[x], brut[y], ()))
        doc["tours"][nom] = t
    return doc


def rejouer_temoin(doc: dict) -> list:
    """Recompute, depuis les octets EMBARQUÉS, chaque compte publié par `agreger_temoin` ; rend la liste des
    désaccords (vide = tout se rejoue). Une empreinte qui ne correspond plus est un désaccord, pas un avertissement."""
    import base64
    import itertools
    desaccords = []
    vol = tuple(doc.get("volatils", VOLATILS_DEFAUT))
    for nom, t in doc.get("tours", {}).items():
        brut = {c: base64.b64decode(v["sortie_b64"]) for c, v in t["cotes"].items()}
        for c, v in t["cotes"].items():
            if hashlib.sha256(brut[c]).hexdigest() != v["sortie_sha256"]:
                desaccords.append(f"{nom}/{c} : empreinte")
        for x, y in itertools.combinations(sorted(brut), 2):
            k = f"{x}~{y}"
            for cle, vv in (("comparaisons_regle_declaree", vol), ("controle_sans_volatils", ())):
                if t[cle].get(k) != len(ecarts_hors_volatils(brut[x], brut[y], vv)):
                    desaccords.append(f"{nom}/{cle}/{k}")
    return desaccords


# ------------------------------------------------------------------------------------------ CLI
def code_de_sortie(rc) -> int:
    """Le code du runner tel quel ; un code ABSENT du MANIFEST n'est pas un succès (rendu 1, jamais 0)."""
    return rc if isinstance(rc, int) and not isinstance(rc, bool) else 1


def _commun(p):
    p.add_argument("--sha", default="HEAD")


def _env_cli(p):
    p.add_argument("--env", action="append", default=[], metavar="CLE=VALEUR",
                   help="variable passée au runner (pod ET local), publiée dans le MANIFEST")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.jobs.remote", description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="action", required=True)
    for nom in ("executer", "soumettre"):
        p = sp.add_parser(nom)
        _commun(p)
        _env_cli(p)
        p.add_argument("--cpu", type=float, default=2.0)
        p.add_argument("--req-cpu", type=float, default=1.0)
        p.add_argument("--mem", default="4Gi")
        p.add_argument("--req-mem", default="1Gi")
        p.add_argument("--attente-s", type=float, default=3600, help="fenêtre de rapatriement après le run")
        p.add_argument("--deadline-s", type=float, default=2 * 3600, help="durée max du runner (avant minuit)")
        p.add_argument("--image-divergente-ok", action="store_true")
        if nom == "executer":
            p.add_argument("--into", default=None)
        p.add_argument("commande", nargs=argparse.REMAINDER)
    p = sp.add_parser("local")
    _commun(p)
    _env_cli(p)
    p.add_argument("--into", default=None)
    p.add_argument("commande", nargs=argparse.REMAINDER)
    p = sp.add_parser("attendre")
    p.add_argument("job")
    p = sp.add_parser("rapatrier")
    p.add_argument("job")
    p.add_argument("--into", default=None)
    p = sp.add_parser("installer", help="installer une sortie conservée (runs/deport/<job>/sortie_non_installee)")
    p.add_argument("repertoire")
    p.add_argument("--into", required=True)
    p = sp.add_parser("image")
    _commun(p)
    p.add_argument("--reconstruire", action="store_true")
    sp.add_parser("etat")
    p = sp.add_parser("namespace", help="rendre les manifestes du namespace depuis la configuration")
    p.add_argument("--appliquer", action="store_true", help="kubectl apply du rendu (sinon : imprimé)")
    sp.add_parser("config", help="afficher la configuration résolue et d'où vient chaque clé")
    p = sp.add_parser("surveiller", help="sonde LECTURE SEULE du namespace (Job échoué, OOMKilled, Pending)")
    p.add_argument("--duree-s", type=float, default=6 * 3600)
    p.add_argument("--pas-s", type=float, default=60)
    p.add_argument("--ignorer", action="append", default=[], metavar="MOTIF",
                   help="sous-chaîne de nom DÉCLARÉE dont les anomalies sont comptées mais ne réveillent pas")
    p = sp.add_parser("temoin", help="rejouer les comptes d'un témoin publié depuis ses octets embarqués")
    p.add_argument("json")
    a = ap.parse_args(argv)
    try:
        if a.action in ("executer", "soumettre"):
            kw = dict(sha=a.sha, cpu=a.cpu, req_cpu=a.req_cpu, mem=a.mem, req_mem=a.req_mem, env=a.env,
                      attente_s=a.attente_s, deadline_s=a.deadline_s,
                      image_divergente_ok=a.image_divergente_ok)
            job = soumettre(a.commande, **kw)
            if a.action == "soumettre":
                print(job)
                return 0
            fin = attendre(job)
            if fin["etat"] == "pret":
                return code_de_sortie(rapatrier(job, into=a.into)["returncode"])
            print(f"[remote] {job} : {json.dumps(fin, ensure_ascii=False)}", file=sys.stderr)
            return 1
        if a.action == "local":
            env = valider_env(a.env)
            return code_de_sortie(executer_local(a.commande, sha=a.sha, into=a.into, env=env)["returncode"])
        if a.action == "attendre":
            print(json.dumps(attendre(a.job), ensure_ascii=False))
            return 0
        if a.action == "rapatrier":
            return code_de_sortie(rapatrier(a.job, into=a.into)["returncode"])
        if a.action == "installer":
            d = Path(a.repertoire)
            return code_de_sortie(installer_sorties(d, Path(a.into), d.parent.name)["returncode"])
        if a.action == "image":
            construire_image(sha=a.sha, reconstruire=a.reconstruire)
            return 0
        if a.action == "temoin":
            d = rejouer_temoin(json.loads(Path(a.json).read_text(encoding="utf-8")))
            print("tout se rejoue" if not d else f"DÉSACCORDS : {d}")
            return 0 if not d else 1
        if a.action == "etat":
            print(Kube.depuis(charger_config()).brut(["get", "jobs,pods", "-l", "app.kubernetes.io/part-of=agagi"])
                  .stdout.decode())
            return 0
        if a.action == "namespace":
            cfg = charger_config()
            rendu = rendre_manifestes(cfg, racine_depot())
            if not a.appliquer:
                print(rendu)
                return 0
            r = Kube.depuis(cfg).brut(["apply", "-f", "-"], entree=rendu.encode("utf-8"), ns=False)
            print(r.stdout.decode())
            return 0
        if a.action == "surveiller":
            return surveiller(duree_s=a.duree_s, pas_s=a.pas_s, ignorer=tuple(a.ignorer))
        if a.action == "config":
            cfg = charger_config()
            for k in VARIABLES_CONFIG:
                print(f"{k:12s} = {cfg.get(k)!r}   <- {cfg['_source'].get(k, 'absente')}")
            return 0
    except Refus as e:
        print(f"[remote] REFUS : {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
