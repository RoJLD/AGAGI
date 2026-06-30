# Sweep taille cachée compositionnel — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre le banc compositionnel d'EDR 117 avec un sweep de taille cachée (hidden {5,20,50,100}) en double bras d'init (prod / normalisé 1/√N) pour trancher si la taille, la règle d'apprentissage, ou les deux conjointement verrouillent la learnabilité compositionnelle.

**Architecture:** Tâche 1 (BUILD) ajoute deux paramètres (`num_nodes`, `init_scale`) à `run_compositional`, un helper pur `_init_factor`, un helper `_build_agents`, une fonction `sweep`, et un `main()` qui imprime la table-courbe + dump JSON optionnel — le tout DANS `tools/substrate_ab_compositional.py` (notre fichier). Tâche 2 (RUN, pas de code) exécute le sweep 70 runs, vérifie l'ancrage de cohérence (hidden=5 reproduit EDR 117), lit la courbe hit_end vs taille, et écrit EDR 118 (verdict A/B/C).

**Tech Stack:** Python 3.13, numpy, PyTorch (optionnel, backend torch), pytest. Pas de nouvelle dépendance.

## Global Constraints

- Commits **path-scoped** uniquement (`git add <chemins exacts>`, jamais `-A`/`.`/bare) — tree partagé sur `feat/d1-prod-pairing`.
- **NE PAS modifier** `src/agents/backend.py`, `src/agents/backend_torch.py`, `tools/substrate_ab.py` (propriété session //). On IMPORTE : `make_population`, `MambaAgent`, `compute_ab_verdict`, `_MOVE`.
- Formule init normalisé : `factor = sqrt(171.0 / (num_nodes − 1))` ; à `num_nodes=172` → 1.0 (anchor = prod).
- `hidden = num_nodes − 167` ; I/O fixes (num_inputs=59, num_outputs=108).
- Quiet-log : `AGISEED_QUIET_LOG=1` dans le SHELL avant python.
- Détection de succès **par EXIT CODE python**, jamais grep sur log redirigé (piège EDR 108 : `2>/dev/null` avale TRAJ).
- Ne JAMAIS toucher aux artefacts runtime concurrents (`data/state.json`, `data/articles.json`, `tests/test_kuzudb`, fichiers `results/*` d'autres sessions). Le dump JSON du sweep va à un chemin dédié donné par `SABC_OUT`.
- EDR cible = **118** : vérifier qu'il est libre à l'écriture (collisions possibles, tree partagé).

---

### Task 1: Étendre le banc avec sweep taille + double bras d'init

**Files:**
- Modify: `tools/substrate_ab_compositional.py` (ajout d'imports, params, helpers, `sweep`, `main`)
- Test: `tests/sandbox/test_substrate_ab_compositional.py` (ajout de tests purs + smoke sweep)

**Interfaces:**
- Consumes (déjà présents dans le fichier) : `from src.agents.mamba_agent import MambaAgent`, `from src.agents.backend import make_population`, `from tools.substrate_ab import compute_ab_verdict, _MOVE`. `compositional_reward(move2, target_y, did_x) -> float` et `run_compositional(...)` existent déjà (EDR 117).
- Produces (utilisés par Task 2 + tests) :
  - `_init_factor(num_nodes: int, init_scale: str) -> float`
  - `_build_agents(n_agents: int, num_nodes: int, init_scale: str) -> list` (liste de `MambaAgent`)
  - `run_compositional(backend, seed=0, trials=100, n_agents=8, target_x=0, target_y=4, num_nodes=172, init_scale="prod") -> dict` (clés inchangées : backend/seed/trials/n_agents/hit_start/hit_end/delta)
  - `sweep(hiddens=(5,20,50,100), inits=("prod","normalized"), seeds=(0,1,2,3,4), trials=250, n_agents=8) -> dict` avec clés `cells` (liste) et `curve` (dict `legacy`/`torch`)

- [ ] **Step 1: Écrire les tests purs (helpers d'init + taille)**

Ajouter à la fin de `tests/sandbox/test_substrate_ab_compositional.py` :

```python
import numpy as np

from tools.substrate_ab_compositional import _init_factor, _build_agents


def test_init_factor_anchor_is_one():
    """À num_nodes=172 (hidden=5), le facteur normalisé == 1.0 → normalized ≡ prod (dédup ancrage)."""
    assert _init_factor(172, "normalized") == 1.0
    assert _init_factor(172, "prod") == 1.0


def test_init_factor_normalized_formula():
    """Facteur normalisé = sqrt(171/(N-1)) ; prod toujours 1.0 quelle que soit la taille."""
    assert _init_factor(267, "normalized") == pytest.approx(np.sqrt(171.0 / 266.0))
    assert _init_factor(187, "normalized") == pytest.approx(np.sqrt(171.0 / 186.0))
    assert _init_factor(267, "prod") == 1.0


def test_build_agents_size_mapping():
    """num_nodes contrôle la taille ; I/O restent fixes (59/108) ; hidden = num_nodes-167."""
    agents = _build_agents(3, 187, "prod")
    assert len(agents) == 3
    for a in agents:
        assert a.genome.num_nodes == 187
        assert a.genome.num_inputs == 59
        assert a.genome.num_outputs == 108


def test_build_agents_normalized_scales_W():
    """init normalisé multiplie W par sqrt(171/(N-1)) ; prod laisse W intact (même seed)."""
    np.random.seed(7)
    prod = _build_agents(2, 267, "prod")
    np.random.seed(7)
    norm = _build_agents(2, 267, "normalized")
    factor = np.sqrt(171.0 / 266.0)
    for p, q in zip(prod, norm):
        assert np.allclose(q.genome.W, p.genome.W * factor, atol=1e-5)
```

- [ ] **Step 2: Lancer les tests purs → ils échouent (helpers absents)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "init_factor or build_agents" -v`
Expected: FAIL avec `ImportError: cannot import name '_init_factor'` (ou `_build_agents`).

- [ ] **Step 3: Ajouter `import statistics` + helpers `_init_factor` / `_build_agents`**

Dans `tools/substrate_ab_compositional.py`, après la ligne `import numpy as np` (ligne 16), ajouter :

```python
import statistics
```

Puis, juste après la fonction `compositional_reward` (après sa ligne `return ...`, ~ligne 30), insérer :

```python
def _init_factor(num_nodes: int, init_scale: str) -> float:
    """Facteur d'échelle d'init des poids. `normalized` = sqrt(171/(N-1)) → maintient la variance
    d'excitation (Σ_{k≠j} H_k W_kj ∝ (N-1)·Var(W)) ≈ invariante à N, calibrée sur N_ref=172.
    À N=172 → 1.0 (anchor identique à prod). `prod` → 1.0 (init MambaAgent intact). PUR."""
    if init_scale == "normalized":
        return float(np.sqrt(171.0 / (num_nodes - 1)))
    return 1.0


def _build_agents(n_agents: int, num_nodes: int, init_scale: str) -> list:
    """Construit n_agents MambaAgent à `num_nodes` (hidden = num_nodes-167, I/O fixes 59/108),
    puis applique l'échelle d'init au niveau GÉNOME (backend-agnostique : legacy et torch lisent
    le même W). Le caller seed np.random avant d'appeler (déterminisme)."""
    agents = [MambaAgent(num_nodes=num_nodes) for _ in range(n_agents)]
    factor = _init_factor(num_nodes, init_scale)
    if factor != 1.0:
        for a in agents:
            a.genome.W = (a.genome.W * factor).astype(np.float32)
    return agents
```

- [ ] **Step 4: Lancer les tests purs → ils passent**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "init_factor or build_agents" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Câbler `run_compositional` sur `_build_agents` (params num_nodes/init_scale)**

Dans `tools/substrate_ab_compositional.py`, remplacer la signature et la construction d'agents de `run_compositional`.

Remplacer la signature actuelle :

```python
def run_compositional(backend: str, seed: int = 0, trials: int = 100, n_agents: int = 8,
                      target_x: int = 0, target_y: int = 4) -> dict:
```

par :

```python
def run_compositional(backend: str, seed: int = 0, trials: int = 100, n_agents: int = 8,
                      target_x: int = 0, target_y: int = 4,
                      num_nodes: int = 172, init_scale: str = "prod") -> dict:
```

Puis remplacer la ligne de construction (actuellement `agents = [MambaAgent() for _ in range(n_agents)]`) par :

```python
    agents = _build_agents(n_agents, num_nodes, init_scale)
```

(Le reste de la fonction — obs_a/obs_b dérivés de `agents[0].genome.num_inputs`, boucle trials, calcul hit_start/hit_end/delta — reste inchangé : I=59 quelle que soit la taille.)

- [ ] **Step 6: Vérifier la non-régression de la signature (les défauts préservent EDR 117)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -k "truth_table" -v`
Expected: PASS (`test_compositional_reward_truth_table` inchangé).

- [ ] **Step 7: Écrire le smoke test du sweep**

Ajouter à la fin de `tests/sandbox/test_substrate_ab_compositional.py` :

```python
@pytest.mark.slow
def test_sweep_smoke():
    """sweep renvoie une cellule par (hidden,init) avec verdict structuré + courbe non vide."""
    pytest.importorskip("torch")
    from tools.substrate_ab_compositional import sweep
    res = sweep(hiddens=(5, 20), inits=("prod",), seeds=(0,), trials=20, n_agents=4)
    assert res["cells"] and len(res["cells"]) == 2
    for c in res["cells"]:
        assert c["verdict"] in {"GRADIENT_GAGNE", "HEBBIEN_GAGNE", "NEUTRE"}
        assert c["hidden"] in (5, 20) and c["init"] == "prod"
        assert c["per_seed"] and len(c["per_seed"]) == 1
    assert len(res["curve"]["legacy"]) == 2 and len(res["curve"]["torch"]) == 2
    assert all("median_hit_end" in p for p in res["curve"]["torch"])
```

- [ ] **Step 8: Lancer le smoke sweep → il échoue (`sweep` absent)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_sweep_smoke -v`
Expected: FAIL avec `ImportError: cannot import name 'sweep'`.

- [ ] **Step 9: Implémenter `sweep` (avec déduplication de l'ancrage)**

Dans `tools/substrate_ab_compositional.py`, après la fonction `compare` (qui reste inchangée, utilisée par `test_compositional_ab_smoke`), insérer :

```python
def sweep(hiddens=(5, 20, 50, 100), inits=("prod", "normalized"),
          seeds=(0, 1, 2, 3, 4), trials: int = 250, n_agents: int = 8) -> dict:
    """Grille A/B legacy↔torch par cellule (hidden, init). Déduplique normalized@5 == prod@5
    (même facteur 1.0). Renvoie {cells, curve} ; curve = hit_end médian par taille et backend
    (lecture décisive A/B/C). Jamais de scalaire nu : per_seed conservé par cellule."""
    cells = []
    curve = {"legacy": [], "torch": []}
    seen = set()
    for hidden in hiddens:
        num_nodes = 167 + hidden
        for init in inits:
            factor = round(_init_factor(num_nodes, init), 6)
            key = (hidden, factor)            # dédup : normalized@anchor (factor 1.0) == prod
            if key in seen:
                continue
            seen.add(key)
            rows = []
            for s in seeds:
                leg = run_compositional("legacy", seed=s, trials=trials, n_agents=n_agents,
                                        num_nodes=num_nodes, init_scale=init)
                tor = run_compositional("torch", seed=s, trials=trials, n_agents=n_agents,
                                        num_nodes=num_nodes, init_scale=init)
                rows.append({"seed": int(s), "legacy_delta": leg["delta"], "torch_delta": tor["delta"],
                             "diff": tor["delta"] - leg["delta"], "legacy": leg, "torch": tor})
            verdict = compute_ab_verdict(rows)
            cells.append({"hidden": hidden, "init": init, **verdict, "per_seed": rows})
            curve["legacy"].append({"hidden": hidden, "init": init,
                                    "median_hit_end": statistics.median([r["legacy"]["hit_end"] for r in rows]),
                                    "median_delta": statistics.median([r["legacy_delta"] for r in rows])})
            curve["torch"].append({"hidden": hidden, "init": init,
                                   "median_hit_end": statistics.median([r["torch"]["hit_end"] for r in rows]),
                                   "median_delta": statistics.median([r["torch_delta"] for r in rows])})
    return {"cells": cells, "curve": curve}
```

- [ ] **Step 10: Lancer le smoke sweep → il passe**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py::test_sweep_smoke -v`
Expected: PASS.

- [ ] **Step 11: Mettre à jour `main()` (env knobs + table-courbe + dump JSON optionnel)**

Dans `tools/substrate_ab_compositional.py`, remplacer entièrement la fonction `main()` actuelle par :

```python
def main():
    hiddens = [int(h) for h in os.environ.get("SABC_HIDDENS", "5,20,50,100").split(",") if h.strip()]
    inits = [x.strip() for x in os.environ.get("SABC_INITS", "prod,normalized").split(",") if x.strip()]
    seeds = [int(s) for s in os.environ.get("SABC_SEEDS", "0,1,2,3,4").split(",") if s.strip()]
    trials = int(os.environ.get("SABC_TRIALS", "250"))
    n_agents = int(os.environ.get("SABC_AGENTS", "8"))
    res = sweep(hiddens=hiddens, inits=inits, seeds=seeds, trials=trials, n_agents=n_agents)
    print("CELLS (hidden x init -> verdict, median diff, hit_end medians):")
    for c in res["cells"]:
        leg_he = statistics.median([r["legacy"]["hit_end"] for r in c["per_seed"]])
        tor_he = statistics.median([r["torch"]["hit_end"] for r in c["per_seed"]])
        print(f"  hidden={c['hidden']:>3} init={c['init']:<10} verdict={c['verdict']:<14} "
              f"median_diff={c['median_diff']:+.3f} sign_p={c['sign_p']:.3f} "
              f"legacy_hit_end={leg_he:.3f} torch_hit_end={tor_he:.3f}")
    print("CURVE legacy:", [(p["hidden"], p["init"], round(p["median_hit_end"], 3)) for p in res["curve"]["legacy"]])
    print("CURVE torch :", [(p["hidden"], p["init"], round(p["median_hit_end"], 3)) for p in res["curve"]["torch"]])
    out = os.environ.get("SABC_OUT")
    if out:
        import json
        with open(out, "w") as f:
            json.dump(res, f, indent=2)
        print(f"WROTE {out}")
    return res
```

- [ ] **Step 12: Vérifier toute la suite du fichier (non-régression + nouveaux)**

Run: `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_substrate_ab_compositional.py -v`
Expected: PASS — `test_compositional_reward_truth_table`, `test_init_factor_anchor_is_one`, `test_init_factor_normalized_formula`, `test_build_agents_size_mapping`, `test_build_agents_normalized_scales_W` ; les `slow` (`test_compositional_ab_smoke`, `test_sweep_smoke`) PASS si torch installé, sinon SKIP propre.

- [ ] **Step 13: Smoke manuel du `main` (table + JSON, petit budget) — détection par EXIT CODE**

Run:
```bash
AGISEED_QUIET_LOG=1 SABC_HIDDENS=5,20 SABC_INITS=prod SABC_SEEDS=0 SABC_TRIALS=20 SABC_AGENTS=4 \
  SABC_OUT="$TMPDIR/sab_sweep_smoke.json" python tools/substrate_ab_compositional.py; echo "EXIT=$?"
```
Expected: affiche `CELLS`/`CURVE legacy`/`CURVE torch`/`WROTE ...`, puis `EXIT=0`. (Si torch absent : le run lèvera sur le backend torch — c'est attendu hors environnement torch ; dans ce cas, valider seulement la suite pytest de l'étape 12 et noter que le RUN de Task 2 exige torch.)

- [ ] **Step 14: Commit (path-scoped)**

```bash
git add tools/substrate_ab_compositional.py tests/sandbox/test_substrate_ab_compositional.py
git commit -m "feat(sab-compo): sweep taille cachee + double bras init (prod/normalise)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: RUN du sweep + ancrage de cohérence + EDR 118 (pas de code)

**Files:**
- Create: `docs/EDR/118_<titre>.md` (vérifier 118 libre ; sinon prochain libre)
- Read-only : sortie du sweep (log + JSON `SABC_OUT`)

**Interfaces:**
- Consumes : `sweep`/`main` de Task 1 ; `tools/substrate_ab.py` (run de contrôle mono-étape, déjà existant) pour comparer la dureté si besoin.
- Produces : EDR 118 (verdict A/B/C documenté, table-courbe, per-seed, caveats).

- [ ] **Step 1: Vérifier le numéro d'EDR libre**

Run: `ls docs/EDR/ | grep -E '^11[5-9]|^12'`
Expected : confirmer si `118_*` existe. Si pris, viser le prochain libre et l'annoncer dans l'EDR.

- [ ] **Step 2: Lancer le sweep complet (70 runs) — détection par EXIT CODE, JSON dumpé**

Run (en arrière-plan, budget ~30-60 min ; chemin JSON dédié, PAS sous results/ d'autres sessions) :
```bash
AGISEED_QUIET_LOG=1 SABC_HIDDENS=5,20,50,100 SABC_INITS=prod,normalized \
  SABC_SEEDS=0,1,2,3,4 SABC_TRIALS=250 SABC_AGENTS=8 \
  SABC_OUT="results/sab_compositional_sweep.json" \
  python tools/substrate_ab_compositional.py > /tmp/sab_sweep.log 2>&1; echo "EXIT=$?"
```
Expected : `EXIT=0` (succès jugé par le CODE, jamais par grep sur le log). Le JSON contient `cells` + `curve`.
Garde-fou : si `EXIT≠0`, lire `/tmp/sab_sweep.log` pour la cause (ex. torch absent, OOM) — NE PAS conclure depuis un log tronqué.

- [ ] **Step 3: Ancrage de cohérence — hidden=5 doit reproduire EDR 117**

Inspecter la cellule `hidden=5, init=prod` du JSON : `legacy` Δ médian ≈ −0.007 et `torch` Δ médian ≈ +0.010, `torch` hit_end ≤ ~0.16 (tolérance : même ORDRE de grandeur, plancher proche de 0 ; le RNG diffère de trials=150→250 donc pas d'égalité stricte). Si l'ancrage diverge nettement (ex. torch hit_end > 0.4 à hidden=5), SUSPENDRE le verdict : le banc a dérivé, investiguer avant de conclure.

- [ ] **Step 4: Lire la courbe et trancher A/B/C (jamais le scalaire nu)**

Extraire `curve["legacy"]` et `curve["torch"]` (hit_end médian par hidden, par init). Lecture :
- **A — taille lève LES DEUX** : hit_end monte avec hidden pour legacy ET torch (vers >0.3) → capacité/représentation = verrou ; règle secondaire.
- **B — taille lève TORCH seul** : torch monte, legacy reste au plancher (0–0.15) → verrou conjoint gradient×taille → torch-prod gros justifié.
- **C — taille ne lève NI l'un NI l'autre** : plancher jusqu'à hidden=100 sous les DEUX inits → pas la taille ; verrou plus profond → re-spec (curriculum/k-étapes).
Contrôle d'init : si `prod` montre un null mais `normalized` lève à grande taille → c'était l'échelle d'activation (le noter) ; si les deux inits montrent le même plancher → null réel.

- [ ] **Step 5: Écrire EDR 118**

Créer `docs/EDR/118_<titre>.md` selon le moule d'EDR 117 (frontmatter `id/type/title/status/gate/verdict`, sections Contexte / Méthode / Contrôle de cohérence / Résultats (table-courbe complète hidden×init×backend : hit_end + delta médians + per-seed) / Verdict A/B/C / Caveats / Conséquences / Liens). Caveats obligatoires : n=5 seeds (sign_p par cellule plafonné), confond d'init contrôlé par le bras normalisé, micro-tâche proxy (pas une preuve apex), trials=250 (anti-sous-entraînement). Liens : `[[sota-gap-substrate]]`, `[[coop-competence-is-population-property]]`, EDR 117, EDR 115.

- [ ] **Step 6: Commit (path-scoped)**

```bash
git add docs/EDR/118_<titre>.md
git commit -m "docs(EDR118): sweep taille cachee compositionnel — verdict <A|B|C>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notes d'exécution

- **Pas de PR-off-main** : le banc importe `backend.py`/`substrate_ab.py` absents de `origin/main` → le chantier vit sur `feat/d1-prod-pairing` (mêmes contraintes qu'EDR 117).
- Le dump JSON (`SABC_OUT`) protège contre la perte de données log-only (piège EDR 108/113).
- Si torch est absent de l'environnement, Task 2 ne peut pas produire le bras torch : le signaler et différer le RUN, mais Task 1 (BUILD + tests purs) reste livrable (les `slow` skippent proprement).
