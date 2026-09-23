"""Compteurs des rôles, RECOMPUTÉS (spec §6.2) : alertes du PM (journal) et ratio science/méthodo par CHEMINS de
fichiers modifiés sur une FENÊTRE GLISSANTE de 30 jours. Écrit paths.pm_dir("ROLES_COUNTS.json") — jamais recopié
dans ROLES.md à la main.
science = docs/EDR, results, docs/preregistrations ; méthodo = tools/check_*, tools/pm, tests/sandbox, docs/REF,
docs/roadmap, .claude, docs/superpowers, CLAUDE.md ; le reste = autre, publié à part.

⚠️ `DEBUT` n'est PLUS la borne de mesure, seulement le point de départ PUBLIÉ. Une borne FIXE fait
diverger le ratio : plus le temps passe, plus il agrège, et « le ratio du mois » devient « le ratio
depuis toujours » sans que rien ne le dise. La fenêtre glisse ; sa date effective est publiée dans
`fenetre`, pour qu'un chiffre cité soit toujours rattachable à sa période.
⚠️ Le point de départ publié 26 / 78 (2026-09-08) comptait des COMMITS ; ici on compte des FICHIERS
modifiés — deux unités, non comparables."""
import argparse
import json
import os
import subprocess
import sys
import time

from src import paths
from tools.pm import alerts as AL
from tools.pm.snapshot import ancrer_data_root

DEBUT = "2026-09-16"
FENETRE_JOURS = 30
_SCIENCE = ("docs/EDR/", "results/", "docs/preregistrations/")
# `tools/pm/`, `.claude/` et `docs/superpowers/` SONT de la méthodologie : la couche des rôles, les
# hooks et les specs de processus tombaient en « autre », donc le dénominateur du ratio 1:1 excluait
# précisément le travail que ce ratio est censé borner.
_METHODO = ("tools/check_", "tools/pm/", "tests/sandbox/", "docs/REF/", "docs/roadmap/",
            ".claude/", "docs/superpowers/")


def bucket(chemin):
    c = chemin.replace("\\", "/")
    if c == "CLAUDE.md" or c.startswith(_METHODO):
        return "methodo"
    if c.startswith(_SCIENCE):
        return "science"
    return "autre"


def _depuis_glissant(now=None, jours=FENETRE_JOURS):
    return time.strftime("%Y-%m-%d", time.localtime((time.time() if now is None else float(now)) - jours * 86400.0))


def fichiers_modifies(repo_root, depuis=None, now=None):
    """`depuis=None` -> fenêtre GLISSANTE de 30 jours se terminant à `now` (défaut : maintenant).

    ⚠️ Une DATE NUE (`--since=2026-09-16`) est lue par git à l'HEURE COURANTE de cette date-là : le
    2026-09-16, ça vaut « depuis maintenant », donc ZÉRO commit (mesuré : 0 contre 44 avec l'heure
    fixée à minuit) et la fenêtre DÉRIVE avec l'horloge au lieu d'être ancrée au jour. Toujours fixer
    l'heure."""
    if depuis is None:
        depuis = _depuis_glissant(now)
    try:
        out = subprocess.run(["git", "log", "--all", f"--since={depuis} 00:00", "--name-only", "--format="],
                             cwd=repo_root, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return sorted({l.strip() for l in out.stdout.splitlines() if l.strip()})


def compute_counts(journal, fichiers, now, fenetre_jours=FENETRE_JOURS):
    f = {"science": 0, "methodo": 0, "autre": 0}
    for c in (fichiers or []):
        f[bucket(c)] += 1
    ratio = (f["science"] / f["methodo"]) if f["methodo"] else None
    return {"generated_at": now, "depuis": DEBUT,
            "fenetre": {"depuis": _depuis_glissant(now, fenetre_jours), "jours": fenetre_jours},
            "alertes": AL.compteurs(journal, now), "fichiers": f,
            "ratio_science_methodo": ratio, "fichiers_disponibles": fichiers is not None}


def main(argv=None):
    ancrer_data_root()                                  # AVANT tout paths.* : le journal du PM vit dans le dépôt COMMUN
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=os.getcwd())
    args = ap.parse_args(argv)
    now = time.time()
    c = compute_counts(AL.charger(paths.pm_dir("alerts.jsonl")), fichiers_modifies(args.repo_root, now=now), now)
    os.makedirs(paths.pm_dir(), exist_ok=True)
    with open(paths.pm_dir("ROLES_COUNTS.json"), "w", encoding="utf-8") as fh:
        json.dump(c, fh, ensure_ascii=False, indent=1)
    print(f"alertes {c['alertes']} | fichiers {c['fichiers']} | science/méthodo = {c['ratio_science_methodo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
