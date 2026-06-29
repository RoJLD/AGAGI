# EDR 110 — Capacite cachee monte-t-elle le plafond de navigation ? Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mesurer si semer de la capacite cachee (N in {5,20,40,80} noeuds, figee) monte le plafond de navigation `p_reach` de Lewis au-dela des ~0.36 d'EDR 107.

**Architecture:** Extension DRY de `tools/lewis_survival_sweep.py` (comme 105/106/107). Une fonction-knob `_fresh_genome(n_hidden)` seme un connectome a capacite cachee fixee ; `_capacity_arm` reutilise la boucle evolve_nav d'EDR 107 avec une mutation a capacite FIGEE (`add_node=0, prune=0`) ; on lit deux signaux gratuits par bras (p_reach gen-0 brut + plateau evolue) et on compare a travers N via `_verdict_capacity`.

**Tech Stack:** Python, numpy, pytest. Reutilise `MambaAgent`, `_reproduce`, `_evolve_nav_gen`, `_p_reach_of_pool`, `_cfg`, `seed_at`, `Harness`, `MutationConfig`.

## Global Constraints

- **1 variable (Commandement 15)** : la SEULE difference entre bras est `n_hidden`. Monde (Lewis vide d'apex, `base_metabolism=0.0`, `forage_payoff=3`), selection (`calculate_life_score`, cliquet best-ever top-5), config de mutation (capacite figee identique), ticks, population, graines (deterministes par bras) — tous identiques.
- **Capacite figee** : `_capacity_mc()` impose `add_node_rate=0.0, prune_rate=0.0`. Un assert par generation verifie `g.num_nodes == 167 + n_hidden` (garde-fou anti-derive).
- **Dimensions exactes** : I=59, O=108 ; `num_nodes = 167 + n_hidden` ; baseline N=5 -> 172 ; N=80 -> 247 (sous le cap soft 256).
- **ASCII-only dans tout `print` execute** (Windows cp1252) : pas de fleche unicode/accents/x-multiplication. `->` ASCII autorise.
- **Non-regression** : toutes les fonctions sont NOUVELLES et additives ; aucun chemin existant (`main_evolve_nav`, etc.) n'est modifie.
- **Determinisme** : `seed_at` pose la graine avant toute consommation RNG (`_fresh_genome`, `_reproduce`, era).
- **Provenance** : `results/` gitignore ; seed du run reel = 110 ; le run reel est lance APRES la revue de code, et AUCUN test n'est relance apres (sinon il ecraserait le JSON de provenance — lecon EDR 107).
- **Verdict pre-enregistre** (fige avant donnees) : CAPACITE LEVE / CAPACITE INERTE / CAPACITE AMBIGUE (seuils en Task 3).

---

### Task 1: `_fresh_genome` + materialisation de la capacite (de-risk go/no-go)

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (ajouter `_fresh_genome` apres `_cfg`, ~ligne 47)
- Test: `tests/sandbox/test_edr110_capacity_nav.py` (creer)

**Interfaces:**
- Consumes: `MambaAgent(num_inputs, num_outputs, num_nodes)` (src/agents/mamba_agent.py) ; `from_genome(genome, preserve_dims=True)`.
- Produces: `_fresh_genome(n_hidden: int) -> Genome` avec `num_nodes == 167 + n_hidden`, `num_inputs == 59`, `num_outputs == 108`.

- [ ] **Step 1: Write the failing tests**

Creer `tests/sandbox/test_edr110_capacity_nav.py` :

```python
import numpy as np
import pytest
from src.seed_ai.harness import seed_at
from src.agents.mamba_agent import MambaAgent
from tools.lewis_survival_sweep import _fresh_genome


def test_fresh_genome_dims():
    seed_at(110, 0)
    g80 = _fresh_genome(80)
    assert g80.num_nodes == 247
    assert g80.num_inputs == 59
    assert g80.num_outputs == 108
    g5 = _fresh_genome(5)
    assert g5.num_nodes == 172


def test_capacity_materializes_in_phenotype():
    # De-risk go/no-go : un genome seme a N=80 materialise 247 noeuds, caches non-inertes,
    # forward sans exception. Si ce test echoue -> STOP (substrat ne supporte pas la capacite).
    seed_at(110, 0)
    g = _fresh_genome(80)
    a = MambaAgent()
    a.from_genome(g)
    assert a.genome.num_nodes == 247
    # bande cachee [59, 139) non tout-zero (caches reellement cables dans W)
    assert np.any(a.genome.W[59:139, :] != 0.0)
    # forward tourne et renvoie 108 logits finis
    obs = np.zeros(59, dtype=np.float32)
    logits = a.forward(obs)
    assert logits.shape[-1] == 108
    assert np.all(np.isfinite(logits))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr110_capacity_nav.py -v`
Expected: FAIL avec `ImportError: cannot import name '_fresh_genome'`.

- [ ] **Step 3: Implement `_fresh_genome`**

Dans `tools/lewis_survival_sweep.py`, ajouter juste apres `_cfg` (apres la ligne 46, `return cfg`) :

```python
def _fresh_genome(n_hidden):
    """EDR110 : genome frais a capacite cachee n_hidden (num_nodes=167+n_hidden, I=59, O=108,
    W dense aleatoire x0.1). Reutilise la construction par defaut de MambaAgent ; seule la bande
    mediane [59, 59+n_hidden) grossit. La graine RNG doit etre posee par l'appelant (seed_at)
    pour le determinisme."""
    return MambaAgent(num_inputs=59, num_outputs=108, num_nodes=167 + n_hidden).genome
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr110_capacity_nav.py -v`
Expected: PASS (2/2). **Si `test_capacity_materializes_in_phenotype` echoue, NE PAS contourner : signaler BLOCKED (go/no-go rouge).**

- [ ] **Step 5: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr110_capacity_nav.py
git commit -m "feat(EDR110): _fresh_genome (capacite cachee semee) + de-risk materialisation"
```

---

### Task 2: `_capacity_mc` + `_capacity_arm` (boucle evolve par palier, capacite figee)

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (ajouter `_capacity_mc` et `_capacity_arm` apres `_fresh_genome`)
- Test: `tests/sandbox/test_edr110_capacity_nav.py` (ajouter)

**Interfaces:**
- Consumes: `MutationConfig(weight_init_std, add_node_rate, prune_rate)` (src/seed_ai/mutation.py, dataclass : `add_node_rate` defaut 0.2, `prune_rate` defaut 0.1) ; `apply_mutations` (src/seed_ai/mutation.py) ; `_fresh_genome` (Task 1) ; `_reproduce(champions, num_agents, mc)` (deja importe) ; `_evolve_nav_gen(cfg, genomes, max_ticks)` -> `(scored, p_reach, stats)` (EDR107, deja present) ; `seed_at`.
- Produces:
  - `_capacity_mc() -> MutationConfig` avec `add_node_rate == 0.0`, `prune_rate == 0.0`.
  - `_capacity_arm(cfg, mc, n_hidden, generations, num_agents, max_ticks, base_seed) -> dict` avec cles `n_hidden, num_nodes, traj (list[float]), gen0 (float), first (float), plateau (float), stats (list[dict])`.

- [ ] **Step 1: Write the failing tests**

Ajouter a `tests/sandbox/test_edr110_capacity_nav.py` :

```python
from src.seed_ai.mutation import apply_mutations
from tools.lewis_survival_sweep import _capacity_mc, _capacity_arm, _cfg


def test_capacity_mc_freezes_capacity():
    mc = _capacity_mc()
    assert mc.add_node_rate == 0.0
    assert mc.prune_rate == 0.0


def test_apply_mutations_preserves_num_nodes_under_frozen_mc():
    seed_at(110, 0)
    g = _fresh_genome(40)  # 207 noeuds
    mc = _capacity_mc()
    for _ in range(10):
        g = apply_mutations(g, mc)
    assert g.num_nodes == 207


def test_capacity_arm_smoke_returns_expected_keys():
    cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
    mc = _capacity_mc()
    arm = _capacity_arm(cfg, mc, n_hidden=5, generations=2, num_agents=6,
                        max_ticks=40, base_seed=12345)
    assert arm["n_hidden"] == 5
    assert arm["num_nodes"] == 172
    assert len(arm["traj"]) == 2
    assert 0.0 <= arm["plateau"] <= 1.0
    assert 0.0 <= arm["gen0"] <= 1.0
    assert len(arm["stats"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr110_capacity_nav.py -k "capacity_mc or preserves_num_nodes or capacity_arm" -v`
Expected: FAIL avec `ImportError: cannot import name '_capacity_mc'`.

- [ ] **Step 3: Implement `_capacity_mc` et `_capacity_arm`**

Dans `tools/lewis_survival_sweep.py`, apres `_fresh_genome` :

```python
def _capacity_mc():
    """EDR110 : MutationConfig a CAPACITE FIGEE (add_node_rate=0, prune_rate=0) pour que n_hidden
    soit la seule variable entre bras. Mutation de poids + add_connection conservees (cabler les
    caches semes sans changer N). weight_init_std=2.0 comme EDR107. NB : le defaut de MutationConfig
    porte add_node_rate=0.2 ET prune_rate=0.1 -> sans ce gel, les bras deriveraient en taille."""
    return MutationConfig(weight_init_std=2.0, add_node_rate=0.0, prune_rate=0.0)


def _capacity_arm(cfg, mc, n_hidden, generations, num_agents, max_ticks, base_seed):
    """EDR110 : un bras = evolue la navigation a capacite cachee FIXEE n_hidden. Calque
    main_evolve_nav (EDR107) mais (a) seme best_ever depuis _fresh_genome(n_hidden) au lieu de
    _load_champions, (b) utilise mc a capacite figee, (c) assert num_nodes==167+n_hidden a chaque
    generation (garde-fou anti-derive). Renvoie un dict {n_hidden, num_nodes, traj, gen0, first,
    plateau, stats}. gen0 = p_reach de la 1re generation (capacite BRUTE) ; plateau = mediane des
    k dernieres (k=5 si gen>=10) ; first = mediane des k premieres."""
    expected_nodes = 167 + n_hidden
    seed_at(base_seed, 0)
    best_ever = [(0.0, _fresh_genome(n_hidden)) for _ in range(5)]
    traj, stats_hist = [], []
    for gen in range(1, generations + 1):
        seed_at(base_seed + gen, 0)
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents, mc)
        assert all(g.num_nodes == expected_nodes for g in genomes), (
            f"capacity drift: n_hidden={n_hidden} attendu {expected_nodes} noeuds")
        scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=max_ticks)
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        traj.append(p_reach)
        stats_hist.append(stats)
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    return {
        "n_hidden": n_hidden, "num_nodes": expected_nodes,
        "traj": traj, "gen0": float(traj[0]) if traj else 0.0,
        "first": float(np.median(traj[:k])), "plateau": float(np.median(traj[-k:])),
        "stats": stats_hist,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/sandbox/test_edr110_capacity_nav.py -k "capacity_mc or preserves_num_nodes or capacity_arm" -v`
Expected: PASS (3/3).

- [ ] **Step 5: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr110_capacity_nav.py
git commit -m "feat(EDR110): _capacity_mc (capacite figee) + _capacity_arm (evolve_nav par palier)"
```

---

### Task 3: `_verdict_capacity` + `_report_capacity_nav` + `main_capacity_nav`

**Files:**
- Modify: `tools/lewis_survival_sweep.py` (ajouter les 3 fonctions apres `_capacity_arm`)
- Test: `tests/sandbox/test_edr110_capacity_nav.py` (ajouter)

**Interfaces:**
- Consumes: `_capacity_arm` (Task 2) ; `_capacity_mc` ; `_cfg` ; `Harness(seed, name, with_db=False)` ; `seed_at` ; `_disable_kuzu()` ; `np.polyfit`, `np.log2`, `np.median`.
- Produces:
  - `_verdict_capacity(arms: list[dict]) -> str` in {"CAPACITE LEVE", "CAPACITE INERTE", "CAPACITE AMBIGUE"}.
  - `_report_capacity_nav(h, arms, generations, num_agents, max_ticks, _return) -> dict|None`.
  - `main_capacity_nav(hidden_levels=(5,20,40,80), generations=20, num_agents=24, max_ticks=80, seed=110, _return=False)`.

- [ ] **Step 1: Write the failing tests**

Ajouter a `tests/sandbox/test_edr110_capacity_nav.py` :

```python
from tools.lewis_survival_sweep import _verdict_capacity, main_capacity_nav


def _arm(n, plateau):
    return {"n_hidden": n, "num_nodes": 167 + n, "plateau": plateau,
            "gen0": plateau, "first": plateau, "traj": [plateau], "stats": []}


def test_verdict_leve_on_rising_plateaus():
    arms = [_arm(5, 0.20), _arm(20, 0.30), _arm(40, 0.42), _arm(80, 0.55)]
    assert _verdict_capacity(arms) == "CAPACITE LEVE"


def test_verdict_inerte_on_flat_plateaus():
    arms = [_arm(5, 0.36), _arm(20, 0.37), _arm(40, 0.35), _arm(80, 0.36)]
    assert _verdict_capacity(arms) == "CAPACITE INERTE"


def test_verdict_ambigue_on_descending_plateaus():
    arms = [_arm(5, 0.55), _arm(20, 0.40), _arm(40, 0.30), _arm(80, 0.20)]
    assert _verdict_capacity(arms) == "CAPACITE AMBIGUE"


def test_main_capacity_nav_smoke_and_determinism():
    # Seed DISTINCT de 110 (le run reel) pour ne pas ecraser la provenance.
    r1 = main_capacity_nav(hidden_levels=(5, 20), generations=2, num_agents=6,
                           max_ticks=40, seed=12345, _return=True)
    assert r1["verdict"] in ("CAPACITE LEVE", "CAPACITE INERTE", "CAPACITE AMBIGUE")
    assert len(r1["arms"]) == 2
    r2 = main_capacity_nav(hidden_levels=(5, 20), generations=2, num_agents=6,
                           max_ticks=40, seed=12345, _return=True)
    assert [a["traj"] for a in r1["arms"]] == [a["traj"] for a in r2["arms"]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/sandbox/test_edr110_capacity_nav.py -k "verdict or main_capacity" -v`
Expected: FAIL avec `ImportError: cannot import name '_verdict_capacity'`.

- [ ] **Step 3: Implement les 3 fonctions**

Dans `tools/lewis_survival_sweep.py`, apres `_capacity_arm` :

```python
def _verdict_capacity(arms):
    """EDR110 : verdict pre-enregistre sur l'effet de la capacite cachee sur le plateau de navigation.
    delta = plateau(N_max) - plateau(N_min) ; slope = pente du plateau vs log2(N) (lisse l'echelle
    geometrique 5->80). CAPACITE LEVE si delta>=0.10 ET slope>0. CAPACITE INERTE si abs(delta)<0.10
    ET abs(slope)<0.05. CAPACITE AMBIGUE sinon (signal partiel/non-monotone)."""
    arms = sorted(arms, key=lambda a: a["n_hidden"])
    plateaus = [a["plateau"] for a in arms]
    delta = plateaus[-1] - plateaus[0]
    x = [float(np.log2(a["n_hidden"])) for a in arms]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms) >= 2 else 0.0
    if delta >= 0.10 and slope > 0:
        return "CAPACITE LEVE"
    if abs(delta) < 0.10 and abs(slope) < 0.05:
        return "CAPACITE INERTE"
    return "CAPACITE AMBIGUE"


def _report_capacity_nav(h, arms, generations, num_agents, max_ticks, _return):
    """Table ASCII (1 ligne/bras : n_hidden, num_nodes, gen0, first, plateau, delta_vs_base) +
    pente plateau vs log2(N) + delta(max-min) + verdict pre-enregistre. Sauvegarde JSON. Tout ASCII."""
    verdict = _verdict_capacity(arms)
    arms_sorted = sorted(arms, key=lambda a: a["n_hidden"])
    base_plateau = arms_sorted[0]["plateau"]
    plateaus = [a["plateau"] for a in arms_sorted]
    x = [float(np.log2(a["n_hidden"])) for a in arms_sorted]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms_sorted) >= 2 else 0.0
    print("\n=== EDR110 capacite cachee -> plafond navigation Lewis ===")
    print("  n_hidden | num_nodes | gen0  first plateau | delta_vs_base")
    for a in arms_sorted:
        print(f"  {a['n_hidden']:8d} | {a['num_nodes']:9d} | {a['gen0']:.3f} {a['first']:.3f} "
              f"{a['plateau']:.3f} | {a['plateau'] - base_plateau:+.3f}")
    print(f"  pente plateau vs log2(N) = {slope:+.4f}  delta(max-min) = "
          f"{plateaus[-1] - plateaus[0]:+.3f} (gate +0.10)")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "n_hidden", "hidden_levels": [a["n_hidden"] for a in arms_sorted],
            "generations": generations, "num_agents": num_agents, "max_ticks": max_ticks,
            "slope_vs_log2N": slope, "delta": plateaus[-1] - plateaus[0], "verdict": verdict,
            "arms": arms_sorted})
    if _return:
        return {"verdict": verdict, "arms": arms_sorted, "slope": slope,
                "delta": plateaus[-1] - plateaus[0]}


def main_capacity_nav(hidden_levels=(5, 20, 40, 80), generations=20, num_agents=24,
                      max_ticks=80, seed=110, _return=False):
    """EDR 110 : seme une echelle de capacite cachee (n_hidden) figee et evolue la navigation a
    chaque palier (boucle evolve_nav EDR107, metab=0, Lewis vide d'apex, forage_payoff=3). Lit
    gen0 (capacite brute) + plateau evolue. Verdict CAPACITE LEVE / INERTE / AMBIGUE."""
    with Harness(seed=seed, name="lewis_capacity_nav", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR110 : capacite cachee nav, hidden={hidden_levels}, gen={generations}, "
              f"pop={num_agents}, max_ticks={max_ticks}, seed={base}.")
        mc = _capacity_mc()
        cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
        prog = h.progress(len(hidden_levels), label="paliers de capacite")
        arms = []
        for n_hidden in hidden_levels:
            arms.append(_capacity_arm(cfg, mc, n_hidden, generations, num_agents,
                                      max_ticks, base + n_hidden))
            prog.update()
        return _report_capacity_nav(h, arms, generations, num_agents, max_ticks, _return)
```

- [ ] **Step 4: Run the full EDR 110 test file**

Run: `python -m pytest tests/sandbox/test_edr110_capacity_nav.py -v`
Expected: PASS (tous : 2 Task1 + 3 Task2 + 4 Task3 = 9). Le smoke `main_capacity_nav` est lent (deux runs 2-gen) mais doit passer en < ~2 min.

- [ ] **Step 5: Commit**

```bash
git add tools/lewis_survival_sweep.py tests/sandbox/test_edr110_capacity_nav.py
git commit -m "feat(EDR110): _verdict_capacity + _report + main_capacity_nav (echelle + verdict)"
```

---

### Task 4: Run reel + doc EDR + memoire (controleur, APRES revue de code)

> **Non-TDD.** Execute par le controleur une fois Tasks 1-3 revues et fusionnees. AUCUN test
> n'est relance apres le run reel (il ecraserait le JSON de provenance — lecon EDR 107).

**Files:**
- Create: `docs/EDR/110_<verdict-slug>.md` (titre = verdict, ASCII)
- Modify (hors worktree, branche memoire) : fichier memoire `lewis-energy-economy-wall.md` + `MEMORY.md`

- [ ] **Step 1: Lancer le run reel (seed 110, 4 bras, 20 gen)**

Run: `python -c "from tools.lewis_survival_sweep import main_capacity_nav; main_capacity_nav()"`
Expected: table 4 lignes (n_hidden 5/20/40/80, num_nodes 172/187/207/247), pente, delta, verdict.
Capturer la sortie stdout integralement (c'est la provenance primaire ; `results/lewis_capacity_nav_110.json` est gitignore).

- [ ] **Step 2: Re-lancer une fois pour confirmer le determinisme**

Run: meme commande. Expected: trajectoires `p_reach` identiques bit-a-bit a Step 1. Si divergence -> investiguer (memory_retriever ambiant ? graine ?) avant de rediger le verdict.

- [ ] **Step 3: Rediger le doc EDR**

Creer `docs/EDR/110_<slug>.md` selon le moule 105/106/107 : contexte (EDR107 -> architecture), question, methode (echelle capacite figee + double lecture gen0/plateau), TABLE des 4 bras, pente vs log2(N), delta, VERDICT pre-enregistre atteint, lecture secondaire gen0, caveats (R=1 ; gen0 vs plateau), suite. Titre = le verdict obtenu (slug ASCII).

- [ ] **Step 4: Mettre a jour la memoire**

Mettre a jour `lewis-energy-economy-wall.md` (chaine 090...107 -> 110) et la ligne 8 de `MEMORY.md`. Lier `[[nas-d1-metabolic-cost-refuted]]`, `[[nas-bottleneck-is-substrate-not-search]]`, `[[from-genome-flattens-architecture]]`.

- [ ] **Step 5: Commit doc EDR**

```bash
git add docs/EDR/110_*.md
git commit -m "docs(EDR110): verdict <verdict> (capacite cachee monte-t-elle le plafond de navigation)"
```

---

## Notes de revue (pour le reviewer final)

- **Verifier qu'aucun chemin existant n'est modifie** : `git diff origin/main -- tools/lewis_survival_sweep.py` ne doit ajouter que des fonctions (`_fresh_genome`, `_capacity_mc`, `_capacity_arm`, `_verdict_capacity`, `_report_capacity_nav`, `main_capacity_nav`), zero ligne supprimee/modifiee ailleurs.
- **Capacite figee effective** : l'assert `g.num_nodes == 167 + n_hidden` dans `_capacity_arm` est le garde-fou central ; il DOIT etre present (sans lui, add_node/prune par defaut feraient deriver les bras).
- **ASCII** : grep les `print` ajoutes pour fleche unicode/accents/x.
- **Seuils du verdict** : delta>=0.10, slope vs log2(N), abs(slope)<0.05 pour INERTE — coherents avec la spec section 5.
- **Smoke a seed 12345** (pas 110) : confirme que le test ne collisionne pas la provenance du run reel.
