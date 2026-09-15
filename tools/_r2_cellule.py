"""Une cellule de LEGACY-LR-CURVE-R2, isolee dans un sous-processus (bornee par `timeout` a l'appel) : ecrit
`results/legacy_lr_curve_r2.json`[cle] et s'arrete. Usage : python tools/_r2_cellule.py <lr> <seed>
Pourquoi : la cellule lr=0,001 seed 2036 a tourne > 3 h (1,7 Go) la ou ses soeurs prenaient 2-3 min -- E13 :
un cout non borne DANS le design ; ici la borne est le timeout du sous-processus, et le depassement est PUBLIE
comme cellule non mesuree (raison 'depassement de cout'), jamais avale."""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file
from tools.cognitive_demand_inworld import run_learner_probe
from tools.preregister import stamp

lr, seed = float(sys.argv[1]), int(sys.argv[2])
out_path = str(results_file("legacy_lr_curve_r2.json"))
db = json.load(open(out_path, encoding="utf-8"))
k = f"lr={lr}|seed={seed}"
t0 = time.time()
try:
    r = run_learner_probe(seed=seed, num_agents=12, ticks=2000, block=400, policy="legacy", lr=lr)
except ValueError as exc:
    r = {"policy": "legacy", "seed": seed, "lr": lr, "erreur": str(exc), "hit_first": None, "hit_last": None,
         "blocks": [], "learning": None}
r["elapsed_s"] = time.time() - t0
db = json.load(open(out_path, encoding="utf-8"))          # relu : un autre processus a pu ecrire
db[k] = r
json.dump(stamp(db, "LEGACY-LR-CURVE-R2"), open(out_path, "w", encoding="utf-8"), indent=1)
print(k, "->", r.get("hit_last"), "resur", r.get("resurrections"), f"{r['elapsed_s']:.0f}s")
