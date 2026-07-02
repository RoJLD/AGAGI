"""tools/energy_readout_probe.py — Le mur d'ENERGIE est-il le MEME READOUT_GAP que la navigation ? (P3 suite)

EDR-NAV-001 : le mur de navigation = READOUT_GAP (H encode la direction, la tete d'action l'ignore).
EDR 094/099/100 : le mur d'energie (famine ~tick 5-58) = la politique emet des actions cheres/inutiles
au lieu de forager. Hypothese unificatrice : MEME defaut de readout — le substrat represente l'etat
utile (ici la DETRESSE ENERGETIQUE) mais la tete d'action ne le convertit PAS en comportement de survie
(forager davantage, gaspiller moins).

Fait de cadrage (exploration) : hp ~758 (phenotype_hp_bonus) >> 100 -> le soin (action 6) est un NO-OP
garde (l.692 : ne s'execute que si hp<100 & E>50), pourtant EMIS 22-42% du temps -> la politique gaspille
1/4 a 1/2 de ses decisions sur une action sans effet, en mourant de faim. hp invariant (n_apex=0) -> la
variable qui DEVRAIT moduler forager-vs-gaspiller est l'ENERGIE (varie 80 -> negatif).

Test (transpose NAV-001, methodo probe lineaire) : par (agent, tick) de forage en regime energie-limite
(metab reel, n_apex=0) on capture H, obs, energie, action emise. Puis :
  - obs -> energy_low : SANITY (l'energie est dans l'obs).
  - H   -> energy_low : test ENCODEUR (la detresse energetique est-elle dans H ?).
  - p_forage(bas E) vs p_forage(haut E) : la politique forage-t-elle PLUS quand l'energie chute ?
Verdict :
  - H encode energy_low ET le forage NE monte PAS sous stress => ENERGY_READOUT_GAP (represente mais pas agi)
  - H n'encode pas energy_low                                => ENCODER_GAP
  - le forage monte sous stress                              => CONDITIONED (pas de gap ici)

Tooling-only (git diff src/ VIDE ; coordination session //). Cohorte fixe (benchmark_mode) -> H dim
constante. Reutilise le decodeur lineaire d'EDR-NAV-001 (DRY).
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
from tools.nav_localization_probe import linear_probe_accuracy

MOVE_CLASSES = (0, 1, 2, 3)   # forager = se deplacer (atteindre la nourriture, cf. EDR 105)
HEAL_ACTION = 6               # no-op garde ici (hp~758 >> 100) mais emis compulsivement


def energy_verdict(acc_obs, acc_H, chance, obs_margin=0.10, preserve_frac=1.0):
    """Verdict ENCODEUR sur l'energie : la detresse energetique est-elle representee dans H ?

    NB (honnetete methodo) : contrairement a la navigation (direction-cible EXOGENE, donnee par l'oracle
    de position), l'energie est ENDOGENE au forage (peu d'energie = a mal forage -> causalite inverse) ->
    le test COMPORTEMENTAL (la politique forage-t-elle plus sous stress ?) est CONFONDU et son signe
    flippe selon regime/fenetre. Ce banc ne conclut donc PAS un readout-gap comportemental ; il etablit
    la moitie ENCODEUR (robuste) : le substrat represente-t-il la detresse energetique aussi bien que
    l'obs ? -> ENCODER_RICH (thse « encodeur OK » de NAV-001 etendue a l'energie) vs ENCODER_GAP.

    - acc_obs : sanity (energy_low decodable de l'obs). Sinon INVALID_TARGET.
    - preserve = (acc_H - chance) >= preserve_frac*(acc_obs - chance) : H represente l'energie AU MOINS
      aussi bien que l'obs (preserve_frac=1.0 : exigeant, car H integre dans le temps -> devrait depasser).
    """
    if acc_obs - chance < obs_margin:
        return "INVALID_TARGET"
    preserve = (acc_H - chance) >= preserve_frac * (acc_obs - chance)
    return "ENCODER_RICH" if preserve else "ENCODER_GAP"


def capture(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=200):
    """Forage en cohorte fixe (clones du champion). Capture par (agent,tick) : H, obs, energie (AVANT
    le step = etat sur lequel la decision est prise), action emise (post-step). H dim constante."""
    champ = _load_champions()[0]
    Hs, OBSs, ENE, EMIT = [], [], [], []
    for s in seeds:
        seed_at(s, 0)
        env = Biosphere3D(cfg)
        env.benchmark_mode = True
        _setup_critical(env, 0.0, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        env.use_ref_head = False
        env.decode_act = False
        env.explore_eps = 0.0
        for _ in range(num_agents):
            a = MambaAgent()
            a.from_genome(champ)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            pre = list(env.agents)
            obs_pre = env.get_batch_observations()
            ene_by_id = {id(a): float(a["energy"]) for a in pre}
            obs_by_id = {id(a): obs_pre[i] for i, a in enumerate(pre)}
            env.step()
            for a in env.agents:
                if id(a) not in ene_by_id:
                    continue
                model = a.get("model")
                if model is None or getattr(model, "H_prev", None) is None:
                    continue
                Hs.append(np.asarray(model.H_prev[0], dtype=np.float32).copy())
                OBSs.append(np.asarray(obs_by_id[id(a)], dtype=np.float32).copy())
                ENE.append(ene_by_id[id(a)])
                EMIT.append(int(a.get("last_action", -1)))
            t += 1
    if Hs:
        lens = [len(h) for h in Hs]
        modal = max(set(lens), key=lens.count)
        keep = [i for i, l in enumerate(lens) if l == modal]
        Hs, OBSs, ENE, EMIT = ([x[i] for i in keep] for x in (Hs, OBSs, ENE, EMIT))
    return {"H": np.array(Hs), "obs": np.array(OBSs),
            "energy": np.array(ENE, dtype=np.float32), "emit": np.array(EMIT, dtype=int)}


def analyze(cap, seed=0):
    """energy_low = energie sous la mediane. Decode de obs/H. Conditionnement du forage par tercile d'E."""
    H, obs, ene, emit = cap["H"], cap["obs"], cap["energy"], cap["emit"]
    n = len(ene)
    if n < 20:
        return {"n": int(n), "verdict": "INVALID_TARGET"}
    med = float(np.median(ene))
    y_low = (ene < med).astype(int)                     # 1 = detresse energetique
    acc_obs, ch_obs = linear_probe_accuracy(obs, y_low, seed=seed)
    acc_H, ch_H = linear_probe_accuracy(H, y_low, seed=seed)
    chance = ch_H if not np.isnan(ch_H) else 0.5
    is_move = np.isin(emit, MOVE_CLASSES)
    is_heal = (emit == HEAL_ACTION)
    lo = ene <= np.percentile(ene, 33)                  # tercile bas / haut
    hi = ene >= np.percentile(ene, 67)
    p_forage_lo = float(np.mean(is_move[lo])) if lo.any() else float("nan")
    p_forage_hi = float(np.mean(is_move[hi])) if hi.any() else float("nan")
    d_forage = p_forage_lo - p_forage_hi   # DESCRIPTIF/CONFONDU (energie endogene) -> pas dans le verdict
    verdict = energy_verdict(acc_obs, acc_H, chance)
    return {"n": int(n), "acc_obs": acc_obs, "acc_H": acc_H, "chance": chance,
            "p_forage_lowE": p_forage_lo, "p_forage_highE": p_forage_hi, "d_forage": d_forage,
            "p_move": float(np.mean(is_move)), "p_heal_noop": float(np.mean(is_heal)),
            "verdict": verdict}


def _report(h, res, metab, _return):
    print("\n=== ENERGIE : le mur d'energie est-il le meme READOUT_GAP que la navigation ? ===")
    print(f"  metab={metab}  n(agent-ticks)={res['n']}  chance={res.get('chance', float('nan')):.3f}")
    print(f"  obs -> energy_low : acc={res['acc_obs']:.3f}   (SANITY : energie dans l'obs)")
    print(f"  H   -> energy_low : acc={res['acc_H']:.3f}   (ENCODEUR : detresse energetique dans H ?)")
    print(f"  [descriptif CONFONDU - energie endogene, ne conclut PAS] "
          f"d_forage(basse-haute E)={res['d_forage']:+.3f}")
    print(f"  p_move global={res['p_move']:.3f}  |  p_heal(NO-OP hp~758) emis={res['p_heal_noop']:.3f} "
          f"(la politique emet une action SANS effet)")
    print("=== VERDICT ===")
    print(f"  -> {res['verdict']}")
    return res


def main(metab=0.25, seed=1140, n_eval=6, max_ticks=200, _return=False):
    with Harness(seed=seed, name="energy_readout", with_db=False) as h:
        _disable_kuzu()
        base = h.seed
        seeds = [base + i for i in range(n_eval)]
        cfg = _cfg(3, base_metabolism=metab, trace_forage=True, prey_speed_scale=0.0)
        cap = capture(cfg, seeds, n_apex=0, max_ticks=max_ticks)
        res = analyze(cap, seed=base)
        h.save({"metab": metab, "seed": base, "n_eval": n_eval, **res})
        return _report(h, res, metab, _return)


if __name__ == "__main__":
    main(metab=float(os.getenv("EN_METAB", "0.25")),
         seed=int(os.getenv("EXPERIMENT_SEED", "1140")),
         n_eval=int(os.getenv("EN_NEVAL", "6")),
         max_ticks=int(os.getenv("EN_TICKS", "200")))
