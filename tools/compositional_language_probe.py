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
import math
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
                      seed: int = 0, lr: float = 0.05, rotate: bool = True, warmstart_fixed: int = 0,
                      credit: str = "joint", num_nodes: int = 172,
                      warmstart_easy: int = 0, easy_values: int = 0):
    """Entraîne sender+receiver sur le jeu compositionnel (référents (a0,a1), messages 2-symboles), en
    tenant la DIAGONALE (a,a) hors entraînement. Renvoie within (combos vus), zeroshot (combos held-out),
    topsim, et cross_mi (intelligibilité mutuelle croisée), + chance=1/A. rotate=True apparie
    sender_i<->receiver_{i+s} (décalage aléatoire/épisode). warmstart_fixed>0 (LANG-004) : ce nombre
    d'épisodes INITIAUX est joué en PAIRES FIGÉES (s=0) avant la phase `rotate` -> curriculum dyade->rotation
    (warm-start d'un code compositionnel avant de le partager)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06, famille run_* -- 7e elargissement du cliquet). Un
    # argument degenere est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte
    # vide / un horizon nul rend 0.0 ou nan comme une MESURE que l'aval lit comme un resultat
    # (biais negatif systematique du depot). Posee AVANT toute construction -> refus < 0.5 s.
    if int(episodes) + int(warmstart_fixed) + int(warmstart_easy) <= 0 or int(n_agents) < 2 or int(A) < 2 or int(V) < 1:
        raise ValueError(
            f"run_compositional : argument degenere (episodes={episodes}, warmstart_fixed={warmstart_fixed}, warmstart_easy={warmstart_easy}, n_agents={n_agents}, A={A}, V={V}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    import numpy as np
    import torch
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend import make_population
    from src.agents.backend_torch import TorchPopulationModel

    np.random.seed(seed)
    torch.manual_seed(seed)

    saved = (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
             TorchPopulationModel.BILINEAR)
    TorchPopulationModel.CONDITION_GATE = False
    TorchPopulationModel.GATE_TARGET = None
    # P2.27 : substrat EPINGLE -- attribut de CLASSE, sinon herite de l ambiant du
    # processus. Pose AVANT make_population : U/V/W_bl ne sont crees qu a la construction.
    TorchPopulationModel.BILINEAR = False
    try:
        # num_nodes = capacité du substrat (LTC) ; défaut 172 (prod). LANG-005 : sweep pour tester le plafond.
        sender = make_population([MambaAgent(num_nodes=num_nodes) for _ in range(n_agents)], backend="torch")
        receiver = make_population([MambaAgent(num_nodes=num_nodes) for _ in range(n_agents)], backend="torch")
        sender.opt = torch.optim.Adam(
            [sender.W] + [p for p in (sender.U, sender.V, sender.W_bl) if p is not None], lr=lr)
        receiver.opt = torch.optim.Adam(
            [receiver.W] + [p for p in (receiver.U, receiver.V, receiver.W_bl) if p is not None], lr=lr)
        I = sender.I
        rng = np.random.RandomState(seed + 1)

        combos = [(i, j) for i in range(A) for j in range(A)]
        heldout = [(k, k) for k in range(A)]                       # diagonale = combos jamais entraînés
        train = [c for c in combos if c not in heldout]            # chaque VALEUR d'attribut reste vue
        train_arr = np.array(train)
        # CURR-001 : sous-monde FACILE = combos restreints aux `easy_values` premières valeurs (dims fixes,
        # seule la plage de valeurs échantillonnée change) -> curriculum de difficulté easy->full.
        train_easy = [c for c in train if c[0] < easy_values and c[1] < easy_values] if easy_values else []
        train_easy_arr = np.array(train_easy) if train_easy else train_arr

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

        # independent=True (crédit par-attribut, LANG-005) : réinitialise H entre les 2 pas -> chaque symbole
        # est une fonction pure de (référent, position), crédité 1-pas séparément (cohérent avec le replay).
        def _message(a0, a1, greedy=False, independent=False):
            sender.H = torch.zeros((n_agents, sender.N))
            o0 = _sender_obs(a0, a1, 0)
            p0, _ = sender.forward(o0)                              # H porté au pas suivant (sauf independent)
            if independent:
                sender.H = torch.zeros((n_agents, sender.N))
            o1 = _sender_obs(a0, a1, 1)
            p1, _ = sender.forward(o1)
            if greedy:
                s0 = np.asarray(p0)[:, :V].argmax(axis=1)
                s1 = np.asarray(p1)[:, :V].argmax(axis=1)
            else:
                s0 = _sample(p0, V)
                s1 = _sample(p1, V)
            return s0, s1, o0, o1

        def _decode(s0, s1, greedy=False, independent=False):
            receiver.H = torch.zeros((n_agents, receiver.N))
            r0 = _recv_obs(s0, s1, 0)
            q0, _ = receiver.forward(r0)
            if independent:
                receiver.H = torch.zeros((n_agents, receiver.N))
            r1 = _recv_obs(s0, s1, 1)
            q1, _ = receiver.forward(r1)
            if greedy:
                g0 = np.asarray(q0)[:, :A].argmax(axis=1)
                g1 = np.asarray(q1)[:, :A].argmax(axis=1)
            else:
                g0 = _sample(q0, A)
                g1 = _sample(q1, A)
            return g0, g1, r0, r1

        independent = (credit == "per_attr")

        def _acts(vals):
            return [{"move": int(x)} for x in vals]

        for ep in range(warmstart_fixed + warmstart_easy + episodes):
            # curriculum LANG-004 (social) : phase 1 = paires FIGÉES puis `rotate`.
            phase_rotate = rotate and ep >= warmstart_fixed
            # curriculum CURR-001 (difficulté) : phase 1 = sous-monde FACILE (valeurs restreintes) puis full.
            easy_phase = easy_values > 0 and ep < warmstart_easy
            src = train_easy_arr if easy_phase else train_arr
            idx = rng.randint(0, len(src), size=n_agents)
            a0, a1 = src[idx, 0], src[idx, 1]
            s0, s1, o0, o1 = _message(a0, a1, independent=independent)
            s = rng.randint(1, n_agents) if phase_rotate else 0    # appariement sender_i<->receiver_{i+s}
            rs0, rs1 = np.roll(s0, s), np.roll(s1, s)              # receiver_j lit le message de sender_{j-s}
            ra0, ra1 = np.roll(a0, s), np.roll(a1, s)             # ... et vise SES attributs
            g0, g1, r0, r1 = _decode(rs0, rs1, independent=independent)
            c0 = (g0 == ra0).astype(np.float32)                    # correction attribut 0 (receiver j)
            c1 = (g1 == ra1).astype(np.float32)                    # correction attribut 1
            if credit == "per_attr":
                # LANG-005 : chaque symbole/guess crédité par SON attribut seul (signal net, faible variance) ;
                # épisodes 1-pas séparés par position. Sender : reward de l'attribut ré-alignée par roll(-s).
                sc0, sc1 = np.roll(c0, -s), np.roll(c1, -s)
                receiver.learn_episode([r0], [_acts(g0)], c0 - c0.mean(), gate_last_only=False)
                receiver.learn_episode([r1], [_acts(g1)], c1 - c1.mean(), gate_last_only=False)
                sender.learn_episode([o0], [_acts(s0)], sc0 - sc0.mean(), gate_last_only=False)
                sender.learn_episode([o1], [_acts(s1)], sc1 - sc1.mean(), gate_last_only=False)
            else:
                # joint (défaut, LANG-003/004) : retour épisodique = fraction d'attributs corrects.
                rew = 0.5 * c0 + 0.5 * c1
                snd_rew = np.roll(rew, -s)                         # sender_i récolte la reward de receiver_{i+s}
                receiver.learn_episode([r0, r1], [_acts(g0), _acts(g1)],
                                       rew - rew.mean(), gate_last_only=False)
                sender.learn_episode([o0, o1], [_acts(s0), _acts(s1)],
                                     snd_rew - snd_rew.mean(), gate_last_only=False)

        # --- éval greedy : within/zeroshot en paire d'origine (shift=0) ; cross-MI en partenaire décalé ---
        # ⚠️ `scramble=True` (P2.15, 2026-09-08) : le message est REMPLACÉ par des symboles ALÉATOIRES,
        # décorrélés du sens. Tout le reste est identique — mêmes agents ENTRAÎNÉS, même décodeur, même
        # jeu de combinaisons. C'est donc « ce qu'atteint un récepteur dont le canal ne transporte
        # RIEN », c.-à-d. le PLAFOND DE L'INCAPABLE, mesuré DANS le dispositif et au régime configuré.
        # Sans lui, la généralisation zéro-shot se jugeait contre `chance + 0.12`, un seuil posé à
        # l'estime dont personne n'avait montré ce qu'il séparait. Coût : ÉVAL SEULE, zéro épisode
        # d'entraînement supplémentaire. Même dispositif que le bras BROUILLÉ de LANG-001.
        rng_scr = np.random.RandomState(seed + 4242)

        def _acc_over(comboset, shift=0, scramble=False):
            accs = []
            for (a0v, a1v) in comboset:
                a0 = np.full(n_agents, a0v)
                a1 = np.full(n_agents, a1v)
                s0, s1, _, _ = _message(a0, a1, greedy=True, independent=independent)
                rs0, rs1 = np.roll(s0, shift), np.roll(s1, shift)  # receiver_j décode le msg de sender_{j-shift}
                if scramble:
                    rs0 = rng_scr.randint(0, V, size=n_agents)
                    rs1 = rng_scr.randint(0, V, size=n_agents)
                ra0, ra1 = np.roll(a0, shift), np.roll(a1, shift)
                g0, g1, _, _ = _decode(rs0, rs1, greedy=True, independent=independent)
                accs.append(0.5 * (g0 == ra0) + 0.5 * (g1 == ra1))
            return float(np.mean(np.concatenate(accs)))

        within = _acc_over(train, 0)
        zeroshot = _acc_over(heldout, 0)
        # PLAFONDS de l'incapable, ÉVAL SEULE : le même récepteur entraîné, mais canal vide. Un par
        # grandeur jugée — `within` et `zeroshot` n'ont pas le même incapable (l'un porte sur des
        # combinaisons VUES, l'autre sur des combinaisons TENUES À L'ÉCART).
        zeroshot_scrambled = _acc_over(heldout, 0, scramble=True)
        within_scrambled = _acc_over(train, 0, scramble=True)
        # intelligibilité mutuelle croisée (LANG-002 porté au 2-attributs) : un partenaire jamais co-apparié
        # décode-t-il le message ? code partagé -> cross ~ within ; code privé -> cross ~ chance.
        cross_shifts = sorted({max(1, (j * n_agents) // 4) for j in range(1, 4)})
        cross = float(np.mean([_acc_over(train, sh) for sh in cross_shifts]))

        # --- similarité topographique (métrique CANONIQUE de compositionnalité, indépendante du split
        #     zéro-shot) : corrélation de rang entre distance de SENS (Hamming attributs) et distance de
        #     MESSAGE (Hamming symboles greedy), par agent, médiane sur agents. rho>0 => code systématique.
        msgs = []                                                  # (n_combos, n_agents, 2) symboles greedy
        for (a0v, a1v) in combos:
            s0, s1, _, _ = _message(np.full(n_agents, a0v), np.full(n_agents, a1v),
                                    greedy=True, independent=independent)
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
        # ⚠️ P2.15 : le denominateur du MI n'est defini que si le regime a APPRIS — jugé désormais contre
        # le PLAFOND MESURÉ d'un récepteur à canal vide, plus que contre `chance + 0.05` posé à l'estime.
        # Ce `nan` est une NON-MESURE assumée, jamais un zéro : le confondre fabriquerait un négatif.
        _appris = within > within_scrambled + math.sqrt(
            max(within_scrambled * (1.0 - within_scrambled), 0.0) / max(n_agents, 1))
        cross_mi = max(-1.0, min(2.0, (cross - chance) / (within - chance))) if _appris else float("nan")
        return {"seed": int(seed), "A": A, "V": V, "rotate": bool(rotate), "chance": chance,
                "within": within, "zeroshot": zeroshot, "gen_gap": zeroshot - chance, "topsim": topsim,
                "zeroshot_scrambled": zeroshot_scrambled, "within_scrambled": within_scrambled,
                "learned": bool(_appris), "cross": cross, "cross_mi": cross_mi}
    finally:
        (TorchPopulationModel.CONDITION_GATE, TorchPopulationModel.GATE_TARGET,
         TorchPopulationModel.BILINEAR) = saved


def main():
    import math
    import statistics

    from tools.experiment_preflight import assert_bar_separates_the_incapable
    episodes = int(os.environ.get("CLP_EPISODES", "5000"))
    seeds = list(range(int(os.environ.get("CLP_SEEDS", "2"))))
    A = int(os.environ.get("CLP_A", "3"))
    V = int(os.environ.get("CLP_V", "6"))
    M = int(os.environ.get("CLP_AGENTS", "16"))

    def _cell(rotate):
        rows = [run_compositional(episodes=episodes, n_agents=M, A=A, V=V, seed=s, rotate=rotate)
                for s in seeds]
        # le PLAFOND de l'incapable est un MAX sur les seeds, pas une mediane (cf. `_acc_over(scramble)`)
        return (statistics.median(r["within"] for r in rows),
                statistics.median(r["zeroshot"] for r in rows),
                statistics.median(r["topsim"] for r in rows),
                max(r["zeroshot_scrambled"] for r in rows),
                max(r["within_scrambled"] for r in rows))

    chance = 1.0 / A
    fw, fz, ft, f_scr, f_within_scr = _cell(False)
    rw, rz, rt, r_scr, r_within_scr = _cell(True)
    print(f"A={A} V={V} chance={chance:.2f} episodes={episodes} seeds={len(seeds)} agents={M}")
    print(f"FIXED     within={fw:.3f} zeroshot={fz:.3f} gen_gap={fz - chance:+.3f} topsim={ft:+.3f}")
    print(f"ROTATION  within={rw:.3f} zeroshot={rz:.3f} gen_gap={rz - chance:+.3f} topsim={rt:+.3f}")
    # ⚠️ P2.15 (2026-09-08) — la généralisation zéro-shot se jugeait contre `chance + 0.12`, un seuil
    # posé à l'estime. Le PLAFOND DE L'INCAPABLE est désormais MESURÉ dans le run : mêmes agents
    # ENTRAÎNÉS, même décodeur, même jeu tenu à l'écart, mais MESSAGE BROUILLÉ — donc « ce qu'atteint un
    # récepteur dont le canal ne transporte rien ». Coût : ÉVAL SEULE. Même dispositif que LANG-001.
    # Mesure de contrôle (budget réduit, A=4) : brouillé 0.281 contre un hasard de 0.250 — le plafond de
    # l'incapable est bien AU-DESSUS du hasard, ce qu'un seuil ancré sur `chance` ne pouvait pas voir.
    # ⚠️ `n_eval` = nombre d'AGENTS, pas combos x agents. C'est DELIBERE et conservateur : l'erreur-type
    # en est SUR-estimee, donc la barre est plus HAUTE, donc plus dure a franchir. L'unite de replication
    # du depot est le seed, pas l'agent (les agents d'un seed partagent entrainement et tirages) ;
    # compter combos x agents comme independants serait le choix OPTIMISTE, celui qui abaisse la barre.
    _se = math.sqrt(max(f_scr * (1.0 - f_scr), 0.0) / max(M, 1))
    bar_gen = f_scr + _se
    assert_bar_separates_the_incapable(
        bar_gen, f_scr,
        "zero-shot a MESSAGE BROUILLE : memes agents entraines, meme decodeur, meme jeu tenu a l'ecart, "
        "message remplace par des symboles aleatoires -- plafond d'un recepteur dont le canal ne "
        "transporte rien, MAX sur les seeds du MEME run",
        label="barre de generalisation zero-shot")
    fixed_comp = fz > bar_gen and ft > 0.15
    # ⚠️ P2.15 : « ROTATION a convergé » se jugeait contre `chance + 0.08`. Même correctif : le plafond
    # d'un récepteur à canal vide sur les combinaisons VUES, mesuré dans le run.
    _bar_rot = r_within_scr + math.sqrt(max(r_within_scr * (1.0 - r_within_scr), 0.0) / max(M, 1))
    assert_bar_separates_the_incapable(
        _bar_rot, r_within_scr,
        "within a MESSAGE BROUILLE sous ROTATION : plafond d'un recepteur dont le canal ne transporte "
        "rien sur les combinaisons VUES, MAX sur les seeds du MEME run",
        label="barre de convergence de la rotation")
    rot_learned = rw > _bar_rot
    verdict = ("COMPOSITIONAL_PROTOCOL_EMERGES" if fixed_comp else
               "COMPOSITIONAL_ONLY_MARGINAL" if fz > f_scr else
               "HOLISTIC_NO_GENERALIZATION")
    print(f"VERDICT={verdict} : FIXED généralise={fixed_comp} (zeroshot {fz:.2f} vs barre MESUREE "
          f"{bar_gen:.3f} = brouillé {f_scr:.3f} + 1 erreur-type ; chance {chance:.2f}), "
          f"topsim {ft:+.2f}) ; ROTATION {'convergé' if rot_learned else 'NON-convergé (goulot consensus LANG-002)'}")


if __name__ == "__main__":
    main()
