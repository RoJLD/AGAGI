"""
tools/harness/cell.py — UNE cellule du harnais (ADR-004, spec §2.3) : (Task acceptée, Learner accepté, n seeds,
règle scellée) -> db -> verdict à trois conditions -> JSON via Harness.save.

Tout ce qui est DÉCIDABLE SANS builder un learner refuse EN TÊTE, dans cet ordre : règle altérée
(PreregistrationTampered) · clé de `rule_path` absente (KeyError) · défauts de règle intrinsèques
(`validate_rule` : lrs dupliqués, provenance courte, n_floor<1 -- ValueError) · seeds dupliqués (ValueError)
· sélection vide (PreflightError) · episodes<2 (ValueError, "mid" serait lu à i==0, politique jamais
entraînée) · n_floor > len(seeds) (ValueError, instrument à issue unique -- E2) · ablation/bayes_floor de la
règle absente de la tâche (KeyError) · contrat de tâche (PreflightError) · pièce absente du learner
(KeyError) · L4 vérifiée à un hyper différent de celui du bras A (ValueError) · coût projeté À UNITÉ DONNÉE
(CostTooHighToStart). Le contrat du learner (`assert_learner_contract`, qui appelle `learner.build` en
interne pour vérifier L0-L7 -- c'est SA façon de tester le contrat) ne s'exécute qu'APRÈS ce refus de coût
à unité donnée : sinon un learner sentinelle dont le SEUL contact avec `build` doit lever serait atteint par
le contrat avant que `CostTooHighToStart` n'ait la moindre chance de refuser.

Bras par seed, tous sur les MÊMES tirages : A (sweep[0]) · A0 (référence lr=0, même nombre d'épisodes) ·
A2 (sweep[1]) · D (sans la pièce, sweep[0]) · D2 (sans la pièce, sweep[1]). Le bras A porte l'éval : `last` sur
le rng d'entraînement CONTINUÉ (bit-identité avec bilinear_composition_probe._train_eval_one), `noop` sur un
second rng (plancher de bruit, PAR BRAS -- R3), ablations et contrôles sur les MÊMES lots que `last`. Aucun
bail, aucun monde.

`piece_removed_verified` (lu par harness_verdict_lecture depuis db["regime"]) n'est publié True qu'APRÈS
`assert_learner_contract(learner, task, pieces=[piece])` ait effectivement passé (L4 : la variante "sans" la
pièce change bien les logits après apprentissage) -- jamais câblé.

Revue contrôleur, fix round 1 (2026-09-16) : trois défauts réels, tous corrigés ici.
(1) `_tick` tickait `guard.tick()` une fois PAR AGENT -- un gonfleur d'appels d'horloge sur un lot
    VECTORISÉ, pas une mesure par agent. Un seul `guard.tick()` par unité de travail (un lot d'éval, un
    épisode d'entraînement) : le placement était déjà correct, seul le multiplicateur ne l'était pas.
(2) Trois refus DÉCIDABLES en tête ne tombaient qu'au verdict, après jusqu'à 65 builds, sans rien
    sauvegarder : une règle nommant une ablation absente de la tâche (`KeyError 'ablated:...'` profond
    dans `_demand`), un sweep à lrs dupliqués (`ValueError` de `validate_rule`, mais jamais appelée avant
    la fin), `n_floor > len(seeds)` (cellule complète puis `INCONCLUSIVE_N` garanti -- instrument à issue
    unique, E2). Les trois sont maintenant vérifiés EN TÊTE, avant `assert_task_contract`.
(3) `cost.unit_s_measured` portait la valeur DONNÉE quand `unit_s` était fourni (E8, une grandeur qui dit
    ce qu'elle n'est pas) ; `rule_path` et la sous-règle effectivement lue n'étaient pas publiés dans
    `data["preregistration"]`.
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
from src.seed_ai.harness_verdict import (  # noqa: E402
    harness_verdict_lecture, measure_ablated_bayes_ceiling, validate_rule)
from tools.cost_guard import CostExceeded, CostGuard, project_cost  # noqa: E402
from tools.experiment_preflight import assert_control_family, assert_selection_nonempty, declare_design  # noqa: E402
from tools.preregister import provenance, verify  # noqa: E402

ARMS = ("A", "A0", "A2", "D", "D2")


def _tick(guard):
    """`guard.tick()` (PENDANT, cf. tools/cost_guard.py) une fois par UNITÉ DE TRAVAIL -- un lot d'éval
    dans `_accuracy`/`_accuracy_ablated`, un épisode d'entraînement dans `_run_arm`. PAS une fois par
    agent : le lot est VECTORISÉ (un seul appel numpy traite les `n` agents), et ticker par agent
    gonflerait le nombre d'appels d'horloge sans qu'aucun travail supplémentaire n'ait eu lieu entre deux
    appels -- une garde de coût, pas une mesure par réplicat statistique (l'unité de réplication reste le
    SEED, cf. CLAUDE.md). `guard=None` -> no-op (mesure de coût de la toute première unité, avant qu'aucun
    CostGuard n'existe)."""
    if guard is not None:
        guard.tick()


def _accuracy(inst, task, rng, batches, n, ablate=None, split="train", oracle=False, guard=None):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n, split)
        if oracle:
            hits.append(np.asarray(task.score(np.asarray(task.oracle(ep)), ep), dtype=np.float32))
        else:
            hits.append(run_episode(inst, ep, task, ablate=ablate)[1])
        _tick(guard)
    if not hits:
        raise ValueError("_accuracy : aucun lot évalué")
    return float(np.mean(np.concatenate(hits)))


def _accuracy_ablated(inst, task, rng, batches, n, ablation, rng_abl, guard=None):
    hits = []
    for _ in range(batches):
        ep = task.episodes(rng, n, "train")
        ep_a = ablation.apply(ep, rng_abl)
        hits.append(run_episode(inst, ep_a, task)[1])
        _tick(guard)
    return float(np.mean(np.concatenate(hits)))


def _run_arm(task, learner, seed, n, K, hyper, episodes, eval_batches, *, without=None, reference=False,
            full_eval=False, guard=None):
    """Un bras : entraîne `episodes` lots puis évalue `last` sur le rng continué. full_eval (bras A seulement)
    ajoute first/mid (rng de courbe), noop (second rng, TOUS les bras -- R3), ablations, contrôles, oracle.
    `guard` (CostGuard ou None) est tické une fois par UNITÉ (lot d'éval ou épisode d'entraînement) : c'est
    ce qui permet à la garde PENDANT d'attraper une unité qui dérape avant la fin du run entier."""
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
            _tick(guard)
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
    """Voir docstring de module. Rend {"db", "verdict", "path", "cost"}. `rule_path` (liste de clés, ex.
    ["cellules", "B"]) descend dans la règle scellée -- `verify` vérifie le sceau sur la règle ENTIÈRE ; la
    sélection d'une sous-cellule est un indexage PUR, donc une clé absente lève KeyError avant tout le reste."""
    whole = verify(rule_name, _dir=prereg_dir)
    rule = whole
    if rule_path:
        for k in rule_path:
            rule = rule[k]
    validate_rule(rule)                                     # lrs dupliqués / provenance courte / n_floor<1
    prov = provenance(rule_name, _dir=prereg_dir)
    seeds = [int(s) for s in seeds]
    if len(seeds) != len(set(seeds)):
        dupes = sorted({s for s in seeds if seeds.count(s) > 1})
        raise ValueError(f"seeds contient des doublons : {dupes} -- l'unité de réplication est le SEED "
                         "(CLAUDE.md), un doublon compterait deux fois la MÊME unité")
    assert_selection_nonempty(len(seeds), label="seeds")
    if int(episodes) < 2:
        raise ValueError(f"episodes={episodes} < 2 : 'mid' est lu à i == episodes//2 == 0, sur une "
                         "politique qui n'a encore subi AUCUN pas d'entraînement")
    if int(rule["n_floor"]) > len(seeds):
        raise ValueError(f"rule.n_floor={rule['n_floor']} > len(seeds)={len(seeds)} : la cellule ne peut "
                         "JAMAIS réunir n_floor seeds complètes -- instrument à issue unique (E2), tout "
                         "run rendrait INCONCLUSIVE_N après coup, quel que soit le résultat mesuré")
    abl_names_task = {a.name for a in task.demand.ablations}
    abl_names_rule = {a["name"] for a in rule["ablations"]}
    if not abl_names_rule <= abl_names_task:
        raise KeyError(f"rule.ablations nomme {sorted(abl_names_rule - abl_names_task)}, absente(s) de "
                       f"la tâche {task.name!r} ({sorted(abl_names_task)})")
    bayes_keys_rule = set(rule.get("bayes_floors", {}))
    if not bayes_keys_rule <= abl_names_task:
        raise KeyError(f"rule.bayes_floors nomme {sorted(bayes_keys_rule - abl_names_task)}, absente(s) "
                       f"de la tâche {task.name!r} ({sorted(abl_names_task)})")
    contract_task = assert_task_contract(task, seed=seeds[0], n=64)
    K = int(task.K)
    sweep = [dict(h) for h in rule["sweep"]]
    piece = rule["piece"]
    pieces = {p.name: p for p in learner.pieces}
    if piece not in pieces:
        raise KeyError(f"la règle cible la pièce {piece!r}, absente de {learner.name} ({sorted(pieces)})")
    without = dict(pieces[piece].without)
    # L4 (VACUOUS_PIECE) de assert_learner_contract est vérifiée à learner.sweep()[0], pas à rule.sweep[0]
    # (la signature n'accepte pas de hyper explicite) : si les deux diffèrent, le contrat valide la pièce à
    # un réglage DIFFÉRENT de celui du bras A de cette cellule -- refuser plutôt que publier une nécessité
    # vérifiée hors du régime réellement mesuré.
    learner_sweep0 = dict(learner.sweep()[0])
    if learner_sweep0 != sweep[0]:
        raise ValueError(f"learner.sweep()[0]={learner_sweep0} != rule.sweep[0]={sweep[0]} : le contrat L4 "
                         "(VACUOUS_PIECE) serait vérifié à un hyperparamètre différent de celui du bras A "
                         "de cette cellule -- assert_learner_contract n'accepte pas de hyper explicite")
    n_abl = len(task.demand.ablations)
    family = assert_control_family(cells=n_abl * 1 * len(sweep))
    bayes = {a.name: measure_ablated_bayes_ceiling(task, a, n=4096, seed=seeds[0])
             for a in task.demand.ablations if a.site == "input"}
    clock = clock or time.monotonic
    # Coût : refuse AVANT tout build quand l'unité est DONNÉE -- test_cost_projection_refuses_before_any_build
    # utilise une sentinelle dont le SEUL contact avec `build` doit lever ; le placer ici, avant le contrat du
    # learner (qui appelle `build` en interne pour vérifier L0-L7), est ce qui le garantit.
    projected = None
    unit_measured = None                    # E8 : ne PUBLIE une valeur "mesurée" que si elle l'est réellement
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
        unit_measured = unit
        projected = project_cost(unit, n_units=len(seeds) * len(ARMS), budget_s=float(budget_s), safety=3.0,
                                 label=out_name)
    design = declare_design(
        question=rule.get("question", rule_name), replication_unit="seed", n_independent=len(seeds),
        links={"ablation->chute": "measured", "dose->acquisition": "measured", "sans_piece->chute": "measured",
               "analogue_bio": "inferred"},
        allow_inferred_reason="l'analogue biologique d'une pièce est une hypothèse portée par le registre "
                              "(spec §2.6), jamais mesurée ici",
        cost_estimate=projected, control_family=family)
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
            "preregistration": {"name": rule_name, "seal": prov.get("seal"), "rule_path": rule_path,
                                "rule": rule},
            "provenance": prov, "db": db, "verdict": verdict,
            "cost": {"unit_s_measured": unit_measured, "unit_s_given": unit_s, "projected_s": projected,
                     "actual_s": clock() - t0, "machine_load_note": "charge machine a noter dans le record (E12)"}}
    path = None
    if save:
        h = Harness(seed=seeds[0], name=out_name, with_db=False)
        path = h.save(data)
    return {"db": db, "verdict": verdict, "path": path, "cost": data["cost"]}
