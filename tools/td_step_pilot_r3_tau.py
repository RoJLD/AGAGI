"""TD-STEP-PILOT-R3, mesure de τ AVANT le sceau (P4.19 (c) ; enchaînement (3) -> (2) -> (1) recommandé par Master 2 et
soumis à robla le 2026-10-13) : la dispersion VRAIE, entre seeds, de l'effet de la trace (d = lam09 − lam0, en pas de la
grille exhaustive 576), mesurée sur des seeds TENUES À L'ÉCART (13-24) pour choisir la marge ou le compte de
PAS_D_EFFET et déclarer le modèle de bruit de la calibration, sans regarder une cellule des seeds du verdict (1-12).

Pourquoi la dispersion observée EST τ : l'éval est EXHAUSTIVE (les K² couples, argmax, aucun tirage) et l'entraînement
est déterministe par seed -- il n'y a pas de bruit d'éval à retrancher (la calibration v1 en comptait 9,3 pas par bras).

Deux bras SEULEMENT : `lam0` (TD(0)) et `lam09` (trace λ 0,9), pas 4,0, 3000 épisodes, 16 agents, K = 6, traces remises à
zéro à chaque épisode -- le dispositif de R3. JAMAIS le sham : il donnerait f sur des seeds voisines avant le sceau
(chemin bifurquant sur la grandeur du verdict). Refus EN TÊTE, avant toute construction : une seed du verdict, un bras
hors des deux. Lieu = celui de R3 (nexus, threads posés par le déport et publiés) ; l'agrégat REFUSE des cellules de
lieux mêlés (torch diffère au dernier bit entre nexus et batcave).

Une commande = une cellule = un fichier (déport : une sortie par Job) :
  python -m tools.td_step_pilot_r3_tau cellule --bras lam0 --seed 13
  python -m tools.td_step_pilot_r3_tau agreger [--deport runs/deport]   # τ, aucune simulation
Sorties : results/td_step_pilot_r3_tau/<bras>_seed<seed>.json (par cellule), results/td_step_pilot_r3_tau.json (SUIVI).
"""
import argparse
import glob
import json
import os
import platform
import re
import statistics
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file   # noqa: E402  (porte 12)

K, N_AGENTS, EPISODES, PAS, LAMBDA = 6, 16, 3000, 4.0, 0.9
N_GRILLE = N_AGENTS * K * K                       # 576
MARGE_PAS = 29                                    # marge du brouillon v1 (0,05 × 576 arrondi au-dessus)
BRAS = {"lam0": 0.0, "lam09": LAMBDA}
SEEDS_TENUES = tuple(range(13, 25))
SEEDS_VERDICT = tuple(range(1, 13))
DOSSIER = "td_step_pilot_r3_tau"
_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def _refus(bras, seed):
    """Refus EN TÊTE (aucune construction, aucun import de torch) : jamais une seed du verdict, jamais un autre bras."""
    if bras not in BRAS:
        raise ValueError(f"bras {bras!r} refusé : seuls {sorted(BRAS)} -- JAMAIS le sham avant le sceau de R3")
    if seed in SEEDS_VERDICT:
        raise ValueError(f"seed {seed} refusée : les seeds {SEEDS_VERDICT[0]}-{SEEDS_VERDICT[-1]} sont celles du "
                         "VERDICT de R3, on ne les regarde pas avant le sceau")
    if seed not in SEEDS_TENUES:
        raise ValueError(f"seed {seed} hors des seeds tenues à l'écart {SEEDS_TENUES[0]}-{SEEDS_TENUES[-1]}")


def _chemin_cellule(bras, seed):
    return str(results_file(DOSSIER, f"{bras}_seed{seed}.json"))


def _environnement():
    import numpy as np
    import torch
    return {"torch": torch.__version__, "numpy": np.__version__, "python": platform.python_version(),
            "hote": platform.node(), "systeme": platform.platform(), "threads_torch": torch.get_num_threads(),
            "threads_env": {v: os.environ.get(v) for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                           "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}}


def cellule(bras, seed, entraine=None):
    """Une cellule : entraîne le bras au seed, évalue EXHAUSTIVEMENT, écrit son fichier. `entraine` injectable (tests)."""
    _refus(bras, seed)
    from tools.preregister import provenance
    if entraine is None:
        from tools.td_step_pilot import _train_eval_td_step as entraine
    t0, c0 = time.time(), time.process_time()
    acc640, dose = entraine(seed, BRAS[bras], EPISODES, N_AGENTS, K, PAS, trace_reset_per_episode=True,
                            eval_exhaustive=True, mesure_dose=True)
    ex = dose["eval_exhaustive"]
    if ex["n"] != N_GRILLE:
        raise ValueError(f"grille {ex['n']} ≠ {N_GRILLE} : la cellule ne mesure pas le dispositif de R3")
    rec = {"bras": bras, "seed": seed, "lambda": BRAS[bras], "pas": PAS, "episodes": EPISODES, "n_agents": N_AGENTS,
           "K": K, "succes": int(ex["succes"]), "n": int(ex["n"]), "succes_par_agent": ex["succes_par_agent"],
           "acc640_tiree": acc640, "dose": {k: v for k, v in dose.items() if k != "eval_exhaustive"},
           "mur_s": time.time() - t0, "cpu_s": time.process_time() - c0, "environnement": _environnement(),
           "provenance": provenance()}
    p = _chemin_cellule(bras, seed)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rec, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{bras} seed {seed} : {rec['succes']}/{rec['n']} ({rec['mur_s']:.0f} s mur) -> {p}", flush=True)
    return rec


def measure_tau(succes):
    """τ depuis {(bras, seed): succès sur 576}. PURE. d_s = succès(lam09) − succès(lam0), en pas, par seed tenue à l'écart
    où les DEUX bras sont présents. Rend la moyenne, l'écart-type (ddof 1) = τ, le compte des d_s > MARGE_PAS, et les
    cellules manquantes. Moins de 2 seeds complètes : τ None (jamais 0 fabriqué) ; une seed du verdict : REFUS."""
    for (b, sd) in succes:
        _refus(b, sd)
    complets = sorted(sd for sd in SEEDS_TENUES if ("lam0", sd) in succes and ("lam09", sd) in succes)
    manquantes = sorted(f"{b}|seed={sd}" for sd in SEEDS_TENUES for b in BRAS if (b, sd) not in succes)
    d = [int(succes[("lam09", sd)]) - int(succes[("lam0", sd)]) for sd in complets]
    out = {"seeds_completes": complets, "d_pas": d, "manquantes": manquantes, "marge_pas": MARGE_PAS,
           "n_grille": N_GRILLE}
    if len(d) < 2:
        return dict(out, moyenne_pas=(float(d[0]) if d else None), tau_pas=None,
                    d_sup_marge=None, raison=f"{len(d)} seed(s) complète(s) : pas d'écart-type")
    return dict(out, moyenne_pas=statistics.mean(d), tau_pas=statistics.stdev(d),
                d_sup_marge=sum(1 for x in d if x > MARGE_PAS), raison=None)


def _manifestes(deport):
    """{(bras, seed): résumé du MANIFEST du Job qui a produit la cellule} -- image par son DIGEST seulement (dépôt
    public : l'adresse du registre ne sort jamais)."""
    out = {}
    for p in glob.glob(os.path.join(deport, "*", "MANIFEST.json")):
        try:
            m = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        cmd = m.get("commande") or []
        if "tools.td_step_pilot_r3_tau" not in cmd or "cellule" not in cmd:
            continue
        try:
            bras, seed = cmd[cmd.index("--bras") + 1], int(cmd[cmd.index("--seed") + 1])
        except (ValueError, IndexError):
            continue
        img = m.get("image") or ""
        dig = re.search(r"@(sha256:[0-9a-f]{64})", img)
        cpu = m.get("cpu") or {}
        out[(bras, seed)] = {"job": m.get("job"), "lieu": m.get("lieu"), "sha": m.get("sha"),
                             "returncode": m.get("returncode"), "image_digest": dig.group(1) if dig else None,
                             "limite_cpu": cpu.get("limite_cpu"), "threads_poses": cpu.get("threads_poses"),
                             "threads_source": cpu.get("threads_source"), "duree_mur_s": m.get("duree_mur_s")}
    return out


def agreger(deport=os.path.join("runs", "deport")):
    """Relit les cellules, refuse des LIEUX mêlés, calcule τ, publie results/td_step_pilot_r3_tau.json (suivi)."""
    cellules = {}
    for p in sorted(glob.glob(os.path.join(str(results_file(DOSSIER)), "*_seed*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        cellules[(r["bras"], int(r["seed"]))] = r
    lieux = {(r["environnement"]["systeme"].split("-")[0], r["environnement"]["torch"]) for r in cellules.values()}
    if len(lieux) > 1:
        raise ValueError(f"lieux mêlés {sorted(lieux)} : torch diffère au dernier bit entre lieux, refus d'agréger")
    man = _manifestes(deport)
    tau = measure_tau({k: r["succes"] for k, r in cellules.items()})
    db = {"objet": __doc__.split("\n\n")[0], "tau": tau, "lieu": sorted(lieux),
          "cellules": {f"{b}|seed={sd}": {"succes": r["succes"], "n": r["n"], "succes_par_agent": r["succes_par_agent"],
                                          "acc640_tiree": r["acc640_tiree"], "mur_s": r["mur_s"], "cpu_s": r["cpu_s"],
                                          "environnement": r["environnement"], "provenance": r["provenance"],
                                          "dose_updates": r["dose"].get("updates"),
                                          "manifeste": man.get((b, sd))}
                       for (b, sd), r in sorted(cellules.items())}}
    texte = json.dumps(db, indent=1, ensure_ascii=False)
    if _IP.search(texte):
        raise ValueError("adresse de type IP dans l'agrégat (dépôt public) : refus d'écrire")
    dest = str(results_file("td_step_pilot_r3_tau.json"))
    open(dest, "w", encoding="utf-8").write(texte)
    print(json.dumps(tau, indent=1, ensure_ascii=False), "\n->", dest)
    return db


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("cellule")
    c.add_argument("--bras", required=True)
    c.add_argument("--seed", type=int, required=True)
    g = sp.add_parser("agreger")
    g.add_argument("--deport", default=os.path.join("runs", "deport"))
    a = ap.parse_args(argv)
    if a.cmd == "cellule":
        cellule(a.bras, a.seed)
    else:
        agreger(a.deport)


if __name__ == "__main__":
    main()
