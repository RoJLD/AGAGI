"""
tools/strong_align.py — Lever FORT : sélection alignée énergie + fitness/propagation (EDR 056).

EDR 055 : la distinction primée en ÉNERGIE (survie+apprentissage) -> tendance bonne mais non
confirmée. EDR 054 : ce qui se PROPAGE (le HoF) restait classé par life_score, aveugle au langage.
Lever fort (EDR 056) : la distinction entre AUSSI dans la fitness (calculate_life_score) -> le HoF
propage les communicants. Énergie + fitness alignées -> effet visé LARGE (résolvable à faible n).

Étape 1 : jauger à 8 seeds si l'effet est franc. Si oui -> confirmer à ~40 seeds (étape 2).

Usage : HEADLESS=1 python -m tools.strong_align
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import verdict
from tools.aligned_selection import arm, _stats
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def main(seeds=range(8), eras=16, align=5.0):
    async_logger.start()
    db = None
    for _ in range(50):
        db = async_logger.get_db()
        if db:
            break
        time.sleep(0.1)
    if db is None:
        print("KuzuDB indisponible.")
        return
    config = WorldConfig()
    seeds = list(seeds)

    _backup()
    print(f"LEVER FORT (energie + fitness/propagation) : align ON({align}) vs OFF. {len(seeds)} seeds x {eras} eres.")
    on_g, on_rate = arm(config, db, align, seeds, eras, "FORT")
    off_g, off_rate = arm(config, db, 0.0, seeds, eras, "OFF")

    res = {"fort": _stats(on_g), "base": _stats(off_g)}
    v = verdict("fort", "base", res)
    print("\n=== VERDICT (etape 1, jauge) ===")
    print(f"  taux d'emergence : OFF={off_rate*100:.0f}%  vs  FORT={on_rate*100:.0f}%")
    print(f"  {v['summary']}")
    big = on_rate >= off_rate + 0.34 or (v["significant"] and v["winner"] == "fort")
    if big:
        print("  -> effet FRANC : le lever fort fiabilise. Confirmer a ~40 seeds (etape 2).")
    else:
        print("  -> effet non franc a 8 seeds : soit faible, soit a confirmer en puissance.")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
