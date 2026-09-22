# Harnais R1 (semaines 1-3) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer les deux contrats (`Task`, `Learner`), le verdict pur à trois conditions, le runner de cellule, le learner tabulaire de vérité-terrain, le port de `CompositionTask`, l'adaptateur `ConnectomeLearner`, puis sceller et exécuter la famille `HARNESS-R1` (cellules A, A', B) et graver son record.

**Architecture:** Contrats + lecture de verdict PURE dans `src/seed_ai/` (périmètre des quatre cliquets) ; tâches, learners, runner et scripts dans `tools/harness/` (os.walk récursif : couvert). Le runner compose l'existant (`experiment_preflight`, `preregister`, `cost_guard`, `demand_marker.ablation_verdict`, `alias_guard_verdict`, `learner_verdict`, `Harness.save`). Chaque instrument neuf a son test à réponse connue AVANT tout torch ; le connectome n'entre qu'en tâche 9.

**Tech Stack:** Python 3.13, numpy, torch (optionnel : seuls `connectome.py` et ses tests l'importent), pytest (+ `pytest-timeout`, marqueur `slow`).

**Spec:** `docs/superpowers/specs/2026-09-16-harness-contracts-design.md` (sections 2.1-2.5, 3). Le plan amende le spec sur six points MESURÉS par la cartographie du 2026-09-16 (voir « Amendements »).

## Global Constraints

- Aucun littéral `data/` ou `results/` dans le code : passer par `src.paths.results_file` (porte 12).
- Aucune agrégation `... if xs else <constante>` : `raise` ou `None` (porte 14).
- Toute fonction top-level nommée `assert_*`, `run*`, `*verdict*`, `measure*` et toute MÉTHODE `learn*` est un instrument : entrée `CALIBRATED` **qualifiée** `"chemin::nom"` dans `tests/sandbox/test_instrument_calibration.py` (dict LITTÉRAL, `}` en colonne 0), ou `NOT_AN_INSTRUMENT` qualifié (porte 2).
- Tout fichier contenant `make_population(` doit porter textuellement `<X>.BILINEAR = ...` et un `optim.Adam([...W...])` mentionnant `U`/`V`/`W_bl` (porte 6).
- Aucune barre de la forme `1/K + <constante>` ni `floor + <constante>` sans appel NOMMÉ et INCONDITIONNEL à `assert_bar_separates_the_incapable` dans le même fichier ; écrire `bar = reference_last + 0.05` (porte 9).
- Tout module qui fait `from tools.preregister import verify` et appelle `verify(` doit appeler `declare_design(` ET `provenance(` dans le même fichier (porte 11 + `test_preregistration_guard.py:156`).
- `declare_design(links=...)` avec un maillon `"inferred"` exige `allow_inferred_reason="<texte non vide>"`.
- `dv_primaire` d'une règle scellée = **chaîne** avec grandeurs entre backticks ; `discrimination` = dict avec une clé contenant `AUTRE` (porte 5).
- Unité de réplication = seed ; n = 12 ; `n_agents = 16` n'est PAS un minibatch (batch effectif 1).
- Fichiers PARTAGÉS (`tests/sandbox/test_instrument_calibration.py`, `CLAUDE.md`, `docs/SDR/G2_agent_composes.md`, `docs/roadmap/PRIORITES_ET_DETTES.md`) : `snapshot(...)` AVANT édition, `verify(...)` AVANT commit (`tools/check_staged_authorship.py`) ; commits `git commit -F <msg> -- <chemins>`, jamais nus ; aucun backtick dans une chaîne passée au shell.
- Les tests qui importent torch le font par `pytest.importorskip("torch")` dans LEUR module ; les tests sans torch restent exécutables sans lui. Ne pas écrire le mot `MambaAgent` dans le source d'un test (skip automatique sous bail kuzu) : passer par `ConnectomeLearner`.
- Pas de commit tant que robla n'a pas donné l'ordre pour la séquence en cours (arbre partagé, ~100 fichiers d'autres sessions) ; chaque tâche PRÉPARE son commit (message dans un fichier) et l'exécute sur signal.

## Amendements au spec (mesurés le 2026-09-16, s'imposent au plan)

1. **Cellule B** : le 0,923 de `retain_compose_lr_replication.json` n'est reproduit par `imitate_episode_bptt` qu'avec `n_classes=K` (`align_train_eval=True`) ; à 8 classes le 2-pas rend ≈ 0,80. B scelle `n_classes=6` ; A garde `n_classes=None` (bit-identité avec `results/bilinear_composition.json`). `n_classes` est un hyperparamètre PUBLIÉ dans `regime`.
2. **Référence lr=0** : `build(reference=True)` = Adam à `lr=0.0` avec le MÊME nombre d'épisodes (les épisodes consomment le rng des opérandes ; `episodes=0` déplace le jeu d'éval). Valeurs mesurées seed 0 : bil 0,16875 / plain 0,17031.
3. **Cellule A'** (recall same_tick supervisé 150 ép.) : plain = bilinéaire = **1,0** (seeds 0-2). Réponse connue : (iii) `PIECE_NOT_NECESSARY` avec les deux bras au plafond ; le verdict (iii) est appelé avec `ceiling=None` (deux bras identiques au plafond = « pas nécessaire », pas « dégénéré »), `intervention_verified=True` (L4 a prouvé que la variante change les logits).
4. **Garde de barre** : `assert_bar_separates_the_incapable(bar=ref+0,05, incapable_ceiling=med(D))` LÈVE sur la cellule A attendue PARTIAL (0,217 ≤ 0,271). Elle n'est PAS appelée sur med(D) ; elle est appelée sur le **plafond de REPRÉSENTATION déclaré** et son issue est PUBLIÉE (`bar_status`), jamais levée hors du verdict.
5. `learner_verdict` prend des SCALAIRES et n'a pas de `PRIOR_SOLVES` : `harness_verdict_lecture` compose `PRIOR_SOLVES` AVANT (référence médiane > 0,5) et fait le 12/12 apparié lui-même. Franchissement de barre STRICT (`sep <= 0.05` → INERT).
6. **Drapeaux de classe** `BILINEAR`/`BILINEAR_RANK`/`CONDITION_GATE`/`GATE_TARGET` : relus à CHAQUE `_step` → posés dans `build`, restaurés seulement par `LearnerInstance.close()` (ajouté au contrat, no-op pour le tabulaire) ; une seule instance connectome ouverte par process (verrou de module).

## Structure de fichiers

| fichier | responsabilité | tâche |
|---|---|---|
| `src/seed_ai/harness_task.py` | `Episode`, `Ablation`, `DemandDeclaration`, `Task` (Protocol), `assert_task_contract` | 1 |
| `src/seed_ai/harness_learner.py` | `Piece`, `Dose`, `LearnerInstance`/`Learner` (Protocols), `assert_learner_contract` | 2 |
| `tools/harness/tasks/composition.py` | `CompositionTask` (port de `_make_seq`/`_slot`) | 3 |
| `tools/harness/learners/tabular.py` | `TabularLearner` (vérité-terrain, sans torch) | 4 |
| `src/seed_ai/harness_verdict.py` | `harness_verdict_lecture`, `measure_noise_floor`, `measure_ablated_bayes_ceiling` (purs) | 5 |
| `tools/harness/cell.py` | `run_harness_cell` (bras appariés, éval, JSON) | 6 |
| `src/seed_ai/harness_pieces.py`, `docs/REF/REF-HARNESS-PIECES.md`, `docs/REF/REF-HARNESS-CONTRACTS.md` | registre + prose du contrat | 7 |
| `tests/sandbox/test_instrument_calibration.py`, `CLAUDE.md`, `docs/SDR/G2_agent_composes.md` | déclarations `CALIBRATED`, compteurs | 8 |
| `tools/harness/learners/connectome.py` | `ConnectomeLearner` (adaptateur unique vers `make_population`) | 9 |
| `tools/harness/smoke_r1.py`, `tools/harness/seal_r1.py`, `docs/preregistrations/HARNESS-R1.json` | smoke 3 seeds, scellement | 10 |
| `tools/harness/run_r1.py`, `docs/EDR/HARNESS-R1_*.md` | run n=12, record | 11 |
| `tests/sandbox/test_harness_{task,learner,composition,tabular,verdict,cell,pieces,connectome}.py` | cas à réponse connue | 1-9 |

Aucun `__init__.py` dans `tools/harness/` (packages implicites, comme `tools/evo_runs/`). Imports par `from tools.harness.tasks.composition import CompositionTask` avec `sys.path` sur la racine (convention des tests : `sys.path.insert(0, ...)`).

---

### Task 1: Contrat `Task` et garde `assert_task_contract`

**Files:**
- Create: `src/seed_ai/harness_task.py`
- Test: `tests/sandbox/test_harness_task.py`

**Interfaces:**
- Consumes: `tools.experiment_preflight.PreflightError` (import paresseux dans la garde).
- Produces: `Episode(obs_seq: tuple[np.ndarray], target: np.ndarray, mask_seq: tuple|None, meta: dict)` avec propriétés `n`, `T` ; `Ablation(name, site, must_bite, apply=None, bayes_floor=None)` ; `DemandDeclaration(capacity, ablations, incapable_ceiling=None, key_entropy_bits=None)` ; `assert_task_contract(task, seed=0, n=64) -> dict` avec clés `"bayes_floors"` (dict ablation → float déclaré ou `1/K`), `"certified"`, `"elapsed_ms"`. Toute Task expose `name, version, K, obs_dim, T, demand`, `episodes(rng, n, split="train") -> Episode`, `score(actions, ep) -> np.ndarray (n,)`, `oracle(ep) -> np.ndarray (n,)`, `enumerate_states() -> int|None`, `regime() -> dict`.

- [ ] **Step 1: Écrire le test qui échoue (une Task jouet dans le test, sans torch)**

```python
# tests/sandbox/test_harness_task.py
"""Contrat Task du harnais (spec 2026-09-16 §2.1) : la garde refuse en tête, en < 50 ms, sans entraînement,
tout ce qui rendrait le marqueur de demande incapable de produire LES DEUX issues (question A du pré-vol)."""
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_task import Ablation, DemandDeclaration, Episode, assert_task_contract  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402


class ToyParity:
    """Tâche jouet : obs (n, 4) one-hot de a dans [0,2) sur [0:2) et b sur [2:4) ; cible (a + b) % 2 ; T == 1."""
    name, version, K, obs_dim, T = "toy_parity", "1", 2, 4, 1

    def __init__(self, bite_key=True, with_nobite=True, ceiling=(0.75, "plafond jouet declare pour le test, minorant", False)):
        abls = [Ablation("permute_a", "input", bite_key, apply=self._permute_a, bayes_floor=0.5)]
        if with_nobite:
            abls.append(Ablation("permute_nothing", "input", False, apply=self._permute_nothing))
        self.demand = DemandDeclaration("parity", tuple(abls), incapable_ceiling=ceiling)

    def episodes(self, rng, n, split="train"):
        a = rng.randint(0, 2, size=n)
        b = rng.randint(0, 2, size=n)
        obs = np.zeros((n, 4), dtype=np.float32)
        obs[np.arange(n), a] = 1.0
        obs[np.arange(n), 2 + b] = 1.0
        return Episode((obs,), ((a + b) % 2).astype(np.int64), None, {"a": a, "b": b})

    def _permute_a(self, ep, rng):
        a2 = ep.meta["a"][rng.permutation(ep.n)]
        obs = np.zeros_like(ep.obs_seq[0])
        obs[np.arange(ep.n), a2] = 1.0
        obs[np.arange(ep.n), 2 + ep.meta["b"]] = 1.0
        return Episode((obs,), ep.target.copy(), None, {"a": a2, "b": ep.meta["b"]})

    def _permute_nothing(self, ep, rng):
        return Episode((ep.obs_seq[0].copy(),), ep.target.copy(), None, dict(ep.meta))

    def score(self, actions, ep):
        if ep.n == 0:
            raise ValueError("score : episode vide")
        return (np.asarray(actions) == ep.target).astype(np.float32)

    def oracle(self, ep):
        return (ep.meta["a"] + ep.meta["b"]) % 2

    def enumerate_states(self):
        return 4

    def regime(self):
        return {"K": 2, "T": 1}


def test_toy_task_passes_the_contract_and_reports_bayes_floors():
    out = assert_task_contract(ToyParity(), seed=0, n=64)
    assert out["certified"] is True
    assert out["bayes_floors"] == {"permute_a": 0.5}
    assert out["elapsed_ms"] < 50.0


def test_contract_refuses_a_task_without_a_non_biting_ablation():
    with pytest.raises(PreflightError, match="must_bite=False"):
        assert_task_contract(ToyParity(with_nobite=False))


def test_contract_refuses_a_biting_ablation_that_does_not_bite():
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (Ablation("permute_nothing", "input", True, apply=task._permute_nothing),
                                               Ablation("nobite", "input", False, apply=task._permute_nothing)))
    with pytest.raises(PreflightError, match="permute_nothing"):
        assert_task_contract(task)


def test_contract_refuses_a_verifier_that_is_the_oracle():
    task = ToyParity()
    task.score = lambda actions, ep: np.ones(ep.n, dtype=np.float32)   # note 1.0 quoi qu'on reponde
    with pytest.raises(PreflightError, match="oracle décalé"):
        assert_task_contract(task)


def test_contract_refuses_an_aliased_ablation():
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (
        Ablation("alias", "input", True, apply=lambda ep, rng: Episode(ep.obs_seq, ep.target, None, dict(ep.meta)), bayes_floor=0.5),
        Ablation("nobite", "input", False, apply=task._permute_nothing)))
    with pytest.raises(PreflightError, match="shares_memory|VUE"):
        assert_task_contract(task)


def test_contract_refuses_chance_as_representational_ceiling():
    with pytest.raises(PreflightError, match="1/K"):
        assert_task_contract(ToyParity(ceiling=(0.5, "chance deguisee en plafond, vingt caracteres", False)))


def test_contract_refuses_a_short_provenance():
    with pytest.raises(PreflightError, match="provenance"):
        assert_task_contract(ToyParity(ceiling=(0.75, "court", False)))


def test_contract_refuses_non_reproducible_episodes():
    task = ToyParity()
    task.episodes = lambda rng, n, split="train": ToyParity.episodes(task, np.random.RandomState(), n, split)
    with pytest.raises(PreflightError, match="bit-identique"):
        assert_task_contract(task)


def test_state_ablation_requires_a_control_split():
    task = ToyParity()
    task.demand = DemandDeclaration("parity", (Ablation("state_reset", "state", True, bayes_floor=0.5),
                                               Ablation("nobite", "input", False, apply=task._permute_nothing)))
    with pytest.raises(PreflightError, match="control"):
        assert_task_contract(task)
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_task.py -q`
Expected: `ModuleNotFoundError: No module named 'src.seed_ai.harness_task'`

- [ ] **Step 3: Écrire `src/seed_ai/harness_task.py`**

```python
"""
src/seed_ai/harness_task.py — Contrat `Task` du harnais (ADR-004, spec 2026-09-16 §2.1).

Une Task est un jeu de logique VÉRIFIABLE qui DÉCLARE la capacité qu'elle exige et l'ablation qui la teste
(marqueur de demande porté par la tâche, REF-DEMAND-MARKER). Elle ne connaît ni learner, ni torch, ni monde.
`assert_task_contract` est une garde EN TÊTE : zéro entraînement, refus en quelques millisecondes — elle vérifie
que l'instrument peut rendre LES DEUX issues (question A du pré-vol) avant qu'un seul poids ne bouge.
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional, Protocol

import numpy as np


@dataclass(frozen=True)
class Episode:
    """Un lot de n épisodes de longueur T. `meta` porte les opérandes OBSERVABLES (lus par oracle/ablate),
    jamais par le Learner ; `target` porte la VÉRITÉ (lue par score). Sous ablation, meta reflète ce qui reste
    observable et target ne change pas : c'est ce qui fait tomber l'oracle au plancher de Bayes."""
    obs_seq: tuple            # T tableaux (n, obs_dim) float32
    target: np.ndarray        # (n,) int64 dans [0, K)
    mask_seq: Optional[tuple] # T tableaux (n,) float32, 1.0 au pas noté ; None ssi T == 1
    meta: dict

    @property
    def n(self) -> int:
        return int(np.asarray(self.target).shape[0])

    @property
    def T(self) -> int:
        return len(self.obs_seq)


@dataclass(frozen=True)
class Ablation:
    """`apply(ep, rng) -> Episode` NEUF (distribution conservée, information détruite : barreau `permuted`,
    jamais `zero`). site="state" : appliquée par le Learner (`ablate_state`) avant le pas de réponse ; exige un
    split "control". `bayes_floor` = accuracy attendue de l'oracle SOUS cette ablation (None -> 1/K)."""
    name: str
    site: str                 # "input" | "state"
    must_bite: bool           # True : la capacité EXIGE ce canal ; False : contrôle de SPÉCIFICITÉ
    apply: Optional[Callable] = None
    bayes_floor: Optional[float] = None


@dataclass(frozen=True)
class DemandDeclaration:
    capacity: str
    ablations: tuple
    incapable_ceiling: Optional[tuple] = None     # (valeur, provenance >= 20 car., prouvé: bool) ; JAMAIS 1/K
    key_entropy_bits: Optional[float] = None      # familles LLM, v2


class Task(Protocol):
    name: str
    version: str
    K: int
    obs_dim: int
    T: int
    demand: DemandDeclaration

    def episodes(self, rng: np.random.RandomState, n: int, split: str = "train") -> Episode: ...
    def score(self, actions: np.ndarray, ep: Episode) -> np.ndarray: ...
    def oracle(self, ep: Episode) -> np.ndarray: ...
    def enumerate_states(self) -> Optional[int]: ...
    def regime(self) -> dict: ...


def _fail(msg):
    from tools.experiment_preflight import PreflightError
    raise PreflightError("assert_task_contract : " + msg)


def _check_episode_shape(task, ep, n, label):
    if not isinstance(ep, Episode):
        _fail(f"{label} : episodes() doit rendre un Episode (reçu {type(ep).__name__})")
    if ep.T != int(task.T):
        _fail(f"{label} : T déclaré {task.T}, obs_seq de longueur {ep.T}")
    for t, obs in enumerate(ep.obs_seq):
        obs = np.asarray(obs)
        if obs.shape != (n, int(task.obs_dim)) or obs.dtype != np.float32:
            _fail(f"{label} : obs_seq[{t}] de forme {obs.shape} / {obs.dtype}, attendu ({n}, {task.obs_dim}) float32")
    tgt = np.asarray(ep.target)
    if tgt.shape != (n,) or not np.issubdtype(tgt.dtype, np.integer):
        _fail(f"{label} : target de forme {tgt.shape} / {tgt.dtype}, attendu ({n},) entier")
    if tgt.size and (tgt.min() < 0 or tgt.max() >= int(task.K)):
        _fail(f"{label} : target hors [0, K={task.K})")
    if ep.T == 1 and ep.mask_seq is not None:
        _fail(f"{label} : mask_seq doit être None quand T == 1")
    if ep.T > 1:
        if ep.mask_seq is None or len(ep.mask_seq) != ep.T:
            _fail(f"{label} : mask_seq doit avoir T={ep.T} entrées quand T > 1")
        if not any(float(np.asarray(m).sum()) > 0 for m in ep.mask_seq):
            _fail(f"{label} : aucun pas noté (mask_seq tout à zéro)")


def _episodes_bit_identical(a: Episode, b: Episode) -> bool:
    if a.T != b.T or not np.array_equal(a.target, b.target):
        return False
    return all(np.array_equal(x, y) for x, y in zip(a.obs_seq, b.obs_seq))


def assert_task_contract(task, seed=0, n=64) -> dict:
    """Garde EN TÊTE, zéro entraînement, refus < 50 ms :
    (a) >= 1 ablation must_bite=True et >= 1 must_bite=False ; site="state" -> le split "control" existe ;
    (b) score(oracle) == 1.0 ; oracle décalé ((x+1) % K) -> 0.0 (le vérifieur n'est pas l'oracle, E1) ;
    (c) must_bite=True : score(oracle, apply(ep)) dans [bayes_floor ± 2 se] ; must_bite=False : > 0.9 ;
    (d) deux appels episodes(rng même état) bit-identiques ; apply(ep) ne partage aucune mémoire avec ep ;
    (e) incapable_ceiling : provenance >= 20 caractères, valeur dans ]0, 1], != 1/K ;
    (f) regime() non vide ; score sur n == 0 lève.
    Rend {"bayes_floors": {ablation: float}, "certified": enumerate_states() is not None, "elapsed_ms": float}."""
    t0 = time.perf_counter()
    K = int(task.K)
    if not isinstance(task.regime(), dict) or not task.regime():
        _fail("(f) regime() vide : le régime doit être PUBLIÉ par la tâche (E8 occ. 4)")
    abls = tuple(task.demand.ablations)
    if not any(a.must_bite for a in abls):
        _fail("(a) aucune ablation must_bite=True : rien ne peut mordre")
    if not any(not a.must_bite for a in abls):
        _fail("(a) aucune ablation must_bite=False : aucun contrôle de spécificité, une seule issue possible")
    rng = np.random.RandomState(seed)
    ep = task.episodes(rng, n, "train")
    _check_episode_shape(task, ep, n, "(d) split train")
    ep2 = task.episodes(np.random.RandomState(seed), n, "train")
    if not _episodes_bit_identical(ep, ep2):
        _fail("(d) deux appels episodes() au même état de rng ne sont pas bit-identiques (tirage hors rng ?)")
    if any(a.site == "state" for a in abls):
        ctrl = task.episodes(np.random.RandomState(seed), n, "control")
        _check_episode_shape(task, ctrl, n, "(a) split control")
    # (b) le vérifieur est indépendant de l'oracle
    orc = np.asarray(task.oracle(ep))
    acc = float(np.mean(task.score(orc, ep)))
    if acc != 1.0:
        _fail(f"(b) score(oracle) = {acc:.4f}, attendu 1.0 : le contrôle positif de la DV échoue")
    acc_shift = float(np.mean(task.score((orc + 1) % K, ep)))
    if acc_shift != 0.0:
        _fail(f"(b) oracle décalé noté {acc_shift:.4f}, attendu 0.0 : le vérifieur n'est pas indépendant de l'oracle (E1)")
    try:
        task.score(np.zeros(0, dtype=np.int64), Episode(tuple(o[:0] for o in ep.obs_seq), ep.target[:0], ep.mask_seq, {}))
    except Exception:
        pass
    else:
        _fail("(f) score() sur un lot VIDE doit lever (porte 14 : une constante sur collection vide fabrique un résultat)")
    # (c) chaque ablation d'entrée rend les DEUX issues
    floors = {}
    for a in abls:
        if a.site != "input":
            floors[a.name] = float(a.bayes_floor) if a.bayes_floor is not None else 1.0 / K
            continue
        if a.apply is None:
            _fail(f"(c) ablation d'entrée {a.name!r} sans apply")
        ep_a = a.apply(ep, np.random.RandomState(seed + 1))
        _check_episode_shape(task, ep_a, n, f"(c) ablation {a.name!r}")
        for o, oa in zip(ep.obs_seq, ep_a.obs_seq):
            if np.shares_memory(o, oa):
                _fail(f"(d) ablation {a.name!r} rend une VUE de l'épisode intact (np.shares_memory) : écrire dedans muterait la source")
        acc_a = float(np.mean(task.score(np.asarray(task.oracle(ep_a)), ep_a)))
        if a.must_bite:
            floor = float(a.bayes_floor) if a.bayes_floor is not None else 1.0 / K
            se = float(np.sqrt(max(floor * (1.0 - floor), 1e-12) / n))
            if abs(acc_a - floor) > 2.0 * se:
                _fail(f"(c) ablation must_bite {a.name!r} : l'oracle note {acc_a:.3f} sous ablation, attendu {floor:.3f} ± {2*se:.3f} — elle ne MORD pas")
            floors[a.name] = floor
        elif acc_a <= 0.9:
            _fail(f"(c) ablation de spécificité {a.name!r} (must_bite=False) fait tomber l'oracle à {acc_a:.3f} : elle mord, ce n'est pas un contrôle")
    # (e) plafond de représentation déclaré
    ceil = task.demand.incapable_ceiling
    if ceil is not None:
        try:
            value, prov, _proven = ceil
        except (TypeError, ValueError):
            _fail("(e) incapable_ceiling doit être (valeur, provenance, prouvé)")
        if not isinstance(prov, str) or len(prov.strip()) < 20:
            _fail("(e) provenance du plafond de l'incapable non déclarée (>= 20 caractères)")
        value = float(value)
        if not (0.0 < value <= 1.0):
            _fail(f"(e) plafond {value} hors ]0, 1]")
        if abs(value - 1.0 / K) < 1e-9:
            _fail("(e) le plafond déclaré vaut 1/K : c'est le niveau de CHANCE, pas le plafond de l'INCAPABLE (P2.15)")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {"bayes_floors": floors, "certified": task.enumerate_states() is not None, "elapsed_ms": elapsed_ms}
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_task.py -q`
Expected: `9 passed`

- [ ] **Step 5: Vérifier les portes sur le fichier neuf**

Run: `PYTHONIOENCODING=utf-8 python tools/check_bar_separation.py --only src/seed_ai/harness_task.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only src/seed_ai/harness_task.py && PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only src/seed_ai/harness_task.py`
Expected: trois `OK`. (La porte 2 bloquera jusqu'à la tâche 8 : c'est attendu ; la déclaration `CALIBRATED` de `assert_task_contract` y est écrite — ne pas committer avant.)

- [ ] **Step 6: Préparer le commit (exécuté à la tâche 8 avec les déclarations)**

Écrire `scratchpad/commit_msg_t1.txt` : `feat(harness): contrat Task + assert_task_contract (garde en tete, 9 cas a reponse connue)`. Fichiers : `src/seed_ai/harness_task.py tests/sandbox/test_harness_task.py`.

---

### Task 2: Contrat `Learner` et garde `assert_learner_contract`

**Files:**
- Create: `src/seed_ai/harness_learner.py`
- Test: `tests/sandbox/test_harness_learner.py`

**Interfaces:**
- Consumes: `Episode`, `Task` (tâche 1) ; `tools.experiment_preflight.assert_no_aliasing`, `PreflightError`.
- Produces: `Piece(name, artificial_form, biological_analogue, analogue_solidity, bio_lesion_prediction, capacity_served, without: dict, dose_matched: bool, matched_sham: dict|None, in_repo_today: str, evo_discoverable="unknown")` ; `Dose(calls, updates, dparam_abs_sum, episodes_seen, unit)` ; `LearnerInstance` : `init_state()`, `act(obs_t, state) -> (logits (n,K) COPIÉS, state)`, `learn(ep, actions, hits) -> Dose`, `ablate_state(state, name)`, `state_dict()`, `dose()`, `close()` ; `Learner` : `name, family, pieces, entry_task, max_K, supported_state_ablations`, `sweep() -> list[dict]`, `build(seed, n, obs_dim, K, hyper, *, without={}, reference=False) -> LearnerInstance` ; `assert_learner_contract(learner, task, seed=0) -> dict` (clés `"n_pieces"`, `"reference_dparam"`, `"elapsed_ms"`) ; `run_episode(inst, ep, task, ablate=None) -> (actions, hits)` (boucle d'un épisode, partagée par la garde et le runner).

- [ ] **Step 1: Écrire le test qui échoue (un Learner jouet « compteur » dans le test)**

```python
# tests/sandbox/test_harness_learner.py
"""Contrat Learner (spec §2.1) : L0-L7. Le learner jouet est une table de comptes en numpy pur ; chaque cas
casse UNE clause et vérifie que la garde la nomme."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_learner import Dose, Piece, assert_learner_contract, run_episode  # noqa: E402
from src.seed_ai.harness_task import Ablation, DemandDeclaration, Episode  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402
from tests.sandbox.test_harness_task import ToyParity  # noqa: E402


class _CounterInstance:
    def __init__(self, K, obs_dim, lr, learning, without, aliased=False, dead=False):
        self.K, self.lr, self.learning, self.without = K, float(lr), learning, dict(without)
        self.table = np.zeros((obs_dim, K), dtype=np.float64)
        self.bias = np.zeros(K, dtype=np.float64) + (0.0 if without.get("bias") else 0.01)
        self._dose = Dose(unit="count_updates")
        self.aliased, self.dead = aliased, dead
        self._state_buf = np.zeros((1, K), dtype=np.float32)

    def init_state(self):
        return None

    def act(self, obs_t, state):
        logits = obs_t.astype(np.float64) @ self.table + self.bias
        if self.without.get("table"):
            logits = np.zeros_like(logits) + self.bias
        out = logits.astype(np.float32)
        if self.aliased:
            self._state_buf = out
            return out, self._state_buf      # la sortie EST l'état : L5 doit lever
        return np.array(out, copy=True), state

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        self._dose.episodes_seen += ep.n
        if not self.learning or self.dead:
            self._dose.dparam_abs_sum = (self._dose.dparam_abs_sum or 0.0)
            return self._dose
        before = self.table.copy()
        rows = ep.obs_seq[-1] > 0
        for i in range(ep.n):
            self.table[rows[i], ep.target[i]] += self.lr
        d = float(np.abs(self.table - before).sum())
        self._dose.updates += int(d > 0)
        self._dose.dparam_abs_sum = (self._dose.dparam_abs_sum or 0.0) + d
        return self._dose

    def ablate_state(self, state, name):
        return state

    def state_dict(self):
        return {"table": self.table.copy()}

    def dose(self):
        return self._dose

    def close(self):
        pass


class CounterLearner:
    name, family, max_K = "counter", "toy", 64
    entry_task = "toy_parity"
    supported_state_ablations = frozenset()

    def __init__(self, vacuous_piece=False, aliased=False, dead=False, reference_learns=False, one_lr=False):
        self.pieces = (Piece("table", "test", "aucun", "aucune", None, "parity", {"table": True}, True, None, "absent"),
                       Piece("bias", "test", "aucun", "aucune", None, "parity", {"bias": True}, True, None, "absent"))
        if vacuous_piece:
            self.pieces += (Piece("decoy", "test", "aucun", "aucune", None, "parity", {"decoy": True}, True, None, "absent"),)
        self.aliased, self.dead, self.reference_learns, self.one_lr = aliased, dead, reference_learns, one_lr

    def sweep(self):
        return [{"lr": 1.0}] if self.one_lr else [{"lr": 1.0}, {"lr": 0.5}]

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        learning = (not reference) or self.reference_learns
        return _CounterInstance(K, obs_dim, hyper["lr"], learning, without or {}, aliased=self.aliased, dead=self.dead)


def test_counter_learner_passes_L0_to_L7():
    out = assert_learner_contract(CounterLearner(), ToyParity(), seed=0)
    assert out["n_pieces"] == 2 and out["reference_dparam"] == 0.0


def test_L0_refuses_K_above_max_K():
    task = ToyParity()
    task.K = 65
    with pytest.raises(PreflightError, match="max_K"):
        assert_learner_contract(CounterLearner(), task)


def test_L2_refuses_a_reference_that_learns():
    with pytest.raises(PreflightError, match="REFERENCE_LEARNS"):
        assert_learner_contract(CounterLearner(reference_learns=True), ToyParity())


def test_L3_refuses_a_dead_learner():
    with pytest.raises(PreflightError, match="DEAD_LEARNER"):
        assert_learner_contract(CounterLearner(dead=True), ToyParity())


def test_L4_refuses_a_vacuous_piece():
    with pytest.raises(PreflightError, match="VACUOUS_PIECE.*decoy"):
        assert_learner_contract(CounterLearner(vacuous_piece=True), ToyParity())


def test_L5_refuses_logits_that_alias_the_state():
    with pytest.raises(PreflightError, match="shares_memory|aliasing"):
        assert_learner_contract(CounterLearner(aliased=True), ToyParity())


def test_L7_refuses_a_single_sweep_point():
    with pytest.raises(PreflightError, match="sweep"):
        assert_learner_contract(CounterLearner(one_lr=True), ToyParity())


def test_run_episode_scores_with_the_task_verifier():
    task = ToyParity()
    inst = CounterLearner().build(0, 8, task.obs_dim, task.K, {"lr": 1.0})
    ep = task.episodes(np.random.RandomState(0), 8)
    actions, hits = run_episode(inst, ep, task)
    assert actions.shape == (8,) and hits.shape == (8,) and set(np.unique(hits)) <= {0.0, 1.0}
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_learner.py -q`
Expected: `ModuleNotFoundError: No module named 'src.seed_ai.harness_learner'`

- [ ] **Step 3: Écrire `src/seed_ai/harness_learner.py`**

```python
"""
src/seed_ai/harness_learner.py — Contrat `Learner` du harnais (ADR-004, spec §2.1).

Un Learner est une ARCHITECTURE qui déclare ses PIÈCES, chacune avec sa variante « sans » : c'est le marqueur de
NÉCESSITÉ porté par l'architecture. `build(reference=True)` rend le bras de référence de la condition (ii) :
même init, mêmes tirages, même boucle, apprentissage COUPÉ. La dose est comptée EN LIGNE dans `learn` (le patch
de classe `count_learning_events` ne voit pas `imitate_episode_bptt`). `assert_learner_contract` refuse en tête.
"""
import time
from dataclasses import dataclass, field
from typing import Optional, Protocol

import numpy as np

from src.seed_ai.harness_task import Episode


@dataclass(frozen=True)
class Piece:
    name: str
    artificial_form: str              # fichier:ligne
    biological_analogue: str
    analogue_solidity: str            # "solide" | "moyenne" | "faible" | "aucune"
    bio_lesion_prediction: Optional[str]
    capacity_served: str
    without: dict                     # kwargs de build() pour la variante « sans » ; DOIT changer >= 1 logit
    dose_matched: bool
    matched_sham: Optional[dict]      # variante à MÊME nombre de paramètres ; None -> PARAMS_NON_APPARIES
    in_repo_today: str
    evo_discoverable: str = "unknown"


@dataclass
class Dose:
    calls: int = 0
    updates: int = 0                  # mises à jour qui ont RÉELLEMENT changé un paramètre
    dparam_abs_sum: Optional[float] = None
    episodes_seen: int = 0
    unit: str = "gradient_updates"

    def as_dict(self) -> dict:
        return {"calls": self.calls, "updates": self.updates, "dparam_abs_sum": self.dparam_abs_sum,
                "episodes_seen": self.episodes_seen, "unit": self.unit}


class LearnerInstance(Protocol):
    def init_state(self): ...
    def act(self, obs_t: np.ndarray, state) -> tuple: ...
    def learn(self, ep: Episode, actions: np.ndarray, hits: np.ndarray) -> Dose: ...
    def ablate_state(self, state, name: str): ...
    def state_dict(self) -> dict: ...
    def dose(self) -> Dose: ...
    def close(self) -> None: ...


class Learner(Protocol):
    name: str
    family: str
    pieces: tuple
    entry_task: str
    max_K: int
    supported_state_ablations: frozenset

    def sweep(self) -> list: ...
    def build(self, seed: int, n: int, obs_dim: int, K: int, hyper: dict, *,
              without: dict = None, reference: bool = False) -> LearnerInstance: ...


def run_episode(inst, ep: Episode, task, ablate: Optional[str] = None):
    """Déroule UN lot d'épisodes en boucle ouverte : act à chaque pas, décision = argmax des logits du DERNIER
    pas noté. `ablate` (nom d'une Ablation site="state") est appliqué à l'état AVANT le pas de réponse.
    Rend (actions (n,) int64, hits (n,) float32) via task.score — le vérifieur, jamais l'oracle."""
    state = inst.init_state()
    last = ep.T - 1
    logits = None
    for t, obs_t in enumerate(ep.obs_seq):
        if ablate is not None and t == last:
            state = inst.ablate_state(state, ablate)
        logits, state = inst.act(np.asarray(obs_t, dtype=np.float32), state)
    actions = np.asarray(logits)[:, :int(task.K)].argmax(axis=1).astype(np.int64)
    hits = np.asarray(task.score(actions, ep), dtype=np.float32)
    return actions, hits


def _fail(msg):
    from tools.experiment_preflight import PreflightError
    raise PreflightError("assert_learner_contract : " + msg)


def _logits_of(inst, ep):
    state = inst.init_state()
    out = None
    for obs_t in ep.obs_seq:
        out, state = inst.act(np.asarray(obs_t, dtype=np.float32), state)
    return np.asarray(out), state


def assert_learner_contract(learner, task, seed=0, n_probe=8, n_learn=5) -> dict:
    """Garde EN TÊTE, une population de n_probe, n_learn épisodes :
    (L0) task.K <= learner.max_K ; toute Ablation site="state" de la tâche ∈ supported_state_ablations ;
    (L1) deux build(seed) -> logits bit-identiques ; build(without={}) bit-identique (no-op EXACT) ;
    (L2) REFERENCE_LEARNS : build(reference=True).learn x n_learn -> dparam_abs_sum == 0 et updates == 0 ;
    (L3) DEAD_LEARNER : build().learn x n_learn -> dparam_abs_sum > 0 (le cas « curiosité morte », P4.8) ;
    (L4) VACUOUS_PIECE : pour chaque Piece, build(without=p.without) diffère de l'intact sur >= 1 logit ;
    (L5) assert_no_aliasing(logits, state) ; (L6) entry_task non vide ; (L7) len(sweep()) >= 2 pas distincts.
    Rend {"n_pieces", "reference_dparam", "elapsed_ms"}."""
    from tools.experiment_preflight import assert_no_aliasing, PreflightError
    t0 = time.perf_counter()
    K, obs_dim = int(task.K), int(task.obs_dim)
    if K > int(learner.max_K):
        _fail(f"(L0) task.K={K} > learner.max_K={learner.max_K}")
    for a in task.demand.ablations:
        if a.site == "state" and a.name not in learner.supported_state_ablations:
            _fail(f"(L0) ablation d'état {a.name!r} non supportée par {learner.name} ({sorted(learner.supported_state_ablations)})")
    if not isinstance(getattr(learner, "entry_task", ""), str) or not learner.entry_task.strip():
        _fail("(L6) entry_task vide : la famille n'a pas de billet d'entrée (règle E2)")
    sweep = list(learner.sweep())
    if len(sweep) < 2 or len({tuple(sorted(h.items())) for h in sweep}) < 2:
        _fail(f"(L7) sweep() doit déclarer >= 2 réglages DISTINCTS (reçu {sweep})")
    hyper = sweep[0]
    ep = task.episodes(np.random.RandomState(seed), n_probe, "train")
    # (L1) déterminisme et no-op exact
    inst_a = learner.build(seed, n_probe, obs_dim, K, hyper)
    la, state_a = _logits_of(inst_a, ep)
    inst_b = learner.build(seed, n_probe, obs_dim, K, hyper)
    lb, _ = _logits_of(inst_b, ep)
    inst_b.close()
    if la.shape != (n_probe, K) and la.shape[:1] != (n_probe,):
        inst_a.close()
        _fail(f"(L1) act rend des logits de forme {la.shape}, attendu ({n_probe}, >= {K})")
    if not np.array_equal(la, lb):
        inst_a.close()
        _fail("(L1) deux build(seed) identiques ne rendent pas les mêmes logits : le learner tire hors seed")
    inst_c = learner.build(seed, n_probe, obs_dim, K, hyper, without={})
    lc, _ = _logits_of(inst_c, ep)
    inst_c.close()
    if not np.array_equal(la, lc):
        inst_a.close()
        _fail("(L1) build(without={}) n'est pas bit-identique à l'intact : le no-op n'est pas EXACT")
    # (L5) aucune vue de l'état dans la sortie
    try:
        assert_no_aliasing(la, state_a, label="logits de act")
        if state_a is not None and hasattr(state_a, "shape"):
            assert_no_aliasing(la, np.asarray(state_a), label="logits de act")
    except PreflightError as e:
        inst_a.close()
        _fail(f"(L5) {e}")
    # (L3) l'intact apprend ; (L2) la référence n'apprend pas
    dose_a = None
    for _ in range(n_learn):
        actions, hits = run_episode(inst_a, ep, task)
        dose_a = inst_a.learn(ep, actions, hits)
    inst_a.close()
    if dose_a is None or not isinstance(dose_a, Dose) or dose_a.calls != n_learn:
        _fail(f"(L3) learn doit rendre la Dose cumulée (calls == {n_learn}), reçu {dose_a}")
    if dose_a.dparam_abs_sum is not None and not (dose_a.dparam_abs_sum > 0.0):
        _fail(f"(L3) DEAD_LEARNER : {n_learn} appels de learn et dparam_abs_sum == {dose_a.dparam_abs_sum} — l'apprenant est INERTE (cas « curiosité morte », P4.8)")
    inst_r = learner.build(seed, n_probe, obs_dim, K, hyper, reference=True)
    dose_r = None
    for _ in range(n_learn):
        actions, hits = run_episode(inst_r, ep, task)
        dose_r = inst_r.learn(ep, actions, hits)
    inst_r.close()
    ref_d = 0.0 if dose_r.dparam_abs_sum is None else float(dose_r.dparam_abs_sum)
    if ref_d != 0.0 or dose_r.updates != 0:
        _fail(f"(L2) REFERENCE_LEARNS : build(reference=True) a bougé (dparam_abs_sum={ref_d}, updates={dose_r.updates}) — la barre de (ii) est contaminée")
    if dose_r.calls != n_learn:
        _fail(f"(L2) la référence doit consommer les MÊMES appels que l'intact (calls {dose_r.calls} != {n_learn})")
    # (L4) chaque pièce a une variante « sans » qui change quelque chose
    for p in learner.pieces:
        inst_w = learner.build(seed, n_probe, obs_dim, K, hyper, without=dict(p.without))
        lw, _ = _logits_of(inst_w, ep)
        inst_w.close()
        if np.array_equal(la, lw):
            _fail(f"(L4) VACUOUS_PIECE : la variante sans {p.name!r} ({p.without}) rend des logits bit-identiques à l'intact — la « pièce » n'existe pas dans ce learner")
    return {"n_pieces": len(learner.pieces), "reference_dparam": ref_d,
            "elapsed_ms": (time.perf_counter() - t0) * 1000.0}
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_learner.py -q`
Expected: `8 passed`

- [ ] **Step 5: Portes sur le fichier neuf**

Run: `PYTHONIOENCODING=utf-8 python tools/check_bar_separation.py --only src/seed_ai/harness_learner.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only src/seed_ai/harness_learner.py`
Expected: deux `OK`. Note : le stub `def learn(...)` du Protocol est capté par la porte 2 (motif indenté `learn\w*`) — déclaration `NOT_AN_INSTRUMENT` qualifiée à la tâche 8.

- [ ] **Step 6: Préparer le commit**

`scratchpad/commit_msg_t2.txt` : `feat(harness): contrat Learner + assert_learner_contract (L0-L7, 8 cas) + run_episode`. Fichiers : `src/seed_ai/harness_learner.py tests/sandbox/test_harness_learner.py`.

---

### Task 3: `CompositionTask` — port sans copie de `_make_seq` / `_slot`

**Files:**
- Create: `tools/harness/tasks/composition.py`
- Test: `tests/sandbox/test_harness_composition.py`

**Interfaces:**
- Consumes: `tools.bilinear_composition_probe._make_seq(key, q, task, K, I, n, same_tick)`, `_slot(idx, K, offset, I, n)` (inchangés : ils restent la réponse connue) ; `Episode`, `Ablation`, `DemandDeclaration`, `assert_task_contract` ; `tools.plain_substrate_ceiling.PLAIN_COMPOSITION_CEILING`, `PLAIN_COMPOSITION_PROVENANCE`.
- Produces: `CompositionTask(K=6, same_tick=True, kind="composition", obs_dim=59, name=None)` ; `episodes(rng, n, split)` consomme `rng.randint(0, K, n)` pour `key` PUIS `q` (ordre de `_train_eval_one:133-134`) ; `meta = {"key", "q", "split"}` ; `split="control"` (2-pas seulement) = key RE-PRÉSENTÉE au pas de réponse ; ablations `permute_key`, `permute_query` (must_bite, `bayes_floor=1/K`), `inject_distractor_slot` (must_bite=False : un one-hot ALEATOIRE, tire du rng d'ablation, ecrit dans le slot [2K:3K) de la copie ablatee — perturbation REELLE de l'observation, information nulle pour la cible ; les episodes INTACTS restent bit-identiques a `_make_seq`) et, en 2-pas, `state_reset` (site="state", must_bite) ; `regime()` publie `task, K, T, same_tick, kind, obs_dim, slots`.

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/sandbox/test_harness_composition.py
"""Port de la tâche (q+key)%K : les épisodes sont BIT-IDENTIQUES à _make_seq au même rng (c'est ce qui rend la
cellule A rejouable), le contrat passe, et chaque ablation rend l'issue attendue sur l'oracle."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_task import assert_task_contract  # noqa: E402
from tools.bilinear_composition_probe import _make_seq  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402


@pytest.mark.parametrize("same_tick,kind", [(True, "composition"), (False, "composition"), (True, "recall")])
def test_episodes_are_bit_identical_to_make_seq(same_tick, kind):
    task = CompositionTask(K=6, same_tick=same_tick, kind=kind)
    rng = np.random.RandomState(1)
    ep = task.episodes(rng, 16)
    ref = np.random.RandomState(1)
    key = ref.randint(0, 6, size=16)
    q = ref.randint(0, 6, size=16)
    seq, mask = _make_seq(key, q, kind, 6, 59, 16, same_tick)
    assert all(np.array_equal(a, b) for a, b in zip(ep.obs_seq, seq))
    assert (mask is None and ep.mask_seq is None) or all(np.array_equal(a, b) for a, b in zip(ep.mask_seq, mask))
    tgt = (q + key) % 6 if kind == "composition" else key
    assert np.array_equal(ep.target, tgt)
    assert rng.randint(0, 6) == ref.randint(0, 6)     # même position de rng après l'appel


@pytest.mark.parametrize("same_tick", [True, False])
def test_contract_passes_and_names_bayes_floors(same_tick):
    out = assert_task_contract(CompositionTask(K=6, same_tick=same_tick), seed=0, n=256)
    assert out["certified"] is True
    assert out["bayes_floors"]["permute_key"] == pytest.approx(1 / 6)
    assert out["bayes_floors"]["permute_query"] == pytest.approx(1 / 6)
    if not same_tick:
        assert out["bayes_floors"]["state_reset"] == pytest.approx(1 / 6)


def test_recall_declares_query_as_non_biting():
    task = CompositionTask(K=6, same_tick=True, kind="recall")
    names = {a.name: a.must_bite for a in task.demand.ablations}
    assert names["permute_key"] is True and names["permute_query"] is False
    assert_task_contract(task, seed=0, n=256)


def test_control_split_re_presents_key_at_the_answer_step():
    task = CompositionTask(K=6, same_tick=False)
    ep = task.episodes(np.random.RandomState(3), 8, split="control")
    key, q = ep.meta["key"], ep.meta["q"]
    assert ep.T == 2
    assert np.array_equal(ep.obs_seq[1][np.arange(8), key], np.ones(8, dtype=np.float32))
    assert np.array_equal(ep.obs_seq[1][np.arange(8), 6 + q], np.ones(8, dtype=np.float32))
    assert np.array_equal(ep.target, (q + key) % 6)


def test_regime_is_published_and_ceiling_is_the_frozen_minorant():
    task = CompositionTask(K=6, same_tick=True)
    r = task.regime()
    assert r["K"] == 6 and r["T"] == 1 and r["same_tick"] is True and r["kind"] == "composition"
    value, prov, proven = task.demand.incapable_ceiling
    assert value == pytest.approx(34 / 36) and proven is False and len(prov) >= 20
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_composition.py -q`
Expected: `ModuleNotFoundError: No module named 'tools.harness'`

- [ ] **Step 3: Écrire `tools/harness/tasks/composition.py`**

```python
"""
tools/harness/tasks/composition.py — CompositionTask : (q + key) % K, portée SANS COPIE depuis
tools/bilinear_composition_probe.py (_make_seq / _slot restent la réponse connue de la cellule A).

Slots : key dans [0:K), q dans [K:2K), distracteur dans [2K:3K) — VIDE dans l'episode intact (bit-identite avec
_make_seq), REMPLI d'un one-hot aleatoire par l'ablation `inject_distractor_slot` (REVIEW-01 R1 : un controle qui
permute des zeros ne peut pas echouer, classe E1 ; celui-ci peut : un learner sensible aux noeuds 2K..3K y perd). same_tick=True -> T = 1 ; sinon T = 2
(key au pas 0, q au pas 1, masque [0, 1]). kind="recall" : cible = key. split="control" (2-pas) : key
RE-PRÉSENTÉE au pas de réponse -> une politique qui lit l'entrée n'a pas besoin de l'état porté : c'est le bras
CONTROL de alias_guard_verdict pour `state_reset`. Sous ablation la VÉRITÉ (target) ne change pas ; `meta` porte
ce qui reste OBSERVABLE, c'est ce que l'oracle lit — et ce qui le fait tomber au plancher de Bayes.
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness_task import Ablation, DemandDeclaration, Episode  # noqa: E402
from tools.bilinear_composition_probe import _make_seq, _slot  # noqa: E402
from tools.plain_substrate_ceiling import PLAIN_COMPOSITION_CEILING, PLAIN_COMPOSITION_PROVENANCE  # noqa: E402


class CompositionTask:
    version = "1"

    def __init__(self, K=6, same_tick=True, kind="composition", obs_dim=59, name=None):
        if kind not in ("composition", "recall"):
            raise ValueError(f"kind inconnu : {kind!r}")
        if 3 * K > obs_dim:
            raise ValueError(f"3K={3*K} slots ne tiennent pas dans obs_dim={obs_dim}")
        self.K, self.same_tick, self.kind, self.obs_dim = int(K), bool(same_tick), kind, int(obs_dim)
        self.T = 1 if same_tick else 2
        self.name = name or f"{kind}_{'same_tick' if same_tick else 'two_step'}_K{K}"
        floor = 1.0 / self.K
        abls = [Ablation("permute_key", "input", True, apply=self._permute_key, bayes_floor=floor),
                Ablation("permute_query", "input", kind == "composition", apply=self._permute_query,
                         bayes_floor=(floor if kind == "composition" else None)),
                Ablation("inject_distractor_slot", "input", False, apply=self._inject_distractor)]
        if not same_tick:
            abls.append(Ablation("state_reset", "state", True, bayes_floor=floor))
        ceiling = None
        if kind == "composition" and same_tick:
            ceiling = (float(PLAIN_COMPOSITION_CEILING), PLAIN_COMPOSITION_PROVENANCE + " MINORANT, jamais PROUVE.", False)
        self.demand = DemandDeclaration(kind, tuple(abls), incapable_ceiling=ceiling)

    def _build(self, key, q, split, target=None):
        n = key.shape[0]
        seq, mask = _make_seq(key, q, self.kind, self.K, self.obs_dim, n, self.same_tick)
        if split == "control":
            if self.same_tick:
                raise ValueError("split control : seulement en 2-pas")
            seq = [seq[0], seq[1] + _slot(key, self.K, 0, self.obs_dim, n)]   # key re-présentée au pas de réponse
        if target is None:
            target = ((q + key) % self.K) if self.kind == "composition" else key
        return Episode(tuple(np.ascontiguousarray(x, dtype=np.float32) for x in seq),
                       np.asarray(target).astype(np.int64), (None if mask is None else tuple(mask)),
                       {"key": np.asarray(key), "q": np.asarray(q), "split": split})

    def episodes(self, rng, n, split="train"):
        key = rng.randint(0, self.K, size=n)       # ORDRE de _train_eval_one:133-134 : key PUIS q
        q = rng.randint(0, self.K, size=n)
        return self._build(key, q, split)

    def _permute_key(self, ep, rng):
        return self._build(ep.meta["key"][rng.permutation(ep.n)], ep.meta["q"], ep.meta["split"], target=ep.target)

    def _permute_query(self, ep, rng):
        return self._build(ep.meta["key"], ep.meta["q"][rng.permutation(ep.n)], ep.meta["split"], target=ep.target)

    def _inject_distractor(self, ep, rng):
        """Controle de SPECIFICITE : ecrit un one-hot aleatoire dans le slot distracteur [2K:3K) du DERNIER pas de
        la copie ablatee. L'observation CHANGE (le contrat (c) l'exige : un controle qui ne change rien ne peut pas
        echouer, E1), l'information utile a la cible ne change pas (oracle 1,0), et un learner dont le readout est
        sensible a ces noeuds d'entree PEUT y perdre — c'est ce qui rend l'issue DECOY informative."""
        seq = [np.array(x, copy=True) for x in ep.obs_seq]
        d = rng.randint(0, self.K, size=ep.n)
        seq[-1][np.arange(ep.n), 2 * self.K + d] = 1.0
        return Episode(tuple(seq), ep.target.copy(), ep.mask_seq, dict(ep.meta, distractor=d))

    def score(self, actions, ep):
        if ep.n == 0:
            raise ValueError("CompositionTask.score : lot vide (porte 14)")
        return (np.asarray(actions).reshape(-1) == np.asarray(ep.target)).astype(np.float32)

    def oracle(self, ep):
        key, q = ep.meta["key"], ep.meta["q"]
        return ((q + key) % self.K) if self.kind == "composition" else np.asarray(key)

    def enumerate_states(self):
        return self.K * self.K

    def regime(self):
        return {"task": self.name, "K": self.K, "T": self.T, "same_tick": self.same_tick, "kind": self.kind,
                "obs_dim": self.obs_dim, "slots": {"key": [0, self.K], "q": [self.K, 2 * self.K],
                                                    "distractor": [2 * self.K, 3 * self.K]}}
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_composition.py -q`
Expected: `8 passed` (le contrat à n=256 prend < 1 s : `_make_seq` est numpy pur).

- [ ] **Step 4bis: Amender `assert_task_contract` (REVIEW-01 R1/R2) et ses tests**

Dans `src/seed_ai/harness_task.py`, boucle (c) : pour TOUTE ablation d'entree, exiger que l'observation ablatee
DIFFERE de l'intacte sur au moins un pas (`any(not np.array_equal(o, oa) for o, oa in zip(ep.obs_seq, ep_a.obs_seq))`,
sinon `_fail("(c) ablation {name!r} ne change PAS l'observation : un controle qui ne peut pas echouer ne prouve rien (E1)")`)
et que `np.array_equal(ep_a.target, ep.target)` (la VERITE ne change pas sous ablation ; sinon `_fail("(d) ...")`).
Ajouter dans `tests/sandbox/test_harness_task.py` : `test_contract_refuses_a_control_that_does_not_change_the_observation`
(ToyParity avec `permute_nothing` remplace par une ablation qui rend une copie identique -> PreflightError match "E1")
et `test_contract_refuses_an_ablation_that_changes_the_target` (apply rend target+1 -> PreflightError match "(d)").
Mettre a jour l'entree CALIBRATED de `assert_task_contract` (+ "no-change-control:raises", "target-changed:raises").
Consequence : le `permute_nothing` de ToyParity (tests de la tache 1) devient une VRAIE perturbation — porter
`obs_dim` de ToyParity a 5 et faire ecrire 1.0 dans la 5e colonne (inutilisee) par l'ablation, renommee `inject_noise` ;
les tests des taches 1 et 2 qui la nomment suivent (chercher `permute_nothing`).

- [ ] **Step 5: Portes**

Run: `PYTHONIOENCODING=utf-8 python tools/check_bar_separation.py --only tools/harness/tasks/composition.py && PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/harness/tasks/composition.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/harness/tasks/composition.py`
Expected: trois `OK` (`1.0 / self.K` seul, sans constante ajoutée : hors périmètre de la porte 9).

- [ ] **Step 6: Préparer le commit**

`scratchpad/commit_msg_t3.txt` : `feat(harness): CompositionTask -- port sans copie de _make_seq, bit-identique au rng, 4 ablations, split control`. Fichiers : `tools/harness/tasks/composition.py tests/sandbox/test_harness_composition.py`.

---

### Task 4: `TabularLearner` — vérité-terrain sans torch

**Files:**
- Create: `tools/harness/learners/tabular.py`
- Test: `tests/sandbox/test_harness_tabular.py`

**Interfaces:**
- Consumes: `Piece`, `Dose`, `assert_learner_contract`, `run_episode` (tâche 2) ; `CompositionTask` (tâche 3).
- Produces: `TabularLearner(honest=False)` avec `pieces = (table, decoy)` — `decoy` est VOLONTAIREMENT vacue (jamais lue) : la garde L4 doit la REFUSER ; `TabularLearner(honest=True)` n'a que `table` et passe le contrat. `build(seed, n, obs_dim, K, hyper={"lr": ...}, without, reference)` ; l'instance : table de comptes indexée par la CLÉ de l'observation cumulée (tuple des colonnes actives vues à chaque pas) → `act` = comptes de la clé (zéros si inconnue), `learn` lit `ep.target` (crédit supervisé), `ablate_state(state, "state_reset")` vide l'historique, `close()` no-op.

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/sandbox/test_harness_tabular.py
"""Learner de vérité-terrain : une table de comptes apprend (q+key)%K par construction (T=1 : 36 clés),
la pièce `table` est nécessaire par construction, la pièce `decoy` est REFUSÉE par L4 (jamais « dispensable »)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_learner import assert_learner_contract, run_episode  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402
from tools.harness.learners.tabular import TabularLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402


def _train(inst, task, seed, episodes, n=16):
    rng = np.random.RandomState(seed + 1)
    for _ in range(episodes):
        ep = task.episodes(rng, n)
        actions, hits = run_episode(inst, ep, task)
        inst.learn(ep, actions, hits)
    return rng


def _accuracy(inst, task, rng, batches=40, n=16, ablate=None):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n)
        hits.append(run_episode(inst, ep, task, ablate=ablate)[1])
    return float(np.mean(np.concatenate(hits)))


def test_honest_tabular_passes_the_contract_on_both_regimes():
    for same_tick in (True, False):
        assert_learner_contract(TabularLearner(honest=True), CompositionTask(K=6, same_tick=same_tick), seed=0)


def test_decoy_piece_is_refused_by_L4_not_judged_dispensable():
    with pytest.raises(PreflightError, match="VACUOUS_PIECE.*decoy"):
        assert_learner_contract(TabularLearner(), CompositionTask(K=6), seed=0)


def test_table_learns_composition_and_reference_stays_at_chance():
    task = CompositionTask(K=6, same_tick=True)
    lrn = TabularLearner(honest=True)
    inst = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0})
    rng = _train(inst, task, 0, 300)
    assert _accuracy(inst, task, rng) > 0.95
    assert inst.dose().updates == 300 and inst.dose().calls == 300
    ref = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0}, reference=True)
    rng_r = _train(ref, task, 0, 300)
    assert ref.dose().updates == 0 and ref.dose().dparam_abs_sum == 0.0
    assert abs(_accuracy(ref, task, rng_r) - 1 / 6) < 0.1


def test_without_table_falls_to_chance_and_state_reset_kills_two_step():
    task = CompositionTask(K=6, same_tick=False)
    lrn = TabularLearner(honest=True)
    inst = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0})
    rng = _train(inst, task, 0, 600)
    state = rng.get_state()
    acc = _accuracy(inst, task, rng)
    rng.set_state(state)
    acc_reset = _accuracy(inst, task, rng, ablate="state_reset")
    assert acc > 0.95 and abs(acc_reset - 1 / 6) < 0.1
    off = lrn.build(0, 16, task.obs_dim, task.K, {"lr": 1.0}, without={"table": True})
    rng_o = _train(off, task, 0, 600)
    assert abs(_accuracy(off, task, rng_o) - 1 / 6) < 0.1
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_tabular.py -q`
Expected: `ModuleNotFoundError: No module named 'tools.harness.learners'`

- [ ] **Step 3: Écrire `tools/harness/learners/tabular.py`**

```python
"""
tools/harness/learners/tabular.py — Learner de VÉRITÉ-TERRAIN : une table de comptes sur la clé de l'observation
cumulée. Il calibre le runner et la lecture (cellule tabulaire, secondes, zéro torch) : `table` est nécessaire
par construction (sans elle, logits constants -> chance), `decoy` est un paramètre JAMAIS lu que L4 doit REFUSER.
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness_learner import Dose, Piece  # noqa: E402


class _TabularInstance:
    def __init__(self, K, lr, learning, without):
        self.K, self.lr, self.learning = int(K), float(lr), bool(learning)
        self.no_table = bool(without.get("table", False))
        self.table = {}                                  # clé (tuple) -> np.ndarray (K,) comptes
        self._dose = Dose(unit="count_updates")
        self.decoy = 0.0 if without.get("decoy") else 1.0   # jamais lu : la « pièce » vacue

    @staticmethod
    def _keys(obs_t, history):
        cols = [tuple(np.flatnonzero(row).tolist()) for row in np.asarray(obs_t)]
        return [h + (c,) for h, c in zip(history, cols)]

    def init_state(self):
        return None

    def act(self, obs_t, state):
        n = np.asarray(obs_t).shape[0]
        history = state if state is not None else [() for _ in range(n)]
        keys = self._keys(obs_t, history)
        logits = np.zeros((n, self.K), dtype=np.float32)
        if not self.no_table:
            for i, k in enumerate(keys):
                c = self.table.get(k)
                if c is not None:
                    logits[i] = c
        return np.array(logits, copy=True), keys

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        self._dose.episodes_seen += ep.n
        if self._dose.dparam_abs_sum is None:
            self._dose.dparam_abs_sum = 0.0
        if not self.learning:
            return self._dose
        history = [() for _ in range(ep.n)]
        keys = None
        for obs_t in ep.obs_seq:
            keys = self._keys(obs_t, history)
            history = keys
        d = 0.0
        for k, t in zip(keys, np.asarray(ep.target)):
            row = self.table.setdefault(k, np.zeros(self.K, dtype=np.float32))
            row[int(t)] += self.lr
            d += self.lr
        self._dose.updates += int(d > 0.0)
        self._dose.dparam_abs_sum += d
        return self._dose

    def ablate_state(self, state, name):
        if name != "state_reset":
            raise KeyError(f"ablation d'état inconnue : {name!r}")
        return None if state is None else [() for _ in state]

    def state_dict(self):
        return {"table": {k: v.copy() for k, v in self.table.items()}}

    def dose(self):
        return self._dose

    def close(self):
        pass


class TabularLearner:
    name, family, max_K = "tabular", "tabular", 64
    entry_task = "composition_same_tick_K6 (par construction : 36 cles)"
    supported_state_ablations = frozenset({"state_reset"})

    def __init__(self, honest=False):
        table = Piece("table", "tools/harness/learners/tabular.py::_TabularInstance.table", "aucun", "aucune", None,
                      "composition", {"table": True}, True, None, "verite-terrain : necessaire par construction")
        decoy = Piece("decoy", "tools/harness/learners/tabular.py::_TabularInstance.decoy", "aucun", "aucune", None,
                      "composition", {"decoy": True}, True, None, "parametre JAMAIS lu : L4 doit le refuser")
        self.pieces = (table,) if honest else (table, decoy)

    def sweep(self):
        return [{"lr": 1.0}, {"lr": 0.5}]

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        return _TabularInstance(K, hyper["lr"], learning=not reference, without=without or {})
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_tabular.py -q`
Expected: `4 passed`

- [ ] **Step 5: Portes** — `PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/harness/learners/tabular.py` → `OK`. La méthode `learn` est captée (porte 2) : déclaration qualifiée à la tâche 8.

- [ ] **Step 6: Préparer le commit** — `scratchpad/commit_msg_t4.txt` : `feat(harness): TabularLearner de verite-terrain (table necessaire par construction, decoy refusee par L4)`. Fichiers : `tools/harness/learners/tabular.py tests/sandbox/test_harness_tabular.py`.

---

### Task 5: Verdict PUR à trois conditions — `harness_verdict_lecture`

**Files:**
- Create: `src/seed_ai/harness_verdict.py`
- Test: `tests/sandbox/test_harness_verdict.py`

**Interfaces:**
- Consumes: `tools.demand_marker.ablation_verdict(intact, ablated, floor=None, ceiling=None, n_floor=12, intervention_verified=False)` (rend `{"verdict": X_DEMANDED|X_DECOY|INCONCLUSIVE|INCONCLUSIVE_INVERTED|INCONCLUSIVE_DEGENERATE, "ratio", ...}`) ; `tools.language_memory_demand_probe.alias_guard_verdict(control_intact, control_ablated, x_response, floor, ceiling=1.0, tol=0.05, alive_margin=None, intervention_verified=True)` (`alias_verdict` ∈ SURGICAL/FUNCTIONAL_LEAK/VACUOUS_ABLATION/DEGENERATE_CONTROL) ; `tools.cognitive_demand_inworld.learner_verdict(learner_first, learner_last, reference_last, oracle_last, min_sep=0.05, ...)` — **import PARESSEUX** (le module charge les mondes) ; `tools.experiment_preflight.assert_verdict_invariant_to_optimizer(measure, lrs, reference_floor)`, `ReferenceCollapsedError`, `PreflightError`, `assert_bar_separates_the_incapable`.
- Produces: `harness_verdict_lecture(db, rule) -> dict` (clés `verdict`, `branch`, `demand`, `noise_floor`, `acquisition`, `necessity`, `e19`, `why`) ; `measure_noise_floor(intact, noop) -> {"band": [lo, hi], "per_seed": {seed: ratio}}` ; `measure_ablated_bayes_ceiling(task, ablation, n=4096, seed=0) -> {"declared", "measured", "se", "certified"}` ; `BRANCHES` (tuple, l'ORDRE imposé 2.3-b).

**Format `db`** (produit par le runner, tâche 6 ; dict JSON-sérialisable, seeds en clés `str`) :

```python
db = {
  "seeds": [0, 1, ..., 11],
  "arms": {"A":  {"first": {"0": acc, ...}, "mid": {...}, "last": {...}, "dose": {"0": dose.as_dict(), ...}},
           "A0": {"last": {...}, "dose": {...}},          # référence lr=0, mêmes tirages
           "A2": {"last": {...}, "dose": {...}},          # intact au 2e pas du sweep
           "D":  {"last": {...}, "dose": {...}},          # sans la pièce ciblée, sweep[0]
           "D2": {"last": {...}, "dose": {...}}},         # sans la pièce, sweep[1]
  "eval": {"noop": {"A": {"0": acc, ...}, "A0": {...}, "A2": {...}, "D": {...}, "D2": {...}},   # PAR BRAS (REVIEW-01 R3), second rng d'éval
           "oracle": {"0": 1.0, ...},                     # oracle sur les lots d'éval de A
           "ablated": {"permute_key": {"0": acc, ...}, ...},
           "control": {"state_reset": {"intact": {...}, "ablated": {...}}}},   # site="state" seulement
  "abandoned": {"A": [], "A0": [], "A2": [], "D": [], "D2": []},
}
rule = {"n_floor": 12, "piece": "bilinear", "sweep": [{"lr": 0.02}, {"lr": 0.002}],
        "ablations": [{"name": "permute_key", "site": "input", "must_bite": True}, ...],
        "bayes_floors": {"permute_key": 1/6, ...},
        "incapable_ceiling": {"value": 0.944, "provenance": "...", "proven": False} or None,
        "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5, "alive_margin": 0.05,
        "matched_sham": None}
```

- [ ] **Step 1: Écrire le test qui échoue (db factices à dose connue — 13 cas, un par branche)**

```python
# tests/sandbox/test_harness_verdict.py
"""Lecture pure du harnais : chaque branche de l'ORDRE 2.3-b est atteinte par UNE db factice, et rien d'autre.
Aucune constante sur collection vide : listes vides et nan LÈVENT."""
import copy
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_verdict import BRANCHES, harness_verdict_lecture, measure_noise_floor  # noqa: E402

SEEDS = list(range(12))


def _col(values):
    return {str(s): float(v) for s, v in zip(SEEDS, values)}


def _dose(updates):
    return {str(s): {"calls": 300, "updates": updates, "dparam_abs_sum": float(updates), "episodes_seen": 4800,
                     "unit": "gradient_updates"} for s in SEEDS}


def _rule(piece="bilinear"):
    return {"n_floor": 12, "piece": piece, "sweep": [{"lr": 0.02}, {"lr": 0.002}],
            "ablations": [{"name": "permute_key", "site": "input", "must_bite": True},
                          {"name": "inject_distractor_slot", "site": "input", "must_bite": False}],
            "bayes_floors": {"permute_key": 1 / 6},
            "incapable_ceiling": {"value": 34 / 36, "provenance": "forme close plain 34/36, MINORANT (plain_substrate_ceiling.py)", "proven": False},
            "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5, "alive_margin": 0.05,
            "matched_sham": None}


def _db(A=0.93, A0=0.17, A2=0.90, D=0.27, D2=0.30, noop=None, abl_key=0.17, abl_dist=None, oracle=1.0, first=0.20):
    rng = np.random.RandomState(0)
    j = lambda v, w=0.01: [v + w * x for x in rng.uniform(-1, 1, 12)]   # noqa: E731
    noop = j(A) if noop is None else noop
    abl_dist = j(A) if abl_dist is None else abl_dist
    return {"seeds": SEEDS,
            "arms": {"A": {"first": _col(j(first)), "mid": _col(j((first + A) / 2)), "last": _col(j(A)), "dose": _dose(300)},
                     "A0": {"last": _col(j(A0)), "dose": _dose(0)},
                     "A2": {"last": _col(j(A2)), "dose": _dose(300)},
                     "D": {"last": _col(j(D)), "dose": _dose(300)},
                     "D2": {"last": _col(j(D2)), "dose": _dose(300)}},
            "eval": {"noop": {"A": _col(noop), "A0": _col(j(A0)), "A2": _col(j(A2)), "D": _col(j(D)), "D2": _col(j(D2))},
                     "oracle": _col([oracle] * 12),
                     "ablated": {"permute_key": _col(j(abl_key)), "inject_distractor_slot": _col(abl_dist)},
                     "control": {}},
            "abandoned": {k: [] for k in ("A", "A0", "A2", "D", "D2")}}


def test_branch_order_is_the_sealed_one():
    assert BRANCHES == ("INCOMPLET", "INCONCLUSIVE_N", "INDETERMINE_HARNAIS", "LR_ARTIFACT", "NOT_DEMANDED",
                        "DEMAND_WITHIN_NOISE", "INCONCLUSIVE_SPECIFICITY", "INCONCLUSIVE_ALIAS", "NOT_ACQUIRED",
                        "PIECE_NOT_NECESSARY", "PIECE_INCONCLUSIVE", "PIECE_PARTIAL", "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")


def test_cell_A_known_answer_is_PARTIAL_with_ceiling_above_bar():
    out = harness_verdict_lecture(_db(), _rule())
    assert out["verdict"] == "PIECE_PARTIAL"
    assert out["demand"]["permute_key"]["verdict"] == "X_DEMANDED"
    assert out["demand"]["inject_distractor_slot"]["verdict"] == "X_DECOY"
    assert out["acquisition"]["verdict"] == "ACQUIRED" and out["acquisition"]["per_seed_above_ref"] == "12/12"
    assert out["acquisition"]["representational_ceiling_above_bar"] is True
    assert out["acquisition"]["bar_status"] == "CEILING_ABOVE_BAR"
    assert out["necessity"]["bilinear"]["verdict"] == "PIECE_PARTIAL"
    assert out["necessity"]["bilinear"]["sham"] == "PARAMS_NON_APPARIES"
    assert 0.0 <= out["e19"]["closure"] <= 2 / 3


def test_cell_B_known_answer_is_NECESSARY():
    out = harness_verdict_lecture(_db(D=0.18, D2=0.19), _rule("recurrent_state"))
    assert out["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"
    assert out["necessity"]["recurrent_state"]["verdict"] == "NECESSARY"


def test_ablated_equal_to_intact_is_NOT_DEMANDED():
    assert harness_verdict_lecture(_db(abl_key=0.93), _rule())["verdict"] == "NOT_DEMANDED"


def test_ratio_inside_the_measured_noise_band_is_DEMAND_WITHIN_NOISE_never_decoy():
    db = _db(abl_key=0.88, noop=[0.93 / r for r in np.linspace(0.92, 1.08, 12)])   # bande [0.92 ; 1.08] mesurée
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "DEMAND_WITHIN_NOISE"
    assert out["demand"]["permute_key"]["in_noise_band"] is True


def test_a_biting_control_is_INCONCLUSIVE_SPECIFICITY():
    assert harness_verdict_lecture(_db(abl_dist=[0.40] * 12), _rule())["verdict"] == "INCONCLUSIVE_SPECIFICITY"


def test_learner_at_reference_is_NOT_ACQUIRED_with_dose_and_saturation():
    out = harness_verdict_lecture(_db(A=0.18, A2=0.18, D=0.17, D2=0.17, abl_key=0.10, first=0.17), _rule())
    assert out["verdict"] == "NOT_ACQUIRED"
    assert out["acquisition"]["dose"]["A"]["updates"] == 300
    assert out["acquisition"]["saturation"] in ("TENDANCE", "PLATEAU")


def test_reference_above_prior_max_is_INDETERMINE_HARNAIS_PRIOR_SOLVES():
    out = harness_verdict_lecture(_db(A0=0.60), _rule())
    assert out["verdict"] == "INDETERMINE_HARNAIS" and "PRIOR_SOLVES" in out["why"]


def test_oracle_below_min_is_INDETERMINE_HARNAIS():
    assert harness_verdict_lecture(_db(oracle=0.85), _rule())["verdict"] == "INDETERMINE_HARNAIS"


def test_piece_gap_that_closes_at_the_second_lr_is_LR_ARTIFACT():
    assert harness_verdict_lecture(_db(D=0.27, D2=0.88, A2=0.90), _rule())["verdict"] == "LR_ARTIFACT"


def test_intact_collapsed_at_the_second_lr_is_INDETERMINE_HARNAIS():
    # acquis à sweep[0] (0,93) mais l'intact tombe SOUS la barre au second pas (0,18) : la closure E19 n'a plus de référence
    assert harness_verdict_lecture(_db(A2=0.18, D2=0.17), _rule())["verdict"] == "INDETERMINE_HARNAIS"


def test_acquisition_null_that_vanishes_at_the_second_lr_is_LR_ARTIFACT():
    # inerte à sweep[0] (0,18 ~ référence) mais acquiert au second pas (0,90 sur 12/12) : nul d'acquisition NON robuste au pas
    assert harness_verdict_lecture(_db(A=0.18, A2=0.90, D=0.17, D2=0.30, first=0.17), _rule())["verdict"] == "LR_ARTIFACT"


def test_D_equal_to_A_is_PIECE_NOT_NECESSARY_and_both_at_ceiling_is_not_degenerate():
    db = _db(A=1.0, A2=1.0, D=1.0, D2=1.0, noop=[1.0] * 12, abl_dist=[1.0] * 12)
    db["eval"]["noop"]["D"] = _col([1.0] * 12)
    out = harness_verdict_lecture(db, _rule())
    assert out["verdict"] == "PIECE_NOT_NECESSARY"


def test_missing_arm_is_INCOMPLET_and_n11_is_INCONCLUSIVE_N():
    db = _db()
    del db["arms"]["D2"]
    assert harness_verdict_lecture(db, _rule())["verdict"] == "INCOMPLET"
    db = _db()
    db["abandoned"]["D"] = [3]
    del db["arms"]["D"]["last"]["3"]
    assert harness_verdict_lecture(db, _rule())["verdict"] == "INCONCLUSIVE_N"


def test_nan_and_empty_raise_instead_of_fabricating():
    db = _db()
    db["arms"]["A"]["last"]["0"] = float("nan")
    with pytest.raises(ValueError, match="nan"):
        harness_verdict_lecture(db, _rule())
    with pytest.raises(ValueError, match="vide"):
        measure_noise_floor({}, {})


def test_noise_floor_band_is_min_max_of_paired_ratios():
    out = measure_noise_floor(_col([0.93] * 12), _col([0.93 / r for r in np.linspace(0.95, 1.05, 12)]))
    assert out["band"][0] == pytest.approx(0.95, abs=1e-6) and out["band"][1] == pytest.approx(1.05, abs=1e-6)


def test_necessity_uses_the_band_of_the_WEAK_arm_not_only_A():
    """R3 : a p = 0,27 la bande du bras D est large (+-18 %) ; un ratio A/D de 1,5 DANS la bande de D est WITHIN_NOISE."""
    db = _db(D=0.62, D2=0.62)                                  # ratio A/D = 1,5 : hors bande de A (+-1 %)...
    db["eval"]["noop"]["D"] = _col([0.62 / r for r in np.linspace(0.6, 1.6, 12)])   # ...mais DANS la bande de D
    out = harness_verdict_lecture(db, _rule())
    assert out["noise_floor"]["D"]["band"][1] > 1.5
    assert out["necessity"]["bilinear"]["in_noise_band"] is True and out["verdict"] == "PIECE_NOT_NECESSARY"


def test_mutating_necessity_threshold_to_strict_flips_the_boundary_case():
    """Porte 15 en miniature : med(D) == référence + min_sep exactement ; la règle dit <= -> NECESSARY."""
    db = _db(D=0.22, D2=0.22, A0=0.17)
    for s in SEEDS:
        db["arms"]["D"]["last"][str(s)] = 0.17 + 0.05
        db["arms"]["A0"]["last"][str(s)] = 0.17
    assert harness_verdict_lecture(db, _rule())["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_verdict.py -q`
Expected: `ModuleNotFoundError: No module named 'src.seed_ai.harness_verdict'`

- [ ] **Step 3: Écrire `src/seed_ai/harness_verdict.py`**

```python
"""
src/seed_ai/harness_verdict.py — Lecture PURE du harnais (ADR-004, spec §2.3-6) : trois conditions, branches
dans un ORDRE imposé, aucune constante fabriquée sur collection vide (nan et vide LÈVENT). Compose les instruments
déjà calibrés : ablation_verdict (demande, nécessité), alias_guard_verdict (ablation d'état), learner_verdict
(acquisition, import paresseux : son module charge les mondes), assert_verdict_invariant_to_optimizer (E19).
La garde de barre est appelée sur le plafond de REPRÉSENTATION déclaré et son issue est PUBLIÉE (bar_status),
jamais levée : sur la cellule A, 0,944 > 0,217 est exactement ce que le harnais doit savoir DIRE.
"""
import statistics
from typing import Optional

import numpy as np

BRANCHES = ("INCOMPLET", "INCONCLUSIVE_N", "INDETERMINE_HARNAIS", "LR_ARTIFACT", "NOT_DEMANDED",
            "DEMAND_WITHIN_NOISE", "INCONCLUSIVE_SPECIFICITY", "INCONCLUSIVE_ALIAS", "NOT_ACQUIRED",
            "PIECE_NOT_NECESSARY", "PIECE_INCONCLUSIVE", "PIECE_PARTIAL", "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")

_ARMS = ("A", "A0", "A2", "D", "D2")


def _series(col: dict, seeds, label) -> list:
    """dict seed->valeur -> liste alignée sur `seeds` ; LÈVE sur absence, vide ou non fini (jamais 0.0)."""
    if not col:
        raise ValueError(f"{label} : série vide")
    out = []
    for s in seeds:
        v = col.get(str(s), col.get(s))
        if v is None:
            raise KeyError(f"{label} : seed {s} absent")
        v = float(v)
        if not np.isfinite(v):
            raise ValueError(f"{label} : seed {s} vaut nan/inf")
        out.append(v)
    return out


def _med(xs):
    if not xs:
        raise ValueError("médiane d'une liste vide")
    return float(statistics.median(xs))


def measure_noise_floor(intact: dict, noop: dict) -> dict:
    """Plancher de bruit MESURÉ : ratios intact/noop appariés par seed (même politique, second rng d'éval).
    Rend {"band": [min, max], "per_seed": {seed: ratio}}. Un no-op à l'argmax sur le MÊME lot rendrait 1,0 par
    construction : c'est le second rng qui fait la bande."""
    if not intact or not noop:
        raise ValueError("measure_noise_floor : série vide")
    seeds = sorted(intact, key=lambda k: int(k))
    i, n = _series(intact, seeds, "intact"), _series(noop, seeds, "noop")
    ratios = {str(s): (a / b if b > 0 else float("inf")) for s, a, b in zip(seeds, i, n)}
    vals = list(ratios.values())
    if any(not np.isfinite(r) for r in vals):
        raise ValueError("measure_noise_floor : un bras noop est à 0 (ratio infini)")
    return {"band": [min(vals), max(vals)], "per_seed": ratios}


def measure_ablated_bayes_ceiling(task, ablation, n=4096, seed=0) -> dict:
    """Plafond de Bayes du flux ABLATÉ : accuracy de l'oracle sous l'ablation sur n tirages, confrontée au
    `bayes_floor` DÉCLARÉ. certified ssi déclaré, dans ± 2 se, et espace d'états énumérable."""
    ep = task.episodes(np.random.RandomState(seed), n, "train")
    ep_a = ablation.apply(ep, np.random.RandomState(seed + 1))
    measured = float(np.mean(task.score(np.asarray(task.oracle(ep_a)), ep_a)))
    declared = None if ablation.bayes_floor is None else float(ablation.bayes_floor)
    p = measured if declared is None else declared
    se = float(np.sqrt(max(p * (1.0 - p), 1e-12) / n))
    certified = declared is not None and abs(measured - declared) <= 2.0 * se and task.enumerate_states() is not None
    return {"declared": declared, "measured": measured, "se": se, "certified": bool(certified)}


def _demand(db, rule, seeds, last_A, band):
    from tools.demand_marker import ablation_verdict
    from tools.language_memory_demand_probe import alias_guard_verdict
    out, worst = {}, None
    for a in rule["ablations"]:
        name, must = a["name"], bool(a["must_bite"])
        col = db["eval"]["ablated"].get(name)
        if col is None:
            raise KeyError(f"ablated:{name}")
        ablated = _series(col, seeds, f"ablated:{name}")
        floor = rule["bayes_floors"].get(name)
        # ceiling=None : deux bras au plafond = « n'a pas mordu » (spécificité SATISFAITE), pas « dégénéré » —
        # le contrat de tâche a déjà prouvé sur l'oracle que chaque must_bite mord.
        raw = ablation_verdict(last_A, ablated, floor=(floor if must else None), ceiling=None, n_floor=int(rule["n_floor"]),
                               collapse_factor=float(rule["collapse_factor"]), intervention_verified=True)
        in_band = bool(band[0] <= raw["ratio"] <= band[1])
        entry = {"must_bite": must, "verdict": raw["verdict"], "ratio": raw["ratio"], "in_noise_band": in_band,
                 "raw": raw, "alias": None}
        if a["site"] == "state":
            ctrl = db["eval"]["control"].get(name)
            if ctrl is None:
                raise KeyError(f"control:{name}")
            ci, ca = _series(ctrl["intact"], seeds, "ctrl_intact"), _series(ctrl["ablated"], seeds, "ctrl_ablated")
            x_resp = abs(_med(last_A) - _med(ablated))
            entry["alias"] = alias_guard_verdict(ci, ca, x_resp, floor=(floor if floor is not None else 0.0),
                                                 ceiling=1.0, alive_margin=float(rule["alive_margin"]))
        out[name] = entry
        # branche la plus sévère parmi les ablations (ordre : NOT_DEMANDED < WITHIN_NOISE < SPECIFICITY < ALIAS)
        if must:
            if raw["verdict"] != "X_DEMANDED":
                b = "DEMAND_WITHIN_NOISE" if in_band else "NOT_DEMANDED"
                worst = _worse(worst, b)
            elif in_band:
                worst = _worse(worst, "DEMAND_WITHIN_NOISE")
            if entry["alias"] is not None and entry["alias"]["alias_verdict"] != "SURGICAL":
                worst = _worse(worst, "INCONCLUSIVE_ALIAS")
        elif raw["verdict"] != "X_DECOY":
            worst = _worse(worst, "INCONCLUSIVE_SPECIFICITY")
    return out, worst


def _worse(current, candidate):
    if current is None:
        return candidate
    return current if BRANCHES.index(current) <= BRANCHES.index(candidate) else candidate


def _acquisition(db, rule, seeds, first_A, mid_A, last_A, last_A0, oracle):
    from tools.cognitive_demand_inworld import learner_verdict          # paresseux : le module charge les mondes
    from tools.experiment_preflight import PreflightError, assert_bar_separates_the_incapable
    min_sep = float(rule["min_sep"])
    ref, med_A = _med(last_A0), _med(last_A)
    bar = ref + min_sep
    above = sum(1 for a, r in zip(last_A, last_A0) if a > r + min_sep)
    ceil = rule.get("incapable_ceiling")
    bar_status, ceiling_above = "CEILING_UNVALIDATED", None
    if ceil is not None:
        try:
            assert_bar_separates_the_incapable(bar, float(ceil["value"]), str(ceil["provenance"]), label="barre d'acquisition")
            bar_status, ceiling_above = "SEPARATES", False
        except PreflightError:
            bar_status, ceiling_above = "CEILING_ABOVE_BAR", True
    saturation = "PLATEAU" if (med_A - _med(mid_A)) <= min_sep else "TENDANCE"
    entry = {"bar": bar, "reference_last": ref, "learner_last": med_A, "learner_first": _med(first_A),
             "per_seed_above_ref": f"{above}/{len(seeds)}", "saturation": saturation, "bar_status": bar_status,
             "representational_ceiling_above_bar": ceiling_above,
             "dose": {arm: db["arms"][arm]["dose"] for arm in ("A", "A0")}}
    if _med(oracle) < float(rule["oracle_min"]):
        entry.update(verdict="INDETERMINE_HARNAIS", why=f"oracle {_med(oracle):.3f} < {rule['oracle_min']} : le contrôle positif de la DV échoue")
        return entry
    if ref > float(rule["prior_max"]):
        entry.update(verdict="INDETERMINE_HARNAIS", why=f"PRIOR_SOLVES : la référence lr=0 note {ref:.3f} > {rule['prior_max']} (contamination ou tâche triviale, jamais « acquis »)")
        return entry
    raw = learner_verdict(_med(first_A), med_A, ref, _med(oracle), min_sep=min_sep, min_gain=min_sep,
                          oracle_min=float(rule["oracle_min"]), reference_max=float(rule["prior_max"]))
    entry["raw"] = raw
    if raw["verdict"] == "LEARNER_LEARNS" and above == len(seeds):
        entry.update(verdict="ACQUIRED", why=None)
    elif raw["verdict"] == "INDETERMINE_HARNAIS":
        entry.update(verdict="INDETERMINE_HARNAIS", why=raw["why"])
    else:
        entry.update(verdict="NOT_ACQUIRED", why=raw.get("why") or f"{above}/{len(seeds)} seeds au-dessus de leur référence appariée")
    return entry


def _necessity(db, rule, seeds, last_A, last_D, ref, band):
    from tools.demand_marker import ablation_verdict
    min_sep = float(rule["min_sep"])
    raw = ablation_verdict(last_A, last_D, floor=None, ceiling=None, n_floor=int(rule["n_floor"]),
                           collapse_factor=float(rule["collapse_factor"]), intervention_verified=True)
    med_D = _med(last_D)
    in_band = bool(band[0] <= raw["ratio"] <= band[1])
    if raw["verdict"] == "X_DEMANDED" and not in_band:
        verdict = "NECESSARY" if med_D <= ref + min_sep else "PIECE_PARTIAL"
    elif raw["verdict"] in ("X_DECOY", "INCONCLUSIVE_INVERTED") or in_band:
        verdict = "NOT_NECESSARY"
    else:
        verdict = "INCONCLUSIVE"
    return {"verdict": verdict, "ratio": raw["ratio"], "in_noise_band": in_band, "med_without": med_D,
            "per_seed_diff": [a - d for a, d in zip(last_A, last_D)], "raw": raw,
            "sham": ("DECLARED" if rule.get("matched_sham") else "PARAMS_NON_APPARIES")}


def _e19(rule, last_A, last_A2, last_D, last_D2, bar):
    from tools.experiment_preflight import PreflightError, ReferenceCollapsedError, assert_verdict_invariant_to_optimizer
    lrs = [float(h["lr"]) for h in rule["sweep"]]
    table = {lrs[0]: (_med(last_D), _med(last_A)), lrs[1]: (_med(last_D2), _med(last_A2))}
    gaps = {str(lr): ref - tested for lr, (tested, ref) in table.items()}
    g = list(gaps.values())
    closure = None if max(g) <= 0 else 1.0 - min(g) / max(g)
    out = {"lrs": lrs, "gaps_by_lr": gaps, "closure": closure, "status": "ROBUST"}
    try:
        assert_verdict_invariant_to_optimizer(lambda lr: table[lr], lrs=lrs, reference_floor=bar, label="nécessité de la pièce")
    except ReferenceCollapsedError as e:
        out.update(status="REFERENCE_COLLAPSED", why=str(e))
    except PreflightError as e:
        out.update(status="LR_ARTIFACT", why=str(e))
    return out


def harness_verdict_lecture(db: dict, rule: dict) -> dict:
    """Verdict global dans l'ORDRE 2.3-b (BRANCHES). LÈVE sur nan ou série vide ; INCOMPLET sur bras/éval absent ;
    INCONCLUSIVE_N si un bras a moins de n_floor seeds ; rend toujours `branch` ∈ BRANCHES."""
    seeds = [int(s) for s in db.get("seeds", [])]
    n_floor = int(rule["n_floor"])
    out = {"verdict": None, "branch": None, "why": None, "demand": None, "noise_floor": None,
           "acquisition": None, "necessity": None, "e19": None}

    def _done(branch, why=None):
        out.update(verdict=branch, branch=branch, why=why)
        return out

    for arm in _ARMS:
        if arm not in db.get("arms", {}) or "last" not in db["arms"][arm]:
            return _done("INCOMPLET", f"bras {arm} absent")
    for k in ("noop", "oracle", "ablated"):
        if k not in db.get("eval", {}):
            return _done("INCOMPLET", f"éval {k} absente")
    for arm in _ARMS:
        if arm not in db["eval"]["noop"]:
            return _done("INCOMPLET", f"noop du bras {arm} absent (bande de bruit PAR BRAS, REVIEW-01 R3)")
    if not seeds:
        raise ValueError("db.seeds vide")
    abandoned = {arm: set(int(s) for s in db.get("abandoned", {}).get(arm, [])) for arm in _ARMS}
    kept = [s for s in seeds if not any(s in abandoned[a] for a in _ARMS)]
    if len(kept) < n_floor:
        return _done("INCONCLUSIVE_N", f"{len(kept)} seeds complets < n_floor={n_floor} (abandons : { {a: sorted(v) for a, v in abandoned.items() if v} })")
    last = {arm: _series(db["arms"][arm]["last"], kept, f"{arm}.last") for arm in _ARMS}
    first_A = _series(db["arms"]["A"]["first"], kept, "A.first")
    mid_A = _series(db["arms"]["A"]["mid"], kept, "A.mid")
    oracle = _series(db["eval"]["oracle"], kept, "oracle")
    out["noise_floor"] = {arm: measure_noise_floor({str(s): v for s, v in zip(kept, last[arm])},
                                                   {str(s): db["eval"]["noop"][arm][str(s)] for s in kept})
                          for arm in _ARMS}
    band = out["noise_floor"]["A"]["band"]                       # (i) : le sujet A contre ses ablations
    band_AD = [min(band[0], out["noise_floor"]["D"]["band"][0]),   # (iii) : union des bandes des DEUX bras compares
               max(band[1], out["noise_floor"]["D"]["band"][1])]
    out["acquisition"] = _acquisition(db, rule, kept, first_A, mid_A, last["A"], last["A0"], oracle)
    if out["acquisition"]["verdict"] == "INDETERMINE_HARNAIS":
        return _done("INDETERMINE_HARNAIS", out["acquisition"]["why"])
    bar = out["acquisition"]["bar"]
    min_sep = float(rule["min_sep"])
    if out["acquisition"]["verdict"] != "ACQUIRED":
        # E19 sur l'ACQUISITION : le nul tient-il au pas ? (l'intact acquiert-il au second pas du sweep ?)
        above2 = sum(1 for a, r in zip(last["A2"], last["A0"]) if a > r + min_sep)
        out["e19"] = {"lrs": [float(h["lr"]) for h in rule["sweep"]], "gaps_by_lr": None, "closure": None,
                      "status": ("LR_ARTIFACT" if (_med(last["A2"]) > bar and above2 == len(kept)) else "ACQUISITION_NULL_ROBUST"),
                      "why": f"A2 (second pas) médiane {_med(last['A2']):.3f}, {above2}/{len(kept)} seeds au-dessus de la référence"}
        if out["e19"]["status"] == "LR_ARTIFACT":
            return _done("LR_ARTIFACT", "le nul d'acquisition disparaît au second pas du sweep (E19) : " + out["e19"]["why"])
        out["demand"], worst = _demand(db, rule, kept, last["A"], band)
        if worst is not None:
            return _done(worst, "au moins une ablation ne rend pas l'issue exigée (voir demand)")
        return _done("NOT_ACQUIRED", out["acquisition"]["why"])
    # E19 sur la NÉCESSITÉ : l'écart intact / sans-pièce tient-il aux deux pas ? (référence = l'intact, jamais sous la barre)
    out["e19"] = _e19(rule, last["A"], last["A2"], last["D"], last["D2"], bar)
    if out["e19"]["status"] == "REFERENCE_COLLAPSED":
        return _done("INDETERMINE_HARNAIS", out["e19"]["why"])
    if out["e19"]["status"] == "LR_ARTIFACT":
        return _done("LR_ARTIFACT", out["e19"]["why"])
    out["demand"], worst = _demand(db, rule, kept, last["A"], band)
    if worst is not None:
        return _done(worst, "au moins une ablation ne rend pas l'issue exigée (voir demand)")
    piece = rule["piece"]
    nec = _necessity(db, rule, kept, last["A"], last["D"], out["acquisition"]["reference_last"], band_AD)
    out["necessity"] = {piece: nec}
    if nec["verdict"] == "NOT_NECESSARY":
        return _done("PIECE_NOT_NECESSARY")
    if nec["verdict"] == "INCONCLUSIVE":
        return _done("PIECE_INCONCLUSIVE", "ratio A/D dans la zone grise [1,3 ; 1,5[")
    if nec["verdict"] == "PIECE_PARTIAL":
        return _done("PIECE_PARTIAL", f"la variante sans {piece} chute ({nec['ratio']:.2f}x) mais franchit la barre d'acquisition ({nec['med_without']:.3f} > {bar:.3f})")
    if nec["verdict"] == "NECESSARY":
        return _done("DEMANDED_ACQUIRED_NECESSARY")
    return _done("AUTRE", f"nécessité inattendue : {nec['verdict']}")
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_verdict.py -q`
Expected: `18 passed`. Si `test_learner_at_reference_is_NOT_ACQUIRED...` rend `LR_ARTIFACT` : les gaps A-D y sont ≈ 0,01 aux deux pas (g_max ≤ 0,02) — vérifier que `closure` reste ≤ 2/3 ; sinon régler `D2=0.18` dans le cas.

- [ ] **Step 5: Portes**

Run: `PYTHONIOENCODING=utf-8 python tools/check_bar_separation.py --only src/seed_ai/harness_verdict.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only src/seed_ai/harness_verdict.py`
Expected: deux `OK` (`bar = ref + min_sep` n'a ni nom de chance ni constante littérale ; aucun `IfExp` à constante).

- [ ] **Step 6: Préparer le commit** — `scratchpad/commit_msg_t5.txt` : `feat(harness): harness_verdict_lecture -- trois conditions, 14 branches ordonnees, plancher de bruit mesure, E19 publie ; 16 cas a reponse connue`. Fichiers : `src/seed_ai/harness_verdict.py tests/sandbox/test_harness_verdict.py`.

---

### Task 6: Runner de cellule — `run_harness_cell`

**Files:**
- Create: `tools/harness/cell.py`
- Test: `tests/sandbox/test_harness_cell.py`

**Interfaces:**
- Consumes: `assert_task_contract`, `assert_learner_contract`, `run_episode`, `harness_verdict_lecture`, `measure_ablated_bayes_ceiling` ; `tools.preregister.verify(name, _dir=None)`, `provenance(name, _dir=None)` ; `tools.experiment_preflight.declare_design`, `assert_control_family`, `assert_selection_nonempty` ; `tools.cost_guard.project_cost`, `CostGuard`, `CostExceeded`, `CostTooHighToStart` ; `src.seed_ai.harness.Harness(with_db=False, name, seed)` + `.save(data)`.
- Produces: `run_harness_cell(task, learner, rule_name, *, seeds, episodes, out_name, n_agents=16, eval_batches=40, budget_s=3600.0, unit_s=None, prereg_dir=None, save=True, clock=None) -> {"db", "verdict", "path", "cost"}`. Bras par seed : `A` (sweep[0]), `A0` (référence lr=0, mêmes tirages), `A2` (sweep[1]), `D` (sans `rule["piece"]`, sweep[0]), `D2` (sans, sweep[1]). RNG : opérandes `RandomState(seed + 1)` (train PUIS éval `last` en continu = bit-identité avec `_train_eval_one`) ; `first`/`mid` sur `RandomState(seed + 7919)` (courbe, pas la DV) ; `noop` sur `RandomState(seed + 104729)` ; ablations d'entrée et contrôles sur les MÊMES lots que `last` (état du rng restauré) avec `RandomState(seed + 31)` pour la permutation.

- [ ] **Step 1: Écrire le test qui échoue (injection : learner jouet, règle scellée dans un répertoire temporaire)**

```python
# tests/sandbox/test_harness_cell.py
"""Runner de cellule testé par INJECTION (P2.56) : un learner jouet, une règle scellée dans un dossier temporaire,
une sentinelle qui LÈVE si le corps est atteint avant les gardes, une horloge factice pour l'abandon."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_task import Ablation, DemandDeclaration  # noqa: E402
from tools.cost_guard import CostTooHighToStart  # noqa: E402
from tools.experiment_preflight import PreflightError  # noqa: E402
from tools.harness.cell import run_harness_cell  # noqa: E402
from tools.preregister import PreregistrationTampered, preregister  # noqa: E402
from tests.sandbox.test_harness_learner import CounterLearner  # noqa: E402
from tests.sandbox.test_harness_task import ToyParity  # noqa: E402

SEEDS = list(range(12))


def _rule():
    return {"question": "cellule jouet", "n_floor": 12, "piece": "table", "sweep": [{"lr": 1.0}, {"lr": 0.5}],
            "ablations": [{"name": "permute_a", "site": "input", "must_bite": True},
                          {"name": "permute_nothing", "site": "input", "must_bite": False}],
            "bayes_floors": {"permute_a": 0.5}, "incapable_ceiling": None,
            "min_sep": 0.05, "prior_max": 0.6, "oracle_min": 0.9, "collapse_factor": 1.5, "alive_margin": 0.05,
            "matched_sham": None, "budget_s": 600.0,
            "dv_primaire": "`hits` par seed ; `ratio_within` ; `sep_ref` ; `dose.updates`",
            "discrimination": {k: "…" for k in ("INCOMPLET", "NOT_ACQUIRED", "DEMANDED_ACQUIRED_NECESSARY", "AUTRE")}}


@pytest.fixture
def sealed(tmp_path):
    preregister("HARNESS-TOY", _rule(), _dir=str(tmp_path))
    return str(tmp_path)


class _Sentinel(CounterLearner):
    def build(self, *a, **k):
        raise AssertionError("CORPS ATTEINT : build appelé avant les gardes")


def test_task_contract_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    task = ToyParity(with_nobite=False)
    with pytest.raises(PreflightError, match="must_bite=False"):
        run_harness_cell(task, _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy", prereg_dir=sealed)


def test_tampered_rule_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    p = os.path.join(sealed, "HARNESS-TOY.json")
    payload = json.load(open(p, encoding="utf-8"))
    payload["rule"]["n_floor"] = 3
    json.dump(payload, open(p, "w", encoding="utf-8"))
    with pytest.raises(PreregistrationTampered):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy", prereg_dir=sealed)


def test_cost_projection_refuses_before_any_build(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    with pytest.raises(CostTooHighToStart):
        run_harness_cell(ToyParity(), _Sentinel(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy",
                         prereg_dir=sealed, budget_s=1.0, unit_s=10.0)


def test_unit_is_the_seed_and_reference_is_dose_matched(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    out = run_harness_cell(ToyParity(), CounterLearner(), "HARNESS-TOY", seeds=SEEDS, episodes=40, out_name="toy",
                           prereg_dir=sealed, n_agents=8, eval_batches=10)
    db = out["db"]
    assert sorted(int(s) for s in db["arms"]["A"]["last"]) == SEEDS
    for s in SEEDS:
        assert db["arms"]["A0"]["dose"][str(s)]["calls"] == db["arms"]["A"]["dose"][str(s)]["calls"] == 40
        assert db["arms"]["A0"]["dose"][str(s)]["updates"] == 0
    assert set(db["eval"]["ablated"]) == {"permute_a", "permute_nothing"}
    assert out["verdict"]["verdict"] == "DEMANDED_ACQUIRED_NECESSARY"       # la table est nécessaire par construction
    assert os.path.exists(out["path"])
    saved = json.load(open(out["path"], encoding="utf-8"))
    assert saved["data"]["regime"]["episodes"] == 40 and saved["data"]["preregistration"]["name"] == "HARNESS-TOY"
    assert saved["data"]["design"]["replication_unit"] == "seed" and saved["data"]["design"]["n_independent"] == 12


def test_abandoned_seed_is_counted_and_yields_INCONCLUSIVE_N(sealed, tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", str(tmp_path / "res"))
    t = {"now": 0.0}

    def clock():
        t["now"] += 0.0 if t["now"] < 5 else 1000.0     # les premiers appels sont gratuits, puis le temps saute
        t["now"] += 0.001
        return t["now"]

    out = run_harness_cell(ToyParity(), CounterLearner(), "HARNESS-TOY", seeds=SEEDS, episodes=5, out_name="toy",
                           prereg_dir=sealed, n_agents=8, eval_batches=5, budget_s=3600.0, unit_s=0.001, clock=clock)
    assert out["verdict"]["verdict"] == "INCONCLUSIVE_N"
    assert any(out["db"]["abandoned"][arm] for arm in out["db"]["abandoned"])
```

- [ ] **Step 2: Lancer le test, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_cell.py -q`
Expected: `ModuleNotFoundError: No module named 'tools.harness.cell'`

- [ ] **Step 3: Écrire `tools/harness/cell.py`**

```python
"""
tools/harness/cell.py — UNE cellule du harnais (ADR-004, spec §2.3) : (Task acceptée, Learner accepté, n seeds,
règle scellée) -> db -> verdict à trois conditions -> JSON via Harness.save.

Tout ce qui refuse refuse AVANT le premier entraînement : règle scellée (verify), contrats (assert_*),
design déclaré (declare_design + famille de contrôles), coût projeté sur une unité MESURÉE (project_cost).
Bras par seed, tous sur les MÊMES tirages : A (sweep[0]) · A0 (référence lr=0, même nombre d'épisodes) ·
A2 (sweep[1]) · D (sans la pièce, sweep[0]) · D2 (sans la pièce, sweep[1]). Le bras A porte l'éval : `last` sur
le rng d'entraînement CONTINUÉ (bit-identité avec bilinear_composition_probe._train_eval_one), `noop` sur un
second rng (plancher de bruit), ablations et contrôles sur les MÊMES lots que `last`. Aucun bail, aucun monde.
"""
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness import Harness  # noqa: E402
from src.seed_ai.harness_learner import assert_learner_contract, run_episode  # noqa: E402
from src.seed_ai.harness_task import assert_task_contract  # noqa: E402
from src.seed_ai.harness_verdict import harness_verdict_lecture, measure_ablated_bayes_ceiling  # noqa: E402
from tools.cost_guard import CostExceeded, CostGuard, project_cost  # noqa: E402
from tools.experiment_preflight import assert_control_family, assert_selection_nonempty, declare_design  # noqa: E402
from tools.preregister import provenance, verify  # noqa: E402

ARMS = ("A", "A0", "A2", "D", "D2")


def _accuracy(inst, task, rng, batches, n, ablate=None, split="train", oracle=False):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n, split)
        if oracle:
            hits.append(np.asarray(task.score(np.asarray(task.oracle(ep)), ep), dtype=np.float32))
        else:
            hits.append(run_episode(inst, ep, task, ablate=ablate)[1])
    if not hits:
        raise ValueError("_accuracy : aucun lot évalué")
    return float(np.mean(np.concatenate(hits)))


def _accuracy_ablated(inst, task, rng, batches, n, ablation, rng_abl):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n, "train")
        ep_a = ablation.apply(ep, rng_abl)
        hits.append(run_episode(inst, ep_a, task)[1])
    return float(np.mean(np.concatenate(hits)))


def _run_arm(task, learner, seed, n, K, hyper, episodes, eval_batches, *, without=None, reference=False, full_eval=False):
    """Un bras : entraîne `episodes` lots puis évalue `last` sur le rng continué. full_eval (bras A seulement)
    ajoute first/mid (rng de courbe), noop (second rng), ablations, contrôles, oracle."""
    inst = learner.build(seed, n, task.obs_dim, K, hyper, without=without or {}, reference=reference)
    try:
        rng = np.random.RandomState(seed + 1)                       # opérandes : key PUIS q par épisode
        rng_curve = np.random.RandomState(seed + 7919)
        out = {}
        if full_eval:
            out["first"] = _accuracy(inst, task, rng_curve, eval_batches, n)
        for i in range(episodes):
            if full_eval and i == episodes // 2:
                out["mid"] = _accuracy(inst, task, rng_curve, eval_batches, n)
            ep = task.episodes(rng, n, "train")
            actions, hits = run_episode(inst, ep, task)
            inst.learn(ep, actions, hits)
        if full_eval and "mid" not in out:
            out["mid"] = out["first"]
        state = rng.get_state()
        out["last"] = _accuracy(inst, task, rng, eval_batches, n)
        out["dose"] = inst.dose().as_dict()
        out["noop"] = _accuracy(inst, task, np.random.RandomState(seed + 104729), eval_batches, n)   # TOUS les bras (R3)
        if full_eval:
            rng.set_state(state)
            out["oracle"] = _accuracy(inst, task, rng, eval_batches, n, oracle=True)
            out["ablated"], out["control"] = {}, {}
            for a in task.demand.ablations:
                rng.set_state(state)
                if a.site == "input":
                    out["ablated"][a.name] = _accuracy_ablated(inst, task, rng, eval_batches, n, a, np.random.RandomState(seed + 31))
                else:
                    out["ablated"][a.name] = _accuracy(inst, task, rng, eval_batches, n, ablate=a.name)
                    rng.set_state(state)
                    ci = _accuracy(inst, task, rng, eval_batches, n, split="control")
                    rng.set_state(state)
                    ca = _accuracy(inst, task, rng, eval_batches, n, split="control", ablate=a.name)
                    out["control"][a.name] = {"intact": ci, "ablated": ca}
        return out
    finally:
        inst.close()


def run_harness_cell(task, learner, rule_name, *, seeds, episodes, out_name, n_agents=16, eval_batches=40,
                     budget_s=3600.0, unit_s=None, prereg_dir=None, save=True, clock=None):
    """Voir docstring de module. Rend {"db", "verdict", "path", "cost"}. Refus EN TÊTE : règle altérée
    (PreregistrationTampered), contrat de tâche / de learner (PreflightError), coût (CostTooHighToStart)."""
    rule = verify(rule_name, _dir=prereg_dir)
    prov = provenance(rule_name, _dir=prereg_dir)
    seeds = [int(s) for s in seeds]
    assert_selection_nonempty(len(seeds), label="seeds")
    contract_task = assert_task_contract(task, seed=seeds[0], n=64)
    assert_learner_contract(learner, task, seed=seeds[0])
    K = int(task.K)
    sweep = [dict(h) for h in rule["sweep"]]
    piece = rule["piece"]
    pieces = {p.name: p for p in learner.pieces}
    if piece not in pieces:
        raise KeyError(f"la règle cible la pièce {piece!r}, absente de {learner.name} ({sorted(pieces)})")
    without = dict(pieces[piece].without)
    n_abl = len(task.demand.ablations)
    family = assert_control_family(cells=n_abl * 1 * len(sweep))
    design = declare_design(
        question=rule.get("question", rule_name), replication_unit="seed", n_independent=len(seeds),
        links={"ablation->chute": "measured", "dose->acquisition": "measured", "sans_piece->chute": "measured",
               "analogue_bio": "inferred"},
        allow_inferred_reason="l'analogue biologique d'une pièce est une hypothèse portée par le registre (spec §2.6), jamais mesurée ici",
        cost_estimate=None, control_family=family)
    bayes = {a.name: measure_ablated_bayes_ceiling(task, a, n=4096, seed=seeds[0])
             for a in task.demand.ablations if a.site == "input"}
    clock = clock or time.monotonic
    # unité MESURÉE : un bras A complet sur le premier seed, si non fournie
    t0 = clock()
    first_arm = _run_arm(task, learner, seeds[0], n_agents, K, sweep[0], episodes, eval_batches, full_eval=True)
    unit = float(unit_s) if unit_s is not None else max(clock() - t0, 1e-6)
    projected = project_cost(unit, n_units=len(seeds) * len(ARMS), budget_s=float(budget_s), safety=3.0, label=out_name)
    db = {"seeds": seeds, "arms": {a: {"last": {}, "dose": {}} for a in ARMS},
          "eval": {"noop": {a: {} for a in ARMS}, "oracle": {}, "ablated": {a.name: {} for a in task.demand.ablations}, "control": {}},
          "abandoned": {a: [] for a in ARMS}}
    db["arms"]["A"].update(first={}, mid={})
    for a in task.demand.ablations:
        if a.site == "state":
            db["eval"]["control"][a.name] = {"intact": {}, "ablated": {}}

    def _store(seed, arm, res):
        s = str(seed)
        db["arms"][arm]["last"][s] = res["last"]
        db["arms"][arm]["dose"][s] = res["dose"]
        db["eval"]["noop"][arm][s] = res["noop"]
        if arm == "A":
            db["arms"]["A"]["first"][s], db["arms"]["A"]["mid"][s] = res["first"], res["mid"]
            db["eval"]["oracle"][s] = res["oracle"]
            for name, v in res["ablated"].items():
                db["eval"]["ablated"][name][s] = v
            for name, v in res["control"].items():
                db["eval"]["control"][name]["intact"][s] = v["intact"]
                db["eval"]["control"][name]["ablated"][s] = v["ablated"]

    _store(seeds[0], "A", first_arm)
    for seed in seeds:
        guard = CostGuard(budget_s=float(budget_s) / len(seeds), label=f"{out_name} seed {seed}", clock=clock)
        for arm in ARMS:
            if seed == seeds[0] and arm == "A":
                continue
            try:
                guard.tick()
                hyper = sweep[0] if arm in ("A", "A0", "D") else sweep[1]
                res = _run_arm(task, learner, seed, n_agents, K, hyper, episodes, eval_batches,
                               without=(without if arm in ("D", "D2") else None), reference=(arm == "A0"),
                               full_eval=(arm == "A"))
                _store(seed, arm, res)
            except CostExceeded as e:
                db["abandoned"][arm].append(seed)
                print(f"  seed {seed:>2} bras {arm}: ABANDONNE (cout wall-clock) : {e}")
    verdict = harness_verdict_lecture(db, rule)
    data = {"regime": {"task": task.regime(), "learner": {"name": learner.name, "family": learner.family,
                                                          "sweep": sweep, "piece": piece, "without": without,
                                                          "n_agents": n_agents, "episodes": episodes,
                                                          "eval_batches": eval_batches},
                       "seeds": seeds, "bayes_floors": bayes, "contract_task": contract_task,
                       "incapable_ceiling": rule.get("incapable_ceiling")},
            "design": design, "control_family": family, "preregistration": {"name": rule_name, "seal": prov.get("seal")},
            "provenance": prov, "db": db, "verdict": verdict,
            "cost": {"unit_s_measured": unit, "unit_s_given": unit_s, "projected_s": projected,
                     "actual_s": clock() - t0, "machine_load_note": "charge machine a noter dans le record (E12)"}}
    path = None
    if save:
        h = Harness(seed=seeds[0], name=out_name, with_db=False)
        path = h.save(data)
    return {"db": db, "verdict": verdict, "path": path, "cost": data["cost"]}
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_cell.py -q`
Expected: `5 passed` (le cas complet : 12 seeds × 5 bras × 40 épisodes du learner jouet, quelques secondes).

- [ ] **Step 5: Portes**

Run: `PYTHONIOENCODING=utf-8 python tools/check_control_family.py --only tools/harness/cell.py && PYTHONIOENCODING=utf-8 python tools/check_substrate_pinning.py --only tools/harness/cell.py && PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/harness/cell.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/harness/cell.py && PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_preregistration_guard.py -q`
Expected: quatre `OK` (le fichier importe `verify` par `from tools.preregister import`, appelle `verify(`, `declare_design(` et `provenance(` ; il ne contient PAS `make_population(`) et le test de garde vert.

- [ ] **Step 6: Préparer le commit** — `scratchpad/commit_msg_t6.txt` : `feat(harness): run_harness_cell -- cinq bras apparies par seed, eval du meme sujet (last/noop/ablations/controles/oracle), cout sur unite mesuree, abandon compte ; 5 cas par injection`. Fichiers : `tools/harness/cell.py tests/sandbox/test_harness_cell.py`.

---

### Task 7: Registre de pièces et contrat en prose

**Files:**
- Create: `src/seed_ai/harness_pieces.py`, `docs/REF/REF-HARNESS-PIECES.md`, `docs/REF/REF-HARNESS-CONTRACTS.md`
- Test: `tests/sandbox/test_harness_pieces.py`

**Interfaces:**
- Consumes: `Piece` (tâche 2).
- Produces: `PIECES: dict[str, Piece]` (les 11 lignes du spec §2.2, statut dans `in_repo_today`) ; `PIECE_STATUS: dict[str, str]` (`"R1" | "R2" | "attend" | "hors_v1" | "hors_registre"`) ; `check_pieces_registry(learners) -> None` (lève `KeyError` si un Learner cite une pièce absente du registre, `ValueError` si une pièce `absent` est référencée par un Learner).

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/sandbox/test_harness_pieces.py
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_learner import Piece  # noqa: E402
from src.seed_ai.harness_pieces import PIECES, PIECE_STATUS, check_pieces_registry  # noqa: E402


def test_registry_has_the_eleven_pieces_with_R1_marked():
    assert set(PIECES) >= {"bilinear", "recurrent_state", "bptt_credit", "td_critic", "condition_gate",
                           "warm_start_prior", "neuromod_plasticity", "frozen_llm_backbone",
                           "state_noise_regulator", "curiosity_intrinsic", "targeted_variation"}
    assert PIECE_STATUS["bilinear"] == "R1" and PIECE_STATUS["recurrent_state"] == "R1"
    for name, p in PIECES.items():
        assert p.analogue_solidity in ("solide", "moyenne", "faible", "aucune"), name
        assert p.without, name


def test_registry_refuses_a_learner_citing_an_unknown_or_absent_piece():
    class L:
        name = "x"
        pieces = (Piece("phlogiston", "", "", "aucune", None, "", {"x": True}, True, None, "absent"),)
    with pytest.raises(KeyError, match="phlogiston"):
        check_pieces_registry([L()])

    class M:
        name = "y"
        pieces = (PIECES["frozen_llm_backbone"],)
    with pytest.raises(ValueError, match="absent"):
        check_pieces_registry([M()])
```

- [ ] **Step 2: Lancer, vérifier l'échec** — `ModuleNotFoundError: src.seed_ai.harness_pieces`.

- [ ] **Step 3: Écrire `src/seed_ai/harness_pieces.py`** — un dict littéral de 11 `Piece(...)` recopiant la table du spec §2.2 colonne par colonne (`artificial_form` = fichier:ligne du spec ; `in_repo_today` = la colonne « déjà mesuré », ou `"absent"` pour `neuromod_plasticity` et `frozen_llm_backbone`) ; `PIECE_STATUS` = `{"bilinear": "R1", "recurrent_state": "R1", "bptt_credit": "R2", "td_critic": "attend", "condition_gate": "attend", "warm_start_prior": "attend", "neuromod_plasticity": "attend", "frozen_llm_backbone": "attend", "state_noise_regulator": "hors_v1", "curiosity_intrinsic": "hors_registre", "targeted_variation": "attend"}` ; puis :

```python
def check_pieces_registry(learners):
    """Toute pièce citée par un Learner existe au registre ; une pièce `absent` n'est citée par aucun Learner."""
    for lrn in learners:
        for p in lrn.pieces:
            if p.name not in PIECES:
                raise KeyError(f"{lrn.name} cite la pièce {p.name!r}, absente du registre")
            if PIECES[p.name].in_repo_today == "absent":
                raise ValueError(f"{lrn.name} cite {p.name!r}, marquée absent au registre : elle n'a pas de forme dans le dépôt")
```

`docs/REF/REF-HARNESS-PIECES.md` : frontmatter `id: REF-HARNESS-PIECES`, `type: REF`, `title`, puis la table du spec §2.2 telle quelle, avec la phrase de statut. `docs/REF/REF-HARNESS-CONTRACTS.md` : frontmatter `id: REF-HARNESS-CONTRACTS`, `type: REF`, puis les deux contrats en PROSE (ce que le prompt du proposeur citera en semaine 5) — recopier §2.1 du spec sans le code, avec les sept clauses de `assert_task_contract` et les huit de `assert_learner_contract`.

- [ ] **Step 4: Lancer, vérifier que ça passe** — `2 passed`. Puis `PYTHONIOENCODING=utf-8 python tools/check_record_links.py` → `Aucun nouveau` (les REF sont des ancrages structurels, jamais orphelins).

- [ ] **Step 5: Préparer le commit** — `scratchpad/commit_msg_t7.txt` : `docs(harness): registre de pieces (11 lignes, statut R1/R2/attend) + REF-HARNESS-PIECES + REF-HARNESS-CONTRACTS`. Fichiers : `src/seed_ai/harness_pieces.py tests/sandbox/test_harness_pieces.py docs/REF/REF-HARNESS-PIECES.md docs/REF/REF-HARNESS-CONTRACTS.md`.

---

### Task 8: Déclarations `CALIBRATED`, compteurs, et LE commit des tâches 1-7

La porte 2 couple un instrument et sa déclaration : elles partent dans le MÊME commit. Les tâches 1-7 ont préparé leurs fichiers ; cette tâche les committe ensemble, path-scoped, sur signal de robla.

**Files:**
- Modify: `tests/sandbox/test_instrument_calibration.py` (dicts `NOT_AN_INSTRUMENT` et `CALIBRATED`, LITTÉRAUX)
- Modify: `CLAUDE.md:31-33`, `docs/SDR/G2_agent_composes.md:59` (trois balises `count:instruments_*`)

- [ ] **Step 1: Snapshot d'autorat des fichiers partagés**

Run: `python -c "from tools.check_staged_authorship import snapshot; snapshot(['tests/sandbox/test_instrument_calibration.py', 'CLAUDE.md', 'docs/SDR/G2_agent_composes.md'], owner='harness-r1-t8')"`

- [ ] **Step 2: Ajouter les déclarations (Edit, ancres uniques ; le dict reste un littéral, `}` en colonne 0)**

Dans `NOT_AN_INSTRUMENT` :
```python
    "src/seed_ai/harness_learner.py::learn": "stub de PROTOCOL (LearnerInstance.learn, corps `...`) : declare la signature du contrat, n'apprend rien, ne rend rien ; les implementations (tabular.py::learn, connectome.py::learn) sont declarees CALIBRATED.",
```
Dans `CALIBRATED` (commentaire pointant le fichier de cas au-dessus de chaque entrée) :
```python
    # Harnais ADR-004 (2026-09-16). Cas dans tests/sandbox/test_harness_task.py.
    "src/seed_ai/harness_task.py::assert_task_contract": [
        "toy:passes", "no-nobite:raises", "biting-control:raises", "verifier-is-oracle:raises",
        "aliased-ablation:raises", "chance-as-ceiling:raises", "short-provenance:raises",
        "non-reproducible:raises", "state-without-control:raises"],
    # Cas dans tests/sandbox/test_harness_learner.py.
    "src/seed_ai/harness_learner.py::assert_learner_contract": [
        "counter:passes-L0-L7", "L0:max_K", "L2:REFERENCE_LEARNS", "L3:DEAD_LEARNER", "L4:VACUOUS_PIECE",
        "L5:aliasing", "L7:single-sweep"],
    # Cas dans tests/sandbox/test_harness_verdict.py (branches dans l'ORDRE 2.3-b).
    "src/seed_ai/harness_verdict.py::harness_verdict_lecture": [
        "cellA:PIECE_PARTIAL", "cellB:NECESSARY", "NOT_DEMANDED", "DEMAND_WITHIN_NOISE", "INCONCLUSIVE_SPECIFICITY",
        "NOT_ACQUIRED:dose+saturation", "INDETERMINE_HARNAIS:prior-solves", "INDETERMINE_HARNAIS:oracle",
        "LR_ARTIFACT:necessity", "LR_ARTIFACT:acquisition", "INDETERMINE_HARNAIS:reference-collapsed", "PIECE_NOT_NECESSARY:both-at-ceiling",
        "INCOMPLET", "INCONCLUSIVE_N", "nan:raises", "boundary:<=-is-necessary"],
    "src/seed_ai/harness_verdict.py::measure_noise_floor": ["band:min-max", "empty:raises", "per-arm:weak-arm-band"],
    "src/seed_ai/harness_verdict.py::measure_ablated_bayes_ceiling": ["composition:certified-1/K"],
    # Cas dans tests/sandbox/test_harness_cell.py (injection, sentinelle, horloge factice).
    "tools/harness/cell.py::run_harness_cell": [
        "guard-before-world:task-contract", "guard-before-world:tampered", "guard-before-world:cost",
        "injection:unite=seed", "injection:reference-dose-matched", "abandon:INCONCLUSIVE_N"],
    # Cas dans tests/sandbox/test_harness_tabular.py.
    "tools/harness/learners/tabular.py::learn": ["table:learns", "reference:no-update", "without-table:chance", "state_reset:chance"],
```
Ajouter dans `tests/sandbox/test_harness_verdict.py` le cas nommé `composition:certified-1/K` :
```python
def test_measure_ablated_bayes_ceiling_certifies_the_declared_floor():
    from src.seed_ai.harness_verdict import measure_ablated_bayes_ceiling
    from tools.harness.tasks.composition import CompositionTask
    task = CompositionTask(K=6)
    abl = [a for a in task.demand.ablations if a.name == "permute_key"][0]
    out = measure_ablated_bayes_ceiling(task, abl, n=4096, seed=0)
    assert out["certified"] is True and out["declared"] == pytest.approx(1 / 6) and abs(out["measured"] - 1 / 6) <= 2 * out["se"]
```

- [ ] **Step 3: Vérifier la porte 2 et recomputer les compteurs**

Run: `PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py --report | grep -i "harness\|REFUS\|detect"`
Expected: chaque instrument du harnais `OK`, AUCUNE ligne `REFUSEE`, et la ligne de compte (`N détectés / M calibrés / 2 non calibrés`). Reporter N et M dans `CLAUDE.md:31-33` et `docs/SDR/G2_agent_composes.md:59` — le chiffre DANS la phrase ET dans la balise (`**N détectés** <!-- count:instruments_detectes=N -->`). Puis : `PYTHONIOENCODING=utf-8 python tools/check_synthesis_counts.py` → `OK : aucun compte publié n'est périmé.`

- [ ] **Step 4: Suite complète des tests du harnais + portes sur l'ensemble**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_task.py tests/sandbox/test_harness_learner.py tests/sandbox/test_harness_composition.py tests/sandbox/test_harness_tabular.py tests/sandbox/test_harness_verdict.py tests/sandbox/test_harness_cell.py tests/sandbox/test_harness_pieces.py -q`
Expected: `~48 passed`. Puis `verify([...], owner='harness-r1-t8')` sur les trois fichiers partagés.

- [ ] **Step 5: Commit unique, path-scoped, sur signal de robla**

Message `scratchpad/commit_msg_t8.txt` : `feat(harness): semaine 1 -- contrats Task/Learner, verdict pur a trois conditions, runner de cellule, CompositionTask portee, TabularLearner de verite-terrain, registre de pieces ; 7 instruments calibres (~48 cas), compteurs recomputes`.
Run: `git add -- src/seed_ai/harness_task.py src/seed_ai/harness_learner.py src/seed_ai/harness_verdict.py src/seed_ai/harness_pieces.py tools/harness/tasks/composition.py tools/harness/learners/tabular.py tools/harness/cell.py tests/sandbox/test_harness_task.py tests/sandbox/test_harness_learner.py tests/sandbox/test_harness_composition.py tests/sandbox/test_harness_tabular.py tests/sandbox/test_harness_verdict.py tests/sandbox/test_harness_cell.py tests/sandbox/test_harness_pieces.py tests/sandbox/test_instrument_calibration.py docs/REF/REF-HARNESS-PIECES.md docs/REF/REF-HARNESS-CONTRACTS.md CLAUDE.md docs/SDR/G2_agent_composes.md && PYTHONIOENCODING=utf-8 git commit -F scratchpad/commit_msg_t8.txt -- <les mêmes chemins>`
Expected: 17 portes vertes ; lire le compte de suppressions (attendu : quelques lignes sur les trois fichiers partagés, ZÉRO ailleurs). ⚠️ Si une autre session a un hunk non committé dans `test_instrument_calibration.py`/`CLAUDE.md`, `verify` le dit : passer par un index temporaire (script `commit_insert_block.py` du scratchpad, adapté en REMPLACEMENT d'ancres : `BLOCK_EDITS`).

---

### Task 9: `ConnectomeLearner` — adaptateur unique vers `make_population`, bit-identité de la cellule A

**Files:**
- Create: `tools/harness/learners/connectome.py`
- Test: `tests/sandbox/test_harness_connectome.py` (torch, `@pytest.mark.slow` pour la bit-identité)
- Modify: `tests/sandbox/test_instrument_calibration.py` (`"tools/harness/learners/connectome.py::learn"`), compteurs (même procédure qu'en tâche 8)

**Interfaces:**
- Consumes: `src.agents.backend.make_population(agents, backend="torch")`, `src.agents.mamba_agent.MambaAgent()` (I=59, O=108, N=172 ; tire `W` sur le rng GLOBAL numpy), `src.agents.backend_torch.TorchPopulationModel` (drapeaux de CLASSE `CONDITION_GATE`, `GATE_TARGET`, `BILINEAR`, `BILINEAR_RANK` relus à chaque `_step` ; `forward(obs) -> (logits VUE de H (n, 108), 0)` ; `imitate_episode_bptt(obs_seq, target_moves_seq, truncate_window=None, mask_seq=None, n_classes=None)` ; `pop.opt` remplacé par `torch.optim.Adam`) ; `PIECES` (tâche 7 : `bilinear.without == {"bilinear": False}`, `recurrent_state.without == {"feedforward": True}`, `bptt_credit.without == {"truncate": True}`).
- Produces: `ConnectomeLearner(credit="supervised", rank=16, lrs=(0.02, 0.002), n_classes=None)` ; `sweep() -> [{"lr", "rank", "n_classes", "credit"}, ...]` ; `build(seed, n, obs_dim=59, K<=8, hyper, without, reference)` → `_ConnectomeInstance` qui POSE les drapeaux et ne les RESTAURE qu'à `close()` (la dernière instance ouverte restaure l'état d'origine ; deux instances ouvertes à drapeaux DIFFÉRENTS → `RuntimeError`) ; `learn` compte la dose EN LIGNE (Σ|Δθ| sur W, U, V, W_bl après `opt.step`) ; `ablate_state(state, "state_reset")` → zéros.

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/sandbox/test_harness_connectome.py
"""Adaptateur connectome : contrat L0-L7, bit-identité de la cellule A (seed 0 : 0,932812511920929 / 0,27031248807907104,
results bilinear_composition.json), régime de la cellule B (n_classes=6 : 0,932812511920929 au seed 0), référence lr=0."""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("torch")

from src.paths import results_file  # noqa: E402
from src.seed_ai.harness_learner import assert_learner_contract  # noqa: E402
from tools.harness.cell import _run_arm  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402

HYPER_A = {"lr": 0.02, "rank": 16, "n_classes": None, "credit": "supervised"}
HYPER_B = {"lr": 0.002, "rank": 16, "n_classes": 6, "credit": "supervised"}


def test_connectome_passes_the_learner_contract():
    out = assert_learner_contract(ConnectomeLearner(), CompositionTask(K=6, same_tick=False), seed=0)
    assert out["n_pieces"] == 3 and out["reference_dparam"] == 0.0


def test_two_open_instances_with_different_flags_are_refused():
    lrn, task = ConnectomeLearner(), CompositionTask(K=6)
    a = lrn.build(0, 4, task.obs_dim, 6, HYPER_A)
    try:
        with pytest.raises(RuntimeError, match="drapeaux"):
            lrn.build(0, 4, task.obs_dim, 6, HYPER_A, without={"bilinear": False})
    finally:
        a.close()


@pytest.mark.slow
def test_cell_A_seed0_is_bit_identical_to_the_published_json():
    pub = json.load(open(results_file("bilinear_composition.json"), encoding="utf-8"))["decisive_same_tick_supervised"]["per_seed"]
    task, lrn = CompositionTask(K=6, same_tick=True), ConnectomeLearner()
    bil = _run_arm(task, lrn, 0, 16, 6, HYPER_A, 300, 40, full_eval=True)
    assert bil["last"] == pub["bilinear"][0]                       # 0.932812511920929, EXACT
    plain = _run_arm(task, lrn, 0, 16, 6, HYPER_A, 300, 40, without={"bilinear": False})
    assert plain["last"] == pub["plain"][0]                        # 0.27031248807907104, EXACT
    ref = _run_arm(task, lrn, 0, 16, 6, HYPER_A, 300, 40, reference=True)
    assert ref["dose"]["updates"] == 0 and ref["dose"]["calls"] == 300
    assert abs(ref["last"] - 0.16875000298023224) < 1e-9            # mesuré le 2026-09-16 (même nombre d'épisodes)
    assert bil["oracle"] == 1.0 and 0.9 < bil["noop"] < 1.0 and bil["ablated"]["permute_key"] < 0.3


@pytest.mark.slow
def test_cell_B_regime_reproduces_retain_compose_at_seed0():
    task, lrn = CompositionTask(K=6, same_tick=False), ConnectomeLearner()
    res = _run_arm(task, lrn, 0, 16, 6, HYPER_B, 600, 40, full_eval=True)
    assert res["last"] == 0.932812511920929                          # retain_compose_lr_replication lr_0.002 learned[0]
    assert res["ablated"]["state_reset"] < 0.3
    assert 0.2 < res["control"]["state_reset"]["intact"]              # le split control est PUBLIÉ, pas supposé
```

- [ ] **Step 2: Lancer, vérifier l'échec** — `ModuleNotFoundError: tools.harness.learners.connectome`.

- [ ] **Step 3: Écrire `tools/harness/learners/connectome.py`**

```python
"""
tools/harness/learners/connectome.py — ConnectomeLearner : l'adaptateur UNIQUE vers make_population(backend="torch")
(frontière population, ADR-003). Il rejoue EXACTEMENT la séquence de tools/bilinear_composition_probe._train_eval_one
(np.random.seed(seed) AVANT les MambaAgent() ; torch.manual_seed(seed) AVANT make_population ; drapeaux de classe
posés AVANT ; Adam sur [W] + [U, V, W_bl] présents ; rng des opérandes seed+1 tenu par le runner) : c'est ce qui rend
la cellule A bit-identique à results bilinear_composition.json.

Piège E5 : type(self).BILINEAR est relu à CHAQUE _step (backend_torch.py:128) — les drapeaux restent posés tant
qu'une instance est ouverte ; close() de la DERNIÈRE instance restaure l'état d'origine ; ouvrir une instance à
drapeaux DIFFÉRENTS d'une instance ouverte est refusé.
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness_learner import Dose  # noqa: E402
from src.seed_ai.harness_pieces import PIECES  # noqa: E402

_OPEN = []            # instances ouvertes (état global du process)
_ORIGINAL = {"flags": None}


class _ConnectomeInstance:
    def __init__(self, seed, n, K, hyper, without, reference):
        import torch
        from src.agents.backend import make_population
        from src.agents.backend_torch import TorchPopulationModel
        from src.agents.mamba_agent import MambaAgent
        cfg = {"bilinear": True, "feedforward": False, "truncate": False}
        cfg.update(without or {})
        flags = (False, None, bool(cfg["bilinear"]), int(hyper.get("rank", 16)))
        for other in _OPEN:
            if other._flags != flags:
                raise RuntimeError(f"une instance connectome ouverte porte d'autres drapeaux {other._flags} != {flags} (état global E5) : close() d'abord")
        if not _OPEN:
            _ORIGINAL["flags"] = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
                                  TorchPopulationModel.BILINEAR, TorchPopulationModel.BILINEAR_RANK)
        TorchPopulationModel.CONDITION_GATE = False
        TorchPopulationModel.GATE_TARGET = None
        TorchPopulationModel.BILINEAR = flags[2]
        TorchPopulationModel.BILINEAR_RANK = flags[3]
        self._flags, self._TPM, self._torch = flags, TorchPopulationModel, torch
        self.K, self.n = int(K), int(n)
        self.feedforward, self.truncate = bool(cfg["feedforward"]), bool(cfg["truncate"])
        self.n_classes, self.credit = hyper.get("n_classes"), hyper.get("credit", "supervised")
        if self.credit != "supervised":
            raise NotImplementedError("crédit REINFORCE : pièce optionnelle, hors R1")
        np.random.seed(int(seed))                     # MambaAgent() tire W sur le rng GLOBAL (29 584 tirages/agent)
        torch.manual_seed(int(seed))                  # U, V, W_bl dans cet ordre, ssi BILINEAR
        self.pop = make_population([MambaAgent() for _ in range(self.n)], backend="torch")
        self._params = [self.pop.W] + [p for p in (self.pop.U, self.pop.V, self.pop.W_bl) if p is not None]
        self.pop.opt = torch.optim.Adam([self.pop.W] + [p for p in (self.pop.U, self.pop.V, self.pop.W_bl) if p is not None],
                                        lr=(0.0 if reference else float(hyper["lr"])))
        self._dose = Dose(unit="gradient_updates")
        _OPEN.append(self)

    def init_state(self):
        return self._torch.zeros((self.n, self.pop.N))

    def act(self, obs_t, state):
        if self.feedforward:
            state = self._torch.zeros_like(state)
        self.pop.H = state
        logits, _ = self.pop.forward(obs_t)           # met à jour pop.H ; logits = VUE de H -> copie
        return np.array(np.asarray(logits)[:, :self.K], copy=True), self.pop.H.detach().clone()

    def learn(self, ep, actions, hits):
        self._dose.calls += 1
        self._dose.episodes_seen += ep.n
        before = [p.detach().clone() for p in self._params]
        tgt = np.asarray(ep.target, dtype=np.int64)
        targets = [tgt] if ep.T == 1 else [np.zeros(ep.n, dtype=np.int64)] * (ep.T - 1) + [tgt]
        mask = None if ep.mask_seq is None else [np.asarray(m, dtype=np.float32) for m in ep.mask_seq]
        self.pop.imitate_episode_bptt(list(ep.obs_seq), targets, mask_seq=mask, n_classes=self.n_classes,
                                      truncate_window=(1 if self.truncate else None))
        d = float(sum((p.detach() - b).abs().sum().item() for p, b in zip(self._params, before)))
        self._dose.updates += int(d > 0.0)
        self._dose.dparam_abs_sum = (self._dose.dparam_abs_sum or 0.0) + d
        return self._dose

    def ablate_state(self, state, name):
        if name != "state_reset":
            raise KeyError(f"ablation d'état inconnue : {name!r}")
        return self._torch.zeros_like(state)

    def state_dict(self):
        return {"W": self.pop.W.detach().cpu().numpy(),
                "U": None if self.pop.U is None else self.pop.U.detach().cpu().numpy(),
                "V": None if self.pop.V is None else self.pop.V.detach().cpu().numpy(),
                "W_bl": None if self.pop.W_bl is None else self.pop.W_bl.detach().cpu().numpy(),
                "opt": self.pop.opt.state_dict()}

    def dose(self):
        return self._dose

    def close(self):
        if self in _OPEN:
            _OPEN.remove(self)
        if not _OPEN and _ORIGINAL["flags"] is not None:
            (self._TPM.CONDITION_GATE, self._TPM.GATE_TARGET, self._TPM.BILINEAR, self._TPM.BILINEAR_RANK) = _ORIGINAL["flags"]
            _ORIGINAL["flags"] = None


class ConnectomeLearner:
    name, family, max_K = "connectome_torch", "connectome_torch", 8
    entry_task = "composition_same_tick_K6 -- billet PAYE : bilinear_composition.json (results), 0,932 vs 0,271, n=12"
    supported_state_ablations = frozenset({"state_reset"})

    def __init__(self, credit="supervised", rank=16, lrs=(0.02, 0.002), n_classes=None):
        self.pieces = (PIECES["bilinear"], PIECES["recurrent_state"], PIECES["bptt_credit"])
        self.credit, self.rank, self.lrs, self.n_classes = credit, int(rank), tuple(float(x) for x in lrs), n_classes

    def sweep(self):
        return [{"lr": lr, "rank": self.rank, "n_classes": self.n_classes, "credit": self.credit} for lr in self.lrs]

    def build(self, seed, n, obs_dim, K, hyper, *, without=None, reference=False):
        if int(obs_dim) != 59:
            raise ValueError(f"obs_dim={obs_dim} : le connectome par défaut a I=59 entrées (MambaAgent)")
        if int(K) > self.max_K:
            raise ValueError(f"K={K} > max_K={self.max_K} (_MOVE_LOGITS)")
        return _ConnectomeInstance(seed, n, K, hyper, without or {}, reference)
```

- [ ] **Step 4: Lancer les tests (non lents d'abord, puis lents)**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_connectome.py -q -m "not slow"` → `2 passed` ; puis `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_connectome.py -q -m slow` → `2 passed` (≈ 30-60 s : 3 bras à 300 ép. + 1 bras à 600 ép.). Si la bit-identité échoue : comparer pas à pas avec `_train_eval_one` (ordre np.random.seed / torch.manual_seed / drapeaux / make_population / Adam), puis le rng des opérandes (key PUIS q, éval sur le rng CONTINUÉ) — ne rien « ajuster » à la main.

- [ ] **Step 5: Portes** — `check_substrate_pinning.py --only tools/harness/learners/connectome.py` (assignation `.BILINEAR =` présente, Adam mentionne U/V/W_bl) → `OK` ; `check_data_paths.py --only ...` → `OK` (aucun littéral `results/`) ; déclaration `"tools/harness/learners/connectome.py::learn": ["supervised:dose-counted", "reference:dparam=0", "truncate:variant", "cellA:bit-identical"]` + compteurs, comme en tâche 8 (snapshot/verify).

- [ ] **Step 6: Commit (sur signal)** — `feat(harness): ConnectomeLearner -- adaptateur unique vers make_population, bit-identite de la cellule A (seed 0 EXACT), regime B (n_classes=6), reference lr=0 a dose appariee`. Fichiers : `tools/harness/learners/connectome.py tests/sandbox/test_harness_connectome.py tests/sandbox/test_instrument_calibration.py CLAUDE.md docs/SDR/G2_agent_composes.md`.

---

### Task 10: Smoke R1 (3 seeds) puis scellement de `HARNESS-R1` — semaine 2

Le second lr de la cellule B sort d'un SMOKE publié, jamais importé d'un autre régime (E8). Le smoke mesure aussi
l'unité de coût par bras et le plancher de bruit, qui entrent dans la règle.

**Files:**
- Create: `tools/harness/smoke_r1.py`, `tools/harness/seal_r1.py`
- Create (par `seal_r1.py`): `docs/preregistrations/HARNESS-R1.json`
- Test: `tests/sandbox/test_harness_seal_r1.py`

**Interfaces:**
- Consumes: `_run_arm` (tâche 6), `ConnectomeLearner`, `CompositionTask`, `Harness(with_db=False).save`, `tools.preregister.preregister`, `src.seed_ai.harness_verdict.BRANCHES`.
- Produces: `results/harness_r1_smoke_0.json` (via `Harness`, `name="harness_r1_smoke"`, seed 0) avec `data = {"A": {lr: {seed: acc}}, "A_plain", "A_ref", "Aprime", "B": {lr: {seed: acc}}, "B_ref", "unit_s": {...}, "noise": {...}}` ; `build_rule_r1(smoke: dict) -> dict` (pure, testable) ; la règle scellée.

- [ ] **Step 1: Test de la fonction pure `build_rule_r1`**

```python
# tests/sandbox/test_harness_seal_r1.py
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.seed_ai.harness_verdict import BRANCHES  # noqa: E402
from tools.harness.seal_r1 import build_rule_r1  # noqa: E402


def _smoke(b_med=None):
    b_med = b_med or {"0.002": 0.92, "0.001": 0.88, "0.0005": 0.70}
    return {"A": {"0.02": {"0": 0.93, "1": 0.92, "2": 0.94}}, "A_ref": {"0": 0.17, "1": 0.20, "2": 0.18},
            "B": {lr: {"0": m, "1": m, "2": m} for lr, m in b_med.items()}, "B_ref": {"0": 0.17, "1": 0.19, "2": 0.18},
            "unit_s": {"A": 3.5, "Aprime": 1.8, "B": 7.0}}


def test_second_lr_of_B_is_the_best_measured_alternative_above_the_bar():
    rule = build_rule_r1(_smoke())
    assert rule["cellules"]["B"]["sweep"] == [{"lr": 0.002, "rank": 16, "n_classes": 6, "credit": "supervised"},
                                              {"lr": 0.001, "rank": 16, "n_classes": 6, "credit": "supervised"}]


def test_seal_refuses_when_no_alternative_lr_clears_the_bar():
    with pytest.raises(ValueError, match="aucun second pas"):
        build_rule_r1(_smoke({"0.002": 0.92, "0.001": 0.20, "0.0005": 0.19}))


def test_rule_has_exhaustive_discrimination_backticked_dv_and_predictions():
    rule = build_rule_r1(_smoke())
    assert set(rule["discrimination"]) == set(BRANCHES) and "AUTRE" in rule["discrimination"]
    assert "`hits`" in rule["dv_primaire"] and "`dose.updates`" in rule["dv_primaire"]
    assert rule["predictions_chiffrees_AVANT_le_run"]["A"].startswith("PIECE_PARTIAL")
    assert rule["predictions_chiffrees_AVANT_le_run"]["B"].startswith("DEMANDED_ACQUIRED_NECESSARY")
    assert rule["budget_s"] == pytest.approx(3.0 * (3.5 + 1.8 + 7.0) * 12 * 5, rel=0.01)
```

- [ ] **Step 2: Écrire `tools/harness/smoke_r1.py`**

```python
"""
tools/harness/smoke_r1.py — SMOKE de la famille HARNESS-R1 : 3 seeds, sans bail. Mesure (a) la bit-identité de A au
seed 0, (b) le candidat second lr de B parmi {0.001, 0.0005} à n_classes=6, (c) l'unité de coût par bras, (d) une
première bande no-op. Sortie : results harness_r1_smoke_0.json (Harness, sans DB). Usage : PYTHONIOENCODING=utf-8
python -m tools.harness.smoke_r1
"""
import os
import sys
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.harness import Harness  # noqa: E402
from tools.harness.cell import _run_arm  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402

SEEDS = (0, 1, 2)
H_A = {"lr": 0.02, "rank": 16, "n_classes": None, "credit": "supervised"}


def _hb(lr):
    return {"lr": lr, "rank": 16, "n_classes": 6, "credit": "supervised"}


def main():
    lrn = ConnectomeLearner()
    A, Ap, B = CompositionTask(K=6, same_tick=True), CompositionTask(K=6, same_tick=True, kind="recall"), CompositionTask(K=6, same_tick=False)
    out = {"A": {"0.02": {}}, "A_plain": {}, "A_ref": {}, "Aprime": {}, "Aprime_plain": {}, "B": {}, "B_ref": {},
           "noise": {}, "unit_s": {}}
    t = {}
    for s in SEEDS:
        t0 = time.perf_counter()
        r = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, full_eval=True)
        t.setdefault("A", []).append(time.perf_counter() - t0)
        out["A"]["0.02"][str(s)], out["noise"][str(s)] = r["last"], r["last"] / r["noop"]
        out["A_plain"][str(s)] = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, without={"bilinear": False})["last"]
        out["A_ref"][str(s)] = _run_arm(A, lrn, s, 16, 6, H_A, 300, 40, reference=True)["last"]
        t0 = time.perf_counter()
        out["Aprime"][str(s)] = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40)["last"]
        t.setdefault("Aprime", []).append(time.perf_counter() - t0)
        out["Aprime_plain"][str(s)] = _run_arm(Ap, lrn, s, 16, 6, H_A, 150, 40, without={"bilinear": False})["last"]
        for lr in (0.002, 0.001, 0.0005):
            t0 = time.perf_counter()
            out["B"].setdefault(str(lr), {})[str(s)] = _run_arm(B, lrn, s, 16, 6, _hb(lr), 600, 40)["last"]
            t.setdefault("B", []).append(time.perf_counter() - t0)
        out["B_ref"][str(s)] = _run_arm(B, lrn, s, 16, 6, _hb(0.002), 600, 40, reference=True)["last"]
        print(f"seed {s}: A {out['A']['0.02'][str(s)]:.4f} plain {out['A_plain'][str(s)]:.4f} ref {out['A_ref'][str(s)]:.4f} | "
              f"B " + " ".join(f"{lr}:{out['B'][str(lr)][str(s)]:.3f}" for lr in (0.002, 0.001, 0.0005)))
    out["unit_s"] = {k: float(np.median(v)) for k, v in t.items()}
    assert out["A"]["0.02"]["0"] == 0.932812511920929, "bit-identite de la cellule A PERDUE au seed 0"
    assert out["A_plain"]["0"] == 0.27031248807907104, "bit-identite du plain PERDUE au seed 0"
    h = Harness(seed=0, name="harness_r1_smoke", with_db=False)
    print("->", h.save(out))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lancer le smoke** — `PYTHONIOENCODING=utf-8 python -m tools.harness.smoke_r1` (≈ 3 seeds × (3 bras A + 2 A' + 4 B) ≈ 5-8 min). Expected : les deux assertions de bit-identité passent ; B à 0,002 ≈ 0,90-0,93 ; publier les chiffres dans le message de commit.

- [ ] **Step 4: Écrire `tools/harness/seal_r1.py`**

```python
"""
tools/harness/seal_r1.py — Scelle HARNESS-R1 à partir du SMOKE (jamais de chiffre importé d'un autre régime, E8).
Usage : PYTHONIOENCODING=utf-8 python -m tools.harness.seal_r1 [chemin du smoke]
"""
import json
import os
import statistics
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file  # noqa: E402
from src.seed_ai.harness_verdict import BRANCHES  # noqa: E402
from tools.preregister import preregister  # noqa: E402

N_SEEDS, N_ARMS = 12, 5


def _hyper(lr, n_classes):
    return {"lr": lr, "rank": 16, "n_classes": n_classes, "credit": "supervised"}


def build_rule_r1(smoke: dict) -> dict:
    """Pure : choisit le second lr de B = le meilleur des lr ≠ 0,002 dont la médiane dépasse la barre
    (référence + 0,05) ; lève s'il n'y en a aucun (la cellule B ne serait pas scellable)."""
    ref_b = statistics.median(float(v) for v in smoke["B_ref"].values())
    bar_b = ref_b + 0.05
    cands = {float(lr): statistics.median(float(v) for v in col.values()) for lr, col in smoke["B"].items() if float(lr) != 0.002}
    ok = {lr: m for lr, m in cands.items() if m > bar_b}
    if not ok:
        raise ValueError(f"aucun second pas de B ne franchit la barre {bar_b:.3f} : {cands}")
    lr2 = max(ok, key=ok.get)
    unit = smoke["unit_s"]
    budget = 3.0 * (float(unit["A"]) + float(unit["Aprime"]) + float(unit["B"])) * N_SEEDS * N_ARMS
    common = {"n_floor": N_SEEDS, "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5,
              "alive_margin": 0.05, "matched_sham": None}
    ceiling = {"value": 34 / 36, "provenance": "forme close plain 34/36, tools/plain_substrate_ceiling.py:155, MINORANT jamais PROUVE", "proven": False}
    abl_1 = [{"name": "permute_key", "site": "input", "must_bite": True}, {"name": "permute_query", "site": "input", "must_bite": True},
             {"name": "inject_distractor_slot", "site": "input", "must_bite": False}]
    abl_rec = [dict(abl_1[0]), {"name": "permute_query", "site": "input", "must_bite": False}, abl_1[2]]
    abl_2 = abl_1 + [{"name": "state_reset", "site": "state", "must_bite": True}]
    floors = {"permute_key": 1 / 6, "permute_query": 1 / 6, "state_reset": 1 / 6}
    cells = {
        "A": dict(common, task="composition_same_tick_K6", learner="connectome_torch", piece="bilinear", episodes=300,
                  sweep=[_hyper(0.02, None), _hyper(0.002, None)], ablations=abl_1, bayes_floors=floors, incapable_ceiling=ceiling),
        "Aprime": dict(common, task="recall_same_tick_K6", learner="connectome_torch", piece="bilinear", episodes=150,
                       sweep=[_hyper(0.02, None), _hyper(0.002, None)], ablations=abl_rec, bayes_floors={"permute_key": 1 / 6}, incapable_ceiling=None),
        "B": dict(common, task="composition_two_step_K6", learner="connectome_torch", piece="recurrent_state", episodes=600,
                  sweep=[_hyper(0.002, 6), _hyper(lr2, 6)], ablations=abl_2, bayes_floors=floors, incapable_ceiling=None),
    }
    return {
        "question": "Le harnais a trois conditions rend-il, sur trois cellules PORTEES a reponse connue, PARTIAL (A), NOT_NECESSARY (A') et NECESSARY (B) ?",
        "design": "unite = seed, n = 12 (seeds 0-11), 5 bras apparies par seed (A, A0, A2, D, D2), eval du meme sujet, plancher de bruit par second rng",
        "cellules": cells,
        "dv_primaire": "`hits` par seed et par bras ; `ratio_within` par ablation ; `sep_ref` (mediane A - mediane A0) ; `dose.updates` par bras ; `noise_band` ; `closure` (E19)",
        "discrimination": {b: "voir src/seed_ai/harness_verdict.py::BRANCHES, ordre impose" for b in BRANCHES},
        "regle_de_lecture_continue": "ORDRE IMPOSE : " + " -> ".join(BRANCHES),
        "predictions_chiffrees_AVANT_le_run": {
            "A": "PIECE_PARTIAL : chute >= 3x hors bande, plain ~0,27 > barre ~0,22 ; bit-identite seed 0 (0,9328125 / 0,2703125) ; bar_status CEILING_ABOVE_BAR (0,944 > barre)",
            "Aprime": "PIECE_NOT_NECESSARY : plain = bilineaire = 1,0 (mesure seeds 0-2 au smoke) ; acquisition ACQUIRED",
            "B": f"DEMANDED_ACQUIRED_NECESSARY : intact ~0,92 a lr 0,002 (smoke), state_reset -> ~1/6, sans recurrent_state (feedforward) -> ~1/6 ; second pas {lr2} (mediane smoke {ok[lr2]:.3f})"},
        "clause_E19": "toute cellule non NECESSARY passe assert_verdict_invariant_to_optimizer sur les deux pas du sweep ; closure > 2/3 = LR_ARTIFACT, pas un verdict",
        "smoke": {"B_medians_by_lr": {str(k): v for k, v in cands.items()}, "B_ref_median": ref_b, "unit_s": unit},
        "budget_s": budget,
        "cout": f"unites mesurees au smoke (s/bras) : {unit} ; budget = 3 x somme x 12 seeds x 5 bras = {budget/60:.0f} min ; sans bail kuzu",
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    path = argv[0] if argv else results_file("harness_r1_smoke_0.json")
    smoke = json.load(open(path, encoding="utf-8"))["data"]
    rule = build_rule_r1(smoke)
    print("->", preregister("HARNESS-R1", rule))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Lancer le test puis sceller** — `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_harness_seal_r1.py -q` → `3 passed` ; `PYTHONIOENCODING=utf-8 python -m tools.harness.seal_r1` → `docs/preregistrations/HARNESS-R1.json` ; `PYTHONIOENCODING=utf-8 python tools/check_preregistration_applied.py` → la famille HARNESS-R1 a des grandeurs (pas encore de record : « sans record » toléré jusqu'à la tâche 11).

- [ ] **Step 6: Commit (sur signal)** — `feat(harness): HARNESS-R1 -- smoke 3 seeds (bit-identite A seed 0 confirmee, second lr de B mesure), regle SCELLEE avant toute cellule`. Fichiers : `tools/harness/smoke_r1.py tools/harness/seal_r1.py tests/sandbox/test_harness_seal_r1.py docs/preregistrations/HARNESS-R1.json results/harness_r1_smoke_0.json`.

---

### Task 11: Run R1 (n = 12), record `EDR-HARNESS-R1`, revue adversariale — semaine 3

**Files:**
- Create: `tools/harness/run_r1.py`
- Create: `docs/EDR/HARNESS-R1_Three_Ported_Cells_Calibrate_The_Three_Condition_Harness.md`
- Modify: `docs/roadmap/SCIENCE.md:11` (`records_total` +1), `docs/roadmap/PRIORITES_ET_DETTES.md` (dettes trouvées en passant, avec preuve)
- Create (par le run): `results/harness_r1_A_0.json`, `results/harness_r1_Aprime_0.json`, `results/harness_r1_B_0.json`

- [ ] **Step 1: Écrire `tools/harness/run_r1.py`**

```python
"""
tools/harness/run_r1.py — Exécute les trois cellules de HARNESS-R1 (n = 12) via run_harness_cell, sous la règle
SCELLÉE, et imprime les verdicts. Reprise : une cellule dont le JSON existe et est suivi par git est détournée en
_rerun par Harness (P2.61). Usage : PYTHONIOENCODING=utf-8 python -m tools.harness.run_r1 [A|Aprime|B ...]
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.harness.cell import run_harness_cell  # noqa: E402
from tools.harness.learners.connectome import ConnectomeLearner  # noqa: E402
from tools.harness.tasks.composition import CompositionTask  # noqa: E402
from tools.preregister import verify  # noqa: E402

TASKS = {"A": lambda: CompositionTask(K=6, same_tick=True),
         "Aprime": lambda: CompositionTask(K=6, same_tick=True, kind="recall"),
         "B": lambda: CompositionTask(K=6, same_tick=False)}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    rule = verify("HARNESS-R1")
    for cell in (argv or ("A", "Aprime", "B")):
        c = rule["cellules"][cell]
        lrn = ConnectomeLearner(lrs=tuple(h["lr"] for h in c["sweep"]), n_classes=c["sweep"][0]["n_classes"])
        out = run_harness_cell(TASKS[cell](), lrn, "HARNESS-R1", seeds=range(12), episodes=int(c["episodes"]),
                               out_name=f"harness_r1_{cell}", budget_s=float(rule["budget_s"]))
        print(f"[{cell}] verdict = {out['verdict']['verdict']}  ({out['verdict']['why']})  ->  {out['path']}")


if __name__ == "__main__":
    main()
```

⚠️ `run_harness_cell` lit `rule["piece"]`, `rule["sweep"]`, `rule["ablations"]`… au NIVEAU RACINE de la règle passée à `harness_verdict_lecture`. Dans `run_r1.py`, passer `rule["cellules"][cell]` fusionnée : ajouter dans `cell.py` un paramètre `rule_path=None` (liste de clés, ex. `["cellules", "B"]`) qui sélectionne la sous-règle après `verify(...)` — le sceau reste vérifié sur la règle ENTIÈRE. Écrire le cas de test correspondant dans `test_harness_cell.py` (`rule_path` absent → règle racine, présent → sous-dict ; clé absente → `KeyError` avant tout build).

- [ ] **Step 2: Lancer** — `PYTHONIOENCODING=utf-8 python -m tools.harness.run_r1` (≈ 12 seeds × 5 bras × (3,5 + 1,8 + 7) s ≈ 25 min, machine au repos ; noter la charge, E12). Expected : `[A] PIECE_PARTIAL`, `[Aprime] PIECE_NOT_NECESSARY`, `[B] DEMANDED_ACQUIRED_NECESSARY`. Toute autre issue est GRAVÉE telle quelle avec sa branche — pas de relance « pour voir ».

- [ ] **Step 3: Écrire le record** — frontmatter exact :

```yaml
---
id: EDR-HARNESS-R1
type: EDR
title: Trois cellules PORTEES calibrent le harnais a trois conditions -- PARTIAL (bilinear, plafond 0,944 au-dessus de la barre), NOT_NECESSARY (recall), NECESSARY (recurrent_state)
status: <verdict>
verdict: <A>/<Aprime>/<B>
gate: G2
tests: [SDR-G2]
adopts: [REF-DEMAND-MARKER, REF-HARNESS-CONTRACTS, REF-HARNESS-PIECES]
---
```
Corps : (1) règle citée `docs/preregistrations/HARNESS-R1.json` ; (2) bloc `regime` recopié du JSON (jamais de mémoire) ; (3) par cellule : verdict, `hits` par seed, `ratio_within` par ablation avec `noise_band`, `sep_ref`, `dose.updates` par bras, `closure`, `bar_status` ; (4) ce que le record NE tranche PAS (tâches portées, pas générées : Q7 reste ouvert) ; (5) coût réel vs projeté, charge machine.

- [ ] **Step 4: Revue adversariale à sondes propres** — lancer un panel de 3 réfutateurs (Workflow : lentilles « bit-identité », « E19/plancher », « fuite d'oracle ») qui RELANCENT au moins un seed par cellule et confrontent chaque chiffre du record au JSON ; toute erreur trouvée → correction + cas de calibration ajouté (auto-amélioration). Ne pas graver avant la revue.

- [ ] **Step 5: Portes et commit (sur signal)** — `check_preregistration_applied.py` (grandeurs de `dv_primaire` présentes dans le record), `check_record_links.py`, `check_synthesis_counts.py` (records_total), `check_backlog_freshness.py`. Commit : `feat(HARNESS-R1): trois cellules portees, verdicts <A>/<Aprime>/<B> ; le harnais sait dire PARTIAL quand le plafond depasse la barre`. Fichiers : `tools/harness/run_r1.py tools/harness/cell.py tests/sandbox/test_harness_cell.py docs/EDR/HARNESS-R1_*.md results/harness_r1_A_0.json results/harness_r1_Aprime_0.json results/harness_r1_B_0.json docs/roadmap/SCIENCE.md docs/roadmap/PRIORITES_ET_DETTES.md`.

---

## Auto-revue du plan (faite le 2026-09-16)

1. **Couverture du spec** — §2.1 contrats : T1, T2 ; port : T3 ; tabulaire : T4 ; §2.3 cellule et JSON : T5, T6 ; §2.2 registre + REF : T7 ; porte 2 et compteurs : T8 ; §2.4 connectome et bit-identité : T9 ; scellement avec second lr mesuré : T10 ; run, record, revue : T11. Hors plan (semaines 4+) : `claude_code_llm_fn`, `propose.py`/`accept.py`, `secure_sandbox` par kind, `src/paths.proposals_root`, preprint — spec §3 semaines 4-12.
2. **Placeholders** — aucun `TBD` ; la seule valeur non écrite d'avance est le second lr de B, PRODUIT par `build_rule_r1` depuis le smoke (procédure déterministe, refus si aucun candidat).
3. **Cohérence des types** — `Episode(obs_seq: tuple, target, mask_seq: tuple|None, meta)` partout ; `Ablation.bayes_floor` lu par `assert_task_contract` et `measure_ablated_bayes_ceiling` ; `Dose.as_dict()` consommé par `_run_arm` et lu par `harness_verdict_lecture` (`dose.updates`) ; `LearnerInstance.close()` appelé dans `_run_arm` (`finally`) et dans la garde ; `rule["sweep"]` = liste de dicts `{"lr", ...}` projetée en floats pour `assert_verdict_invariant_to_optimizer` ; `run_harness_cell` renvoie `{"db", "verdict", "path", "cost"}` ; `rule_path` (T11) à ajouter dans `cell.py` avec son test.
4. **Angles morts consignés en passant** (à porter au backlog avec preuve à T11) : `check_bar_separation` aveugle à un import sous alias ; `check_control_family` aveugle à `import tools.preregister as X` ; `check_substrate_pinning.scan(None)` non récursif (`tools/harness/learners/` invisible hors `--only`) ; `count_learning_events` ne patche pas `imitate_episode_bptt` ; `learner_verdict` vit dans un module qui charge les cinq mondes.
