# Sweep dose de diversité — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un mode `mixture` à `tools/target_competence_probe.py` qui construit une population de `n_clones` clones d'un génome frais + `(N − n_clones)` génomes diversifiés (fraction pilotée par `CT_CLONE_FRAC`), puis balayer 5 fractions pour tracer la courbe diversité→apex.

**Architecture:** Réutilisation totale de l'outil existant (soupe `init_primordial_soup`, `from_genome`, décompo `frac_apex`/`frac_tool` par ère, knob `preserve_dims`). Une seule branche `elif mode == "mixture":` ajoutée dans `run_probe`, plus un knob d'env `CT_CLONE_FRAC` (défaut `0.0`). Le balayage est piloté par 5 invocations CLI distinctes (pattern EDR 102/103), pas par du code d'orchestration.

**Tech Stack:** Python 3.13, pytest (marqueur `slow`), env vars `CT_*`, `MambaAgent.from_genome`.

## Global Constraints

- **Tree partagé** : commits OBLIGATOIREMENT path-scoped (`git commit <paths> -m`), JAMAIS `git add -A`/`.`/commit nu. Plusieurs sessions Claude partagent le working tree.
- **Quiet-log** : `AGISEED_QUIET_LOG=1` doit être dans le SHELL avant que python démarre (singleton lu à l'import), sinon ~10× plus lent.
- **Sweet spot énergie** (EDR 085) : `CT_METAB=0.25`, `CT_PAYOFF=3.0` (sinon plancher létal).
- **Défaut non-régressif** : `CT_CLONE_FRAC` défaut `"0.0"` ; la nouvelle branche ne touche PAS `tabula`/`champion`/`mono_fresh`.
- **`preserve_dims` reste OFF** (no-op apex confirmé EDR 103) — câblé via la variable `preserve_dims` déjà lue dans `run_probe`.
- **Anti-théâtre** : décompo `frac_apex`/`frac_tool`/`total_mammoth` par ère, apparié par seed, jamais le scalaire nu.

---

### Task 1: Mode `mixture` + knob `CT_CLONE_FRAC`

**Files:**
- Modify: `tools/target_competence_probe.py` (lire `CT_CLONE_FRAC` près de `preserve_dims:65` ; nouvelle branche `elif mode == "mixture":` entre la branche `mono_fresh` `:78-87` et le `else` tabula `:88`)
- Test: `tests/sandbox/test_diversity_dose_probe.py` (créer)

**Interfaces:**
- Consumes : `run_probe(target, k, num_agents, max_ticks, shared_db, mode="tabula")` (signature inchangée) ; `init_primordial_soup(num_agents, import_agent_id, keep_memory, shared_db, config)` → `(genomes, _ntm)` ; `MambaAgent().from_genome(genome, preserve_dims=False)` ; `env.add_agent(agent, energy=50.0)` ; variable locale `preserve_dims` déjà calculée dans `run_probe`.
- Produces : mode `"mixture"` reconnu par `run_probe` ; lit `os.environ["CT_CLONE_FRAC"]` (float, défaut `0.0`) ; construit une population de taille EXACTEMENT `num_agents` (`per_era[i]["n"] == num_agents` quand tous survivent au moins l'init) ; `result["mode"] == "mixture"`.

- [ ] **Step 1: Write the failing smoke test**

Créer `tests/sandbox/test_diversity_dose_probe.py` (calqué sur `test_mono_fresh.py`) :

```python
# tests/sandbox/test_diversity_dose_probe.py
import pytest


@pytest.mark.slow
def test_mixture_mode_runs_population_exact_and_decomposes(monkeypatch):
    """Le mode mixture (f=0.5) peuple EXACTEMENT N agents, tourne, sort la décompo apex/lance."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    monkeypatch.setenv("CT_CLONE_FRAC", "0.5")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.target_competence_probe import run_probe
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_probe("stoneage", k=1, num_agents=20, max_ticks=80, shared_db=db, mode="mixture")
    finally:
        async_logger.stop()
    assert res["mode"] == "mixture" and res["per_era"]
    row = res["per_era"][0]
    # Garde-fou compte : population construite = N exactement (pas de fuite de clones/frais).
    assert row["n"] == 20
    assert "frac_apex" in row and "frac_tool" in row
    assert "total_mammoth" in row and "total_spears" in row
    assert 0.0 <= res["median_competence"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_diversity_dose_probe.py -v -m slow`
Expected : FAIL — `run_probe` avec `mode="mixture"` tombe dans la branche `else` (tabula), `res["mode"]` serait `"mixture"` mais la population n'est pas construite via la logique mixture ; le test échoue sur l'absence de la branche (ou passe par hasard sur `n==20` mais sans la sémantique clone/frais). Le but du fail-first ici : confirmer que la branche `mixture` n'existe pas encore (le `else` traite tout mode inconnu comme tabula).

Note : comme le `else` actuel attrape tout mode non reconnu, le test pourrait NE PAS échouer franchement. Pour un vrai fail-first, vérifier d'abord que la branche n'existe pas via `grep`. Si le test passe déjà (car tabula construit aussi N agents), considérer le fail-first satisfait par l'absence de la branche dédiée et passer au Step 3 — la valeur du test est la non-régression du compte exact une fois la branche écrite.

- [ ] **Step 3: Read the current dispatch block to anchor the edit**

Lire `tools/target_competence_probe.py:63-94` pour confirmer l'emplacement exact (lecture `preserve_dims` ligne 65 ; branche `mono_fresh` lignes 78-87 ; `else` tabula lignes 88-94).

- [ ] **Step 4: Add the `CT_CLONE_FRAC` read**

Dans `run_probe`, juste après la ligne `preserve_dims = os.environ.get("CT_PRESERVE_DIMS", "") == "1"` (`:65`), ajouter :

```python
    clone_frac = float(os.environ.get("CT_CLONE_FRAC", "0.0"))  # dose diversité : 0=diverse, 1=monoculture
```

- [ ] **Step 5: Add the `mixture` branch**

Insérer la branche AVANT le `else:` tabula (entre la fin de la branche `mono_fresh` à `:87` et `else:` à `:88`) :

```python
        elif mode == "mixture":
            # SWEEP dose de diversité : n_clones clones d'UN génome frais + reste diversifié.
            # f=0 -> N frais diversifiés (≈ tabula) ; f=1 -> N clones (≡ mono_fresh).
            genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                                 keep_memory=False, shared_db=shared_db, config=config)
            n_clones = round(clone_frac * num_agents)
            clone_g = genomes[0]
            n_diverse = num_agents - n_clones
            diverse_pool = genomes[1:] if len(genomes) > 1 else genomes
            for _ in range(n_clones):
                a = MambaAgent()
                a.from_genome(clone_g, preserve_dims=preserve_dims)
                env.add_agent(a, energy=50.0)
            for j in range(n_diverse):
                g = diverse_pool[j % len(diverse_pool)]
                a = MambaAgent()
                a.from_genome(g, preserve_dims=preserve_dims)
                env.add_agent(a, energy=50.0)
```

- [ ] **Step 6: Run the smoke test to verify it passes**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_diversity_dose_probe.py -v -m slow`
Expected : PASS — `res["mode"] == "mixture"`, `row["n"] == 20`, décompo présente, `median_competence ∈ [0,1]`.

- [ ] **Step 7: Run non-regression on existing modes**

Run : `AGISEED_QUIET_LOG=1 python -m pytest tests/sandbox/test_mono_fresh.py tests/sandbox/test_live_harvest.py -v -m slow`
Expected : PASS (les 2) — le défaut `CT_CLONE_FRAC="0.0"` et la nouvelle branche n'altèrent ni `mono_fresh` ni la récolte vivante (`tabula`).

- [ ] **Step 8: Commit (path-scoped)**

```bash
git add tools/target_competence_probe.py tests/sandbox/test_diversity_dose_probe.py
git commit -m "feat(probe): mode mixture + knob CT_CLONE_FRAC (sweep dose de diversite)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Run le sweep 5 points + EDR (pas de code applicatif)

**Files:**
- Create: `docs/EDR/NNN_*.md` (numéro libre — éviter 098-101 pris par l'arc Lewis ; viser 104, vérifier qu'il est libre avant d'écrire)

**Interfaces:**
- Consumes : mode `mixture` + `CT_CLONE_FRAC` de la Task 1 ; sortie `run_probe` → JSON via `Harness.save` (écrit toujours seed=0, donc s'écrase entre runs).
- Produces : un EDR documentant la courbe `frac_apex` vs fraction de clones (5 points), avec décompo par ère et cohérence des bouts.

- [ ] **Step 1: Run f=0.0 (tabula-équivalent)**

```bash
AGISEED_QUIET_LOG=1 CT_MODE=mixture CT_CLONE_FRAC=0.0 CT_TARGET=stoneage \
  CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 \
  python -u tools/target_competence_probe.py
```
Sauver le JSON produit dans le scratchpad sous `dose_f00.json` AVANT le run suivant (il s'écrase). Noter `median_competence` et la moyenne de `frac_apex` sur les 8 ères.

- [ ] **Step 2: Run f=0.25**

Idem avec `CT_CLONE_FRAC=0.25`. Sauver `dose_f025.json`.

- [ ] **Step 3: Run f=0.5**

Idem avec `CT_CLONE_FRAC=0.5`. Sauver `dose_f050.json`.

- [ ] **Step 4: Run f=0.75**

Idem avec `CT_CLONE_FRAC=0.75`. Sauver `dose_f075.json`.

- [ ] **Step 5: Run f=1.0 (mono_fresh-équivalent)**

Idem avec `CT_CLONE_FRAC=1.0`. Sauver `dose_f100.json`.

- [ ] **Step 6: Collationner la courbe + contrôles de cohérence**

Pour chaque fraction, calculer la moyenne de `frac_apex` sur les 8 ères et `median_competence`. Tracer (table) `frac_apex` vs f. Vérifier :
- **Cohérence des bouts** : f=0 doit retomber sur tabula EDR 102 (frac_apex moy ~0.211) ; f=1 sur mono_fresh (~0.158). Écart > bruit inter-ère → signaler (changement de régime ou caveat d'identité f=0 du spec).
- **Forme** : monotone décroissante ? seuil net entre deux points ? plateau-puis-chute ?
- **Décompo par ère** : rapporter la dispersion inter-ère (pas que la moyenne).

- [ ] **Step 7: Vérifier le prochain numéro EDR libre**

Run : `ls docs/EDR/ | sort` — confirmer que 104 (ou le prochain libre hors 098-101) n'est pas pris (sessions Lewis parallèles).

- [ ] **Step 8: Écrire l'EDR**

Créer `docs/EDR/104_Diversity_Dose_Curve_<verdict>.md` (titre selon la forme observée). Contenu : contexte (trilogie close → doser la diversité), table `frac_apex`/`median_C` par fraction, décompo par ère, verdict sur la FORME du collapse, cohérence des bouts, signification (la diversité est-elle un seuil ou un continuum ?), liens `[[coop-competence-is-population-property]]`, statut + suite (option 2 clone-champion si pertinent).

- [ ] **Step 9: Commit (path-scoped)**

```bash
git add docs/EDR/104_Diversity_Dose_Curve_*.md
git commit -m "docs(EDR104): courbe dose de diversite -> apex (forme du collapse)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage :**
- Mode `mixture` + `CT_CLONE_FRAC` (spec Unité 1) → Task 1 Steps 4-5. ✅
- Population = N exactement (spec garde-fou) → Task 1 Step 1 (`row["n"] == 20`). ✅
- Smoke test + non-rég (spec Tests) → Task 1 Steps 1, 6, 7. ✅
- 5 invocations sweet spot K=8/40/300 (spec Unité 2) → Task 2 Steps 1-5. ✅
- Courbe `frac_apex` vs f + cohérence des bouts (spec anti-théâtre) → Task 2 Step 6. ✅
- `preserve_dims` OFF réutilisé (spec) → Task 1 Step 5 (`preserve_dims=preserve_dims`). ✅
- EDR numéro libre hors 098-101 (spec) → Task 2 Steps 7-8. ✅
- Caveat d'identité f=0 (spec) → Task 2 Step 6 (contrôle de cohérence). ✅

**2. Placeholder scan :** Aucun TBD/TODO ; tout le code est complet (branche mixture, test). Le `NNN`/`<verdict>` du nom de fichier EDR est résolu en Task 2 Step 7 (vérif numéro libre) — intentionnel, pas un placeholder de code.

**3. Type consistency :** `clone_frac` (float), `n_clones`/`n_diverse` (int via `round`), `diverse_pool` (list), `from_genome(g, preserve_dims=preserve_dims)` cohérent avec la signature `from_genome(genome, preserve_dims=False)` (mamba_agent.py:136) et les autres branches. `res["mode"]`, `row["n"]`, `row["frac_apex"]` cohérents avec le schéma `per_era` existant (`:110-123`).
