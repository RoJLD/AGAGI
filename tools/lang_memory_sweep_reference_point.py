"""Balayage POINT-REFERENCE de la sonde language->memory A NIVEAU (gap S1, cartographie 2026-09-02,
prealable a P2.14b). EXPLORATOIRE : aucun verdict d'arete -- cherche le point (lr, episodes) ou le
bras de REFERENCE (LANG intact, bilineaire, credit REINFORCE) APPREND. Re-mesurer l'arete avant ce
point = regraver du bruit E3 (les 2 negatifs precedents : la reference meurt aussi).

RESUMABLE : resultats persistes dans results/lang_memory_sweep.json, cellule(seed) deja faite =
sautee. Chaque invocation travaille au plus SLICE_S secondes (defaut 520 -- sous le cap Bash de
600 s) puis sort en listant ce qui reste : relancer jusqu'a RESTE=0. Toute troncature est LISTEE.

    PYTHONPATH=. python -u tools/lang_memory_sweep_reference_point.py
"""
import json
import os
import sys
import time

sys.path.insert(0, '.')
import numpy as np
import torch

torch.set_num_threads(1)
from tools.experiment_preflight import declare_design
from tools.language_memory_demand_probe import _train_and_eval

SLICE_S = float(os.environ.get("SWEEP_SLICE_S", "520"))
OUT = os.path.join("results", "lang_memory_sweep.json")
SEEDS = (0, 1, 2)
K, N_AGENTS = 6, 16
# (lr, episodes, D) ordonnes par promesse ; D=0 = tache de l'ancre 0.923 ; D=2 seulement au point gagnant
CELLULES = [(0.002, 3600, 0), (0.002, 1200, 0), (0.02, 1200, 0), (0.02, 3600, 0)]

design = declare_design(
    question="A quel point (lr, episodes) le bras LANG intact (bilineaire, REINFORCE) apprend-il "
             "(q+key)%K a D=0 ?",
    replication_unit="seed", n_independent=len(SEEDS),
    links={"lr_episodes->apprentissage_reference": "measured"},
    cost_estimate="tranches <= 520 s, total grille ~30 min")
print("DESIGN:", design["replication_unit"], f"n={design['n_independent']} (EXPLORATOIRE, resumable)")

os.makedirs("results", exist_ok=True)
db = {}
if os.path.exists(OUT):
    db = json.load(open(OUT, encoding="utf-8"))

def cle(lr, ep, d, s):
    return f"lr={lr:g}|ep={ep}|D={d}|seed={s}"

t0, reste = time.time(), []
for lr, ep, d in CELLULES:
    for s in SEEDS:
        k = cle(lr, ep, d, s)
        if k in db:
            continue
        if time.time() - t0 > SLICE_S:
            reste.append(k)
            continue
        li, la, ci, ca = _train_and_eval(seed=s, episodes=ep, n_agents=N_AGENTS, K=K, D=d,
                                         lr=lr, memory_mode="learned",
                                         control_mode="feedforward", bilinear=True)
        db[k] = {"lang_i": li, "lang_a": la, "ctrl_i": ci, "ctrl_a": ca}
        json.dump(db, open(OUT, "w", encoding="utf-8"), indent=1)
        print(f"  {k}: lang_i={li:.3f} lang_a={la:.3f} ctrl_i={ci:.3f} ctrl_a={ca:.3f} "
              f"[{time.time()-t0:.0f}s]")

print(f"\n=== ETAT (chance={1/K:.3f}) ===")
meilleur, best_med = None, -1.0
for lr, ep, d in CELLULES:
    accs = [db[cle(lr, ep, d, s)]["lang_i"] for s in SEEDS if cle(lr, ep, d, s) in db]
    if len(accs) == len(SEEDS):
        med = float(np.median(accs))
        print(f"  lr={lr:g} ep={ep} D={d}: median lang_intact={med:.3f}  {['%.2f' % a for a in accs]}")
        if med > best_med:
            best_med, meilleur = med, (lr, ep, d)
    elif accs:
        print(f"  lr={lr:g} ep={ep} D={d}: PARTIEL {len(accs)}/{len(SEEDS)}")
print(f"RESTE={len(reste)}", reste if reste else "(grille complete)")

if not reste and meilleur is not None:
    if best_med >= 0.5:
        lr, ep, _ = meilleur
        fait = [cle(lr, ep, 2, s) in db for s in SEEDS]
        if not all(fait):
            print(f"\nreference APPREND (med={best_med:.3f}) -> relancer pour le spot-check D=2 "
                  f"(cellule ({lr:g},{ep},2) ajoutee au travail)")
            for s in SEEDS:
                k = cle(lr, ep, 2, s)
                if k in db or time.time() - t0 > SLICE_S:
                    continue
                li, la, ci, ca = _train_and_eval(seed=s, episodes=ep, n_agents=N_AGENTS, K=K, D=2,
                                                 lr=lr, memory_mode="learned",
                                                 control_mode="feedforward", bilinear=True)
                db[k] = {"lang_i": li, "lang_a": la, "ctrl_i": ci, "ctrl_a": ca}
                json.dump(db, open(OUT, "w", encoding="utf-8"), indent=1)
                print(f"  {k}: lang_i={li:.3f} lang_a={la:.3f} ctrl_i={ci:.3f} ctrl_a={ca:.3f}")
    else:
        print(f"\nAUCUN point d'apprentissage dans la grille (meilleur {best_med:.3f}). Options "
              "ordonnees : episodes plus longs / curriculum / amorcage supervise (warm-start, loi "
              "transversale). NE PAS mesurer l'arete dans cet etat (S1 non etabli).")
