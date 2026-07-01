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
    shuf = np.random.permutation(acts)
    return float(np.mean(preds == shuf))


def _latent_probe(records, split=0.7):
    """Sonde lineaire (moindres carres + biais) : le latent expose (68 dims) predit-il l'action du
    congenere ? Renvoie (acc_true, acc_shuffle) held-out. < 20 records -> (0.0, 0.0). Split par ORDRE
    (deterministe)."""
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
    acc_shuffle = _fit_eval(np.random.permutation(y))
    return acc_true, acc_shuffle


def _verdict_tom_emergence(acc_head_tom, acc_head_ctrl, acc_shuffle_tom):
    """TOM_EMERGES ssi la recompense ToM leve l'accuracy au-dessus du shuffle (base-rate) ET du bras
    CONTROL, des deux >= 0.10 ; sinon TOM_INERT (la faculte n'emerge pas sur le substrat plat)."""
    if acc_head_tom >= acc_shuffle_tom + 0.10 and acc_head_tom >= acc_head_ctrl + 0.10:
        return "TOM_EMERGES"
    return "TOM_INERT"
