"""tools/s2_cognition_body.py — S2 : Cognition ou Corps ?

Décompose l'edge de survie 4x du champion HoF via un 2x2 GÉNOME × POLITIQUE. La perception ayant été
écartée (S2-ablation : le champion survit sans que la perception soit causale), on tranche : la survie
vient-elle de la COGNITION (politique/ce que l'agent FAIT) ou du CORPS (génome/métabolisme/ce que l'agent
EST) ? La seule cellule nouvelle = `champion_body` (génome champion + actions RANDOM). Additif, réutilise
`run_condition` de s2_demand ; ne modifie pas CONDITIONS. RAG-off. Usage : python -m tools.s2_cognition_body
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.baseline_models import RandomActionBatchModel
from src.seed_ai.harness import Harness
from src.seed_ai.s2_stats import verdict_cognition_body, holm
from tools.s2_demand import run_condition, load_champion_genome, WORLDS

# 2x2 GÉNOME × POLITIQUE. (batch_model_cls, fresh_genome) :
#  champion       = génome champion + moteur normal (Mamba)          -> réel (~4x)
#  champion_body  = génome champion + actions RANDOM                 -> le CORPS seul (politique détruite)
#  random_genome  = génome frais    + moteur normal (Mamba)          -> politique sur corps random
#  random_action  = génome frais    + actions RANDOM                 -> floor
CELLS = {
    "champion":      {"batch_model_cls": None,                   "fresh_genome": False},
    "champion_body": {"batch_model_cls": RandomActionBatchModel, "fresh_genome": False},
    "random_genome": {"batch_model_cls": None,                   "fresh_genome": True},
    "random_action": {"batch_model_cls": RandomActionBatchModel, "fresh_genome": True},
}


def cognition_body_study(worlds=None, seed=2026, K=12, num_agents=20, max_ticks=200,
                         run_fn=None, champion_genome=None):
    """Déroule les 4 cellules du 2x2 par monde et rend `verdict_cognition_body`. run_fn/champion_genome
    injectables (tests). Holm sur les p de l'effet POLITIQUE (famille des mondes). RAG-off = appelant."""
    run_fn = run_fn or run_condition
    worlds = worlds or list(WORLDS)
    champion = champion_genome if champion_genome is not None else load_champion_genome()
    report = {"seed": seed, "K": K, "worlds": {}}
    with Harness(seed=seed, name="s2_cogbody", with_db=False):
        for w in worlds:
            wcls = WORLDS[w]
            conds = {}
            for name, spec in CELLS.items():
                genome = None if spec["fresh_genome"] else champion
                conds[name] = run_fn(wcls, spec["batch_model_cls"], genome, seed,
                                     num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
            v = verdict_cognition_body(conds["champion"], conds["champion_body"],
                                       conds["random_genome"], conds["random_action"])
            v["survivals"] = {k: (float(np.median(conds[k]["survival"])) if conds[k]["survival"] else 0.0)
                              for k in CELLS}
            report["worlds"][w] = v
    decided = [w for w in worlds if report["worlds"][w].get("policy_cmp")]
    if decided:
        adj = holm([report["worlds"][w]["policy_cmp"]["p"] for w in decided])
        for w, pa in zip(decided, adj):
            report["worlds"][w]["policy_p_holm"] = float(pa)
    _report_cogbody(report)
    return report


def _report_cogbody(report):
    print("\n=== S2 — Cognition ou Corps ? 2x2 GÉNOME × POLITIQUE (seed=%s, K=%s) ===" % (report["seed"], report["K"]))
    for w, v in report["worlds"].items():
        s = v["survivals"]
        pc, bc, ic = v["policy_cmp"], v["body_cmp"], v["inter_cmp"]
        print("  %-12s : %-9s | survies champ=%.1f champ_body=%.1f rnd_genome=%.1f rnd_action=%.1f"
              % (w, v["verdict"], s["champion"], s["champion_body"], s["random_genome"], s["random_action"]))
        print("      politique (champ vs champ_body): Cliff d=%+.2f p=%.4f | corps (champ_body vs random): Cliff d=%+.2f p=%.4f"
              " | interaction (rnd_genome vs random): Cliff d=%+.2f"
              % (pc["cliff"], v.get("policy_p_holm", pc["p"]), bc["cliff"], bc["p"], ic["cliff"]))
    print("  -> COGNITION = la survie vient du FAIRE (politique) ; BODY = de l'ÊTRE (corps/génome).")


if __name__ == "__main__":
    from tools.lethality_curriculum import _disable_kuzu
    _disable_kuzu()
    cognition_body_study()
