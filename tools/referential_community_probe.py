"""La signalisation référentielle du substrat torch est-elle un PROTOCOLE PARTAGÉ ou des CODES PRIVÉS ?
(Arc 4 langage, LANG-002 — suite de LANG-001, clôt son caveat #2 : coordination appariée ≠ langage.)

LANG-001 a montré que 128 paires APPARIÉES sender_i<->receiver_i développent une signalisation
référentielle porteuse (FIABLE 0.77 vs chance/BROUILLÉ). MAIS un batch torch = 128 politiques DISTINCTES
(W (B,N,N), bmm par agent) : chaque paire i pouvait inventer un code PRIVÉ (mapping cible->symbole
arbitraire, propre à la paire) — coordination, pas convention partagée. Le vrai marqueur de « langage »
est la MUTUALITÉ : un receiver comprend-il un sender qu'il n'a JAMAIS co-entraîné ?

Levier testé = ROTATION DE PARTENAIRES. À chaque épisode on apparie sender_i <-> receiver_{(i+s) mod B}
par un décalage cyclique s (np.roll) :
- FIXED (rotate=False) : s=0 toujours (réplique LANG-001, paires figées).
- ROTATION (rotate=True) : s tiré aléatoire non-nul -> chaque sender parle à des receivers variés ->
  pression de CONVENTIONNALISATION (effet communauté).

Métrique = intelligibilité mutuelle. À l'éval, accuracy WITHIN (s=0, paire d'origine) vs CROSS (moyenne
sur décalages s>0, partenaires JAMAIS appariés directement). MI = (cross-chance)/(within-chance) :
- codes PRIVÉS -> cross ~ chance -> MI ~ 0.
- protocole PARTAGÉ -> cross ~ within -> MI ~ 1.

Prédiction : FIXED -> MI~0 (privé) ; ROTATION -> MI eleve (partagé). La rotation CAUSE le protocole partagé.

Usage : python tools/referential_community_probe.py   (env: RCP_EPISODES, RCP_SEEDS, RCP_K, RCP_V)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_community(episodes: int = 2000, n_agents: int = 128, K: int = 6, V: int = 8,
                  seed: int = 0, lr: float = 0.05, rotate: bool = True, eval_shifts: int = 8):
    """Entraîne 128 senders + 128 receivers (politiques distinctes, batch torch) sur le jeu référentiel,
    en appariant sender_i<->receiver_{i+s}. rotate=False => s=0 (paires figées, LANG-001) ; rotate=True =>
    s aléatoire non-nul par épisode (conventionnalisation). Renvoie within/cross/MI et chance."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    try:
        sender = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        receiver = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        sender.opt = torch.optim.Adam([sender.W], lr=lr)
        receiver.opt = torch.optim.Adam([receiver.W], lr=lr)
        I = sender.I
        rng = np.random.RandomState(seed + 1)

        def _onehot(idx, size):
            m = np.zeros((n_agents, I), dtype=np.float32)
            m[np.arange(n_agents), idx % size] = 1.0
            return m

        def _sample(preds, n):
            p = _softmax_np(np.asarray(preds)[:, :n])
            return np.array([rng.choice(n, p=pi) for pi in p])

        def _signal(targets):
            sender.H = torch.zeros((n_agents, sender.N))
            preds_s, _ = sender.forward(_onehot(targets, K))
            return _sample(preds_s, V)

        def _guess(signal):
            receiver.H = torch.zeros((n_agents, receiver.N))
            preds_r, _ = receiver.forward(_onehot(signal, V))
            return _sample(preds_r, K)

        for _ in range(episodes):
            targets = rng.randint(0, K, size=n_agents)
            signal = _signal(targets)
            s = rng.randint(1, n_agents) if rotate else 0     # décalage d'appariement de l'épisode
            recv_sig = np.roll(signal, s)                       # receiver_j lit le signal de sender_{j-s}
            recv_tgt = np.roll(targets, s)                      # ... et vise sa cible
            guess = _guess(recv_sig)
            reward = (guess == recv_tgt).astype(np.float32)     # indexé par receiver j
            snd_reward = np.roll(reward, -s)                    # sender_i recolte la reward de receiver_{i+s}
            receiver.learn_episode([_onehot(recv_sig, V)],
                                   [[{"move": int(g)} for g in guess]],
                                   reward - reward.mean(), gate_last_only=False)
            sender.learn_episode([_onehot(targets, K)],
                                 [[{"move": int(x)} for x in signal]],
                                 snd_reward - snd_reward.mean(), gate_last_only=False)

        # --- éval greedy : WITHIN (s=0) vs CROSS (partenaires jamais appariés directement) ---
        def _eval_shift(s):
            hits = []
            for _ in range(30):
                targets = rng.randint(0, K, size=n_agents)
                sender.H = torch.zeros((n_agents, sender.N))
                ps, _ = sender.forward(_onehot(targets, K))
                sig = np.asarray(ps)[:, :V].argmax(axis=1)
                recv_sig = np.roll(sig, s)
                recv_tgt = np.roll(targets, s)
                receiver.H = torch.zeros((n_agents, receiver.N))
                pr, _ = receiver.forward(_onehot(recv_sig, V))
                guess = np.asarray(pr)[:, :K].argmax(axis=1)
                hits.append((guess == recv_tgt).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        within = _eval_shift(0)
        # décalages non-nuls répartis sur la communauté (partenaires distincts jamais co-appariés en FIXED)
        shifts = sorted({max(1, (j * n_agents) // (eval_shifts + 1)) for j in range(1, eval_shifts + 1)})
        cross = float(np.mean([_eval_shift(s) for s in shifts]))
        chance = 1.0 / K
        # MI = fraction du skill within qui transfère à un partenaire neuf. Défini seulement si le régime
        # a APPRIS (within nettement > chance) ; sinon le dénominateur ~0 rend le ratio ininterprétable.
        learned = within > chance + 0.05
        mi = max(-1.0, min(2.0, (cross - chance) / (within - chance))) if learned else float("nan")
        return {"seed": int(seed), "K": K, "V": V, "rotate": bool(rotate), "chance": chance,
                "within": within, "cross": cross, "mi": mi, "learned": bool(learned)}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def main():
    import statistics
    episodes = int(os.environ.get("RCP_EPISODES", "3000"))
    seeds = list(range(int(os.environ.get("RCP_SEEDS", "2"))))
    K = int(os.environ.get("RCP_K", "6"))
    V = int(os.environ.get("RCP_V", "8"))
    # Taille de communauté : le consensus sous rotation devient plus dur quand M grandit (goulot de
    # conventionnalisation) -> défaut sur une taille traitable qui reproduit le protocole PARTAGÉ.
    M = int(os.environ.get("RCP_AGENTS", "16"))

    def _med(rows, key):
        vals = [r[key] for r in rows if not (r[key] != r[key])]   # ignore NaN (régime non-appris)
        return statistics.median(vals) if vals else float("nan")

    def _cell(rotate):
        rows = [run_community(episodes=episodes, n_agents=M, K=K, V=V, seed=s, rotate=rotate,
                              eval_shifts=min(6, M - 1)) for s in seeds]
        return (_med(rows, "within"), _med(rows, "cross"), _med(rows, "mi"))

    chance = 1.0 / K
    fw, fc, fmi = _cell(False)
    rw, rc, rmi = _cell(True)
    print(f"K={K} V={V} chance={chance:.2f} episodes={episodes} seeds={len(seeds)} agents={M}")
    print(f"FIXED     within={fw:.3f} cross={fc:.3f} MI={fmi:.2f}")
    print(f"ROTATION  within={rw:.3f} cross={rc:.3f} MI={rmi:.2f}")
    # Le discriminant robuste = le CROSS (accuracy à un partenaire jamais co-appraié) : code privé -> cross
    # ~chance ; protocole partagé -> cross >> chance. La rotation doit le hisser bien au-dessus du fixed.
    d_cross = rc - fc
    shared = rc > chance + 0.10 and d_cross > 0.15 and (rmi == rmi and rmi > 0.5)
    verdict = ("PARTNER_ROTATION_YIELDS_SHARED_PROTOCOL" if shared else
               "ROTATION_HELPS_PARTIAL" if d_cross > 0.08 else
               "NO_SHARED_PROTOCOL_FIXED_STAYS_PRIVATE")
    print(f"VERDICT={verdict} : d_cross(rot-fix)={d_cross:+.3f}  "
          f"(FIXED code {'PRIVE (cross~chance)' if fc < chance + 0.08 else 'partage'}, "
          f"ROTATION MI={rmi:.2f})")


if __name__ == "__main__":
    main()
