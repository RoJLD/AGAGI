# Sonde mémoire compositionnelle — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si `did_x` (l'action X de S1) est décodable linéairement de l'état récurrent `H_S2` qui produit `move2`, pour trancher si la mémoire est le verrou compositionnel (suite EDR 119, Issue C → H1).

**Architecture:** Tâche 1 (BUILD) ajoute à `tools/substrate_ab_compositional.py` trois helpers (`_read_state`, `_decode_auc`, `memory_probe`) + un `main_memory_probe`, avec décodage logistique sklearn per-agent et contrôle au hasard `H_pre`. Tâche 2 (RUN, pas de code) exécute la sonde legacy+torch ×3 seeds, vérifie le contrôle `H_pre`≈0.5, et écrit EDR 120 (verdict MEMORY_PRESENT/ABSENT/ASYMÉTRIQUE).

**Tech Stack:** Python 3.13, numpy, PyTorch (backend torch), scikit-learn 1.8 (LogisticRegression/StandardScaler/roc_auc_score), pytest. Pas de nouvelle dépendance.

## Global Constraints

- Commits **path-scoped** uniquement (`git add <chemins exacts>`, jamais `-A`/`.`/bare) — tree partagé sur `feat/d1-prod-pairing`.
- **NE PAS modifier** `src/agents/backend.py`, `src/agents/backend_torch.py`, `tools/substrate_ab.py`. Lecture seule de leurs attributs autorisée (`pop._model.H_prev_batch`, `pop.H`).
- Quiet-log : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- Détection de succès **par EXIT CODE python**, jamais grep sur log redirigé (piège EDR 108).
- Lecture d'état : legacy `pop._model.H_prev_batch` (B,N) ; torch `pop.H.detach().cpu().numpy()` (B,N). Décodage sur la tranche non-input `H[:, I:]` (I = `agents[0].genome.num_inputs` = 59).
- **Mesure SANS apprentissage** (pas de `pop.learn`) ; `obs_a` VARIÉ par trial (RNG seedé), `obs_b` FIXE.
- Décodage **PER-AGENT** (jamais cross-agent) ; métrique **ROC-AUC** ; agent inclus seulement si les 2 classes de `did_x` ont ≥ `MIN_PER_CLASS=8` échantillons ; `n_qualifying` REPORTÉ.
- Déterminisme : `np.random.seed` + `torch.manual_seed` + RNG décodeur seedé.
- Ne JAMAIS toucher aux artefacts runtime concurrents (`data/state.json`, `data/articles.json`, `tests/test_kuzudb`, `results/*` d'autres sessions). Dump JSON via `SABC_MP_OUT`.
- EDR cible = **120** : vérifier libre à l'écriture (collisions, tree partagé).

---

### Task 1: Helpers de sonde mémoire + `memory_probe` + `main_memory_probe`

**Files:**
- Modify: `tools/substrate_ab_compositional.py` (ajout d'imports + 3 helpers + `memory_probe` + `main_memory_probe`)
- Test: `tests/sandbox/test_substrate_ab_compositional.py` (ajout de tests purs + smoke slow)

**Interfaces:**
- Consumes (déjà dans le fichier) : `from src.agents.mamba_agent import MambaAgent`, `from src.agents.backend import make_population`, `from tools.substrate_ab import compute_ab_verdict, _MOVE` ; helpers `_init_factor`/`_build_agents` (EDR 119) ; `import numpy as np`, `import statistics`.
- Produces :
  - `_read_state(pop, backend: str) -> np.ndarray` (B, N)
  - `_decode_auc(X, y, *, min_per_class: int = 8, seed: int = 0) -> float | None`
  - `memory_probe(seeds=(0,1,2), n_agents=16, trials=300, num_nodes=172, target_x=0) -> dict` avec clés `cells` (liste) et `verdict` (str)
  - `main_memory_probe()` (env `SABC_MP_*`, dump JSON `SABC_MP_OUT`)

- [ ] **Step 1: Écrire les tests purs de `_decode_auc`**

Ajouter à la fin de `tests/sandbox/test_substrate_ab_compositional.py` :

```python
def test_decode_auc_separable_signal():
    """Sur un signal linéairement séparable, l'AUC du décodeur ≈ 1."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    rng = np.random.RandomState(0)
    y = np.array([0, 1] * 60)                          # 120 samples, 2 classes équilibrées
    X = rng.randn(120, 4) + y[:, None] * 6.0           # signal fort corrélé à y
    auc = _decode_auc(X, y, min_per_class=8, seed=0)
    assert auc is not None and auc > 0.9


def test_decode_auc_pure_noise():
    """Sur du bruit indépendant de y, l'AUC ≈ 0.5 (pas de signal décodable)."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    rng = np.random.RandomState(1)
    y = np.array([0, 1] * 60)
    X = rng.randn(120, 4)                               # aucun lien avec y
    auc = _decode_auc(X, y, min_per_class=8, seed=0)
    assert auc is not None and 0.35 <= auc <= 0.65


def test_decode_auc_missing_class_returns_none():
    """Si une classe manque (ou < min_per_class), renvoie None (agent non qualifiant)."""
    import numpy as np
    from tools.substrate_ab_compositional import _decode_auc
    X = np.random.RandomState(2).randn(40, 4)
    y_one_class = np.zeros(40, dtype=int)              # une seule classe
    assert _decode_auc(X, y_one_class, min_per_class=8, seed=0) is None
    y_too_few = np.array([1] * 3 + [0] * 37)           # classe 1 < min_per_class
    assert _decode_auc(X, y_too_few, min_per_class=8, seed=0) is None
```

- [ ] **Step 2: Lancer → échec (`_decode_auc` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "decode_auc" -v`
Expected: FAIL avec `ImportError: cannot import name '_decode_auc'`.

- [ ] **Step 3: Implémenter `_decode_auc` (+ imports sklearn)**

Dans `tools/substrate_ab_compositional.py`, après les imports existants (après `import statistics`), ajouter :

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
```

Puis, après les helpers `_init_factor`/`_build_agents`, insérer :

```python
def _decode_auc(X, y, *, min_per_class: int = 8, seed: int = 0):
    """ROC-AUC d'une régression logistique linéaire décodant y depuis X (split train/test stratifié
    70/30, StandardScaler). Renvoie None si une classe a < min_per_class échantillons (agent non
    qualifiant). Mesure la décodabilité LINÉAIRE de y (pur, testable sans backend)."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y).astype(int)
    n0 = int(np.sum(y == 0))
    n1 = int(np.sum(y == 1))
    if n0 < min_per_class or n1 < min_per_class:
        return None
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=seed)
    if len(np.unique(y_tr)) < 2 or len(np.unique(y_te)) < 2:
        return None
    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    clf.fit(X_tr, y_tr)
    proba = clf.predict_proba(X_te)[:, 1]
    return float(roc_auc_score(y_te, proba))
```

- [ ] **Step 4: Lancer → succès**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "decode_auc" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Écrire le test pur de `_read_state` (forme)**

Ajouter à la fin du fichier de test :

```python
def test_read_state_legacy_shape():
    """_read_state(legacy) renvoie l'état récurrent batché (B, N) après un forward."""
    import numpy as np
    from src.agents.backend import make_population
    from tools.substrate_ab_compositional import _build_agents, _read_state
    np.random.seed(0)
    agents = _build_agents(4, 172, "prod")
    pop = make_population(agents, backend="legacy")
    obs = (np.random.RandomState(1).randn(4, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
    pop.forward(obs)
    st = _read_state(pop, "legacy")
    assert st.shape == (4, 172)


@pytest.mark.slow
def test_read_state_torch_shape():
    """_read_state(torch) renvoie pop.H sous forme numpy (B, N)."""
    pytest.importorskip("torch")
    import numpy as np
    from src.agents.backend import make_population
    from tools.substrate_ab_compositional import _build_agents, _read_state
    np.random.seed(0)
    agents = _build_agents(4, 172, "prod")
    pop = make_population(agents, backend="torch")
    obs = (np.random.RandomState(1).randn(4, agents[0].genome.num_inputs) * 0.5).astype(np.float32)
    pop.forward(obs)
    st = _read_state(pop, "torch")
    assert st.shape == (4, 172)
```

- [ ] **Step 6: Lancer → échec (`_read_state` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "read_state_legacy" -v`
Expected: FAIL avec `ImportError: cannot import name '_read_state'`.

- [ ] **Step 7: Implémenter `_read_state`**

Dans `tools/substrate_ab_compositional.py`, après `_decode_auc`, insérer :

```python
def _read_state(pop, backend: str):
    """Lit l'état récurrent batché (B, N) du backend (LECTURE SEULE, ne modifie rien).
    legacy -> MambaBatchModel.H_prev_batch ; torch -> TorchPopulationModel.H."""
    if backend == "torch":
        return pop.H.detach().cpu().numpy().copy()
    return np.asarray(pop._model.H_prev_batch, dtype=np.float64).copy()
```

- [ ] **Step 8: Lancer → succès (legacy ; torch slow si présent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "read_state" -v`
Expected: PASS (`test_read_state_legacy_shape` ; `test_read_state_torch_shape` PASS si torch installé sinon SKIP).

- [ ] **Step 9: Écrire le smoke test de `memory_probe`**

Ajouter à la fin du fichier de test :

```python
@pytest.mark.slow
def test_memory_probe_smoke():
    """memory_probe renvoie un dict structuré ; le contrôle AUC_pre est sain (≈0.5)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import memory_probe
    res = memory_probe(seeds=(0,), n_agents=8, trials=60)
    assert res["verdict"] in {"MEMORY_PRESENT", "MEMORY_ABSENT", "ASYMÉTRIQUE"}
    assert res["cells"]
    for c in res["cells"]:
        assert c["backend"] in {"legacy", "torch"}
        for k in ("n_qualifying", "base_rate", "median_auc_s2", "median_auc_pre", "median_delta"):
            assert k in c
        if c["median_auc_pre"] is not None:
            assert 0.3 <= c["median_auc_pre"] <= 0.7   # contrôle au hasard sain
```

- [ ] **Step 10: Lancer → échec (`memory_probe` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_memory_probe_smoke -v`
Expected: FAIL avec `ImportError: cannot import name 'memory_probe'`.

- [ ] **Step 11: Implémenter `memory_probe`**

Dans `tools/substrate_ab_compositional.py`, après `_read_state`, insérer :

```python
def _probe_one(backend: str, seed: int, n_agents: int, trials: int, num_nodes: int, target_x: int):
    """Collecte (H_pre, H_S2, did_x) par agent SANS apprentissage, puis décode per-agent.
    obs_a VARIÉ par trial (fait varier did_x), obs_b FIXE (S2 n'encode pas did_x)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, num_nodes, "prod")
    pop = make_population(agents, backend=backend)
    I = agents[0].genome.num_inputs
    rng = np.random.RandomState(seed + 1)
    obs_b = (rng.randn(n_agents, I) * 0.5).astype(np.float32)         # S2 fixe
    pre_buf = [[] for _ in range(n_agents)]
    s2_buf = [[] for _ in range(n_agents)]
    didx_buf = [[] for _ in range(n_agents)]
    for _ in range(trials):
        H_pre = _read_state(pop, backend)                             # état AVANT S1
        obs_a = (rng.randn(n_agents, I) * 0.5).astype(np.float32)     # S1 VARIÉ
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.forward(obs_b)                                            # S2 -> met à jour l'état
        H_s2 = _read_state(pop, backend)
        for i in range(n_agents):
            pre_buf[i].append(H_pre[i, I:])
            s2_buf[i].append(H_s2[i, I:])
            didx_buf[i].append(bool(did_x[i]))
    auc_s2, auc_pre, base = [], [], []
    for i in range(n_agents):
        y = np.array(didx_buf[i], dtype=int)
        base.append(float(np.mean(y)))
        a2 = _decode_auc(np.array(s2_buf[i]), y, seed=seed)
        ap = _decode_auc(np.array(pre_buf[i]), y, seed=seed)
        if a2 is not None:
            auc_s2.append(a2)
        if ap is not None:
            auc_pre.append(ap)
    med_s2 = statistics.median(auc_s2) if auc_s2 else None
    med_pre = statistics.median(auc_pre) if auc_pre else None
    med_delta = (med_s2 - med_pre) if (med_s2 is not None and med_pre is not None) else None
    return {"backend": backend, "seed": int(seed), "n_qualifying": len(auc_s2),
            "base_rate": float(np.mean(base)), "median_auc_s2": med_s2,
            "median_auc_pre": med_pre, "median_delta": med_delta,
            "per_agent_auc_s2": auc_s2, "per_agent_auc_pre": auc_pre}


def memory_probe(seeds=(0, 1, 2), n_agents: int = 16, trials: int = 300,
                 num_nodes: int = 172, target_x: int = 0) -> dict:
    """Sonde la décodabilité linéaire de did_x depuis H_S2 (mémoire) vs H_pre (contrôle au hasard),
    per-agent, par backend. Verdict : MEMORY_PRESENT si AUC_S2 médian >0.6 ET delta >0.1 sur les DEUX
    backends ; MEMORY_ABSENT si AUC_S2 ≈0.5 (≤0.55) sur les deux ; sinon ASYMÉTRIQUE."""
    cells = []
    for backend in ("legacy", "torch"):
        for s in seeds:
            cells.append(_probe_one(backend, s, n_agents, trials, num_nodes, target_x))

    def _agg(backend):
        vals_s2 = [c["median_auc_s2"] for c in cells if c["backend"] == backend and c["median_auc_s2"] is not None]
        vals_d = [c["median_delta"] for c in cells if c["backend"] == backend and c["median_delta"] is not None]
        return (statistics.median(vals_s2) if vals_s2 else None,
                statistics.median(vals_d) if vals_d else None)

    leg_s2, leg_d = _agg("legacy")
    tor_s2, tor_d = _agg("torch")

    def _carries(s2, d):
        return (s2 is not None and s2 > 0.6 and d is not None and d > 0.1)

    def _absent(s2):
        return (s2 is not None and s2 <= 0.55)

    if _carries(leg_s2, leg_d) and _carries(tor_s2, tor_d):
        verdict = "MEMORY_PRESENT"
    elif _absent(leg_s2) and _absent(tor_s2):
        verdict = "MEMORY_ABSENT"
    else:
        verdict = "ASYMÉTRIQUE"
    return {"cells": cells, "verdict": verdict,
            "summary": {"legacy_auc_s2": leg_s2, "legacy_delta": leg_d,
                        "torch_auc_s2": tor_s2, "torch_delta": tor_d}}
```

- [ ] **Step 12: Lancer le smoke → succès**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_memory_probe_smoke -v`
Expected: PASS.

- [ ] **Step 13: Implémenter `main_memory_probe` (knobs env + table + dump JSON)**

Dans `tools/substrate_ab_compositional.py`, après `memory_probe`, insérer :

```python
def main_memory_probe():
    seeds = [int(s) for s in os.environ.get("SABC_MP_SEEDS", "0,1,2").split(",") if s.strip()]
    n_agents = int(os.environ.get("SABC_MP_AGENTS", "16"))
    trials = int(os.environ.get("SABC_MP_TRIALS", "300"))
    res = memory_probe(seeds=tuple(seeds), n_agents=n_agents, trials=trials)
    print(f"VERDICT={res['verdict']}  summary={res['summary']}")
    print("CELLS (backend x seed -> n_qual, base_rate, AUC_s2, AUC_pre, delta):")
    for c in res["cells"]:
        def _f(x):
            return f"{x:.3f}" if x is not None else "  NA "
        print(f"  {c['backend']:<6} seed={c['seed']} n_qual={c['n_qualifying']:>2} "
              f"base={c['base_rate']:.3f} AUC_s2={_f(c['median_auc_s2'])} "
              f"AUC_pre={_f(c['median_auc_pre'])} delta={_f(c['median_delta'])}")
    out = os.environ.get("SABC_MP_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res


if __name__ == "__main__":
    import sys as _sys
    if "--memory-probe" in _sys.argv:
        main_memory_probe()
    else:
        main()
```

(Remplacer le bloc `if __name__ == "__main__": main()` existant par ce bloc qui aiguille sur le flag `--memory-probe` ; le sweep reste accessible sans flag.)

- [ ] **Step 14: Vérifier toute la suite du fichier**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -v`
Expected: PASS — tests purs (truth_table, init_factor×2, build_agents×2, decode_auc×3, read_state_legacy) ; slow (compositional_ab_smoke, sweep_smoke, read_state_torch, memory_probe_smoke) PASS si torch présent sinon SKIP propre.

- [ ] **Step 15: Smoke manuel du `main --memory-probe` (petit budget) — EXIT CODE**

Run:
```bash
AGISEED_QUIET_LOG=1 SABC_MP_SEEDS=0 SABC_MP_AGENTS=8 SABC_MP_TRIALS=60 \
  SABC_MP_OUT="$TMPDIR/mp_smoke.json" python tools/substrate_ab_compositional.py --memory-probe; echo "EXIT=$?"
```
Expected: affiche `VERDICT=...`, `CELLS ...`, `WROTE ...`, puis `EXIT=0`. (Si torch absent : le backend torch lèvera — attendu hors environnement torch ; valider alors la suite pytest de l'étape 14 et noter que le RUN de Task 2 exige torch.)

- [ ] **Step 16: Commit (path-scoped)**

```bash
git add tools/substrate_ab_compositional.py tests/sandbox/test_substrate_ab_compositional.py
git commit -m "feat(sab-compo): sonde memoire (decode did_x de H_S2 vs controle H_pre, per-agent AUC)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: RUN de la sonde + contrôle H_pre + EDR 120 (pas de code)

**Files:**
- Create: `docs/EDR/120_<titre>.md` (vérifier 120 libre ; sinon prochain libre)
- Read-only : sortie de la sonde (log + JSON `SABC_MP_OUT`)

**Interfaces:**
- Consumes : `memory_probe`/`main_memory_probe` de Task 1.
- Produces : EDR 120 (verdict MEMORY_PRESENT/ABSENT/ASYMÉTRIQUE documenté, table per-cellule, contrôle H_pre, caveats).

- [ ] **Step 1: Vérifier le numéro d'EDR libre**

Run: `ls docs/EDR/ | grep -E '^11[89]|^12[0-3]'`
Expected : confirmer si `120_*` existe. Si pris, viser le prochain libre et l'annoncer dans l'EDR.

- [ ] **Step 2: Lancer la sonde complète — EXIT CODE, JSON dumpé**

Run (chemin JSON dédié, PAS sous results/ d'autres sessions) :
```bash
AGISEED_QUIET_LOG=1 SABC_MP_SEEDS=0,1,2 SABC_MP_AGENTS=16 SABC_MP_TRIALS=300 \
  SABC_MP_OUT="results/sab_memory_probe.json" \
  python tools/substrate_ab_compositional.py --memory-probe > /tmp/mp_run.log 2>&1; echo "EXIT=$?"
```
Expected : `EXIT=0` (succès jugé par le CODE, jamais par grep). Le JSON contient `cells` + `summary` + `verdict`.
Garde-fou : si `EXIT≠0`, lire `/tmp/mp_run.log` pour la cause — NE PAS conclure depuis un log tronqué.

- [ ] **Step 3: Contrôle au hasard `H_pre` (le héros) — valider la méthodo AVANT le verdict**

Inspecter `median_auc_pre` par cellule : il DOIT être ≈ 0.5 (tolérance ~[0.40, 0.60]). Si `AUC_pre` est franchement > 0.6, le décodage exploite l'identité-agent/historique, pas la mémoire S1→S2 → **SUSPENDRE le verdict** et investiguer (le `obs_a` varié devrait l'empêcher). Reporter aussi `n_qualifying` (assez d'agents avec les 2 classes ?) et `base_rate` (≈ 1/8 attendu pour target_x sur 8 moves).

- [ ] **Step 4: Lire le verdict (jamais le scalaire nu)**

Extraire `summary` (legacy/torch AUC_s2 + delta) et les `cells` per-seed. Lecture :
- **MEMORY_PRESENT** : AUC_s2 ≫ 0.5 (>0.6) ET delta (s2−pre) >0.1 sur les DEUX backends → la récurrence porte did_x → verrou EN AVAL → prochain chantier = curriculum.
- **MEMORY_ABSENT** : AUC_s2 ≈ 0.5 (≤0.55) sur les deux → la récurrence lave did_x → verrou = mémoire → mécanisme explicite.
- **ASYMÉTRIQUE** : un backend porte, l'autre non → cibler le backend porteur.
Rapporter AUC_s2/AUC_pre/delta PAR backend et par seed + n_qualifying + base_rate (jamais le scalaire nu).

- [ ] **Step 5: Écrire EDR 120**

Créer `docs/EDR/120_<titre>.md` selon le moule d'EDR 119 (frontmatter `id/type/title/status/gate/verdict`, sections Contexte / Méthode / Contrôle au hasard H_pre / Résultats (table per-cellule : n_qual, base_rate, AUC_s2, AUC_pre, delta + per-agent résumé) / Verdict / Caveats / Conséquences / Liens). Caveats obligatoires : décodage per-agent à l'init (capacité, pas apprentissage) ; AUC_pre = contrôle de validité méthodo ; n=3 seeds ; micro-tâche proxy ; base_rate déséquilibré (AUC choisi exprès). Liens : `[[sota-gap-substrate]]`, `[[coop-competence-is-population-property]]`, EDR 119, EDR 117.

- [ ] **Step 6: Commit (path-scoped)**

```bash
git add docs/EDR/120_<titre>.md
git commit -m "docs(EDR120): sonde memoire compositionnelle — verdict <MEMORY_PRESENT|ABSENT|ASYMETRIQUE>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes d'exécution

- **Pas de PR-off-main** : le banc importe `backend.py`/`substrate_ab.py` absents d'`origin/main` → le chantier vit sur `feat/d1-prod-pairing` (mêmes contraintes qu'EDR 117/119).
- Le dump JSON (`SABC_MP_OUT`) protège contre la perte de données log-only (piège EDR 108/113).
- Si torch est absent, Task 2 ne produit pas le bras torch : signaler et différer ; Task 1 (BUILD + tests purs) reste livrable (slow skippés).
- Seuils du verdict (`>0.6`/`>0.1`/`≤0.55`) = heuristiques de cadrage ; le RUN reporte les chiffres bruts, le verdict final est lu par l'humain/contrôleur sur les données (pas seulement l'enum du code).
