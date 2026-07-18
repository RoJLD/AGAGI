"""S2-009 — Réalise la recette S2-006 IN-WORLD (flag cognitive_demand sur stoneage) et prouve via
l'ablation-perception que la survie devient perception-SENSIBLE (oracle) — flip du NEUTRE de S2-003.

Oracle = lecteur-de-signal câblé (décode bit_a/bit_b de l'obs → direction correcte) : preuve DÉCISIVE que
le monde EXIGE la perception (intact survit, ablé s'effondre), indépendamment du crédit. Contraste mode OFF
(doit rester NEUTRE). Réutilise run_condition (seam batch_model_cls) + derange_rows + ablation_verdict.

Usage : python tools/cognitive_demand_inworld.py  (env: CDI_SEED, CDI_K, CDI_AGENTS, CDI_TICKS, CDI_METAB, CDI_COG)
REF-DEMAND-MARKER. NE modifie PAS s2_demand.
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.baseline_models import BaselineBatchModel
from tools.s2_demand_ablation import derange_rows
from tools.demand_marker import ablation_verdict
from tools.s2_demand import run_condition, WORLDS

BIT_A, BIT_B = 12, 13                                  # colonnes du signal dans l'obs (world_1 column_stack)


class CognitiveOracleBatchModel(BaselineBatchModel):
    """Décode le signal (bit_a/bit_b) → logits favorisant la direction correcte dir=2*(a>0)+(b>0)."""

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        a = batch_obs[:, BIT_A] if batch_obs.shape[1] > BIT_A else np.ones(self.B)
        b = batch_obs[:, BIT_B] if batch_obs.shape[1] > BIT_B else np.ones(self.B)
        dirs = (2 * (a > 0) + (b > 0)).astype(int)
        for i in range(self.B):
            logits[i, dirs[i]] = 1.0
        return logits


class CognitiveOracleAblated(CognitiveOracleBatchModel):
    """Oracle recevant l'obs DÉRANGÉE (within-subject) → décode le signal d'un pair → rate."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(derange_rows(batch_obs), env_surprise_batch)


def _median_survival(cond):
    s = cond.get("survival") or []
    return float(np.median(s)) if s else 0.0


def _run_mode(cognitive_demand, seed, K, num_agents, max_ticks, base_metabolism, cog_gain):
    """Configure le régime (via un world_cls partiel) puis oracle intact vs ablé → verdict."""
    from src.worlds.world_1_stoneage import Biosphere3D

    def make_world():
        env = Biosphere3D()
        env.config.cognitive_demand = cognitive_demand
        env.config.cog_gain = cog_gain
        env.config.base_metabolism = base_metabolism
        env.config.forage_payoff = 0.0                # neutralise la chasse (corps insuffisant en ON)
        return env

    intact = run_condition(make_world, CognitiveOracleBatchModel, None, seed,
                           num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    ablated = run_condition(make_world, CognitiveOracleAblated, None, seed,
                            num_agents=num_agents, max_ticks=max_ticks, n_eras=K)
    v = ablation_verdict(intact["era_survival"], ablated["era_survival"])
    verdict = ("PERCEPTION_DEMANDED" if v["collapse"] and v["n"] >= 12
               else "NEUTRAL" if v["decoy"] else "MIXED")
    return {"ratio": v["ratio"], "verdict": verdict, "n": v["n"]}


def run_cog_demand_map(seed=2026, K=12, num_agents=12, max_ticks=200, base_metabolism=4.0, cog_gain=6.0):
    """Oracle intact vs ablé, mode ON vs OFF. ON attendu SENSIBLE (PERCEPTION_DEMANDED), OFF NEUTRE."""
    return {
        "on": _run_mode(True, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
        "off": _run_mode(False, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
    }


def main():
    seed = int(os.environ.get("CDI_SEED", "2026"))
    K = int(os.environ.get("CDI_K", "12"))
    num_agents = int(os.environ.get("CDI_AGENTS", "12"))
    max_ticks = int(os.environ.get("CDI_TICKS", "200"))
    metab = float(os.environ.get("CDI_METAB", "4.0"))
    cog = float(os.environ.get("CDI_COG", "6.0"))
    m = run_cog_demand_map(seed, K, num_agents, max_ticks, metab, cog)
    print(f"\n=== S2-009 — recette cognitive IN-WORLD (oracle, seed={seed}, K={K}, metab={metab}, cog={cog}) ===")
    print(f"{'mode':6s} {'ratio':>7s}  verdict")
    for mode in ("on", "off"):
        r = m[mode]
        print(f"{mode:6s} {r['ratio']:7.2f}  {r['verdict']} (n={r['n']})")
    print("\nAttendu : ON=PERCEPTION_DEMANDED (ratio>>1, le monde exige la perception) / OFF=NEUTRAL "
          "(ratio~1) -> la recette S2-006 flip la survie IN-WORLD. -> Rédiger EDR-S2-009.")
    return m


if __name__ == "__main__":
    main()
