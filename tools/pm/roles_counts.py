"""Compteurs des rôles, RECOMPUTÉS (spec §6.2) : alertes du PM (journal) et ratio science/méthodo par CHEMINS de
fichiers modifiés depuis DEBUT. Écrit paths.pm_dir("ROLES_COUNTS.json") — jamais recopié dans ROLES.md à la main.
science = docs/EDR, results, docs/preregistrations ; méthodo = tools/check_*, tests/sandbox, docs/REF, docs/roadmap,
CLAUDE.md ; le reste = autre, publié à part. Point de départ publié : 26 / 78 (2026-09-08)."""
import argparse
import json
import os
import subprocess
import sys
import time

from src import paths
from tools.pm import alerts as AL

DEBUT = "2026-09-16"
_SCIENCE = ("docs/EDR/", "results/", "docs/preregistrations/")
_METHODO = ("tools/check_", "tests/sandbox/", "docs/REF/", "docs/roadmap/")


def bucket(chemin):
    c = chemin.replace("\\", "/")
    if c == "CLAUDE.md" or c.startswith(_METHODO):
        return "methodo"
    if c.startswith(_SCIENCE):
        return "science"
    return "autre"


def fichiers_modifies(repo_root, depuis=DEBUT):
    try:
        out = subprocess.run(["git", "log", "--all", f"--since={depuis}", "--name-only", "--format="], cwd=repo_root,
                             capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return sorted({l.strip() for l in out.stdout.splitlines() if l.strip()})


def compute_counts(journal, fichiers, now):
    f = {"science": 0, "methodo": 0, "autre": 0}
    for c in (fichiers or []):
        f[bucket(c)] += 1
    ratio = (f["science"] / f["methodo"]) if f["methodo"] else None
    return {"generated_at": now, "depuis": DEBUT, "alertes": AL.compteurs(journal, now), "fichiers": f,
            "ratio_science_methodo": ratio, "fichiers_disponibles": fichiers is not None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=os.getcwd())
    args = ap.parse_args(argv)
    now = time.time()
    c = compute_counts(AL.charger(paths.pm_dir("alerts.jsonl")), fichiers_modifies(args.repo_root), now)
    os.makedirs(paths.pm_dir(), exist_ok=True)
    with open(paths.pm_dir("ROLES_COUNTS.json"), "w", encoding="utf-8") as fh:
        json.dump(c, fh, ensure_ascii=False, indent=1)
    print(f"alertes {c['alertes']} | fichiers {c['fichiers']} | science/méthodo = {c['ratio_science_methodo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
