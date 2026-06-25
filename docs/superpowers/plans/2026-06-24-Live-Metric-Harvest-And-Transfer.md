# Câblage récolte métrique vivante + re-mesure transfert — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Alimenter `mammoth_kills`/`spears_crafted` dans la récolte d'`agent_stats` (sans quoi la `stoneage_competence` réparée est inerte) + exposer la décomposition apex/lance, puis re-mesurer le transfert (B champion-vs-frais, A curriculum) sur la dimension vivante.

**Architecture:** Tâche 1 = câblage (2 sites de récolte + décompo de sortie de la sonde B) + smoke. Tâches 2-3 = runs (pas de code) + EDR. B avant A.

**Tech Stack:** Python 3.13, pytest. Réutilise `_frac_reaching`/`competence_for` (`src.curriculum.competence`), `make_run_era_fn`, `target_competence_probe`, `curriculum_transfer`.

## Global Constraints

- **Câblage = condition de validité** : sans `mammoth_kills`/`spears_crafted` dans `agent_stats`, `_frac_reaching` lit un champ absent → `frac_apex=frac_tool=0` → FAUX plancher. La métrique réparée (PR #50) est INERTE sans ça (curriculum réel inclus).
- **Additif et sûr** : `a.get("mammoth_kills", 0)` / `a.get("spears_crafted", 0)` — champs présents sur stoneage (`world_1_stoneage.py:337,339` init ; `:717-723,1210` incrément), 0 ailleurs ; les métriques non-réparées ne les lisent pas.
- **Décomposition rapportée, jamais le scalaire nu** (anti-théâtre). Apex/lance sont des conduites de minorité → rapporter FRACTION + TOTAL, pas la médiane (EDR 094).
- **Sweet spot** explicite (`CT_METAB=0.25 CT_PAYOFF=3.0`) sinon plancher létal (EDR 085).
- **Tree partagé** : commits **pathspec-limités** `git commit <paths> -m`. Branche `feat/d1-prod-pairing`.
- **Fichiers** : `main_curriculum.py`, `tools/target_competence_probe.py` (modif) ; `tests/sandbox/test_live_harvest.py` (nouveau).

---

## File Structure

- **Modify** `main_curriculum.py:108-114` — +2 clés dans `agent_stats` de `make_run_era_fn` (curriculum réel + expérience A).
- **Modify** `tools/target_competence_probe.py` — +2 clés dans `stats` (`:92-94`) + décompo apex/lance dans la row `per_era` (`:97-105`) + import `_frac_reaching` (`:27`).
- **Create** `tests/sandbox/test_live_harvest.py` — smoke `slow` (la sonde sort la décompo vivante).

---

### Task 1: Câbler la récolte des signaux vivants (+ décompo de sortie)

**Files:**
- Modify: `main_curriculum.py` (~lignes 108-114)
- Modify: `tools/target_competence_probe.py` (~lignes 27, 92-105)
- Test: `tests/sandbox/test_live_harvest.py`

**Interfaces:**
- Consumes: `_frac_reaching` (`src.curriculum.competence`), `run_probe` (`tools.target_competence_probe`), `make_run_era_fn`/`_acquire_shared_db` (`main_curriculum`).
- Produces: `agent_stats` (les deux sites) inclut `mammoth_kills`/`spears_crafted` ; les rows `per_era` de `run_probe` incluent `frac_apex`, `frac_tool`, `total_mammoth`, `total_spears`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/sandbox/test_live_harvest.py
import pytest


@pytest.mark.slow
def test_probe_outputs_live_decomposition(monkeypatch):
    """Après câblage : run_probe sur stoneage expose la décompo apex/lance dans per_era
    (preuve que mammoth_kills/spears_crafted sont récoltés ET rapportés)."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    monkeypatch.setenv("CT_METAB", "0.25")
    monkeypatch.setenv("CT_PAYOFF", "3.0")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.target_competence_probe import run_probe
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_probe("stoneage", k=1, num_agents=30, max_ticks=120, shared_db=db, mode="tabula")
    finally:
        async_logger.stop()
    assert res["per_era"], "aucune ère"
    row = res["per_era"][0]
    assert "frac_apex" in row and "frac_tool" in row
    assert "total_mammoth" in row and "total_spears" in row
    assert 0.0 <= res["median_competence"] <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/sandbox/test_live_harvest.py -q -p no:cacheprovider`
Expected: FAIL (`KeyError`/assert : `frac_apex` absent de la row `per_era` — pas encore câblé).

- [ ] **Step 3: Câbler `main_curriculum.py` (remplacer le dict `agent_stats`, ~lignes 108-114)**

Remplacer EXACTEMENT :

```python
        agent_stats = [{
            "age": a.get("age", 0),
            "energy": a.get("energy", 0.0),
            "preys_eaten": a.get("preys_eaten", 0),
            "altars_solved": a.get("altars_solved", 0),
            "total_dreams": a.get("total_dreams", 0),
        } for a in all_agents]
```

par :

```python
        agent_stats = [{
            "age": a.get("age", 0),
            "energy": a.get("energy", 0.0),
            "preys_eaten": a.get("preys_eaten", 0),
            "altars_solved": a.get("altars_solved", 0),
            "total_dreams": a.get("total_dreams", 0),
            "mammoth_kills": a.get("mammoth_kills", 0),    # signal vivant (stoneage_competence réparée, EDR 096)
            "spears_crafted": a.get("spears_crafted", 0),
        } for a in all_agents]
```

- [ ] **Step 4: Câbler `tools/target_competence_probe.py` — import (ligne 27)**

Remplacer :

```python
from src.curriculum.competence import competence_for
```

par :

```python
from src.curriculum.competence import competence_for, _frac_reaching
```

- [ ] **Step 5: Câbler `tools/target_competence_probe.py` — le dict `stats` (~lignes 92-94)**

Remplacer EXACTEMENT :

```python
        stats = [{"age": a.get("age", 0), "energy": a.get("energy", 0.0),
                  "preys_eaten": a.get("preys_eaten", 0), "altars_solved": a.get("altars_solved", 0),
                  "total_dreams": a.get("total_dreams", 0)} for a in all_agents]
```

par :

```python
        stats = [{"age": a.get("age", 0), "energy": a.get("energy", 0.0),
                  "preys_eaten": a.get("preys_eaten", 0), "altars_solved": a.get("altars_solved", 0),
                  "total_dreams": a.get("total_dreams", 0),
                  "mammoth_kills": a.get("mammoth_kills", 0),
                  "spears_crafted": a.get("spears_crafted", 0)} for a in all_agents]
```

- [ ] **Step 6: Câbler `tools/target_competence_probe.py` — la décompo dans la row `per_era` (~lignes 97-105)**

Remplacer EXACTEMENT :

```python
        row = {
            "era": i, "competence": round(competence, 4), "n": len(all_agents), "ticks": t,
            "med_age": _median([s["age"] for s in stats]),
            "med_altars": _median([s["altars_solved"] for s in stats]),
            "med_preys": _median([s["preys_eaten"] for s in stats]),
            "med_dreams": _median([s["total_dreams"] for s in stats]),
            "max_altars": max((s["altars_solved"] for s in stats), default=0),
            "max_age": max((s["age"] for s in stats), default=0),
        }
```

par :

```python
        row = {
            "era": i, "competence": round(competence, 4), "n": len(all_agents), "ticks": t,
            "med_age": _median([s["age"] for s in stats]),
            "med_altars": _median([s["altars_solved"] for s in stats]),
            "med_preys": _median([s["preys_eaten"] for s in stats]),
            "med_dreams": _median([s["total_dreams"] for s in stats]),
            "max_altars": max((s["altars_solved"] for s in stats), default=0),
            "max_age": max((s["age"] for s in stats), default=0),
            # Décompo des signaux VIVANTS (EDR 096) — fraction de participation (≠ médiane qui lave) + total.
            "frac_apex": round(_frac_reaching(stats, "mammoth_kills"), 4),
            "frac_tool": round(_frac_reaching(stats, "spears_crafted"), 4),
            "total_mammoth": sum(s["mammoth_kills"] for s in stats),
            "total_spears": sum(s["spears_crafted"] for s in stats),
        }
```

- [ ] **Step 7: Run the smoke test**

Run: `python -m pytest tests/sandbox/test_live_harvest.py -q -p no:cacheprovider`
Expected: PASS (~10-40 s).

- [ ] **Step 8: Non-régression**

Run: `python -m pytest tests/sandbox/test_competence_repair.py tests/sandbox/test_curriculum_transfer.py -q -p no:cacheprovider`
Expected: PASS (signatures inchangées ; `agent_stats`/`stats` gagnent 2 clés, lues seulement par la métrique réparée + la décompo).

- [ ] **Step 9: Commit**

```bash
git commit main_curriculum.py tools/target_competence_probe.py tests/sandbox/test_live_harvest.py -m "feat(competence): cabler mammoth_kills/spears_crafted dans la recolte + decompo apex/lance (active la metrique vivante, EDR 096)"
```

---

### Task 2: Run B — champion-vs-frais (pas de code)

**Files:** aucun (exécution + EDR).

- [ ] **Step 1: Lancer le bras tabula (soupe fraîche) sur stoneage, sweet spot**

Run: `AGISEED_QUIET_LOG=1 CT_TARGET=stoneage CT_MODE=tabula CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py`
Expected: une ligne `VERDICT=... median_C=...` + un JSON `results/target_competence_probe_0.json`. Noter `median_competence` + `frac_apex`/`frac_tool` par ère.

- [ ] **Step 2: Lancer le bras champion (clones HoF) — même config**

Run: `AGISEED_QUIET_LOG=1 CT_TARGET=stoneage CT_MODE=champion CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py`
Expected: idem (écrase le JSON — copier/relire les deux sorties depuis les logs). Si le HoF est vide → `RuntimeError` : le signaler (mode champion impossible).

- [ ] **Step 3: Comparer et conclure**

- Le champion PORTE la compétence vivante si `median_competence(champion) > median_competence(tabula)` ET la décompo (`frac_apex`/`frac_tool` par ère) est supérieure chez le champion.
- `champion ≈ tabula` (ou apex identique) → la compétence vivante n'est PAS portée par les champions (re-questionner HoF/sélection).
- Rapporter la **décomposition complète** (`frac_apex`/`frac_tool`/`total_*` par ère, les deux bras), JAMAIS le scalaire nu. Signaler la rareté (fractions, n).

- [ ] **Step 4: Écrire l'EDR du résultat B** (numéro libre suivant, ex. 097) et committer (pathspec-limité).

---

### Task 3: Run A — transfert curriculum (pas de code)

**Files:** aucun (exécution + EDR).

- [ ] **Step 1: Vérifier que la pré-étape du ladder est runnable**

La compétence du transfert est mesurée sur le DERNIER monde du ladder (`target = ladder[-1]`). Pour mesurer la métrique réparée, le ladder DOIT se terminer par `stoneage`. Vérifier qu'une pré-étape (`soup`) est runnable :

Run: `AGISEED_QUIET_LOG=1 CT_TARGET=soup CT_MODE=tabula CT_K=1 CT_NUM_AGENTS=20 CT_MAX_TICKS=40 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/target_competence_probe.py`
Expected: s'exécute sans erreur (soup est un monde valide). Si erreur → utiliser un ladder à une seule pré-étape valide ou documenter l'impossibilité dans l'EDR.

- [ ] **Step 2: Lancer le transfert sur la métrique vivante (ladder se terminant par stoneage)**

Run: `AGISEED_QUIET_LOG=1 CT_METRIC=world CT_TARGET=stoneage CT_LADDER=soup,stoneage CT_SEEDS=0,1,2,3,4 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 python -u tools/curriculum_transfer.py`
Expected: `VERDICT=TRANSFERE|NEUTRE|NUIT median_ratio=... (n_fav=…/…, sign_p=…)` + JSON `results/curriculum_transfer_0.json`.

- [ ] **Step 3: Interpréter et conclure**

- `TRANSFERE` (median_ratio>1.05, sign_p bas) → l'échafaudage développemental construit la compétence vivante stoneage → déblocage majeur (contredit le NEUTRE d'EDR 091 qui mesurait le plancher mort).
- `NEUTRE` → le curriculum ne construit pas plus de compétence vivante que tabula à budget égal.
- `NUIT` → l'échafaudage dégrade.
- Rapporter le **ratio par seed** (`per_seed`), `sign_p`, n. Jamais le label nu.

- [ ] **Step 4: Écrire l'EDR du résultat A** (numéro suivant) et committer (pathspec-limité).

---

## Self-Review

**Spec coverage :** câblage des 2 sites (`make_run_era_fn` + `run_probe`) → Task 1 Steps 3-5 ; décompo
apex/lance en sortie (condition de la décomposition rapportée de B) → Task 1 Step 6 ; smoke régression →
Task 1 Step 1/7 ; non-régression → Step 8 ; Run B + EDR → Task 2 ; Run A + EDR → Task 3 ; vérif
pré-étape ladder → Task 3 Step 1. ✓

**Placeholder scan :** aucun TODO/TBD ; tous les blocs à remplacer cités verbatim avec leur remplacement
complet ; commandes exactes avec sortie attendue. ✓

**Type consistency :** `_frac_reaching(List[Dict], str) -> float` (existant) consommé dans `run_probe`
avec `stats` qui contient désormais `mammoth_kills`/`spears_crafted` (Step 5 avant Step 6) ✓.
`agent_stats` enrichi (Step 3) → lu par `stoneage_competence` réparée (existante) ✓. Les rows `per_era`
gagnent `frac_apex`/`frac_tool`/`total_mammoth`/`total_spears`, lus par le smoke (Task 1 Step 1) ✓.
Ordre des steps correct : `stats` enrichi (Step 5) AVANT son usage dans la décompo (Step 6). ✓
