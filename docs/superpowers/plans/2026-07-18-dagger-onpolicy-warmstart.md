# WARM-003 — DAgger on-policy contre le plafond de transfert — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Tester si DAgger on-policy (entraîner sur les états que le learner visite lui-même, réétiquetés par l'oracle, en BPTT récurrent masqué) casse le plafond `acc_on-policy=0.734` de WARM-001 et fait décoller la survie.

**Architecture:** Extension de `tools/warmstart_evolution_inworld.py` (+ `mask_seq` additif dans `imitate_episode_bptt`). Réutilise make_cog_world, verdict_demand_marker, _inworld_accuracy, _collect_oracle_trajectory, _torch_survival_eras. NE modifie PAS les outils partagés.

**Tech Stack:** Python 3, numpy, PyTorch (installé), pytest.

## Global Constraints

- Régime S2-009 verbatim : cognitive_demand=True, base_metabolism=0.75, cog_gain=12.0, forage_payoff=0.0, benchmark_mode=True, night_enabled=False, current_era=10_000. Plancher ≈ 7, oracle ≈ 200, acc_on-policy WARM-001 ≈ 0.73.
- `imitate_episode_bptt(mask_seq=...)` STRICTEMENT additif : `mask_seq=None` → comportement inchangé (tests WARM-001 verts).
- W GELÉ pendant toute collecte on-policy (patch make_population restauré en `finally`). `memory_retriever.stop()` après chaque rollout.
- Alignement à travers les morts par `id(a["model"])` (les objets-modèles persistent aux reconstructions de pop).
- Réétiquetage oracle = `correct_dir = 2*(bit_a>0)+(bit_b>0)`, bit_a=12/bit_b=13, move logits = out[:, :8].
- Compute modéré : round-robin sur le dataset → `epochs_per_round × rounds` appels d'imitation bornés.
- Barre PASS = marqueur PERCEPTION_DEMANDED ET survie intacte ≥ 0.5·200 = 100 (K≥12).
- torch absent → WARM-003 skip propre.
- Commits par tâche : APPROUVÉS (path-scopés) ; push/PR/merge = aval robla explicite.

---

### Task 1 : `mask_seq` additif dans `imitate_episode_bptt`

**Files:**
- Modify: `src/agents/backend_torch.py` (méthode `imitate_episode_bptt`)
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py` (ajouter)

**Interfaces:**
- Produces : `imitate_episode_bptt(obs_seq, target_moves_seq, truncate_window=None, mask_seq=None) -> float`. `mask_seq` = liste de (B,) ∈ {0,1} par pas ; perte CE pondérée + normalisée par Σmask. None → moyenne uniforme (inchangé).

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à `tests/sandbox/test_warmstart_evolution_inworld.py` :

```python
def test_imitate_episode_bptt_mask_all_ones_trains_and_zero_mask_noop():
    pytest.importorskip("torch")
    pop = _tiny_torch_pop(B=4, I=2, O=8, N=12, seed=3)
    rng = np.random.RandomState(4)
    obs_seq, tgt_seq = [], []
    for _ in range(5):
        s = rng.choice([-1.0, 1.0], size=4).astype(np.float32)
        o = np.zeros((4, 2), dtype=np.float32); o[:, 0] = s
        obs_seq.append(o); tgt_seq.append(np.where(s > 0, 3, 0).astype(int))
    ones = [np.ones(4, dtype=np.float32) for _ in range(5)]
    first = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=ones)
    for _ in range(50):
        last = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=ones)
    assert last < first, "masque tout-à-1 doit entraîner (perte décroît)"
    zeros = [np.zeros(4, dtype=np.float32) for _ in range(5)]
    lz = pop.imitate_episode_bptt(obs_seq, tgt_seq, mask_seq=zeros)
    assert lz <= 1e-6, "masque tout-à-0 -> perte nulle, pas d'exception"
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_imitate_episode_bptt_mask_all_ones_trains_and_zero_mask_noop -v`
Expected: FAIL (mask_seq inconnu / TypeError).

- [ ] **Step 3 : Modifier `imitate_episode_bptt`**

Dans `src/agents/backend_torch.py`, remplacer la signature et le corps de `imitate_episode_bptt` par :

```python
    def imitate_episode_bptt(self, obs_seq, target_moves_seq, truncate_window=None, mask_seq=None):
        """IMITATION récurrente supervisée (BPTT) — distincte de learn_episode_bptt (REINFORCE). Rejoue
        obs_seq depuis H=0 en RETENANT le graphe récurrent ; perte = cross-entropy des move-logits vs
        l'action-enseignant par pas ; backprop unique -> _write_back. ADDITIF (ne touche pas forward/
        learn/learn_episode/learn_episode_bptt).

        obs_seq : liste de (B,>=I) ; target_moves_seq : liste de (B,) entiers dans [0,8).
        truncate_window=W : détache H tous les W pas (stabilité longue fenêtre).
        mask_seq (optionnel) : liste de (B,) ∈ {0,1} par pas -> perte CE PONDÉRÉE, normalisée par Σmask
        (exclut les pas post-mortem des agents). None -> moyenne uniforme (comportement INCHANGÉ)."""
        if self.B == 0 or not obs_seq:
            return None
        F = torch.nn.functional
        H = torch.zeros((self.B, self.N), device=self.device)
        loss = torch.zeros((), device=self.device)
        denom = 0.0
        for t, obs in enumerate(obs_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :self.I], device=self.device)
            if truncate_window and t > 0 and (t % truncate_window == 0):
                H = H.detach()
            H = self._step(obs_t, H)
            out = H[:, self.N - self.O:self.N]
            move_logits = out[:, :_MOVE_LOGITS]
            tgt = torch.tensor(np.asarray(target_moves_seq[t]), dtype=torch.long, device=self.device)
            if mask_seq is None:
                loss = loss + F.cross_entropy(move_logits, tgt)
                denom += 1.0
            else:
                ce = F.cross_entropy(move_logits, tgt, reduction="none")      # (B,)
                m = torch.tensor(np.asarray(mask_seq[t], dtype=np.float32), device=self.device)
                loss = loss + (ce * m).sum()
                denom += float(m.sum().item())
        loss = loss / max(1.0, denom)
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self._write_back()
        return float(loss.item())
```

- [ ] **Step 4 : Lancer, vérifier le succès + non-régression**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py -v`
Expected: PASS (nouveau test + les 6 existants inchangés).

- [ ] **Step 5 : Non-régression torch**

Run: `python -m pytest tests/sandbox/test_torch_inworld.py tests/sandbox/test_agent_backend_torch.py -q`
Expected: PASS.

- [ ] **Step 6 : Commit (path-scopé, après feu vert commits déjà donné)**

```bash
git add src/agents/backend_torch.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-003): mask_seq additif dans imitate_episode_bptt (BPTT masqué)"
```

---

### Task 2 : `_collect_onpolicy_trajectory` — collecteur on-policy fixed-B masqué

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py`

**Interfaces:**
- Consumes : `TorchPopulationModel`, `Biosphere3D`, `MambaAgent`, `seed_at`, `BIT_A`, `BIT_B`, `make_population` (patché localement).
- Produces : `_collect_onpolicy_trajectory(genome, seed=2026, num_agents=12, max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT) -> (obs_seq, tgt_seq, mask_seq)` ; chacun = liste (par tick) alignée fixed-B=num_agents ; obs_seq[t] (num_agents,59), tgt_seq[t] (num_agents,) int, mask_seq[t] (num_agents,) ∈ {0,1}. Renvoie ([],[],[]) si torch absent.

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter au test :

```python
def test_collect_onpolicy_trajectory_shapes_and_mask():
    from tools.warmstart_evolution_inworld import _collect_onpolicy_trajectory
    from src.agents.mamba_agent import MambaAgent
    pytest.importorskip("torch")
    g = MambaAgent().genome
    obs_seq, tgt_seq, mask_seq = _collect_onpolicy_trajectory(g, seed=2026, num_agents=4, max_ticks=10)
    assert len(obs_seq) == len(tgt_seq) == len(mask_seq) >= 1
    assert obs_seq[0].shape == (4, obs_seq[0].shape[1]) and obs_seq[0].shape[1] >= 14
    assert tgt_seq[0].shape == (4,) and mask_seq[0].shape == (4,)
    assert set(np.unique(mask_seq[0])).issubset({0.0, 1.0})
    assert mask_seq[0].sum() == 4.0           # tous vivants au 1er tick
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_collect_onpolicy_trajectory_shapes_and_mask -v`
Expected: FAIL (ImportError).

- [ ] **Step 3 : Implémenter dans `tools/warmstart_evolution_inworld.py`** (après `_inworld_accuracy`)

```python
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
```

- [ ] **Step 4 : Lancer, vérifier le succès**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_collect_onpolicy_trajectory_shapes_and_mask -v`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-003): _collect_onpolicy_trajectory (collecteur on-policy fixed-B masqué, aligné par id(model))"
```

---

### Task 3 : `run_dagger_warmstart` — boucle DAgger + wiring main

**Files:**
- Modify: `tools/warmstart_evolution_inworld.py`
- Test: `tests/sandbox/test_warmstart_evolution_inworld.py`

**Interfaces:**
- Consumes : `_collect_oracle_trajectory`, `_collect_onpolicy_trajectory`, `_inworld_accuracy`, `_torch_survival_eras`, `verdict_demand_marker`, `imitate_episode_bptt(mask_seq=)`, `TorchPopulationModel`, `MambaAgent`, `seed_at`.
- Produces : `run_dagger_warmstart(seed=2026, rounds=6, epochs_per_round=3000, lr=0.5, num_agents=12, max_ticks=200, metab=METAB_DEFAULT, cog=COG_DEFAULT, K=12) -> {trend_onpolicy_acc, trend_survival, final_genome, final_verdict}` ou None (torch absent).

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter au test :

```python
def test_run_dagger_warmstart_smoke():
    from tools.warmstart_evolution_inworld import run_dagger_warmstart
    from src.seed_ai.mutation import Genome
    pytest.importorskip("torch")
    out = run_dagger_warmstart(seed=2026, rounds=2, epochs_per_round=6, lr=0.5,
                               num_agents=4, max_ticks=12, K=2)
    assert len(out["trend_onpolicy_acc"]) == 2
    assert len(out["trend_survival"]) == 2
    assert isinstance(out["final_genome"], Genome)
    assert set(out["final_verdict"]) >= {"ratio", "verdict", "intact_survival"}
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py::test_run_dagger_warmstart_smoke -v`
Expected: FAIL (ImportError).

- [ ] **Step 3 : Implémenter `run_dagger_warmstart`** (après `run_bptt_imitation_warmstart`)

```python
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
```

- [ ] **Step 4 : Wiring `main()`** — ajouter, à la fin de `main()` (avant le `return`), un bloc DAgger optionnel piloté par env :

Repérer dans `main()` la ligne `return {"evo": evo["trend"], ...}` et INSÉRER juste AVANT elle :

```python
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
```

- [ ] **Step 5 : Lancer le test smoke + suite complète**

Run: `python -m pytest tests/sandbox/test_warmstart_evolution_inworld.py -v`
Expected: PASS (tous).

- [ ] **Step 6 : Smoke CLI**

Run: `WARM_GEN=2 WARM_POP=6 WARM_EPOCHS=5 WARM_K=2 WARM_DAGGER_ROUNDS=2 python tools/warmstart_evolution_inworld.py`
Expected: s'exécute sans exception ; imprime la courbe acc_on-policy + survie DAgger + verdict final.

- [ ] **Step 7 : Commit**

```bash
git add tools/warmstart_evolution_inworld.py tests/sandbox/test_warmstart_evolution_inworld.py
git commit -m "feat(WARM-003): run_dagger_warmstart (boucle DAgger on-policy) + wiring main WARM_DAGGER_ROUNDS"
```

---

### Task 4 : Run modéré + EDR-WARM-003 + MàJ REF/mémoire

**Files:**
- Create: `docs/EDR/WARM-003_DAgger_OnPolicy_Warmstart.md`
- Modify: `docs/REF/REF-DEMAND-MARKER.md`, mémoire `within-subject-demand-marker.md`

- [ ] **Step 1 : Run modéré**

Run: `WARM_SEED=2026 WARM_K=12 WARM_GEN=1 WARM_POP=6 WARM_EPOCHS=1 WARM_DAGGER_ROUNDS=6 python tools/warmstart_evolution_inworld.py`
(WARM_GEN/POP/EPOCHS minimaux pour ne pas relancer WARM-001/002 en entier ; seul DAgger nous intéresse ici.)
Ou appeler `run_dagger_warmstart(rounds=6)` via un mini-driver scratchpad. Noter la courbe acc_on-policy + survie + verdict final.

- [ ] **Step 2 : Interpréter et rédiger EDR-WARM-003** (`gate: G0`, `tests: [SDR-G0]`, `adopts: [REF-DEMAND-MARKER]`, liens `[[...]]`).
  - Si acc_on-policy ↑ et survie ↑ (≥100) → POSITIF : le verrou WARM-001 était le transfert (fixable on-policy).
  - Si acc_on-policy plafonne / survie stagne → NÉGATIF : verrou de RÉTENTION (le substrat récurrent ne soutient pas la carte 200 ticks auto-pilotés), pas de transfert. Distinguer nettement des deux, avec la courbe par round.

- [ ] **Step 3 : MàJ REF-DEMAND-MARKER** (adopt_for + ligne de table WARM-003).

- [ ] **Step 4 : MàJ mémoire** `within-subject-demand-marker.md` (résultat DAgger, conclusion sur transfert vs rétention).

- [ ] **Step 5 : Commit**

```bash
git add docs/EDR/WARM-003_DAgger_OnPolicy_Warmstart.md docs/REF/REF-DEMAND-MARKER.md
git commit -m "docs(WARM-003): EDR DAgger on-policy (transfert vs rétention) + MàJ REF-DEMAND-MARKER"
```

---

## Self-Review

**1. Couverture du spec** : mask_seq (Task 1) ✓ ; collecteur on-policy identity-aligné masqué (Task 2) ✓ ; boucle DAgger agrégée round-robin + wiring (Task 3) ✓ ; run + EDR + REF + mémoire (Task 4) ✓ ; barre PASS survie≥100 (Task 3 Step 4) ✓ ; alignement id(model) (Task 2) ✓ ; W gelé + memory_retriever.stop (Task 2) ✓.

**2. Placeholders** : aucun ; code complet fourni (Task 4 = analyse, contenu décrit).

**3. Cohérence des types** : `imitate_episode_bptt(..., mask_seq=)` (Task 1) = usage Task 3 ; `_collect_onpolicy_trajectory -> (obs,tgt,mask)` (Task 2) = usage Task 3 ; `run_dagger_warmstart -> {trend_onpolicy_acc, trend_survival, final_genome, final_verdict}` (Task 3 def) = usage main + test. `ORACLE_REF` déjà défini (WARM-001 fix). Cohérent.
