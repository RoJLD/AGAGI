"""
src/seed_ai/harness_learner.py — Contrat `Learner` du harnais (ADR-004, spec §2.1).

Un Learner est une ARCHITECTURE qui déclare ses PIÈCES, chacune avec sa variante « sans » : c'est le marqueur de
NÉCESSITÉ porté par l'architecture. `build(reference=True)` rend le bras de référence de la condition (ii) :
même init, mêmes tirages, même boucle, apprentissage COUPÉ. La dose est comptée EN LIGNE dans `learn` (le patch
de classe `count_learning_events` ne voit pas `imitate_episode_bptt`). `assert_learner_contract` refuse en tête.

Décision contrôleur (tâche 2, 2026-09-16) — L4 (VACUOUS_PIECE) compare les logits APRÈS apprentissage, pas à
l'init : un apprenant tabulaire non entraîné rend des zéros avec ou sans sa table, et une pièce du CHEMIN DE
CRÉDIT ne change rien à l'init. La variante « sans » subit donc les MÊMES n_learn pas d'apprentissage, sur les
MÊMES épisodes, que l'intact — via `run_episode` + `learn`, exactement comme la boucle qui calibre (L2)/(L3).
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


def _learn_n_steps(inst, ep, task, n_learn):
    """Fait subir n_learn pas d'apprentissage à `inst` sur `ep`, EXACTEMENT comme la boucle (L2)/(L3) :
    run_episode (act sur tous les pas) puis learn. Rend la Dose du dernier appel."""
    dose = None
    for _ in range(n_learn):
        actions, hits = run_episode(inst, ep, task)
        dose = inst.learn(ep, actions, hits)
    return dose


def assert_learner_contract(learner, task, seed=0, n_probe=8, n_learn=5, pieces=None) -> dict:
    """Garde EN TÊTE, une population de n_probe, n_learn épisodes :
    (L0) task.K <= learner.max_K ; toute Ablation site="state" de la tâche ∈ supported_state_ablations ;
    (L1) deux build(seed) -> logits bit-identiques ; build(without={}) bit-identique (no-op EXACT) À L'INIT
    ET après n_learn pas d'apprentissage ;
    (L2) REFERENCE_LEARNS : build(reference=True).learn x n_learn -> dparam_abs_sum == 0 et updates == 0 ;
    (L3) DEAD_LEARNER : build().learn x n_learn -> dparam_abs_sum > 0 (le cas « curiosité morte », P4.8) ;
    (L4) VACUOUS_PIECE : pour chaque Piece EN PORTÉE (`pieces`, défaut = toutes), build(without=p.without)
    subit les MÊMES n_learn pas d'apprentissage que l'intact puis diffère de lui sur >= 1 logit APRÈS coup —
    un apprenant tabulaire non entraîné rend des zéros avec ou sans sa table, comparer à l'init serait aveugle
    à toute pièce du chemin de crédit ; (L5) assert_no_aliasing(logits, state) ; (L6) entry_task non vide ;
    (L7) len(sweep()) >= 2 pas distincts.
    `pieces` (défaut None = `learner.pieces`) restreint (L4) aux noms listés ; un nom absent de
    `learner.pieces` lève "(L4) pièce inconnue".
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
    # (L4) portée : quels noms de pièce sont jugés
    all_names = {p.name for p in learner.pieces}
    scope_names = all_names if pieces is None else set(pieces)
    for name in scope_names:
        if name not in all_names:
            _fail(f"(L4) pièce inconnue {name!r} : absente de learner.pieces ({sorted(all_names)})")
    scoped_pieces = [p for p in learner.pieces if p.name in scope_names]
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
    if not np.array_equal(la, lc):
        inst_a.close()
        inst_c.close()
        _fail("(L1) build(without={}) n'est pas bit-identique à l'intact À L'INIT : le no-op n'est pas EXACT")
    # (L5) aucune vue de l'état dans la sortie
    try:
        assert_no_aliasing(la, state_a, label="logits de act")
        if state_a is not None and hasattr(state_a, "shape"):
            assert_no_aliasing(la, np.asarray(state_a), label="logits de act")
    except PreflightError as e:
        inst_a.close()
        inst_c.close()
        _fail(f"(L5) {e}")
    # (L3) l'intact apprend ; la même trace de logits post-apprentissage sert à (L4)
    dose_a = _learn_n_steps(inst_a, ep, task, n_learn)
    la_trained, _ = _logits_of(inst_a, ep)
    inst_a.close()
    if dose_a is None or not isinstance(dose_a, Dose) or dose_a.calls != n_learn:
        _fail(f"(L3) learn doit rendre la Dose cumulée (calls == {n_learn}), reçu {dose_a}")
    if dose_a.dparam_abs_sum is not None and not (dose_a.dparam_abs_sum > 0.0):
        _fail(f"(L3) DEAD_LEARNER : {n_learn} appels de learn et dparam_abs_sum == {dose_a.dparam_abs_sum} — l'apprenant est INERTE (cas « curiosité morte », P4.8)")
    # (L1) no-op exact APRÈS apprentissage : build(without={}) subit la même trace, doit rester bit-identique
    dose_c = _learn_n_steps(inst_c, ep, task, n_learn)
    lc_trained, _ = _logits_of(inst_c, ep)
    inst_c.close()
    if not np.array_equal(la_trained, lc_trained):
        _fail("(L1) build(without={}) n'est pas bit-identique à l'intact APRÈS n_learn pas d'apprentissage : le no-op n'est pas EXACT")
    # (L2) la référence n'apprend pas
    inst_r = learner.build(seed, n_probe, obs_dim, K, hyper, reference=True)
    dose_r = _learn_n_steps(inst_r, ep, task, n_learn)
    inst_r.close()
    ref_d = 0.0 if dose_r.dparam_abs_sum is None else float(dose_r.dparam_abs_sum)
    if ref_d != 0.0 or dose_r.updates != 0:
        _fail(f"(L2) REFERENCE_LEARNS : build(reference=True) a bougé (dparam_abs_sum={ref_d}, updates={dose_r.updates}) — la barre de (ii) est contaminée")
    if dose_r.calls != n_learn:
        _fail(f"(L2) la référence doit consommer les MÊMES appels que l'intact (calls {dose_r.calls} != {n_learn})")
    # (L4) chaque pièce EN PORTÉE a une variante « sans » qui change quelque chose APRÈS apprentissage
    for p in scoped_pieces:
        inst_w = learner.build(seed, n_probe, obs_dim, K, hyper, without=dict(p.without))
        _learn_n_steps(inst_w, ep, task, n_learn)
        lw_trained, _ = _logits_of(inst_w, ep)
        inst_w.close()
        if np.array_equal(la_trained, lw_trained):
            _fail(f"(L4) VACUOUS_PIECE : la variante sans {p.name!r} ({p.without}) rend, après {n_learn} pas d'apprentissage, des logits bit-identiques à l'intact — la « pièce » n'existe pas dans ce learner")
    return {"n_pieces": len(learner.pieces), "reference_dparam": ref_d,
            "elapsed_ms": (time.perf_counter() - t0) * 1000.0}
