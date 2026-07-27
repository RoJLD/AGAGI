# ToM représentationnel (décode + émergence) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un banc tooling `tools/tom_probe.py` qui mesure (a) si la représentation encode déjà l'action des congénères par défaut et (b) si activer la récompense ToM fait ÉMERGER une prédiction réelle vs rester inerte.

**Architecture:** Deux bras évolutifs appariés par seed (CONTROL `active_exp_variable="NONE"` / TOM `="TOM"`), mesurés sur cohorte fixe. Accuracy de `predictor_head` vs shuffle + sonde linéaire sur latent exposé. Verdict gelé sur l'écart d'accuracy. Réutilise par imports — zéro `src/`.

**Tech Stack:** Python 3, numpy. Réutilise `tools/map_elites_compare.py` + `tools/competence_profile.py` (mergés) + lecture `src/agents/mamba_agent.py` / `src/worlds/world_1_stoneage.py`.

## Global Constraints

- TOOLING pur : `git diff <merge-base> HEAD -- src/` VIDE. Ne modifie NI `src/` NI substrate_ab/torch/famine/binding-probe (session //).
- Tout `print` exécuté est **ASCII-only** (cp1252). Accents seulement dans docstrings/commentaires.
- Réutilise par IMPORT (zéro modif) : `_make_cfg`, `_seed_genome`, `_reproduce`, `run_era_pool`, `PRESERVE_DIMS` (map_elites_compare).
- Verdict gelé : `TOM_EMERGES` ssi `acc_head_tom >= acc_shuffle_tom + 0.10` ET `acc_head_tom >= acc_head_ctrl + 0.10` ; sinon `TOM_INERT`. Seuils NON modifiables.
- Pairing = **same-cell** (`x,y,z` égaux), réplique de `world_1_stoneage.py:789`. `pred = argmax(predictor_head)` ∈ {0..7} ; `act = last_action`.
- Seed réel 1280, smoke 99280. Tests `tests/sandbox/test_tom_probe.py`. AUCUN test relancé après le run (EDR 107).

---

### Task 1: Squelette + métriques pures + verdict

**Files:**
- Create: `tools/tom_probe.py`
- Test: `tests/sandbox/test_tom_probe.py`

**Interfaces:**
- Consumes: `_make_cfg` (map_elites_compare) → `WorldConfig` avec `.active_exp_variable`.
- Produces: `_make_cfg_tom(exp_var)` ; `_head_accuracy(records)` ; `_shuffle_accuracy(records)` ; `_latent_probe(records, split=0.7) -> (acc_true, acc_shuffle)` ; `_verdict_tom_emergence(acc_head_tom, acc_head_ctrl, acc_shuffle_tom) -> str`. Un `record` = dict `{"pred": int, "act": int, "latent": np.ndarray(68,)}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/sandbox/test_tom_probe.py
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.tom_probe import (
    _make_cfg_tom,
    _head_accuracy,
    _shuffle_accuracy,
    _latent_probe,
    _verdict_tom_emergence,
)


def test_make_cfg_tom_sets_flag_and_keeps_sweet():
    cfg = _make_cfg_tom("TOM")
    assert cfg.active_exp_variable == "TOM"
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0
    assert _make_cfg_tom("NONE").active_exp_variable == "NONE"


def _rec(pred, act, latent=None):
    return {"pred": pred, "act": act, "latent": np.zeros(68) if latent is None else latent}


def test_head_accuracy_exact_fraction():
    recs = [_rec(3, 3), _rec(3, 3), _rec(3, 3), _rec(0, 1)]
    assert _head_accuracy(recs) == 0.75
    assert _head_accuracy([]) == 0.0


def test_shuffle_accuracy_deterministic_edges():
    # tous match -> shuffle des acts identiques reste 1.0
    assert _shuffle_accuracy([_rec(3, 3), _rec(3, 3)]) == 1.0
    # jamais match, acts identiques -> 0.0
    assert _shuffle_accuracy([_rec(0, 1), _rec(0, 1)]) == 0.0
    assert _shuffle_accuracy([]) == 0.0


def test_latent_probe_separable_beats_shuffle():
    np.random.seed(0)
    recs = []
    for c in range(4):
        base = np.zeros(68)
        base[c] = 5.0  # signal lineairement separable par classe
        for _ in range(30):
            lat = base + np.random.randn(68) * 0.1
            recs.append(_rec(c, c, lat))
    acc_true, acc_shuffle = _latent_probe(recs)
    assert acc_true > 0.8
    assert acc_true > acc_shuffle


def test_latent_probe_too_few_records():
    assert _latent_probe([_rec(0, 0)]) == (0.0, 0.0)


def test_verdict_tom_emergence_two_branches():
    assert _verdict_tom_emergence(0.45, 0.20, 0.22) == "TOM_EMERGES"
    assert _verdict_tom_emergence(0.22, 0.20, 0.21) == "TOM_INERT"
    # leve vs shuffle mais pas vs control -> INERT
    assert _verdict_tom_emergence(0.40, 0.35, 0.20) == "TOM_INERT"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_tom_probe.py -v`
Expected: FAIL (`ModuleNotFoundError: tools.tom_probe`).

- [ ] **Step 3: Create the module skeleton + pure functions**

```python
# tools/tom_probe.py
"""tools/tom_probe.py — ToM representationnel : decode + emergence (P4 audit memoire, chantier 1).

Le substrat a un circuit ToM GATE OFF : predictor_head (8 dims, mamba_agent) + recompense ToM
(world_1_stoneage:817-826, active_exp_variable=TOM : +2 energie si argmax(predictor_head_A)==last_action_B
pour deux agents au meme cellule). Jamais actif par defaut. Ce banc mesure, en 2 bras appareilles
CONTROL(NONE)/TOM : (a) DECODE — la representation encode-t-elle deja l'action des congeneres ? (b)
EMERGENCE — la recompense ToM fait-elle emerger une prediction reelle (vs inerte comme le tool-gate 111) ?

Tooling pur (pas de src/ modifie ; map_elites_compare/competence_profile importes). Usage : python -m tools.tom_probe
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from collections import defaultdict

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool, PRESERVE_DIMS


def _make_cfg_tom(exp_var):
    """cfg stoneage sweet-spot (via _make_cfg) avec active_exp_variable pose (NONE/TOM)."""
    cfg = _make_cfg()
    cfg.active_exp_variable = exp_var
    return cfg


def _head_accuracy(records):
    """Fraction des records ou argmax(predictor_head_A) == last_action_B. Liste vide -> 0.0."""
    if not records:
        return 0.0
    return float(np.mean([r["pred"] == r["act"] for r in records]))


def _shuffle_accuracy(records):
    """Baseline base-rate : accuracy quand les 'act' sont permutes (detruit la specificite A-B)."""
    if not records:
        return 0.0
    preds = np.array([r["pred"] for r in records])
    acts = np.array([r["act"] for r in records])
    shuf = np.random.permutation(acts)
    return float(np.mean(preds == shuf))


def _latent_probe(records, split=0.7):
    """Sonde lineaire (moindres carres + biais) : le latent expose (68 dims) predit-il l'action du
    congenere ? Renvoie (acc_true, acc_shuffle) held-out. < 20 records -> (0.0, 0.0). Split par ORDRE
    (deterministe)."""
    if len(records) < 20:
        return 0.0, 0.0
    X = np.stack([np.asarray(r["latent"], dtype=np.float64) for r in records])
    X = np.hstack([X, np.ones((len(X), 1))])  # biais
    y = np.array([r["act"] for r in records])
    classes = sorted(set(int(v) for v in y))
    cls_idx = {c: i for i, c in enumerate(classes)}
    n_tr = int(len(records) * split)

    def _fit_eval(y_use):
        Xtr, Xte = X[:n_tr], X[n_tr:]
        ytr, yte = y_use[:n_tr], y_use[n_tr:]
        if len(yte) == 0:
            return 0.0
        Y = np.zeros((len(ytr), len(classes)))
        for i, c in enumerate(ytr):
            Y[i, cls_idx[int(c)]] = 1.0
        W, *_ = np.linalg.lstsq(Xtr, Y, rcond=None)
        pred_idx = np.argmax(Xte @ W, axis=1)
        pred = np.array([classes[i] for i in pred_idx])
        return float(np.mean(pred == yte))

    acc_true = _fit_eval(y)
    acc_shuffle = _fit_eval(np.random.permutation(y))
    return acc_true, acc_shuffle


def _verdict_tom_emergence(acc_head_tom, acc_head_ctrl, acc_shuffle_tom):
    """TOM_EMERGES ssi la recompense ToM leve l'accuracy au-dessus du shuffle (base-rate) ET du bras
    CONTROL, des deux >= 0.10 ; sinon TOM_INERT (la faculte n'emerge pas sur le substrat plat)."""
    if acc_head_tom >= acc_shuffle_tom + 0.10 and acc_head_tom >= acc_head_ctrl + 0.10:
        return "TOM_EMERGES"
    return "TOM_INERT"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_tom_probe.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Verify zero src/ change**

Run: `git status --short src/` (attendu VIDE) puis `git add tools/tom_probe.py tests/sandbox/test_tom_probe.py`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(tom-probe): squelette + metriques accuracy/shuffle/probe + verdict (logique pure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Collecte de paires (env) + évolution 2 bras + report + main

**Files:**
- Modify: `tools/tom_probe.py` (ajoute fonctions APRÈS `_verdict_tom_emergence`)
- Test: `tests/sandbox/test_tom_probe.py` (ajoute 2 tests)

**Interfaces:**
- Consumes: `run_era_pool`, `_seed_genome`, `_reproduce`, `PRESERVE_DIMS` (map_elites_compare) ; `Biosphere3D` (`.benchmark_mode`, `.memory_retriever`, `.add_agent`, `.current_era`, `.step`, `.agents`) ; `MambaAgent().from_genome(g, preserve_dims=)` ; agents = dicts avec `x,y,z,last_action,model` ; `model.predictor_head/goal_vector/explicit_memory/ntm_memory`.
- Produces: `_agent_latent(model) -> np.ndarray(68,)` ; `_pair_record(a, b) -> dict|None` ; `_collect_pairs_from_agents(agents, records) -> None` (mutation) ; `_collect_tom_pairs(cfg, genomes, max_ticks) -> list` ; `_evolve_champions_tom(seed, exp_var, eras, num_agents, max_ticks) -> list` ; `_report_tom(h, per_seed, R, _return)` ; `main_tom_probe(R, eras, num_agents, max_ticks, seed, _return) -> dict|None`.

- [ ] **Step 1: Write the failing tests**

```python
# Ajouter a tests/sandbox/test_tom_probe.py
import types

from tools.tom_probe import _collect_pairs_from_agents, _agent_latent, main_tom_probe


def _fake_model(pred_argmax):
    ph = np.zeros(8)
    ph[pred_argmax] = 1.0
    return types.SimpleNamespace(
        predictor_head=ph,
        goal_vector=np.zeros(5),
        explicit_memory=np.zeros(5),
        ntm_memory=np.zeros((10, 5)),
    )


def _fake_agent(x, y, pred_argmax, last_action):
    return {"x": x, "y": y, "z": 0, "last_action": last_action, "model": _fake_model(pred_argmax)}


def test_collect_pairs_same_cell_both_directions():
    a = _fake_agent(0, 0, pred_argmax=3, last_action=2)
    b = _fake_agent(0, 0, pred_argmax=5, last_action=3)
    far = _fake_agent(9, 9, pred_argmax=1, last_action=1)
    records = []
    _collect_pairs_from_agents([a, b, far], records)
    # 2 records (A->B et B->A), far exclu (pas same-cell)
    assert len(records) == 2
    preds_acts = sorted((r["pred"], r["act"]) for r in records)
    # A predit 3, B a joue action 3 -> match ; B predit 5, A a joue 2 -> pas match
    assert (3, 3) in preds_acts and (5, 2) in preds_acts
    assert all(r["latent"].shape == (68,) for r in records)


def test_agent_latent_shape_and_none_guard():
    assert _agent_latent(_fake_model(0)).shape == (68,)
    empty = types.SimpleNamespace(predictor_head=None, goal_vector=None, explicit_memory=None, ntm_memory=None)
    assert _agent_latent(empty).shape == (68,)


def test_smoke_main_tom_probe_returns_verdict():
    res = main_tom_probe(R=1, eras=2, num_agents=12, max_ticks=80, seed=99280, _return=True)
    assert res["verdict"] in {"TOM_EMERGES", "TOM_INERT"}
    assert len(res["per_seed"]) == 1
    assert set(res["per_seed"][0].keys()) >= {"seed", "ctrl", "tom"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_tom_probe.py -k "collect or latent_shape or smoke" -v`
Expected: FAIL (ImportError sur `_collect_pairs_from_agents` / `main_tom_probe`).

- [ ] **Step 3: Implement collection + evolution + report + main**

```python
# Ajouter a tools/tom_probe.py apres _verdict_tom_emergence

def _agent_latent(model):
    """Latent expose concatene : predictor_head(8)+goal_vector(5)+explicit_memory(5)+ntm(50) = 68. None -> zeros."""
    def _vec(x, n):
        if x is None:
            return np.zeros(n, dtype=np.float64)
        arr = np.asarray(x, dtype=np.float64).flatten()
        if arr.size < n:
            return np.concatenate([arr, np.zeros(n - arr.size)])
        return arr[:n]
    return np.concatenate([
        _vec(getattr(model, "predictor_head", None), 8),
        _vec(getattr(model, "goal_vector", None), 5),
        _vec(getattr(model, "explicit_memory", None), 5),
        _vec(getattr(model, "ntm_memory", None), 50),
    ])


def _pair_record(a, b):
    """Record dirige A->B : pred=argmax(predictor_head_A), act=last_action_B, latent_A. None si invalide."""
    act = b.get("last_action", -1)
    if act is None or act < 0:
        return None
    model = a.get("model")
    ph = getattr(model, "predictor_head", None) if model is not None else None
    if ph is None:
        return None
    return {"pred": int(np.argmax(ph)), "act": int(act), "latent": _agent_latent(model)}


def _collect_pairs_from_agents(agents, records):
    """Pour chaque paire ORDONNEE (a,b) au meme cellule (x,y,z), append _pair_record(a,b) (les 2 directions)."""
    cells = defaultdict(list)
    for ag in agents:
        cells[(ag["x"], ag["y"], ag.get("z", 0))].append(ag)
    for group in cells.values():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(len(group)):
                if i == j:
                    continue
                rec = _pair_record(group[i], group[j])
                if rec is not None:
                    records.append(rec)


def _collect_tom_pairs(cfg, genomes, max_ticks=400):
    """Cohorte fixe (benchmark_mode + memory neutralisee AVANT boucle, lecons 114b/P0). A chaque tick,
    collecte les paires same-cell. Renvoie la liste des records."""
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    records = []
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        _collect_pairs_from_agents(env.agents, records)
        t += 1
    return records


def _evolve_champions_tom(seed, exp_var, eras=12, num_agents=30, max_ticks=400):
    """Cliquet top-5 (comme competence_profile._evolve_champions) MAIS cfg = _make_cfg_tom(exp_var) ->
    la recompense ToM est active (ou non) pendant l'evolution. Renvoie top-5 best_ever."""
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg_tom(exp_var)
    best_ever = [(0.0, g) for g in [_seed_genome(i) for i in range(5)]]
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents)
        pool, _m = run_era_pool(cfg, genomes, max_ticks)
        scored = sorted([(s, g) for s, g, _st in pool], key=lambda x: x[0], reverse=True)[:5]
        best_ever = sorted(best_ever + scored, key=lambda x: x[0], reverse=True)[:5]
    return [g for _s, g in best_ever]


def _report_tom(h, per_seed, R, _return):
    """Table ASCII (par seed : ctrl acc_head/shuffle/probe | tom acc_head/shuffle) + moyennes + decode +
    verdict emergence. Save JSON."""
    def _m(arm, k):
        return float(np.mean([p[arm][k] for p in per_seed]))
    ctrl = {k: _m("ctrl", k) for k in ("acc_head", "acc_shuffle", "probe_true", "probe_shuffle")}
    tom = {k: _m("tom", k) for k in ("acc_head", "acc_shuffle")}
    verdict = _verdict_tom_emergence(tom["acc_head"], ctrl["acc_head"], tom["acc_shuffle"])
    print("\n=== ToM representationnel : decode + emergence (cohorte fixe, 2 bras) ===")
    print("  seed | CTRL head shuf probe(t/s) | TOM  head shuf")
    for p in per_seed:
        c, t = p["ctrl"], p["tom"]
        print(f"  {p['seed']:4d} |      {c['acc_head']:.3f} {c['acc_shuffle']:.3f} "
              f"{c['probe_true']:.3f}/{c['probe_shuffle']:.3f} |      {t['acc_head']:.3f} {t['acc_shuffle']:.3f}")
    print(f"  MOYEN|      {ctrl['acc_head']:.3f} {ctrl['acc_shuffle']:.3f} "
          f"{ctrl['probe_true']:.3f}/{ctrl['probe_shuffle']:.3f} |      {tom['acc_head']:.3f} {tom['acc_shuffle']:.3f}")
    print("=== DECODE (bras CONTROL) ===")
    print(f"  head vs shuffle : {ctrl['acc_head']:.3f} vs {ctrl['acc_shuffle']:.3f} "
          f"| latent-probe vs shuffle : {ctrl['probe_true']:.3f} vs {ctrl['probe_shuffle']:.3f}")
    print("=== VERDICT (emergence ToM) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "mean_ctrl": ctrl, "mean_tom": tom, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "mean_ctrl": ctrl, "mean_tom": tom, "per_seed": per_seed, "R": R}


def _measure_arm_records(exp_var_for_evo, seed, eras, num_agents, max_ticks):
    """Evolue un bras puis collecte ses paires sur cohorte fixe (cfg de mesure NEUTRE = NONE pour les 2 bras)."""
    champs = _evolve_champions_tom(seed, exp_var_for_evo, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    reps = (champs * (num_agents // len(champs) + 1))[:num_agents] if champs else []
    return _collect_tom_pairs(_make_cfg_tom("NONE"), reps, max_ticks=max_ticks)


def main_tom_probe(R=3, eras=12, num_agents=30, max_ticks=400, seed=1280, _return=False):
    """Par seed base+r : evolue CONTROL(NONE) + TOM, mesure les paires per-bras sur cohorte fixe (mesure
    neutre), calcule accuracy head/shuffle (+ sonde latente sur CONTROL), agrege, verdict emergence."""
    base = seed
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            rc = _measure_arm_records("NONE", s, eras, num_agents, max_ticks)
            rt = _measure_arm_records("TOM", s, eras, num_agents, max_ticks)
            probe_true, probe_shuffle = _latent_probe(rc)
            per_seed.append({
                "seed": int(s),
                "ctrl": {"acc_head": _head_accuracy(rc), "acc_shuffle": _shuffle_accuracy(rc),
                         "probe_true": probe_true, "probe_shuffle": probe_shuffle, "n": len(rc)},
                "tom": {"acc_head": _head_accuracy(rt), "acc_shuffle": _shuffle_accuracy(rt), "n": len(rt)},
            })
    finally:
        async_logger.stop()
    h = Harness(seed=base, name="tom_probe", with_db=False, config=WorldConfig())
    return _report_tom(h, per_seed, R, _return)


if __name__ == "__main__":
    main_tom_probe()
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_tom_probe.py -v`
Expected: PASS (9 tests). Le smoke lance 2 bras evolutifs (R=1, eras=2) + collectes → quelques dizaines de secondes.

- [ ] **Step 5: Verify zero src/ change**

Run: `git diff --stat <task1-head> HEAD -- src/` (attendu VIDE).

- [ ] **Step 6: Commit**

```bash
git add tools/tom_probe.py tests/sandbox/test_tom_probe.py
git commit -m "feat(tom-probe): collecte paires same-cell + evolution 2 bras + report + main

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage** : §5.1 `_make_cfg_tom` → T1. §5.4 `_head/_shuffle_accuracy` → T1. §5.5 `_latent_probe` → T1. §5.6 verdict → T1. §5.3 `_collect_tom_pairs` (+ `_agent_latent`/`_pair_record`/`_collect_pairs_from_agents`) → T2. §5.2 `_evolve_champions_tom` → T2. §5.7 `_report_tom` → T2. §5.8 `main_tom_probe` → T2. §8 tests 1-6 → T1 (t1-4/6 pures) + T2 (pairing + smoke). Couvert.
- **Placeholders** : aucun ; code complet à chaque step.
- **Type consistency** : `record = {"pred","act","latent"}` cohérent (produit par `_pair_record`, consommé par `_head_accuracy`/`_shuffle_accuracy`/`_latent_probe`). `_measure_arm_records` renvoie une liste de records consommée par les accuracies. `per_seed[i]` = `{seed, ctrl:{acc_head,acc_shuffle,probe_true,probe_shuffle,n}, tom:{acc_head,acc_shuffle,n}}` cohérent entre `main` (produit) et `_report_tom` (moyenne les mêmes clés). Verdict prend 3 floats. Cohérent.
- **Run réel** (hors plan, après revue) : `python -m tools.tom_probe` (seed 1280, R=3), 2 passes byte-identiques, puis EDR 131 + mémoire + PR.
