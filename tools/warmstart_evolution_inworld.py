"""WARM-001 / WARM-002 — deux optimiseurs (imitation BPTT récurrente ; évolution W-only) contre le
verrou crédit in-world. Verdict DÉCISIF partagé = témoin within-subject (marqueur + survie) sur le
génome résultant, évalué sous le MÊME forward que celui qui l'a produit (anti-confound). Réutilise le
régime S2-009 (cognitive_demand). NE modifie PAS les outils partagés (s2_demand, demand_marker,
s2_demand_ablation, mutation). REF-DEMAND-MARKER.

Usage : python tools/warmstart_evolution_inworld.py
  (env: WARM_SEED, WARM_GEN, WARM_POP, WARM_EPOCHS, WARM_LR, WARM_K, WARM_METAB, WARM_COG)
  Ex. reproduction table EDR-WARM-001 (acc->1.0) : WARM_LR=0.6 WARM_EPOCHS=20000 python tools/warmstart_evolution_inworld.py
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
PLANCHER = 7.0                      # survie no-perception (S2-009) ; repère bas
ORACLE_REF = 200.0                 # survie de l'oracle (S2-009) ; repère haut. PASS = survie ≥ mi-chemin.


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


def _inworld_accuracy(genome, seed=2026, num_agents=12, max_ticks=200,
                      metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """Sonde DÉCISIVE (EDR-WARM-001 §mécanisme) : accuracy per-tick RÉELLE du génome quand il pilote
    SES PROPRES états in-world (forward torch, W gelé), vs l'accuracy sur la trajectoire-enseignant.
    Enregistre argmax(logits[:8]) vs correct_dir=2*(bit_a>0)+(bit_b>0) de CHAQUE tick, sur les obs que
    l'agent visite lui-même. Si elle s'effondre vs l'accuracy enseignant -> la carte ne tient PAS hors
    de la distribution de l'oracle (dérive de l'état récurrent / sur-apprentissage mono-trajectoire) ;
    si elle reste haute alors que la survie plafonne -> le mur n'est pas la décision (autre cause).
    NB : lit les logits BRUTS du forward (avant pénalité anti-répétition/consensus appliqués par le monde)
    = la décision INTRINSÈQUE du génome. Renvoie l'accuracy on-policy (float)."""
    try:
        import torch  # noqa: F401
    except Exception:
        return None
    import src.agents.backend as backend_mod
    from src.agents.backend_torch import TorchPopulationModel
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at

    stats = {"correct": 0, "total": 0}

    class _RecAccTorchPop(TorchPopulationModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            arr = np.asarray(batch_obs, dtype=np.float32)
            logits, cs = super().forward(arr, env_surprise_batch)
            if getattr(logits, "shape", (0,))[0]:
                pred = np.argmax(logits[:, :8], axis=1)
                cd = (2 * (arr[:, BIT_A] > 0) + (arr[:, BIT_B] > 0)).astype(int)
                stats["correct"] += int(np.sum(pred == cd))
                stats["total"] += int(len(cd))
            return logits, cs

    _orig = backend_mod.make_population

    def _frozen_rec(agents, backend="legacy", world_model=None):
        if backend == "torch":
            pop = _RecAccTorchPop(agents, world_model=world_model)
            for grp in pop.opt.param_groups:
                grp["lr"] = 0.0
            return pop
        return _orig(agents, backend=backend, world_model=world_model)

    backend_mod.make_population = _frozen_rec
    try:
        seed_at(seed, 0)
        e = Biosphere3D()
        e.benchmark_mode = True
        e.night_enabled = False
        e.current_era = 10_000
        e.config.cognitive_demand = True
        e.config.cog_gain = cog
        e.config.base_metabolism = metab
        e.config.forage_payoff = 0.0
        e.use_torch_inworld = True
        e.torch_episode_k = 10 ** 9
        for _ in range(num_agents):
            a = MambaAgent()
            a.from_genome(genome)
            e.add_agent(a, energy=80.0)
        t = 0
        while e.agents and t < max_ticks:
            e.step()
            t += 1
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    finally:
        backend_mod.make_population = _orig
    return stats["correct"] / max(1, stats["total"])


def _collect_onpolicy_trajectory(genome, seed=2026, num_agents=12, max_ticks=200,
                                 metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """Déroule le génome LEARNER on-policy sous torch (W gelé) et enregistre les séquences fixed-B
    masquées qu'il visite LUI-MÊME (DAgger). Alignement à travers les morts par id(model) : les objets-
    modèles persistent aux reconstructions de pop -> chaque ligne du forward est remise à son index
    d'origine ; les morts -> obs 0 / mask 0. Réétiquette par l'oracle correct_dir=2*(bit_a>0)+(bit_b>0).
    L'obs est lue DANS forward (signal _cog_sig frais du tick). Renvoie (obs_seq, tgt_seq, mask_seq)."""
    try:
        import torch  # noqa: F401
    except Exception:
        return [], [], []
    import src.agents.backend as backend_mod
    from src.agents.backend_torch import TorchPopulationModel
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at

    rec = {"obs": [], "tgt": [], "mask": []}
    orig_index = {}

    class _RecTorchPop(TorchPopulationModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            arr = np.asarray(batch_obs, dtype=np.float32)
            logits, cs = super().forward(arr, env_surprise_batch)
            cols = arr.shape[1] if arr.ndim == 2 else 0
            obs_row = np.zeros((num_agents, cols), dtype=np.float32)
            tgt_row = np.zeros(num_agents, dtype=np.int64)
            mask_row = np.zeros(num_agents, dtype=np.float32)
            for j in range(arr.shape[0]):
                oi = orig_index.get(id(self.agents[j]))
                if oi is None:
                    continue
                obs_row[oi] = arr[j]
                tgt_row[oi] = int(2 * (arr[j, BIT_A] > 0) + (arr[j, BIT_B] > 0))
                mask_row[oi] = 1.0
            rec["obs"].append(obs_row)
            rec["tgt"].append(tgt_row)
            rec["mask"].append(mask_row)
            return logits, cs

    _orig = backend_mod.make_population

    def _frozen_rec(agents, backend="legacy", world_model=None):
        if backend == "torch":
            pop = _RecTorchPop(agents, world_model=world_model)
            for grp in pop.opt.param_groups:
                grp["lr"] = 0.0
            return pop
        return _orig(agents, backend=backend, world_model=world_model)

    backend_mod.make_population = _frozen_rec
    try:
        seed_at(seed, 0)
        e = Biosphere3D()
        e.benchmark_mode = True
        e.night_enabled = False
        e.current_era = 10_000
        e.config.cognitive_demand = True
        e.config.cog_gain = cog
        e.config.base_metabolism = metab
        e.config.forage_payoff = 0.0
        e.use_torch_inworld = True
        e.torch_episode_k = 10 ** 9
        for _ in range(num_agents):
            a = MambaAgent()
            a.from_genome(genome)
            e.add_agent(a, energy=80.0)
        for i, ag in enumerate(e.agents):                 # index d'origine par identité du modèle
            orig_index[id(ag["model"])] = i
        t = 0
        while e.agents and t < max_ticks:
            e.step()
            t += 1
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    finally:
        backend_mod.make_population = _orig
    # filtre les ticks entièrement vides (aucun agent mappé) par sécurité
    keep = [k for k in range(len(rec["obs"])) if rec["mask"][k].sum() > 0]
    return ([rec["obs"][k] for k in keep], [rec["tgt"][k] for k in keep],
            [rec["mask"][k] for k in keep])


def _collect_diag_trajectory(driver, genome=None, seed=2026, num_agents=12, max_ticks=200,
                             metab=METAB_DEFAULT, cog=COG_DEFAULT):
    """Collecteur de DIAGNOSTIC (WARM-004) : trajectoire PLEINE LONGUEUR (aucune troncature à la 1re
    mort) et MASQUÉE, alignée par id(model) à travers les morts. Enregistre aussi l'ÉNERGIE au moment
    de la DÉCISION (lue depuis l'env dans forward, avant la résolution biologique).
      driver='oracle' : l'ORACLE pilote (chemin non-torch via batch_model_cls) -> fournit les états
        TARDIFS (ticks > ~35) que le learner ne visite JAMAIS (ce que _collect_oracle_trajectory, qui
        tronque à la 1re mort, ne peut pas donner).
      driver='genome' : `genome` pilote sous torch, W GELÉ -> rollout on-policy du learner.
    Morts -> obs 0 / tgt 0 / mask 0 / énergie NaN. Renvoie (obs_seq, tgt_seq, mask_seq, energy_seq)."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.harness import seed_at

    rec = {"obs": [], "tgt": [], "mask": [], "energy": []}
    orig_index = {}
    env_ref = {}

    def _record(arr, models):
        cols = arr.shape[1] if arr.ndim == 2 else 0
        obs_row = np.zeros((num_agents, cols), dtype=np.float32)
        tgt_row = np.zeros(num_agents, dtype=np.int64)
        mask_row = np.zeros(num_agents, dtype=np.float32)
        en_row = np.full(num_agents, np.nan, dtype=np.float32)
        e = env_ref.get("e")
        energies = [float(a["energy"]) for a in e.agents] if e is not None else []
        for j in range(arr.shape[0]):
            oi = orig_index.get(id(models[j]))
            if oi is None:
                continue
            obs_row[oi] = arr[j]
            tgt_row[oi] = int(2 * (arr[j, BIT_A] > 0) + (arr[j, BIT_B] > 0))
            mask_row[oi] = 1.0
            if j < len(energies):
                en_row[oi] = energies[j]
        rec["obs"].append(obs_row)
        rec["tgt"].append(tgt_row)
        rec["mask"].append(mask_row)
        rec["energy"].append(en_row)

    class _RecOracle(CognitiveOracleBatchModel):
        def forward(self, batch_obs, env_surprise_batch=None):
            _record(np.asarray(batch_obs, dtype=np.float32), self.agents)
            return super().forward(batch_obs, env_surprise_batch)

    seed_at(seed, 0)
    e = Biosphere3D()
    e.benchmark_mode = True
    e.night_enabled = False
    e.current_era = 10_000
    e.config.cognitive_demand = True
    e.config.cog_gain = cog
    e.config.base_metabolism = metab
    e.config.forage_payoff = 0.0
    env_ref["e"] = e

    backend_mod = None
    _orig = None
    if driver == "genome":
        import src.agents.backend as backend_mod
        from src.agents.backend_torch import TorchPopulationModel

        class _RecTorch(TorchPopulationModel):
            def forward(self, batch_obs, env_surprise_batch=None):
                arr = np.asarray(batch_obs, dtype=np.float32)
                logits, cs = super().forward(arr, env_surprise_batch)
                _record(arr, self.agents)
                return logits, cs

        _orig = backend_mod.make_population

        def _frozen(agents, backend="legacy", world_model=None):
            if backend == "torch":
                pop = _RecTorch(agents, world_model=world_model)
                for grp in pop.opt.param_groups:
                    grp["lr"] = 0.0
                return pop
            return _orig(agents, backend=backend, world_model=world_model)

        backend_mod.make_population = _frozen
        e.use_torch_inworld = True
        e.torch_episode_k = 10 ** 9
    elif driver == "oracle":
        e.batch_model_cls = _RecOracle
    else:                                    # instrument de mesure : pas de repli silencieux sur l'oracle
        raise ValueError(f"driver inconnu : {driver!r} (attendu 'oracle' ou 'genome')")

    try:
        for _ in range(num_agents):
            a = MambaAgent()
            if genome is not None:
                a.from_genome(genome)
            e.add_agent(a, energy=80.0)
        for i, ag in enumerate(e.agents):
            orig_index[id(ag["model"])] = i
        t = 0
        while e.agents and t < max_ticks:
            e.step()
            t += 1
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    finally:
        if _orig is not None:
            backend_mod.make_population = _orig
    keep = [k for k in range(len(rec["obs"])) if rec["mask"][k].sum() > 0]
    return ([rec["obs"][k] for k in keep], [rec["tgt"][k] for k in keep],
            [rec["mask"][k] for k in keep], [rec["energy"][k] for k in keep])


def bins_by_tick(mask_seq, edges):
    """bin_ids[t] = (B,) index du segment de tick contenant t selon `edges` croissants ; -1 hors bornes."""
    ids = []
    for t, m in enumerate(mask_seq):
        b = -1
        for k in range(len(edges) - 1):
            if edges[k] <= t < edges[k + 1]:
                b = k
                break
        ids.append(np.full(len(m), b, dtype=np.int64))
    return ids


def bins_by_energy(energy_seq, edges):
    """bin_ids[t] = (B,) index du segment d'énergie par agent selon `edges` ; NaN (mort) -> -1."""
    ids = []
    for en in energy_seq:
        en = np.asarray(en, dtype=np.float64)
        b = np.full(en.shape[0], -1, dtype=np.int64)
        for k in range(len(edges) - 1):
            sel = (~np.isnan(en)) & (en >= edges[k]) & (en < edges[k + 1])
            b[sel] = k
        ids.append(b)
    return ids


def accuracy_binned(genome, obs_seq, tgt_seq, mask_seq, bin_ids, n_bins, num_agents=12,
                    reset_h_every=None):
    """Rejoue `genome` (forward torch, no_grad, W gelé, replay PUR sans monde) sur obs_seq depuis H=0 et
    agrège l'accuracy de décision par bin. Ignore mask==0 et bin<0. Renvoie [{bin,n,acc}]. None si torch
    absent.

    ⚠️ CONFOND DE PROFONDEUR RÉCURRENTE (EDR-WARM-004) : en replay continu, H tourne sans interruption
    sur toute la séquence, alors qu'IN-WORLD le pop torch est RECONSTRUIT (H→0) à chaque changement de B,
    c'est-à-dire à CHAQUE MORT. Sur des états identiques, ce seul écart vaut ~0.11 d'accuracy. Donc une
    dégradation par bin de tick mélange (i) les états eux-mêmes et (ii) la profondeur récurrente atteinte.
    `reset_h_every=W` remet H à 0 tous les W pas -> permet de DÉPARTAGER les deux (comparer le replay
    continu et le replay réinitialisé sur les mêmes bins)."""
    try:
        import torch
    except Exception:
        return None
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel

    agents = [MambaAgent() for _ in range(num_agents)]
    for a in agents:
        a.from_genome(genome)
    pop = TorchPopulationModel(agents, lr=0.0)
    correct = np.zeros(n_bins, dtype=np.int64)
    total = np.zeros(n_bins, dtype=np.int64)
    H = torch.zeros((pop.B, pop.N), device=pop.device)
    with torch.no_grad():
        for t, obs in enumerate(obs_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :pop.I], device=pop.device)
            if reset_h_every and t > 0 and (t % reset_h_every == 0):
                H = torch.zeros((pop.B, pop.N), device=pop.device)   # borne la profondeur récurrente
            H = pop._step(obs_t, H)
            out = H[:, pop.N - pop.O:pop.N]
            pred = torch.argmax(out[:, :8], dim=1).cpu().numpy()
            tgt = np.asarray(tgt_seq[t])
            m = np.asarray(mask_seq[t])
            b = np.asarray(bin_ids[t])
            for i in range(min(len(tgt), len(pred))):
                if m[i] <= 0 or b[i] < 0 or b[i] >= n_bins:
                    continue
                total[b[i]] += 1
                if int(pred[i]) == int(tgt[i]):
                    correct[b[i]] += 1
    return [{"bin": k, "n": int(total[k]),
             "acc": (float(correct[k]) / total[k]) if total[k] else float("nan")}
            for k in range(n_bins)]


def run_bptt_imitation_warmstart(seed=2026, num_agents=12, n_epochs=200, truncate_window=25,
                                 max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT, lr=0.5):
    """WARM-001 : collecte la trajectoire-enseignant (oracle, B constant) puis entraîne une cohorte
    torch par imitation récurrente BPTT (imitate_episode_bptt) sur les obs RÉELLES 59-dim. `lr` est
    EXPOSÉ (le run par défaut lr=0.04 sous-entraîne ; la table EDR-WARM-001 balaie lr∈[0.5,0.7]). Renvoie
    le génome warm-starté (agent 0), la trace de perte et l'accuracy d'imitation finale. None si torch absent."""
    try:
        import torch  # noqa: F401
    except Exception:
        print("WARM-001 SKIP : torch absent (requirements-torch.txt).")
        return None
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel      # lr exposé (make_population ne le propage pas)
    from src.seed_ai.harness import seed_at

    obs_seq, tgt_seq = _collect_oracle_trajectory(seed, num_agents, max_ticks, metab, cog)
    if not obs_seq:
        print("WARM-001 SKIP : trajectoire oracle vide.")
        return None

    seed_at(seed, 1)
    agents = [MambaAgent() for _ in range(num_agents)]        # génomes apprenants (dims homogènes)
    pop = TorchPopulationModel(agents, lr=lr)
    loss_trend = []
    for _ in range(n_epochs):
        loss = pop.imitate_episode_bptt(obs_seq, tgt_seq, truncate_window=truncate_window)
        loss_trend.append(loss)
    pop._write_back()
    acc = _imitation_accuracy(pop, obs_seq, tgt_seq)
    return {"learned_genome": agents[0].genome, "loss_trend": loss_trend, "imit_acc": acc}


def run_dagger_warmstart(seed=2026, rounds=6, epochs_per_round=3000, lr=0.5, num_agents=12,
                         max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT, K=12):
    """WARM-003 : DAgger on-policy. Round 0 = bootstrap sur la trajectoire-ENSEIGNANT (= WARM-001).
    Rounds suivants : agrège les états que le learner visite lui-même (réétiquetés oracle) et réentraîne
    en BPTT récurrent MASQUÉ (round-robin sur le dataset -> coût borné = epochs_per_round×rounds appels).
    Trace acc_on-policy + survie par round ; attaque le plafond 0.734 de WARM-001. None si torch absent."""
    try:
        import torch  # noqa: F401
    except Exception:
        print("WARM-003 SKIP : torch absent.")
        return None
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    from src.seed_ai.harness import seed_at

    o0, t0 = _collect_oracle_trajectory(seed, num_agents, max_ticks, metab, cog)
    if not o0:
        print("WARM-003 SKIP : trajectoire oracle vide.")
        return None
    dataset = [(o0, t0, [np.ones(len(t), dtype=np.float32) for t in t0])]   # round 0 = oracle (mask=1)

    seed_at(seed, 1)
    agents = [MambaAgent() for _ in range(num_agents)]
    pop = TorchPopulationModel(agents, lr=lr)

    trend_acc, trend_surv = [], []
    for r in range(rounds):
        for ep in range(epochs_per_round):
            obs_s, tgt_s, mask_s = dataset[ep % len(dataset)]        # round-robin (coût borné)
            pop.imitate_episode_bptt(obs_s, tgt_s, truncate_window=25, mask_seq=mask_s)
        pop._write_back()
        g = agents[0].genome
        acc_op = _inworld_accuracy(g, seed=seed, num_agents=num_agents, max_ticks=max_ticks,
                                   metab=metab, cog=cog)
        surv = _torch_survival_eras(g, False, seed, K, num_agents, max_ticks, metab, cog)
        trend_acc.append(float(acc_op) if acc_op is not None else 0.0)
        trend_surv.append(float(np.median(surv)) if surv else 0.0)
        if r < rounds - 1:                                          # collecte pour le round suivant
            oo, tt, mm = _collect_onpolicy_trajectory(g, seed=seed, num_agents=num_agents,
                                                      max_ticks=max_ticks, metab=metab, cog=cog)
            if oo:
                dataset.append((oo, tt, mm))
    final_v = verdict_demand_marker(agents[0].genome, backend="torch", seed=seed, K=K,
                                    metab=metab, cog=cog)
    return {"trend_onpolicy_acc": trend_acc, "trend_survival": trend_surv,
            "final_genome": agents[0].genome, "final_verdict": final_v}


TICK_EDGES = [0, 35, 70, 120, 10 ** 6]        # bins de tick : ≤35 = vécu du learner ; >35 = jamais visité
ENERGY_EDGES = [0, 20, 40, 60, 80, 10 ** 6]   # bins d'énergie : bas = états critiques


def run_coverage_precision_diagnostic(seed=2026, rounds=6, epochs_per_round=3000, lr=0.5,
                                      num_agents=12, max_ticks=200, metab=METAB_DEFAULT,
                                      cog=COG_DEFAULT, K=12,
                                      genome_path="results/warm003_dagger_genome.npz"):
    """WARM-004 : tranche COUVERTURE vs PRÉCISION pour le gap résiduel de WARM-003.
      (A) COUVERTURE : accuracy du génome DAgger sur les états TARDIFS de l'ORACLE (jamais visités),
          binnée par tick -> effondrement sur les bins tardifs = couverture.
      (B) PRÉCISION : accuracy sur SON PROPRE rollout, binnée par ÉNERGIE -> chute en basse énergie =
          précision aux états critiques.
    Reproduit (ou recharge) le génome DAgger et le PERSISTE (il n'avait pas été sauvé en WARM-003)."""
    try:
        import torch  # noqa: F401
    except Exception:
        print("WARM-004 SKIP : torch absent.")
        return None
    from src.seed_ai.mutation import Genome

    g = None
    if genome_path and os.path.exists(genome_path):
        d = np.load(genome_path, allow_pickle=False)
        g = Genome(d["W"], int(d["num_inputs"]), int(d["num_outputs"]))
        print(f"WARM-004 : génome rechargé depuis {genome_path}")
    else:
        dg = run_dagger_warmstart(seed=seed, rounds=rounds, epochs_per_round=epochs_per_round, lr=lr,
                                  num_agents=num_agents, max_ticks=max_ticks, metab=metab, cog=cog, K=K)
        if dg is None:
            return None
        g = dg["final_genome"]
        if genome_path:
            os.makedirs(os.path.dirname(genome_path) or ".", exist_ok=True)
            np.savez(genome_path, W=np.asarray(g.W, dtype=np.float32),
                     num_inputs=g.num_inputs, num_outputs=g.num_outputs)
            print(f"WARM-004 : génome DAgger sauvé -> {genome_path}")

    # (A) COUVERTURE — états de l'ORACLE, binnés par tick
    o_obs, o_tgt, o_mask, _o_en = _collect_diag_trajectory("oracle", seed=seed,
                                                           num_agents=num_agents, max_ticks=max_ticks,
                                                           metab=metab, cog=cog)
    cov = accuracy_binned(g, o_obs, o_tgt, o_mask, bins_by_tick(o_mask, TICK_EDGES),
                          n_bins=len(TICK_EDGES) - 1, num_agents=num_agents)

    # (B) PRÉCISION — rollout du génome, binné par énergie
    g_obs, g_tgt, g_mask, g_en = _collect_diag_trajectory("genome", genome=g, seed=seed,
                                                          num_agents=num_agents, max_ticks=max_ticks,
                                                          metab=metab, cog=cog)
    prec = accuracy_binned(g, g_obs, g_tgt, g_mask, bins_by_energy(g_en, ENERGY_EDGES),
                           n_bins=len(ENERGY_EDGES) - 1, num_agents=num_agents)

    def _late(rows, first_late=1):
        vals = [r["acc"] for r in rows[first_late:] if r["n"] > 0 and r["acc"] == r["acc"]]
        return min(vals) if vals else float("nan")

    def _low(rows):
        vals = [r["acc"] for r in rows[:2] if r["n"] > 0 and r["acc"] == r["acc"]]
        return min(vals) if vals else float("nan")

    def _high_e(rows, n_floor=30):
        """Bins d'énergie CONFORTABLE (index >=2) — le comparateur interne au test B."""
        vals = [r["acc"] for r in rows[2:] if r["n"] >= n_floor and r["acc"] == r["acc"]]
        return max(vals) if vals else float("nan")

    late_acc, low_e_acc = _late(cov), _low(prec)
    high_e_acc = _high_e(prec)
    early_acc = cov[0]["acc"] if cov and cov[0]["n"] > 0 else float("nan")

    # Deux effets GRADUÉS, jugés séparément et sur des comparaisons INTERNES à leur propre test.
    # (corrige un défaut de conception : comparer low_energy (test B) à late (test A) confrontait
    #  deux trajectoires DIFFÉRENTES ; la comparaison de précision doit être interne au test B.)
    COV_DROP, PREC_DROP = 0.10, 0.10
    cov_gap = (early_acc - late_acc) if (early_acc == early_acc and late_acc == late_acc) else float("nan")
    prec_gap = (high_e_acc - low_e_acc) if (high_e_acc == high_e_acc and low_e_acc == low_e_acc) else float("nan")
    has_cov = cov_gap == cov_gap and cov_gap >= COV_DROP
    has_prec = prec_gap == prec_gap and prec_gap >= PREC_DROP
    if has_cov and has_prec:
        verdict = "LES_DEUX"
    elif has_cov:
        verdict = "COUVERTURE"
    elif has_prec:
        verdict = "PRECISION"
    else:
        verdict = "NI_COUVERTURE_NI_PRECISION"
    if late_acc == late_acc and late_acc < 0.4:
        verdict += "_COUVERTURE_DOMINANTE"      # effondrement quasi-total hors du vécu

    print(f"\n=== WARM-004 — couverture vs précision (seed={seed}) ===")
    print(f"(A) COUVERTURE — acc du génome sur les états de l'ORACLE, par bin de tick {TICK_EDGES[:-1]}+ :")
    for r in cov:
        print(f"    bin {r['bin']} (ticks {TICK_EDGES[r['bin']]}-{TICK_EDGES[r['bin']+1]}) : "
              f"n={r['n']:5d} acc={r['acc']:.3f}")
    print(f"(B) PRÉCISION — acc sur son propre rollout, par bin d'énergie {ENERGY_EDGES[:-1]}+ :")
    for r in prec:
        print(f"    bin {r['bin']} (énergie {ENERGY_EDGES[r['bin']]}-{ENERGY_EDGES[r['bin']+1]}) : "
              f"n={r['n']:5d} acc={r['acc']:.3f}")
    print(f"\n(A) écart COUVERTURE : early(≤35)={early_acc:.3f} -> late(>35)={late_acc:.3f} "
          f"| gap={cov_gap:.3f} (seuil {COV_DROP})")
    print(f"(B) écart PRÉCISION  : haute-énergie={high_e_acc:.3f} -> basse-énergie={low_e_acc:.3f} "
          f"| gap={prec_gap:.3f} (seuil {PREC_DROP})")
    print(f"VERDICT WARM-004 : {verdict}")
    print("  COUVERTURE = dégradation sur les états jamais visités (mur de données).")
    print("  PRECISION  = dégradation aux états critiques basse-énergie.")
    print("  LES_DEUX   = les deux effets contribuent (plateau sur-déterminé).")
    print("  ⚠️ Le test (B) est CORRÉLATIONNEL : les états basse-énergie sont peuplés par des agents "
          "qui ont DÉJÀ erré -> causalité inverse non exclue. Le test (A) est propre (états imposés "
          "par l'oracle, aucune sélection par le comportement du génome).")
    return {"coverage": cov, "precision": prec, "verdict": verdict, "genome_path": genome_path,
            "cov_gap": cov_gap, "prec_gap": prec_gap, "early_acc": early_acc,
            "late_acc": late_acc, "low_e_acc": low_e_acc, "high_e_acc": high_e_acc}


def main():
    seed = int(os.environ.get("WARM_SEED", "2026"))
    generations = int(os.environ.get("WARM_GEN", "50"))
    pop_size = int(os.environ.get("WARM_POP", "24"))
    n_epochs = int(os.environ.get("WARM_EPOCHS", "200"))
    lr = float(os.environ.get("WARM_LR", "0.5"))
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
                                       max_ticks=200, metab=metab, cog=cog, lr=lr)
    if imi is None:
        vi = None
        print("WARM-001 : SKIP (torch absent)")
    else:
        # Sonde décisive du MÉCANISME : accuracy enseignant (in-sample) vs on-policy (états auto-visités).
        acc_onpolicy = _inworld_accuracy(imi["learned_genome"], seed=seed, num_agents=max(12, K),
                                         metab=metab, cog=cog)
        print(f"WARM-001 imitation : loss {imi['loss_trend'][0]:.3f} -> {imi['loss_trend'][-1]:.3f} "
              f"| acc_enseignant={imi['imit_acc']:.3f} | acc_on-policy={acc_onpolicy:.3f}")
        vi = verdict_demand_marker(imi["learned_genome"], backend="torch", seed=seed, K=K,
                                   metab=metab, cog=cog)
        print(f"WARM-001 verdict (torch) : ratio={vi['ratio']:.2f} intact={vi['intact_survival']:.1f} "
              f"ablé={vi['ablated_survival']:.1f} -> {vi['verdict']} (n={vi['n']})")

    def _pass(v):
        # PASS = perception causalement portée (marqueur) ET survie ≥ mi-chemin de l'oracle (pas juste
        # « un peu > plancher ») : un suiveur qui utilise la perception SANS survivre n'est pas un succès.
        return (bool(v) and v["verdict"] == "PERCEPTION_DEMANDED"
                and v["intact_survival"] >= 0.5 * ORACLE_REF)

    print(f"\nSynthèse (PASS = marqueur PERCEPTION_DEMANDED ET survie intacte ≥ {0.5*ORACLE_REF:.0f} "
          f"= mi-chemin oracle) :")
    print(f"  WARM-002 évolution W-only : {'PASS' if _pass(ve) else 'FAIL'}")
    print(f"  WARM-001 imitation BPTT   : {'PASS' if _pass(vi) else ('SKIP' if vi is None else 'FAIL')}")
    print("-> Interpréter : un PASS où le REINFORCE froid échoue = le verrou était le chemin de crédit "
          "de CET optimiseur. Deux FAIL = verrou plus profond. Si (WARM-001) acc_enseignant haute MAIS "
          "acc_on-policy s'effondre -> la carte ne tient pas hors de la distribution de l'oracle (dérive "
          "de l'état récurrent). Rédiger EDR-WARM-001/002 + MàJ REF-DEMAND-MARKER.")

    dagger_rounds = int(os.environ.get("WARM_DAGGER_ROUNDS", "0"))
    if dagger_rounds > 0:
        dg = run_dagger_warmstart(seed=seed, rounds=dagger_rounds, lr=lr, num_agents=max(12, K),
                                  K=K, metab=metab, cog=cog)
        if dg is not None:
            print(f"\nWARM-003 DAgger : acc_on-policy par round = "
                  f"{[round(a, 3) for a in dg['trend_onpolicy_acc']]}")
            print(f"WARM-003 DAgger : survie par round = {[round(s, 1) for s in dg['trend_survival']]}")
            fv = dg["final_verdict"]
            print(f"WARM-003 verdict final (torch) : ratio={fv['ratio']:.2f} "
                  f"intact={fv['intact_survival']:.1f} ablé={fv['ablated_survival']:.1f} -> {fv['verdict']}")
            print(f"WARM-003 : {'PASS' if (fv['verdict']=='PERCEPTION_DEMANDED' and fv['intact_survival']>=0.5*ORACLE_REF) else 'FAIL'} "
                  f"(vs WARM-001 point de départ : acc_on-policy~0.73, survie~15)")
    return {"evo": evo["trend"], "warm002": ve, "warm001": vi}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()
