"""Le protocole émergent du substrat torch est-il STRUCTURELLEMENT COMPOSITIONNEL ? (Arc 4, LANG-003)

LANG-001 : signalisation référentielle porteuse. LANG-002 : sous rotation de partenaires, protocole
PARTAGÉ (vs codes privés). Ces deux tests portent sur des référents ATOMIQUES (un symbole = un référent).
Un vrai langage DÉCOMPOSE le sens : référent = (attribut1, attribut2), message = 2 symboles, et le protocole
GÉNÉRALISE à des combinaisons JAMAIS VUES (systématicité). C'est le test-or de l'emergent-comm.

Jeu référentiel compositionnel (2 populations torch distinctes, crédit épisodique, sans gate) :
- SENDER voit un référent (a0, a1) in [0,A)^2 -> émet un MESSAGE de 2 symboles (rollout 2 pas, indicé par
  position : obs = référent complet + drapeau de position ; H porté). Le sender PEUT encoder de façon
  holistique (chaque symbole = f(a0,a1)) ou compositionnelle (symbole_t = f(a_t)) — non pré-câblé.
- RECEIVER lit le MESSAGE complet (2 symboles) -> prédit les DEUX attributs (rollout 2 pas, position -> quel
  attribut sortir ; obs = message complet aux deux pas). Récompense partagée = fraction d'attributs corrects.

Test = GÉNÉRALISATION ZÉRO-SHOT. Entraînement sur un SOUS-ENSEMBLE des A^2 combos (held-out = diagonale) ;
éval sur les combos held-out (jamais vus, mais chaque VALEUR d'attribut vue ailleurs). Code compositionnel
-> zéro-shot >> chance (1/A) ; code holistique -> zéro-shot ~ chance.

Levier = ROTATION de partenaires (LANG-002) : l'effet communauté augmente-t-il la compositionnalité ?
FIXED (paires figées) vs ROTATION (partenaire aléatoire/épisode) sur le gap zéro-shot.

Usage : python tools/compositional_language_probe.py  (env: CLP_EPISODES, CLP_SEEDS, CLP_A, CLP_V, CLP_AGENTS)
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


def run_compositional(episodes: int = 5000, n_agents: int = 16, A: int = 3, V: int = 6,
                      seed: int = 0, lr: float = 0.05, rotate: bool = True, warmstart_fixed: int = 0):
    """Entraîne sender+receiver sur le jeu compositionnel (référents (a0,a1), messages 2-symboles), en
    tenant la DIAGONALE (a,a) hors entraînement. Renvoie within (combos vus), zeroshot (combos held-out),
    topsim, et cross_mi (intelligibilité mutuelle croisée), + chance=1/A. rotate=True apparie
    sender_i<->receiver_{i+s} (décalage aléatoire/épisode). warmstart_fixed>0 (LANG-004) : ce nombre
    d'épisodes INITIAUX est joué en PAIRES FIGÉES (s=0) avant la phase `rotate` -> curriculum dyade->rotation
    (warm-start d'un code compositionnel avant de le partager)."""
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

        combos = [(i, j) for i in range(A) for j in range(A)]
        heldout = [(k, k) for k in range(A)]                       # diagonale = combos jamais entraînés
        train = [c for c in combos if c not in heldout]            # chaque VALEUR d'attribut reste vue
        train_arr = np.array(train)

        def _sender_obs(a0, a1, pos):
            """[a0_onehot(A), a1_onehot(A), position_onehot(2)] dans les I premières dims."""
            m = np.zeros((n_agents, I), dtype=np.float32)
            m[np.arange(n_agents), a0 % A] = 1.0
            m[np.arange(n_agents), A + (a1 % A)] = 1.0
            m[:, 2 * A + pos] = 1.0
            return m

        def _recv_obs(s0, s1, pos):
            """[s0_onehot(V), s1_onehot(V), position_onehot(2)] : message complet aux deux pas."""
            m = np.zeros((n_agents, I), dtype=np.float32)
            m[np.arange(n_agents), s0 % V] = 1.0
            m[np.arange(n_agents), V + (s1 % V)] = 1.0
            m[:, 2 * V + pos] = 1.0
            return m

        def _sample(preds, n):
            p = _softmax_np(np.asarray(preds)[:, :n])
            return np.array([rng.choice(n, p=pi) for pi in p])

        def _message(a0, a1, greedy=False):
            sender.H = torch.zeros((n_agents, sender.N))
            o0 = _sender_obs(a0, a1, 0)
            p0, _ = sender.forward(o0)                              # H porté au pas suivant
            o1 = _sender_obs(a0, a1, 1)
            p1, _ = sender.forward(o1)
            if greedy:
                s0 = np.asarray(p0)[:, :V].argmax(axis=1)
                s1 = np.asarray(p1)[:, :V].argmax(axis=1)
            else:
                s0 = _sample(p0, V)
                s1 = _sample(p1, V)
            return s0, s1, o0, o1

        def _decode(s0, s1, greedy=False):
            receiver.H = torch.zeros((n_agents, receiver.N))
            r0 = _recv_obs(s0, s1, 0)
            q0, _ = receiver.forward(r0)
            r1 = _recv_obs(s0, s1, 1)
            q1, _ = receiver.forward(r1)
            if greedy:
                g0 = np.asarray(q0)[:, :A].argmax(axis=1)
                g1 = np.asarray(q1)[:, :A].argmax(axis=1)
            else:
                g0 = _sample(q0, A)
                g1 = _sample(q1, A)
            return g0, g1, r0, r1

        for ep in range(warmstart_fixed + episodes):
            # curriculum (LANG-004) : phase 1 = paires FIGÉES (warm-start du code) ; phase 2 = `rotate`
            phase_rotate = rotate and ep >= warmstart_fixed
            idx = rng.randint(0, len(train), size=n_agents)
            a0, a1 = train_arr[idx, 0], train_arr[idx, 1]
            s0, s1, o0, o1 = _message(a0, a1)
            s = rng.randint(1, n_agents) if phase_rotate else 0    # appariement sender_i<->receiver_{i+s}
            rs0, rs1 = np.roll(s0, s), np.roll(s1, s)              # receiver_j lit le message de sender_{j-s}
            ra0, ra1 = np.roll(a0, s), np.roll(a1, s)             # ... et vise SES attributs
            g0, g1, r0, r1 = _decode(rs0, rs1)
            rew = 0.5 * (g0 == ra0) + 0.5 * (g1 == ra1)            # fraction d'attributs corrects (receiver j)
            rew = rew.astype(np.float32)
            snd_rew = np.roll(rew, -s)                             # sender_i récolte la reward de receiver_{i+s}
            receiver.learn_episode([r0, r1],
                                   [[{"move": int(x)} for x in g0], [{"move": int(x)} for x in g1]],
                                   rew - rew.mean(), gate_last_only=False)
            sender.learn_episode([o0, o1],
                                 [[{"move": int(x)} for x in s0], [{"move": int(x)} for x in s1]],
                                 snd_rew - snd_rew.mean(), gate_last_only=False)

        # --- éval greedy : within/zeroshot en paire d'origine (shift=0) ; cross-MI en partenaire décalé ---
        def _acc_over(comboset, shift=0):
            accs = []
            for (a0v, a1v) in comboset:
                a0 = np.full(n_agents, a0v)
                a1 = np.full(n_agents, a1v)
                s0, s1, _, _ = _message(a0, a1, greedy=True)
                rs0, rs1 = np.roll(s0, shift), np.roll(s1, shift)  # receiver_j décode le msg de sender_{j-shift}
                ra0, ra1 = np.roll(a0, shift), np.roll(a1, shift)
                g0, g1, _, _ = _decode(rs0, rs1, greedy=True)
                accs.append(0.5 * (g0 == ra0) + 0.5 * (g1 == ra1))
            return float(np.mean(np.concatenate(accs)))

        within = _acc_over(train, 0)
        zeroshot = _acc_over(heldout, 0)
        # intelligibilité mutuelle croisée (LANG-002 porté au 2-attributs) : un partenaire jamais co-apparié
        # décode-t-il le message ? code partagé -> cross ~ within ; code privé -> cross ~ chance.
        cross_shifts = sorted({max(1, (j * n_agents) // 4) for j in range(1, 4)})
        cross = float(np.mean([_acc_over(train, sh) for sh in cross_shifts]))

        # --- similarité topographique (métrique CANONIQUE de compositionnalité, indépendante du split
        #     zéro-shot) : corrélation de rang entre distance de SENS (Hamming attributs) et distance de
        #     MESSAGE (Hamming symboles greedy), par agent, médiane sur agents. rho>0 => code systématique.
        msgs = []                                                  # (n_combos, n_agents, 2) symboles greedy
        for (a0v, a1v) in combos:
            s0, s1, _, _ = _message(np.full(n_agents, a0v), np.full(n_agents, a1v), greedy=True)
            msgs.append(np.stack([s0, s1], axis=1))
        msgs = np.stack(msgs, axis=0)                              # (C, n_agents, 2)
        meanings = np.array(combos)                                # (C, 2)
        C = len(combos)
        iu, ju = np.triu_indices(C, k=1)
        mean_d = (meanings[iu, 0] != meanings[ju, 0]).astype(float) + (meanings[iu, 1] != meanings[ju, 1])

        def _spearman(x, y):
            if x.std() < 1e-9 or y.std() < 1e-9:
                return 0.0
            rx = np.argsort(np.argsort(x)).astype(float)
            ry = np.argsort(np.argsort(y)).astype(float)
            return float(np.corrcoef(rx, ry)[0, 1])

        rhos = []
        for ag in range(n_agents):
            m = msgs[:, ag, :]                                     # (C,2)
            msg_d = (m[iu, 0] != m[ju, 0]).astype(float) + (m[iu, 1] != m[ju, 1])
            rhos.append(_spearman(mean_d, msg_d))
        import statistics as _st
        topsim = float(_st.median(rhos))

        chance = 1.0 / A
        cross_mi = max(-1.0, min(2.0, (cross - chance) / (within - chance))) if within > chance + 0.05 else float("nan")
        return {"seed": int(seed), "A": A, "V": V, "rotate": bool(rotate), "chance": chance,
                "within": within, "zeroshot": zeroshot, "gen_gap": zeroshot - chance, "topsim": topsim,
                "cross": cross, "cross_mi": cross_mi}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET) = saved


def main():
    import statistics
    episodes = int(os.environ.get("CLP_EPISODES", "5000"))
    seeds = list(range(int(os.environ.get("CLP_SEEDS", "2"))))
    A = int(os.environ.get("CLP_A", "3"))
    V = int(os.environ.get("CLP_V", "6"))
    M = int(os.environ.get("CLP_AGENTS", "16"))

    def _cell(rotate):
        rows = [run_compositional(episodes=episodes, n_agents=M, A=A, V=V, seed=s, rotate=rotate)
                for s in seeds]
        return (statistics.median(r["within"] for r in rows),
                statistics.median(r["zeroshot"] for r in rows),
                statistics.median(r["topsim"] for r in rows))

    chance = 1.0 / A
    fw, fz, ft = _cell(False)
    rw, rz, rt = _cell(True)
    print(f"A={A} V={V} chance={chance:.2f} episodes={episodes} seeds={len(seeds)} agents={M}")
    print(f"FIXED     within={fw:.3f} zeroshot={fz:.3f} gen_gap={fz - chance:+.3f} topsim={ft:+.3f}")
    print(f"ROTATION  within={rw:.3f} zeroshot={rz:.3f} gen_gap={rz - chance:+.3f} topsim={rt:+.3f}")
    # compositionnel = généralise zéro-shot bien au-dessus de la chance (corroboré par topsim>0)
    fixed_comp = fz > chance + 0.12 and ft > 0.15
    rot_learned = rw > chance + 0.08
    verdict = ("COMPOSITIONAL_PROTOCOL_EMERGES" if fixed_comp else
               "COMPOSITIONAL_ONLY_MARGINAL" if fz > chance + 0.06 else
               "HOLISTIC_NO_GENERALIZATION")
    print(f"VERDICT={verdict} : FIXED généralise={fz > chance + 0.12} (zeroshot {fz:.2f} vs chance {chance:.2f}, "
          f"topsim {ft:+.2f}) ; ROTATION {'convergé' if rot_learned else 'NON-convergé (goulot consensus LANG-002)'}")


if __name__ == "__main__":
    main()
