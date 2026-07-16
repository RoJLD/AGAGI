"""tools/nav_localization_probe.py — Probe de LOCALISATION du mur de navigation Lewis (P3 NAV).

Le mur de navigation est CLOS cote MONDE (EDR 090-114b : energie/cinematique/selection/capacite/
demande/affordance tous elimines) : la politique apprise atteint ~0.52 (figees) vs oracle 0.875 ->
le verrou est la POLITIQUE/SUBSTRAT. Ce banc LOCALISE le gap 0.52->0.875 DANS le substrat.

Question : la direction-cible (pas glouton vers la proie la plus proche = l'oracle d'EDR 114) est-elle
PRESERVEE jusqu'a l'etat cache H (readout defaillant) ou DETRUITE par la dynamique recurrente
(encodeur defaillant) ?

Methodo maison = PROBE LINEAIRE (decoder une cible d'un etat cache, cf. EDR 120 memoire AUC~0.90 /
EDR 150 ToM). Par (agent, tick) de forage on capture :
  - H       : etat cache post-forward (a["model"].H_prev, l.727 mamba_agent : le batch le reecrit)
  - obs     : observation (contient dn/ds/de/dw = direction-proie)
  - correct : action gloutonne-correcte = env._reach_oracle_action(agent) AVANT le step (positions
              pre-mouvement = base de l'obs que l'agent a vue) -> reutilise l'oracle 114, zero logique neuve
  - emise   : action reellement choisie par la politique apprise (a["last_action"], post-step)

Decodeurs (probe lineaire ridge, argmax sur 4 classes N/S/E/O) :
  - obs -> correct : SANITY (la direction est dans l'obs -> doit etre ~parfait)
  - H   -> correct : test ENCODEUR (H preserve-t-il la direction ?)
  - emise vs correct : test COMPORTEMENTAL (l'agent fait-il le bon pas ? attendu bas, cf. mur p_reach)
  - H   -> emise   : sanity que H pilote le readout (les logits sont un readout lineaire de H)

Verdict :
  - H->correct HAUT + emise!=correct  => READOUT_GAP  (info dans H, readout la jette -> cible torch = tete d'action)
  - H->correct BAS                    => ENCODER_GAP  (dynamique detruit le signal -> cible torch = encodeur)
  - sinon                             => MIXED / INVALID_TARGET (si l'obs elle-meme ne decode pas)

Tooling-only (git diff src/ VIDE ; coordination session //). Cohorte fixe (benchmark_mode) : de-confond
p_reach (dette 114b) ET garantit un H de dimension constante (prerequis du probe lineaire). Conditions
MAXIMALES de navigation (n_apex=0, metab=0), comme EDR 107/114.
"""
import os
import numpy as np

from src.seed_ai.harness import Harness, seed_at
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.robust_eval import _load_champions
from tools.lewis_critical import _setup_critical
from tools.lethality_curriculum import _disable_kuzu
from tools.lewis_survival_sweep import _cfg, NUM_AGENTS, PREY_COUNT

MOVE_CLASSES = (0, 1, 2, 3)   # N/S/E/O : les seules decisions de NAVIGATION (6=no-op filtre)


# ----------------------------------------------------------------------------- probe lineaire (pur)
def linear_probe_accuracy(X, y, seed=0, test_frac=0.3, ridge=1.0):
    """Accuracy d'un DECODEUR LINEAIRE ridge X->y (multiclasse, argmax sur one-hot). Features z-scorees
    sur le train (stats train uniquement -> pas de fuite). Split train/test deterministe au seed.
    Renvoie (accuracy_test, chance) ou chance = frequence de la classe majoritaire du test."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=int)
    n = len(y)
    if n < 10:
        return float("nan"), float("nan")
    classes = np.unique(y)
    k = len(classes)
    cls_idx = {c: i for i, c in enumerate(classes)}
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    n_te = max(1, int(round(n * test_frac)))
    te, tr = perm[:n_te], perm[n_te:]
    Xtr, Xte = X[tr], X[te]
    ytr, yte = y[tr], y[te]
    # z-score sur le train
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0) + 1e-8
    Xtr = (Xtr - mu) / sd
    Xte = (Xte - mu) / sd
    # biais
    Xtr = np.hstack([Xtr, np.ones((len(Xtr), 1))])
    Xte = np.hstack([Xte, np.ones((len(Xte), 1))])
    Ytr = np.zeros((len(ytr), k), dtype=np.float64)
    for i, yy in enumerate(ytr):
        Ytr[i, cls_idx[yy]] = 1.0
    d = Xtr.shape[1]
    reg = ridge * np.eye(d)
    reg[-1, -1] = 0.0                      # ne pas regulariser le biais
    W = np.linalg.solve(Xtr.T @ Xtr + reg, Xtr.T @ Ytr)     # (d, k)
    pred = np.argmax(Xte @ W, axis=1)
    pred_cls = classes[pred]
    acc = float(np.mean(pred_cls == yte))
    _, counts = np.unique(yte, return_counts=True)
    chance = float(counts.max() / len(yte))
    return acc, chance


def nav_verdict(acc_obs, acc_H, match_emit, chance, obs_margin=0.10, preserve_frac=0.5,
                behav_hi=0.5):
    """Verdict de localisation du gap de navigation.

    - acc_obs : sanity (direction decodable de l'obs). Si acc_obs - chance < obs_margin -> INVALID_TARGET.
    - preserve = (acc_H - chance) >= preserve_frac * (acc_obs - chance) : H recupere au moins la moitie
      du signal au-dessus du hasard que porte l'obs (plafond).
    - behav_fails = match_emit < behav_hi : l'agent ne fait pas le bon pas (attendu, mur p_reach).

    READOUT_GAP  : preserve ET behav_fails  (H a l'info, readout la jette)
    ENCODER_GAP  : NON preserve             (la dynamique detruit le signal)
    MIXED        : preserve mais l'agent reussit deja (behav ok) -> pas de gap a localiser ici
    """
    if acc_obs - chance < obs_margin:
        return "INVALID_TARGET"
    preserve = (acc_H - chance) >= preserve_frac * (acc_obs - chance)
    behav_fails = match_emit < behav_hi
    if not preserve:
        return "ENCODER_GAP"
    if behav_fails:
        return "READOUT_GAP"
    return "MIXED"


# ----------------------------------------------------------------------------- capture (impur)
def capture(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150):
    """Fait tourner le forage (cohorte fixe = clones du champion, dimension H constante) et capture par
    (agent,tick) : H, obs, action correcte (oracle, pre-step), action emise (post-step). Aligne par
    identite d'agent (benchmark_mode -> pas de naissance -> survivants = sous-ensemble du pre-step)."""
    champ = _load_champions()[0]                     # UN champion, clone tel quel -> N constant
    Hs, OBSs, CORR, EMIT = [], [], [], []
    for s in seeds:
        seed_at(s, 0)
        env = Biosphere3D(cfg)
        env.benchmark_mode = True                    # de-confond (114b) + H dim constante
        _setup_critical(env, 0.0, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        env.use_ref_head = False
        env.decode_act = False
        env.explore_eps = 0.0                        # action emise = pur choix politique (pas d'ε-greedy)
        for _ in range(num_agents):
            a = MambaAgent()
            a.from_genome(champ)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            pre = list(env.agents)
            obs_pre = env.get_batch_observations()                    # (N, I), ordre env.agents
            corr_by_id = {id(a): env._reach_oracle_action(a) for a in pre}
            obs_by_id = {id(a): obs_pre[i] for i, a in enumerate(pre)}
            env.step()
            for a in env.agents:
                c = corr_by_id.get(id(a))
                if c not in MOVE_CLASSES:                             # garder les decisions de NAV only
                    continue
                model = a.get("model")
                if model is None or getattr(model, "H_prev", None) is None:
                    continue
                Hs.append(np.asarray(model.H_prev[0], dtype=np.float32).copy())
                OBSs.append(np.asarray(obs_by_id[id(a)], dtype=np.float32).copy())
                CORR.append(int(c))
                EMIT.append(int(a.get("last_action", -1)))
            t += 1
    # H peut varier de longueur si (bug) la topologie derive -> tronquer a la longueur modale
    if Hs:
        lens = [len(h) for h in Hs]
        modal = max(set(lens), key=lens.count)
        keep = [i for i, l in enumerate(lens) if l == modal]
        Hs = [Hs[i] for i in keep]
        OBSs = [OBSs[i] for i in keep]
        CORR = [CORR[i] for i in keep]
        EMIT = [EMIT[i] for i in keep]
    return {"H": np.array(Hs), "obs": np.array(OBSs),
            "correct": np.array(CORR, dtype=int), "emit": np.array(EMIT, dtype=int)}


# ----------------------------------------------------------------------------- analyse + rapport
def analyze(cap, seed=0):
    """Calcule les 4 mesures + le verdict a partir d'une capture."""
    H, obs, correct, emit = cap["H"], cap["obs"], cap["correct"], cap["emit"]
    n = len(correct)
    acc_obs, ch_obs = linear_probe_accuracy(obs, correct, seed=seed)
    acc_H, ch_H = linear_probe_accuracy(H, correct, seed=seed)
    acc_H_emit, _ = linear_probe_accuracy(H, emit, seed=seed)
    match_emit = float(np.mean(emit == correct)) if n else float("nan")
    # Ventilation comportementale : l'action emise est-elle seulement un MOVE ? (sinon soin/lance/grab...)
    is_move = np.isin(emit, MOVE_CLASSES)
    p_emit_move = float(np.mean(is_move)) if n else float("nan")
    match_when_move = float(np.mean(emit[is_move] == correct[is_move])) if is_move.any() else float("nan")
    chance = ch_H if not np.isnan(ch_H) else 0.25
    verdict = nav_verdict(acc_obs, acc_H, match_emit, chance)
    return {"n": int(n), "acc_obs": acc_obs, "acc_H": acc_H, "acc_H_emit": acc_H_emit,
            "match_emit": match_emit, "p_emit_move": p_emit_move, "match_when_move": match_when_move,
            "chance": chance, "verdict": verdict}


def _report(h, res, speed, _return):
    print("\n=== NAV localisation : ou vit le gap 0.52->0.875 (Lewis) ? ===")
    print(f"  proies={'figees' if speed == 0.0 else 'mobiles'}  n(decisions NAV)={res['n']}  chance={res['chance']:.3f}")
    print(f"  obs   -> correct : acc={res['acc_obs']:.3f}   (SANITY : direction dans l'obs)")
    print(f"  H     -> correct : acc={res['acc_H']:.3f}   (ENCODEUR : H preserve-t-il la direction ?)")
    print(f"  H     -> emise   : acc={res['acc_H_emit']:.3f}   (sanity : H pilote le readout)")
    print(f"  emise == correct : {res['match_emit']:.3f}   (COMPORTEMENT : l'agent fait-il le bon pas ?)")
    print(f"    dont emise=move  : {res['p_emit_move']:.3f}  | correct SI move : {res['match_when_move']:.3f}")
    print("=== VERDICT ===")
    print(f"  -> {res['verdict']}")
    if _return:
        return res
    return res


def main(speed=0.0, seed=1140, n_eval=6, max_ticks=150, _return=False):
    """Probe de localisation. speed=0.0 (proies figees, comparable 114b figees) recommande."""
    with Harness(seed=seed, name="nav_localization", with_db=False) as h:
        _disable_kuzu()
        base = h.seed
        seeds = [base + i for i in range(n_eval)]
        cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True,
                   prey_speed_scale=speed)
        cap = capture(cfg, seeds, n_apex=0, max_ticks=max_ticks)
        res = analyze(cap, seed=base)
        h.save({"speed": speed, "seed": base, "n_eval": n_eval, "max_ticks": max_ticks, **res})
        return _report(h, res, speed, _return)


if __name__ == "__main__":
    main(speed=float(os.getenv("NAV_SPEED", "0.0")),
         seed=int(os.getenv("EXPERIMENT_SEED", "1140")),
         n_eval=int(os.getenv("NAV_NEVAL", "6")),
         max_ticks=int(os.getenv("NAV_TICKS", "150")))
