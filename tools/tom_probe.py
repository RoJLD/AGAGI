"""tools/tom_probe.py — ToM representationnel : decode + emergence (P4 audit memoire, chantier 1).

Le substrat a un circuit ToM GATE OFF : predictor_head (8 dims, mamba_agent) + recompense ToM
(world_1_stoneage:817-826, active_exp_variable=TOM : +2 energie si argmax(predictor_head_A)==last_action_B
pour deux agents au meme cellule). Jamais actif par defaut. Ce banc mesure, en 2 bras appareilles
CONTROL(NONE)/TOM : (a) DECODE — la representation encode-t-elle deja l'action des congeneres ? (b)
EMERGENCE — la recompense ToM fait-elle emerger une prediction reelle (vs inerte comme le tool-gate 111) ?

Tooling pur (pas de src/ modifie ; map_elites_compare/competence_profile importes). Usage : python -m tools.tom_probe
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from collections import defaultdict

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.worlds.world_1_stoneage import Biosphere3D
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool, PRESERVE_DIMS


def _make_cfg_tom(exp_var):
    """cfg stoneage sweet-spot (via _make_cfg) avec active_exp_variable pose (NONE/TOM)."""
    cfg = _make_cfg()
    cfg.active_exp_variable = exp_var
    return cfg


def _head_accuracy(records):
    """Fraction des records ou argmax(predictor_head_A) == last_action_B. Liste vide -> 0.0."""
    if not records:
        return 0.0
    return float(np.mean([r["pred"] == r["act"] for r in records]))


def _shuffle_accuracy(records):
    """Baseline base-rate : accuracy quand les 'act' sont permutes (detruit la specificite A-B)."""
    if not records:
        return 0.0
    preds = np.array([r["pred"] for r in records])
    acts = np.array([r["act"] for r in records])
    shuf = np.random.default_rng(0).permutation(acts)
    return float(np.mean(preds == shuf))


def _latent_probe(records, split=0.7):
    """Sonde lineaire (moindres carres + biais) : le latent expose (68 dims) predit-il l'action du
    congenere ? Renvoie (acc_true, acc_shuffle) held-out. < 20 records -> (0.0, 0.0). Split stratifie
    par classe (deterministe : premiers 70% des indices de chaque classe)."""
    if len(records) < 20:
        return 0.0, 0.0
    X = np.stack([np.asarray(r["latent"], dtype=np.float64) for r in records])
    X = np.hstack([X, np.ones((len(X), 1))])  # biais
    y = np.array([r["act"] for r in records])
    classes = sorted(set(int(v) for v in y))
    cls_idx = {c: i for i, c in enumerate(classes)}

    # Stratified split: maintain class distribution
    indices = np.arange(len(records))
    train_idx = []
    test_idx = []
    for c in classes:
        c_idx = indices[y == c]
        n_tr = int(len(c_idx) * split)
        train_idx.extend(c_idx[:n_tr])
        test_idx.extend(c_idx[n_tr:])

    train_idx = np.array(train_idx)
    test_idx = np.array(test_idx)

    def _fit_eval(y_use):
        Xtr, Xte = X[train_idx], X[test_idx]
        ytr, yte = y_use[train_idx], y_use[test_idx]
        if len(yte) == 0:
            return 0.0
        Y = np.zeros((len(ytr), len(classes)))
        for i, c in enumerate(ytr):
            Y[i, cls_idx[int(c)]] = 1.0
        W, *_ = np.linalg.lstsq(Xtr, Y, rcond=None)
        pred_idx = np.argmax(Xte @ W, axis=1)
        pred = np.array([classes[i] for i in pred_idx])
        return float(np.mean(pred == yte))

    acc_true = _fit_eval(y)
    acc_shuffle = _fit_eval(np.random.default_rng(0).permutation(y))
    return acc_true, acc_shuffle


def _verdict_tom_emergence(acc_head_tom, acc_head_ctrl, acc_shuffle_tom):
    """TOM_EMERGES ssi la recompense ToM leve l'accuracy au-dessus du shuffle (base-rate) ET du bras
    CONTROL, des deux >= 0.10 ; sinon TOM_INERT (la faculte n'emerge pas sur le substrat plat)."""
    if acc_head_tom >= acc_shuffle_tom + 0.10 and acc_head_tom >= acc_head_ctrl + 0.10:
        return "TOM_EMERGES"
    return "TOM_INERT"


def _agent_latent(model):
    """Latent expose concatene : predictor_head(8)+goal_vector(5)+explicit_memory(5)+ntm(50) = 68. None -> zeros."""
    def _vec(x, n):
        if x is None:
            return np.zeros(n, dtype=np.float64)
        arr = np.asarray(x, dtype=np.float64).flatten()
        if arr.size < n:
            return np.concatenate([arr, np.zeros(n - arr.size)])
        return arr[:n]
    return np.concatenate([
        _vec(getattr(model, "predictor_head", None), 8),
        _vec(getattr(model, "goal_vector", None), 5),
        _vec(getattr(model, "explicit_memory", None), 5),
        _vec(getattr(model, "ntm_memory", None), 50),
    ])


def _pair_record(a, b):
    """Record dirige A->B : pred=argmax(predictor_head_A), act=last_action_B, latent_A. None si invalide."""
    act = b.get("last_action", -1)
    if act is None or act < 0:
        return None
    model = a.get("model")
    ph = getattr(model, "predictor_head", None) if model is not None else None
    if ph is None:
        return None
    return {"pred": int(np.argmax(ph)), "act": int(act), "latent": _agent_latent(model)}


def _collect_pairs_from_agents(agents, records):
    """Pour chaque paire ORDONNEE (a,b) au meme cellule (x,y,z), append _pair_record(a,b) (les 2 directions)."""
    cells = defaultdict(list)
    for ag in agents:
        cells[(ag["x"], ag["y"], ag.get("z", 0))].append(ag)
    for group in cells.values():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(len(group)):
                if i == j:
                    continue
                rec = _pair_record(group[i], group[j])
                if rec is not None:
                    records.append(rec)


def _collect_tom_pairs(cfg, genomes, max_ticks=400):
    """Cohorte fixe (benchmark_mode + memory neutralisee AVANT boucle, lecons 114b/P0). A chaque tick,
    collecte les paires same-cell. Renvoie la liste des records."""
    env = Biosphere3D(cfg)
    env.benchmark_mode = True
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g, preserve_dims=PRESERVE_DIMS)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    records = []
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        _collect_pairs_from_agents(env.agents, records)
        t += 1
    return records


def _evolve_champions_tom(seed, exp_var, eras=12, num_agents=30, max_ticks=400):
    """Cliquet top-5 (comme competence_profile._evolve_champions) MAIS cfg = _make_cfg_tom(exp_var) ->
    la recompense ToM est active (ou non) pendant l'evolution. Renvoie top-5 best_ever."""
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg_tom(exp_var)
    best_ever = [(0.0, g) for g in [_seed_genome(i) for i in range(5)]]
    for _ in range(eras):
        genomes = _reproduce([g for _s, g in best_ever], num_agents)
        pool, _m = run_era_pool(cfg, genomes, max_ticks)
        scored = sorted([(s, g) for s, g, _st in pool], key=lambda x: x[0], reverse=True)[:5]
        best_ever = sorted(best_ever + scored, key=lambda x: x[0], reverse=True)[:5]
    return [g for _s, g in best_ever]


def _report_tom(h, per_seed, R, _return):
    """Table ASCII (par seed : ctrl acc_head/shuffle/probe | tom acc_head/shuffle) + moyennes + decode +
    verdict emergence. Save JSON."""
    def _m(arm, k):
        return float(np.mean([p[arm][k] for p in per_seed]))
    ctrl = {k: _m("ctrl", k) for k in ("acc_head", "acc_shuffle", "probe_true", "probe_shuffle")}
    tom = {k: _m("tom", k) for k in ("acc_head", "acc_shuffle")}
    verdict = _verdict_tom_emergence(tom["acc_head"], ctrl["acc_head"], tom["acc_shuffle"])
    print("\n=== ToM representationnel : decode + emergence (cohorte fixe, 2 bras) ===")
    print("  seed | CTRL head shuf probe(t/s) nC | TOM  head shuf nT")
    for p in per_seed:
        c, t = p["ctrl"], p["tom"]
        print(f"  {p['seed']:4d} |      {c['acc_head']:.3f} {c['acc_shuffle']:.3f} "
              f"{c['probe_true']:.3f}/{c['probe_shuffle']:.3f} {c['n']:5d} |      "
              f"{t['acc_head']:.3f} {t['acc_shuffle']:.3f} {t['n']:5d}")
    print(f"  MOYEN|      {ctrl['acc_head']:.3f} {ctrl['acc_shuffle']:.3f} "
          f"{ctrl['probe_true']:.3f}/{ctrl['probe_shuffle']:.3f} |      {tom['acc_head']:.3f} {tom['acc_shuffle']:.3f}")
    print("=== DECODE (bras CONTROL) ===")
    print(f"  head vs shuffle : {ctrl['acc_head']:.3f} vs {ctrl['acc_shuffle']:.3f} "
          f"| latent-probe vs shuffle : {ctrl['probe_true']:.3f} vs {ctrl['probe_shuffle']:.3f}")
    n_ctrl = float(np.mean([p["ctrl"]["n"] for p in per_seed]))
    n_tom = float(np.mean([p["tom"]["n"] for p in per_seed]))
    print(f"  records/seed (moyenne) : CTRL {n_ctrl:.0f} | TOM {n_tom:.0f}")
    print("=== VERDICT (emergence ToM) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "n_ctrl": n_ctrl, "n_tom": n_tom,
            "mean_ctrl": ctrl, "mean_tom": tom, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "n_ctrl": n_ctrl, "n_tom": n_tom,
                "mean_ctrl": ctrl, "mean_tom": tom, "per_seed": per_seed, "R": R}


def _measure_arm_records(exp_var_for_evo, seed, eras, num_agents, max_ticks):
    """Evolue un bras puis collecte ses paires sur cohorte fixe (cfg de mesure NEUTRE = NONE pour les 2 bras)."""
    champs = _evolve_champions_tom(seed, exp_var_for_evo, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
    reps = (champs * (num_agents // len(champs) + 1))[:num_agents] if champs else []
    return _collect_tom_pairs(_make_cfg_tom("NONE"), reps, max_ticks=max_ticks)


def main_tom_probe(R=3, eras=12, num_agents=30, max_ticks=400, seed=1280, _return=False):
    """Par seed base+r : evolue CONTROL(NONE) + TOM, mesure les paires per-bras sur cohorte fixe (mesure
    neutre), calcule accuracy head/shuffle (+ sonde latente sur CONTROL), agrege, verdict emergence."""
    base = seed
    h = Harness(seed=base, name="tom_probe", with_db=False, config=WorldConfig())
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            rc = _measure_arm_records("NONE", s, eras, num_agents, max_ticks)
            rt = _measure_arm_records("TOM", s, eras, num_agents, max_ticks)
            probe_true, probe_shuffle = _latent_probe(rc)
            per_seed.append({
                "seed": int(s),
                "ctrl": {"acc_head": _head_accuracy(rc), "acc_shuffle": _shuffle_accuracy(rc),
                         "probe_true": probe_true, "probe_shuffle": probe_shuffle, "n": len(rc)},
                "tom": {"acc_head": _head_accuracy(rt), "acc_shuffle": _shuffle_accuracy(rt), "n": len(rt)},
            })
    finally:
        async_logger.stop()
    return _report_tom(h, per_seed, R, _return)


if __name__ == "__main__":
    main_tom_probe()
