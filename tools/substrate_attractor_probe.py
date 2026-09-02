"""Sonde dynamique du substrat récurrent (EDR-DREAM-005), promue du scratchpad au cliquet.

Corrobore [[EDR-DREAM-004]] HORS-MONDE : sous entrée constante, l'état récurrent `H` converge-t-il vers
un point fixe (substrat contractif) ? le bruit d'action laisse-t-il `H` inchangé (il n'écrit jamais dans
l'état) ? le bruit porté fait-il errer `H` ?

Le CŒUR scientifique est `measure_convergence` : il décide « cette trajectoire d'état converge-t-elle ? ».
C'est lui qui produit l'affirmation, donc lui qui est sous cliquet
(`tests/sandbox/test_instrument_calibration.py`, calibré sur un système contractif et une marche
aléatoire CONNUS). `probe_substrate_attractor` orchestre ; il n'affirme rien que `measure_convergence`
ne tranche.

Portée (cf. le record) : P2 — « le bruit d'action laisse `H` bit-identique à off » — est rigoureux et
indépendant de l'entrée (propriété du point d'injection). P1/P3 sous entrée constante sont illustratifs
du régime dynamique, PAS une preuve in-world (l'entrée y varie).
"""
import os
import sys
from typing import Dict, List

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.agents.mamba_agent import MambaAgent, MambaBatchModel


def step_sizes(traj: List[np.ndarray]) -> List[float]:
    """||H_t - H_{t-1}|| le long d'une trajectoire d'état (liste de vecteurs)."""
    return [float(np.linalg.norm(traj[t] - traj[t - 1])) for t in range(1, len(traj))]


def measure_convergence(traj: List[np.ndarray], tail: int = 8, tol: float = 1e-3) -> Dict:
    """INSTRUMENT (sous cliquet) : une trajectoire d'état converge-t-elle vers un point fixe ?

    Verdict = le pas médian sur la QUEUE (`tail` derniers) tombe sous `tol`. Renvoie aussi ce pas de
    queue (amplitude de l'errance résiduelle) pour rendre la décision lisible et graduée.

    Calibré sur réponse CONNUE (`test_instrument_calibration.py`) : un système contractif (`H<-0.5 H`)
    -> CONVERGE ; une marche aléatoire (`H<-H+bruit`) -> NE CONVERGE PAS. Sans cette calibration, un
    détecteur cassé FABRIQUE le verdict — c'est la raison d'être du cliquet."""
    s = step_sizes(traj)
    if len(s) < tail:
        return {"converges": False, "tail_step": float("inf"), "n_steps": len(s)}
    tail_step = float(np.median(s[-tail:]))
    return {"converges": tail_step < tol, "tail_step": tail_step, "n_steps": len(s)}


def _fresh_batch(n: int, seed: int):
    # SEED GLOBAL avant création : MambaAgent() tire W sur np.random GLOBAL (mamba_agent.py:23). Sans ce
    # reset, deux bras créés en séquence porteraient des génomes DIFFÉRENTS -> on comparerait des
    # populations distinctes (classe E9/E15 — le piège attrapé sur cette sonde même, cf. EDR-DREAM-005).
    np.random.seed(seed)
    rng = np.random.RandomState(seed + 777)                       # RNG local séparé pour l'obs fixe
    agents = []
    for _ in range(n):
        a = MambaAgent()
        a.genome.organ_genes = np.array([True, False])            # organe ON -> éligible au rêve
        agents.append(a)
    return MambaBatchModel(agents), rng


def _drive(mode: str, n: int, T: int, seed: int, sigma_H: float, sigma_a: float, obs_mode: str):
    """Conduit le batch model T ticks sous entrée CONSTANTE. Renvoie (trajectoires de H, suites d'actions)."""
    m, rng = _fresh_batch(n, seed)
    I = m.max_I
    obs = np.zeros((n, I), np.float32) if obs_mode == "zero" \
        else np.tile(rng.randn(1, I).astype(np.float32), (n, 1))
    MambaBatchModel.FORCE_DREAM = 8 if mode == "H" else "off"
    MambaBatchModel.DREAM_SHAM = (mode == "H")
    MambaBatchModel.DREAM_NOISE = sigma_H
    MambaBatchModel.ACTION_NOISE = sigma_a if mode == "action" else 0.0
    np.random.seed(1000 + seed)
    H_traj = [[] for _ in range(n)]
    A_traj = [[] for _ in range(n)]
    try:
        for _ in range(T):
            preds, _ = m.forward(obs.copy())
            Hs = m.H_prev_batch
            A = min(MambaBatchModel.PLAN_A, preds.shape[1])
            for i in range(n):
                H_traj[i].append(Hs[i].copy())
                A_traj[i].append(int(np.argmax(preds[i, :A])))
    finally:
        MambaBatchModel.FORCE_DREAM = None
        MambaBatchModel.DREAM_SHAM = False
        MambaBatchModel.DREAM_NOISE = 0.05
        MambaBatchModel.ACTION_NOISE = 0.0
    return H_traj, A_traj


def probe_substrate_attractor(n: int = 12, T: int = 50, seed: int = 0,
                              sigma_H: float = 0.2, sigma_a: float = 8.0,
                              obs_mode: str = "zero") -> Dict:
    """Orchestration (n'affirme rien que `measure_convergence` ne tranche). Trois bras off/action/H sous
    entrée constante, MÊMES génomes (seed global identique). Renvoie les métriques P1/P2/P3 du record."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-02, 6e elargissement du cliquet). Un argument degenere
    # est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte vide ou un horizon
    # nul rend 0.0 comme une MESURE, que l'aval lit comme « reste au plancher » / « n'emerge pas ».
    # Posee AVANT toute construction de monde -> le refus est instantane (teste : < 0.5 s).
    if int(n) <= 0 or int(T) <= 0:
        raise ValueError(
            f"probe_substrate_attractor : argument degenere (n={n}, T={T}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    H_off, A_off = _drive("off", n, T, seed, sigma_H, sigma_a, obs_mode)
    H_act, A_act = _drive("action", n, T, seed, sigma_H, sigma_a, obs_mode)
    H_H, A_H = _drive("H", n, T, seed, sigma_H, sigma_a, obs_mode)

    conv = {k: sum(measure_convergence(t[i])["converges"] for i in range(n))
            for k, t in (("off", H_off), ("action", H_act), ("H", H_H))}
    bit_identical = sum(1 for i in range(n)
                        if all(np.array_equal(H_off[i][t], H_act[i][t]) for t in range(len(H_off[i]))))
    d_act = float(np.median([np.linalg.norm(H_off[i][-1] - H_act[i][-1]) for i in range(n)]))
    d_H = float(np.median([np.linalg.norm(H_off[i][-1] - H_H[i][-1]) for i in range(n)]))

    def _div(A):
        half = len(A[0]) // 2
        return float(np.median([len(set(A[i][half:])) for i in range(n)]))

    return {"n": n, "obs_mode": obs_mode,
            "P1_converge": conv,                                  # off/action gèlent, H erre
            "P2_bit_identical_off_action": bit_identical, "div_action": d_act, "div_H": d_H,
            "P3_action_diversity": {"off": _div(A_off), "action": _div(A_act), "H": _div(A_H)}}


if __name__ == "__main__":
    for om in ("zero", "fixed_random"):
        r = probe_substrate_attractor(obs_mode=om)
        print(f"=== {om} ===")
        print(f"  P1 converge (/{r['n']}): off={r['P1_converge']['off']} "
              f"action={r['P1_converge']['action']} H={r['P1_converge']['H']}")
        print(f"  P2 H(off)==H(action) bit-a-bit: {r['P2_bit_identical_off_action']}/{r['n']} "
              f"(div action={r['div_action']:.2e} vs H={r['div_H']:.2e})")
        print(f"  P3 diversite action: {r['P3_action_diversity']}")
