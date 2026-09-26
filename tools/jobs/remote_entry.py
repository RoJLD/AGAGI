# -*- coding: utf-8 -*-
"""Point d'entrée d'un run DÉPORTÉ — exécuté DANS le pod, et à l'identique en local (`remote.py local`).

**stdlib seule** (plus le binaire `git`) : ce fichier voyage avec chaque Job, à côté du code au sha demandé.
Il ne peut importer ni AGAGI (le code n'est pas encore extrait quand il démarre) ni une dépendance tierce.

Le code arrive comme un DÉPÔT GIT SUPERFICIEL (profondeur 1, fins de ligne du commit) et non comme un
`git archive` : (a) les runners tamponnent leur provenance par `git rev-parse HEAD` / `git status`
(`tools/preregister.provenance`, P2.68 ; `src/seed_ai/harness`) — sans `.git`, un run déporté publierait
`git_sha: None` ; (b) `git archive` sur la batcave applique `core.autocrlf=true` (config SYSTÈME de Git for
Windows, mesuré le 2026-09-26) et aurait livré au pod des sources en CRLF, pas les blobs du commit.

Séquence, chaque étape pouvant REFUSER avant la suivante :
  1. le dépôt reçu est-il EXACTEMENT le sha annoncé ? (HEAD détaché = sha, `git status` vide) — un code qui
     n'est pas celui qu'on croit lancer ne tourne pas ;
  2. empreinte sha256 + horodatage de chaque fichier (hors `.git/`) ;
  3. limite CPU lue dans le CGROUP (`os.cpu_count()` rend les CPU de l'HÔTE : 16 sur nexus pour une
     limite de 2, mesuré le 2026-09-24), variables de threads posées sur cette limite, charge notée ;
  4. la commande tourne (cwd = sources), stdout/stderr recopiés vers les logs du pod ET des fichiers ;
  5. après : tout fichier CRÉÉ, MODIFIÉ ou RÉÉCRIT À L'IDENTIQUE est une sortie — le runner n'a rien à
     déclarer ; une reproduction exacte d'un résultat committé est donc attestée, pas invisible ;
  6. sorties + journaux + MANIFEST.json (sha256 de chaque fichier) dans --out ;
  7. --depot (optionnel, aucun appelant aujourd'hui) : copie par renommage ATOMIQUE, MANIFEST en DERNIER ;
  8. --attendre-rapatriement S : le pod reste vivant jusqu'à ce que la batcave ait tiré --out
     (`.rapatrie` posé par `remote.py rapatrier`) ; faute de quoi il échoue BRUYAMMENT.

Codes de sortie : celui du runner ; 86 = REFUS avant exécution (sha, archive, commande) — un `REFUS.json` est
alors écrit dans --out ; 87 = run terminé mais jamais rapatrié (résultats perdus avec le pod : PAS un
succès). Des codes rares plutôt que 2/75, qu'un runner (argparse, sysexits) rend lui-même ; la vérité reste
le MANIFEST (présent = le runner a tourné, `returncode` = SON code), jamais le code du processus seul.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time

SCHEMA = "agagi-deport/1"
REFUS = 86
NON_RAPATRIE = 87
_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
# Ni sortie ni suppression : caches d'interprète et bails de la machine d'exécution.
_IGNORES_DIRS = frozenset({".git", "__pycache__", ".pytest_cache", ".mypy_cache"})
_IGNORES_PREFIXES = ("runs/leases/",)
_JOURNAL = "_deport"
MANIFEST = "MANIFEST.json"
# Variables qui DÉPLACERAIENT les écritures du runner HORS de l'arbre extrait (src/paths.py) ou qui changent
# le code exécuté (harnais de mutation, porte 15) : jamais transmises au runner.
_ENV_INTERDITES = re.compile(r"^(GIT_.*|AGAGI_(\w+_)?ROOT|AGAGI_MUTATION_SPEC)$")


class Refus(RuntimeError):
    """Refus AVANT exécution : rien n'a tourné, rien ne doit être lu comme un résultat."""


# --------------------------------------------------------------------------------------------- CPU
def parse_cpu_max(brut: str):
    """`cpu.max` (cgroup v2) → nombre de CPU, ou None si « max » (AUCUNE limite).

    None est une AFFIRMATION (« pas de limite »), jamais un « je ne sais pas » : un contenu illisible LÈVE."""
    parts = brut.split()
    if len(parts) != 2:
        raise ValueError(f"cpu.max illisible : {brut!r}")
    quota, periode = parts
    if quota == "max":
        return None
    q, p = int(quota), int(periode)
    if q <= 0 or p <= 0:
        raise ValueError(f"cpu.max incohérent : {brut!r}")
    return q / p


def lire_limite_cpu(racine: str = "/sys/fs/cgroup") -> dict:
    """Limite CPU du conteneur, avec sa SOURCE. Trois issues distinctes, jamais fondues :
    `cgroup2`/`cgroup1` (lue), `absente` (aucun fichier de limite à cet endroit : Windows, ou cgroup v2 dont la
    racine ne porte pas cpu.max, ex. WSL — limite INCONNUE, pas « illimitée »), `illisible` (erreur dite)."""
    out = {"source": "absente", "cpu_max_brut": None, "limite_cpu": None, "erreur": None}
    p2 = os.path.join(racine, "cpu.max")
    if os.path.exists(p2):
        try:
            with open(p2, encoding="ascii") as f:
                brut = f.read().strip()
            out.update(source="cgroup2", cpu_max_brut=brut, limite_cpu=parse_cpu_max(brut))
        except (OSError, ValueError) as e:
            out.update(source="illisible", erreur=f"{type(e).__name__}: {e}")
        return out
    q1, p1 = os.path.join(racine, "cpu", "cpu.cfs_quota_us"), os.path.join(racine, "cpu", "cpu.cfs_period_us")
    if os.path.exists(q1) and os.path.exists(p1):
        try:
            with open(q1) as fq, open(p1) as fp:
                q, per = int(fq.read().strip()), int(fp.read().strip())
            out.update(source="cgroup1", cpu_max_brut=f"{q} {per}", limite_cpu=None if q < 0 else q / per)
        except (OSError, ValueError) as e:
            out.update(source="illisible", erreur=f"{type(e).__name__}: {e}")
    return out


def _affinite():
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return None


def _charge():
    """Charge de la MACHINE (pas du conteneur) : loadavg sur Linux, et % CPU système sur 1 s via psutil
    quand il est importable (Windows n'a pas de loadavg). None = non mesuré, jamais « machine libre »."""
    out = {"loadavg": None, "cpu_pct_systeme_1s": None}
    try:
        out["loadavg"] = list(os.getloadavg())
    except (AttributeError, OSError):
        pass
    try:
        import psutil
        out["cpu_pct_systeme_1s"] = psutil.cpu_percent(interval=1.0)
    except Exception:                                         # noqa: BLE001 — non mesuré, dit par None
        pass
    return out


# --------------------------------------------------------------------------------------- empreintes
def _sha256(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _ignore(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in _IGNORES_DIRS for p in parts[:-1]) or rel.endswith(".pyc"):
        return True
    return rel.startswith(_IGNORES_PREFIXES)


def _parcours(racine: str):
    for d, dirs, fichiers in os.walk(racine):
        dirs[:] = sorted(x for x in dirs if x not in _IGNORES_DIRS)
        for fn in sorted(fichiers):
            p = os.path.join(d, fn)
            rel = os.path.relpath(p, racine).replace(os.sep, "/")
            if not _ignore(rel) and os.path.isfile(p):
                yield rel, p


def empreinte(racine: str) -> dict:
    """{chemin relatif POSIX: sha256} de tous les fichiers sous `racine`, hors caches."""
    return {rel: _sha256(p) for rel, p in _parcours(racine)}


def horodatages(racine: str) -> dict:
    """{chemin relatif POSIX: mtime_ns} — sert à voir une RÉÉCRITURE à l'identique, que l'empreinte ne voit pas."""
    return {rel: os.stat(p).st_mtime_ns for rel, p in _parcours(racine)}


def sorties(avant: dict, apres: dict, t_avant: dict | None = None, t_apres: dict | None = None):
    """(créés ou modifiés, réécrits à l'identique, supprimés). Un résultat committé que le runner RÉÉCRIT à
    l'octet près est une reproduction : il doit être rapatrié et attesté, pas disparaître (revue du
    2026-09-26, sonde S3). Sans horodatages, la deuxième liste est vide — elle n'est pas « aucune »."""
    changes = sorted(r for r, h in apres.items() if avant.get(r) != h)
    reecrits = []
    if t_avant is not None and t_apres is not None:
        reecrits = sorted(r for r, h in apres.items()
                          if avant.get(r) == h and t_avant.get(r) != t_apres.get(r))
    supprimes = sorted(r for r in avant if r not in apres)
    return changes, reecrits, supprimes


# ------------------------------------------------------------------------------------------ archive
def _git_ici(depot: str, *args) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # jamais le dépôt de l'appelant
    return subprocess.run(["git", "-C", depot, "-c", "core.autocrlf=false", *args], capture_output=True,
                          text=True, env=env)


def extraire_au_sha(archive: str, sha: str, dest: str) -> None:
    """Extrait `archive` (tar.gz d'un dépôt superficiel, cf. remote.preparer_source) dans `dest`, puis vérifie
    que c'est EXACTEMENT `sha` : HEAD détaché égal au sha, arbre PROPRE. Refus sinon — y compris si `git`
    manque (la provenance des runners serait alors fabriquée : « unknown », dirty=False)."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        raise Refus(f"sha attendu complet (40 hexa) : {sha!r}")
    if shutil.which("git") is None:
        raise Refus("git absent : la provenance des runners (git rev-parse HEAD) ne pourrait pas être lue")
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(archive, "r:*") as tf:
        tf.extractall(dest, filter="data")
    tete = os.path.join(dest, ".git", "HEAD")
    if not os.path.isfile(tete):
        raise Refus("l'archive n'est pas un dépôt git (pas de .git/HEAD) — refus : la provenance serait perdue")
    with open(tete, encoding="ascii") as f:
        porte = f.read().strip()
    r = _git_ici(dest, "rev-parse", "HEAD")
    if porte != sha or r.returncode != 0 or r.stdout.strip() != sha:
        raise Refus(f"le dépôt reçu est au commit {porte!r}, pas {sha!r} — refus d'exécuter un autre code")
    st = _git_ici(dest, "status", "--porcelain")
    if st.returncode != 0 or st.stdout.strip():
        raise Refus(f"le dépôt reçu n'est pas l'arbre propre du commit : {(st.stdout or st.stderr)[:300]!r}")


# ---------------------------------------------------------------------------------------- exécution
def _tee(flux, fichier, miroir):
    for ligne in iter(flux.readline, b""):
        fichier.write(ligne)
        fichier.flush()
        try:
            miroir.write(ligne)
            miroir.flush()
        except (OSError, ValueError):
            pass


def _cpu_enfant_windows(proc):
    """(user_s, sys_s) du fils DIRECT terminé, via GetProcessTimes — `resource` n'existe pas sous Windows et
    `os.times()` y rend des temps d'enfants toujours nuls. ⚠️ Ne compte PAS les petits-enfants, là où
    RUSAGE_CHILDREN (Linux) compte tous les descendants attendus : `cpu_mesure` le dit dans le MANIFEST."""
    import ctypes
    from ctypes import wintypes
    c, e, k, u = (wintypes.FILETIME() for _ in range(4))
    ok = ctypes.windll.kernel32.GetProcessTimes(int(proc._handle), ctypes.byref(c), ctypes.byref(e),
                                                ctypes.byref(k), ctypes.byref(u))
    if not ok:
        return None, None
    en_s = lambda ft: ((ft.dwHighDateTime << 32) | ft.dwLowDateTime) / 1e7  # noqa: E731
    return en_s(u), en_s(k)


def executer(cmd: list, cwd: str, env: dict, journal: str) -> dict:
    """Lance `cmd`, recopie ses flux, mesure mur + CPU des enfants. Rend les mesures (aucun verdict)."""
    os.makedirs(journal, exist_ok=True)
    ru0 = None
    try:
        import resource
        ru0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    except ImportError:
        resource = None
    t0_mur, debut = time.perf_counter(), _dt.datetime.now(_dt.timezone.utc)
    with open(os.path.join(journal, "stdout.txt"), "wb") as fo, open(os.path.join(journal, "stderr.txt"), "wb") as fe:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        fils = [threading.Thread(target=_tee, args=(proc.stdout, fo, sys.stdout.buffer), daemon=True),
                threading.Thread(target=_tee, args=(proc.stderr, fe, sys.stderr.buffer), daemon=True)]
        for t in fils:
            t.start()
        rc = proc.wait()
        for t in fils:
            t.join()
    duree = time.perf_counter() - t0_mur
    user = syst = rss_max_ko = None
    methode = None
    if resource is not None and ru0 is not None:
        ru1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        user, syst, rss_max_ko = ru1.ru_utime - ru0.ru_utime, ru1.ru_stime - ru0.ru_stime, ru1.ru_maxrss
        methode = "RUSAGE_CHILDREN (tous descendants attendus)"
    elif os.name == "nt":
        user, syst = _cpu_enfant_windows(proc)
        methode = "GetProcessTimes (fils direct seul)"
    return {"returncode": rc, "debut_utc": debut.isoformat(), "duree_mur_s": round(duree, 3),
            "cpu_user_s": user, "cpu_sys_s": syst, "rss_max_ko": rss_max_ko, "cpu_mesure": methode}


def env_du_runner(env: dict, src: str, limite: dict) -> tuple[dict, list]:
    """(environnement du runner, variables RETIRÉES). Retirées : `GIT_*` (un GIT_DIR hérité viserait le dépôt
    de la batcave — P2.121 famille 6), les racines `AGAGI_*ROOT` (elles déplaceraient les écritures HORS de
    l'arbre extrait, donc hors du MANIFEST) et le harnais de mutation. Sources en tête de PYTHONPATH, threads
    calés sur la limite cgroup QUAND elle est connue."""
    retirees = sorted(k for k in env if _ENV_INTERDITES.match(k))
    out = {k: v for k, v in env.items() if k not in retirees}
    out["PYTHONPATH"] = src + (os.pathsep + out["PYTHONPATH"] if out.get("PYTHONPATH") else "")
    out.setdefault("MPLBACKEND", "Agg")
    lim = limite.get("limite_cpu")
    if lim:
        n = str(max(1, int(lim)))
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            out[var] = n
        out["AGAGI_CPU_LIMIT"] = repr(lim)
    return out, retirees


def _versions(python: str, env: dict) -> dict:
    code = ("import json,importlib.metadata as m\nd={}\n"
            "for n in ('numpy','scipy','torch','kuzu'):\n"
            "  try: d[n]=m.version(n)\n  except Exception: d[n]=None\nprint(json.dumps(d))")
    try:
        r = subprocess.run([python, "-c", code], env=env, capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout)
    except Exception as e:                                    # noqa: BLE001 — dit, jamais avalé
        return {"erreur": f"{type(e).__name__}: {e}"}


# ------------------------------------------------------------------------------------------- dépôt
def ecrire_atomique(donnees: bytes, dest: str) -> None:
    """Écrit `dest` par fichier temporaire du MÊME répertoire + fsync + os.replace : un lecteur voit l'ancien
    fichier ou le nouveau, jamais un fichier tronqué."""
    d = os.path.dirname(dest) or "."
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(dest)}.part-{os.getpid()}")
    with open(tmp, "wb") as f:
        f.write(donnees)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, dest)


def deposer(sortie: str, depot: str) -> int:
    """Recopie `sortie` dans `depot`, MANIFEST.json en DERNIER. Refuse un dépôt déjà COMPLET (un nom de
    Job est unique : réécrire un dépôt terminé, c'est effacer une preuve). Rend le nombre de fichiers."""
    if os.path.exists(os.path.join(depot, MANIFEST)):
        raise Refus(f"dépôt déjà complet : {depot} — jamais réécrit")
    n = 0
    fichiers = [r for r in empreinte(sortie) if r != MANIFEST]
    for rel in fichiers:
        with open(os.path.join(sortie, rel), "rb") as f:
            ecrire_atomique(f.read(), os.path.join(depot, rel))
        n += 1
    with open(os.path.join(sortie, MANIFEST), "rb") as f:
        ecrire_atomique(f.read(), os.path.join(depot, MANIFEST))
    return n + 1


def attendre_rapatriement(sortie: str, delai_s: float, pas_s: float = 5.0) -> bool:
    """Pose `.pret`, puis attend `.rapatrie` (posé par la batcave après vérification). False à l'échéance."""
    with open(os.path.join(sortie, ".pret"), "w") as f:
        f.write("pret\n")
    fin = time.monotonic() + delai_s
    while time.monotonic() < fin:
        if os.path.exists(os.path.join(sortie, ".rapatrie")):
            return True
        time.sleep(pas_s)
    return os.path.exists(os.path.join(sortie, ".rapatrie"))


# --------------------------------------------------------------------------------------------- main
def principal(a) -> int:
    commande = list(a.commande)
    if commande[:1] == ["--"]:
        commande = commande[1:]
    if len(commande) < 2 or commande[0] != "-m" or not _MODULE.match(commande[1]):
        raise Refus(f"commande attendue « -m <module> [args] », reçu {commande!r}")
    src, sortie = os.path.join(a.work, "src"), a.out
    os.makedirs(sortie, exist_ok=True)
    if os.listdir(sortie) and not a.autoriser_sortie_non_vide:
        raise Refus(f"répertoire de sortie non vide : {sortie}")
    if a.source_sha256 and _sha256(a.source) != a.source_sha256:
        raise Refus("l'archive reçue ne correspond pas à l'empreinte envoyée (transfert tronqué ?)")
    interdites = [k for k in a.env_declare if _ENV_INTERDITES.match(k)]
    if interdites:
        raise Refus(f"variables déclarées interdites {interdites} (elles déplacent les écritures ou le code)")
    extraire_au_sha(a.source, a.sha, src)
    avant, t_avant = empreinte(src), horodatages(src)
    limite = lire_limite_cpu(a.cgroup)
    env, retirees = env_du_runner(dict(os.environ), src, limite)
    cmd = [sys.executable] + commande
    print(f"[deport] sha={a.sha} lieu={a.lieu} limite_cpu={limite['limite_cpu']} ({limite['source']}) "
          f"os.cpu_count={os.cpu_count()} cmd={' '.join(commande)}", flush=True)
    charge0 = _charge()
    mesure = executer(cmd, src, env, os.path.join(sortie, _JOURNAL))
    charge1 = _charge()
    changes, reecrits, supprimes = sorties(avant, empreinte(src), t_avant, horodatages(src))
    for rel in changes + reecrits:
        dest = os.path.join(sortie, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(src, rel), dest)
    with open(__file__, "rb") as f:
        entry_sha = hashlib.sha256(f.read()).hexdigest()
    fichiers = {r: {"sha256": h, "octets": os.path.getsize(os.path.join(sortie, r))}
                for r, h in empreinte(sortie).items() if r not in (MANIFEST, ".pret", ".rapatrie")}
    manifeste = {
        "schema": SCHEMA, "job": a.job, "lieu": a.lieu, "noeud": os.environ.get("NODE_NAME") or platform.node(),
        "sha": a.sha, "sha_verifie": True, "commande": commande, **mesure,
        "fin_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "cpu": {**limite, "affinite": _affinite(), "os_cpu_count": os.cpu_count(),
                "threads_poses": env.get("OMP_NUM_THREADS")},
        "charge_debut": charge0, "charge_fin": charge1,
        "python": platform.python_version(), "plateforme": platform.platform(),
        "versions": _versions(sys.executable, env), "image": os.environ.get("AGAGI_IMAGE"),
        "env_declare": {k: os.environ.get(k) for k in a.env_declare}, "env_retirees": retirees,
        "entry_sha256": entry_sha, "sorties": changes + reecrits, "reecrits_identiques": reecrits,
        "supprimes": supprimes, "fichiers": fichiers,
    }
    ecrire_atomique(json.dumps(manifeste, indent=2, ensure_ascii=False).encode("utf-8"),
                    os.path.join(sortie, MANIFEST))
    print(f"[deport] rc={mesure['returncode']} duree_mur_s={mesure['duree_mur_s']} sorties={len(changes)} "
          f"reecrits_identiques={len(reecrits)} supprimes={len(supprimes)}", flush=True)
    if not changes and not reecrits:
        print("[deport] ⚠ AUCUNE sortie dans l'arbre : le runner n'a rien écrit, ou il a écrit HORS de l'arbre "
              "(chemin absolu, répertoire temporaire) — rien de cela ne sera rapatrié.", file=sys.stderr, flush=True)
    if a.depot:
        n = deposer(sortie, a.depot)
        print(f"[deport] dépôt atomique : {n} fichier(s) -> {a.depot} (MANIFEST en dernier)", flush=True)
    if a.attendre_rapatriement:
        if not attendre_rapatriement(sortie, a.attendre_rapatriement):
            print(f"[deport] ÉCHEC : sorties jamais rapatriées en {a.attendre_rapatriement:.0f} s — elles "
                  "disparaissent avec le pod. Ce run n'a PAS de résultat.", file=sys.stderr, flush=True)
            return NON_RAPATRIE
        print("[deport] rapatriement confirmé par la batcave", flush=True)
    return mesure["returncode"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", required=True, help="tar.gz du dépôt superficiel au sha")
    ap.add_argument("--sha", required=True, help="sha complet ANNONCÉ, vérifié contre le dépôt reçu")
    ap.add_argument("--source-sha256", default=None, help="empreinte de l'archive, vérifiée avant extraction")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--job", default="local")
    ap.add_argument("--lieu", default="inconnu")
    ap.add_argument("--env-declare", action="append", default=[], metavar="VAR",
                    help="variable DÉCLARÉE par la soumission : sa valeur est publiée dans le MANIFEST")
    ap.add_argument("--depot", default=None, help="répertoire de dépôt atomique (optionnel)")
    ap.add_argument("--attendre-rapatriement", type=float, default=0.0, metavar="S")
    ap.add_argument("--cgroup", default="/sys/fs/cgroup")
    ap.add_argument("--autoriser-sortie-non-vide", action="store_true")
    ap.add_argument("commande", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    try:
        return principal(a)
    except Refus as e:
        print(f"[deport] REFUS : {e}", file=sys.stderr, flush=True)
        try:
            os.makedirs(a.out, exist_ok=True)
            with open(os.path.join(a.out, "REFUS.json"), "w", encoding="utf-8") as f:
                json.dump({"schema": SCHEMA, "refus": str(e), "sha": a.sha, "job": a.job}, f, ensure_ascii=False)
        except OSError:
            pass
        return REFUS


if __name__ == "__main__":
    sys.exit(main())
