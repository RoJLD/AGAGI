"""TD-STEP-PILOT-R3, mesures AVANT le sceau sur des seeds TENUES À L'ÉCART (13-24), jamais celles du verdict (1-12).

(a) τ (P4.19 (c), 2026-10-13) : la dispersion VRAIE, entre seeds, de l'effet de la trace (d = lam09 − lam0, en pas de la
grille exhaustive 576), pour choisir la marge de PAS_D_EFFET et déclarer le modèle de bruit de la calibration.
Pourquoi la dispersion observée EST τ : l'éval est EXHAUSTIVE (les K² couples, argmax, aucun tirage) et l'entraînement
est déterministe par seed -- il n'y a pas de bruit d'éval à retrancher.

(b) Séance du 2026-10-14 (décisions de robla après la revue de la règle v2) :
  (4) μ et τ au pas SECONDAIRE 4√2 (`--pas p2`), la règle exigeant TRANSPORTE aux deux pas ;
  (7) dispersion du rapport appliqué/contrefactuel de la garde de dose du sham, par un sham EN DOSE SEULE (`sham_dose` :
      AUCUNE évaluation, ni tirée ni exhaustive -- la cellule ne porte AUCUNE accuracy, donc aucun f n'est vu) ;
  (8) déterminisme par seed sur nexus (`--replique N` : une cellule lam0 / lam09 refaite, comparée au bit) et no-op de
      f̂ par un sham IDENTITÉ (`sham_identite` : δ̃ = δ, f = 1 attendu ; il ne révèle rien du sham DÉCALÉ).
JAMAIS le sham décalé avec évaluation : il donnerait f sur des seeds voisines avant le sceau (chemin bifurquant sur la
grandeur du verdict). Refus EN TÊTE, avant toute construction. Lieu = celui de R3 (nexus) ; l'agrégat REFUSE des cellules
de lieux mêlés (torch diffère au dernier bit entre nexus et batcave).

Une commande = une cellule = un fichier (déport : une sortie par Job) :
  python -m tools.td_step_pilot_r3_tau cellule --bras <lam0|lam09|sham_dose|sham_identite> --seed S [--pas p1|p2]
                                               [--replique N]
  python -m tools.td_step_pilot_r3_tau agreger [--deport runs/deport]   # aucune simulation
Sorties : results/td_step_pilot_r3_tau/<cellule>.json (par cellule), results/td_step_pilot_r3_tau.json (SUIVI).
"""
import argparse
import glob
import json
import math
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
PAS_VALEURS = {"p1": PAS, "p2": PAS * math.sqrt(2.0)}
N_GRILLE = N_AGENTS * K * K                       # 576
MARGE_PAS = 29                                    # marge du brouillon v1 (0,05 × 576 arrondi au-dessus)
BRAS = {"lam0": 0.0, "lam09": LAMBDA}             # les bras de τ (évaluation exhaustive)
MODES = {"sham_dose": ("decale", False), "sham_identite": ("identite", True)}   # (mode du sham, évalué ?)
GARDE_DOSE = (0.9, 1.1)                           # bande de la règle v2, confrontée ici à sa dispersion
SEEDS_TENUES = tuple(range(13, 25))
SEEDS_VERDICT = tuple(range(1, 13))
DOSSIER = "td_step_pilot_r3_tau"
_IP = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")


def _refus(bras, seed, pas="p1", replique=0):
    """Refus EN TÊTE (aucune construction, aucun import de torch) : jamais une seed du verdict, jamais le sham décalé
    évalué, jamais un pas hors règle ; une réplique ne vaut que pour lam0 / lam09."""
    if bras not in BRAS and bras not in MODES:
        raise ValueError(f"bras {bras!r} refusé : seuls {sorted(BRAS) + sorted(MODES)} -- JAMAIS le sham décalé avec "
                         "évaluation avant le sceau de R3")
    if seed in SEEDS_VERDICT:
        raise ValueError(f"seed {seed} refusée : les seeds {SEEDS_VERDICT[0]}-{SEEDS_VERDICT[-1]} sont celles du "
                         "VERDICT de R3, on ne les regarde pas avant le sceau")
    if seed not in SEEDS_TENUES:
        raise ValueError(f"seed {seed} hors des seeds tenues à l'écart {SEEDS_TENUES[0]}-{SEEDS_TENUES[-1]}")
    if pas not in PAS_VALEURS:
        raise ValueError(f"pas {pas!r} hors règle : {sorted(PAS_VALEURS)}")
    if int(replique) < 0 or (int(replique) and bras not in BRAS):
        raise ValueError(f"réplique {replique} refusée : seules lam0 et lam09 se répliquent (déterminisme par seed)")


def _nom(bras, seed, pas="p1", replique=0):
    """Nom de cellule ; celui des 24 cellules de τ du 2026-10-13 (pas p1, sans réplique) est INCHANGÉ."""
    base = f"{bras}_seed{seed}" if pas == "p1" else f"{bras}_{pas}_seed{seed}"
    return base + (f"_rep{int(replique)}" if int(replique) else "")


def _chemin_cellule(bras, seed, pas="p1", replique=0):
    return str(results_file(DOSSIER, f"{_nom(bras, seed, pas, replique)}.json"))


def _environnement():
    import numpy as np
    import torch
    return {"torch": torch.__version__, "numpy": np.__version__, "python": platform.python_version(),
            "hote": platform.node(), "systeme": platform.platform(), "threads_torch": torch.get_num_threads(),
            "threads_env": {v: os.environ.get(v) for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                           "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}}


def cellule(bras, seed, entraine=None, pas="p1", replique=0):
    """Une cellule ; écrit son fichier. `entraine` injectable (tests). Un `sham_dose` ne porte AUCUNE accuracy (refus
    d'écrire si l'entraîneur en rend une)."""
    _refus(bras, seed, pas, replique)
    from tools.preregister import provenance
    if entraine is None:
        from tools.td_step_pilot import _train_eval_td_step as entraine
    lr = PAS_VALEURS[pas]
    t0, c0 = time.time(), time.process_time()
    rec = {"bras": bras, "seed": seed, "pas": lr, "pas_cle": pas, "replique": int(replique), "episodes": EPISODES,
           "n_agents": N_AGENTS, "K": K}
    if bras in BRAS:
        acc640, dose = entraine(seed, BRAS[bras], EPISODES, N_AGENTS, K, lr, trace_reset_per_episode=True,
                                eval_exhaustive=True, mesure_dose=True)
    else:
        mode, evalue = MODES[bras]
        if evalue:
            acc640, dose = entraine(seed, LAMBDA, EPISODES, N_AGENTS, K, lr, trace_reset_per_episode=True,
                                    eval_exhaustive=True, mesure_dose=True, sham=mode)
        else:
            acc640, dose = entraine(seed, LAMBDA, EPISODES, N_AGENTS, K, lr, eval_batches=0,
                                    trace_reset_per_episode=True, eval_exhaustive=False, mesure_dose=True, sham=mode)
            if acc640 is not None or "eval_exhaustive" in dose:
                raise ValueError("sham en dose seule : l'entraîneur a rendu une accuracy -- refus d'écrire (aucun f "
                                 "ne doit être vu avant le sceau)")
            sh = dose["sham"]
            cf = sh["chemin_porte_contrefactuel"]
            rec.update({"lambda": LAMBDA, "sham": sh,
                        "ratio_applique_contrefactuel": (sh["chemin_porte_applique"] / cf) if cf > 0 else None})
    if "ratio_applique_contrefactuel" not in rec:
        ex = dose["eval_exhaustive"]
        if ex["n"] != N_GRILLE:
            raise ValueError(f"grille {ex['n']} ≠ {N_GRILLE} : la cellule ne mesure pas le dispositif de R3")
        rec.update({"lambda": BRAS.get(bras, LAMBDA), "succes": int(ex["succes"]), "n": int(ex["n"]),
                    "succes_par_agent": ex["succes_par_agent"], "acc640_tiree": acc640})
    rec.update({"dose": {k: v for k, v in dose.items() if k != "eval_exhaustive"}, "mur_s": time.time() - t0,
                "cpu_s": time.process_time() - c0, "environnement": _environnement(), "provenance": provenance()})
    p = _chemin_cellule(bras, seed, pas, replique)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(rec, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{_nom(bras, seed, pas, replique)} ({rec['mur_s']:.0f} s mur) -> {p}", flush=True)
    return rec


def measure_tau(succes):
    """τ depuis {(bras, seed): succès sur 576}, UN pas. PURE. d_s = succès(lam09) − succès(lam0), en pas, par seed tenue
    à l'écart où les DEUX bras sont présents. Rend la moyenne, l'écart-type (ddof 1) = τ, le compte des d_s > MARGE_PAS,
    et les cellules manquantes. Moins de 2 seeds complètes : τ None (jamais 0 fabriqué) ; une seed du verdict : REFUS."""
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


def measure_dispersion_dose(ratios, bande=GARDE_DOSE):
    """Dispersion du rapport appliqué/contrefactuel de la garde de dose du sham, {seed: rapport}. PURE. Rend n, min, max,
    médiane, écart-type (ddof 1), et le compte HORS bande (bornes incluses = dans la bande). Un rapport None (chemin
    contrefactuel nul) est COMPTÉ à part, jamais remplacé ; moins de 2 rapports : écart-type None."""
    vals = {sd: r for sd, r in ratios.items() if r is not None}
    for sd in ratios:
        _refus("sham_dose", sd)
    x = sorted(vals.values())
    out = {"n": len(x), "indefinis": sorted(sd for sd, r in ratios.items() if r is None), "bande": list(bande),
           "par_seed": {str(sd): vals[sd] for sd in sorted(vals)}}
    if not x:
        return dict(out, min=None, max=None, mediane=None, ecart_type=None, hors_bande=None)
    return dict(out, min=x[0], max=x[-1], mediane=statistics.median(x),
                ecart_type=statistics.stdev(x) if len(x) >= 2 else None,
                hors_bande=sum(1 for r in x if not (bande[0] <= r <= bande[1])))


def measure_noop_identite(succes, graine=4190, B=2000):
    """No-op de f̂ (sham IDENTITÉ, f = 1 attendu), {(bras, seed): succès} pour lam0, lam09 et sham_identite au MÊME
    pas. PURE. Rend l'écart sham_identite − lam09 par seed (en pas : le bruit d'un no-op que le bit ne garantit pas), et
    f̂ = Σe/Σd avec son IC90 bootstrap (la fonction de lecture de R3, seuil 0). Seeds incomplètes : ignorées et nommées."""
    from tools.td_step_pilot_r3 import f_hat
    complets = sorted(sd for sd in SEEDS_TENUES
                      if all((b, sd) in succes for b in ("lam0", "lam09", "sham_identite")))
    for (b, sd) in succes:
        _refus(b, sd)
    ecart = [int(succes[("sham_identite", sd)]) - int(succes[("lam09", sd)]) for sd in complets]
    d = [int(succes[("lam09", sd)]) - int(succes[("lam0", sd)]) for sd in complets]
    e = [int(succes[("sham_identite", sd)]) - int(succes[("lam0", sd)]) for sd in complets]
    out = {"seeds_completes": complets, "ecart_identite_moins_trace_pas": ecart,
           "ecart_max_abs_pas": max((abs(v) for v in ecart), default=None),
           "ecart_type_pas": statistics.stdev(ecart) if len(ecart) >= 2 else None,
           "identiques_au_bit": sum(1 for v in ecart if v == 0)}
    out["f_hat"] = f_hat(d, e, 0, B, graine) if complets else None
    return out


def measure_replication(paires):
    """Déterminisme par seed : [(cellule originale, réplique)] -> par paire, l'égalité AU BIT des succès, des succès par
    agent, de l'accuracy tirée et du net total. PURE. Rend le compte des paires identiques et le détail."""
    detail = []
    for a, b in paires:
        champs = {"succes": a.get("succes") == b.get("succes"),
                  "succes_par_agent": a.get("succes_par_agent") == b.get("succes_par_agent"),
                  "acc640_tiree": a.get("acc640_tiree") == b.get("acc640_tiree"),
                  "net_total": ((a.get("dose") or {}).get("dose_instrument") or {}).get("net_total")
                  == ((b.get("dose") or {}).get("dose_instrument") or {}).get("net_total")}
        detail.append({"cellule": f"{a.get('bras')}|seed={a.get('seed')}|pas={a.get('pas_cle', 'p1')}",
                       "identique_au_bit": all(champs.values()), "champs": champs})
    return {"paires": len(detail), "identiques": sum(1 for x in detail if x["identique_au_bit"]), "detail": detail}


def _manifestes(deport):
    """{(bras, pas, seed, réplique): résumé du MANIFEST du Job qui a produit la cellule} -- image par son DIGEST
    seulement (dépôt public : l'adresse du registre ne sort jamais)."""
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
            pas = cmd[cmd.index("--pas") + 1] if "--pas" in cmd else "p1"
            rep = int(cmd[cmd.index("--replique") + 1]) if "--replique" in cmd else 0
        except (ValueError, IndexError):
            continue
        img = m.get("image") or ""
        dig = re.search(r"@(sha256:[0-9a-f]{64})", img)
        cpu = m.get("cpu") or {}
        out[(bras, pas, seed, rep)] = {"job": m.get("job"), "lieu": m.get("lieu"), "sha": m.get("sha"),
                                       "returncode": m.get("returncode"),
                                       "image_digest": dig.group(1) if dig else None,
                                       "limite_cpu": cpu.get("limite_cpu"), "threads_poses": cpu.get("threads_poses"),
                                       "threads_source": cpu.get("threads_source"),
                                       "duree_mur_s": m.get("duree_mur_s")}
    return out


def _cle_cellule(b, pas, sd, rep):
    """Clé publiée : celle des 24 cellules de τ (« bras|seed=S ») est INCHANGÉE."""
    k = f"{b}|seed={sd}" if pas == "p1" else f"{b}|pas={pas}|seed={sd}"
    return k + (f"|rep={rep}" if rep else "")


def agreger(deport=os.path.join("runs", "deport")):
    """Relit les cellules, refuse des LIEUX mêlés, calcule τ (par pas), la dispersion de la garde de dose, le no-op de
    f̂ et le déterminisme ; publie results/td_step_pilot_r3_tau.json (suivi). Aucune simulation."""
    cellules = {}
    for p in sorted(glob.glob(os.path.join(str(results_file(DOSSIER)), "*_seed*.json"))):
        r = json.load(open(p, encoding="utf-8"))
        pas = r.get("pas_cle") or ("p1" if abs(float(r.get("pas", PAS)) - PAS) < 1e-12 else "p2")
        cellules[(r["bras"], pas, int(r["seed"]), int(r.get("replique", 0)))] = r
    lieux = {(r["environnement"]["systeme"].split("-")[0], r["environnement"]["torch"]) for r in cellules.values()}
    if len(lieux) > 1:
        raise ValueError(f"lieux mêlés {sorted(lieux)} : torch diffère au dernier bit entre lieux, refus d'agréger")
    man = _manifestes(deport)

    def succes(pas, bras_admis):
        return {(b, sd): r["succes"] for (b, p, sd, rep), r in cellules.items()
                if p == pas and rep == 0 and b in bras_admis and "succes" in r}
    tau_par_pas = {p: measure_tau(succes(p, BRAS)) for p in PAS_VALEURS
                   if any(k[1] == p and k[0] in BRAS for k in cellules)}
    disp = {p: measure_dispersion_dose({sd: r["ratio_applique_contrefactuel"] for (b, pp, sd, rep), r in
                                        cellules.items() if b == "sham_dose" and pp == p})
            for p in PAS_VALEURS if any(k[0] == "sham_dose" and k[1] == p for k in cellules)}
    noop = {p: measure_noop_identite(succes(p, ("lam0", "lam09", "sham_identite"))) for p in PAS_VALEURS
            if any(k[0] == "sham_identite" and k[1] == p for k in cellules)}
    paires = [(cellules[(b, p, sd, 0)], r) for (b, p, sd, rep), r in sorted(cellules.items())
              if rep and (b, p, sd, 0) in cellules]
    db = {"objet": __doc__.split("\n\n")[0], "tau": tau_par_pas.get("p1"), "tau_par_pas": tau_par_pas,
          "dispersion_dose_sham": disp, "noop_identite": noop, "replication": measure_replication(paires),
          "lieu": sorted(lieux),
          "dispositif": {"pas": PAS, "pas_valeurs": PAS_VALEURS, "lambda": LAMBDA, "episodes": EPISODES,
                         "n_agents": N_AGENTS, "K": K, "n_grille": N_GRILLE, "bras": sorted(BRAS) + sorted(MODES),
                         "seeds": list(SEEDS_TENUES)},
          "cellules": {_cle_cellule(b, p, sd, rep): {
              "succes": r.get("succes"), "n": r.get("n"), "succes_par_agent": r.get("succes_par_agent"),
              "acc640_tiree": r.get("acc640_tiree"), "mur_s": r["mur_s"], "cpu_s": r["cpu_s"],
              "environnement": r["environnement"], "provenance": r["provenance"],
              "dose_updates": r["dose"].get("updates"),
              **({"ratio_applique_contrefactuel": r["ratio_applique_contrefactuel"]}
                 if "ratio_applique_contrefactuel" in r else {}),
              "manifeste": man.get((b, p, sd, rep))} for (b, p, sd, rep), r in sorted(cellules.items())}}
    # Compatibilité : l'agrégat du 2026-10-13 (24 cellules au pas p1) publiait `dispositif.pas` et `dispositif.bras`
    # sans les modes ; les clés de ses cellules et son bloc `tau` sont INCHANGÉS.
    texte = json.dumps(db, indent=1, ensure_ascii=False)
    if _IP.search(texte):
        raise ValueError("adresse de type IP dans l'agrégat (dépôt public) : refus d'écrire")
    dest = str(results_file("td_step_pilot_r3_tau.json"))
    open(dest, "w", encoding="utf-8").write(texte)
    print(json.dumps({"tau_par_pas": tau_par_pas, "dispersion_dose_sham": disp}, indent=1, ensure_ascii=False),
          "\n->", dest)
    return db


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("cellule")
    c.add_argument("--bras", required=True)
    c.add_argument("--seed", type=int, required=True)
    c.add_argument("--pas", default="p1")
    c.add_argument("--replique", type=int, default=0)
    g = sp.add_parser("agreger")
    g.add_argument("--deport", default=os.path.join("runs", "deport"))
    a = ap.parse_args(argv)
    if a.cmd == "cellule":
        cellule(a.bras, a.seed, pas=a.pas, replique=a.replique)
    else:
        agreger(a.deport)


if __name__ == "__main__":
    main()
