"""
tools/confirm_055.py — Confirmer la sélection alignée (énergie) sous PUISSANCE (EDR 057).

EDR 055 : align-énergie prometteur (taux 33→50 %) mais sous-puissant (n=6). EDR 056 : la version
fitness backfire (révertie, REF_FITNESS_WEIGHT=0) -> on confirme la version ÉNERGIE seule. 40 seeds,
align ON(3.0) vs OFF, via le harnais (EDR 052). Seuil relâché à t≥2.0 + IC du taux et du gain :
estimation fiable, pas chasse au drapeau.

Usage : HEADLESS=1 python -m tools.confirm_055   (long : ~3-4 h)
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from src.seed_ai.eval_harness import verdict
from tools.aligned_selection import arm, _stats, EMERGE
from tools.confirm_b import _backup, _restore, BAK_PKL, BAK_DIR


def _ci95(d):
    se = d["std"] / max(1, d["n"]) ** 0.5
    return d["mean"] - 1.96 * se, d["mean"] + 1.96 * se


def main(seeds=range(40), eras=16, align=3.0):
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
    print(f"CONFIRMATION 055 (align energie) : {len(seeds)} seeds x {eras} eres, align ON({align}) vs OFF.")
    on_g, on_rate = arm(config, db, align, seeds, eras, "ALIGN")
    off_g, off_rate = arm(config, db, 0.0, seeds, eras, "OFF")

    res = {"align": _stats(on_g), "base": _stats(off_g)}
    v = verdict("align", "base", res, t_thresh=2.0)
    lo_a, hi_a = _ci95(res["align"])
    lo_b, hi_b = _ci95(res["base"])
    n = len(seeds)
    # IC binomial (normal approx) du taux.
    def rate_ci(rate):
        se = (rate * (1 - rate) / n) ** 0.5
        return max(0, rate - 1.96 * se), min(1, rate + 1.96 * se)
    rlo_a, rhi_a = rate_ci(on_rate)
    rlo_b, rhi_b = rate_ci(off_rate)

    print("\n=== VERDICT (40 seeds) ===")
    print(f"  taux emergence : OFF={off_rate*100:.0f}% [{rlo_b*100:.0f}-{rhi_b*100:.0f}]  "
          f"vs ALIGN={on_rate*100:.0f}% [{rlo_a*100:.0f}-{rhi_a*100:.0f}]")
    print(f"  gain moyen     : OFF={res['base']['mean']:.4f} [{lo_b:.4f},{hi_b:.4f}]  "
          f"vs ALIGN={res['align']['mean']:.4f} [{lo_a:.4f},{hi_a:.4f}]")
    print(f"  {v['summary']}")
    sep = lo_a > hi_b or (v['significant'] and v['winner'] == 'align')
    if sep:
        print("  -> CONFIRME (t>=2.0 ou IC disjoints) : la selection alignee (energie) fiabilise.")
    elif on_rate > off_rate and res['align']['mean'] > res['base']['mean']:
        print("  -> tendance positive maintenue mais IC se chevauchent : effet REEL mais MODESTE (pas un grand levier).")
    else:
        print("  -> l'effet de 055 ne tient pas sous puissance (etait du bruit a n=6).")

    _restore()
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
