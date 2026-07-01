# De-confond p_reach (knob `disable_repro`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exposer le `benchmark_mode` existant dans le harnais forage (`_measure_forage`) pour mesurer un `p_reach` de-confondu du pooling-reproduction, et re-baser les baselines forage d'EDR 105/106.

**Architecture:** Tout dans `tools/lewis_survival_sweep.py` (zero fichier partage -> zero collision avec la session // torch). Un param `disable_repro` a `_measure_forage` pose `env.benchmark_mode = True` apres construction (active le flag monde existant qui coupe les 3 chemins de reproduction). Une matrice 2x2 `main_forage_deconfound` quantifie le confond et donne les baselines corriges.

**Tech Stack:** Python, numpy, pytest. Reutilise `Biosphere3D` (et son `benchmark_mode`), `_measure_forage`, `_cfg`, `Harness`, `seed_at`, `_disable_kuzu`.

## Global Constraints

- **Zero fichier partage** : SEUL `tools/lewis_survival_sweep.py` (+ tests + doc) est modifie. NE PAS toucher `src/environments/config.py` ni `src/worlds/world_1_stoneage.py` (la session // les edite -> conflit de merge). Le flag `benchmark_mode` est pose APRES `Biosphere3D(cfg)` via `env.benchmark_mode = True`.
- **Non-regression** : `disable_repro=False` par defaut -> `_measure_forage` byte-identique ; appelants existants (`main_forage`, `main_approach`) inchangés.
- **`benchmark_mode` existant** : `Biosphere3D.benchmark_mode` (attribut, defaut False) gate les 3 reproductions (energie `world_1_stoneage:1341` ; social/MATE+HGT `:1544`). Le poser a True = cohorte fixe (pas de repro/mutation/HGT) -> pool = cohorte initiale, pas de dilution par nouveau-nes tardifs.
- **`_measure_forage` exige `trace_forage=True` ET `trace_energy_sinks=True`** (co-activer dans `main_forage_deconfound`).
- **ASCII-only dans tout `print` execute** (Windows cp1252) : `->` ASCII OK, pas de fleche unicode/accents.
- **Provenance** : harnais `name="lewis_forage_deconfound"` (JSON distinct) ; seed reel 1140 ; smoke 99140 distinct. Run reel APRES revue ; AUCUN test relancé apres.
- **Verdict** : `CONFOND CONFIRME` si ratio figees (no-repro / repro) >= 1.5 ; `CONFOND NEGLIGEABLE` si < 1.5 ; `INDETERMINE` si cellule figee absente.

---

### Task 1: harnais de-confond — `disable_repro` + verdict + report + entry point

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (param a `_measure_forage` ~l.370/385 ; ajouter 3 fonctions apres `main_approach`)
- Test: `tests/sandbox/test_p_reach_deconfound.py` (creer)

**Interfaces:**
- Consumes: `_measure_forage(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150)` (l.370) ; renvoie dict avec cles `p_reach, p_cap, mean_min_dist, n_agents, reached_raw, ...` ; `Biosphere3D.benchmark_mode` (attribut existant) ; `_cfg(forage_payoff, ..., trace_energy_sinks, trace_forage, prey_speed_scale)` ; `Harness`, `seed_at`, `_disable_kuzu`, `np`.
- Produces:
  - `_measure_forage(..., disable_repro=False)` : pose `env.benchmark_mode = True` si `disable_repro`.
  - `_verdict_deconfound(aggs) -> str` (aggs = liste `(disable_repro: bool, speed: float, agg: dict)`).
  - `_report_deconfound(h, aggs, R, n_eval, _return) -> dict|None`.
  - `main_forage_deconfound(speeds=(1.0, 0.0), n_eval=8, R=1, seed=1140, _return=False)`.

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_p_reach_deconfound.py` :

```python
from tools.lewis_survival_sweep import (_cfg, _measure_forage, _verdict_deconfound,
                                        main_forage_deconfound)


def test_measure_forage_accepts_disable_repro_default_false():
    # signature : disable_repro existe et vaut False par defaut (non-regression).
    import inspect
    sig = inspect.signature(_measure_forage)
    assert "disable_repro" in sig.parameters
    assert sig.parameters["disable_repro"].default is False


def test_disable_repro_freezes_cohort_and_lifts_p_reach():
    # A proies figees, couper la reproduction -> pool BEAUCOUP plus petit (cohorte fixe) ET p_reach
    # plus haut (pas de dilution par nouveau-nes tardifs). Verification directe du mecanisme.
    seeds = [1140 + i for i in range(4)]
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    with_repro = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=False)
    no_repro = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=True)
    assert no_repro["n_agents"] < with_repro["n_agents"], "no-repro doit figer la cohorte (pool plus petit)"
    assert no_repro["p_reach"] > with_repro["p_reach"], "couper la repro doit lever p_reach (de-confond)"


def test_non_regression_disable_repro_false_deterministic():
    seeds = [777 + i for i in range(3)]
    cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=0.0)
    a = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=False)
    b = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=False)
    assert a["p_reach"] == b["p_reach"]
    assert a["n_agents"] == b["n_agents"]


def _agg(p_reach):
    return {"p_reach": p_reach, "p_cap": 1.0, "mean_min_dist": 0.5, "n_agents": 100, "reached_raw": [1, 0]}


def test_verdict_deconfound_branches():
    confirme = [(False, 1.0, _agg(0.18)), (False, 0.0, _agg(0.21)),
                (True, 1.0, _agg(0.30)), (True, 0.0, _agg(0.43))]   # ratio figees 0.43/0.21 = 2.05
    assert _verdict_deconfound(confirme) == "CONFOND CONFIRME"
    negl = [(False, 0.0, _agg(0.40)), (True, 0.0, _agg(0.42))]      # ratio 1.05
    assert _verdict_deconfound(negl) == "CONFOND NEGLIGEABLE"
    assert _verdict_deconfound([(False, 1.0, _agg(0.2)), (True, 1.0, _agg(0.4))]) == "INDETERMINE"


def test_main_forage_deconfound_smoke():
    r = main_forage_deconfound(speeds=(0.0,), n_eval=2, R=1, seed=99140, _return=True)
    assert r["verdict"] in ("CONFOND CONFIRME", "CONFOND NEGLIGEABLE", "INDETERMINE")
    assert len(r["table"]) == 2   # 2 cellules : {repro on/off} x {1 vitesse}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_p_reach_deconfound.py -v`
Expected: FAIL — `disable_repro` absent de la signature ; `ImportError: cannot import name '_verdict_deconfound'`.

- [ ] **Step 3: Add `disable_repro` to `_measure_forage`**

Dans `tools/lewis_survival_sweep.py`, modifier la signature de `_measure_forage` (l.370) pour ajouter `disable_repro=False` en fin :

```python
def _measure_forage(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150, disable_repro=False):
```

Puis, juste apres `env = Biosphere3D(cfg)` (l.385) et avant `_setup_critical(...)`, inserer :

```python
        if disable_repro:
            env.benchmark_mode = True   # cohorte fixe : coupe repro energie/MATE/HGT -> de-confond p_reach (pas de dilution par nouveau-nes tardifs)
```

- [ ] **Step 4: Implement `_verdict_deconfound`, `_report_deconfound`, `main_forage_deconfound`**

Ajouter dans `tools/lewis_survival_sweep.py`, apres `main_approach` :

```python
def _verdict_deconfound(aggs):
    """De-confond p_reach : compare la cellule FIGEE (speed=0) sans-repro vs avec-repro.
    CONFOND CONFIRME si ratio (no-repro / repro) >= 1.5 (deflation par pooling reelle) ; CONFOND
    NEGLIGEABLE si < 1.5 ; INDETERMINE si une des deux cellules figees manque. aggs = liste
    (disable_repro, speed, agg)."""
    repro = next((a for d, s, a in aggs if d is False and s == 0.0), None)
    norepro = next((a for d, s, a in aggs if d is True and s == 0.0), None)
    if repro is None or norepro is None:
        return "INDETERMINE"
    ratio = norepro["p_reach"] / max(repro["p_reach"], 1e-9)
    return "CONFOND CONFIRME" if ratio >= 1.5 else "CONFOND NEGLIGEABLE"


def _report_deconfound(h, aggs, R, n_eval, _return):
    """Table 2x2 (1 ligne/cellule : disable_repro, speed, p_reach, p_cap, min_dist, n) + facteur de
    deflation par vitesse (no-repro / repro) + verdict. reached_raw retire avant save. Tout ASCII."""
    verdict = _verdict_deconfound(aggs)
    print("\n=== De-confond p_reach (benchmark_mode = cohorte fixe) ===")
    print("  disable_repro | speed | p_reach p_cap | min_dist | n")
    for d, s, a in aggs:
        print(f"  {str(bool(d)):<13} | {s:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['mean_min_dist']:8.2f} | {a['n_agents']}")
    for s in sorted({s for _, s, _ in aggs}):
        rp = next((a['p_reach'] for d, sp, a in aggs if d is False and sp == s), None)
        nr = next((a['p_reach'] for d, sp, a in aggs if d is True and sp == s), None)
        if rp is not None and nr is not None:
            print(f"  speed={s:<5.3g} : repro={rp:.3f} -> no-repro={nr:.3f}  (deflation x{nr / max(rp, 1e-9):.2f})")
    print("=== VERDICT (de-confond) ===")
    print(f"  -> {verdict}")
    table = [{"disable_repro": bool(d), "speed": s, **{k: v for k, v in a.items() if k != "reached_raw"}}
             for d, s, a in aggs]
    h.save({"knob": "disable_repro x prey_speed_scale", "R": R, "n_eval": n_eval,
            "verdict": verdict, "table": table})
    if _return:
        return {"verdict": verdict, "table": table, "R": R, "n_eval": n_eval}


def main_forage_deconfound(speeds=(1.0, 0.0), n_eval=8, R=1, seed=1140, _return=False):
    """De-confond p_reach : matrice 2x2 {disable_repro False/True} x {prey_speed mobiles/figees}, politique
    APPRISE (replicas _load_champions), a N_APEX=0/metab=0/forage_payoff=3, SANS evolution. Quantifie la
    deflation de p_reach par pooling-reproduction et donne les baselines corriges (re-base EDR 105/106)."""
    with Harness(seed=seed, name="lewis_forage_deconfound", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"De-confond p_reach : speeds={speeds}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]   # memes seeds/cellule
        prog = h.progress(2 * len(speeds), label="cellules (disable_repro x speed)")
        aggs = []
        for disable_repro in (False, True):
            for s in speeds:
                cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True,
                           prey_speed_scale=s)
                aggs.append((disable_repro, s,
                             _measure_forage(cfg, seeds, n_apex=0, max_ticks=150, disable_repro=disable_repro)))
                prog.update()
        return _report_deconfound(h, aggs, R, n_eval, _return)
```

- [ ] **Step 5: Run the full test file**

Run: `python -m pytest tests/sandbox/test_p_reach_deconfound.py -v`
Expected: PASS (5/5). `test_disable_repro_freezes_cohort_and_lifts_p_reach` et le smoke sont un peu lents (sims forage) mais doivent passer.

- [ ] **Step 6: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_p_reach_deconfound.py
git commit -m "feat(tooling): disable_repro de-confond p_reach (benchmark_mode) + main_forage_deconfound (matrice 2x2)"
```

---

### Task 2: Run reel + doc 114b + memoire (controleur, APRES revue de code)

> **Non-TDD.** Execute par le controleur une fois Task 1 revue. AUCUN test relancé apres le run reel.

**Files:**
- Create: `docs/EDR/114b_P_Reach_Deconfound_Corrected_Forage_Baselines.md`
- Modify (memoire, hors worktree) : `lewis-energy-economy-wall.md`

- [ ] **Step 1: Lancer le run reel (seed 1140, 2x2, n_eval=8)**

Run: `python -c "from tools.lewis_survival_sweep import main_forage_deconfound; main_forage_deconfound()"`
Expected: table 4 cellules (disable_repro False/True x speed 1.0/0.0), facteur de deflation par vitesse, verdict. Capturer le stdout (provenance ; `results/lewis_forage_deconfound_1140.json` gitignore). **Controle** : la cellule (False, figees) doit reproduire ~0.21 (EDR 106) ; (True, figees) doit monter (~0.43 attendu d'apres diag EDR 114).

- [ ] **Step 2: Re-lancer une fois pour confirmer le determinisme**

Run: meme commande. Expected: table identique a Step 1. Si divergence -> investiguer (memory_retriever ?) avant de rediger.

- [ ] **Step 3: Rediger le doc 114b**

Creer `docs/EDR/114b_P_Reach_Deconfound_Corrected_Forage_Baselines.md` : addendum a EDR 114 ; rappel du confond pooling-reproduction (deflation 2-4x) ; TABLE 2x2 corrigee (avec-repro confondu ~ EDR 105/106 vs sans-repro corrige) ; facteur de deflation par vitesse ; outil `disable_repro` (cable `benchmark_mode` existant) ; re-base EXPLICITE des baselines 105/106 (qualitatif intact — le mur reste le substrat, EDR 114 apprise 0.43 ≪ oracle 0.875 — magnitudes corrigees). Tout ASCII dans les blocs de donnees.

- [ ] **Step 4: Mettre a jour la memoire**

Dans `lewis-energy-economy-wall.md` : noter les p_reach corriges (apprise figees ~0.43 vs replica confondu 0.21 ; mobiles corrige = chiffre du run) et que l'outil de de-confond est cable (`disable_repro` dans `_measure_forage` / `main_forage_deconfound`). Lien [[lewis-energy-economy-wall]].

- [ ] **Step 5: Commit doc**

```bash
git add docs/EDR/114b_*.md
git commit -m "docs(114b): baselines forage p_reach corriges (de-confond pooling-reproduction)"
```

---

## Notes de revue (pour le reviewer final)

- **Zero fichier partage** : `git diff origin/main -- src/` doit etre VIDE. Seuls `tools/lewis_survival_sweep.py` + tests + `docs/` changent. (Coordination session // torch.)
- **Non-regression** : `disable_repro=False` defaut -> `_measure_forage` inchange ; l'insertion est gardee `if disable_repro:`.
- **Mecanisme** : `env.benchmark_mode = True` pose APRES `Biosphere3D(cfg)` (le flag existe deja, gate les 3 repro). Le test `test_disable_repro_freezes_cohort_and_lifts_p_reach` prouve l'effet (pool plus petit + p_reach plus haut).
- **Verdict** : ratio figees (no-repro/repro) >= 1.5 -> CONFOND CONFIRME ; coherent spec section 3.3. Les 3 branches testees.
- **ASCII** : grep les `print` ajoutes.
- **Seeds** : run reel 1140 ; smoke 99140 distinct (provenance ; nom de harnais distinct aussi).
