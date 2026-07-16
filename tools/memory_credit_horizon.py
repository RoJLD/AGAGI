"""tools/memory_credit_horizon.py — Banc « horizon de credit » (P1 audit memoire).

Fait VARIER le delai D d'une tache K-bit recall (reseau simplifie de grad_mem) et compare la frontiere
(acc vs D) entre BPTT et mutation. Question falsifiable : l'avantage du gradient s'ELARGIT-il quand le
delai croit (assignation de credit a travers le temps) ? Si oui -> HORIZON CONFIRME (aligne EDR 067 +
le verrou credit-assignment d'EDR 119/120) ; si la mutation suit BPTT a grand D -> HORIZON REFUTE.

Tooling pur (pas de src/, pas de make_population/torch/Biosphere). Usage : python -m tools.memory_credit_horizon
"""
import sys
import numpy as np

from src.seed_ai.harness import Harness
from tools.grad_mem import train, train_mutation


def train_arm(arm, N=19, I=8, O=8, K=4, D=3, epochs=400, batch=64, seed=0):
    """Entraine un bras sur le reseau simplifie. arm in {'bptt','mutation'}. Meme reseau/tache/budget
    -> comparaison appariee. Renvoie l'accuracy sign-match finale."""
    if arm == "bptt":
        return train(N, I, O, K, D, epochs, batch, seed=seed)
    if arm == "mutation":
        return train_mutation(N, I, O, K, D, epochs, batch, seed=seed)
    raise ValueError(f"arm inconnu: {arm!r}")


def frontier(arm, K=4, Ds=(1, 3, 6, 10, 16, 24), seeds=(0, 1, 2), N=19, I=8, O=8, epochs=400, batch=64):
    """Balaie le delai D a K fixe, R=len(seeds) seeds appaires. Renvoie {D: mean_acc}."""
    out = {}
    for D in Ds:
        accs = [train_arm(arm, N=N, I=I, O=O, K=K, D=D, epochs=epochs, batch=batch, seed=s) for s in seeds]
        out[D] = float(np.mean(accs))
    return out


def _verdict_horizon(front_bptt, front_mut, gap_margin=0.20, hi=0.90, lo=0.65):
    """HORIZON CONFIRME si le gap (bptt - mut) CROIT avec D (delta >= gap_margin) ET il existe un D ou
    BPTT tient (>=hi) la ou la mutation s'effondre (<=lo) ; HORIZON REFUTE sinon ; INDETERMINE si une
    frontiere est vide."""
    if not front_bptt or not front_mut:
        return "INDETERMINE"
    Ds = sorted(set(front_bptt) & set(front_mut))
    if not Ds:
        return "INDETERMINE"
    d_lo, d_hi = Ds[0], Ds[-1]
    gap_lo = front_bptt[d_lo] - front_mut[d_lo]
    gap_hi = front_bptt[d_hi] - front_mut[d_hi]
    grows = (gap_hi - gap_lo) >= gap_margin
    separated = any(front_bptt[d] >= hi and front_mut[d] <= lo for d in Ds)
    return "HORIZON CONFIRME" if (grows and separated) else "HORIZON REFUTE"


def _report_horizon(h, K, front_bptt, front_mut, R, _return):
    """Table ASCII (1 ligne/D : D, acc_bptt, acc_mut, gap) + D_max par bras + verdict. Save JSON."""
    verdict = _verdict_horizon(front_bptt, front_mut)
    Ds = sorted(set(front_bptt) & set(front_mut))
    print("\n=== Horizon de credit : frontiere (delai D) BPTT vs mutation ===")
    print("  D | acc_bptt acc_mut |   gap")
    for d in Ds:
        gb, gm = front_bptt[d], front_mut[d]
        print(f"  {d:2d} | {gb:8.3f} {gm:6.3f} | {gb - gm:+.3f}")

    def _dmax(front):
        ok = [d for d in Ds if front[d] >= 0.95]
        return max(ok) if ok else 0

    print(f"  D_max(acc>=0.95) : bptt={_dmax(front_bptt)} mutation={_dmax(front_mut)}")
    print("=== VERDICT (horizon de credit) ===")
    print(f"  -> {verdict}")
    table = [{"D": d, "acc_bptt": front_bptt[d], "acc_mut": front_mut[d], "gap": front_bptt[d] - front_mut[d]}
             for d in Ds]
    h.save({"K": K, "R": R, "verdict": verdict, "table": table})
    if _return:
        return {"verdict": verdict, "table": table, "K": K, "R": R}


def main_credit_horizon(K=4, Ds=(1, 3, 6, 10, 16, 24), R=3, epochs=400, seed=1167, _return=False):
    """Frontiere (K,D) appariee BPTT vs mutation sur le reseau simplifie. Quantifie si l'avantage du
    gradient s'elargit avec le delai (horizon de credit)."""
    with Harness(seed=seed, name="memory_credit_horizon", with_db=False) as h:
        base = h.seed
        seeds = [base + r for r in range(R)]
        print(f"Horizon de credit : K={K}, Ds={Ds}, R={R}, epochs={epochs}, seed={base}.")
        front_bptt = frontier("bptt", K=K, Ds=Ds, seeds=seeds, epochs=epochs)
        front_mut = frontier("mutation", K=K, Ds=Ds, seeds=seeds, epochs=epochs)
        return _report_horizon(h, K, front_bptt, front_mut, R, _return)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main_credit_horizon()
