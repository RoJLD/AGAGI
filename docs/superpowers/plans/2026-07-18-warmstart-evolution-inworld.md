# WARM-001 / WARM-002 — Deux optimiseurs contre le verrou crédit in-world — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tester si deux optimiseurs NON-REINFORCE-froid (imitation BPTT récurrente ; évolution W-only) installent un suiveur-de-signal in-world qui PASSE le témoin within-subject (marqueur + survie), là où le REINFORCE froid restait au plancher.

**Architecture:** Un nouvel outil `tools/warmstart_evolution_inworld.py` (deux expériences + verdict partagé) ; une méthode additive `imitate_episode_bptt` dans `src/agents/backend_torch.py`. Réutilise sans les modifier : `s2_demand.run_condition`, `s2_demand_ablation.{derange_rows,PerceptionAblatedMamba}`, `demand_marker.ablation_verdict`, `cognitive_demand_inworld.CognitiveOracleBatchModel`, `world_1_stoneage.Biosphere3D`, `backend.make_population`.

**Tech Stack:** Python 3, numpy (WARM-002 pur numpy), PyTorch (WARM-001, dépendance optionnelle `requirements-torch.txt`), pytest.

## Global Constraints

- Régime monde partagé (verbatim S2-009) : `cognitive_demand=True`, `base_metabolism=0.75`, `cog_gain=12.0`, `forage_payoff=0.0`, `benchmark_mode=True`, `night_enabled=False`, `current_era=10_000`. Repères : plancher no-perception ≈ 7 ; oracle intact ≈ 200.
- Flag monde `cognitive_demand` reste OFF par défaut (non-régressif ; déjà couvert S2-009 3/3 + 10/10). NE PAS modifier `world_1_stoneage.py` dans ce plan.
- NE PAS modifier les outils partagés : `tools/s2_demand.py`, `tools/demand_marker.py`, `tools/s2_demand_ablation.py`, `src/seed_ai/mutation.py` (la mutation W-only est LOCALE à l'outil). NE PAS toucher `compute_ab_verdict`.
- `imitate_episode_bptt` est ADDITIVE : ne modifie NI `forward`, NI `learn`, NI `learn_episode`, NI `learn_episode_bptt`.
- Anti-non-repro KuzuDB : `env.memory_retriever.stop()` après chaque boucle sim (mémoire `biosphere-ambient-memory-nonrepro`).
- Garde-fou petit-n : pas de verdict POSITIF sous n=12 ; les verdicts finaux tournent à K ≥ 12 (mémoire `power-evaporation-guardrail`).
- Torch absent → WARM-001 skip proprement (message) ; WARM-002 (numpy) reste exécutable. Tests torch : `pytest.importorskip("torch")`.
- **Commits** : la règle projet interdit tout commit sans demande explicite de robla. Les étapes « Commit » ci-dessous sont préparées mais NE SONT EXÉCUTÉES qu'après feu vert explicite ; sinon, empiler les changements et demander.
- Indices obs (world_1_stoneage `get_batch_observations`) : `bit_a=12`, `bit_b=13` ; `correct_dir = 2*(bit_a>0)+(bit_b>0)` ; move logits = `out[:, :8]` (0=N,1=S,2=E,3=W). `num_inputs=59`, `num_outputs=108`, `num_nodes=172` (MambaAgent défaut).

---

### Task 1 : `imitate_episode_bptt` — imitation récurrente supervisée (BPTT) dans le backend torch

**Files:**
- Modify: `src/agents/backend_torch.py` (ajouter une méthode après `learn_episode_bptt`, ~ligne 242)
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py` (créer)

**Interfaces:**
- Consumes : `TorchPopulationModel` (existant : `self.B/N/O/I`, `self._step`, `self.opt`, `self._write_back`, constante `_MOVE_LOGITS=8`).
- Produces : `TorchPopulationModel.imitate_episode_bptt(obs_seq, target_moves_seq, truncate_window=None) -> float` — obs_seq = liste de (B, ≥I) ; target_moves_seq = liste de (B,) entiers ∈ [0,8) ; renvoie la perte cross-entropy moyenne. RETIENT le graphe récurrent (BPTT) sauf détachement périodique par `truncate_window`.

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/sandbox/test_warmstart_evolution_inworld.py` :

```python
"""Tests WARM-001/WARM-002 — imitation BPTT récurrente + évolution in-world W-only + verdict partagé."""
import os, sys
import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=0):
    """Construit un TorchPopulationModel minimal sur des agents jouets (Genome réel, petit N)."""
    torch = pytest.importorskip("torch")
    from src.seed_ai.mutation import Genome
    from src.agents.backend_torch import TorchPopulationModel
    rng = np.random.RandomState(seed)

    class _A:
        def __init__(self, g): self.genome = g
    agents = []
    for _ in range(B):
        W = (rng.randn(N, N) * 0.1).astype(np.float32)
        agents.append(_A(Genome(W, num_inputs=I, num_outputs=O)))
    return TorchPopulationModel(agents, lr=0.2)


def test_imitate_episode_bptt_reduces_loss_and_learns_separable_map():
    pytest.importorskip("torch")
    pop = _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=1)
    rng = np.random.RandomState(2)
    # Tâche jouet séparable : le signe de obs[:,0] -> cible 0 (négatif) ou 3 (positif).
    T = 6
    obs_seq, tgt_seq = [], []
    for _ in range(T):
        s = rng.choice([-1.0, 1.0], size=4).astype(np.float32)
        obs = np.zeros((4, 2), dtype=np.float32); obs[:, 0] = s
        obs_seq.append(obs)
        tgt_seq.append(np.where(s > 0, 3, 0).astype(int))
    first = pop.imitate_episode_bptt(obs_seq, tgt_seq)
    for _ in range(60):
        last = pop.imitate_episode_bptt(obs_seq, tgt_seq)
    assert last < first, f"la perte d'imitation devrait décroître ({first:.3f} -> {last:.3f})"
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_imitate_episode_bptt_reduces_loss_and_learns_separable_map -v`
Expected: FAIL — `AttributeError: 'TorchPopulationModel' object has no attribute 'imitate_episode_bptt'`

- [ ] **Step 3 : Implémenter la méthode (additive)**

Dans `src/agents/backend_torch.py`, insérer APRÈS la fin de `learn_episode_bptt` (après la ligne `return float(loss.item())`, ~l.242) et AVANT `def learn_episode` :

```python
    def imitate_episode_bptt(self, obs_seq, target_moves_seq, truncate_window=None):
        """IMITATION récurrente supervisée (BPTT) — distincte de learn_episode_bptt (REINFORCE par le
        retour). Rejoue obs_seq depuis H=0 en RETENANT le graphe récurrent ; perte = cross-entropy des
        move-logits (out[:, :8]) vs l'action-enseignant par pas ; backprop unique à travers la fenêtre
        -> _write_back. Matcher le forward RÉCURRENT du monde (pas _step isolé) sur la distribution
        d'obs RÉELLE (attaque le shift qui a tué le BC single-step). ADDITIF : ne touche NI forward NI
        learn NI learn_episode NI learn_episode_bptt.

        obs_seq : liste de (B, >=I) ; target_moves_seq : liste de (B,) entiers dans [0, 8).
        truncate_window=W : détache H tous les W pas (stabilité gradient longue fenêtre ; la tâche
        réactive n'exige pas le crédit pleine-fenêtre). Renvoie la perte moyenne (float)."""
        if self.B == 0 or not obs_seq:
            return None
        F = torch.nn.functional
        H = torch.zeros((self.B, self.N), device=self.device)
        loss = torch.zeros((), device=self.device)
        nsteps = 0
        for t, obs in enumerate(obs_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :self.I], device=self.device)
            if truncate_window and t > 0 and (t % truncate_window == 0):
                H = H.detach()
            H = self._step(obs_t, H)                              # graphe retenu (BPTT)
            out = H[:, self.N - self.O:self.N]
            move_logits = out[:, :_MOVE_LOGITS]                  # (B, 8)
            tgt = torch.tensor(np.asarray(target_moves_seq[t]), dtype=torch.long, device=self.device)
            loss = loss + F.cross_entropy(move_logits, tgt)
            nsteps += 1
        loss = loss / max(1, nsteps)
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self._write_back()
        return float(loss.item())
```

- [ ] **Step 4 : Lancer le test, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_imitate_episode_bptt_reduces_loss_and_learns_separable_map -v`
Expected: PASS

- [ ] **Step 5 : Non-régression torch (additivité)**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py tests/sandbox/test_agent_backend_torch.py -v`
Expected: PASS (suite torch existante inchangée)

- [ ] **Step 6 : Commit (après feu vert robla — voir Global Constraints)**

```bash
git add src/agents/backend_torch.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-001): imitate_episode_bptt (imitation récurrente supervisée, additive)"
```

---

### Task 2 : `verdict_demand_marker` — témoin within-subject (marqueur + survie) sur un génome, forward-consistant

**Files:**
- Create: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py` (ajouter)

**Interfaces:**
- Consumes : `run_condition`, `derange_rows`, `PerceptionAblatedMamba` (s2_demand_ablation) ; `ablation_verdict` (demand_marker) ; `Biosphere3D` ; `make_population`, `TorchPopulationModel` ; `Genome`, `MambaAgent`.
- Produces :
  - `make_cog_world(metab=0.75, cog=12.0) -> callable` (zero-arg → env `cognitive_demand` configuré).
  - `verdict_demand_marker(genome, backend, seed=2026, K=12, num_agents=12, max_ticks=200, metab=0.75, cog=12.0) -> dict{ratio, verdict, n, intact_survival, ablated_survival}`. `backend in {"mamba","torch"}`. PASS = `verdict == "PERCEPTION_DEMANDED"` ET `intact_survival` ≫ plancher.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à `tests/sandbox/test_warmstart_evolution_inworld.py` :

```python
def test_verdict_demand_marker_random_genome_is_neutral_and_wellformed():
    from tools.warmstart_evolution_inworld import verdict_demand_marker
    from src.agents.mamba_agent import MambaAgent
    g = MambaAgent().genome                         # génome aléatoire (non-suiveur)
    r = verdict_demand_marker(g, backend="mamba", seed=2026, K=2,
                              num_agents=4, max_ticks=20)
    assert set(r) >= {"ratio", "verdict", "n", "intact_survival", "ablated_survival"}
    assert r["verdict"] in ("PERCEPTION_DEMANDED", "NEUTRAL", "INCONCLUSIVE")
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_verdict_demand_marker_random_genome_is_neutral_and_wellformed -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.warmstart_evolution_inworld'`

- [ ] **Step 3 : Créer l'outil avec l'en-tête, `make_cog_world`, le chemin mamba et torch du verdict**

Créer `tools/warmstart_evolution_inworld.py` :

```python
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
```

- [ ] **Step 4 : Lancer le test, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_verdict_demand_marker_random_genome_is_neutral_and_wellformed -v`
Expected: PASS

- [ ] **Step 5 : Commit (après feu vert robla)**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM): verdict_demand_marker (témoin within-subject forward-consistant)"
```

---

### Task 3 : WARM-002 — évolution in-world W-only (`run_inworld_evolution`)

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py` (ajouter)

**Interfaces:**
- Consumes : `make_cog_world` (Task 2), `Biosphere3D`, `MambaAgent`, `Genome.clone`, `seed_at`.
- Produces :
  - `_mutate_W_only(genome, power, rate=0.8, rng=None) -> None` (mute EN PLACE les entrées non-nulles de `genome.W` ; ne touche PAS W_router/bytecode → comparaison propre au gradient).
  - `_eval_generation(genomes, seed, era_idx, max_ticks, metab, cog) -> list[int]` (âges alignés sur `genomes`).
  - `run_inworld_evolution(seed=2026, generations=50, pop_size=24, survival_frac=0.25, mut_power=0.15, max_ticks=200, metab=0.75, cog=12.0) -> dict{trend, best_genome, best_age}`.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter au test :

```python
def test_run_inworld_evolution_smoke_returns_trend_and_best():
    from tools.warmstart_evolution_inworld import run_inworld_evolution
    from src.seed_ai.mutation import Genome
    out = run_inworld_evolution(seed=2026, generations=2, pop_size=6, survival_frac=0.34,
                                mut_power=0.2, max_ticks=15)
    assert len(out["trend"]) == 2
    assert isinstance(out["best_genome"], Genome)
    assert out["best_age"] >= 0


def test_mutate_w_only_changes_W_not_router():
    from tools.warmstart_evolution_inworld import _mutate_W_only
    from src.agents.mamba_agent import MambaAgent
    g = MambaAgent().genome
    W0 = g.W.copy()
    router0 = None if g.W_router is None else g.W_router.copy()
    _mutate_W_only(g, power=0.5, rng=np.random.RandomState(0))
    assert not np.allclose(g.W, W0), "W devrait changer"
    if router0 is not None:
        assert np.allclose(g.W_router, router0), "W_router ne doit PAS changer (comparaison propre au gradient)"
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_run_inworld_evolution_smoke_returns_trend_and_best tests/sandbox/test_warmstart_evolution_inworld.py::test_mutate_w_only_changes_W_not_router -v`
Expected: FAIL — `ImportError: cannot import name 'run_inworld_evolution'`

- [ ] **Step 3 : Implémenter dans `tools/warmstart_evolution_inworld.py`**

Ajouter à la fin du fichier :

```python
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
    agents = []
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        e.add_agent(a, energy=80.0)
        agents.append(a)
    t = 0
    while e.agents and t < max_ticks:
        e.step()
        t += 1
    ages_by_id = {a["id"]: int(a["age"])
                  for a in list(e.agents) + list(getattr(e, "dead_agents", []))}
    if hasattr(e, "memory_retriever"):
        e.memory_retriever.stop()
    return [ages_by_id.get(a["id"], 0) for a in agents]


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
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_run_inworld_evolution_smoke_returns_trend_and_best tests/sandbox/test_warmstart_evolution_inworld.py::test_mutate_w_only_changes_W_not_router -v`
Expected: PASS

- [ ] **Step 5 : Commit (après feu vert robla)**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-002): évolution in-world W-only (hill-climb sur genome.W pour la survie)"
```

---

### Task 4 : WARM-001 — imitation BPTT sur trajectoire-enseignant (`run_bptt_imitation_warmstart`)

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py` (ajouter)

**Interfaces:**
- Consumes : `imitate_episode_bptt` (Task 1), `make_cog_world` (Task 2), `run_condition`, `CognitiveOracleBatchModel` + `BIT_A/BIT_B` (cognitive_demand_inworld), `make_population`, `MambaAgent`.
- Produces :
  - `RecordingOracleBatchModel(CognitiveOracleBatchModel)` (enregistre par tick obs + label oracle en attributs de classe `RECORDED_OBS`, `RECORDED_TGT`).
  - `_collect_oracle_trajectory(seed, num_agents, max_ticks, metab, cog) -> (obs_seq, tgt_seq)` (à B constant : garde le préfixe où toutes les lignes sont présentes).
  - `run_bptt_imitation_warmstart(seed=2026, num_agents=12, n_epochs=200, truncate_window=25, max_ticks=200, metab=0.75, cog=12.0) -> dict{learned_genome, loss_trend, imit_acc}` — renvoie None si torch absent.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter au test :

```python
def test_collect_oracle_trajectory_shapes():
    from tools.warmstart_evolution_inworld import _collect_oracle_trajectory
    obs_seq, tgt_seq = _collect_oracle_trajectory(seed=2026, num_agents=4, max_ticks=8,
                                                  metab=0.75, cog=12.0)
    assert len(obs_seq) == len(tgt_seq) and len(obs_seq) >= 1
    assert obs_seq[0].shape[0] == 4 and obs_seq[0].shape[1] >= 14      # B=4, >= colonnes bit_a/bit_b
    assert tgt_seq[0].shape[0] == 4 and tgt_seq[0].max() < 8


def test_run_bptt_imitation_warmstart_smoke_reduces_loss():
    pytest.importorskip("torch")
    from tools.warmstart_evolution_inworld import run_bptt_imitation_warmstart
    from src.seed_ai.mutation import Genome
    out = run_bptt_imitation_warmstart(seed=2026, num_agents=4, n_epochs=8,
                                       truncate_window=10, max_ticks=12)
    assert isinstance(out["learned_genome"], Genome)
    assert out["loss_trend"][-1] <= out["loss_trend"][0]
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_collect_oracle_trajectory_shapes tests/sandbox/test_warmstart_evolution_inworld.py::test_run_bptt_imitation_warmstart_smoke_reduces_loss -v`
Expected: FAIL — `ImportError: cannot import name '_collect_oracle_trajectory'`

- [ ] **Step 3 : Implémenter dans `tools/warmstart_evolution_inworld.py`**

Ajouter en haut du fichier, sous les imports existants :

```python
from tools.cognitive_demand_inworld import CognitiveOracleBatchModel, BIT_A, BIT_B
```

Puis ajouter à la fin du fichier :

```python
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
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_collect_oracle_trajectory_shapes tests/sandbox/test_warmstart_evolution_inworld.py::test_run_bptt_imitation_warmstart_smoke_reduces_loss -v`
Expected: PASS

- [ ] **Step 5 : Commit (après feu vert robla)**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-001): imitation BPTT récurrente sur trajectoire-enseignant + collecte oracle"
```

---

### Task 5 : `main()` — orchestration + synthèse comparée (les deux optimiseurs vs REINFORCE froid vs oracle)

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`

**Interfaces:**
- Consumes : `run_inworld_evolution` (Task 3), `run_bptt_imitation_warmstart` (Task 4), `verdict_demand_marker` (Task 2).
- Produces : `main() -> dict` (imprime les traces + verdicts marqueur+survie des deux expériences, avec repères plancher/oracle).

- [ ] **Step 1 : Implémenter `main()` et le point d'entrée**

Ajouter à la fin de `tools/warmstart_evolution_inworld.py` :

```python
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
```

- [ ] **Step 2 : Smoke du point d'entrée à budget minuscule**

Run: `WARM_GEN=2 WARM_POP=6 WARM_EPOCHS=5 WARM_K=2 python tools/warmstart_evolution_inworld.py`
Expected: s'exécute sans exception ; imprime les deux traces + deux verdicts (ou WARM-001 SKIP si torch absent) + la synthèse.

- [ ] **Step 3 : Suite de tests complète du fichier**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py -v`
Expected: PASS (tous ; ceux marqués torch skip proprement si torch absent)

- [ ] **Step 4 : Commit (après feu vert robla)**

```bash
git add tools/warmstart_evolution_inworld.py
git commit -m "feat(WARM): main() orchestration + synthèse comparée des deux optimiseurs"
```

---

### Task 6 : Run à budget modéré + records (EDR-WARM-001/002 + MàJ REF-DEMAND-MARKER + mémoire)

**Files:**
- Create: `docs/EDR/WARM-001_BPTT_Imitation_Warmstart_InWorld.md`, `docs/EDR/WARM-002_InWorld_Evolution_WOnly.md`
- Modify: `docs/REF/REF-DEMAND-MARKER.md` (ligne `adopt_for` + une ligne de table par verdict), `C:\Users\robla\.claude\projects\c--Users-robla-VScode-Project-AGAGI\memory\within-subject-demand-marker.md` (+ `MEMORY.md`)

**Interfaces:**
- Consumes : le CLI de Task 5 à budget modéré.

- [ ] **Step 1 : Run modéré (WARM-002 d'abord — numpy pur, toujours exécutable)**

Run: `WARM_GEN=50 WARM_POP=24 WARM_K=12 python tools/warmstart_evolution_inworld.py`
Expected: trace évolution (croissante ou plate), verdict WARM-002 (mamba), et — si torch présent — verdict WARM-001 (torch). Noter durée (attendu : minutes–dizaines de min).

- [ ] **Step 2 : Consigner les verdicts bruts**

Copier la sortie console (traces + ratios + verdicts + synthèse PASS/FAIL) dans le scratchpad pour la rédaction.

- [ ] **Step 3 : Rédiger EDR-WARM-002** (`gate: G0`, `adopts: [REF-DEMAND-MARKER]`, frontmatter conforme aux règles records-graph : `tests: [SDR-G0]`, liens `[[...]]`). Contenu : question, méthode (évolution W-only, régime S2-009), résultats (trend + verdict marqueur+survie), verdict (PASS/FAIL) + interprétation (verrou = chemin de crédit gradient vs plus profond), portée/limites (budget modéré, W-only). Converge `[[decisive-substrate-thesis-test]]`, `[[warm-start-transversal-law]]`.

- [ ] **Step 4 : Rédiger EDR-WARM-001** (idem ; méthode = imitation BPTT récurrente sur trajectoire-enseignant, forward torch ; souligner : teacher parfait → un échec de transfert = installation par gradient récurrent, pas découverte).

- [ ] **Step 5 : Mettre à jour REF-DEMAND-MARKER** : ajouter `EDR-WARM-001, EDR-WARM-002` à `adopt_for` + deux lignes de table (modalité « recette IN-WORLD optimisée »).

- [ ] **Step 6 : Mettre à jour la mémoire** `within-subject-demand-marker.md` (résultat des deux leviers, PASS/FAIL, conclusion sur le verrou) + pointeur `MEMORY.md` si nécessaire.

- [ ] **Step 7 : Commit (après feu vert robla)**

```bash
git add docs/EDR/WARM-001_BPTT_Imitation_Warmstart_InWorld.md docs/EDR/WARM-002_InWorld_Evolution_WOnly.md docs/REF/REF-DEMAND-MARKER.md
git commit -m "docs(WARM): EDR-WARM-001/002 (deux optimiseurs vs verrou crédit) + MàJ REF-DEMAND-MARKER"
```

---

## Self-Review

**1. Couverture du spec**
- Régime monde partagé → Global Constraints + `make_cog_world` (Task 2). ✓
- Critère marqueur + survie → `verdict_demand_marker` + `_pass` (Task 2/5). ✓
- WARM-001 imitation BPTT récurrente (trajectoire-enseignant, finding réactif) → Task 1 + Task 4. ✓
- WARM-002 évolution W-only (mutate W seul, pas W_router) → Task 3 (`_mutate_W_only` + test router inchangé). ✓
- Consistance du forward (torch pour WARM-001, mamba pour WARM-002) → `verdict_demand_marker(backend=...)` (Task 2). ✓
- Cadrage décisif (même W-space) → EDR interprétation (Task 6). ✓
- Non-régression (flag OFF, additivité) → Task 1 Step 5 + Global Constraints. ✓
- Garde-fou petit-n → K défaut 12 (Task 5), tests en mini-K explicitement smoke. ✓
- Anti-non-repro KuzuDB → `memory_retriever.stop()` dans chaque helper d'épisode. ✓
- Follow-up DAgger documenté → spec (non implémenté ici, conforme à « modéré »). ✓

**2. Placeholders** : aucun « TBD/TODO/handle edge cases » ; tout le code est fourni. Task 6 (rédaction EDR) décrit le contenu exigé, pas du code — c'est une tâche d'analyse, acceptable.

**3. Cohérence des types** : `verdict_demand_marker` renvoie partout `{ratio, verdict, n, intact_survival, ablated_survival}` (Task 2 def = Task 5 usage). `run_inworld_evolution` → `{trend, best_genome, best_age}` (Task 3 def = Task 5 usage). `run_bptt_imitation_warmstart` → `{learned_genome, loss_trend, imit_acc}` ou None (Task 4 def = Task 5 usage). `imitate_episode_bptt(obs_seq, target_moves_seq, truncate_window)` (Task 1 def = Task 4 usage). Cohérent.
