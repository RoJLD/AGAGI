# Curriculum compositionnel — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trancher crédit (H2) vs découverte (H3) du verrou compositionnel : enseigner X seul (dense) en phase A puis tester Y|X compositionnel en phase B (bascule dure), sur le banc `substrate_ab_compositional`.

**Architecture:** Tâche 1 (BUILD) ajoute `run_curriculum` (2 phases) + `compare_curriculum` (A/B + verdict) + `main_curriculum` à `tools/substrate_ab_compositional.py`, avec tests purs + smoke. Tâche 2 (RUN, pas de code) exécute legacy+torch ×5 seeds, vérifie l'efficacité de la phase A (did_x monte) et le baseline planché, et écrit EDR 121 (DISCOVERY/CREDIT/WARMUP_FAILED).

**Tech Stack:** Python 3.13, numpy, PyTorch (backend torch), pytest. Pas de nouvelle dépendance.

## Global Constraints

- Commits **path-scoped** uniquement (`git add <chemins exacts>`, jamais `-A`/`.`/bare) — tree partagé sur `feat/d1-prod-pairing`.
- **NE PAS modifier** `src/agents/backend.py`, `src/agents/backend_torch.py`, `tools/substrate_ab.py`. On IMPORTE / réutilise `make_population`, `MambaAgent`, `compute_ab_verdict`, `_MOVE`, `_build_agents`, `compositional_reward`.
- Quiet-log : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- Détection de succès **par EXIT CODE python**, jamais grep sur log redirigé (piège EDR 108).
- **Bascule DURE** : phase B = compositionnel pur (S1 reward 0). Pas de shaping décroissant.
- `obs_a` et `obs_b` FIXES (mêmes vecteurs dans les deux phases) ; `obs_a` partagé A↔B (le X appris se réutilise).
- Phase A reward = `+1.0 si did_x sinon −1.0` ; phase B reward S2 = `compositional_reward` existant ; phase B reward S1 = 0.0 (différé).
- Jamais de scalaire nu : trajectoires (warmup_didx_start/end, hit_start/end, compo_didx_start/end) par seed + médianes.
- Ne JAMAIS toucher aux artefacts runtime concurrents (`data/state.json`, `data/articles.json`, `tests/test_kuzudb`, `results/*` d'autres sessions). Dump JSON via `SABC_CU_OUT`.
- EDR cible = **121** : vérifier libre à l'écriture (collisions, tree partagé).

---

### Task 1: `run_curriculum` + `compare_curriculum` + `main_curriculum`

**Files:**
- Modify: `tools/substrate_ab_compositional.py` (ajout de 3 fonctions + aiguillage `--curriculum`)
- Test: `tests/sandbox/test_substrate_ab_compositional.py` (tests purs + smoke slow)

**Interfaces:**
- Consumes (déjà dans le fichier) : `MambaAgent`, `make_population`, `compute_ab_verdict`, `_MOVE`, `_build_agents`, `compositional_reward`, `import numpy as np`, `import statistics`, `import os`, `import sys`.
- Produces :
  - `run_curriculum(backend, seed=0, warmup_trials=150, compo_trials=250, n_agents=8, target_x=0, target_y=4) -> dict`
  - `compare_curriculum(seeds=(0,1,2,3,4), warmup_trials=150, compo_trials=250, n_agents=8) -> dict` (clés de `compute_ab_verdict` + `per_seed` + `verdict_curriculum`)
  - `main_curriculum()` (env `SABC_CU_*`, dump JSON `SABC_CU_OUT`)

- [ ] **Step 1: Écrire le test pur de la récompense de warmup + structure**

Ajouter à la fin de `tests/sandbox/test_substrate_ab_compositional.py` :

```python
def test_warmup_reward_rule():
    """Phase A (warmup) : reward = +1 si l'action == target_x (did_x), sinon −1. Pur."""
    from tools.substrate_ab_compositional import _warmup_reward
    assert _warmup_reward(move1=0, target_x=0) == 1.0
    assert _warmup_reward(move1=3, target_x=0) == -1.0
    assert _warmup_reward(move1=4, target_x=4) == 1.0


@pytest.mark.slow
def test_run_curriculum_warmup0_is_compositional():
    """warmup_trials=0 → phase A vide → run_curriculum exécute la phase B seule (plancher compo)."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import run_curriculum
    r = run_curriculum("legacy", seed=0, warmup_trials=0, compo_trials=40, n_agents=4)
    # warmup vide → did_x de warmup non défini/neutre ; les clés existent et hit ∈ [0,1]
    for k in ("warmup_didx_end", "hit_start", "hit_end", "compo_didx_end", "delta"):
        assert k in r
    assert 0.0 <= r["hit_end"] <= 1.0
```

- [ ] **Step 2: Lancer → échec (`_warmup_reward` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "warmup_reward" -v`
Expected: FAIL avec `ImportError: cannot import name '_warmup_reward'`.

- [ ] **Step 3: Implémenter `_warmup_reward` + `run_curriculum`**

Dans `tools/substrate_ab_compositional.py`, après la fonction `run_compositional` (et avant `compare`), insérer :

```python
def _warmup_reward(move1: int, target_x: int) -> float:
    """Phase A : récompense DENSE directe sur l'action X de S1. +1 si did_x, −1 sinon. PURE."""
    return 1.0 if move1 == target_x else -1.0


def run_curriculum(backend: str, seed: int = 0, warmup_trials: int = 150, compo_trials: int = 250,
                   n_agents: int = 8, target_x: int = 0, target_y: int = 4) -> dict:
    """Curriculum 2 phases (bascule dure). Phase A : enseigner X (reward dense did_x, S1 seul).
    Phase B : compositionnel pur (S1 reward 0, S2 reward Y|X). Trace l'efficacité (warmup did_x),
    le hit compositionnel (phase B) et la rétention de X en phase B. warmup_trials=0 → phase B seule."""
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
    obs_a = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)    # S1 fixe (partagé A/B)
    obs_b = (rng.randn(n_agents, n_in) * 0.5).astype(np.float32)    # S2 fixe

    # --- Phase A : warmup dense sur X (S1 seul) ---
    warm = []
    for _ in range(warmup_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        reward = np.array([_warmup_reward(int(m), target_x) for m in move1], dtype=np.float32)
        pop.learn(reward, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])
        warm.append(float(np.mean(did_x)))
    qa = max(1, warmup_trials // 4) if warmup_trials else 0
    warmup_didx_start = float(np.mean(warm[:qa])) if qa else 0.0
    warmup_didx_end = float(np.mean(warm[-qa:])) if qa else 0.0

    # --- Phase B : compositionnel pur (bascule dure) ---
    hit, bx = [], []
    zeros = np.zeros(n_agents, dtype=np.float32)
    for _ in range(compo_trials):
        preds1, _ = pop.forward(obs_a)
        move1 = np.asarray(preds1)[:, :_MOVE].argmax(axis=1)
        did_x = (move1 == target_x)
        pop.learn(zeros, [{"move": int(m), "grab": 0, "rub": 0} for m in move1])   # S1 différé (0)
        preds2, _ = pop.forward(obs_b)
        move2 = np.asarray(preds2)[:, :_MOVE].argmax(axis=1)
        reward2 = np.array([compositional_reward(int(move2[i]), target_y, bool(did_x[i]))
                            for i in range(n_agents)], dtype=np.float32)
        pop.learn(reward2, [{"move": int(m), "grab": 0, "rub": 0} for m in move2])
        hit.append(float(np.mean((move2 == target_y) & did_x)))
        bx.append(float(np.mean(did_x)))
    qb = max(1, compo_trials // 4)
    hit_start, hit_end = float(np.mean(hit[:qb])), float(np.mean(hit[-qb:]))
    compo_didx_start, compo_didx_end = float(np.mean(bx[:qb])), float(np.mean(bx[-qb:]))
    return {"backend": backend, "seed": int(seed), "warmup_trials": warmup_trials,
            "compo_trials": compo_trials, "n_agents": n_agents,
            "warmup_didx_start": warmup_didx_start, "warmup_didx_end": warmup_didx_end,
            "hit_start": hit_start, "hit_end": hit_end,
            "compo_didx_start": compo_didx_start, "compo_didx_end": compo_didx_end,
            "delta": hit_end - hit_start}
```

- [ ] **Step 4: Lancer → succès (test pur)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "warmup_reward" -v`
Expected: PASS.

- [ ] **Step 5: Lancer le test slow warmup=0**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_run_curriculum_warmup0_is_compositional -v`
Expected: PASS (torch présent ; sinon SKIP propre).

- [ ] **Step 6: Écrire le smoke test de `compare_curriculum`**

Ajouter à la fin du fichier de test :

```python
@pytest.mark.slow
def test_compare_curriculum_smoke():
    """compare_curriculum renvoie un verdict curriculum structuré + per_seed avec les trajectoires."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import compare_curriculum
    res = compare_curriculum(seeds=(0,), warmup_trials=40, compo_trials=40, n_agents=4)
    assert res["verdict_curriculum"] in {"DISCOVERY", "CREDIT", "WARMUP_FAILED", "AMBIGU"}
    assert res["per_seed"] and len(res["per_seed"]) == 1
    row = res["per_seed"][0]
    for k in ("legacy", "torch"):
        for kk in ("warmup_didx_end", "hit_end", "compo_didx_end"):
            assert kk in row[k]
```

- [ ] **Step 7: Lancer → échec (`compare_curriculum` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_compare_curriculum_smoke -v`
Expected: FAIL avec `ImportError: cannot import name 'compare_curriculum'`.

- [ ] **Step 8: Implémenter `compare_curriculum`**

Dans `tools/substrate_ab_compositional.py`, après `run_curriculum`, insérer :

```python
def compare_curriculum(seeds=(0, 1, 2, 3, 4), warmup_trials: int = 150,
                       compo_trials: int = 250, n_agents: int = 8) -> dict:
    """A/B apparié legacy vs torch du curriculum. Verdict_curriculum :
    WARMUP_FAILED si did_x ne monte pas en warmup (médiane warmup_didx_end ≤ 0.30 sur un bras) ;
    DISCOVERY si warmup réussit ET hit_end médian décolle (> 0.30) sur ≥1 bras ;
    CREDIT si warmup réussit MAIS hit_end médian reste planché (≤ 0.15) sur les DEUX bras ;
    sinon AMBIGU. Seuils heuristiques (le verdict final est lu par l'humain sur les chiffres)."""
    rows = []
    for s in seeds:
        leg = run_curriculum("legacy", seed=s, warmup_trials=warmup_trials,
                             compo_trials=compo_trials, n_agents=n_agents)
        tor = run_curriculum("torch", seed=s, warmup_trials=warmup_trials,
                             compo_trials=compo_trials, n_agents=n_agents)
        rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                     "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})

    def _med(arm, key):
        return statistics.median([r[arm][key] for r in rows])

    leg_warm, tor_warm = _med("legacy", "warmup_didx_end"), _med("torch", "warmup_didx_end")
    leg_hit, tor_hit = _med("legacy", "hit_end"), _med("torch", "hit_end")
    warmup_ok = (leg_warm > 0.30) and (tor_warm > 0.30)
    if not warmup_ok:
        verdict_c = "WARMUP_FAILED"
    elif leg_hit > 0.30 or tor_hit > 0.30:
        verdict_c = "DISCOVERY"
    elif leg_hit <= 0.15 and tor_hit <= 0.15:
        verdict_c = "CREDIT"
    else:
        verdict_c = "AMBIGU"
    return {**compute_ab_verdict(rows), "verdict_curriculum": verdict_c,
            "summary": {"legacy_warmup_didx_end": leg_warm, "torch_warmup_didx_end": tor_warm,
                        "legacy_hit_end": leg_hit, "torch_hit_end": tor_hit},
            "per_seed": rows}
```

- [ ] **Step 9: Lancer le smoke → succès**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_compare_curriculum_smoke -v`
Expected: PASS.

- [ ] **Step 10: Implémenter `main_curriculum` + aiguillage**

Dans `tools/substrate_ab_compositional.py`, après `compare_curriculum`, insérer :

```python
def main_curriculum():
    seeds = [int(s) for s in os.environ.get("SABC_CU_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    warmup = int(os.environ.get("SABC_CU_WARMUP", "150"))
    compo = int(os.environ.get("SABC_CU_COMPO", "250"))
    n_agents = int(os.environ.get("SABC_CU_AGENTS", "8"))
    res = compare_curriculum(seeds=tuple(seeds), warmup_trials=warmup,
                             compo_trials=compo, n_agents=n_agents)
    print(f"VERDICT_CURRICULUM={res['verdict_curriculum']}  summary={res['summary']}")
    print("PER-SEED (warmup_didx_end -> hit_end ; compo_didx retention):")
    for r in res["per_seed"]:
        for arm in ("legacy", "torch"):
            a = r[arm]
            print(f"  seed={r['seed']} {arm:<6} warmup_didx={a['warmup_didx_end']:.3f} "
                  f"hit_end={a['hit_end']:.3f} compo_didx {a['compo_didx_start']:.3f}->{a['compo_didx_end']:.3f}")
    out = os.environ.get("SABC_CU_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res
```

Puis ÉTENDRE le bloc d'aiguillage `if __name__ == "__main__":` existant (qui gère déjà `--memory-probe`) pour ajouter `--curriculum` :

```python
if __name__ == "__main__":
    import sys as _sys
    if "--memory-probe" in _sys.argv:
        main_memory_probe()
    elif "--curriculum" in _sys.argv:
        main_curriculum()
    else:
        main()
```

(Remplacer le bloc `__main__` actuel par cette version à 3 branches ; `main` (sweep) reste le défaut.)

- [ ] **Step 11: Vérifier toute la suite du fichier**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -v`
Expected: PASS — purs (truth_table, init_factor×2, build_agents×2, decode_auc×3, read_state_legacy, normalized_anchor, warmup_reward) ; slow (compositional_ab_smoke, sweep_smoke, read_state_torch, memory_probe_smoke, run_curriculum_warmup0, compare_curriculum_smoke) PASS si torch présent sinon SKIP propre.

- [ ] **Step 12: Smoke manuel `--curriculum` (petit budget) — EXIT CODE**

Run:
```bash
AGISEED_QUIET_LOG=1 SABC_CU_SEEDS=0 SABC_CU_WARMUP=40 SABC_CU_COMPO=40 SABC_CU_AGENTS=4 \
  SABC_CU_OUT="$TMPDIR/cu_smoke.json" python tools/substrate_ab_compositional.py --curriculum; echo "EXIT=$?"
```
Expected: affiche `VERDICT_CURRICULUM=...`, `PER-SEED ...`, `WROTE ...`, puis `EXIT=0`. (torch présent dans l'env → exécution complète ; sinon le backend torch lèvera et on valide via la suite pytest de l'étape 11.)

- [ ] **Step 13: Commit (path-scoped)**

```bash
git add tools/substrate_ab_compositional.py tests/sandbox/test_substrate_ab_compositional.py
git commit -m "feat(sab-compo): curriculum 2 phases (warmup X dense -> compo Y|X, bascule dure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: RUN du curriculum + efficacité phase A + EDR 121 (pas de code)

**Files:**
- Create: `docs/EDR/121_<titre>.md` (vérifier 121 libre ; sinon prochain libre)
- Read-only : sortie du curriculum (log + JSON `SABC_CU_OUT`)

**Interfaces:**
- Consumes : `compare_curriculum`/`main_curriculum` de Task 1.
- Produces : EDR 121 (verdict DISCOVERY/CREDIT/WARMUP_FAILED documenté, trajectoires, efficacité phase A, baseline).

- [ ] **Step 1: Vérifier le numéro d'EDR libre**

Run: `ls docs/EDR/ | grep -E '^1(19|2[0-4])'`
Expected : confirmer si `121_*` existe. Si pris, viser le prochain libre et l'annoncer dans l'EDR.

- [ ] **Step 2: Lancer le curriculum complet — EXIT CODE, JSON dumpé**

Run (chemin JSON dédié) :
```bash
AGISEED_QUIET_LOG=1 SABC_CU_SEEDS=0,1,2,3,4 SABC_CU_WARMUP=150 SABC_CU_COMPO=250 SABC_CU_AGENTS=8 \
  SABC_CU_OUT="results/sab_curriculum.json" \
  python tools/substrate_ab_compositional.py --curriculum > /tmp/cu_run.log 2>&1; echo "EXIT=$?"
```
Expected : `EXIT=0` (succès par le CODE). Le JSON contient `per_seed` + `summary` + `verdict_curriculum`.
Garde-fou : si `EXIT≠0`, lire `/tmp/cu_run.log` — NE PAS conclure depuis un log tronqué.

- [ ] **Step 3: Efficacité phase A (le héros) — valider AVANT le verdict**

Inspecter `warmup_didx_end` par bras/seed : il DOIT monter nettement au-dessus du base-rate ~1/8
(≈0.125) — viser ≫0.30. Si le warmup ne monte pas (`warmup_didx_end` ≈ base-rate), le curriculum n'a
pas décollé → **SUSPENDRE le verdict** (WARMUP_FAILED) et investiguer (l'apprentissage de X échoue même
en dense, contradiction avec EDR 115 à creuser). Reporter `warmup_didx_start`→`warmup_didx_end`.

- [ ] **Step 4: Baseline + lecture du verdict (jamais le scalaire nu)**

(a) **Baseline cohérence** : lancer un point `warmup=0` (ou réutiliser EDR 117/119) → `hit_end` doit
être au plancher (~0–0.15), confirmant que sans curriculum la compo échoue.
```bash
AGISEED_QUIET_LOG=1 SABC_CU_SEEDS=0,1,2 SABC_CU_WARMUP=0 SABC_CU_COMPO=250 SABC_CU_AGENTS=8 \
  python tools/substrate_ab_compositional.py --curriculum > /tmp/cu_base.log 2>&1; echo "EXIT=$?"
```
(b) **Verdict** (curriculum warmup=150 vs baseline) :
- **DISCOVERY** : warmup réussit (did_x↑) ET `hit_end` décolle (>0.3) vs baseline planché → le verrou
  était la découverte (sparse reward) → shaping du craft actionnable en prod.
- **CREDIT** : warmup réussit MAIS `hit_end` reste planché (≤0.15) → même avec X maîtrisé + mémoire
  (120) + chemin dense, la règle ne binde pas → mécanisme de crédit plus profond (TD(λ)/éligibilité).
- **WARMUP_FAILED** : did_x ne monte pas → re-spec.
Reporter aussi la **rétention X** en phase B (`compo_didx_start`→`compo_didx_end`) : décline-t-il une
fois S1 reward 0 ? (informatif sur le maintien du means par le crédit différé). Par bras et par seed.

- [ ] **Step 5: Écrire EDR 121**

Créer `docs/EDR/121_<titre>.md` selon le moule d'EDR 120 (frontmatter `id/type/title/status/gate/verdict`,
sections Contexte / Méthode / Efficacité phase A (le contrôle) / Résultats (table per-seed : warmup_didx,
hit_end, compo_didx rétention, delta + médianes) / Baseline / Verdict / Caveats / Conséquences / Liens).
Caveats : seuils heuristiques (verdict lu par l'humain) ; n=5 ; micro-tâche proxy ; bascule dure (X peut
décliner en B). Liens : `[[coop-competence-is-population-property]]`, `[[sota-gap-substrate]]`, EDR 120/119/117/115.

- [ ] **Step 6: Commit (path-scoped)**

```bash
git add docs/EDR/121_<titre>.md
git commit -m "docs(EDR121): curriculum compositionnel — verdict <DISCOVERY|CREDIT|WARMUP_FAILED>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes d'exécution

- **Pas de PR-off-main** : le banc importe `backend.py`/`substrate_ab.py` absents d'`origin/main` → le chantier vit sur `feat/d1-prod-pairing` (mêmes contraintes qu'EDR 117/119/120).
- Le dump JSON (`SABC_CU_OUT`) protège contre la perte de données log-only (piège EDR 108/113).
- Si torch est absent, Task 2 ne produit pas le bras torch : signaler et différer ; Task 1 reste livrable (slow skippés).
- Seuils du verdict (0.30 warmup / 0.30 hit DISCOVERY / 0.15 hit CREDIT) = heuristiques de cadrage ; le RUN reporte les chiffres bruts, le verdict final est lu par l'humain/contrôleur sur les données.
