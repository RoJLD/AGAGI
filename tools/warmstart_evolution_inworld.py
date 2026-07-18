"""WARM-001 / WARM-002 — deux optimiseurs (imitation BPTT récurrente ; évolution W-only) contre le
verrou crédit in-world. Verdict DÉCISIF partagé = témoin within-subject (marqueur + survie) sur le
génome résultant, évalué sous le MÊME forward que celui qui l'a produit (anti-confound). Réutilise le
régime S2-009 (cognitive_demand). NE modifie PAS les outils partagés (s2_demand, demand_marker,
s2_demand_ablation, mutation). REF-DEMAND-MARKER.

Usage : python tools/warmstart_evolution_inworld.py
  (env: WARM_SEED, WARM_GEN, WARM_POP, WARM_EPOCHS, WARM_K, WARM_METAB, WARM_COG)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.s2_demand import run_condition
from tools.s2_demand_ablation import derange_rows, PerceptionAblatedMamba
from tools.demand_marker import ablation_verdict
from tools.cognitive_demand_inworld import CognitiveOracleBatchModel, BIT_A, BIT_B

METAB_DEFAULT = 0.75
COG_DEFAULT = 12.0
PLANCHER = 7.0                      # survie no-perception (S2-009) ; repère "≫ plancher"


def make_cog_world(metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """Renvoie un callable zero-arg construisant un Biosphere3D en régime cognitive_demand S2-009."""
    from src.worlds.world_1_stoneage import Biosphere3D

    def _make():
        e = Biosphere3D()
        e.config.cognitive_demand = True
        e.config.cog_gain = cog
        e.config.base_metabolism = metab
        e.config.forage_payoff = 0.0
        return e
    return _make


def _mamba_survival_eras(genome, ablate, seed, K, num_agents, max_ticks, metab, cog):
    """K ères, forward mamba, génome fixé sur des agents frais. ablate=True -> obs dérangée
    (PerceptionAblatedMamba, within-subject). Renvoie era_survival (liste de K médianes)."""
    world = make_cog_world(metab, cog)
    cls = PerceptionAblatedMamba if ablate else None
    res = run_condition(world, cls, genome, seed, num_agents=num_agents,
                        max_ticks=max_ticks, n_eras=K)
    return res["era_survival"]


def _torch_survival_eras(genome, ablate, seed, K, num_agents, max_ticks, metab, cog):
    """K ères, forward torch LTC, W GELÉ (lr=0), génome fixé. ablate=True -> obs dérangée avant le
    forward torch. Robuste aux reconstructions de pop (mortalité) via un patch local de make_population
    qui GÈLE (+ ABLATE) toute pop torch reconstruite par le monde. Renvoie era_survival."""
    import src.agents.backend as backend_mod
    from src.agents.backend_torch import TorchPopulationModel
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at

    class _AblatedTorchPop(TorchPopulationModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            return super().forward(derange_rows(np.asarray(batch_obs, dtype=np.float32)),
                                   env_surprise_batch)

    _orig_make = backend_mod.make_population

    def _frozen_make(agents, backend="legacy", world_model=None):
        if backend == "torch":
            cls = _AblatedTorchPop if ablate else TorchPopulationModel
            pop = cls(agents, world_model=world_model)
            for grp in pop.opt.param_groups:
                grp["lr"] = 0.0                       # GÈLE W (verdict : aucun apprentissage)
            return pop
        return _orig_make(agents, backend=backend, world_model=world_model)

    era_survival = []
    backend_mod.make_population = _frozen_make
    try:
        for i in range(K):
            seed_at(seed, i)
            e = Biosphere3D()
            e.benchmark_mode = True
            e.night_enabled = False
            e.current_era = 10_000
            e.config.cognitive_demand = True
            e.config.cog_gain = cog
            e.config.base_metabolism = metab
            e.config.forage_payoff = 0.0
            e.use_torch_inworld = True
            e.torch_episode_k = 10 ** 9               # _maybe_learn_episode ne se déclenche jamais
            for _ in range(num_agents):
                a = MambaAgent()
                a.from_genome(genome)
                e.add_agent(a, energy=80.0)
            t = 0
            while e.agents and t < max_ticks:
                e.step()
                t += 1
            ages = [int(a["age"]) for a in list(e.agents) + list(getattr(e, "dead_agents", []))]
            era_survival.append(float(np.median(ages)) if ages else 0.0)
            if hasattr(e, "memory_retriever"):
                e.memory_retriever.stop()
    finally:
        backend_mod.make_population = _orig_make      # restaure toujours le seam global
    return era_survival


def verdict_demand_marker(genome, backend, seed=2026, K=12, num_agents=12, max_ticks=200,
                          metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """Témoin within-subject sur un génome : intact vs perception dérangée, K ères, sous le forward
    `backend` ('mamba' ou 'torch'). PASS = verdict PERCEPTION_DEMANDED ET intact ≫ plancher."""
    eras = _torch_survival_eras if backend == "torch" else _mamba_survival_eras
    intact = eras(genome, False, seed, K, num_agents, max_ticks, metab, cog)
    ablated = eras(genome, True, seed, K, num_agents, max_ticks, metab, cog)
    v = ablation_verdict(intact, ablated)
    verdict = {"X_DEMANDED": "PERCEPTION_DEMANDED", "X_DECOY": "NEUTRAL",
               "INCONCLUSIVE": "INCONCLUSIVE"}[v["verdict"]]
    return {"ratio": v["ratio"], "verdict": verdict, "n": v["n"],
            "intact_survival": float(np.median(intact)) if intact else 0.0,
            "ablated_survival": float(np.median(ablated)) if ablated else 0.0}


def _mutate_W_only(genome, power, rate=0.8, rng=None):
    """Mutation W-SEUL (in place) : bruit gaussien sur les entrées non-nulles de genome.W. NE touche
    NI W_router NI bytecode NI thresholds -> même espace de recherche que le gradient (genome.W seul),
    pour que 'évolution vs gradient' n'ait qu'une variable : l'optimiseur."""
    draw = rng or np.random
    W = genome.W
    nz = np.nonzero(W)
    if len(nz[0]) == 0:
        return
    m = draw.rand(len(nz[0])) < rate
    ii, jj = nz[0][m], nz[1][m]
    if len(ii) == 0:
        return
    genome.W[ii, jj] = (genome.W[ii, jj]
                        + draw.normal(0.0, power, size=len(ii))).astype(genome.W.dtype)


def _eval_generation(genomes, seed, era_idx, max_ticks, metab, cog):
    """Un épisode cognitive_demand : tous les génomes = agents dans UN monde ; fitness = âge (survie).
    La population partage un rollout (signal per-agent). Renvoie les âges alignés sur `genomes`."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at

    seed_at(seed, era_idx)
    e = Biosphere3D()
    e.benchmark_mode = True
    e.night_enabled = False
    e.current_era = 10_000
    e.config.cognitive_demand = True
    e.config.cog_gain = cog
    e.config.base_metabolism = metab
    e.config.forage_payoff = 0.0
    ids = []
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        e.add_agent(a, energy=80.0)
        ids.append(e.agents[-1]["id"])          # add_agent() ne renvoie pas l'id -> capturé juste après
    t = 0
    while e.agents and t < max_ticks:
        e.step()
        t += 1
    ages_by_id = {rec["id"]: int(rec["age"])
                  for rec in list(e.agents) + list(getattr(e, "dead_agents", []))}
    if hasattr(e, "memory_retriever"):
        e.memory_retriever.stop()
    return [ages_by_id.get(i, 0) for i in ids]


def run_inworld_evolution(seed=2026, generations=50, pop_size=24, survival_frac=0.25,
                          mut_power=0.15, max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """Évolution W-only : population de MambaAgents (W aléatoire), fitness = survie en cognitive_demand,
    sélection top-k + élitisme + descendance mutée W-seul. Renvoie la trace de survie médiane du top-k
    par génération + le meilleur génome final. L'optimiseur que le SIM utilise (pas le gradient)."""
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at

    seed_at(seed, 0)
    genomes = [MambaAgent().genome for _ in range(pop_size)]
    n_surv = max(1, int(pop_size * survival_frac))
    trend, best_genome, best_age = [], None, 0
    for gen in range(generations):
        ages = _eval_generation(genomes, seed, gen, max_ticks, metab, cog)
        order = list(np.argsort(ages)[::-1])
        survivors = [genomes[i] for i in order[:n_surv]]
        best_genome, best_age = genomes[order[0]].clone(), int(ages[order[0]])
        trend.append(float(np.median([ages[i] for i in order[:n_surv]])))
        new = [s.clone() for s in survivors]                       # élitisme
        while len(new) < pop_size:
            parent = survivors[np.random.randint(n_surv)]
            child = parent.clone()
            _mutate_W_only(child, mut_power)
            new.append(child)
        genomes = new
    return {"trend": trend, "best_genome": best_genome, "best_age": best_age}


class RecordingOracleBatchModel(CognitiveOracleBatchModel):
    """Oracle qui ENREGISTRE, par tick, l'obs présentée (B,59) + le label enseignant correct_dir
    (B,) avant de jouer normalement. Attributs de CLASSE (le monde ré-instancie le batch model chaque
    tick). Réinitialiser RECORDED_OBS/RECORDED_TGT avant chaque collecte."""
    RECORDED_OBS = []
    RECORDED_TGT = []

    def forward(self, batch_obs, env_surprise_batch=None):
        arr = np.asarray(batch_obs, dtype=np.float32)
        a = arr[:, BIT_A]
        b = arr[:, BIT_B]
        tgt = (2 * (a > 0) + (b > 0)).astype(int)
        type(self).RECORDED_OBS.append(arr.copy())
        type(self).RECORDED_TGT.append(tgt.copy())
        return super().forward(batch_obs, env_surprise_batch)


def _collect_oracle_trajectory(seed, num_agents, max_ticks, metab, cog):
    """Rollout d'une cohorte oracle (survie pleine -> B constant) ; renvoie (obs_seq, tgt_seq) à B fixe.
    Garde le préfixe où toutes les lignes sont présentes (B == num_agents) : la séquence BPTT exige B
    constant. L'oracle intact survit ~max_ticks (S2-009) -> préfixe = trajectoire quasi complète."""
    RecordingOracleBatchModel.RECORDED_OBS = []
    RecordingOracleBatchModel.RECORDED_TGT = []
    world = make_cog_world(metab, cog)
    run_condition(world, RecordingOracleBatchModel, None, seed,
                  num_agents=num_agents, max_ticks=max_ticks, n_eras=1)
    obs_all = RecordingOracleBatchModel.RECORDED_OBS
    tgt_all = RecordingOracleBatchModel.RECORDED_TGT
    obs_seq, tgt_seq = [], []
    for obs, tgt in zip(obs_all, tgt_all):
        if obs.shape[0] != num_agents:                 # une mort a réduit B -> stop (B doit rester fixe)
            break
        obs_seq.append(obs)
        tgt_seq.append(tgt)
    return obs_seq, tgt_seq


def _imitation_accuracy(pop, obs_seq, tgt_seq):
    """Taux de bonne-direction du génome courant sous le forward torch (sans grad), sur la trajectoire."""
    import torch
    correct = total = 0
    H = torch.zeros((pop.B, pop.N), device=pop.device)
    with torch.no_grad():
        for obs, tgt in zip(obs_seq, tgt_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :pop.I], device=pop.device)
            H = pop._step(obs_t, H)
            out = H[:, pop.N - pop.O:pop.N]
            pred = torch.argmax(out[:, :8], dim=1).cpu().numpy()
            correct += int(np.sum(pred == np.asarray(tgt)))
            total += len(tgt)
    return correct / max(1, total)


def run_bptt_imitation_warmstart(seed=2026, num_agents=12, n_epochs=200, truncate_window=25,
                                 max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """WARM-001 : collecte la trajectoire-enseignant (oracle, B constant) puis entraîne une cohorte
    torch par imitation récurrente BPTT (imitate_episode_bptt) sur les obs RÉELLES 59-dim. Renvoie le
    génome warm-starté (agent 0), la trace de perte et l'accuracy d'imitation finale. None si torch absent."""
    try:
        import torch  # noqa: F401
    except Exception:
        print("WARM-001 SKIP : torch absent (requirements-torch.txt).")
        return None
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.seed_ai.harness import seed_at

    obs_seq, tgt_seq = _collect_oracle_trajectory(seed, num_agents, max_ticks, metab, cog)
    if not obs_seq:
        print("WARM-001 SKIP : trajectoire oracle vide.")
        return None

    seed_at(seed, 1)
    agents = [MambaAgent() for _ in range(num_agents)]        # génomes apprenants (dims homogènes)
    pop = make_population(agents, backend="torch")
    loss_trend = []
    for _ in range(n_epochs):
        loss = pop.imitate_episode_bptt(obs_seq, tgt_seq, truncate_window=truncate_window)
        loss_trend.append(loss)
    pop._write_back()
    acc = _imitation_accuracy(pop, obs_seq, tgt_seq)
    return {"learned_genome": agents[0].genome, "loss_trend": loss_trend, "imit_acc": acc}


def main():
    seed = int(os.environ.get("WARM_SEED", "2026"))
    generations = int(os.environ.get("WARM_GEN", "50"))
    pop_size = int(os.environ.get("WARM_POP", "24"))
    n_epochs = int(os.environ.get("WARM_EPOCHS", "200"))
    K = int(os.environ.get("WARM_K", "12"))
    metab = float(os.environ.get("WARM_METAB", str(METAB_DEFAULT)))
    cog = float(os.environ.get("WARM_COG", str(COG_DEFAULT)))

    print(f"\n=== WARM — deux optimiseurs vs le verrou crédit in-world "
          f"(seed={seed}, K={K}, metab={metab}, cog={cog}) ===")
    print(f"repères : plancher no-perception ≈ {PLANCHER} | oracle intact ≈ 200 | REINFORCE froid = plat (S2-009)\n")

    # WARM-002 — évolution W-only
    evo = run_inworld_evolution(seed=seed, generations=generations, pop_size=pop_size,
                                max_ticks=200, metab=metab, cog=cog)
    print(f"WARM-002 évolution : trend top-k = {[round(x, 1) for x in evo['trend']]}")
    ve = verdict_demand_marker(evo["best_genome"], backend="mamba", seed=seed, K=K,
                               metab=metab, cog=cog)
    print(f"WARM-002 verdict (mamba) : ratio={ve['ratio']:.2f} intact={ve['intact_survival']:.1f} "
          f"ablé={ve['ablated_survival']:.1f} -> {ve['verdict']} (n={ve['n']})")

    # WARM-001 — imitation BPTT
    imi = run_bptt_imitation_warmstart(seed=seed, num_agents=max(12, K), n_epochs=n_epochs,
                                       max_ticks=200, metab=metab, cog=cog)
    if imi is None:
        vi = None
        print("WARM-001 : SKIP (torch absent)")
    else:
        print(f"WARM-001 imitation : loss {imi['loss_trend'][0]:.3f} -> {imi['loss_trend'][-1]:.3f} "
              f"| imit_acc={imi['imit_acc']:.3f}")
        vi = verdict_demand_marker(imi["learned_genome"], backend="torch", seed=seed, K=K,
                                   metab=metab, cog=cog)
        print(f"WARM-001 verdict (torch) : ratio={vi['ratio']:.2f} intact={vi['intact_survival']:.1f} "
              f"ablé={vi['ablated_survival']:.1f} -> {vi['verdict']} (n={vi['n']})")

    def _pass(v):
        return bool(v) and v["verdict"] == "PERCEPTION_DEMANDED" and v["intact_survival"] > 2 * PLANCHER

    print("\nSynthèse (PASS = marqueur PERCEPTION_DEMANDED ET survie intacte ≫ plancher) :")
    print(f"  WARM-002 évolution W-only : {'PASS' if _pass(ve) else 'FAIL'}")
    print(f"  WARM-001 imitation BPTT   : {'PASS' if _pass(vi) else ('SKIP' if vi is None else 'FAIL')}")
    print("-> Interpréter : un PASS où le REINFORCE froid échoue = le verrou était le chemin de crédit "
          "de CET optimiseur, pas le substrat/monde. Deux FAIL = verrou plus profond (gradient de "
          "sélection cognitif faible). Rédiger EDR-WARM-001/002 + MàJ REF-DEMAND-MARKER.")
    return {"evo": evo["trend"], "warm002": ve, "warm001": vi}


if __name__ == "__main__":
    main()
