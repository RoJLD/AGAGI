"""Différence de deux runs CI : quels tests ROUGES sont apparus, lesquels ont disparu, et à quel compte.

Usage :
    python -m tools.ci_diff_failed <run> <run_de_reference>          # lit les logs par `gh`
    python -m tools.ci_diff_failed --log a.log --log-ref b.log       # logs déjà téléchargés

Pourquoi un instrument et pas un coup d'œil au compte : le 2026-09-26, suite-complete est passé de 68 à 69 rouges au
push de 641e1177. Seule la DIFFÉRENCE des listes a nommé le 69e (test_inventaire_des_portes_..., la porte 24 effacée
de l'inventaire du pilotage) ; un compte stable peut aussi cacher un échange, un rouge qui part et un autre qui
arrive. L'intégrateur de la flotte publie cette différence à chaque push, contre le run du commit précédent.

Absence ≠ zéro : un log sans ligne de bilan pytest (job interrompu, run pas fini) rend `bilan = None` et le rapport
le DIT ; il ne fabrique jamais « 0 failed ». Les erreurs de COLLECTION (`ERROR <nodeid>`) sont comptées à part des
échecs (`FAILED <nodeid>`) : ce n'est pas la même panne.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

DEPOT = "RoJLD/AGAGI"
JOB = "suite-complete"
CALIBRATION = "test_instrument_calibration.py"

# Préfixe d'horodatage des logs d'Actions (« 2026-09-26T09:05:08.7977866Z »), optionnel pour un log local.
_PREFIXE = r"^(?:\S+Z )?"
_ECHEC = re.compile(_PREFIXE + r"FAILED (\S+)", re.M)
_ERREUR = re.compile(_PREFIXE + r"ERROR (\S+::\S+|\S+\.py)", re.M)
_BILAN = re.compile(_PREFIXE + r"=*\s*((?:\d+ (?:failed|passed|skipped|xfailed|xpassed|errors?|deselected|warnings?),?\s*)+)"
                    r"in [\d.]+s", re.M)
_TERME = re.compile(r"(\d+) (failed|passed|skipped|xfailed|xpassed|errors?|deselected|warnings?)")


def lire_bilan(texte: str):
    """Dernière ligne de bilan pytest -> {"failed": n, "passed": n, ...}, ou None si le log n'en porte aucune.

    Seuls les termes PRÉSENTS dans la ligne sont rendus : pytest n'écrit pas « 0 failed », et ce module ne
    l'invente pas non plus."""
    lignes = _BILAN.findall(texte)
    if not lignes:
        return None
    bilan = {}
    for n, terme in _TERME.findall(lignes[-1]):
        cle = {"error": "errors", "warning": "warnings"}.get(terme, terme)
        bilan[cle] = int(n)
    return bilan


def lire_echecs(texte: str) -> dict:
    """{"failed": set(nodeids), "errors": set(nodeids)} lus dans le résumé court de pytest."""
    return {"failed": set(_ECHEC.findall(texte)), "errors": set(_ERREUR.findall(texte))}


def difference(texte: str, texte_ref: str) -> dict:
    """Le run contre sa référence : bilans, rouges nouveaux / disparus, erreurs nouvelles / disparues, rouges
    de la suite de calibration. Fonction PURE sur deux textes de log."""
    e, r = lire_echecs(texte), lire_echecs(texte_ref)
    return {
        "bilan": lire_bilan(texte), "bilan_ref": lire_bilan(texte_ref),
        "nouveaux": sorted(e["failed"] - r["failed"]), "disparus": sorted(r["failed"] - e["failed"]),
        "erreurs_nouvelles": sorted(e["errors"] - r["errors"]),
        "erreurs_disparues": sorted(r["errors"] - e["errors"]),
        "calibration": sorted(n for n in e["failed"] | e["errors"] if CALIBRATION in n),
    }


def _ecart(bilan, bilan_ref, cle):
    if bilan is None or bilan_ref is None:
        return None
    return bilan.get(cle, 0) - bilan_ref.get(cle, 0) if (cle in bilan or cle in bilan_ref) else None


def rapport(d: dict, libelle="run", libelle_ref="référence") -> str:
    def _b(b):
        return "ILLISIBLE (aucune ligne de bilan pytest : job interrompu ou pas fini)" if b is None else \
            " / ".join(f"{v} {k}" for k, v in b.items())
    lignes = [f"bilan {libelle} : {_b(d['bilan'])}", f"bilan {libelle_ref} : {_b(d['bilan_ref'])}"]
    ecarts = [f"{k} {_ecart(d['bilan'], d['bilan_ref'], k):+d}" for k in ("failed", "passed", "skipped")
              if _ecart(d["bilan"], d["bilan_ref"], k) is not None]
    if ecarts:
        lignes.append("écarts : " + ", ".join(ecarts))
    for titre, cle in (("NOUVEAUX rouges", "nouveaux"), ("DISPARUS", "disparus"),
                       ("erreurs de collection NOUVELLES", "erreurs_nouvelles"),
                       ("erreurs de collection DISPARUES", "erreurs_disparues"),
                       (f"rouges de {CALIBRATION} dans {libelle}", "calibration")):
        lignes.append(f"--- {titre} ({len(d[cle])}) :")
        lignes.extend(f"  {n}" for n in d[cle])
    return "\n".join(lignes)


def telecharger_log(run: str, job: str = JOB, depot: str = DEPOT) -> str:
    """Log complet du job `job` du run, par `gh`. Refuse (RuntimeError nommée) un job absent ou pas terminé :
    un log partiel n'a pas de bilan, et une différence sur lui ne dirait rien."""
    r = subprocess.run(["gh", "run", "view", str(run), "-R", depot, "--json", "jobs"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"gh run view {run} a échoué : {r.stderr.strip()}")
    jobs = [j for j in json.loads(r.stdout)["jobs"] if j["name"] == job]
    if not jobs:
        raise RuntimeError(f"run {run} : aucun job nommé {job!r}")
    if jobs[0]["status"] != "completed":
        raise RuntimeError(f"run {run} : le job {job} n'est pas terminé ({jobs[0]['status']}) — attendre sa fin")
    r = subprocess.run(["gh", "api", f"repos/{depot}/actions/jobs/{jobs[0]['databaseId']}/logs"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"log du job {jobs[0]['databaseId']} illisible : {r.stderr.strip()}")
    return r.stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", nargs="?")
    ap.add_argument("run_ref", nargs="?")
    ap.add_argument("--log", help="log du run, déjà téléchargé (sinon lu par gh)")
    ap.add_argument("--log-ref", help="log de la référence, déjà téléchargé")
    ap.add_argument("--job", default=JOB)
    ap.add_argument("--depot", default=DEPOT)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.log and a.log_ref:
            with open(a.log, encoding="utf-8", errors="replace") as fh:
                texte = fh.read()
            with open(a.log_ref, encoding="utf-8", errors="replace") as fh:
                texte_ref = fh.read()
            libelle, libelle_ref = a.log, a.log_ref
        elif a.run and a.run_ref:
            texte, texte_ref = telecharger_log(a.run, a.job, a.depot), telecharger_log(a.run_ref, a.job, a.depot)
            libelle, libelle_ref = f"run {a.run}", f"run {a.run_ref}"
        else:
            ap.error("donner <run> <run_ref>, ou --log et --log-ref")
    except (OSError, RuntimeError) as exc:
        print(f"REFUS : {exc}", file=sys.stderr)
        return 2
    d = difference(texte, texte_ref)
    print(json.dumps(d, ensure_ascii=False, indent=1) if a.json else rapport(d, libelle, libelle_ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
