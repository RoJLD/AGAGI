"""tools/nav_readout_trainability.py — T1/M1 offline : le readout de NAVIGATION est-il recuperable
par CREDIT RL, ou exige-t-il des cibles SUPERVISEES ? (de-risque la fourche de conception de T1).

EDR-NAV-001 : H decode la direction-correcte a ~0.81 (ridge) MAIS l'agent emet le bon pas a 0.03
(READOUT_GAP). Le champion a evolue SOUS RL (recompense de forage) et n'a PAS appris ce readout. Question
qui decide l'archi de T1 (cf. HANDOFF_T1_NAV_readout_brief.md, fourche 'aux supervise vs pur RL') :
sur les MEMES paires (H, correct) FIGEES, un readout Linear(N->4) frais atteint-il le plafond via une
recompense RL clairsemee, ou seulement via des cibles supervisees ?

Controle a UNE variable (comme EDR-COG-001) : meme architecture, meme init au seed, meme split, meme
optimiseur/lr/steps -> SEULE la perte differe :
  - SUP : cross-entropy sur l'oracle (plafond, ~= ridge 0.81)
  - RL  : REINFORCE-bandit contextuel, recompense = 1 si l'action echantillonnee == oracle, baseline EMA
          (signal per-pas DENSE et parfaitement aligne = BORNE SUPERIEURE de ce que le RL peut faire ;
           le forage reel est plus clairseme/desaligne -> s'il echoue ici, il echoue a fortiori en monde)

Verdict : RL_RECOVERS (le readout est RL-recuperable -> T1 doit fournir un signal per-pas dense, l'aux
supervise le fait) vs CREDIT_GATED (meme un RL dense echoue -> exige de VRAIES cibles supervisees).

Reutilise capture() d'EDR-NAV-001 (cohorte fixe, oracle 114). Tooling-only. Usage :
  python -m tools.nav_readout_trainability
"""
import os

import numpy as np

from src.seed_ai.harness import Harness, seed_at
from tools.lethality_curriculum import _disable_kuzu
from tools.lewis_survival_sweep import _cfg
from tools.nav_localization_probe import capture, linear_probe_accuracy, MOVE_CLASSES

try:
    import torch
except Exception:                                      # pragma: no cover
    torch = None

N_CLASSES = len(MOVE_CLASSES)                           # 4 : N/S/E/O


# ----------------------------------------------------------------------------- verdict (pur)
def readout_verdict(acc_sup, acc_rl, chance, target_margin=0.10, recover_hi=0.70, recover_lo=0.30):
    """Le readout de navigation est-il recuperable par credit RL ?

    - acc_sup : plafond supervise (CE sur l'oracle). Si acc_sup - chance < target_margin -> INVALID_TARGET
      (le readout n'est meme pas apprenable en supervise -> cible mal posee).
    - recovery = (acc_rl - chance) / (acc_sup - chance) : fraction du plafond au-dessus du hasard que le RL
      recupere.

    RL_RECOVERS  : recovery >= recover_hi  (le RL dense suffit -> T1 = fournir un signal per-pas dense)
    CREDIT_GATED : recovery <= recover_lo  (meme un RL dense echoue -> T1 = vraies cibles supervisees)
    PARTIAL      : entre les deux
    """
    if acc_sup - chance < target_margin:
        return "INVALID_TARGET"
    recovery = (acc_rl - chance) / (acc_sup - chance)
    if recovery >= recover_hi:
        return "RL_RECOVERS"
    if recovery <= recover_lo:
        return "CREDIT_GATED"
    return "PARTIAL"


# ----------------------------------------------------------------------------- entrainement (impur)
def _split_zscore(H, y, seed, test_frac=0.3):
    """Split train/test deterministe + z-score sur stats TRAIN (pas de fuite). Retourne tenseurs torch."""
    n = len(y)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    n_te = max(1, int(round(n * test_frac)))
    te, tr = perm[:n_te], perm[n_te:]
    mu, sd = H[tr].mean(0), H[tr].std(0) + 1e-8
    Htr = ((H[tr] - mu) / sd).astype(np.float32)
    Hte = ((H[te] - mu) / sd).astype(np.float32)
    return (torch.from_numpy(Htr), torch.from_numpy(y[tr].astype(np.int64)),
            torch.from_numpy(Hte), torch.from_numpy(y[te].astype(np.int64)))


def _train_readout(H, y, mode, seed, steps=1500, lr=1e-2, batch=256):
    """Entraine un readout Linear(N->4) sur (H, y) FIGES. mode='sup' (CE) ou 'rl' (REINFORCE-bandit).
    Meme init/split/optim quel que soit le mode -> seule la perte differe. Retourne l'accuracy test
    (argmax(head(H))==y), la meme metrique dans les 2 bras (le RL est evalue en GLOUTON, pas echantillonne)."""
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
        if mode == "sup":
            loss = F.cross_entropy(logits, ytr[idx])
        else:  # RL bandit contextuel : echantillonne une action, recompense = match oracle
            logp = F.log_softmax(logits, dim=1)
            a = torch.multinomial(logp.exp(), 1, generator=g).squeeze(1)
            reward = (a == ytr[idx]).float()
            baseline = 0.99 * baseline + 0.01 * float(reward.mean())
            chosen = logp[torch.arange(len(a)), a]
            loss = -((reward - baseline) * chosen).mean()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    head.eval()
    with torch.no_grad():
        acc = float((head(Hte).argmax(1) == yte).float().mean())
    return acc


def analyze(cap, seeds=(0, 1, 2), steps=1500):
    """Compare readout SUPERVISE vs RL sur (H, correct) figes, sur plusieurs inits torch. Le ridge d'EDR
    NAV-001 sert de reference externe du plafond."""
    H, y = cap["H"], cap["correct"]
    acc_ridge, chance = linear_probe_accuracy(H, y, seed=0)
    sup = [_train_readout(H, y, "sup", s, steps=steps) for s in seeds]
    rl = [_train_readout(H, y, "rl", s, steps=steps) for s in seeds]
    acc_sup, acc_rl = float(np.mean(sup)), float(np.mean(rl))
    verdict = readout_verdict(acc_sup, acc_rl, chance)
    return {"n": int(len(y)), "chance": chance, "acc_ridge": acc_ridge,
            "acc_sup": acc_sup, "acc_rl": acc_rl, "sup_seeds": sup, "rl_seeds": rl,
            "recovery": (acc_rl - chance) / (acc_sup - chance) if acc_sup > chance else float("nan"),
            "verdict": verdict}


def _report(res):
    print("\n=== T1/M1 : le readout de NAVIGATION est-il RL-recuperable ou exige-t-il du supervise ? ===")
    print(f"  n(agent-ticks)={res['n']}  chance={res['chance']:.3f}  ridge(NAV-001)={res['acc_ridge']:.3f}")
    print(f"  SUPERVISE (CE oracle)   acc={res['acc_sup']:.3f}   seeds={['%.3f' % a for a in res['sup_seeds']]}")
    print(f"  RL (REINFORCE-bandit)   acc={res['acc_rl']:.3f}   seeds={['%.3f' % a for a in res['rl_seeds']]}")
    print(f"  recovery (RL/plafond au-dessus du hasard)={res['recovery']:+.3f}")
    print("=== VERDICT ===")
    print(f"  -> {res['verdict']}")
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
    with Harness(seed=seed, name="nav_readout_trainability", with_db=False) as h:
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
