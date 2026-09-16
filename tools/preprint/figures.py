"""Figures du preprint MÉTHODO (P5.1) — TOUT est lu dans des artefacts du dépôt, RIEN n'est écrit en dur.

Règle E8 appliquée à la rédaction : chaque figure vient d'un JSON de résultats cité par un record, d'une sortie de
cliquet ou de l'historique git ; ce script refuse de tracer une série dont la source manque (il la RAPPORTE).
Sorties : `docs/preprint/figures/<nom>.csv` (la donnée, relisible) + `<nom>.png` si matplotlib est présent.

Usage : python tools/preprint/figures.py [--only F3,F5]
"""
import csv
import json
import os
import subprocess
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file  # noqa: E402

OUT_DIR = os.path.join(_ROOT, "docs", "preprint", "figures")


def _load(name):
    p = str(results_file(name))
    if not os.path.exists(p):
        raise FileNotFoundError(f"source ABSENTE : {p} — la figure n'est pas tracée, elle est rapportée")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _csv(name, header, rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, name + ".csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return p


def _plot(name, fn):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:                               # noqa: BLE001 — pas de matplotlib : la CSV suffit
        return None
    fig, ax = plt.subplots(figsize=(6, 3.6))
    fn(ax)
    fig.tight_layout()
    p = os.path.join(OUT_DIR, name + ".png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


# --- F1 : la dette de calibration dans le temps (baseline gelée, par commit) --------------------------------------
def f1_calibration_debt():
    log = subprocess.check_output(["git", "log", "--format=%H %ad", "--date=short", "--reverse", "--",
                                   "tools/instrument_calibration_baseline.json"], cwd=_ROOT, text=True)
    rows = []
    for line in log.strip().splitlines():
        sha, date = line.split()
        blob = subprocess.check_output(["git", "show", f"{sha}:tools/instrument_calibration_baseline.json"],
                                       cwd=_ROOT, text=True, encoding="utf-8")
        d = json.loads(blob)
        n = len(d.get("uncalibrated", d)) if isinstance(d, dict) else len(d)
        rows.append([date, sha[:7], n])
    p = _csv("F1_dette_calibration", ["date", "commit", "instruments_non_calibres_geles"], rows)

    def draw(ax):
        ax.plot([r[0] for r in rows], [r[2] for r in rows], marker="o")
        ax.set_ylabel("dette gelée (instruments)")
        ax.set_title("F1 — dette de calibration gelée, par commit de la baseline")
    return p, _plot("F1_dette_calibration", draw)


# --- F3 : la bascule E19 (verdict fonction du pas) sur trois instruments ------------------------------------------
def f3_e19_step_switch():
    rows = []
    rc = _load("retain_compose_lr_replication.json")
    for k in ("lr_0.02", "lr_0.002"):
        rows.append(["RETAIN-COMPOSE-LR", float(k.split("_")[1]), rc[k]["learned_median"], rc[k]["gap_verdict"], rc[k]["n"]])
    lk = _load("lock001_proxy_r1.json")
    by = {}
    for key, v in lk.items():
        if "|" not in key:
            continue
        parts = dict(kv.split("=") for kv in key.split("|"))
        by.setdefault((float(parts["lr"]), int(parts["ep"])), []).append(v["lang_i"])
    for (lr, ep), vals in sorted(by.items()):
        rows.append([f"LOCK-002 (D=2, {ep} ép.)", lr, float(np.median(vals)), "", len(vals)])
    r2 = _load("legacy_lr_curve_r2.json")
    for lr, v in r2["_lecture"]["par_lr"].items():
        rows.append(["CALIB-LEGACY-LEARNER R2", float(lr), v["mediane_hit_last"], f"{v['seeds_au_dessus']}/12 au-dessus", 12])
    p = _csv("F3_bascule_E19", ["instrument", "lr", "mediane", "verdict_ou_signe", "n"], rows)

    def draw(ax):
        for inst in sorted(set(r[0] for r in rows)):
            pts = sorted((r[1], r[2]) for r in rows if r[0] == inst and r[1] > 0)
            ax.plot([x for x, _ in pts], [y for _, y in pts], marker="o", label=inst)
        ax.set_xscale("log")
        ax.set_xlabel("pas d'apprentissage (log)")
        ax.set_ylabel("médiane de la DV")
        ax.set_title("F3 — le même nul bascule avec le pas (E19)")
        ax.legend(fontsize=7)
    return p, _plot("F3_bascule_E19", draw)


# --- F4 : dose vs nul — six bras de CALIB-LEARNER, taux de coups par bloc --------------------------------------
def f4_dose():
    d = _load("learner_calibration_v2.json")
    rows = []
    for arm, rec in d["arms"].items():
        per = rec["per_seed"]
        nb = max(len(v["blocks"]) for v in per.values())
        for b in range(nb):
            vals = [v["blocks"][b]["hit_rate"] for v in per.values() if len(v["blocks"]) > b]
            tick = next(v["blocks"][b]["tick"] for v in per.values() if len(v["blocks"]) > b)
            rows.append([arm, tick, float(np.median(vals)), len(vals)])
    p = _csv("F4_dose_vs_nul", ["bras", "tick", "hit_rate_mediane", "n_seeds"], rows)

    def draw(ax):
        for arm in d["arms"]:
            pts = [(r[1], r[2]) for r in rows if r[0] == arm]
            ax.plot([x for x, _ in pts], [y for _, y in pts], marker="o", label=arm)
        ax.set_xlabel("tick (dose de crédit non bornée par la mort)")
        ax.set_ylabel("taux de coups (médiane, 12 seeds)")
        ax.set_title("F4 — CALIB-LEARNER : le nul publié était un nul de dose")
        ax.legend(fontsize=7)
    return p, _plot("F4_dose_vs_nul", draw)


# --- F5 : E28 — résurrections et taux de coups avec / sans garde du World Model ---------------------------------
def f5_e28():
    r1 = _load("legacy_lr_curve_r1.json")
    r2 = _load("legacy_lr_curve_r2.json")
    base = _load("legacy_learner_calibration.json")
    rows = []

    def med(cells, key):
        vals = [c[key] for c in cells if c.get("learning") is not None]
        return float(np.median(vals)) if vals else None
    seeds = list(range(2026, 2038))
    for lr, arm in ((0.04, "natural"), (0.004, "lr_low"), (0.0, "lr0_reference")):
        cells = list(base["arms"][arm]["per_seed"].values())
        rows.append(["sans garde (P3.4)", lr, med(cells, "resurrections"), med(cells, "hit_last")])
    for lr in (0.01, 0.001):
        cells = [r1[f"lr={lr}|seed={s}"] for s in seeds]
        rows.append(["sans garde (R1)", lr, med(cells, "resurrections"), med(cells, "hit_last")])
    for lr, v in r2["_lecture"]["par_lr"].items():
        rows.append(["sous garde E28 (R2)", float(lr), v["resurrections"], v["mediane_hit_last"]])
    p = _csv("F5_E28_garde", ["condition", "lr", "resurrections_mediane", "hit_last_mediane"], rows)

    def draw(ax):
        for cond in ("sans garde (P3.4)", "sans garde (R1)", "sous garde E28 (R2)"):
            pts = sorted((r[1], r[2]) for r in rows if r[0] == cond and r[1] > 0)
            ax.plot([x for x, _ in pts], [y for _, y in pts], marker="o", label=cond)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("pas d'apprentissage (log)")
        ax.set_ylabel("résurrections par seed (log)")
        ax.set_title("F5 — E28 : la « létalité » était max(0.0, nan)")
        ax.legend(fontsize=7)
    return p, _plot("F5_E28_garde", draw)


# --- F6 : le cliquet des cliquets — portes × mutations × verdict -------------------------------------------------
def f6_gate_mutation():
    out = subprocess.run([sys.executable, "tools/check_gate_mutation.py", "--report"], cwd=_ROOT,
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env={**os.environ, "PYTHONIOENCODING": "utf-8"}).stdout
    rows, porte = [], None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("porte "):
            porte = s.split("—")[0].strip()
        elif s.startswith("[") and porte:
            verdict = s[1:s.index("]")].strip()
            rows.append([porte, verdict, s[s.index("]") + 1:].strip()])
    if not rows:
        raise RuntimeError("rapport de check_gate_mutation illisible : figure NON tracée")
    p = _csv("F6_cliquet_des_cliquets", ["porte", "verdict", "mutation"], rows)

    def draw(ax):
        portes = sorted(set(r[0] for r in rows), key=lambda x: int(x.split()[1]))
        tuees = [sum(1 for r in rows if r[0] == q and r[1] == "TUEE") for q in portes]
        surv = [sum(1 for r in rows if r[0] == q and r[1] != "TUEE") for q in portes]
        ax.bar(portes, tuees, label="mutant TUÉ")
        ax.bar(portes, surv, bottom=tuees, label="autre")
        ax.set_title("F6 — chaque porte du hook, cassée d'une ligne en mémoire")
        ax.tick_params(axis="x", labelsize=6, rotation=90)
        ax.legend(fontsize=7)
    return p, _plot("F6_cliquet_des_cliquets", draw)


# --- F2 : le registre des erreurs — occurrences DATÉES par classe (le biais a une direction et une fréquence) -------
def f2_error_register():
    import re
    reg = os.path.join(_ROOT, "docs", "REF", "REGISTRE_ERREURS.md")
    with open(reg, encoding="utf-8") as fh:
        txt = fh.read()
    rows = []
    for line in txt.splitlines():
        if not line.startswith("| **E"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if len(cells) < 5:
            continue
        classe = cells[0].strip("* ")
        titre = re.sub(r"\*\*", "", cells[1])[:70]
        dates = sorted(set(re.findall(r"2026-\d{2}-\d{2}", cells[2])))
        rows.append([classe, titre, len(dates), dates[0] if dates else "", dates[-1] if dates else "", cells[3]])
    rows.sort(key=lambda r: int(r[0][1:]))
    p = _csv("F2_registre_erreurs", ["classe", "titre", "dates_distinctes", "premiere", "derniere", "garde"], rows)

    def draw(ax):
        ax.barh([r[0] for r in rows], [r[2] for r in rows])
        ax.set_xlabel("jours distincts où la classe a été VUE (registre)")
        ax.set_title("F2 — 28 classes d'erreur, occurrences datées")
        ax.tick_params(axis="y", labelsize=6)
        ax.invert_yaxis()
    return p, _plot("F2_registre_erreurs", draw)


# --- F7 : le plancher de bruit du marqueur de demande vs les contrastes publiés ------------------------------------
def f7_noise_floor():
    import glob
    import re
    d = _load("s2_blind_champion.json")
    rows = [[r["seed"], "intact", r["intact"]["within_ratio"]] for r in d["rows"]]
    rows += [[r["seed"], "aveugle", r["blind"]["within_ratio"]] for r in d["rows"]]
    # la bande du NO-OP exact vit dans le record (mesure du 2026-09-08, prose tabulée) : lue, pas recopiée
    rec = glob.glob(os.path.join(_ROOT, "docs", "EDR", "S2-BLIND-CHAMPION_*.md"))
    if not rec:
        raise FileNotFoundError("record S2-BLIND-CHAMPION absent : la bande du no-op n'est pas tracée")
    txt = open(rec[0], encoding="utf-8").read()
    m = re.findall(r"\| champion(?: aveuglé)? \| \*\*([0-9],[0-9]+)\*\* \|", txt)
    if len(m) < 2:
        raise FileNotFoundError("tableau du no-op introuvable dans S2-BLIND-CHAMPION : bande non tracée")
    band = sorted(float(x.replace(",", ".")) for x in m[:2])
    for b, lab in zip(band, ("noop_bas", "noop_haut")):
        rows.append(["record", lab, b])
    p = _csv("F7_plancher_de_bruit", ["seed", "sujet", "within_ratio"], rows)

    def draw(ax):
        for sujet, mk in (("intact", "o"), ("aveugle", "s")):
            pts = [(str(r[0]), r[2]) for r in rows if r[1] == sujet]
            ax.plot([x for x, _ in pts], [y for _, y in pts], mk, label=f"champion {sujet}")
        ax.axhspan(band[0], band[1], alpha=0.2, label=f"bande du no-op exact [{band[0]:.3f} ; {band[1]:.3f}]")
        ax.axhline(1.0, color="k", lw=0.5)
        ax.set_ylabel("within_ratio (intact / ablaté)")
        ax.set_xlabel("seed")
        ax.set_title("F7 — le marqueur de demande et son plancher de bruit")
        ax.legend(fontsize=7)
    return p, _plot("F7_plancher_de_bruit", draw)


FIGURES = {"F1": f1_calibration_debt, "F2": f2_error_register, "F3": f3_e19_step_switch, "F4": f4_dose,
           "F5": f5_e28, "F6": f6_gate_mutation, "F7": f7_noise_floor}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else list(FIGURES)
    for name in only:
        try:
            paths = FIGURES[name]()
            print(name, "->", paths)
        except FileNotFoundError as exc:
            print(name, "NON TRACÉE :", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
