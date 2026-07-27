"""Le substrat torch développe-t-il une SIGNALISATION RÉFÉRENTIELLE fonctionnelle ? (Arc 4 langage, roadmap SCIENCE #1)

Proxy synthétique de capacité, en amont de l'in-world 087 (FIABLE vs BROUILLÉ) — même méthode que les
proxies H-unif : teste la CAPACITÉ hors biosphère, sans toucher le code monde partagé.

Jeu de Lewis (référentiel) à 2 populations torch APPARIÉES :
- SENDER voit une cible (one-hot parmi K référents) -> émet un SIGNAL (symbole parmi V).
- RECEIVER voit le SIGNAL (one-hot, PAS la cible) -> devine le référent (parmi K).
- Récompense partagée +1 si devine == cible (coordination). Crédit ÉPISODIQUE (learn_episode, EDR-158),
  pas de gate (politique standard : sender obs->signal, receiver obs->guess).

Deux questions :
1. Une signalisation ÉMERGE-t-elle ? (accuracy >> chance 1/K)
2. Le CONTENU du signal est-il PORTEUR ? test FIABLE vs BROUILLÉ : à l'éval, remplacer le signal du sender
   par un signal ALÉATOIRE (décorrélé de la cible). Si acc(FIABLE) >> acc(BROUILLÉ≈chance) -> le succès
   DÉPEND du contenu référentiel (analogue synthétique de 087).

Usage : python tools/referential_game_probe.py   (env: RGP_EPISODES, RGP_SEEDS, RGP_K, RGP_V)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_MOVE = 8   # logits d'action disponibles => K, V <= 8


def _softmax_np(z):
    import numpy as np
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def run_lewis(episodes: int = 1500, n_agents: int = 128, K: int = 6, V: int = 8,
              seed: int = 0, lr: float = 0.05):
    """Entraîne sender+receiver (2 pops torch appariées) sur le jeu référentiel. Renvoie accuracy_late
    (signal FIABLE), accuracy_brouille (signal aléatoire à l'éval), chance=1/K, et le gap fiable-brouillé."""
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    # Pas de gate : crédit épisodique pur (politique standard).
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

        acc_hist = []
        for _ in range(episodes):
            targets = rng.randint(0, K, size=n_agents)              # cible par agent
            sender.H = torch.zeros((n_agents, sender.N))
            preds_s, _ = sender.forward(_onehot(targets, K))
            signal = _sample(preds_s, V)                            # symbole émis
            receiver.H = torch.zeros((n_agents, receiver.N))
            preds_r, _ = receiver.forward(_onehot(signal, V))
            guess = _sample(preds_r, K)                             # référent deviné
            reward = (guess == targets).astype(np.float32)          # coordination partagée
            adv = reward - reward.mean()
            sender.learn_episode([_onehot(targets, K)],
                                 [[{"move": int(s)} for s in signal]], adv, gate_last_only=False)
            receiver.learn_episode([_onehot(signal, V)],
                                   [[{"move": int(g)} for g in guess]], adv, gate_last_only=False)
            acc_hist.append(reward)

        q = max(1, episodes // 4)
        acc_late = float(np.mean(np.concatenate(acc_hist[-q:])))

        # --- éval FIABLE vs BROUILLÉ (greedy, sans apprentissage) ---
        def _eval(brouille):
            hits = []
            for _ in range(40):
                targets = rng.randint(0, K, size=n_agents)
                sender.H = torch.zeros((n_agents, sender.N))
                ps, _ = sender.forward(_onehot(targets, K))
                sig = np.asarray(ps)[:, :V].argmax(axis=1)
                if brouille:
                    sig = rng.randint(0, V, size=n_agents)          # signal DÉCORRÉLÉ de la cible
                receiver.H = torch.zeros((n_agents, receiver.N))
                pr, _ = receiver.forward(_onehot(sig, V))
                guess = np.asarray(pr)[:, :K].argmax(axis=1)
                hits.append((guess == targets).astype(np.float32))
            return float(np.mean(np.concatenate(hits)))

        return {"seed": int(seed), "K": K, "V": V, "chance": 1.0 / K,
                "acc_late": acc_late, "acc_fiable": _eval(False), "acc_brouille": _eval(True)}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def main():
    import statistics
    episodes = int(os.environ.get("RGP_EPISODES", "1500"))
    seeds = list(range(int(os.environ.get("RGP_SEEDS", "3"))))
    K = int(os.environ.get("RGP_K", "6"))
    V = int(os.environ.get("RGP_V", "8"))
    rows = [run_lewis(episodes=episodes, K=K, V=V, seed=s) for s in seeds]
    chance = 1.0 / K
    af = statistics.median(r["acc_fiable"] for r in rows)
    ab = statistics.median(r["acc_brouille"] for r in rows)
    al = statistics.median(r["acc_late"] for r in rows)
    print(f"K={K} V={V} chance={chance:.2f}")
    print(f"acc_late (train) median={al:.3f}  |  FIABLE median={af:.3f}  BROUILLE median={ab:.3f}  "
          f"per-seed fiable={['%.2f' % r['acc_fiable'] for r in rows]}")
    emerges = af > chance + 0.10
    content = af > ab + 0.10
    verdict = ("FUNCTIONAL_REFERENTIAL_SIGNALING" if emerges and content else
               "SIGNALING_BUT_CONTENT_FREE" if emerges else "NO_SIGNALING_EMERGES")
    print(f"VERDICT={verdict} : emerge={emerges} (FIABLE {af:.2f} vs chance {chance:.2f}), "
          f"content_porteur={content} (FIABLE {af:.2f} vs BROUILLE {ab:.2f})")


if __name__ == "__main__":
    main()
