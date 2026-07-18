"""tools/nav_credit_structure.py — NAV-005 : le mur in-world du binding (EDR-172) est-il la RARETE du crédit
ou son BIAIS ? (diagnostic actionnable pour la session torch T3).

EDR-172 (session torch) : le throw-gate câblé in-world NE BINDE PAS ; diagnostic = « substrat : rareté du
crédit (kills 0-6/300 ticks) ». Récompense de leur REINFORCE : throw+kill → +1 (RARE), throw sans kill →
−0.5, pas de throw → 0. NAV-004 a montré que la rareté NON-BIAISEE est quasi-gratuite (ρ=0.01 → recovery
0.91) mais que le BIAIS est fatal. Hypothèse : le mur de T3 est le −0.5 (pénalité sur le BON geste non-payant),
pas la rareté.

Modèle sur le readout de navigation (H figé, capture NAV-001) : récompense = +1 si l'action correcte PAIE
(proba p_success, modélise le kill rare), sinon `penalty` (−0.5 = biaisé, comme T3 ; 0 = non-biaisé) ; action
incorrecte → 0. Espérance de l'action correcte = p_success·1 + (1−p_success)·penalty.
  - penalty=0 (non-biaisé) : espérance = p_success ≥ 0 toujours → l'action correcte reste favorisée.
  - penalty=−0.5 (biaisé, T3) : espérance = 1.5·p_success − 0.5 < 0 dès p_success < 1/3 → l'action correcte
    devient NÉGATIVE → le readout apprend à l'ÉVITER (gap négatif, comme le gap_ON<0 observé in-world).

Sweep p_success × {biaisé, non-biaisé} → décompose RARETE vs BIAIS. Verdict + correctif actionnable pour T3.
Reutilise capture()/_train_readout() d'EDR-NAV-001/003. Tooling-only, deterministe. Usage :
  python -m tools.nav_credit_structure
"""
import os
import sys

import numpy as np

try:                                                   # console Windows cp1252 -> force utf-8 (cf. hygiène #151)
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.seed_ai.harness import Harness
from tools.lethality_curriculum import _disable_kuzu
from tools.lewis_survival_sweep import _cfg
from tools.nav_localization_probe import capture, linear_probe_accuracy
from tools.nav_readout_trainability import _split_zscore, _train_readout, N_CLASSES

try:
    import torch
except Exception:                                      # pragma: no cover
    torch = None


# ----------------------------------------------------------------------------- entrainement (impur)
def _train_rl_structured(H, y, p_success, penalty, seed, steps=1500, lr=1e-2, batch=256):
    """RL-bandit avec la structure de récompense de T3 : action correcte PAIE (+1) avec proba p_success,
    sinon `penalty` ; action incorrecte → 0. Même init/split que _train_readout. Retourne l'accuracy test."""
    torch.manual_seed(seed)
    Htr, ytr, Hte, yte = _split_zscore(H, y, seed)
    head = torch.nn.Linear(Htr.shape[1], N_CLASSES)
    opt = torch.optim.Adam(head.parameters(), lr=lr)
    F = torch.nn.functional
    ntr = len(ytr)
    baseline = 0.0
    g = torch.Generator().manual_seed(seed + 1)
    head.train()
    for t in range(steps):
        idx = torch.randint(0, ntr, (min(batch, ntr),), generator=g)
        logits = head(Htr[idx])
        logp = F.log_softmax(logits, dim=1)
        a = torch.multinomial(logp.exp(), 1, generator=g).squeeze(1)
        correct = (a == ytr[idx])
        paid = torch.rand(len(a), generator=g) < p_success
        reward = torch.where(correct, torch.where(paid, 1.0, float(penalty)), 0.0)
        chosen = logp[torch.arange(len(a)), a]
        baseline = 0.99 * baseline + 0.01 * float(reward.mean())
        loss = -((reward - baseline) * chosen).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    head.eval()
    with torch.no_grad():
        return float((head(Hte).argmax(1) == yte).float().mean())


# ----------------------------------------------------------------------------- verdict (pur)
def credit_verdict(unbiased_recs, biased_recs, keep_hi=0.50, collapse_lo=0.30):
    """Au régime le plus RARE (dernier point de chaque sweep) :
    BIAS_NOT_RARITY : le non-biaisé TIENT (>= keep_hi) mais le biaisé S'EFFONDRE (<= collapse_lo)
                      -> le mur in-world de T3 est le BIAIS (−0.5), pas la rareté. Correctif = retirer −0.5.
    RARITY_ALSO_FATAL : les deux s'effondrent au plus rare -> la rareté absolue tue aussi.
    BOTH_ROBUST / MIXED.
    """
    u, b = unbiased_recs[-1], biased_recs[-1]
    if u >= keep_hi and b <= collapse_lo:
        return "BIAS_NOT_RARITY"
    if u <= collapse_lo and b <= collapse_lo:
        return "RARITY_ALSO_FATAL"
    if u >= keep_hi and b >= keep_hi:
        return "BOTH_ROBUST"
    return "MIXED"


def _expected_correct(p_success, penalty):
    """Espérance analytique de récompense de l'action correcte (négative -> évitée)."""
    return p_success * 1.0 + (1.0 - p_success) * penalty


def _recovery(acc, chance, acc_sup):
    return (acc - chance) / (acc_sup - chance) if acc_sup > chance else float("nan")


def analyze(cap, seeds=(0, 1, 2), steps=1500, p_successes=(1.0, 0.3, 0.1, 0.03), penalty=-0.5):
    H, y = cap["H"], cap["correct"]
    _, chance = linear_probe_accuracy(H, y, seed=0)
    acc_sup = float(np.mean([_train_readout(H, y, "sup", s, steps=steps) for s in seeds]))

    def sweep(pen):
        out = []
        for p in p_successes:
            acc = float(np.mean([_train_rl_structured(H, y, p, pen, s, steps=steps) for s in seeds]))
            out.append({"p_success": p, "penalty": pen, "acc": acc,
                        "recovery": _recovery(acc, chance, acc_sup),
                        "E_correct": _expected_correct(p, pen)})
        return out

    unbiased = sweep(0.0)
    biased = sweep(penalty)
    verdict = credit_verdict([r["recovery"] for r in unbiased], [r["recovery"] for r in biased])
    return {"n": int(len(y)), "chance": chance, "acc_sup": acc_sup, "penalty": penalty,
            "unbiased": unbiased, "biased": biased, "verdict": verdict}


def _report(res):
    print("\n=== NAV-005 : le mur in-world du binding (EDR-172) — RARETE du crédit ou BIAIS ? ===")
    print(f"  n={res['n']}  chance={res['chance']:.3f}  plafond SUP={res['acc_sup']:.3f}  penalty biaisé={res['penalty']}")
    print("  -- NON-BIAISE (penalty=0 : récompenser les succès, NE PAS punir le bon geste non-payant) --")
    for r in res["unbiased"]:
        print(f"     p_success={r['p_success']:.2f}  E[correct]={r['E_correct']:+.2f}  recovery={r['recovery']:+.3f}")
    print(f"  -- BIAISE (penalty={res['penalty']} : structure de T3, throw sans kill puni) --")
    for r in res["biased"]:
        print(f"     p_success={r['p_success']:.2f}  E[correct]={r['E_correct']:+.2f}  recovery={r['recovery']:+.3f}")
    print("=== VERDICT ===")
    print(f"  -> {res['verdict']}")
    print("     (in-world T3 : kills ~6/300 -> p_success~0.02 << 1/3 -> E[correct]<0 sous penalty=-0.5 = effondrement PAR LE BIAIS)")
    return res


def main(speed=0.0, seed=1140, n_eval=6, max_ticks=150, steps=1500, _return=False):
    if torch is None:
        print("PyTorch indisponible -> banc saute.")
        return {"verdict": "SKIPPED_NO_TORCH"} if _return else None
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    torch.set_num_threads(1)
    with Harness(seed=seed, name="nav_credit_structure", with_db=False) as h:
        _disable_kuzu()
        base = h.seed
        seeds = [base + i for i in range(n_eval)]
        cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True, prey_speed_scale=speed)
        cap = capture(cfg, seeds, n_apex=0, max_ticks=max_ticks)
        res = analyze(cap, steps=steps)
        h.save({"speed": speed, "seed": base, "n_eval": n_eval, "steps": steps, **res})
        return _report(res) if not _return else res


if __name__ == "__main__":
    main(speed=float(os.getenv("NAV_SPEED", "0.0")),
         seed=int(os.getenv("EXPERIMENT_SEED", "1140")),
         n_eval=int(os.getenv("NAV_NEVAL", "6")),
         max_ticks=int(os.getenv("NAV_TICKS", "150")),
         steps=int(os.getenv("NAV_STEPS", "1500")))
