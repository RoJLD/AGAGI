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
from tools.s2_demand import run_condition

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
    verdict = {"X_DEMANDED": "PERCEPTION_DEMANDED",
               "X_DECOY": "NEUTRAL",
               "INCONCLUSIVE": "INCONCLUSIVE"}[v["verdict"]]
    return {"ratio": v["ratio"], "verdict": verdict, "n": v["n"]}


def run_cog_demand_map(seed=2026, K=12, num_agents=12, max_ticks=200, base_metabolism=4.0, cog_gain=6.0):
    """Oracle intact vs ablé, mode ON vs OFF. ON attendu SENSIBLE (PERCEPTION_DEMANDED), OFF NEUTRE."""
    return {
        "on": _run_mode(True, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
        "off": _run_mode(False, seed, K, num_agents, max_ticks, base_metabolism, cog_gain),
    }


def run_credit_probe(seed=2026, eras=6, num_agents=12, max_ticks=200, base_metabolism=0.75, cog_gain=12.0):
    """Sonde crédit intra-vie (Task 4) : une cohorte FRAÎCHE use_torch_inworld (REINFORCE) apprend-elle la
    nourriture cognitive ? Le monde EXIGE la perception (oracle : survie 200 vs plancher ~7). Si le crédit
    apprend, la survie médiane MONTE sur les ères ; sinon elle reste au plancher (= verrou = crédit, pas le
    monde). Renvoie la liste des survies médianes par ère. Prérequis : corps insuffisant structurel (ver/
    trésor/alignment gatés en cognitive_demand). Borné (à froid, sans warm-start/curriculum)."""
    import numpy as np
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent

    trend = []
    for era in range(eras):
        seed_at(seed, era)
        e = Biosphere3D()
        e.benchmark_mode = True
        e.night_enabled = False
        e.current_era = 10_000
        e.config.cognitive_demand = True
        e.config.cog_gain = cog_gain
        e.config.base_metabolism = base_metabolism
        e.config.forage_payoff = 0.0
        e.use_torch_inworld = True
        for _ in range(num_agents):
            e.add_agent(MambaAgent(), energy=80.0)
        t = 0
        while e.agents and t < max_ticks:
            e.step()
            t += 1
        ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
        trend.append(float(np.median(ages)) if ages else 0.0)
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    return trend


CURRICULUM_COG = [(0.75, 40.0), (0.75, 28.0), (0.75, 20.0), (0.75, 16.0), (0.75, 12.0), (0.75, 12.0)]
CURRICULUM_METAB = [(0.25, 12.0), (0.35, 12.0), (0.5, 12.0), (0.65, 12.0), (0.75, 12.0), (0.75, 12.0)]


def run_warmstart_credit_probe(seed=2026, num_agents=12, max_ticks=200, schedule=None, floor=7.0):
    """Suite naturelle (warm-start/curriculum du credit-probe). Le probe FROID (run_credit_probe) montre que
    le crédit in-world n'apprend pas la nourriture cognitive à froid (survie plate ~7). Catch-22 du
    bootstrap : régime dur = meurt avant d'apprendre ; régime facile = pas de pression. Curriculum : UNE
    cohorte PERSISTÉE (mêmes MambaAgent → genome.W accumule l'apprentissage, world_1 sync) traverse un
    `schedule` de (base_metabolism, cog_gain) allant du FACILE au DUR. Si à l'étape finale (dure) la survie
    TIENT (≫ floor) → le curriculum a franchi le bootstrap (loi warm-start). CURRICULUM_COG = cog annelé
    haut→normal (metab dur fixe) ; CURRICULUM_METAB = metab facile→dur (cog fixe). Renvoie survie médiane
    par étape + flag learned."""
    import numpy as np
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent

    schedule = schedule if schedule is not None else CURRICULUM_COG
    agents = [MambaAgent() for _ in range(num_agents)]     # cohorte PERSISTÉE (genome.W accumule)
    trend = []
    for stage, (metab, cog) in enumerate(schedule):
        seed_at(seed, stage)
        e = Biosphere3D()
        e.benchmark_mode = True
        e.night_enabled = False
        e.current_era = 10_000
        e.config.cognitive_demand = True
        e.config.cog_gain = cog
        e.config.base_metabolism = metab
        e.config.forage_payoff = 0.0
        e.use_torch_inworld = True
        for a in agents:
            e.add_agent(a, energy=80.0)                    # réutilise les objets → genome.W persiste
        t = 0
        while e.agents and t < max_ticks:
            e.step()
            t += 1
        ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
        trend.append((metab, cog, float(np.median(ages)) if ages else 0.0))
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    final = trend[-1][2]
    return {"trend": trend, "final": final, "learned": final >= 4 * floor}   # 4× plancher = franchi


class LinearCognitiveOracle(BaselineBatchModel):
    """Oracle du signal LINÉAIRE 1-bit (S2-011) : dir = int(bit_a>0) ∈ {0,1} (col 12 de l'obs)."""

    def _logits(self, batch_obs):
        logits = np.zeros((self.B, self.O), dtype=np.float32)
        a = batch_obs[:, BIT_A] if batch_obs.shape[1] > BIT_A else np.ones(self.B)
        dirs = (a > 0).astype(int)                         # {0,1}
        for i in range(self.B):
            logits[i, dirs[i]] = 1.0
        return logits


def _bc_clone_linear(agents, steps=800, seed=0):
    """Warm-start des POIDS par behavioral cloning de l'oracle LINÉAIRE (obs col 12 → dir 0/1) dans la
    politique torch, puis sync → genome.W. Renvoie l'accuracy finale (gate : >0.9 = bassin formé).
    ⚠️ CAVEAT (EDR-S2-011) : le BC entraîne `_step(obs, H_in=0)` (SINGLE-step). Le bassin obtenu (acc 1.0)
    NE TRANSFÈRE PAS au forward RÉCURRENT du monde (H accumulé sur les ticks + gate) : la cohorte
    warm-startée survit au plancher (~8) même SANS crédit. Pour un vrai warm-start in-world, cloner sur des
    ROLLOUTS réels (séquences obs/H/action de l'oracle in-world), pas `_step` à H=0."""
    import torch
    from src.agents.backend import make_population
    pop = make_population(agents, backend="torch")
    I, O, N, B = pop.I, pop.O, pop.N, pop.B
    rng = np.random.RandomState(seed)

    def batch():
        a = rng.choice([-1.0, 1.0], B)
        o = np.zeros((B, I), dtype=np.float32)
        o[:, BIT_A] = a
        return torch.tensor(o), torch.tensor((a > 0).astype(np.int64))

    for _ in range(steps):
        o, tg = batch()
        out = pop._step(o, torch.zeros((B, N)))[:, N - O:N][:, :8]
        loss = torch.nn.functional.cross_entropy(out, tg)
        pop.opt.zero_grad(); loss.backward(); pop.opt.step()
    o, tg = batch()
    out = pop._step(o, torch.zeros((B, N)))[:, N - O:N][:, :8]
    acc = float((out.argmax(1) == tg).float().mean())
    pop._write_back()                                      # sync poids appris → genome.W des agents
    return acc


def run_credit_linear(seed=2026, warmstart=False, eras=6, num_agents=12, max_ticks=200,
                      base_metabolism=0.75, cog_gain=12.0, bc_steps=800):
    """Test PROPRE du verrou crédit (tâche LINÉAIREMENT décodable, isole le crédit de la représentation).
    warmstart=False : cohorte fraîche → le crédit in-world APPREND-il la tâche linéaire à froid ?
    warmstart=True  : cohorte BC-clonée (bassin de poids pré-formé) → le crédit RETIENT-il le bassin sous
    le régime dur ? Renvoie {bc_acc, trend (survie médiane/ère), final}."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.seed_ai.harness import seed_at
    from src.agents.mamba_agent import MambaAgent

    agents = [MambaAgent() for _ in range(num_agents)]
    bc_acc = _bc_clone_linear(agents, steps=bc_steps, seed=seed) if warmstart else None
    trend = []
    for era in range(eras):
        seed_at(seed, era)
        e = Biosphere3D()
        e.benchmark_mode = True
        e.night_enabled = False
        e.current_era = 10_000
        e.config.cognitive_demand = True
        e.config.cog_linear = True
        e.config.cog_gain = cog_gain
        e.config.base_metabolism = base_metabolism
        e.config.forage_payoff = 0.0
        e.use_torch_inworld = True
        for a in agents:
            e.add_agent(a, energy=80.0)
        t = 0
        while e.agents and t < max_ticks:
            e.step()
            t += 1
        ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
        import numpy as _np
        trend.append(float(_np.median(ages)) if ages else 0.0)
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    return {"bc_acc": bc_acc, "trend": trend, "final": trend[-1] if trend else 0.0}


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
