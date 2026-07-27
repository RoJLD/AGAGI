# Substrate Functional-Aliasing Calibration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer et calibrer un garde d'aliasing FONCTIONNEL de substrat (`assert_no_functional_aliasing`) + sa sonde, sur le vrai chemin récurrent d'AGAGI, pour donner à SP-2 mesuré un contrôle de spécificité opposable.

**Architecture:** Un `Genome` câblé à la main (matrice `W` contrôlée) tourne dans le VRAI `recurrent_forward`. Câblage disjoint (α=0) → ablater l'entrée X est un no-op EXACT sur une sortie de contrôle Y ; câblage partagé (α>0) → Y fuit. Trois unités : le génome-étalon paramétré (dans `ground_truth_worlds.py`), la sonde (`functional_aliasing_probe.py`), le garde de pré-vol (dans `experiment_preflight.py`). Déterministe (aucun seed).

**Tech Stack:** Python 3, numpy, pytest. Réutilise `src.seed_ai.mutation.Genome`, `src.seed_ai.rl_evolution.recurrent_forward`, `tools/experiment_preflight.py`. Aucune dépendance nouvelle, aucun torch requis, aucun KuzuDB.

## Global Constraints

- **Layout du génome (verbatim, ne pas dériver)** : `I=2`, `O=2`, `N=7`. Nœuds : `0`=X(in), `1`=Y(in), `2`=hA, `3`=hB, `4`=hS (cachés), `5`=out_X, `6`=out_Y (sorties). `W[i,j]` = poids source i → cible j. Câblage : `W[0,2]=1` (X→hA), `W[2,5]=1` (hA→out_X), `W[1,3]=1` (Y→hB), `W[3,6]=1` (hB→out_Y), `W[0,4]=1` (X→hS), `W[4,6]=alpha` (hS→out_Y). Diagonale = 0 (δ=0.5). `W` en `float32`.
- **Conventions d'index de la sonde** : `x_input` = index d'ENTRÉE (`[0:I]`) à ablater ; `x_readout`/`control_readout` = index relatifs aux O SORTIES (0-based dans `preds`, longueur O). Étalon : `x_input=0`, `x_readout=0` (out_X), `control_readout=1` (out_Y).
- **`settle_ticks=4`** (δ=0.5 → ~93 % stabilisé ; un chemin 2-sauts exige ≥2 ticks, on reboucle `H` en `H_prev`). MCTS OFF (génome reflex par défaut).
- **Déterminisme** : `recurrent_forward` est pur → le no-op est EXACT (bit-identique), aucun seed. Ne jamais introduire de RNG non seedé.
- **Valeurs mesurées (vérité-terrain, vérifiées)** : α=0 → `leakage == 0.0` EXACT, `x_response ≈ 0.466`, `out_Y ≈ 0.466`. Balayage α∈{0, 0.3, 0.6, 1.0} → leakage ≈ {0.0, 0.099, 0.177, 0.253}, strictement croissant. `out_X ≈ 0.466` constant.
- **Nommage cliquet** : `run_functional_aliasing_probe` (motif `run_\w*probe`) et `functional_aliasing_verdict` (motif `\w*verdict\w*`) DOIVENT tripper le cliquet ET figurer dans `CALIBRATED`. `make_aliasing_genome`, `assert_no_functional_aliasing`, et les helpers privés (`_run`, `_settle`) ne doivent matcher AUCUN motif d'instrument.
- **Fusion instrument+calibration** : la sonde et ses cas de calibration entrent dans le MÊME commit (le hook pre-commit bloque un instrument non calibré — leçon CALIB-SP3).
- **Pas de bail `kuzu`** : pur numpy via `recurrent_forward`, aucune simulation de monde.
- **Commits path-scoped** : `git add <chemins explicites>` uniquement — JAMAIS `git add -A`/`.`/`-a`. Arbre partagé entre sessions parallèles (fichiers non liés modifiés). Branche courante `feat/d1-prod-pairing`.

## File Structure

- `tools/ground_truth_worlds.py` (MODIFIÉ) — ajout de `make_aliasing_genome(alpha)`, à côté de `partial_oracle` et du monde-jouet SP-3.
- `tools/functional_aliasing_probe.py` (NOUVEAU) — la sonde (`run_functional_aliasing_probe`, `functional_aliasing_verdict`) + un `main()` CLI branché au pré-vol.
- `tools/experiment_preflight.py` (MODIFIÉ) — ajout du garde `assert_no_functional_aliasing`.
- `tests/test_functional_aliasing.py` (NOUVEAU) — tests unitaires du génome, de la sonde, du garde, du CLI.
- `tests/sandbox/test_instrument_calibration.py` (MODIFIÉ) — entrées `CALIBRATED` + cas de calibration + contraste structurel/fonctionnel.
- `docs/EDR/CALIB-ALIAS_Functional_Aliasing_Guard.md` (NOUVEAU) — le record du verdict go/no-go.

---

### Task 1: Génome-étalon paramétré `make_aliasing_genome`

**Files:**
- Modify: `tools/ground_truth_worlds.py` (ajout en fin de fichier)
- Test: `tests/test_functional_aliasing.py`

**Interfaces:**
- Consumes: `src.seed_ai.mutation.Genome`, `src.seed_ai.rl_evolution.recurrent_forward`.
- Produces: `make_aliasing_genome(alpha) -> Genome` (I=2, O=2, N=7, câblage de la §Global Constraints).

- [ ] **Step 1: Écrire les tests du génome (qui échouent)**

Create `tests/test_functional_aliasing.py`:

```python
import numpy as np


def _settle(genome, x, y, ticks=4):
    """Fait tourner recurrent_forward `ticks` fois en rebouclant H ; renvoie preds (O,) = [out_X, out_Y]."""
    from src.seed_ai.rl_evolution import recurrent_forward
    N = genome.num_nodes
    H = np.zeros((1, N), dtype=np.float32)
    Hh = np.zeros((1, 1, N), dtype=np.float32)
    Hp = np.zeros((1, N), dtype=np.float32)
    obs = np.array([[x, y]], dtype=np.float32)
    preds = None
    for _ in range(ticks):
        preds, H, Hh, Hp, _ = recurrent_forward(genome, obs, H, Hh, Hp, 0.0)
    return preds[0].copy()


def test_genome_layout_and_capabilities_respond():
    from tools.ground_truth_worlds import make_aliasing_genome
    g = make_aliasing_genome(0.0)
    assert g.num_nodes == 7 and g.num_inputs == 2 and g.num_outputs == 2
    on = _settle(g, 1.0, 1.0)
    x_off = _settle(g, 0.0, 1.0)
    y_off = _settle(g, 1.0, 0.0)
    assert abs(on[0] - x_off[0]) > 0.1, "out_X doit répondre à X (métrique vivante)"
    assert abs(on[1] - y_off[1]) > 0.1, "out_Y doit répondre à Y (métrique vivante)"


def test_disjoint_is_exact_noop_on_control_output():
    from tools.ground_truth_worlds import make_aliasing_genome
    g = make_aliasing_genome(0.0)
    intact = _settle(g, 1.0, 1.0)
    ablated = _settle(g, 0.0, 1.0)          # X ablaté (entrée 0 = 0)
    assert intact[1] == ablated[1], "α=0 : out_Y doit être BIT-IDENTIQUE (no-op exact)"
    assert abs(intact[0] - ablated[0]) > 0.1, "…mais out_X (capacité propre de X) DOIT chuter"


def test_shared_leaks_and_is_monotone_in_alpha():
    from tools.ground_truth_worlds import make_aliasing_genome
    leaks = []
    for alpha in (0.0, 0.3, 0.6, 1.0):
        g = make_aliasing_genome(alpha)
        leaks.append(abs(_settle(g, 1.0, 1.0)[1] - _settle(g, 0.0, 1.0)[1]))
    assert leaks[0] == 0.0, f"α=0 doit être un no-op exact : {leaks}"
    assert leaks == sorted(leaks) and leaks[-1] > leaks[0], f"fuite non monotone : {leaks}"
    assert leaks[-1] > 0.1, f"α=1 doit fuir nettement : {leaks[-1]}"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_functional_aliasing.py -v`
Expected: FAIL — `ImportError: cannot import name 'make_aliasing_genome'`.

- [ ] **Step 3: Implémenter le génome-étalon**

Append to `tools/ground_truth_worlds.py`:

```python
# ------------------------------------------------------------------------------------------------
# CALIB-ALIAS — GÉNOME-ÉTALON D'ALIASING FONCTIONNEL. Câblé à la main, injecté dans le VRAI
# recurrent_forward (même esprit que partial_oracle). Deux capacités : X (in 0 -> hA -> out_X) et
# Y (in 1 -> hB -> out_Y). `alpha` dose une FUITE de X vers out_Y (in 0 -> hS -> alpha*out_Y). À
# alpha=0 les capacités sont DISJOINTES : ablater X est un no-op EXACT sur out_Y. Réponse connue par
# construction. Layout : [0:I] entrées, [I:N-O] cachés, [N-O:N] sorties ; W[i,j] = source i -> cible j.
# ------------------------------------------------------------------------------------------------

def make_aliasing_genome(alpha):
    """Génome-étalon à DOSE de partage `alpha` (I=2, O=2, N=7). Voir en-tête de section pour le câblage.
    Diagonale = 0 (forget-gate δ=0.5). Reflex (MCTS off) -> 1 micro-tick par appel de recurrent_forward."""
    import numpy as np
    from src.seed_ai.mutation import Genome
    I, O, N = 2, 2, 7
    W = np.zeros((N, N), dtype=np.float32)
    W[0, 2] = 1.0          # X -> hA
    W[2, 5] = 1.0          # hA -> out_X
    W[1, 3] = 1.0          # Y -> hB
    W[3, 6] = 1.0          # hB -> out_Y
    W[0, 4] = 1.0          # X -> hS
    W[4, 6] = float(alpha)  # hS -> out_Y (dose de fuite : 0 = disjoint)
    return Genome(W, I, O)
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/test_functional_aliasing.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/ground_truth_worlds.py tests/test_functional_aliasing.py
git commit -m "feat(CALIB-ALIAS): genome-etalon d'aliasing fonctionnel (cable a la main, vrai recurrent_forward)"
```

---

### Task 2: Garde de pré-vol `assert_no_functional_aliasing`

**Files:**
- Modify: `tools/experiment_preflight.py` (ajout, section « C. mesurer ce qui agit »)
- Test: `tests/test_functional_aliasing.py` (ajout)

**Interfaces:**
- Consumes: `PreflightError` (déjà dans le module).
- Produces: `assert_no_functional_aliasing(control_intact, control_ablated, tol=1e-9, label="capacité de contrôle") -> True`, lève `PreflightError` si `|control_intact − control_ablated| > tol`.

- [ ] **Step 1: Écrire les tests du garde (qui échouent)**

Add to `tests/test_functional_aliasing.py`:

```python
def test_functional_guard_passes_when_control_unchanged():
    from tools.experiment_preflight import assert_no_functional_aliasing
    assert assert_no_functional_aliasing(0.4658, 0.4658) is True


def test_functional_guard_fires_when_control_moves():
    import pytest
    from tools.experiment_preflight import assert_no_functional_aliasing, PreflightError
    with pytest.raises(PreflightError):
        assert_no_functional_aliasing(0.4658, 0.7190)      # fuite mesurée à α=1


def test_functional_guard_respects_tolerance():
    from tools.experiment_preflight import assert_no_functional_aliasing
    assert assert_no_functional_aliasing(1.0, 1.0 + 1e-12) is True   # sous la tolérance
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_functional_aliasing.py -k functional_guard -v`
Expected: FAIL — `ImportError: cannot import name 'assert_no_functional_aliasing'`.

- [ ] **Step 3: Implémenter le garde**

Add to `tools/experiment_preflight.py`, immediately AFTER the existing `assert_no_aliasing` function (same « C. mesurer ce qui agit » section):

```python
def assert_no_functional_aliasing(control_intact, control_ablated, tol=1e-9, label="capacité de contrôle"):
    """Complément COMPORTEMENTAL de `assert_no_aliasing` (qui, lui, est STRUCTUREL via np.shares_memory).

    Une capacité de CONTRÔLE, connue INDÉPENDANTE du canal ablaté, ne doit pas bouger sous l'ablation.
    Si elle bouge, l'ablation agit par un canal partagé du substrat (aliasing FONCTIONNEL) — et tout
    verdict de demande tiré de cette ablation est contaminé.

    Aurait attrapé (le faux positif que SP-2 hériterait) : ablater X pour mesurer « Y demande-t-elle X ? »
    sur un substrat où X et Y partagent des neurones effondre Y par la représentation partagée, pas parce
    que Y demande X. `np.shares_memory` est AVEUGLE à ça (buffers séparés) ; ce garde le mesure."""
    d = abs(float(control_intact) - float(control_ablated))
    if d > float(tol):
        raise PreflightError(
            f"{label} a BOUGÉ de {d:.4g} (> tol {float(tol):.1g}) sous l'ablation d'un canal censé lui être "
            "ÉTRANGER : aliasing FONCTIONNEL de substrat. L'ablation n'est pas chirurgicale -> tout verdict "
            "de demande qui en découle est contaminé (mesurer sur une capacité de contrôle indépendante).")
    return True
```

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `python -m pytest tests/test_functional_aliasing.py -k functional_guard -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/experiment_preflight.py tests/test_functional_aliasing.py
git commit -m "feat(CALIB-ALIAS): garde de pre-vol assert_no_functional_aliasing (complement comportemental)"
```

---

### Task 3: Sonde + calibration (FUSIONNÉS — instrument et cliquet dans la même passe)

**Files:**
- Create: `tools/functional_aliasing_probe.py`
- Modify: `tests/sandbox/test_instrument_calibration.py` (CALIBRATED + cas)
- Test: `tests/test_functional_aliasing.py` (ajout de tests unitaires de la sonde)

**Interfaces:**
- Consumes: `make_aliasing_genome` (Task 1), `assert_no_functional_aliasing` + `assert_no_aliasing` (Task 2 / existant), `recurrent_forward`.
- Produces:
  - `run_functional_aliasing_probe(genome, x_input=0, x_readout=0, control_readout=1, settle_ticks=4, test_input=(1.0, 1.0)) -> dict` : `{"leakage", "x_response", "control_intact", "control_ablated", "verdict"}`.
  - `functional_aliasing_verdict(leakage, x_response, tol=1e-9) -> str` : `"VACUOUS_ABLATION"` | `"SURGICAL"` | `"FUNCTIONAL_LEAK"`.

- [ ] **Step 1: Écrire les tests unitaires de la sonde (qui échouent)**

Add to `tests/test_functional_aliasing.py`:

```python
def test_probe_surgical_on_disjoint():
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(0.0))
    assert r["leakage"] == 0.0 and r["verdict"] == "SURGICAL" and r["x_response"] > 0.1


def test_probe_leak_on_shared():
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(1.0))
    assert r["leakage"] > 0.1 and r["verdict"] == "FUNCTIONAL_LEAK"


def test_verdict_flags_vacuous_ablation():
    # ablate Y (in 1) mais lire out_X (readout 0) : out_X ne dépend pas de Y -> x_response=0 -> vacux
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(0.0), x_input=1, x_readout=0, control_readout=0)
    assert r["x_response"] == 0.0 and r["verdict"] == "VACUOUS_ABLATION"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_functional_aliasing.py -k "probe or vacuous" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.functional_aliasing_probe'`.

- [ ] **Step 3: Implémenter la sonde**

Create `tools/functional_aliasing_probe.py`:

```python
"""CALIB-ALIAS — l'ablation within-subject d'un canal d'entrée reste-t-elle CHIRURGICALE sur le vrai
substrat récurrent, ou fuit-elle vers une capacité de contrôle par la représentation partagée ?

On fait tourner un génome-étalon dans le VRAI recurrent_forward, entrée intacte vs colonne `x_input`=0,
et on lit la variation d'une sortie de CONTRÔLE. Fuite -> l'ablation n'est pas chirurgicale. Le nom
`run_*probe` / `*verdict*` trippe volontairement le cliquet. Usage : python tools/functional_aliasing_probe.py
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.seed_ai.rl_evolution import recurrent_forward


def _settle(genome, obs_vec, settle_ticks):
    """recurrent_forward `settle_ticks` fois (H rebouclé) ; renvoie preds (O,) copié."""
    N = genome.num_nodes
    H = np.zeros((1, N), dtype=np.float32)
    Hh = np.zeros((1, 1, N), dtype=np.float32)
    Hp = np.zeros((1, N), dtype=np.float32)
    obs = np.asarray([obs_vec], dtype=np.float32)
    preds = None
    for _ in range(int(settle_ticks)):
        preds, H, Hh, Hp, _ = recurrent_forward(genome, obs, H, Hh, Hp, 0.0)
    return preds[0].copy()


def run_functional_aliasing_probe(genome, x_input=0, x_readout=0, control_readout=1,
                                  settle_ticks=4, test_input=(1.0, 1.0)):
    """Ablate chirurgicalement l'entrée `x_input` (colonne -> 0) et mesure la fuite sur la sortie de
    contrôle `control_readout` vs la réponse de la capacité propre `x_readout`. Voir docstring du module."""
    intact_vec = list(test_input)
    ablated_vec = list(test_input)
    ablated_vec[int(x_input)] = 0.0
    intact = _settle(genome, intact_vec, settle_ticks)
    ablated = _settle(genome, ablated_vec, settle_ticks)
    leakage = float(abs(intact[int(control_readout)] - ablated[int(control_readout)]))
    x_response = float(abs(intact[int(x_readout)] - ablated[int(x_readout)]))
    return {"leakage": leakage, "x_response": x_response,
            "control_intact": float(intact[int(control_readout)]),
            "control_ablated": float(ablated[int(control_readout)]),
            "verdict": functional_aliasing_verdict(leakage, x_response)}


def functional_aliasing_verdict(leakage, x_response, tol=1e-9):
    """VACUOUS_ABLATION si l'ablation ne fait RIEN à la capacité propre (générateur A échoué) ; SURGICAL
    si la fuite sur le contrôle est nulle ; FUNCTIONAL_LEAK sinon."""
    if float(x_response) <= float(tol):
        return "VACUOUS_ABLATION"
    if float(leakage) <= float(tol):
        return "SURGICAL"
    return "FUNCTIONAL_LEAK"
```

- [ ] **Step 4: Lancer les tests unitaires de la sonde, vérifier le succès**

Run: `python -m pytest tests/test_functional_aliasing.py -k "probe or vacuous" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Déclarer les instruments calibrés**

In `tests/sandbox/test_instrument_calibration.py`, add two entries to the `CALIBRATED` dict (inside the existing `{...}`):

```python
    # CALIB-ALIAS : aliasing FONCTIONNEL de substrat (câblage imposé dans le vrai recurrent_forward).
    # no-op EXACT sur disjoint, FUITE sur partagé, monotone en la dose, + contraste : np.shares_memory
    # (le garde STRUCTUREL) est aveugle à la fuite que le garde COMPORTEMENTAL attrape.
    "run_functional_aliasing_probe": ["*"],
    "functional_aliasing_verdict": ["*"],
```

- [ ] **Step 6: Écrire les cas de calibration**

Append to `tests/sandbox/test_instrument_calibration.py`:

```python
# --- CALIB-ALIAS : run_functional_aliasing_probe / functional_aliasing_verdict ----------------------
# Étalon = un génome câblé à la main dans le VRAI recurrent_forward. Réponse connue PAR CONSTRUCTION :
# α=0 disjoint (ablater X = no-op exact sur out_Y), α>0 partagé (fuite), monotone en α. Déterministe.


def test_alias_noop_exact_on_disjoint_substrate():
    """no-op EXACT (spécificité) : sur un câblage DISJOINT, ablater X ne touche PAS out_Y (bit-identique),
    mais tue bien out_X (ablation NON vacuse -> générateur A). Mesuré : leakage 0.0, x_response ~0.466."""
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(0.0))
    assert r["leakage"] == 0.0 and r["verdict"] == "SURGICAL"
    assert r["x_response"] > 0.1, "l'ablation doit changer la capacité PROPRE de X (sinon no-op vacux)"


def test_alias_positive_control_leak_on_shared_substrate():
    """contrôle positif : sur un câblage PARTAGÉ (α=1), ablater X fait FUIR out_Y. Mesuré : leakage ~0.253."""
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(1.0))
    assert r["verdict"] == "FUNCTIONAL_LEAK" and r["leakage"] > 0.1


def test_alias_leakage_is_monotone_in_the_sharing_dose():
    """monotonie (direction) : la fuite croît avec la dose de partage α. Mesuré : ~0/0.099/0.177/0.253."""
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    leaks = [run_functional_aliasing_probe(make_aliasing_genome(a))["leakage"] for a in (0.0, 0.3, 0.6, 1.0)]
    assert leaks[0] == 0.0, f"α=0 doit être un no-op exact : {leaks}"
    assert all(a < b for a, b in zip(leaks, leaks[1:])), f"fuite non STRICTEMENT croissante : {leaks}"


def test_alias_structural_guard_is_blind_to_functional_leak():
    """LE CONTRASTE QUI JUSTIFIE LE NOUVEAU GARDE. Sur le substrat partagé, la sortie de contrôle FUIT,
    mais les deux mesures sont des arrays INDÉPENDANTS -> np.shares_memory est False -> l'ancien garde
    STRUCTUREL `assert_no_aliasing` PASSE (aveugle), tandis que le garde COMPORTEMENTAL tire."""
    import numpy as np
    import pytest
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    from tools.experiment_preflight import assert_no_aliasing, assert_no_functional_aliasing, PreflightError
    r = run_functional_aliasing_probe(make_aliasing_genome(1.0))
    ci = np.array([r["control_intact"]], dtype=np.float32)
    ca = np.array([r["control_ablated"]], dtype=np.float32)
    assert not np.shares_memory(ci, ca), "deux mesures indépendantes ne partagent pas la mémoire"
    assert assert_no_aliasing(ci, ca) is True, "le garde STRUCTUREL est aveugle à la fuite fonctionnelle"
    with pytest.raises(PreflightError):
        assert_no_functional_aliasing(r["control_intact"], r["control_ablated"])
```

- [ ] **Step 7: Lancer les cas de calibration + vérifier le cliquet VERT**

Run: `python -m pytest tests/sandbox/test_instrument_calibration.py -k alias -v`
Expected: PASS (4 tests).

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.` (les deux `*_probe`/`*verdict` détectés apparaissent calibrés).

- [ ] **Step 8: Commit (FUSIONNÉ — sonde + calibration)**

```bash
git add tools/functional_aliasing_probe.py tests/test_functional_aliasing.py tests/sandbox/test_instrument_calibration.py
git status --short   # confirmer UNIQUEMENT ces trois chemins
git commit -m "feat(CALIB-ALIAS): sonde d'aliasing fonctionnel + calibration (instrument + cliquet meme passe)"
```

Le hook pre-commit passe (calibration accompagne l'instrument). S'il échoue, lire sa sortie et rapporter BLOCKED — ne PAS utiliser `--no-verify`.

---

### Task 4: CLI go/no-go + record

**Files:**
- Modify: `tools/functional_aliasing_probe.py` (ajout d'un `main()`)
- Create: `docs/EDR/CALIB-ALIAS_Functional_Aliasing_Guard.md`
- Test: `tests/test_functional_aliasing.py` (ajout d'un test du pré-vol/main)

**Interfaces:**
- Consumes: tout ce qui précède + `tools/experiment_preflight.py` (`declare_design`, `assert_no_functional_aliasing`, `PreflightError`).
- Produces: `main() -> int` (0 = GO, 1 = NO-GO) ; imprime le verdict go/no-go.

- [ ] **Step 1: Écrire le test du pré-vol (qui échoue)**

Add to `tests/test_functional_aliasing.py`:

```python
def test_preflight_passes_and_main_reports_go():
    from tools.functional_aliasing_probe import main
    assert main() == 0, "disjoint SURGICAL + partagé FUNCTIONAL_LEAK -> GO"
```

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `python -m pytest tests/test_functional_aliasing.py -k preflight -v`
Expected: FAIL — `ImportError: cannot import name 'main'`.

- [ ] **Step 3: Implémenter `main()`**

Append to `tools/functional_aliasing_probe.py`:

```python
def main():
    """Go/no-go CALIB-ALIAS. GO ssi : disjoint -> SURGICAL (no-op exact) ET le garde comportemental passe ;
    partagé -> FUNCTIONAL_LEAK ET le garde comportemental TIRE. Renvoie 0 (GO) ou 1 (NO-GO)."""
    from tools.experiment_preflight import (declare_design, assert_no_functional_aliasing, PreflightError)
    from tools.ground_truth_worlds import make_aliasing_genome

    design = declare_design(
        question="L'ablation within-subject d'un canal reste-t-elle chirurgicale (pas de fuite vers une "
                 "capacité de contrôle) sur le vrai substrat récurrent ?",
        replication_unit="génome-étalon (déterministe)", n_independent=1,
        links={"cablage_impose->reponse": "measured", "ablation->fuite": "measured"},
        cost_estimate="pur numpy, < 1 s")
    print(f"DESIGN: {design['replication_unit']}")

    disjoint = run_functional_aliasing_probe(make_aliasing_genome(0.0))
    shared = run_functional_aliasing_probe(make_aliasing_genome(1.0))

    # disjoint : le garde comportemental DOIT passer (contrôle inchangé)
    guard_ok_on_disjoint = True
    try:
        assert_no_functional_aliasing(disjoint["control_intact"], disjoint["control_ablated"])
    except PreflightError:
        guard_ok_on_disjoint = False
    # partagé : le garde comportemental DOIT tirer (contrôle a bougé)
    guard_fires_on_shared = False
    try:
        assert_no_functional_aliasing(shared["control_intact"], shared["control_ablated"])
    except PreflightError:
        guard_fires_on_shared = True

    passed = (disjoint["verdict"] == "SURGICAL" and disjoint["leakage"] == 0.0 and guard_ok_on_disjoint
              and shared["verdict"] == "FUNCTIONAL_LEAK" and guard_fires_on_shared)
    verdict = "GO (ablation isolable + garde opposable)" if passed else "NO-GO"
    print(f"VERDICT CALIB-ALIAS = {verdict} | disjoint leakage={disjoint['leakage']:.4f} ({disjoint['verdict']}) "
          f"garde_passe={guard_ok_on_disjoint} | partagé leakage={shared['leakage']:.4f} "
          f"({shared['verdict']}) garde_tire={guard_fires_on_shared}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

Note : ajouter `main()` AVANT le bloc `if __name__`, et vérifier qu'il n'y a qu'UN seul `if __name__ == "__main__":` dans le fichier (Task 3 n'en a pas créé).

- [ ] **Step 4: Lancer le test + la CLI, vérifier le succès**

Run: `python -m pytest tests/test_functional_aliasing.py -k preflight -v`
Expected: PASS.

Run: `python tools/functional_aliasing_probe.py`
Expected: affiche `VERDICT CALIB-ALIAS = GO ... | disjoint leakage=0.0000 (SURGICAL) garde_passe=True | partagé leakage=0.2532 (FUNCTIONAL_LEAK) garde_tire=True`. **Noter les valeurs affichées** pour le record.

- [ ] **Step 5: Écrire le record**

Create `docs/EDR/CALIB-ALIAS_Functional_Aliasing_Guard.md` (remplacer les valeurs par celles affichées à l'étape 4 si elles diffèrent) :

```markdown
---
id: CALIB-ALIAS
type: EDR
title: "L'ablation within-subject est chirurgicale sur un substrat DISJOINT (no-op exact) mais fuit sur un substrat PARTAGÉ — nouveau garde assert_no_functional_aliasing, aveugle-point de np.shares_memory comblé"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
---

## Question
CALIB-SP3 (GO) a validé l'ablation within-subject en A1 SANS substrat partagé, et a différé l'aliasing de
substrat à SP-2. Sur le vrai chemin récurrent où deux capacités partagent des neurones, ablater X pour
mesurer « Y demande X ? » peut effondrer Y par la représentation partagée — un faux positif. Le garde
existant `assert_no_aliasing` (np.shares_memory) n'attrape que l'aliasing de mémoire-vue (EDR-WARM-007),
pas l'aliasing FONCTIONNEL.

## Méthode
Génome câblé à la main injecté dans le VRAI `recurrent_forward` : X (in0→hA→out_X), Y (in1→hB→out_Y), fuite
dosée X→hS→α·out_Y. Ablation chirurgicale mono-canal (colonne d'entrée → 0), K=4 ticks de stabilisation.
Déterministe → no-op EXACT (bit-identique), pas statistique.

## Résultat
GO. Disjoint (α=0) : leakage 0.0000 EXACT (out_Y bit-identique) — SURGICAL — pendant que out_X chute (0.466,
ablation non vacuse). Partagé (α=1) : leakage 0.2532 — FUNCTIONAL_LEAK. Monotone en α (0 / 0.099 / 0.177 /
0.253). **Contraste gravé** : sur le partagé, np.shares_memory est False → `assert_no_aliasing` PASSE
(aveugle) alors que le nouveau `assert_no_functional_aliasing` TIRE. Le point-aveugle structurel est comblé.

## Portée (bornée)
Établit que l'ablation within-subject EST fonctionnellement isolable QUAND les capacités sont séparables, et
qu'un contrôle comportemental sur une capacité indépendante détecte la non-séparabilité. L'APPLICATION à un
MambaAgent ÉVOLUÉ réel (câblage appris, non contrôlable) reste SP-2. La correction du `.clone()` conditionnel
par défaut de `TorchPopulationModel.forward` (aliasing mémoire-vue encore actif) = dette séparée.

## Ce que ça débloque
SP-2 mesuré dispose d'un garde de spécificité opposable : avant de conclure « Y demande X » d'une ablation,
`assert_no_functional_aliasing` sur une capacité de contrôle indépendante. Cf.
`docs/superpowers/specs/2026-07-23-substrate-functional-aliasing-calibration-design.md`.
```

- [ ] **Step 6: Vérifier les liens du record + la suite + le cliquet**

Run: `python tools/check_record_links.py`
Expected: aucun orphelin pour `CALIB-ALIAS`.

Run: `python -m pytest tests/test_functional_aliasing.py tests/sandbox/test_instrument_calibration.py -k "alias or functional or genome or disjoint or shared or probe or vacuous or preflight or guard" -v`
Expected: tous PASS.

Run: `python tools/check_instrument_calibration.py`
Expected: `OK : aucun nouvel instrument non calibré.`

- [ ] **Step 7: Commit**

```bash
git add tools/functional_aliasing_probe.py tests/test_functional_aliasing.py docs/EDR/CALIB-ALIAS_Functional_Aliasing_Guard.md
git commit -m "feat(CALIB-ALIAS): CLI go/no-go + record (GO, garde comportemental comble l'aveugle-point structurel)"
```

---

## Self-Review

**Spec coverage :**
- §2 question / go-no-go → Task 4 `main()`. ✓
- §3 payload (contraste structurel/fonctionnel + générateur A + non vacux) → Task 3 `test_alias_structural_guard_is_blind_to_functional_leak`, `functional_aliasing_verdict` (VACUOUS_ABLATION). ✓
- §4 approche (vrai recurrent_forward + câblage imposé) → Task 1 `make_aliasing_genome`. ✓
- §6.1 génome → Task 1. §6.2 sonde → Task 3. §6.3 garde → Task 2. ✓
- §8 trois formes (no-op exact / positif / monotone) + contraste → Task 3 (4 cas de calibration). ✓
- §9 cliquet (2 instruments détectés + CALIBRATED), pré-vol (garde ajouté), record → Tasks 3+2+4. ✓
- §10 déterminisme, no seed → Global Constraints + no-op EXACT (`== 0.0`). ✓
- §11 portée v0 (1 génome paramétré, 4 α) → fixtures. ✓
- §14 pièges (2 sauts≥2 ticks / injection destructive / diagonale=gate / halt / métrique vivante) → `settle_ticks=4`, tests « capabilities respond », MCTS off par défaut. ✓

**Placeholder scan :** aucun TBD/TODO ; code complet ; les seules valeurs à reporter (leakage α=1 ~0.253) sont MESURÉES et insérées, à re-confirmer au Step 4 de Task 4.

**Type consistency :** `make_aliasing_genome(alpha) -> Genome` ; `run_functional_aliasing_probe(genome, x_input, x_readout, control_readout, settle_ticks, test_input) -> {leakage, x_response, control_intact, control_ablated, verdict}` ; `functional_aliasing_verdict(leakage, x_response, tol) -> str` ; `assert_no_functional_aliasing(control_intact, control_ablated, tol, label) -> True|raise` — noms et signatures identiques entre Tasks 1→4. ✓
