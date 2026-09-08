# Curriculum à fade — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tester si le plafond de torch (0.30, EDR 122) était la rétention de X ou le binding : maintenir X via un bonus `did_x` décroissant (fade) en phase B, et MESURER P(Y|X) directement.

**Architecture:** Tâche 1 (BUILD) ajoute à `tools/substrate_ab_compositional.py` deux helpers purs (`_fade_weight`, `_p_y_given_x`) + `run_curriculum_fade` + `compare_curriculum_fade` + `main_curriculum_fade`, avec tests purs + smoke. `run_curriculum` (bascule dure, EDR 122) reste INTACT comme baseline. Tâche 2 (RUN, pas de code) exécute legacy+torch ×5 seeds, vérifie le maintien de X (le fade marche) et lit hit_end + P(Y|X) → verdict CEILING_WAS_RETENTION/BINDING, EDR 123.

**Tech Stack:** Python 3.13, numpy, PyTorch (backend torch), pytest. Pas de nouvelle dépendance.

## Global Constraints

- Commits **path-scoped** uniquement (`git add <chemins exacts>`, jamais `-A`/`.`/bare) — tree partagé sur `feat/d1-prod-pairing`.
- **NE PAS modifier** `src/agents/backend.py`, `src/agents/backend_torch.py`, `tools/substrate_ab.py`, ni `run_curriculum` (bascule dure, instrument EDR 122 — reste INTACT). Réutilise `make_population`, `compute_ab_verdict`, `_MOVE`, `_build_agents`, `compositional_reward`, `_warmup_reward`.
- Quiet-log : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- Détection de succès **par EXIT CODE python**, jamais grep sur log redirigé (piège EDR 108).
- Fade LINÉAIRE : `fade_w = fade_w0 · (1 − t/T)` (t 0-indexé, T=`compo_trials`). `fade_w0=0` ⟹ S1 reward 0 ⟹ identique bascule dure. Défaut `fade_w0=1.0`.
- Phase A reward = `_warmup_reward` (+1/−1) ; phase B S1 reward = `fade_w · _warmup_reward(...)` ; phase B S2 reward = `compositional_reward` (inchangé).
- **P(Y|X) DIRECT** : tracer `y_correct=(move2==target_y)` (inconditionnel) ET `did_x` ; `_p_y_given_x` = fraction de y_correct parmi did_x (None si aucun did_x).
- `obs_a`/`obs_b` FIXES, `obs_a` partagé A↔B. Jamais de scalaire nu (trajectoires). Déterminisme seed np+torch.
- Ne JAMAIS toucher aux artefacts runtime concurrents (`data/state.json`, `data/articles.json`, `tests/test_kuzudb`, `results/*` d'autres sessions). Dump JSON via `SABC_CF_OUT`.
- EDR cible = **123** : vérifier libre à l'écriture (collisions, tree partagé).

---

### Task 1: Helpers fade/P(Y|X) + `run_curriculum_fade` + `compare_curriculum_fade` + `main_curriculum_fade`

**Files:**
- Modify: `tools/substrate_ab_compositional.py` (2 helpers + 3 fonctions + aiguillage `--curriculum-fade`)
- Test: `tests/sandbox/test_substrate_ab_compositional.py` (tests purs + smoke slow)

**Interfaces:**
- Consumes (déjà dans le fichier) : `MambaAgent`, `make_population`, `compute_ab_verdict`, `_MOVE`, `_build_agents`, `compositional_reward`, `_warmup_reward`, `import numpy as np`, `import statistics`, `import os`.
- Produces :
  - `_fade_weight(t: int, total: int, w0: float) -> float`
  - `_p_y_given_x(y_correct, did_x) -> float | None`
  - `run_curriculum_fade(backend, seed=0, warmup_trials=150, compo_trials=250, n_agents=8, target_x=0, target_y=4, fade_w0=1.0) -> dict`
  - `compare_curriculum_fade(seeds=(0,1,2,3,4), warmup_trials=150, compo_trials=250, n_agents=8, fade_w0=1.0) -> dict`
  - `main_curriculum_fade()`

- [ ] **Step 1: Écrire les tests purs des helpers**

Ajouter à la fin de `tests/sandbox/test_substrate_ab_compositional.py` :

```python
def test_fade_weight_linear_decay():
    """fade_w = w0·(1−t/T) : plein à t=0, 0 à t=T, moitié à t=T/2 ; w0=0 → 0 partout (bascule dure)."""
    from tools.substrate_ab_compositional import _fade_weight
    assert _fade_weight(0, 100, 1.0) == 1.0
    assert _fade_weight(100, 100, 1.0) == 0.0
    assert _fade_weight(50, 100, 1.0) == 0.5
    assert _fade_weight(0, 100, 0.0) == 0.0
    assert _fade_weight(50, 100, 0.0) == 0.0


def test_p_y_given_x_conditional():
    """P(Y|X) = fraction de y_correct PARMI les trials où did_x ; None si aucun did_x."""
    import numpy as np
    from tools.substrate_ab_compositional import _p_y_given_x
    # did_x sur trials 0,1 ; y_correct sur 0 seulement → 1/2 = 0.5
    assert _p_y_given_x(np.array([True, False, True, True]),
                        np.array([True, True, False, False])) == 0.5
    # tous did_x, tous y → 1.0
    assert _p_y_given_x(np.array([True, True]), np.array([True, True])) == 1.0
    # aucun did_x → None
    assert _p_y_given_x(np.array([True, True]), np.array([False, False])) is None
```

- [ ] **Step 2: Lancer → échec (helpers absents)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "fade_weight or p_y_given_x" -v`
Expected: FAIL avec `ImportError: cannot import name '_fade_weight'` (ou `_p_y_given_x`).

- [ ] **Step 3: Implémenter `_fade_weight` + `_p_y_given_x`**

Dans `tools/substrate_ab_compositional.py`, après `_warmup_reward` (et avant `run_curriculum`), insérer :

```python
def _fade_weight(t: int, total: int, w0: float) -> float:
    """Poids de maintien de X en phase B : décroissance LINÉAIRE w0·(1−t/total) (plein à t=0, 0 à
    t=total). w0=0 → 0 partout (≡ bascule dure). PUR."""
    if total <= 0 or w0 == 0.0:
        return 0.0
    return float(w0 * (1.0 - t / total))


def _p_y_given_x(y_correct, did_x):
    """P(Y correct | X fait) = fraction de y_correct PARMI les trials où did_x est vrai.
    None si aucun did_x (conditionnel indéfini). MESURE directe du binding (pas d'inférence). PUR."""
    y_correct = np.asarray(y_correct, dtype=bool)
    did_x = np.asarray(did_x, dtype=bool)
    n = int(np.sum(did_x))
    if n == 0:
        return None
    return float(np.sum(y_correct & did_x) / n)
```

- [ ] **Step 4: Lancer → succès**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "fade_weight or p_y_given_x" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Écrire le test slow `run_curriculum_fade` (fade_w0=0 ≡ bascule dure)**

Ajouter à la fin du fichier de test :

```python
@pytest.mark.slow
def test_run_curriculum_fade_keys_and_w0_zero():
    """run_curriculum_fade renvoie les clés (dont p_y_given_x_end) ; fade_w0=0 tourne sans erreur."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum_fade
    r = run_curriculum_fade("legacy", seed=0, warmup_trials=10, compo_trials=40, n_agents=4, fade_w0=0.0)
    for k in ("warmup_didx_end", "hit_end", "compo_didx_end", "p_y_given_x_end", "y_rate_end", "delta"):
        assert k in r
    assert 0.0 <= r["hit_end"] <= 1.0
    assert (r["p_y_given_x_end"] is None) or (0.0 <= r["p_y_given_x_end"] <= 1.0)
```

- [ ] **Step 6: Lancer → échec (`run_curriculum_fade` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_run_curriculum_fade_keys_and_w0_zero -v`
Expected: FAIL avec `ImportError: cannot import name 'run_curriculum_fade'`.

- [ ] **Step 7: Implémenter `run_curriculum_fade`**

Dans `tools/substrate_ab_compositional.py`, après `run_curriculum` (et avant `compare_curriculum`), insérer :

```python
def run_curriculum_fade(backend: str, seed: int = 0, warmup_trials: int = 150, compo_trials: int = 250,
                        n_agents: int = 8, target_x: int = 0, target_y: int = 4,
                        fade_w0: float = 1.0) -> dict:
    """Curriculum à FADE. Phase A : enseigner X (dense). Phase B : S1 reward = fade_w·warmup_reward
    (fade_w décroît linéairement de fade_w0 à 0) → maintient X au lieu de le laisser décliner ;
    S2 reward = compositionnel. Mesure le joint `hit`, la rétention `compo_didx`, ET P(Y|X) DIRECT.
    fade_w0=0 ≡ bascule dure (baseline EDR 122)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    agents = _build_agents(n_agents, 172, "prod")
    pop = make_population(agents, backend=backend)
    rng = np.random.RandomState(seed + 1)
    n_in = agents[0].genome.num_inputs
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)

    # --- Phase A : warmup dense sur X (S1 seul) ---
    warm = []
    for _ in range(warmup_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        warm.append(float(np.mean(move1 == target_x)))
        reward = np.array([_warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
    qa = max(1, warmup_trials // 4) if warmup_trials else 0
    warmup_didx_end = float(np.mean(warm[-qa:])) if qa else 0.0

    # --- Phase B : compositionnel + fade linéaire du maintien de X ---
    hit, bx, yc = [], [], []
    for t in range(compo_trials):
        fade_w = _fade_weight(t, compo_trials, fade_w0)
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        s1_reward = np.array([fade_w * _warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(s1_reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        y_correct = (move2 == target_y)
        reward2 = np.array([compositional_reward(int(move2[i]), target_y, bool(did_x[i]))
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        hit.append(float(np.mean(y_correct & did_x)))
        bx.append(did_x)
        yc.append(y_correct)
    qb = max(1, compo_trials // 4) if compo_trials else 0
    hit_start = float(np.mean(hit[:qb])) if qb else 0.0
    hit_end = float(np.mean(hit[-qb:])) if qb else 0.0
    didx_end = np.concatenate(bx[-qb:]) if qb else np.array([], dtype=bool)
    didx_start = np.concatenate(bx[:qb]) if qb else np.array([], dtype=bool)
    yc_end = np.concatenate(yc[-qb:]) if qb else np.array([], dtype=bool)
    yc_start = np.concatenate(yc[:qb]) if qb else np.array([], dtype=bool)
    compo_didx_start = float(np.mean(didx_start)) if didx_start.size else 0.0
    compo_didx_end = float(np.mean(didx_end)) if didx_end.size else 0.0
    return {"backend": backend, "seed": int(seed), "warmup_trials": warmup_trials,
            "compo_trials": compo_trials, "fade_w0": fade_w0, "n_agents": n_agents,
            "warmup_didx_end": warmup_didx_end,
            "hit_start": hit_start, "hit_end": hit_end,
            "compo_didx_start": compo_didx_start, "compo_didx_end": compo_didx_end,
            "p_y_given_x_start": _p_y_given_x(yc_start, didx_start),
            "p_y_given_x_end": _p_y_given_x(yc_end, didx_end),
            "y_rate_end": float(np.mean(yc_end)) if yc_end.size else 0.0,
            "delta": hit_end - hit_start}
```

- [ ] **Step 8: Lancer → succès**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_run_curriculum_fade_keys_and_w0_zero -v`
Expected: PASS.

- [ ] **Step 9: Écrire le smoke test `compare_curriculum_fade`**

Ajouter à la fin du fichier de test :

```python
@pytest.mark.slow
def test_compare_curriculum_fade_smoke():
    """compare_curriculum_fade renvoie un verdict_fade structuré + per_seed avec P(Y|X)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare_curriculum_fade
    res = compare_curriculum_fade(seeds=(0,), warmup_trials=40, compo_trials=40, n_agents=4)
    assert res["verdict_fade"] in {"CEILING_WAS_RETENTION", "CEILING_WAS_BINDING",
                                   "FADE_INEFFECTIVE", "AMBIGU"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for arm in ("legacy", "torch"):
        for k in ("hit_end", "compo_didx_end", "p_y_given_x_end"):
            assert k in row[arm]
```

- [ ] **Step 10: Lancer → échec (`compare_curriculum_fade` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_compare_curriculum_fade_smoke -v`
Expected: FAIL avec `ImportError: cannot import name 'compare_curriculum_fade'`.

- [ ] **Step 11: Implémenter `compare_curriculum_fade`**

Dans `tools/substrate_ab_compositional.py`, après `run_curriculum_fade`, insérer :

```python
def compare_curriculum_fade(seeds=(0, 1, 2, 3, 4), warmup_trials: int = 150, compo_trials: int = 250,
                            n_agents: int = 8, fade_w0: float = 1.0) -> dict:
    """A/B apparié legacy vs torch du curriculum à fade. Verdict_fade :
    FADE_INEFFECTIVE si torch compo_didx_end médian ≤ 0.40 (le fade n'a PAS maintenu X → garde-fou) ;
    CEILING_WAS_RETENTION si torch hit_end médian > 0.35 ET p_y_given_x_end médian > 0.70 ;
    CEILING_WAS_BINDING si X maintenu (compo_didx_end > 0.60) MAIS hit_end ≤ 0.35 / p_y_given_x ≤ 0.70 ;
    sinon AMBIGU. Seuils heuristiques (verdict final lu par l'humain sur les chiffres)."""
    rows = []
    for s in seeds:
        leg = run_curriculum_fade("legacy", seed=s, warmup_trials=warmup_trials,
                                  compo_trials=compo_trials, n_agents=n_agents, fade_w0=fade_w0)
        tor = run_curriculum_fade("torch", seed=s, warmup_trials=warmup_trials,
                                  compo_trials=compo_trials, n_agents=n_agents, fade_w0=fade_w0)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})

    def _med(arm, key):
        vals = [r[arm][key] for r in rows if r[arm][key] is not None]
        return statistics.median(vals) if vals else None

    tor_didx = _med("torch", "compo_didx_end")
    tor_hit = _med("torch", "hit_end")
    tor_pyx = _med("torch", "p_y_given_x_end")
    if tor_didx is None or tor_didx <= 0.40:
        verdict_f = "FADE_INEFFECTIVE"
    elif tor_hit is not None and tor_hit > 0.35 and tor_pyx is not None and tor_pyx > 0.70:
        verdict_f = "CEILING_WAS_RETENTION"
    elif tor_didx > 0.60 and (tor_hit is None or tor_hit <= 0.35 or tor_pyx is None or tor_pyx <= 0.70):
        verdict_f = "CEILING_WAS_BINDING"
    else:
        verdict_f = "AMBIGU"
    return {**compute_ab_verdict(rows), "verdict_fade": verdict_f,
            "summary": {"torch_compo_didx_end": tor_didx, "torch_hit_end": tor_hit,
                        "torch_p_y_given_x_end": tor_pyx,
                        "legacy_hit_end": _med("legacy", "hit_end"),
                        "legacy_p_y_given_x_end": _med("legacy", "p_y_given_x_end")},
            "per_seed": rows}
```

- [ ] **Step 12: Lancer le smoke → succès**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_compare_curriculum_fade_smoke -v`
Expected: PASS.

- [ ] **Step 13: Implémenter `main_curriculum_fade` + aiguillage**

Dans `tools/substrate_ab_compositional.py`, après `compare_curriculum_fade`, insérer :

```python
def main_curriculum_fade():
    seeds = [int(s) for s in os.environ.get("SABC_CF_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    warmup = int(os.environ.get("SABC_CF_WARMUP", "150"))
    compo = int(os.environ.get("SABC_CF_COMPO", "250"))
    n_agents = int(os.environ.get("SABC_CF_AGENTS", "8"))
    fade_w0 = float(os.environ.get("SABC_CF_W0", "1.0"))
    res = compare_curriculum_fade(seeds=tuple(seeds), warmup_trials=warmup, compo_trials=compo,
                                  n_agents=n_agents, fade_w0=fade_w0)
    print(f"VERDICT_FADE={res['verdict_fade']} (w0={fade_w0})  summary={res['summary']}")
    print("PER-SEED (compo_didx_end ; hit_end ; P(Y|X)_end) :")
    for r in res["per_seed"]:
        for arm in ("legacy", "torch"):
            a = r[arm]
            pyx = a["p_y_given_x_end"]
            pyx_s = f"{pyx:.3f}" if pyx is not None else " None"
            print(f"  seed={r['seed']} {arm:<6} didx_end={a['compo_didx_end']:.3f} "
                  f"hit_end={a['hit_end']:.3f} P(Y|X)={pyx_s} y_rate={a['y_rate_end']:.3f}")
    out = os.environ.get("SABC_CF_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res
```

Puis ÉTENDRE le bloc d'aiguillage `if __name__ == "__main__":` existant (qui gère déjà `--memory-probe` et `--curriculum`) pour ajouter `--curriculum-fade` :

```python
if __name__ == "__main__":
    import sys as _sys
    if "--memory-probe" in _sys.argv:
        main_memory_probe()
    elif "--curriculum-fade" in _sys.argv:
        main_curriculum_fade()
    elif "--curriculum" in _sys.argv:
        main_curriculum()
    else:
        main()
```

(Remplacer le bloc `__main__` actuel par cette version à 4 branches ; `--curriculum-fade` AVANT `--curriculum` car le second est un sous-mot du premier — l'ordre évite que `--curriculum-fade` matche la branche `--curriculum`.)

- [ ] **Step 14: Vérifier toute la suite du fichier**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -v`
Expected: PASS — purs (dont fade_weight, p_y_given_x) ; slow (dont run_curriculum_fade_keys, compare_curriculum_fade_smoke) PASS si torch présent sinon SKIP propre. `run_curriculum`/`compare_curriculum` (bascule dure) inchangés et verts.

- [ ] **Step 15: Smoke manuel `--curriculum-fade` (petit budget) — EXIT CODE**

Run:
```bash
AGISEED_QUIET_LOG=1 SABC_CF_SEEDS=0 SABC_CF_WARMUP=40 SABC_CF_COMPO=40 SABC_CF_AGENTS=4 \
  SABC_CF_OUT="$TMPDIR/cf_smoke.json" python tools/substrate_ab_compositional.py --curriculum-fade; echo "EXIT=$?"
```
Expected: affiche `VERDICT_FADE=...`, `PER-SEED ...`, `WROTE ...`, puis `EXIT=0`. (torch présent → exécution complète ; sinon le backend torch lèvera, valider via pytest étape 14.)

- [ ] **Step 16: Commit (path-scoped)**

```bash
git add tools/substrate_ab_compositional.py tests/sandbox/test_substrate_ab_compositional.py
git commit -m "feat(sab-compo): curriculum a fade (maintien X decroissant) + mesure P(Y|X) directe

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: RUN du fade + maintien de X + EDR 123 (pas de code)

**Files:**
- Create: `docs/EDR/123_<titre>.md` (vérifier 123 libre ; sinon prochain libre)
- Read-only : sortie (log + JSON `SABC_CF_OUT`)

**Interfaces:**
- Consumes : `compare_curriculum_fade`/`main_curriculum_fade` de Task 1.
- Produces : EDR 123 (verdict CEILING_WAS_RETENTION/BINDING/FADE_INEFFECTIVE, trajectoires, P(Y|X), baseline).

- [ ] **Step 1: Vérifier le numéro d'EDR libre**

Run: `ls docs/EDR/ | grep -E '^12[1-5]'`
Expected : confirmer si `123_*` existe. Si pris, viser le prochain libre et l'annoncer dans l'EDR.

- [ ] **Step 2: Lancer le fade complet — EXIT CODE, JSON dumpé**

Run :
```bash
AGISEED_QUIET_LOG=1 SABC_CF_SEEDS=0,1,2,3,4 SABC_CF_WARMUP=150 SABC_CF_COMPO=250 SABC_CF_AGENTS=8 SABC_CF_W0=1.0 \
  SABC_CF_OUT="results/sab_curriculum_fade.json" \
  python tools/substrate_ab_compositional.py --curriculum-fade > /tmp/cf_run.log 2>&1; echo "EXIT=$?"
```
Expected : `EXIT=0`. Le JSON contient `per_seed` + `summary` + `verdict_fade`.
Garde-fou : si `EXIT≠0`, lire `/tmp/cf_run.log` — NE PAS conclure depuis un log tronqué.

- [ ] **Step 3: Maintien de X (le nouveau contrôle) — valider AVANT le verdict de plafond**

Inspecter torch `compo_didx_end` par seed : il DOIT être nettement PLUS HAUT que la bascule dure
(~0.38 en EDR 122) — viser >0.6. Si le fade ne maintient PAS X (`compo_didx_end` ≈ 0.4 comme la bascule
dure), le fade n'a pas fait son travail → **verdict FADE_INEFFECTIVE**, re-spécifier (w0/schedule). Le
test de plafond n'est lisible QUE si X est maintenu. Reporter `compo_didx_start`→`compo_didx_end`.

- [ ] **Step 4: Baseline `fade_w0=0` (cohérence) — reproduit EDR 122**

```bash
AGISEED_QUIET_LOG=1 SABC_CF_SEEDS=0,1,2 SABC_CF_WARMUP=150 SABC_CF_COMPO=250 SABC_CF_AGENTS=8 SABC_CF_W0=0.0 \
  python tools/substrate_ab_compositional.py --curriculum-fade > /tmp/cf_base.log 2>&1; echo "EXIT=$?"
```
Expected : torch `hit_end` ~0.30 et `compo_didx_end` ~0.38 (X décline) = EDR 122 reproduit (fade_w0=0 ≡ bascule dure). Confirme que le banc fade=0 est cohérent avec l'instrument 122.

- [ ] **Step 5: Lire le verdict (jamais le scalaire nu)**

Comparer fade (w0=1.0) vs baseline (w0=0) sur torch :
- **CEILING_WAS_RETENTION** : X maintenu (didx_end >0.6) ET `hit_end` MONTE au-dessus de 0.30 ET
  **P(Y|X) haut (>0.7)** → le cap de 122 était la rétention de X ; le binding Y|X est résolu.
- **CEILING_WAS_BINDING** : X maintenu (didx_end >0.6) MAIS `hit_end` stagne ~0.30 ET **P(Y|X) modéré
  (~0.5–0.7)** → le binding est partiel, pas seulement la rétention.
- **FADE_INEFFECTIVE** : X non maintenu → re-spec.
legacy en contraste (reste CREDIT : hit_end ~0, P(Y|X) bas). Reporter par bras et par seed :
`compo_didx_end`, `hit_end`, **`p_y_given_x_end`** (la mesure DIRECTE du binding), `y_rate_end`.

- [ ] **Step 6: Écrire EDR 123**

Créer `docs/EDR/123_<titre>.md` selon le moule d'EDR 122 (frontmatter `id/type/title/status/gate/verdict`,
sections Contexte / Méthode (fade linéaire + P(Y|X) direct) / Contrôle maintien de X / Résultats (table
per-seed : compo_didx_end, hit_end, P(Y|X)_end, y_rate + médianes) / Baseline w0=0 / Verdict / Caveats /
Conséquences / Liens). Caveats : seuils heuristiques (verdict lu par l'humain) ; n=5 ; micro-tâche proxy ;
P(Y|X) sur le dernier quart (did_x peut encore bouger) ; reporter `sign_p`. Liens : `[[coop-competence-is-population-property]]`,
`[[sota-gap-substrate]]`, EDR 122/120/119/117.

- [ ] **Step 7: Commit (path-scoped)**

```bash
git add docs/EDR/123_<titre>.md
git commit -m "docs(EDR123): curriculum a fade — verdict <CEILING_WAS_RETENTION|BINDING|FADE_INEFFECTIVE>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes d'exécution

- **Pas de PR-off-main** : le banc importe `backend.py`/`substrate_ab.py` absents d'`origin/main` → le chantier vit sur `feat/d1-prod-pairing` (mêmes contraintes qu'EDR 117/119/120/122).
- Le dump JSON (`SABC_CF_OUT`) protège contre la perte de données log-only (piège EDR 108/113).
- `run_curriculum` (bascule dure) reste l'INSTRUMENT EDR 122 ; ce chantier ajoute le fade À CÔTÉ, sans le toucher.
- Seuils du verdict (0.40/0.60 didx, 0.35 hit, 0.70 P(Y|X)) = heuristiques de cadrage ; le RUN reporte les chiffres bruts, le verdict final est lu par l'humain/contrôleur sur les données.
