# deploy/nexus/runner/empreinte_contenu.py — EMPREINTE DE CONTENU de l'image runner (P2.134), stdlib seule.
#
# Exécuté par la DERNIÈRE étape du Dockerfile, dans l'image en construction ; écrit /opt/agagi/empreinte-contenu.json,
# que remote_entry publie dans le MANIFEST de chaque run, à côté du digest. Décision de Master 2 (2026-09-28) : le
# DIGEST est l'identité citée par un record ; cette empreinte est un DIAGNOSTIC — quand le digest change, elle dit si
# l'environnement Python/torch (zone `python` = /usr/local) a changé, ou seulement le reste (zone `systeme` : apt, …).
#
# Ce qui compte : le chemin, le type (fichier, lien, répertoire), les bits de mode et le contenu (sha256) ou la cible
# d'un lien. Ce qui ne compte PAS : les dates (Kaniko les pose), et les chemins que le runtime du BUILD injecte sans
# qu'ils entrent dans l'image (/proc, /sys, /dev, /etc/hosts, /etc/resolv.conf…, le contexte /workspace, Kaniko
# lui-même) — sinon l'empreinte varierait d'un pod de build à l'autre. Fichier du dépôt HACHÉ dans le tag de l'image.
import hashlib
import json
import os
import stat
import sys

SCHEMA = "agagi.empreinte_contenu.v1"
MARQUEUR = "AGAGI-EMPREINTE-CONTENU"
ZONES = (("python", "/usr/local"),)          # le reste de la racine est la zone `systeme`
EXCLUS = ("/proc", "/sys", "/dev", "/run", "/var/run", "/tmp", "/var/tmp", "/kaniko", "/workspace",
          "/etc/hosts", "/etc/hostname", "/etc/resolv.conf", "/etc/mtab")


def _sous(chemin: str, racine: str) -> bool:
    return chemin == racine or chemin.startswith(racine.rstrip("/") + "/")


def _sha256_fichier(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def empreinte(racine: str = "/", exclus=EXCLUS, zones=ZONES, sortie: str | None = None) -> dict:
    """Parcourt `racine` sans suivre les liens, dans un ordre FIXÉ (tri des noms), et rend une empreinte par zone.
    Les chemins sont RELATIFS à `racine` et rendus avec un `/` initial : la même arborescence posée ailleurs rend la
    même empreinte (c'est ce qui permet de la tester hors de l'image). Un fichier illisible fait LEVER : une empreinte
    qui l'omettrait en silence ne distinguerait plus deux images."""
    racine = os.path.abspath(racine)
    lignes = {nom: [] for nom, _ in zones}
    lignes["systeme"] = []

    def zone_de(rel: str) -> str:
        for nom, pref in zones:
            if _sous(rel, pref):
                return nom
        return "systeme"

    def rel_de(chemin: str) -> str:
        r = os.path.relpath(chemin, racine).replace(os.sep, "/")
        return "/" if r == "." else "/" + r

    exclus_rel = tuple(exclus) + ((rel_de(os.path.abspath(sortie)),) if sortie else ())
    for dossier, sous_dossiers, fichiers in os.walk(racine, topdown=True, followlinks=False):
        rel_dossier = rel_de(dossier)
        sous_dossiers[:] = sorted(d for d in sous_dossiers
                                  if not any(_sous(rel_de(os.path.join(dossier, d)), e) for e in exclus_rel))
        noms = sorted(fichiers) + [d for d in sous_dossiers if os.path.islink(os.path.join(dossier, d))]
        if rel_dossier != "/":
            st = os.lstat(dossier)
            lignes[zone_de(rel_dossier)].append(f"d\t{stat.S_IMODE(st.st_mode):o}\t{rel_dossier}\t-")
        for nom in sorted(noms):
            chemin = os.path.join(dossier, nom)
            rel = rel_de(chemin)
            if any(_sous(rel, e) for e in exclus_rel):
                continue
            st = os.lstat(chemin)
            mode = f"{stat.S_IMODE(st.st_mode):o}"
            if stat.S_ISLNK(st.st_mode):
                lignes[zone_de(rel)].append(f"l\t{mode}\t{rel}\t{os.readlink(chemin)}")
            elif stat.S_ISREG(st.st_mode):
                lignes[zone_de(rel)].append(f"f\t{mode}\t{rel}\t{_sha256_fichier(chemin)}")
            else:                                   # fifo, socket, périphérique : le type seul
                lignes[zone_de(rel)].append(f"s\t{mode}\t{rel}\t-")
    out = {"schema": SCHEMA, "exclus": list(exclus_rel), "zones": {}}
    for nom in sorted(lignes):
        corps = "\n".join(sorted(lignes[nom])).encode("utf-8")
        out["zones"][nom] = {"entrees": len(lignes[nom]), "sha256": hashlib.sha256(corps).hexdigest()}
    return out


if __name__ == "__main__":
    racine, dest = sys.argv[1], sys.argv[2]
    e = empreinte(racine, sortie=dest)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        json.dump(e, f, indent=1, sort_keys=True)
        f.write("\n")
    # UNE ligne balisée dans le journal du build : remote.py la reporte dans IMAGE.json (source « journal du build
    # <Job> »), ce qui compare deux images AVANT tout run, sans exécuter l'image ni tirer une couche (Master 2).
    print(MARQUEUR + " " + json.dumps(e, sort_keys=True, separators=(",", ":")), flush=True)
