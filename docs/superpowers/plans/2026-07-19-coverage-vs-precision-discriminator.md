# WARM-004 — Discriminateur couverture vs précision — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Trancher l'hypothèse ouverte d'EDR-WARM-003 (pourquoi DAgger plafonne à 35 ticks malgré acc 0.99) via deux mesures : (A) accuracy sur les états TARDIFS de l'oracle (couverture) et (B) accuracy binnée par énergie sur le rollout du learner (précision).

**Architecture:** Extension additive de `tools/warmstart_evolution_inworld.py` : un collecteur de diagnostic pleine-longueur/masqué/avec-énergie, un évaluateur d'accuracy par bin (replay pur torch, sans monde), deux fabriques de bins, et un driver.

**Tech Stack:** Python 3, numpy, PyTorch, pytest.

## Global Constraints

- Régime S2-009 verbatim : `cognitive_demand=True`, `base_metabolism=0.75`, `cog_gain=12.0`, `forage_payoff=0.0`, `benchmark_mode=True`, `night_enabled=False`, `current_era=10_000`.
- TOUT est ADDITIF : ne modifie AUCUNE fonction existante de `tools/warmstart_evolution_inworld.py` ni de `src/agents/backend_torch.py`. La suite WARM existante (9 tests) doit rester verte.
- NE PAS modifier les outils partagés (`s2_demand`, `demand_marker`, `s2_demand_ablation`, `mutation`, `world_1_stoneage`).
- Alignement à travers les morts par `id(model)` (les objets-modèles persistent aux reconstructions de pop / ré-instanciations du batch model). Morts → obs 0 / tgt 0 / mask 0 / énergie NaN.
- Énergie lue DANS `forward` depuis l'env (closure), donc à l'instant de la DÉCISION (avant résolution biologique). NE PAS deviner une colonne d'obs.
- W GELÉ partout (lr=0 ; patch `make_population` restauré en `finally`). `memory_retriever.stop()` après chaque collecte.
- Étiquette oracle = `2*(bit_a>0)+(bit_b>0)`, `BIT_A=12`/`BIT_B=13`, move logits = `out[:, :8]`.
- torch absent → skip propre. Commits par tâche APPROUVÉS (path-scopés) ; push = aval robla.

---

### Task 1 : `_collect_diag_trajectory` — collecteur pleine-longueur, masqué, avec énergie, 2 pilotes

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py` (ajouter APRÈS `_collect_onpolicy_trajectory`)
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py` (ajouter)

**Interfaces:**
- Produces : `_collect_diag_trajectory(driver, genome=None, seed=2026, num_agents=12, max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT) -> (obs_seq, tgt_seq, mask_seq, energy_seq)`. `driver ∈ {"oracle","genome"}`. Listes alignées fixed-B=num_agents. PLEINE longueur (pas de troncature à la 1ʳᵉ mort) — c'est ce qui donne les états TARDIFS de l'oracle.

- [ ] **Step 1 : Écrire le test qui échoue**

```python
def test_collect_diag_trajectory_oracle_is_long_and_masked():
    from tools.warmstart_evolution_inworld import _collect_diag_trajectory
    pytest.importorskip("torch")
    obs, tgt, mask, en = _collect_diag_trajectory("oracle", seed=2026, num_agents=4, max_ticks=60)
    assert len(obs) == len(tgt) == len(mask) == len(en) >= 1
    assert obs[0].shape[0] == 4 and obs[0].shape[1] >= 14
    assert set(np.unique(mask[0])).issubset({0.0, 1.0})
    alive0 = mask[0] > 0
    assert np.all(np.isfinite(en[0][alive0])), "énergie finie là où mask=1"


def test_collect_diag_trajectory_genome_runs():
    from tools.warmstart_evolution_inworld import _collect_diag_trajectory
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    g = MambaAgent().genome
    obs, tgt, mask, en = _collect_diag_trajectory("genome", genome=g, seed=2026,
                                                 num_agents=4, max_ticks=15)
    assert len(obs) >= 1 and obs[0].shape[0] == 4
    assert mask[0].sum() == 4.0
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_collect_diag_trajectory_oracle_is_long_and_masked -v`
Expected: FAIL — ImportError `_collect_diag_trajectory`.

- [ ] **Step 3 : Implémenter** (ajouter dans `tools/warmstart_evolution_inworld.py`)

```python
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
    else:
        e.batch_model_cls = _RecOracle

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
```

- [ ] **Step 4 : Lancer les deux tests + la suite**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py -v`
Expected: PASS (2 nouveaux + 9 existants inchangés).

- [ ] **Step 5 : Commit**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-004): _collect_diag_trajectory (pleine longueur, masqué, énergie, 2 pilotes)"
```

---

### Task 2 : `accuracy_binned` + fabriques de bins (replay pur torch)

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py`

**Interfaces:**
- Produces :
  - `bins_by_tick(mask_seq, edges) -> list[np.ndarray]` (bin par tick, -1 hors bornes)
  - `bins_by_energy(energy_seq, edges) -> list[np.ndarray]` (bin par énergie, NaN → -1)
  - `accuracy_binned(genome, obs_seq, tgt_seq, mask_seq, bin_ids, n_bins, num_agents=12) -> list[dict{bin,n,acc}]` (replay torch no_grad, W gelé, SANS monde)

- [ ] **Step 1 : Écrire le test qui échoue**

```python
def test_bins_and_accuracy_binned_random_genome_is_chance():
    from tools.warmstart_evolution_inworld import (_collect_diag_trajectory, bins_by_tick,
                                                   accuracy_binned)
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    obs, tgt, mask, en = _collect_diag_trajectory("oracle", seed=2026, num_agents=4, max_ticks=30)
    edges = [0, 10, 1000]
    bids = bins_by_tick(mask, edges)
    assert len(bids) == len(mask) and bids[0].shape == (4,)
    res = accuracy_binned(MambaAgent().genome, obs, tgt, mask, bids, n_bins=2, num_agents=4)
    assert len(res) == 2
    peupled = [r for r in res if r["n"] > 0]
    assert peupled, "au moins un bin peuplé"
    for r in peupled:
        assert 0.0 <= r["acc"] <= 1.0
    # contrôle négatif : un génome aléatoire ne doit pas être excellent partout
    assert min(r["acc"] for r in peupled) < 0.9


def test_bins_by_energy_maps_nan_to_minus_one():
    from tools.warmstart_evolution_inworld import bins_by_energy
    en = [np.array([10.0, 50.0, np.nan, 95.0], dtype=np.float32)]
    b = bins_by_energy(en, [0, 40, 80, 101])
    assert b[0].tolist() == [0, 1, -1, 2]
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_bins_by_energy_maps_nan_to_minus_one -v`
Expected: FAIL — ImportError `bins_by_energy`.

- [ ] **Step 3 : Implémenter**

```python
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


def accuracy_binned(genome, obs_seq, tgt_seq, mask_seq, bin_ids, n_bins, num_agents=12):
    """Rejoue `genome` (forward torch, no_grad, W gelé, replay PUR sans monde) sur obs_seq depuis H=0 et
    agrège l'accuracy de décision par bin. Ignore mask==0 et bin<0. Renvoie [{bin,n,acc}]. None si torch
    absent. NB : sur une trajectoire d'un AUTRE pilote (ex. l'oracle), H suit l'historique de CE pilote —
    contrefactuel voulu (« s'il se trouvait dans ces états, déciderait-il juste ? »)."""
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
```

- [ ] **Step 4 : Lancer, vérifier le succès + suite complète**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py -v`
Expected: PASS (tous).

- [ ] **Step 5 : Commit**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-004): accuracy_binned + bins_by_tick/bins_by_energy (replay pur torch)"
```

---

### Task 3 : `run_coverage_precision_diagnostic` — driver + persistance du génome

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py`

**Interfaces:**
- Produces : `run_coverage_precision_diagnostic(seed=2026, rounds=6, epochs_per_round=3000, lr=0.5, num_agents=12, max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT, K=12, genome_path="results/warm003_dagger_genome.npz") -> dict{coverage, precision, verdict, genome_path}` ou None si torch absent.

- [ ] **Step 1 : Écrire le test qui échoue**

```python
def test_run_coverage_precision_diagnostic_smoke(tmp_path):
    from tools.warmstart_evolution_inworld import run_coverage_precision_diagnostic
    pytest.importorskip("torch")
    out = run_coverage_precision_diagnostic(seed=2026, rounds=1, epochs_per_round=4, lr=0.5,
                                            num_agents=4, max_ticks=12, K=2,
                                            genome_path=str(tmp_path / "g.npz"))
    assert "coverage" in out and "precision" in out and "verdict" in out
    assert isinstance(out["coverage"], list) and isinstance(out["precision"], list)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_run_coverage_precision_diagnostic_smoke -v`
Expected: FAIL — ImportError.

- [ ] **Step 3 : Implémenter**

```python
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

    late_acc, low_e_acc = _late(cov), _low(prec)
    early_acc = cov[0]["acc"] if cov and cov[0]["n"] > 0 else float("nan")
    if late_acc == late_acc and late_acc < 0.6:
        verdict = "COUVERTURE"
    elif low_e_acc == low_e_acc and late_acc == late_acc and low_e_acc < late_acc - 0.15:
        verdict = "PRECISION"
    else:
        verdict = "NI_COUVERTURE_NI_PRECISION"

    print(f"\n=== WARM-004 — couverture vs précision (seed={seed}) ===")
    print(f"(A) COUVERTURE — acc du génome sur les états de l'ORACLE, par bin de tick {TICK_EDGES[:-1]}+ :")
    for r in cov:
        print(f"    bin {r['bin']} (ticks {TICK_EDGES[r['bin']]}-{TICK_EDGES[r['bin']+1]}) : "
              f"n={r['n']:5d} acc={r['acc']:.3f}")
    print(f"(B) PRÉCISION — acc sur son propre rollout, par bin d'énergie {ENERGY_EDGES[:-1]}+ :")
    for r in prec:
        print(f"    bin {r['bin']} (énergie {ENERGY_EDGES[r['bin']]}-{ENERGY_EDGES[r['bin']+1]}) : "
              f"n={r['n']:5d} acc={r['acc']:.3f}")
    print(f"\nacc early(oracle ≤35)={early_acc:.3f} | acc late(oracle >35)={late_acc:.3f} | "
          f"acc basse-énergie={low_e_acc:.3f}")
    print(f"VERDICT WARM-004 : {verdict}")
    print("  COUVERTURE = il ne sait pas hors de son vécu (le plateau est un mur de données).")
    print("  PRECISION  = il sait partout mais rate aux états critiques.")
    print("  NI_L'UN_NI_L'AUTRE = cause non-décisionnelle (dynamique métabolique) -> chercher ailleurs.")
    return {"coverage": cov, "precision": prec, "verdict": verdict, "genome_path": genome_path}
```

- [ ] **Step 4 : Lancer le smoke + suite complète**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py -v`
Expected: PASS (tous).

- [ ] **Step 5 : Commit**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-004): run_coverage_precision_diagnostic (tests A+B) + persistance du génome DAgger"
```

---

### Task 4 : Run décisif + mise à jour des records

**Files:**
- Modify: `docs/EDR/WARM-003_DAgger_OnPolicy_Warmstart.md` (fermer l'hypothèse ouverte), `docs/REF/REF-DEMAND-MARKER.md`, mémoire `within-subject-demand-marker.md`

- [ ] **Step 1 : Run décisif** (contrôleur, en arrière-plan) : `run_coverage_precision_diagnostic(seed=2026, rounds=6, K=12)`. Noter les deux tables + le verdict.
- [ ] **Step 2 : Interpréter selon la table de décision** et METTRE À JOUR EDR-WARM-003 : remplacer « hypothèse OUVERTE (couverture vs précision) » par le mécanisme TRANCHÉ, avec les deux tables comme preuve. Si `NI_COUVERTURE_NI_PRECISION`, le dire franchement et pointer la piste non-décisionnelle.
- [ ] **Step 3 : MàJ REF-DEMAND-MARKER** (ligne WARM-003 : mécanisme désormais tranché) + mémoire.
- [ ] **Step 4 : Commit** (path-scopé).

---

## Self-Review

**1. Couverture du spec** : collecteur pleine-longueur/masqué/énergie 2-pilotes (Task 1) ✓ ; accuracy_binned + 2 fabriques de bins (Task 2) ✓ ; driver A+B + persistance génome + table de décision 4 cases (Task 3) ✓ ; run + records (Task 4) ✓ ; contrôle négatif génome aléatoire (Task 2 test) ✓ ; énergie lue depuis l'env au moment de la décision (Task 1) ✓ ; alignement id(model) (Task 1) ✓ ; W gelé + finally + memory_retriever.stop (Task 1) ✓.

**2. Placeholders** : aucun ; code complet fourni (Task 4 = analyse).

**3. Cohérence des types** : `_collect_diag_trajectory -> 4-uple` (Task 1) = usage Tasks 2/3 ; `bins_by_tick/bins_by_energy -> list[np.ndarray]` = usage `accuracy_binned(bin_ids=…)` ; `accuracy_binned -> list[{bin,n,acc}]` = usage driver (`r["n"]`, `r["acc"]`, `r["bin"]`). `TICK_EDGES`/`ENERGY_EDGES` définis Task 3 avant usage. `run_dagger_warmstart` (WARM-003) réutilisé tel quel.
