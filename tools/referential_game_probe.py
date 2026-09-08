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
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, famille run_* -- 7e elargissement du cliquet). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte
    # vide / un horizon nul rend 0.0 ou nan comme une MESURE que l'aval lit comme un resultat
    # (biais negatif systematique du depot). Posee AVANT toute construction -> refus < 0.5 s.
    if int(episodes) <= 0 or int(n_agents) < 2 or not (2 <= int(K) <= _MOVE) or not (2 <= int(V) <= _MOVE):
        raise ValueError(
            f"run_lewis : argument degenere (episodes={episodes}, n_agents={n_agents}, K={K}, V={V}, _MOVE={_MOVE}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    # Pas de gate : crédit épisodique pur (politique standard).
    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    # P2.27 : substrat EPINGLE -- attribut de CLASSE, sinon herite de l ambiant du
    # processus. Pose AVANT make_population : U/V/W_bl ne sont crees qu a la construction.
    TorchPopulationModel.BILINEAR = False
    try:
        sender = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        receiver = make_population([MambaAgent() for _ in range(n_agents)], backend="torch")
        sender.opt = torch.optim.Adam(
            [sender.W] + [p for p in (sender.U, sender.V, sender.W_bl) if p is not None], lr=lr)
        receiver.opt = torch.optim.Adam(
            [receiver.W] + [p for p in (receiver.U, receiver.V, receiver.W_bl) if p is not None], lr=lr)
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
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR) = saved


def main():
    import math
    import statistics

    from tools.experiment_preflight import assert_bar_separates_the_incapable

    episodes = int(os.environ.get("RGP_EPISODES", "1500"))
    seeds = list(range(int(os.environ.get("RGP_SEEDS", "3"))))
    K = int(os.environ.get("RGP_K", "6"))
    V = int(os.environ.get("RGP_V", "8"))
    # `n_agents` etait implicite (defaut 128 de `run_lewis`) ; il est desormais EXPLICITE parce que la
    # barre d'emergence en depend (erreur-type d'echantillonnage). Meme valeur par defaut : rien ne bouge.
    n_agents = int(os.environ.get("RGP_AGENTS", "128"))
    rows = [run_lewis(episodes=episodes, n_agents=n_agents, K=K, V=V, seed=s) for s in seeds]
    chance = 1.0 / K
    af = statistics.median(r["acc_fiable"] for r in rows)
    ab = statistics.median(r["acc_brouille"] for r in rows)
    al = statistics.median(r["acc_late"] for r in rows)
    print(f"K={K} V={V} chance={chance:.2f}")
    print(f"acc_late (train) median={al:.3f}  |  FIABLE median={af:.3f}  BROUILLE median={ab:.3f}  "
          f"per-seed fiable={['%.2f' % r['acc_fiable'] for r in rows]}")
    # ⚠️ P2.15 (2026-09-08) — la barre d'ÉMERGENCE était `chance + 0.10`, posée à l'estime. Cette sonde
    # porte pourtant SON PROPRE INCAPABLE : le bras BROUILLÉ est un agent ENTRAÎNÉ dont le canal ne
    # transporte RIEN. C'est le meilleur plafond possible — mesuré dans le MÊME run, au MÊME régime,
    # sur les MÊMES seeds — et il n'y avait aucune raison d'aller chercher un seuil ailleurs.
    # Un plafond est un MAX, pas une médiane : on prend le max sur les seeds, plus une erreur-type.
    # Vérifié sur les valeurs publiées (LANG-001) : BROUILLÉ 0.17 -> barre 0.203, contre `chance + 0.10
    # = 0.267` ; FIABLE 0.767 franchit les deux, le verdict publié est INCHANGÉ. L'ancienne barre
    # séparait donc bien — mais personne ne l'avait montré, et c'est cela que P2.15 corrige.
    plafond_incapable = max(r["acc_brouille"] for r in rows)
    # ⚠️ `n_eval` = nombre d'AGENTS, pas combos x agents. C'est DELIBERE et conservateur : l'erreur-type
    # en est SUR-estimee, donc la barre est plus HAUTE, donc plus dure a franchir. L'unite de replication
    # du depot est le seed, pas l'agent (les agents d'un seed partagent entrainement et tirages) ;
    # compter combos x agents comme independants serait le choix OPTIMISTE, celui qui abaisse la barre.
    se = math.sqrt(max(plafond_incapable * (1.0 - plafond_incapable), 0.0) / max(n_agents, 1))
    bar_emergence = plafond_incapable + se
    assert_bar_separates_the_incapable(
        bar_emergence, plafond_incapable,
        "plafond du bras BROUILLE (agent ENTRAINE dont le canal ne transporte rien), MAX sur les seeds "
        "du MEME run, plus une erreur-type -- incapable mesure DANS le dispositif, au regime configure",
        label="barre d'emergence de la signalisation")
    emerges = af > bar_emergence
    content = af > ab + 0.10
    verdict = ("FUNCTIONAL_REFERENTIAL_SIGNALING" if emerges and content else
               "SIGNALING_BUT_CONTENT_FREE" if emerges else "NO_SIGNALING_EMERGES")
    print(f"VERDICT={verdict} : emerge={emerges} (FIABLE {af:.2f} vs barre MESUREE "
          f"{bar_emergence:.3f} = plafond BROUILLE {plafond_incapable:.3f} + 1 erreur-type), "
          f"content_porteur={content} (FIABLE {af:.2f} vs BROUILLE {ab:.2f})")


if __name__ == "__main__":
    main()
