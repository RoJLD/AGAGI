"""tools/nav_signal_density.py — T1/NAV-004 : la FRONTIERE de recuperation du readout de navigation.

EDR-NAV-003 : sur H fige, un readout Linear(N->4) entraine par recompense RL DENSE et ALIGNEE recupere le
readout (recovery +0.92). Question suivante, decisive pour le design de shaping de T1 : jusqu'ou peut-on
DEGRADER le signal RL avant que la recuperation echoue ? Deux facons dont la recompense de forage in-world
echoue -> deux knobs de corruption INDEPENDANTS sur la recompense bandit :

  - SPARSITE rho (NON-BIAISE, moins de donnees) : fraction des pas qui recoivent un gradient (reste masque).
                   Modelise « la recompense ne se declenche qu'occasionnellement ».
  - BRUIT eta (NON-BIAISE, moins de signal) : parmi les pas recompenses, recompense = vrai-match avec proba
                   (1-eta), sinon Bernoulli(0.5) aleatoire (moyenne nulle -> variance, pas biais).
  - MISATTRIBUTION beta (BIAISE, MAUVAIS signal) : pour une fraction beta des pas, la recompense cible une
                   direction SYSTEMATIQUEMENT FAUSSE (y+1 mod 4). Modelise le vrai probleme de credit du
                   forage in-world : atteindre la proie attribue le credit au MAUVAIS pas.

Hypothese (contraste decisif) : la degradation NON-BIAISEE (sparsite, bruit) est indulgente (le readout
recupere avec un signal faible mais correct) ; la corruption BIAISEE (misattribution) EFFONDRE la recovery
SOUS le hasard (le readout apprend activement la mauvaise politique). Dit a T1 : le shaping doit etre ALIGNE
(non-biaise), la densite/variance sont secondaires. Controle a une variable. Reutilise capture()/
_train_readout() d'EDR-NAV-001/003. Tooling-only, deterministe. Usage : python -m tools.nav_signal_density
"""
import os

import numpy as np

from src.seed_ai.harness import Harness
from tools.lethality_curriculum import _disable_kuzu
from tools.lewis_survival_sweep import _cfg
from tools.nav_localization_probe import capture, linear_probe_accuracy
from tools.nav_readout_trainability import _split_zscore, _train_readout, N_CLASSES

try:
    import torch
except Exception:                                      # pragma: no cover
    torch = None


# ----------------------------------------------------------------------------- entrainement corrompu
def _train_rl_corrupt(H, y, sparsity, noise, misattr, seed, steps=1500, lr=1e-2, batch=256):
    """RL-bandit avec recompense corrompue par 3 knobs INDEPENDANTS. sparsity in (0,1] = proba qu'un pas
    contribue ; noise in [0,1] = proba de recompense ALEATOIRE (non-biaise) ; misattr in [0,1] = proba que
    la recompense cible une direction SYSTEMATIQUEMENT FAUSSE (y+1 mod 4, BIAISE). Meme init/split que
    _train_readout -> comparable. Retourne l'accuracy test (argmax glouton == y)."""
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
        target = ytr[idx]
        if misattr > 0:                                # BIAIS : cible une direction systematiquement fausse
            mis = torch.rand(len(a), generator=g) < misattr
            target = torch.where(mis, (target + 1) % N_CLASSES, target)
        reward = (a == target).float()
        if noise > 0:                                  # NON-BIAISE : remplace par un bruit Bernoulli(0.5)
            flip = torch.rand(len(a), generator=g) < noise
            rand_r = (torch.rand(len(a), generator=g) < 0.5).float()
            reward = torch.where(flip, rand_r, reward)
        chosen = logp[torch.arange(len(a)), a]
        adv = reward - baseline
        if sparsity < 1.0:                             # sparsite : masque une fraction des pas
            keep = torch.rand(len(a), generator=g) < sparsity
            if keep.sum() == 0:
                continue
            baseline = 0.99 * baseline + 0.01 * float(reward[keep].mean())
            loss = -(adv[keep] * chosen[keep]).mean()
        else:
            baseline = 0.99 * baseline + 0.01 * float(reward.mean())
            loss = -(adv * chosen).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    head.eval()
    with torch.no_grad():
        return float((head(Hte).argmax(1) == yte).float().mean())


# ----------------------------------------------------------------------------- verdict (pur)
def density_verdict(sparsity_recs, misattr_recs, keep_hi=0.50, collapse_lo=0.30):
    """Contraste NON-BIAISE (sparsite) vs BIAISE (misattribution), au point le plus dur de chaque sweep.

    BIAS_IS_FATAL   : la sparsite (non-biaisee) TIENT (min recovery >= keep_hi) mais la misattribution
                      (biaisee) S'EFFONDRE (min recovery <= collapse_lo) -> T1 : le shaping doit etre
                      ALIGNE ; densite/variance secondaires. (attendu)
    DENSITY_IS_FATAL: l'inverse (la sparsite casse, le biais non).
    BOTH_ROBUST     : les deux tiennent.
    BOTH_FRAGILE    : les deux s'effondrent.
    """
    s_min, m_min = min(sparsity_recs), min(misattr_recs)
    s_ok, m_ok = s_min >= keep_hi, m_min >= keep_hi
    s_bad, m_bad = s_min <= collapse_lo, m_min <= collapse_lo
    if s_ok and m_bad:
        return "BIAS_IS_FATAL"
    if m_ok and s_bad:
        return "DENSITY_IS_FATAL"
    if s_ok and m_ok:
        return "BOTH_ROBUST"
    if s_bad and m_bad:
        return "BOTH_FRAGILE"
    return "MIXED"


def _recovery(acc, chance, acc_sup):
    return (acc - chance) / (acc_sup - chance) if acc_sup > chance else float("nan")


def analyze(cap, seeds=(0, 1, 2), steps=1500,
            sparsities=(1.0, 0.1, 0.03, 0.01), noises=(0.0, 0.5, 0.9, 1.0), misattrs=(0.0, 0.3, 0.6, 1.0)):
    H, y = cap["H"], cap["correct"]
    _, chance = linear_probe_accuracy(H, y, seed=0)
    acc_sup = float(np.mean([_train_readout(H, y, "sup", s, steps=steps) for s in seeds]))

    def sweep(key, values, mk):
        out = []
        for v in values:
            sp_, no_, mi_ = mk(v)
            acc = float(np.mean([_train_rl_corrupt(H, y, sp_, no_, mi_, s, steps=steps) for s in seeds]))
            out.append({key: v, "acc": acc, "recovery": _recovery(acc, chance, acc_sup)})
        return out

    sp = sweep("rho", sparsities, lambda v: (v, 0.0, 0.0))     # NON-BIAISE : moins de donnees
    no = sweep("eta", noises, lambda v: (1.0, v, 0.0))         # NON-BIAISE : moins de signal
    mi = sweep("beta", misattrs, lambda v: (1.0, 0.0, v))      # BIAISE : mauvais signal
    verdict = density_verdict([r["recovery"] for r in sp], [r["recovery"] for r in mi])
    return {"n": int(len(y)), "chance": chance, "acc_sup": acc_sup,
            "sparsity": sp, "noise": no, "misattr": mi, "verdict": verdict}


def _report(res):
    print("\n=== NAV-004 : frontiere de recuperation du readout de navigation (recovery vs signal degrade) ===")
    print(f"  n={res['n']}  chance={res['chance']:.3f}  plafond SUPERVISE acc={res['acc_sup']:.3f}")
    print("  -- SPARSITE rho (NON-BIAISE, moins de donnees) --")
    for r in res["sparsity"]:
        print(f"     rho={r['rho']:.2f}   acc={r['acc']:.3f}  recovery={r['recovery']:+.3f}")
    print("  -- BRUIT eta (NON-BIAISE, moins de signal) --")
    for r in res["noise"]:
        print(f"     eta={r['eta']:.2f}   acc={r['acc']:.3f}  recovery={r['recovery']:+.3f}")
    print("  -- MISATTRIBUTION beta (BIAISE, mauvais signal) --")
    for r in res["misattr"]:
        print(f"     beta={r['beta']:.2f}  acc={r['acc']:.3f}  recovery={r['recovery']:+.3f}")
    print("=== VERDICT ===")
    print(f"  -> {res['verdict']}  (non-biaise=sparsite vs biaise=misattribution)")
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
    with Harness(seed=seed, name="nav_signal_density", with_db=False) as h:
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
