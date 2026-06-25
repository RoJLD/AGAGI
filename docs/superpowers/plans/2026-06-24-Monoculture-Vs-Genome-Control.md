# Contrôle mono_fresh (disjoindre monoculture vs génome) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un bras `mode="mono_fresh"` (monoculture d'un génome frais) à `run_probe`, puis le mesurer en 3-way contre tabula (diverse) et champion (mono-HoF) pour trancher si le déficit apex d'EDR 097 vient de la monoculture ou du génome champion.

**Architecture:** Tâche 1 = une branche `elif` dans le bloc de peuplement de `run_probe` + smoke. Tâche 2 = run + comparaison 3-way + EDR (pas de code). Tout le reste (métrique vivante réparée, récolte câblée, décompo apex/lance, provenance) est réutilisé inchangé.

**Tech Stack:** Python 3.13, pytest. Réutilise `init_primordial_soup`, `MambaAgent`, la métrique réparée `stoneage_competence`, la décompo `frac_apex`/`frac_tool`.

## Global Constraints

- **Additif** : une seule branche `elif mode == "mono_fresh"`. Aucune autre logique modifiée (récolte, métrique, verdict, décompo).
- **`mono_fresh`** = `init_primordial_soup()` puis cloner `genomes[0]` ×`num_agents` (UN génome frais, comme `champion` clone le HoF). `champ_g` reste `None` en mode mono_fresh (`:65`) — non lu.
- **Apparié** : `SeedManager(i)` identique (CT_K égal) → 3-way comparable aux runs tabula/champion sauvegardés.
- **Décomposition rapportée** (`frac_apex`/`frac_tool` par ère), jamais le scalaire nu.
- **Sweet spot** `CT_METAB=0.25 CT_PAYOFF=3.0` (sinon plancher létal).
- **Tree partagé** : commits **pathspec-limités** `git commit <paths> -m`. Branche `feat/d1-prod-pairing`.
- **Fichiers** : `tools/target_competence_probe.py` (modif) ; `tests/sandbox/test_mono_fresh.py` (nouveau).

---

## File Structure

- **Modify** `tools/target_competence_probe.py` — une branche `elif mode == "mono_fresh"` dans `run_probe` (bloc de peuplement ~lignes 72-83).
- **Create** `tests/sandbox/test_mono_fresh.py` — smoke `slow`.

---

### Task 1: Bras `mode="mono_fresh"`

**Files:**
- Modify: `tools/target_competence_probe.py` (`run_probe`, bloc de peuplement ~lignes 72-83)
- Test: `tests/sandbox/test_mono_fresh.py`

**Interfaces:**
- Consumes: `init_primordial_soup`, `MambaAgent` (déjà importés), `run_probe` (existant).
- Produces: `run_probe(..., mode="mono_fresh")` peuple l'env de `num_agents` clones de `genomes[0]` (un génome frais) ; renvoie le même dict que les autres modes (avec `per_era` décomposé).

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/sandbox/test_mono_fresh.py
import pytest


@pytest.mark.slow
def test_mono_fresh_mode_runs_and_decomposes(monkeypatch):
    """Le bras de contrôle mono_fresh peuple, tourne et sort la décompo apex/lance."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.target_competence_probe import run_probe
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_probe("stoneage", k=1, num_agents=20, max_ticks=80, shared_db=db, mode="mono_fresh")
    finally:
        async_logger.stop()
    assert res["mode"] == "mono_fresh" and res["per_era"]
    row = res["per_era"][0]
    assert "frac_apex" in row and "frac_tool" in row
    assert "total_mammoth" in row and "total_spears" in row
    assert 0.0 <= res["median_competence"] <= 1.0
```

- [ ] **Step 2: Note sur la nature du test (smoke d'intégration, pas un TDD-red)**

Ce smoke est un **garde-fou d'intégration de forme**, pas un test TDD à rouge strict : avant le fix,
`mode="mono_fresh"` tombe dans la branche `else` (tabula) qui produit une sortie de forme VALIDE
(`per_era` décomposé, `mode` stocké tel quel) → le test passerait déjà. Le **comportement** voulu
(monoculture = clones de `genomes[0]`) n'est pas observable depuis le dict de retour (les génomes ne
sont pas exposés) et est validé par le **run réel** (Task 2, contraste 3-way). Ne PAS forcer un faux
« expected FAIL ». Procéder directement au Step 3 (ajouter la branche), puis Step 4 (le smoke doit
PASSER).

- [ ] **Step 3: Add the `elif` branch (bloc de peuplement de `run_probe`)**

Remplacer EXACTEMENT :

```python
        if mode == "champion":
            for _ in range(num_agents):
                a = MambaAgent()
                a.from_genome(champ_g)
                env.add_agent(a, energy=50.0)
        else:
            genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                                 keep_memory=False, shared_db=shared_db, config=config)
            for g in genomes:
                a = MambaAgent()
                a.from_genome(g)
                env.add_agent(a, energy=50.0)
```

par :

```python
        if mode == "champion":
            for _ in range(num_agents):
                a = MambaAgent()
                a.from_genome(champ_g)
                env.add_agent(a, energy=50.0)
        elif mode == "mono_fresh":
            # CONTRÔLE (EDR 097) : monoculture d'UN génome frais -> isole l'effet monoculture du
            # génome champion. init_primordial_soup puis cloner genomes[0] x num_agents.
            genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                                 keep_memory=False, shared_db=shared_db, config=config)
            mono_g = genomes[0]
            for _ in range(num_agents):
                a = MambaAgent()
                a.from_genome(mono_g)
                env.add_agent(a, energy=50.0)
        else:
            genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                                 keep_memory=False, shared_db=shared_db, config=config)
            for g in genomes:
                a = MambaAgent()
                a.from_genome(g)
                env.add_agent(a, energy=50.0)
```

- [ ] **Step 4: Run the smoke test**

Run: `python -m pytest tests/sandbox/test_mono_fresh.py -q -p no:cacheprovider`
Expected: PASS (~10-40 s). La population est désormais une monoculture (clones de `genomes[0]`), et la décompo est exposée.

- [ ] **Step 5: Non-régression**

Run: `python -m pytest tests/sandbox/test_live_harvest.py -q -p no:cacheprovider`
Expected: PASS (mode `tabula` inchangé : la branche `else` est intacte).

- [ ] **Step 6: Commit**

```bash
git commit tools/target_competence_probe.py tests/sandbox/test_mono_fresh.py -m "feat(probe): bras controle mode=mono_fresh (monoculture genome frais, disjoindre EDR 097)"
```

---

### Task 2: Run mono_fresh + comparaison 3-way (pas de code)

**Files:** aucun (exécution + EDR).

- [ ] **Step 1: Lancer le bras mono_fresh (même config que tabula/champion d'EDR 097)**

Run: `AGISEED_QUIET_LOG=1 CT_TARGET=stoneage CT_MODE=mono_fresh CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py`
Expected: `VERDICT=... median_C=...` + JSON `results/target_competence_probe_0.json`. Noter `median_competence` + `frac_apex`/`frac_tool` par ère.

- [ ] **Step 2: Comparaison 3-way et verdict**

Référence EDR 097 (sweet spot, 8 ères, appariés par seed) : tabula `median_C=0.313, apex=0.211` ;
champion `median_C=0.256, apex=0.162`. Comparer mono_fresh à ces deux :

- `mono_fresh ≈ champion < tabula` (apex et median_C tous deux abaissés vers le champion) → **MONOCULTURE** : la diversité porte l'apex coop ; le champion n'est pas spécifiquement mauvais.
- `champion < mono_fresh` (mono_fresh récupère vers tabula) → **GÉNOME** : le champion est apex-pauvre en plus de l'effet monoculture.
- `mono_fresh ≈ tabula` → la monoculture est inoffensive → le déficit du champion EST le génome.

Rapporter la **décomposition complète** (`frac_apex`/`frac_tool` par ère, les 3 bras) + le contraste apparié par ère (mono_fresh vs champion, mono_fresh vs tabula). Jamais le scalaire nu. Signaler n=8.

- [ ] **Step 3: Écrire l'EDR du résultat** (numéro libre suivant, ex. 098) et committer (pathspec-limité).

---

## Self-Review

**Spec coverage :** bras `mono_fresh` (clone `genomes[0]`) → Task 1 Step 3 ; smoke (mode tourne +
décompo) → Task 1 Step 1/4 ; non-régression tabula → Step 5 ; run 3-way + verdict
MONOCULTURE/GÉNOME → Task 2 ; EDR → Task 2 Step 3. Garde-fous : apparié (même CT_K), décompo rapportée,
sweet spot. ✓

**Placeholder scan :** aucun TODO/TBD ; le bloc à remplacer est cité verbatim avec son remplacement
complet ; commande de run exacte. La note du Step 2 (le smoke peut passer avant le fix car `res["mode"]`
est stocké tel quel) est une mise en garde HONNÊTE sur la limite du smoke, pas un placeholder — le run
réel (Task 2) est la vraie validation du comportement monoculture. ✓

**Type consistency :** `run_probe(..., mode="mono_fresh")` renvoie le même dict (clés `mode`,
`median_competence`, `per_era` avec `frac_apex`/`frac_tool`/`total_mammoth`/`total_spears`) que les
modes existants — consommé par le smoke (Task 1) et le run (Task 2). `init_primordial_soup` renvoie
`(genomes, ntm)`, `genomes[0]` est un génome valide pour `MambaAgent.from_genome` (même usage que la
branche `else`). ✓
