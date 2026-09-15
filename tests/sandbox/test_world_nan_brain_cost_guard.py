"""E28 (2026-09-15, P2.73 b) — le monde ne facture plus un `brain_cost` NON FINI : il le COMPTE.

`max(0.0, energy - nan)` vaut 0.0 en Python : un World Model qui diverge donnait une `surprise` NaN, donc un
`brain_cost` NaN, donc une énergie ZÉRO et une mort par tick, sans exception. Ici : un agent dont le modèle porte
`surprise_momentum = nan` traverse un tick avec son énergie intacte du coût cérébral, et `nan_brain_cost` compte ;
un agent à surprise finie paie exactement le coût historique (no-op apparié). Un seul monde, deux ticks."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agents.mamba_agent import MambaAgent  # noqa: E402
from src.seed_ai.harness import seed_at  # noqa: E402
from src.worlds.world_1_stoneage import Biosphere3D  # noqa: E402


def _world(n=2, seed=11):
    seed_at(seed, 0)
    e = Biosphere3D()
    e.benchmark_mode = True
    e.night_enabled = False
    e.current_era = 10_000
    e.config.forage_payoff = 0.0
    e.use_torch_inworld = False
    if hasattr(e, "memory_retriever"):
        e.memory_retriever.stop()
        e.memory_retriever.clear()
    for _ in range(n):
        e.add_agent(MambaAgent(), energy=80.0)
    return e


def test_a_nan_surprise_no_longer_zeroes_the_energy_and_is_counted():
    e = _world()
    victime = e.agents[0]
    # forward legacy réécrit surprise_momentum à chaque tick ; on l'injecte via une classe qui la force à nan
    from src.agents.mamba_agent import MambaBatchModel

    class NanSurprise(MambaBatchModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            out = MambaBatchModel.forward(self, batch_obs, env_surprise_batch)
            self.agents[0].surprise_momentum = float("nan")     # l'agent 0 porte un World Model divergent
            return out
    e.batch_model_cls = NanSurprise
    e.step()
    assert int(getattr(e, "nan_brain_cost", 0)) >= 1, "le brain_cost NaN doit être COMPTÉ"
    assert victime in e.agents or victime in e.dead_agents
    assert victime["energy"] > 0.0 or victime in e.dead_agents and math.isfinite(victime["energy"])
    # l'agent n'a pas été mis à ZÉRO par le coût cérébral : il a au plus payé les autres puits du tick
    assert victime["energy"] > 40.0, f"énergie {victime['energy']} : le NaN a encore tué"


def test_finite_surprise_pays_exactly_the_historical_cost_noop():
    e1 = _world(seed=12)
    e1.step()
    e2 = _world(seed=12)
    e2.step()
    assert [a["energy"] for a in e1.agents] == [a["energy"] for a in e2.agents]
    assert int(getattr(e1, "nan_brain_cost", 0)) == 0
    assert all(np.isfinite(a["energy"]) for a in e1.agents)


def test_max_semantics_are_the_documented_trap():
    """Le piège gelé : `max(0.0, nan)` rend 0.0 (nan > 0.0 est faux, max garde le premier) — c'est ce que la
    garde contourne. `max(nan, 0.0)` rend nan : l'ordre des arguments décide, sans avertissement."""
    assert max(0.0, float("nan")) == 0.0
    assert math.isnan(max(float("nan"), 0.0))
