"""tools/disjoint_heads_correlated.py — Profs correles, interference induite (EDR 155, V2).

EDR 152 : les tetes disjointes battent le plat mais cos-conflit~0 -> interference REFUTEE, MAIS les profs etaient
INDEPENDANTS (quasi-orthogonaux) -> pas d'interference a trouver (caveat I2). V2 induit une vraie interference
(profs correles par sous-espace partage signe, sweep rho) et re-teste : quand le cosinus du trunc devient negatif,
le credit-equilibrage PLAT (FLAT_NORM, 153) recouvre-t-il encore l'avantage DISJOINT, ou l'architecture compte-t-elle
enfin ? Reutilise 152 (_train_arm, cosinus) + 153 (FLAT_NORM, recovery). Auto-contenu PyTorch, ne modifie rien.

Usage : python -m tools.disjoint_heads_correlated
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from tools.disjoint_heads_ab import (
    torch, _train_arm, _seed_improv, D, K_A, P_PRED, TEACHER_SEED, STEPS,
)
from tools.disjoint_heads_confound import _train_flat_norm, _recovery

# Signes par tete sur la composante commune : action/value alignees, pred opposee -> au moins une paire contestee.
SIGMA = {"action": 1.0, "value": 1.0, "pred": -1.0}
COS_INDUCED = -0.05   # seuil axe A (gele)


def _make_correlated_teachers(rho, seed=TEACHER_SEED):
    """3 profs correles par sous-espace partage signe. Meme format que _make_teachers (152) : {"action":(w1,w2),...},
    w1 (D,16), w2 (16,out). w1_k(rho) = colnorm(sqrt(1-rho)*indep_k + sqrt(rho)*SIGMA[k]*common). rho=0 -> independants
    (baseline ~orthogonale de CE mecanisme) ; rho->1 -> meme sous-espace, signes opposes -> conflit vise. Meme seed
    pour tout rho -> seule la mixture change a travers le sweep. Deterministe (numpy default_rng)."""
    rng = np.random.default_rng(seed)
    outs = {"action": K_A, "value": 1, "pred": P_PRED}
    common = (rng.standard_normal((D, 16)) / np.sqrt(D)).astype(np.float32)
    teachers = {}
    for name, out in outs.items():
        indep = (rng.standard_normal((D, 16)) / np.sqrt(D)).astype(np.float32)
        w1 = np.sqrt(1.0 - rho) * indep + np.sqrt(rho) * SIGMA[name] * common
        # colnorm : rescale chaque colonne a la norme de la colonne independante d'origine (echelle feature ~rho-invariante)
        for c in range(w1.shape[1]):
            src = float(np.linalg.norm(indep[:, c]))
            cur = float(np.linalg.norm(w1[:, c]))
            if cur > 1e-8:
                w1[:, c] *= src / cur
        w1 = w1.astype(np.float32)
        w2 = (rng.standard_normal((16, out)) / np.sqrt(16)).astype(np.float32)
        teachers[name] = (w1, w2)
    return teachers


def _verdict_correlated(cos_list, recovery_list):
    """Verdict combine 2 axes a rho_max. GELE.
    Axe A : INDUCED si cos<=COS_INDUCED majorite, sinon NOT_INDUCED.
    Axe B : CREDIT_ROBUST recovery>=0.50 majorite / ARCH_MATTERS <=0.20 majorite / sinon CREDIT_PARTIAL."""
    n = len(cos_list)
    maj = n // 2 + 1
    axis_a = "INDUCED" if sum(1 for c in cos_list if c <= COS_INDUCED) >= maj else "NOT_INDUCED"
    robust = sum(1 for r in recovery_list if r >= 0.50)
    arch = sum(1 for r in recovery_list if r <= 0.20)
    if robust >= maj:
        axis_b = "CREDIT_ROBUST"
    elif arch >= maj:
        axis_b = "ARCH_MATTERS"
    else:
        axis_b = "CREDIT_PARTIAL"
    return axis_a + "+" + axis_b
