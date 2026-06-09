"""
tools/retention_map.py — Carte de rétention / oubli catastrophique (EDR 009 §2).

Lance un curriculum (qui snapshotte le champion de chaque monde dans KuzuDB),
puis re-teste chaque champion sur tous les mondes antérieurs pour mesurer ce
qu'il a oublié en poussant plus loin.

    forgetting_i > 0 : oubli (à corriger : périodes critiques / rehearsal / progressif)
    forgetting_i ~ 0 : rétention parfaite
    forgetting_i < 0 : transfert rétrograde (apprendre plus loin a aidé ce monde)

⚠️ Coût : curriculum complet + K(K+1)/2 sondes (une ère chacune). Stochastique.

Usage :
    python -m tools.retention_map --ladder stoneage agricultural industrial --repeats 1
"""
import argparse
import json
import os

import numpy as np

from src.curriculum.runner import GraduationConfig
from src.curriculum.retention import summarize_retention
from src.graph_rag.async_logger import logger as async_logger
from src.environments.config import WorldConfig
from main_curriculum import run_curriculum, make_run_era_fn, _acquire_shared_db


def _print_matrix(summary):
    ladder = summary["ladder"]
    R = summary["matrix"]
    width = max(len(w) for w in ladder) + 2
    header = " " * width + "".join(f"{w[:8]:>10}" for w in ladder)
    print("\nMatrice de rétention  R[testé][stade] :")
    print(header)
    for i, w in enumerate(ladder):
        cells = "".join(
            (f"{R[i][j]:>10.3f}" if R[i][j] is not None else f"{'·':>10}")
            for j in range(len(ladder))
        )
        print(f"{w:<{width}}{cells}")


def run_retention_map(ladder, keep_memory=False, num_agents=60, max_ticks=400,
                      grad_cfg=None):
    grad_cfg = grad_cfg or GraduationConfig()

    async_logger.start()
    try:
        shared_db = _acquire_shared_db()
        if shared_db is None:
            print("KuzuDB indisponible — abandon.")
            return None

        # 1) Curriculum : produit (et snapshotte) un champion par monde.
        transcript = run_curriculum(
            ladder, keep_memory=keep_memory, grad_cfg=grad_cfg,
            num_agents=num_agents, max_ticks=max_ticks, manage_logger=False,
        )
        if not transcript:
            return None

        ladder_actual = [row["world"] for row in transcript]
        champions = [row["champion_promoted"] for row in transcript]

        # 2) Sondes de rétention sur tous les mondes antérieurs.
        run_era_fn = make_run_era_fn(shared_db, WorldConfig(),
                                     num_agents=num_agents, max_ticks=max_ticks)
        summary = summarize_retention(run_era_fn, ladder_actual, champions, keep_memory)
    finally:
        async_logger.stop()

    _print_matrix(summary)
    print("\nOubli par monde :")
    for w, s in summary["forgetting"].items():
        tag = "oubli" if s["forgetting"] > 0.02 else "rétention" if abs(s["forgetting"]) <= 0.02 else "transfert rétrograde"
        print(f"  {w:<14} maîtrise={s['mastery']:.3f} -> finale={s['final']:.3f} "
              f"| oubli={s['forgetting']:+.3f} (ratio {s['retention_ratio']:.2f}) [{tag}]")
    print(f"\nOubli moyen : {summary['mean_forgetting']:+.3f}")

    os.makedirs("results", exist_ok=True)
    out = "results/retention_map.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Carte ecrite dans {out}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Carte de rétention (EDR 009 §2).")
    ap.add_argument("--ladder", nargs="+",
                    default=["stoneage", "agricultural", "industrial"])
    ap.add_argument("--keep-memory", action="store_true")
    ap.add_argument("--num-agents", type=int, default=60)
    ap.add_argument("--max-ticks", type=int, default=400)
    args = ap.parse_args()
    run_retention_map(
        args.ladder, keep_memory=args.keep_memory,
        num_agents=args.num_agents, max_ticks=args.max_ticks,
    )
