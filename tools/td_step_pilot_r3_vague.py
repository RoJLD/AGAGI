"""Vagues de déport de R3 et du pilote τ (P4.19) : soumettre des cellules sur nexus (une commande par Job), puis rendre
un VERDICT PAR CELLULE -- jamais un vert global. Le verdict décide de la suite (relancer, rapatrier, refaire) et donc de
ce qui pourra entrer dans l'agrégat : la procédure vit dans git, au sha du run, avec ses cas à réponse connue
(E27 appliquée à la procédure ; exigence de Master 2, 2026-10-14). Remplace les scripts shell hors suivi du pilote τ.

Classement selon la table PUBLIÉE (P2.168, docs/REF/REF-DEPORT-NEXUS.md, « Codes de sortie d'executer ») ; les codes et
libellés sont IMPORTÉS de tools/jobs/remote.py, jamais recopiés. « relançable » = relançable TEL QUEL, sans correction :
  85, ou « [remote] REFUS » au journal -> REFUS_LOCAL   rien n'a tourné ; relançable SEULEMENT si le refus dit « quota du
                                                        namespace plein » -- un refus de fenêtre, de garde d'image, de
                                                        quota impossible ou de nœud éteint se CORRIGE, il ne s'attend pas
  86 -> REFUS_POD      refus dans le pod, rien n'a tourné : lire REFUS.json (jamais relançable tel quel)
  87 -> SORTIE_PERDUE  le run a tourné, sa sortie est perdue : PAS un succès ; « relancer le run » (table) -> relançable
  88 -> SANS_SORTIE    Job fini SANS sortie : relançable ssi le journal imprime « "relancable": true » (oom, éviction,
                       préemption, nœud perdu)
  89 -> A_RAPATRIER    le run a PU tourner : `rapatrier <job>` ou `installer`, JAMAIS une relance à l'aveugle
  « le RUNNER a rendu » au journal -> RUNNER   un code 85-89 rendu par le runner LUI-MÊME : le MANIFEST tranche
  0 ET fichier de sortie présent -> OK
  tout le reste (code inconnu, 0 sans fichier, aucun code) -> RUNNER, jamais OK
Avant P2.168 un refus local sortait en 2 : le JOURNAL reste lu pour lui.

Spécifications de cellule :
  cellule:<bras>:<pas>:<seed>   -> python -m tools.td_step_pilot_r3 cellule … (td0_app : --rho calculé ICI, sur la
                                   batcave, depuis lam0 et lam09 RAPATRIÉS ; s'ils manquent, RHO_ABSENT, jamais soumis)
  reference:<ref>:<seed>        -> python -m tools.td_step_pilot_r3 reference …
  tau:<bras>:<seed>             -> python -m tools.td_step_pilot_r3_tau cellule … (pas p1)
  tau:<bras>:<pas>:<seed>[:<n>] -> idem au pas donné, réplique n (séance du 2026-10-14)
Usage (depuis le dépôt ou un worktree -- bail et E32) :
  python -m tools.td_step_pilot_r3_vague --sha <sha> --vague <nom> --journaux <dossier> <spec> [<spec> ...]
"""
import argparse
import json
import os
import sys
import threading
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file   # noqa: E402  (porte 12)
from tools.jobs.remote import (LIBELLES_SORTIE, SORTIE_ABANDON, SORTIE_FIN_SANS_SORTIE,  # noqa: E402  (table P2.168)
                               SORTIE_PERDUE, SORTIE_REFUS_LOCAL, SORTIE_REFUS_POD)

ETATS = ("OK", "REFUS_LOCAL", "REFUS_POD", "SORTIE_PERDUE", "SANS_SORTIE", "A_RAPATRIER", "RUNNER", "RHO_ABSENT")
REGLAGES = ["--cpu", "1", "--req-cpu", "0.5", "--mem", "4Gi", "--deadline-s", "1200", "--attente-s", "900"]
PREFIXE_REFUS_LOCAL = f"[remote] {LIBELLES_SORTIE[SORTIE_REFUS_LOCAL]}"   # seul le 85 commence ainsi (table)
QUOTA_PLEIN = "quota du namespace plein"                                  # le texte du refus de tools/jobs/remote.py
CODE_DU_RUNNER = "le RUNNER a rendu"                                      # code réservé rendu par le runner lui-même
_PAR_CODE = {SORTIE_REFUS_POD: "REFUS_POD", SORTIE_PERDUE: "SORTIE_PERDUE", SORTIE_FIN_SANS_SORTIE: "SANS_SORTIE",
             SORTIE_ABANDON: "A_RAPATRIER"}


def classer_cellule(rc, journal, sortie_presente):
    """Verdict d'UNE cellule. PURE. `rc` entier ou None (code absent), `journal` texte, `sortie_presente` booléen."""
    j = journal or ""
    if CODE_DU_RUNNER in j:
        return "RUNNER"
    if rc in _PAR_CODE:
        return _PAR_CODE[rc]
    if rc == SORTIE_REFUS_LOCAL or PREFIXE_REFUS_LOCAL in j:
        return "REFUS_LOCAL"
    if rc == 0 and sortie_presente:
        return "OK"
    return "RUNNER"


def relancable(etat, journal):
    """Relançable TEL QUEL, selon la colonne « quoi faire » de la table : un refus local de QUOTA PLEIN (filtrer sur la
    phrase entière : « il ne serait JAMAIS admis » est aussi un refus de quota, et se corrige), une sortie perdue, une fin
    sans sortie que le déport déclare relançable. Jamais un abandon après soumission (le run a pu tourner)."""
    j = journal or ""
    if etat == "REFUS_LOCAL":
        return QUOTA_PLEIN in j
    if etat == "SORTIE_PERDUE":
        return True
    if etat == "SANS_SORTIE":
        return '"relancable": true' in j
    return False


def analyser_spec(spec):
    """(module, arguments, nom, (dossier, fichier)) d'une spécification ; REFUS d'une forme inconnue."""
    parts = spec.split(":")
    if parts[0] == "cellule" and len(parts) == 4:
        _, bras, pas, sd = parts
        return ("tools.td_step_pilot_r3", ["cellule", "--bras", bras, "--pas", pas, "--seed", str(int(sd))],
                f"{bras}_{pas}_seed{int(sd)}", ("td_step_pilot_r3", f"{bras}_{pas}_seed{int(sd)}.json"))
    if parts[0] == "reference" and len(parts) == 3:
        _, ref, sd = parts
        return ("tools.td_step_pilot_r3", ["reference", "--ref", ref, "--seed", str(int(sd))],
                f"{ref}_seed{int(sd)}", ("td_step_pilot_r3", f"{ref}_seed{int(sd)}.json"))
    if parts[0] == "tau" and len(parts) in (3, 4, 5):
        from tools.td_step_pilot_r3_tau import _nom
        bras = parts[1]
        pas, sd, rep = ("p1", parts[2], 0) if len(parts) == 3 else (parts[2], parts[3], int(parts[4]) if
                                                                      len(parts) == 5 else 0)
        args = ["cellule", "--bras", bras, "--seed", str(int(sd))] + (["--pas", pas] if pas != "p1" else []) + \
            (["--replique", str(rep)] if rep else [])
        nom = _nom(bras, int(sd), pas, rep)
        return ("tools.td_step_pilot_r3_tau", args, nom, ("td_step_pilot_r3_tau", f"{nom}.json"))
    raise ValueError(f"spécification {spec!r} inconnue : cellule:<bras>:<pas>:<seed> | reference:<ref>:<seed> | "
                     "tau:<bras>:<seed> | tau:<bras>:<pas>:<seed>[:<réplique>]")


def _rho_par_defaut(pas, sd):
    """Par le CLI du runner R3 (`rho`) : c'est LUI qui vérifie la règle scellée et déclare son design (porte 11) ; la
    procédure des vagues n'exécute aucune règle."""
    from tools.td_step_pilot_r3 import main_r3
    return main_r3(["rho", "--pas", pas, "--seed", str(sd)])


def _soumettre_par_defaut(cmd, journal):
    import subprocess
    with open(journal, "w", encoding="utf-8") as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=_ROOT).returncode


def lancer_vague(sha, vague, specs, journaux, soumettre=None, rho=None, pause_s=15.0):
    """Soumet chaque cellule (en parallèle, échelonnée de `pause_s`), attend toutes, puis classe chacune. `soumettre`
    et `rho` injectables (tests). Rend {nom: {etat, rc, relancable}} et l'écrit dans <journaux>/<vague>.json."""
    soumettre = soumettre or _soumettre_par_defaut
    rho = rho or _rho_par_defaut
    os.makedirs(journaux, exist_ok=True)
    out, fils = {}, []
    for spec in specs:
        module, args, nom, (dossier, fichier) = analyser_spec(spec)
        journal = os.path.join(journaux, f"{vague}__{nom}.log")
        if args[:3] == ["cellule", "--bras", "td0_app"]:
            try:
                args = args + ["--rho", rho(args[4], int(args[6]))]
            except Exception as exc:                    # noqa: BLE001 -- dit, jamais soumis
                out[nom] = {"etat": "RHO_ABSENT", "rc": None, "relancable": False, "raison": repr(exc)}
                continue
        cmd = [sys.executable, "-m", "tools.jobs.remote", "executer", "--sha", sha, *REGLAGES, "--", "-m", module,
               *args]
        res = {}

        def tache(cmd=cmd, journal=journal, res=res):
            res["rc"] = soumettre(cmd, journal)
        t = threading.Thread(target=tache)
        t.start()
        fils.append((nom, journal, str(results_file(dossier, fichier)), res, t))
        if pause_s:
            time.sleep(pause_s)
    for nom, journal, sortie, res, t in fils:
        t.join()
        texte = open(journal, encoding="utf-8", errors="replace").read() if os.path.exists(journal) else ""
        etat = classer_cellule(res.get("rc"), texte, os.path.exists(sortie))
        out[nom] = {"etat": etat, "rc": res.get("rc"), "relancable": relancable(etat, texte)}
    bilan = {"vague": vague, "sha": sha, "cellules": out,
             "ok": sum(1 for v in out.values() if v["etat"] == "OK"), "n": len(specs)}
    json.dump(bilan, open(os.path.join(journaux, f"{vague}.json"), "w", encoding="utf-8"), indent=1,
              ensure_ascii=False)
    return bilan


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sha", required=True)
    ap.add_argument("--vague", required=True)
    ap.add_argument("--journaux", required=True, help="dossier des journaux et du bilan (hors git)")
    ap.add_argument("--pause-s", type=float, default=15.0)
    ap.add_argument("specs", nargs="+")
    a = ap.parse_args(argv)
    bilan = lancer_vague(a.sha, a.vague, a.specs, a.journaux, pause_s=a.pause_s)
    for nom, v in sorted(bilan["cellules"].items()):
        print(f"{v['etat']:13s} rc={v['rc']} {nom}" + ("  (relançable tel quel)" if v["relancable"] else ""))
    print(f"cellules OK : {bilan['ok']} / {bilan['n']}")
    return bilan


if __name__ == "__main__":
    main()
