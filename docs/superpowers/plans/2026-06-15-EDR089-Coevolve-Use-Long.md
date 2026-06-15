# EDR 089 — Coevolve Use on Long-Survival Substrate : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `tools/coevolve_use_long.py` qui power EDR 083 (co-évolution de l'usage FIABLE vs BRUITÉ) sur le **substrat à survie longue** (sweet-spot 085), avec R répétitions appariées et stats rigoureuses (`exp_stats`), selon le pré-enregistrement EDR 089.

**Architecture:** RÉUTILISE le moteur d'083 (`coevolve` + `_run_era_lewis` ; `_setup` met déjà `night_enabled=False`) en lui passant un **cfg sweet-spot**. N'ajoute qu'un `_measure_full` (composantes kills/net/survie), la **boucle R appariée** (FIABLE & BRUITÉ au même seed/répétition), le gate survie, et le verdict pré-enregistré via `Harness` + `exp_stats`. **N'altère pas `coevolve_language.py`** (artefact 083).

**Tech Stack:** Python 3.13, numpy, `src/seed_ai/harness.py` (D1), `src/seed_ai/exp_stats.py` (EDR 088), biosphère Lewis (`lang_on_competent._run_era_lewis`, `lexicon._setup`). Pas de scipy.

**Spec / pré-enregistrement:** `docs/superpowers/specs/2026-06-15-EDR089-Coevolve-Use-Long-design.md`

---

## File Structure

- **Create** `tools/coevolve_use_long.py` — `_sweet_cfg`, `_NullProg`, `_measure_full`, `main` (boucle R + stats + verdict).
- **Create** `tests/sandbox/test_coevolve_use_long.py` — repro de `_measure_full` + smoke du sweep.
- **Append (addendum)** au spec : R final post-pilote.
- **Create** `docs/EDR/089_*.md` — après le run.

Réutilisé (NON modifié) : `coevolve`, (de `tools/coevolve_language.py`), `_run_era_lewis` (`tools/lang_on_competent.py`), `new_head`/`train_population`, `_load_champions`, `_reproduce`. Worktree isolé `worktree-edr089-coevolve-use-long` (base main). Commits **path-scoped**.

---

### Task 1 : `_sweet_cfg` + `_measure_full` (mesure à composantes)

**Files:**
- Create: `tools/coevolve_use_long.py`
- Test: `tests/sandbox/test_coevolve_use_long.py`

**Contexte** : `_measure` d'083 ne renvoie que `mammoth`. On veut **kills + net (kills−leurre) + survie (ticks)** pour le primaire + diagnostics + gate. `_run_era_lewis(..., measure=True)` renvoie déjà `{ticks, mammoth, leurre, survivors}`.

- [ ] **Step 1 : test qui échoue**

```python
# tests/sandbox/test_coevolve_use_long.py
import numpy as np
from tools import coevolve_use_long as cul
from tools.robust_eval import _load_champions
from src.seed_ai.mutation import MutationConfig


def test_sweet_cfg_is_long_substrate():
    cfg = cul._sweet_cfg()
    assert cfg.base_metabolism == 0.25 and cfg.forage_payoff == 3.0


def test_measure_full_components_reproducible():
    cfg = cul._sweet_cfg()
    mc = MutationConfig(weight_init_std=2.0)
    champs = _load_champions()
    a = cul._measure_full(cfg, champs, mc, use_head=False, heads=None, num_agents=4, n=2, base=5)
    b = cul._measure_full(cfg, champs, mc, use_head=False, heads=None, num_agents=4, n=2, base=5)
    assert set(a) == {"kills", "nets", "survs"}
    assert len(a["kills"]) == 2 and len(a["nets"]) == 2 and len(a["survs"]) == 2
    assert a == b                                  # seedé -> reproductible (apparié)
    assert all(a["nets"][i] == a["kills"][i] - (a["kills"][i] - a["nets"][i]) for i in range(2))  # net = kills - leurre
```

- [ ] **Step 2 : échec**

Run: `python -m pytest tests/sandbox/test_coevolve_use_long.py -k "sweet or measure" -v`
Expected: `ModuleNotFoundError: No module named 'tools.coevolve_use_long'`

- [ ] **Step 3 : implémentation**

```python
# tools/coevolve_use_long.py
"""tools/coevolve_use_long.py — EDR 089 : l'usage co-évolué du langage paye-t-il sur substrat à survie
LONGUE ? Power EDR 083 sur son levier #1 (la survie). Réutilise le moteur d'083 (coevolve + _run_era_lewis ;
_setup met déjà night OFF) avec un cfg SWEET-SPOT (085) ; ajoute mesure à composantes + boucle R appariée
+ stats rigoureuses. N'altère pas coevolve_language.py.
Pré-enregistrement : docs/superpowers/specs/2026-06-15-EDR089-Coevolve-Use-Long-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lang_on_competent import _run_era_lewis
from tools.coevolve_language import coevolve

METAB, PAYOFF = 0.25, 3.0          # sweet spot survie longue (EDR 085)


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


class _NullProg:
    """Progress no-op : la boucle R a sa propre barre ; coevolve ne doit pas en empiler."""
    def update(self, n=1):
        pass


def _measure_full(cfg, champions, mc, use_head, heads, num_agents, n, base):
    """Mesure sur n ères propres (seedées, plage 1000+ disjointe de coevolve) : kills (primaire),
    net (kills − leurre_hits), survie (ticks). decode_act=False (l'usage émerge, n'est pas imposé)."""
    out = {"kills": [], "nets": [], "survs": []}
    for i in range(n):
        seed_at(base, 1000 + i)
        genomes = _reproduce(champions, num_agents, mc)
        hd = heads[:len(genomes)] if heads else None
        r = _run_era_lewis(cfg, genomes, use_head=use_head, decode_act=False, heads=hd, measure=True)
        k = int(r["mammoth"]); le = int(r["leurre"])
        out["kills"].append(k)
        out["nets"].append(k - le)
        out["survs"].append(int(r["ticks"]))
    return out
```

- [ ] **Step 4 : passage**

Run: `python -m pytest tests/sandbox/test_coevolve_use_long.py -k "sweet or measure" -v`
Expected: 2 PASS. Si `_run_era_lewis` ne renvoie pas `leurre`/`ticks` (vérifier sa signature `measure=True`), adapter `_measure_full` — NE PAS truquer l'assert de repro.

- [ ] **Step 5 : commit**

```bash
git add tools/coevolve_use_long.py tests/sandbox/test_coevolve_use_long.py
git commit -m "feat(coevolve_use_long): _sweet_cfg + _measure_full (composantes kills/net/survie, EDR089)" -- tools/coevolve_use_long.py tests/sandbox/test_coevolve_use_long.py
```

---

### Task 2 : boucle R appariée `main` + gate + verdict pré-enregistré

**Files:**
- Modify: `tools/coevolve_use_long.py`
- Test: `tests/sandbox/test_coevolve_use_long.py`

- [ ] **Step 1 : test qui échoue (APPEND)** — smoke de repro de `main`

```python
def test_main_runs_and_is_reproducible(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    a = cul.main(R=2, gens=2, num_agents=6, K=1, n_eval=2, seed=3, _return=True)
    b = cul.main(R=2, gens=2, num_agents=6, K=1, n_eval=2, seed=3, _return=True)
    assert a["d_kills"] == b["d_kills"]            # apparié/seedé -> identique
    assert len(a["d_kills"]) == 2 and "verdict" in a and "surv_med" in a
```

- [ ] **Step 2 : échec**

Run: `python -m pytest tests/sandbox/test_coevolve_use_long.py -k main -v`
Expected: `TypeError` / `AttributeError` (main absent ou sans `_return`)

- [ ] **Step 3 : implémentation (APPEND à `tools/coevolve_use_long.py`)**

```python
def main(R=8, gens=20, num_agents=24, K=4, n_eval=8, seed=None, _return=False):
    with Harness(seed=seed, name="coevolve_use_long", with_db=False) as h:
        base = h.seed
        cfg = _sweet_cfg()
        mc = MutationConfig(weight_init_std=2.0)
        print(f"EDR089 : usage co-evolue sur substrat LONG (sweet-spot). R={R}, gens={gens}, seed={base}.")
        d_kills, fia_k, bru_k, d_nets, survs = [], [], [], [], []
        prog = h.progress(R, label="repetitions FIABLE vs BRUITE")
        for r in range(R):
            rb = base + r * 100000          # base disjointe par répétition (>> gens + 1000+n_eval)
            rng = np.random.RandomState(rb)
            heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(num_agents)]
            train_population(heads, steps=5000, seed=rb)        # locuteurs fiables (par répétition)
            cf = coevolve(cfg, mc, True, heads, gens, num_agents, K, _NullProg(), base=rb)
            cb = coevolve(cfg, mc, False, None, gens, num_agents, K, _NullProg(), base=rb)
            mf = _measure_full(cfg, cf, mc, True, heads, num_agents, n_eval, base=rb)
            mb = _measure_full(cfg, cb, mc, False, None, num_agents, n_eval, base=rb)
            d_kills.append(float(np.mean(mf["kills"]) - np.mean(mb["kills"])))
            d_nets.append(float(np.mean(mf["nets"]) - np.mean(mb["nets"])))
            fia_k.append(float(np.mean(mf["kills"]))); bru_k.append(float(np.mean(mb["kills"])))
            survs.extend(mf["survs"] + mb["survs"])
            prog.update()

        summ = st.paired_summary(d_kills)
        lo, hi = st.bootstrap_ci(d_kills, np.mean, seed=base)
        surv_med = float(np.median(survs))
        print(f"\n=== Mammouths : FIABLE {np.mean(fia_k):.2f} vs BRUITE {np.mean(bru_k):.2f} ({R} reps appariees) ===")
        print(f"  d (FIABLE-BRUITE kills) = {summ['mean']:+.2f} +/- {summ['se']:.2f} SE ; win {summ['win_rate']*100:.0f}% ; "
              f"Wilcoxon p={summ['wilcoxon_p']:.3f} ; IC95=[{lo:+.2f},{hi:+.2f}]")
        print(f"  net (diagnostic) d = {np.mean(d_nets):+.2f} ; survie mediane = {surv_med:.0f} ticks (gate >120)")
        print("=== VERDICT (pre-enregistre) ===")
        if surv_med <= 120:
            verdict = "VOID"
            print(f"  -> VOID : substrat pas assez long (survie {surv_med:.0f} <= 120). Re-regler l'energie.")
        elif summ["wilcoxon_p"] < 0.05 and summ["mean"] > 0 and lo > 0:
            verdict = "USAGE SELECTIONNE"
            print(f"  -> USAGE SELECTIONNE : ecouter un signal FIABLE est selectionne a survie longue "
                  f"(+{summ['mean']:.1f} kills, p={summ['wilcoxon_p']:.3f}, IC_inf={lo:+.2f}). Langage fonctionnel EMERGE.")
        elif summ["mean"] > 0:
            verdict = "TENDANCE SOUS-SEUIL"
            print(f"  -> TENDANCE sous 2 SE (+{summ['mean']:.1f}, comme 083) : la survie longue ne suffit pas a "
                  f"rendre l'effet ROBUSTE. Goulot = selection EXPLICITE de l'usage (levier #2).")
        else:
            verdict = "NEGATIF ROBUSTE"
            print(f"  -> NEGATIF : meme a survie longue, le signal fiable n'est pas exploite ({summ['mean']:+.1f}).")

        h.save({"R": R, "gens": gens, "d_kills": d_kills, "d_nets": d_nets, "fia_k": fia_k, "bru_k": bru_k,
                "summary": summ, "ci": [lo, hi], "surv_med": surv_med, "verdict": verdict})
        if _return:
            return {"d_kills": d_kills, "summary": summ, "ci": [lo, hi], "surv_med": surv_med, "verdict": verdict}


if __name__ == "__main__":
    main()
```

- [ ] **Step 4 : passage du smoke**

Run: `python -m pytest tests/sandbox/test_coevolve_use_long.py -k main -v`
Expected: PASS. (Le smoke entraîne 2×2 têtes + 2×2 co-évolutions courtes → quelques dizaines de secondes ; si >3 min, réduire et noter.)

- [ ] **Step 5 : suite complète + commit**

Run: `python -m pytest tests/sandbox/test_coevolve_use_long.py -v`
Expected: 3 PASS.
```bash
git add tools/coevolve_use_long.py tests/sandbox/test_coevolve_use_long.py
git commit -m "feat(coevolve_use_long): boucle R appariee + gate survie + verdict pre-enregistre (Wilcoxon/bootstrap, EDR089)" -- tools/coevolve_use_long.py tests/sandbox/test_coevolve_use_long.py
```

---

### Task 3 : PILOTE R=3 → temps/répétition + variance → R figé (addendum)

**But** : mesurer `std(d_kills)` + le **temps/répétition** (le compute le plus lourd) → figer R (puissance) + décider faisabilité. Exécution + analyse.

- [ ] **Step 1 : pilote R=3** (chronométré)

```bash
HEADLESS=1 python -c "import time; t=time.time(); from tools.coevolve_use_long import main; main(R=3, seed=89); print('WALL_MIN', round((time.time()-t)/60,1))"
```
Noter `WALL_MIN`. Si une répétition dépasse ~10 min (≈ >30 min total), réduire `gens`/`n_eval` et **documenter** (le compute prime sur l'idéal).

- [ ] **Step 2 : variance + gate**

Lire `results/coevolve_use_long_89.json` → `summary` (mean/se de d_kills) + `surv_med` (gate). Calculer K requis :
`R = max(8, ((1.96+0.84)*sd/effet)^2)` où `sd = se*sqrt(3)`, effet = cible (≥ l'effet observé OU Cohen d=0.8).
```python
import json, numpy as np
d=json.load(open("results/coevolve_use_long_89.json"))["data"]
sd=d["summary"]["se"]*np.sqrt(d["R"]); print("sd≈",round(sd,2),"mean=",d["summary"]["mean"],"surv_med=",d["surv_med"])
```

- [ ] **Step 3 : addendum daté** dans le spec (en bas)

```markdown
## Addendum post-pilote (2026-06-15) — R figé
Pilote R=3 (seed 89) : temps/rép ≈ <WALL_MIN/3> min ; std(d_kills) ≈ <sd> ; survie médiane = <surv_med> ticks (gate <OK/VOID>).
**R final figé = max(<R_calc>, 8) = <R_final>.** Grille : `main(R=<R_final>, seed=2026)`.
```

- [ ] **Step 4 : commit (path-scoped)**

```bash
git add docs/superpowers/specs/2026-06-15-EDR089-Coevolve-Use-Long-design.md
git commit -m "docs(EDR089): addendum post-pilote -- R fige + temps/rep + gate survie" -- docs/superpowers/specs/2026-06-15-EDR089-Coevolve-Use-Long-design.md
```

---

### Task 4 : GRILLE (R figé) → résultats + EDR 089

**But** : run final au R figé → verdict pré-enregistré → EDR 089. Exécution + rédaction.

- [ ] **Step 1 : run final**

```bash
HEADLESS=1 python -c "from tools.coevolve_use_long import main; main(R=<R_final>, seed=2026)"
```
(Cap wall-time ; si trop long, multiprocess par processus OU réduire et noter. Vérifier le **gate** survie >120 — sinon VOID.)

- [ ] **Step 2 : repro**

Relancer `seed=2026` → `d_kills` identique (provenance D1). Confirmer.

- [ ] **Step 3 : rédiger `docs/EDR/089_*.md`**

Selon l'issue (§5 du spec) : table FIABLE/BRUITÉ (kills primaire + net + survie), `d` ± SE + Wilcoxon p + IC95, le **verdict** (1 des 3 issues, ou tendance/VOID), comparaison au +0.29 d'083, honnêteté (gate, limites d'appariement), variables d'expérience. Pointer le JSON.

- [ ] **Step 4 : commit (path-scoped)**

```bash
git add "docs/EDR/089_*.md"
git commit -m "EDR 089 : <verdict en une ligne> (usage co-evolue sur substrat long, pre-enregistre)" -- "docs/EDR/089_*.md"
```

---

## Self-Review

- **Spec coverage** : §1 hypothèse → Task 4 verdict ; §2 substrat (sweet-spot, seul changement) → Task 1 `_sweet_cfg` + réutilisation `coevolve`(cfg) ; §3 métrique (kills primaire + net + survie) + appariement (`seed_at` même base/rép) → Tasks 1-2 ; §4 stats (Wilcoxon/bootstrap) + gate survie → Task 2 ; §5 table de décision → Task 2 verdict ; §6 archi (tool neuf, réutilise 083 sans l'altérer) → Tasks 1-2 ; §7 compute/pilote → Task 3 ; §8-9 provenance/EDR → Tasks 3-4.
- **Placeholders** : les `<WALL_MIN>/<sd>/<R_final>/<verdict>` (Tasks 3-4) sont des valeurs de run (par nature inconnues avant exécution). Aucun placeholder de code dans Tasks 1-2.
- **Cohérence des types** : `_sweet_cfg()→cfg` ; `_measure_full(cfg, champions, mc, use_head, heads, num_agents, n, base) → {kills,nets,survs}` (Task 1↔2↔test) ; `coevolve(cfg, mc, use_head, heads, gens, num_agents, K, prog, base)` (signature réelle migrée, vérifiée) ; `main(R, gens, num_agents, K, n_eval, seed, _return)` cohérent test↔runs. `st.paired_summary/bootstrap_ci` (exp_stats EDR088).
- **Risque connu** : la sortie `_run_era_lewis(measure=True)` doit contenir `leurre` et `ticks` (vérifié dans le code source : `out["leurre"]`, `out["ticks"]`, `out["mammoth"]`, `out["survivors"]`). `train_population(steps=5000)` × (R + pilote) est le coût dominant côté têtes ; le coût principal reste les co-évolutions (gens × biosphère). Le smoke (R=2,gens=2) doit rester < ~3 min.
