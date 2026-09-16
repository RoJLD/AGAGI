"""
tools/harness/cell.py — UNE cellule du harnais (ADR-004, spec §2.3) : (Task acceptée, Learner accepté, n seeds,
règle scellée) -> db -> verdict à trois conditions -> JSON via Harness.save.

Tout ce qui refuse refuse AVANT le premier entraînement : règle scellée (verify), sélection non vide, contrat de
tâche (assert_task_contract), coût projeté sur une unité DONNÉE (project_cost) s'il y en a une, contrat du
learner (assert_learner_contract) -- DANS CET ORDRE. Le contrat du learner appelle lui-même `learner.build`
plusieurs fois (c'est SA façon de vérifier L0-L7) : le placer APRÈS le refus de coût à unité donnée est ce qui
permet à `test_cost_projection_refuses_before_any_build` de lever `CostTooHighToStart` avant qu'un `build`
quelconque n'ait lieu, y compris ceux internes à la garde du learner.

Bras par seed, tous sur les MÊMES tirages : A (sweep[0]) · A0 (référence lr=0, même nombre d'épisodes) ·
A2 (sweep[1]) · D (sans la pièce, sweep[0]) · D2 (sans la pièce, sweep[1]). Le bras A porte l'éval : `last` sur
le rng d'entraînement CONTINUÉ (bit-identité avec bilinear_composition_probe._train_eval_one), `noop` sur un
second rng (plancher de bruit, PAR BRAS -- R3), ablations et contrôles sur les MÊMES lots que `last`. Aucun
bail, aucun monde.

`piece_removed_verified` (lu par harness_verdict_lecture depuis db["regime"]) n'est publié True qu'APRÈS
`assert_learner_contract(learner, task, pieces=[piece])` ait effectivement passé (L4 : la variante "sans" la
pièce change bien les logits après apprentissage) -- jamais câblé.
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


def _tick(guard, n):
    """`guard.tick()` (PENDANT, cf. tools/cost_guard.py) une fois par agent traité -- pas une fois par lot :
    sur cette cellule jouet (quelques dizaines de lots), une fois par lot ne produit jamais assez d'appels
    d'horloge pour qu'un abandon soit même OBSERVABLE sous une horloge injectée qui ne devient chère qu'après
    des milliers d'appels (test_abandoned_seed_is_counted_and_yields_INCONCLUSIVE_N). `guard=None` -> no-op
    (mesure de coût de la toute première unité, avant qu'aucun CostGuard n'existe)."""
    if guard is None:
        return
    for _ in range(int(n)):
        guard.tick()


def _accuracy(inst, task, rng, batches, n, ablate=None, split="train", oracle=False, guard=None):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n, split)
        if oracle:
            hits.append(np.asarray(task.score(np.asarray(task.oracle(ep)), ep), dtype=np.float32))
        else:
            hits.append(run_episode(inst, ep, task, ablate=ablate)[1])
        _tick(guard, n)
    if not hits:
        raise ValueError("_accuracy : aucun lot évalué")
    return float(np.mean(np.concatenate(hits)))


def _accuracy_ablated(inst, task, rng, batches, n, ablation, rng_abl, guard=None):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n, "train")
        ep_a = ablation.apply(ep, rng_abl)
        hits.append(run_episode(inst, ep_a, task)[1])
        _tick(guard, n)
    return float(np.mean(np.concatenate(hits)))


def _run_arm(task, learner, seed, n, K, hyper, episodes, eval_batches, *, without=None, reference=False,
            full_eval=False, guard=None):
    """Un bras : entraîne `episodes` lots puis évalue `last` sur le rng continué. full_eval (bras A seulement)
    ajoute first/mid (rng de courbe), noop (second rng, TOUS les bras -- R3), ablations, contrôles, oracle.
    `guard` (CostGuard ou None) est tické une fois par agent traité, training ET éval confondus : c'est ce qui
    permet à la garde PENDANT d'attraper une unité qui dérape avant la fin du run entier."""
    inst = learner.build(seed, n, task.obs_dim, K, hyper, without=without or {}, reference=reference)
    try:
        rng = np.random.RandomState(seed + 1)                       # opérandes : key PUIS q par épisode
        rng_curve = np.random.RandomState(seed + 7919)
        out = {}
        if full_eval:
            out["first"] = _accuracy(inst, task, rng_curve, eval_batches, n, guard=guard)
        for i in range(episodes):
            if full_eval and i == episodes // 2:
                out["mid"] = _accuracy(inst, task, rng_curve, eval_batches, n, guard=guard)
            ep = task.episodes(rng, n, "train")
            actions, hits = run_episode(inst, ep, task)
            inst.learn(ep, actions, hits)
            _tick(guard, n)
        if full_eval and "mid" not in out:
            out["mid"] = out["first"]
        state = rng.get_state()
        out["last"] = _accuracy(inst, task, rng, eval_batches, n, guard=guard)
        out["dose"] = inst.dose().as_dict()
        out["noop"] = _accuracy(inst, task, np.random.RandomState(seed + 104729), eval_batches, n, guard=guard)
        if full_eval:
            rng.set_state(state)
            out["oracle"] = _accuracy(inst, task, rng, eval_batches, n, oracle=True, guard=guard)
            out["ablated"], out["control"] = {}, {}
            for a in task.demand.ablations:
                rng.set_state(state)
                if a.site == "input":
                    out["ablated"][a.name] = _accuracy_ablated(inst, task, rng, eval_batches, n, a,
                                                                np.random.RandomState(seed + 31), guard=guard)
                else:
                    out["ablated"][a.name] = _accuracy(inst, task, rng, eval_batches, n, ablate=a.name, guard=guard)
                    rng.set_state(state)
                    ci = _accuracy(inst, task, rng, eval_batches, n, split="control", guard=guard)
                    rng.set_state(state)
                    ca = _accuracy(inst, task, rng, eval_batches, n, split="control", ablate=a.name, guard=guard)
                    out["control"][a.name] = {"intact": ci, "ablated": ca}
        return out
    finally:
        inst.close()


def run_harness_cell(task, learner, rule_name, *, seeds, episodes, out_name, n_agents=16, eval_batches=40,
                     budget_s=3600.0, unit_s=None, rule_path=None, prereg_dir=None, save=True, clock=None):
    """Voir docstring de module. Rend {"db", "verdict", "path", "cost"}. Refus EN TÊTE, dans l'ORDRE :
    règle altérée (PreregistrationTampered) · clé de `rule_path` absente (KeyError) · sélection vide
    (PreflightError) · contrat de tâche (PreflightError) · coût projeté À UNITÉ DONNÉE (CostTooHighToStart)
    · contrat du learner (PreflightError). `rule_path` (liste de clés, ex. ["cellules", "B"]) descend dans la
    règle scellée -- `verify` vérifie le sceau sur la règle ENTIÈRE ; la sélection d'une sous-cellule est un
    indexage PUR, donc une clé absente lève KeyError avant tout le reste."""
    whole = verify(rule_name, _dir=prereg_dir)
    rule = whole
    if rule_path:
        for k in rule_path:
            rule = rule[k]
    prov = provenance(rule_name, _dir=prereg_dir)
    seeds = [int(s) for s in seeds]
    assert_selection_nonempty(len(seeds), label="seeds")
    contract_task = assert_task_contract(task, seed=seeds[0], n=64)
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
        allow_inferred_reason="l'analogue biologique d'une pièce est une hypothèse portée par le registre "
                              "(spec §2.6), jamais mesurée ici",
        cost_estimate=None, control_family=family)
    bayes = {a.name: measure_ablated_bayes_ceiling(task, a, n=4096, seed=seeds[0])
             for a in task.demand.ablations if a.site == "input"}
    clock = clock or time.monotonic
    # Coût : refuse AVANT tout build quand l'unité est DONNÉE -- test_cost_projection_refuses_before_any_build
    # utilise une sentinelle dont le SEUL contact avec `build` doit lever ; le placer ici, avant le contrat du
    # learner (qui appelle `build` en interne pour vérifier L0-L7), est ce qui le garantit.
    projected = None
    if unit_s is not None:
        unit = float(unit_s)
        projected = project_cost(unit, n_units=len(seeds) * len(ARMS), budget_s=float(budget_s), safety=3.0,
                                 label=out_name)
    # Contrat du learner restreint à la pièce de CETTE règle (L4 la juge non-vacueuse) : premier point du
    # runner où `learner.build` peut être atteint.
    assert_learner_contract(learner, task, seed=seeds[0], pieces=[piece])
    piece_removed_verified = True
    t0 = clock()
    first_arm = _run_arm(task, learner, seeds[0], n_agents, K, sweep[0], episodes, eval_batches, full_eval=True)
    if unit_s is None:
        unit = max(clock() - t0, 1e-6)
        projected = project_cost(unit, n_units=len(seeds) * len(ARMS), budget_s=float(budget_s), safety=3.0,
                                 label=out_name)
    regime = {"task": task.regime(), "learner_name": learner.name, "learner_family": learner.family,
              "sweep": sweep, "piece": piece, "without": without, "n_agents": n_agents, "episodes": episodes,
              "eval_batches": eval_batches, "seeds": seeds, "bayes_floors": bayes, "contract_task": contract_task,
              "incapable_ceiling": rule.get("incapable_ceiling"), "piece_removed_verified": piece_removed_verified}
    db = {"seeds": seeds, "arms": {a: {"last": {}, "dose": {}} for a in ARMS},
          "eval": {"noop": {a: {} for a in ARMS}, "oracle": {},
                   "ablated": {a.name: {} for a in task.demand.ablations}, "control": {}},
          "abandoned": {a: [] for a in ARMS}, "regime": regime}
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
                               full_eval=(arm == "A"), guard=guard)
                _store(seed, arm, res)
            except CostExceeded as e:
                db["abandoned"][arm].append(seed)
                print(f"  seed {seed:>2} bras {arm}: ABANDONNE (cout wall-clock) : {e}")
    verdict = harness_verdict_lecture(db, rule)
    data = {"regime": regime, "design": design, "control_family": family,
            "preregistration": {"name": rule_name, "seal": prov.get("seal")}, "provenance": prov,
            "db": db, "verdict": verdict,
            "cost": {"unit_s_measured": unit, "unit_s_given": unit_s, "projected_s": projected,
                     "actual_s": clock() - t0, "machine_load_note": "charge machine a noter dans le record (E12)"}}
    path = None
    if save:
        h = Harness(seed=seeds[0], name=out_name, with_db=False)
        path = h.save(data)
    return {"db": db, "verdict": verdict, "path": path, "cost": data["cost"]}
