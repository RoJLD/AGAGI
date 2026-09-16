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
    if not all(np.array_equal(x, y) for x, y in zip(a.obs_seq, b.obs_seq)):
        return False
    if (a.mask_seq is None) != (b.mask_seq is None):
        return False
    if a.mask_seq is None:
        return True
    if len(a.mask_seq) != len(b.mask_seq):
        return False
    return all(np.array_equal(x, y) for x, y in zip(a.mask_seq, b.mask_seq))


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
        if _episodes_bit_identical(ep, ctrl):
            _fail("(a) split 'control' bit-identique au split 'train' (même graine) : episodes() ignore "
                  "l'argument split, aucun control distinct n'existe pour une ablation site='state'")
    # (b) le vérifieur est indépendant de l'oracle
    orc = np.asarray(task.oracle(ep))
    acc = float(np.mean(task.score(orc, ep)))
    if acc != 1.0:
        _fail(f"(b) score(oracle) = {acc:.4f}, attendu 1.0 : le contrôle positif de la DV échoue")
    acc_shift = float(np.mean(task.score((orc + 1) % K, ep)))
    if acc_shift != 0.0:
        _fail(f"(b) oracle décalé noté {acc_shift:.4f}, attendu 0.0 : le vérifieur n'est pas indépendant de l'oracle (E1)")
    try:
        mask0 = None if ep.mask_seq is None else tuple(m[:0] for m in ep.mask_seq)
        task.score(np.zeros(0, dtype=np.int64), Episode(tuple(o[:0] for o in ep.obs_seq), ep.target[:0], mask0, {}))
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
