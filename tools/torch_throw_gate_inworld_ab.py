"""B2 : câblage du throw-gate in-world (cran 2, biosphere). Banc A/B apparie ON vs SHUFFLE :
mesure binding_gap = P(throw | spear-en-inventaire) - P(throw | pas de spear) sur la VRAIE
presence, dans les deux bras. ON = tete entrainee sur la vraie recompense (kill-avec-outil) ;
SHUFFLE = recompense permutee (temoin d'artefact, joyau 169->171). Les spears sont SEMES
exogenement (decouplage du mur du craft EDR-125/127) : spawn + re-semis probabiliste quand
l'inventaire se vide -> melange dynamique spear/¬spear. Verdict via compute_ab_verdict.

Usage : python tools/torch_throw_gate_inworld_ab.py   (env: TTG_SEEDS, TTG_TICKS, TTG_WARMUP, TTG_AGENTS)
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.worlds.world_1_stoneage import Biosphere3D, WorldConfig
from src.agents.mamba_agent import MambaAgent
from src.environments.stone_economy import has_spear
from tools.substrate_ab import compute_ab_verdict


def _seed_spears(world, weight=2.0):
    """Sème un spear en tete d'inventaire de chaque agent (contexte present, throwable en premier).
    `weight` leger (ex. 0.1) = neutralise le drain de portage (couche 1 survie)."""
    for a in world.agents:
        a["inventory"].insert(0, {"type": "Spear", "weight": weight})


def _reseed_spears(world, rng, respawn_p, weight=2.0):
    """Re-sème un spear aux agents vivants qui n'en ont plus, avec proba respawn_p -> melange
    dynamique spear/¬spear a travers agents et temps (les deux contextes restent echantillonnes)."""
    for a in world.agents:
        if not has_spear(a["inventory"]) and rng.rand() < respawn_p:
            a["inventory"].insert(0, {"type": "Spear", "weight": weight})


def run_arm(shuffle=False, seed=0, ticks=400, warmup=200, n_agents=32, respawn_p=0.5,
            base_metabolism=1.0, forage_payoff=1.0, penalty=-0.5, night=True,
            energy=80.0, spear_weight=2.0, shaping=False, antisat=None,
            warm_w=None, warm_b=None, lr=None, prey_count=None, prey_regen=None,
            no_consume=False, weightless=False, conditional_credit=False):
    """Tourne un monde torch avec le throw-gate, sème/re-sème des spears, agrege le binding_gap
    sur la fenetre post-warmup (couples agent,tick sur la VRAIE presence-spear). CRN par seed.
    ON (shuffle=False) vs SHUFFLE (recompense permutee, contexte decorrele). `penalty` = recompense
    throw-sans-kill : -0.5 = BIAISE (EDR-172) ; 0.0 = NON-BIAISE (correctif EDR-NAV-005). `energy`
    haute + `spear_weight` leger + base_metabolism bas = neutralise la couche 1 (survie) pour isoler
    la question du credit (analogue base_metab=0.0 d'EDR-WLD-001)."""
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:
        pass
    w = Biosphere3D(WorldConfig(base_metabolism=base_metabolism, forage_payoff=forage_payoff))
    if prey_count is not None:                    # densite de proies => monte P(hit) => r.P (dose-reponse)
        w.config.target_prey_count = int(prey_count)
        w.prey_regen_burst = int(prey_regen) if prey_regen is not None else int(prey_count)
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=energy)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()               # repro : couper la memoire KuzuDB ambiante
    w.current_era = 1
    w.benchmark_mode = True                     # cohorte fixe -> dims homogenes (114b)
    w.night_enabled = night                     # night=False : leve le tueur couche-1 (nuit mortelle
                                                # tick 50-99) SANS couper le regen de proies (cf. training_mode)
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    w.torch_throw_penalty = penalty             # NAV-005 : le knob teste
    w.torch_throw_shaping = shaping              # EDR-173-suite : credit DENSE de visee
    w.torch_throw_no_consume = no_consume            # F1 (EDR-177)
    w.torch_throw_weightless = weightless             # F2 (EDR-177)
    w.torch_throw_conditional_credit = conditional_credit  # F4 (EDR-177)
    if antisat is not None:
        w.torch_throw_antisat = antisat          # modere l'anti-sat (defaut 6.0 ecrase p->0 => throw_rate~0)
    if lr is not None:
        w.torch_throw_gate_lr = lr               # lr=0 => gate GELE (mesure le warm-start pur, sans REINFORCE)
    w.torch_throw_shuffle = shuffle
    rng = np.random.RandomState(seed + 100)
    _seed_spears(w, weight=spear_weight)
    spear_n = spear_thr = nospear_n = nospear_thr = 0
    _injected = False
    for t in range(ticks):
        if not w.agents:
            break
        w.step()
        if warm_w is not None and not _injected and w._throw_w is not None:
            import torch                          # warm-start : injecte le bassin pre-forme au 1er tick
            with torch.no_grad():                 # (le gate est cree paresseusement au 1er step)
                w._throw_w.data = warm_w.clone().to(w._throw_w.dtype)
                if warm_b is not None:
                    w._throw_b.data = warm_b.clone().to(w._throw_b.dtype)
            _injected = True
        _reseed_spears(w, rng, respawn_p, weight=spear_weight)
        if t >= warmup:
            for a in w.agents:
                ctx = a.get("_throw_ctx")
                if ctx is None:
                    continue
                did = 1 if a.get("_throw_did") else 0
                if ctx:
                    spear_n += 1
                    spear_thr += did
                else:
                    nospear_n += 1
                    nospear_thr += did
    p_spear = (spear_thr / spear_n) if spear_n else 0.0
    p_nospear = (nospear_thr / nospear_n) if nospear_n else 0.0
    tot_n = spear_n + nospear_n
    return {"shuffle": bool(shuffle), "seed": int(seed),
            "binding_gap_inworld": float(p_spear - p_nospear),
            "kills_with_tool": int(getattr(w, "_throw_kills_tool", 0)),
            "spear_n": int(spear_n), "nospear_n": int(nospear_n),
            "n_alive_end": int(len(w.agents)),
            "throw_rate": float((spear_thr + nospear_thr) / tot_n) if tot_n else 0.0}


def compare(seeds=(0, 1, 2, 3), ticks=400, warmup=200, n_agents=32,
            base_metabolism=1.0, forage_payoff=1.0):
    """A/B apparie ON vs SHUFFLE par seed -> verdict. diff = gap_ON - gap_SHUFFLE. diff>0 = le
    throw-gate route sur la VRAIE presence-spear et generalise (pas artefact : le shuffle est plat).
    base_metabolism/forage_payoff : regime energetique (defaut 1.0/1.0 = letal ; sweet EDR-085 =
    0.25/3.0 = survivable, laisse le temps au gate d'apprendre)."""
    rows = []
    for s in seeds:
        on = run_arm(shuffle=False, seed=s, ticks=ticks, warmup=warmup, n_agents=n_agents,
                     base_metabolism=base_metabolism, forage_payoff=forage_payoff)
        sh = run_arm(shuffle=True, seed=s, ticks=ticks, warmup=warmup, n_agents=n_agents,
                     base_metabolism=base_metabolism, forage_payoff=forage_payoff)
        rows.append({"seed": s, "on": on["binding_gap_inworld"], "shuffle": sh["binding_gap_inworld"],
                     "kills_on": on["kills_with_tool"],
                     "on_throw": on["throw_rate"], "on_sn": on["spear_n"], "on_nn": on["nospear_n"],
                     "sh_throw": sh["throw_rate"], "alive": on["n_alive_end"],
                     "diff": on["binding_gap_inworld"] - sh["binding_gap_inworld"]})
    return {"rows": rows, "verdict": compute_ab_verdict(rows, band=0.02)}


def compare_debias(seeds=(0, 1, 2, 3), ticks=400, warmup=200, n_agents=32, respawn_p=0.5,
                   base_metabolism=0.25, forage_payoff=3.0, energy=80.0, spear_weight=2.0):
    """EDR-NAV-005 in-world : experience APPARIEE biaise (-0.5, EDR-172) vs non-biaise (0.0). Pour
    chaque bras, verdict ON-vs-SHUFFLE via compute_ab_verdict (le shuffle est le temoin d'artefact).
    Hypothese : biaise -> NEUTRE (repro EDR-172) ; non-biaise -> GRADIENT_GAGNE (1er binding in-world).
    Couche 1 (survie) a neutraliser via energy haute + spear_weight leger + base_metabolism bas, sinon
    la cohorte s'eteint avant que le gate apprenne (confond couche 1 et couche 2)."""
    biased, unbiased, info = [], [], []
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=False,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff,
              energy=energy, spear_weight=spear_weight)
    for s in seeds:
        b_on = run_arm(shuffle=False, penalty=-0.5, seed=s, **kw)
        b_sh = run_arm(shuffle=True, penalty=-0.5, seed=s, **kw)
        u_on = run_arm(shuffle=False, penalty=0.0, seed=s, **kw)
        u_sh = run_arm(shuffle=True, penalty=0.0, seed=s, **kw)
        biased.append({"seed": s, "on": b_on["binding_gap_inworld"], "shuffle": b_sh["binding_gap_inworld"],
                       "diff": b_on["binding_gap_inworld"] - b_sh["binding_gap_inworld"]})
        unbiased.append({"seed": s, "on": u_on["binding_gap_inworld"], "shuffle": u_sh["binding_gap_inworld"],
                         "diff": u_on["binding_gap_inworld"] - u_sh["binding_gap_inworld"]})
        info.append({"seed": s, "spear_n": u_on["spear_n"], "nospear_n": u_on["nospear_n"],
                     "alive": u_on["n_alive_end"], "b_on": b_on["binding_gap_inworld"],
                     "u_on": u_on["binding_gap_inworld"], "kills_b": b_on["kills_with_tool"],
                     "kills_u": u_on["kills_with_tool"]})
    return {"biased": {"rows": biased, "verdict": compute_ab_verdict(biased, band=0.02)},
            "unbiased": {"rows": unbiased, "verdict": compute_ab_verdict(unbiased, band=0.02)},
            "info": info}


def compare_density(seeds=(0, 1, 2, 3), ticks=400, warmup=200, n_agents=32, respawn_p=0.5,
                    base_metabolism=0.25, forage_payoff=3.0, energy=250.0, spear_weight=2.0,
                    antisat=None):
    """EDR-173-suite in-world : experience APPARIEE credit SPARSE (hit binaire, EDR-173) vs DENSE
    (shaping de visee _throw_aim). LES DEUX non-biaises (penalty=0). Chaque bras verdict ON-vs-SHUFFLE.
    Hypothese (raffine NAV-005) : sparse -> NEUTRE (repro EDR-173, p_success~0.001 < plancher) ; dense ->
    GRADIENT_GAGNE (le shaping remonte le signal au-dessus du plancher NAV-004 -> 1er binding in-world).
    Couche 1 levee (energy/spear_weight/night) — heritee d'EDR-173."""
    sparse, dense, info = [], [], []
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=False,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff,
              energy=energy, spear_weight=spear_weight, penalty=0.0, antisat=antisat)
    for s in seeds:
        s_on = run_arm(shuffle=False, shaping=False, seed=s, **kw)
        s_sh = run_arm(shuffle=True, shaping=False, seed=s, **kw)
        d_on = run_arm(shuffle=False, shaping=True, seed=s, **kw)
        d_sh = run_arm(shuffle=True, shaping=True, seed=s, **kw)
        sparse.append({"seed": s, "on": s_on["binding_gap_inworld"], "shuffle": s_sh["binding_gap_inworld"],
                       "diff": s_on["binding_gap_inworld"] - s_sh["binding_gap_inworld"]})
        dense.append({"seed": s, "on": d_on["binding_gap_inworld"], "shuffle": d_sh["binding_gap_inworld"],
                      "diff": d_on["binding_gap_inworld"] - d_sh["binding_gap_inworld"]})
        info.append({"seed": s, "spear_n": d_on["spear_n"], "nospear_n": d_on["nospear_n"],
                     "alive": d_on["n_alive_end"], "sparse_on": s_on["binding_gap_inworld"],
                     "dense_on": d_on["binding_gap_inworld"], "kills_sparse": s_on["kills_with_tool"],
                     "kills_dense": d_on["kills_with_tool"],
                     "throw_dense": d_on["throw_rate"], "throw_sparse": s_on["throw_rate"]})
    return {"sparse": {"rows": sparse, "verdict": compute_ab_verdict(sparse, band=0.02)},
            "dense": {"rows": dense, "verdict": compute_ab_verdict(dense, band=0.02)},
            "info": info}


def _collect_warm_direction(seed=0, ticks=40, n_agents=30, respawn_p=0.06, base_metabolism=0.05,
                            forage_payoff=3.0, energy=250.0, spear_weight=2.0, antisat=None, scale=3.0,
                            fit_steps=400):
    """Warm-start : rollout court (gate cold, juste pour collecter H), direction discriminante spear
    vs ¬spear par REGRESSION LOGISTIQUE H->has_spear (le vrai discriminant sous features correlees ;
    la difference-de-moyennes echoue). Le bassin pre-forme part 'spear-aware' -> gap>0 a l'init si la
    representation transfere. Retourne (w torch (N,), b torch (1,)) ou (None, None)."""
    import torch
    np.random.seed(seed)
    torch.manual_seed(seed)
    w = Biosphere3D(WorldConfig(base_metabolism=base_metabolism, forage_payoff=forage_payoff))
    for _ in range(n_agents):
        w.add_agent(MambaAgent(), energy=energy)
    if hasattr(w, "memory_retriever"):
        w.memory_retriever.stop()
    w.current_era = 1
    w.benchmark_mode = True
    w.night_enabled = False
    w.use_torch_inworld = True
    w.torch_throw_gate = True
    if antisat is not None:
        w.torch_throw_antisat = antisat
    rng = np.random.RandomState(seed + 100)
    _seed_spears(w, weight=spear_weight)
    Hs, ctxs = [], []
    for t in range(ticks):
        if not w.agents:
            break
        w.step()
        _reseed_spears(w, rng, respawn_p, weight=spear_weight)
        pop = getattr(w, "_torch_pop", None)
        H = None if pop is None else getattr(pop, "H", None)
        if H is None:
            continue
        H = H.detach().cpu().numpy()
        for i, a in enumerate(w.agents):
            ctx = a.get("_throw_ctx")
            if ctx is None or i >= H.shape[0]:
                continue
            Hs.append(H[i]); ctxs.append(1 if ctx else 0)
    if not Hs:
        return None, None
    Hs = np.array(Hs, dtype=np.float32); ctxs = np.array(ctxs, dtype=np.float32)
    if ctxs.sum() == 0 or (1 - ctxs).sum() == 0:
        return None, None
    X = torch.tensor(Hs); y = torch.tensor(ctxs)
    N = X.shape[1]
    w = torch.zeros(N, requires_grad=True); b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=0.05)
    for _ in range(fit_steps):
        loss = torch.nn.functional.binary_cross_entropy_with_logits(X @ w + b, y)
        opt.zero_grad(); loss.backward(); opt.step()
    d = w.detach()
    nrm = float(d.norm())
    if nrm < 1e-8:
        return None, None
    return (d / nrm * scale), b.detach()


def compare_warmstart(seeds=(0, 1, 2, 3), ticks=150, warmup=90, n_agents=30, respawn_p=0.06,
                      base_metabolism=0.05, forage_payoff=3.0, energy=250.0, spear_weight=2.0,
                      antisat=0.3, scale=3.0, collect_ticks=40):
    """Warm-start in-world (test de retention/hysteresis, analogue 167). COLD (_throw_w=0, EDR-173)
    vs WARM (_throw_w = direction spear-aware). gap mesure en fenetre TARDIVE (apres le REINFORCE
    in-world) : si WARM RETIENT gap>0 la ou COLD reste ~0 => bootstrap-barrier confirmee in-world
    (la loi transversale tient) ; si WARM erode -> les dynamiques in-world detruisent le binding."""
    cold, warm, info = [], [], []
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=False,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff, energy=energy,
              spear_weight=spear_weight, penalty=0.0, antisat=antisat)
    for s in seeds:
        wd, _wb = _collect_warm_direction(seed=s, ticks=collect_ticks, n_agents=n_agents, respawn_p=respawn_p,
                                          base_metabolism=base_metabolism, forage_payoff=forage_payoff,
                                          energy=energy, spear_weight=spear_weight, antisat=antisat, scale=scale)
        c_on = run_arm(shuffle=False, seed=s, warm_w=None, **kw)
        c_sh = run_arm(shuffle=True, seed=s, warm_w=None, **kw)
        w_on = run_arm(shuffle=False, seed=s, warm_w=wd, **kw)
        w_sh = run_arm(shuffle=True, seed=s, warm_w=wd, **kw)
        cold.append({"seed": s, "on": c_on["binding_gap_inworld"], "shuffle": c_sh["binding_gap_inworld"],
                     "diff": c_on["binding_gap_inworld"] - c_sh["binding_gap_inworld"]})
        warm.append({"seed": s, "on": w_on["binding_gap_inworld"], "shuffle": w_sh["binding_gap_inworld"],
                     "diff": w_on["binding_gap_inworld"] - w_sh["binding_gap_inworld"]})
        info.append({"seed": s, "warm_ok": wd is not None, "spear_n": w_on["spear_n"],
                     "nospear_n": w_on["nospear_n"], "alive": w_on["n_alive_end"],
                     "cold_on": c_on["binding_gap_inworld"], "warm_on": w_on["binding_gap_inworld"],
                     "throw_warm": w_on["throw_rate"], "throw_cold": c_on["throw_rate"]})
    # verdict PRIMAIRE = warm_on vs cold_on (gap tardif brut) : le warm-start bat-il le cold ?
    wvc = [{"seed": r["seed"], "on": r["warm_on"], "shuffle": r["cold_on"],
            "diff": r["warm_on"] - r["cold_on"]} for r in info]
    return {"cold": {"rows": cold, "verdict": compute_ab_verdict(cold, band=0.02)},
            "warm": {"rows": warm, "verdict": compute_ab_verdict(warm, band=0.02)},
            "warm_vs_cold": {"rows": wvc, "verdict": compute_ab_verdict(wvc, band=0.02)},
            "info": info}


def compare_rp_sweep(seeds=(0, 1, 2, 3), prey_levels=(15, 60, 150), ticks=120, warmup=30, n_agents=30,
                     respawn_p=0.06, base_metabolism=0.05, forage_payoff=3.0, energy=250.0,
                     spear_weight=2.0, antisat=0.3):
    """CONTROLE POSITIF de l'arc 172-175 : dose-reponse densite de proies (=> P(hit) => r.P) -> binding.
    Gate COLD + NON-BIAISE + recompense SPARSE (hit=+1) ; on monte r.P via les PROIES (pas la forme du
    signal, pas l'init). Hypothese (loi retention-167) : le gap bascule ~0/negatif -> POSITIF quand r.P
    franchit le plancher. `kills` = proxy observe de r.P (frequence de payoff). Verdict ON-vs-SHUFFLE
    par niveau ; le niveau ou le gap devient GRADIENT_GAGNE = franchissement du plancher."""
    import statistics as _st
    out = []
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=False,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff, energy=energy,
              spear_weight=spear_weight, penalty=0.0, antisat=antisat)
    for pc in prey_levels:
        rows, kills, throws = [], [], []
        for s in seeds:
            on = run_arm(shuffle=False, seed=s, prey_count=pc, **kw)
            sh = run_arm(shuffle=True, seed=s, prey_count=pc, **kw)
            rows.append({"seed": s, "on": on["binding_gap_inworld"], "shuffle": sh["binding_gap_inworld"],
                         "diff": on["binding_gap_inworld"] - sh["binding_gap_inworld"]})
            kills.append(on["kills_with_tool"]); throws.append(on["throw_rate"])
        out.append({"prey_count": pc, "verdict": compute_ab_verdict(rows, band=0.02),
                    "median_gap_on": _st.median([r["on"] for r in rows]),
                    "median_diff": _st.median([r["diff"] for r in rows]),
                    "median_kills": _st.median(kills), "median_throw": _st.median(throws), "rows": rows})
    return out


def compare_factorial(seeds=(0, 1, 2, 3), prey_sparse=15, prey_dense=300, ticks=120, warmup=30,
                      n_agents=30, respawn_p=0.06, base_metabolism=0.05, forage_payoff=3.0,
                      energy=250.0, spear_weight=2.0, antisat=0.3, night=False):
    """Factoriel 2^4 (EDR-177) : isole les 4 confounds du binding in-world. Facteurs (True=propre) :
    no_consume (F1), weightless (F2), dense (F3 : prey_count=dense/sparse), conditional_credit (F4).
    Regime couche-1 neutralisee + non-biaise (penalty=0) -> seuls les 4 facteurs varient. Par cellule :
    K seeds x {ON, SHUFFLE}, diff = gap_ON - gap_SHUFFLE, verdict via compute_ab_verdict. La cellule
    tout-propre (T,T,T,T) est le test decisif : le substrat binde-t-il in-world PROPREMENT ?"""
    import itertools
    import statistics as _st
    kw = dict(ticks=ticks, warmup=warmup, n_agents=n_agents, respawn_p=respawn_p, night=night,
              base_metabolism=base_metabolism, forage_payoff=forage_payoff, energy=energy,
              spear_weight=spear_weight, penalty=0.0, antisat=antisat)
    cells = []
    for nc, wl, dn, cc in itertools.product([False, True], repeat=4):
        prey = prey_dense if dn else prey_sparse
        rows, kills, throws = [], [], []
        for s in seeds:
            on = run_arm(shuffle=False, seed=s, prey_count=prey, no_consume=nc, weightless=wl,
                         conditional_credit=cc, **kw)
            sh = run_arm(shuffle=True, seed=s, prey_count=prey, no_consume=nc, weightless=wl,
                         conditional_credit=cc, **kw)
            diff = on["binding_gap_inworld"] - sh["binding_gap_inworld"]
            rows.append({"seed": s, "on": on["binding_gap_inworld"],
                         "shuffle": sh["binding_gap_inworld"], "diff": diff})
            kills.append(on["kills_with_tool"]); throws.append(on["throw_rate"])
        cells.append({"no_consume": nc, "weightless": wl, "dense": dn, "conditional_credit": cc,
                      "prey_count": prey, "verdict": compute_ab_verdict(rows, band=0.02),
                      "median_diff": _st.median([r["diff"] for r in rows]),
                      "median_gap_on": _st.median([r["on"] for r in rows]),
                      "median_kills": _st.median(kills), "median_throw": _st.median(throws),
                      "diffs": [r["diff"] for r in rows], "rows": rows})
    return cells


def _factorial_effects(cells):
    """Effets principaux + interactions 2-way sur la carte 2^4 (EDR-177). Chaque cellule expose ses 4
    niveaux booleens (True=propre) + `diffs` (liste des diff ON-SHUFFLE par seed). Effet principal d'un
    facteur = moyenne(diffs | facteur propre) - moyenne(diffs | facteur confound), poole sur les 8
    cellules de chaque niveau. Interaction 2-way = demi-difference des effets simples croises."""
    import statistics as _st
    factors = ("no_consume", "weightless", "dense", "conditional_credit")

    def _pool(pred):
        vals = [d for c in cells if pred(c) for d in c["diffs"]]
        return _st.mean(vals) if vals else 0.0

    main = {f: _pool(lambda c, f=f: c[f]) - _pool(lambda c, f=f: not c[f]) for f in factors}
    inter = {}
    for i in range(len(factors)):
        for j in range(i + 1, len(factors)):
            f, g = factors[i], factors[j]
            both = _pool(lambda c, f=f, g=g: c[f] and c[g])
            neither = _pool(lambda c, f=f, g=g: (not c[f]) and (not c[g]))
            only_f = _pool(lambda c, f=f, g=g: c[f] and not c[g])
            only_g = _pool(lambda c, f=f, g=g: (not c[f]) and c[g])
            inter[f"{f}×{g}"] = 0.5 * ((both + neither) - (only_f + only_g))
    return {"main": main, "interactions": inter}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    seeds = tuple(int(x) for x in os.environ.get("TTG_SEEDS", "0,1,2,3").split(","))
    ticks = int(os.environ.get("TTG_TICKS", "400"))
    warmup = int(os.environ.get("TTG_WARMUP", "200"))
    agents = int(os.environ.get("TTG_AGENTS", "32"))
    bm = float(os.environ.get("TTG_BM", "0.25"))         # base_metabolism (sweet EDR-085)
    fp = float(os.environ.get("TTG_FP", "3.0"))          # forage_payoff  (sweet EDR-085)
    rp = float(os.environ.get("TTG_RESPAWN", "0.5"))     # respawn_p : bas => garde du contexte ¬spear
    en = float(os.environ.get("TTG_ENERGY", "80"))       # energie initiale (haute = survie ++)
    sw = float(os.environ.get("TTG_SPEARW", "2.0"))      # poids spear (leger = pas de drain de portage)
    _as = os.environ.get("TTG_ANTISAT")                  # anti-sat (defaut monde 6.0 ; bas => throw_rate ++)
    asat = float(_as) if _as is not None else None
    if os.environ.get("TTG_MODE", "debias") == "debias":
        out = compare_debias(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents,
                             respawn_p=rp, base_metabolism=bm, forage_payoff=fp,
                             energy=en, spear_weight=sw)
        for r in out["info"]:
            print(f"seed={r['seed']} spear_n={r['spear_n']} nospear_n={r['nospear_n']} alive={r['alive']} "
                  f"| gap_BIAISE={r['b_on']:+.3f} (kills {r['kills_b']}) "
                  f"gap_NONBIAISE={r['u_on']:+.3f} (kills {r['kills_u']})")
        _lab = {"GRADIENT_GAGNE": "BINDING_INWORLD_REEL", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS",
                "NEUTRE": "PAS_DE_BINDING"}
        for arm in ("biased", "unbiased"):
            v = out[arm]["verdict"]
            print(f"[{arm:9s}] VERDICT: {v['verdict']} -> {_lab.get(v['verdict'], v['verdict'])}  {v}")
        bv, uv = out["biased"]["verdict"]["verdict"], out["unbiased"]["verdict"]["verdict"]
        print("CONCLUSION:", "DEBIAS_DEBLOQUE_LE_BINDING" if (uv == "GRADIENT_GAGNE" and bv != "GRADIENT_GAGNE")
              else "PAS_DE_BASCULE" if uv != "GRADIENT_GAGNE" else "BINDING_INDEPENDANT_DU_BIAIS")
    elif os.environ.get("TTG_MODE") == "density":
        out = compare_density(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents,
                              respawn_p=rp, base_metabolism=bm, forage_payoff=fp,
                              energy=en, spear_weight=sw, antisat=asat)
        for r in out["info"]:
            print(f"seed={r['seed']} spear_n={r['spear_n']} nospear_n={r['nospear_n']} alive={r['alive']} "
                  f"| gap_SPARSE={r['sparse_on']:+.3f} (thr {r['throw_sparse']:.2f} kills {r['kills_sparse']}) "
                  f"gap_DENSE={r['dense_on']:+.3f} (thr {r['throw_dense']:.2f} kills {r['kills_dense']})")
        _lab = {"GRADIENT_GAGNE": "BINDING_INWORLD_REEL", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS",
                "NEUTRE": "PAS_DE_BINDING"}
        for arm in ("sparse", "dense"):
            v = out[arm]["verdict"]
            print(f"[{arm:6s}] VERDICT: {v['verdict']} -> {_lab.get(v['verdict'], v['verdict'])}  {v}")
        sv, dv = out["sparse"]["verdict"]["verdict"], out["dense"]["verdict"]["verdict"]
        print("CONCLUSION:", "DENSITE_DEBLOQUE_LE_BINDING" if (dv == "GRADIENT_GAGNE" and sv != "GRADIENT_GAGNE")
              else "PAS_DE_BASCULE" if dv != "GRADIENT_GAGNE" else "BINDING_INDEPENDANT_DE_LA_DENSITE")
    elif os.environ.get("TTG_MODE") == "warmstart":
        scale = float(os.environ.get("TTG_SCALE", "3.0"))
        out = compare_warmstart(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents,
                                respawn_p=rp, base_metabolism=bm, forage_payoff=fp, energy=en,
                                spear_weight=sw, antisat=(asat if asat is not None else 0.3), scale=scale)
        for r in out["info"]:
            print(f"seed={r['seed']} warm_ok={r['warm_ok']} spear_n={r['spear_n']} nospear_n={r['nospear_n']} "
                  f"alive={r['alive']} | gap_COLD={r['cold_on']:+.3f} (thr {r['throw_cold']:.2f}) "
                  f"gap_WARM={r['warm_on']:+.3f} (thr {r['throw_warm']:.2f})")
        _lab = {"GRADIENT_GAGNE": "BINDING_INWORLD_REEL", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS",
                "NEUTRE": "PAS_DE_BINDING"}
        for arm in ("cold", "warm"):
            v = out[arm]["verdict"]
            print(f"[{arm:4s} vs shuffle] {v['verdict']} -> {_lab.get(v['verdict'], v['verdict'])}")
        wvc = out["warm_vs_cold"]["verdict"]
        print(f"[warm vs COLD] VERDICT: {wvc['verdict']}  {wvc}")
        import statistics as _st
        _wm = _st.median([r["warm_on"] for r in out["info"]])
        _cm = _st.median([r["cold_on"] for r in out["info"]])
        print(f"gap tardif median : WARM={_wm:+.3f}  COLD={_cm:+.3f}")
        print("CONCLUSION:", "WARMSTART_RETIENT_LE_BINDING" if (wvc["verdict"] == "GRADIENT_GAGNE" and _wm > 0.02)
              else "WARM_ERODE_VERS_COLD" if _wm <= 0.02
              else "WARM_>_COLD_MAIS_FAIBLE")
    elif os.environ.get("TTG_MODE") == "rpsweep":
        levels = tuple(int(x) for x in os.environ.get("TTG_PREY", "15,60,150,400").split(","))
        rows = compare_rp_sweep(seeds=seeds, prey_levels=levels, ticks=ticks, warmup=warmup,
                                n_agents=agents, respawn_p=rp, base_metabolism=bm, forage_payoff=fp,
                                energy=en, spear_weight=sw, antisat=(asat if asat is not None else 0.3))
        _lab = {"GRADIENT_GAGNE": "BINDING_REEL", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PAS_DE_BINDING"}
        for r in rows:
            v = r["verdict"]
            print(f"prey={r['prey_count']:4d} | median_kills={r['median_kills']:5.1f} (r.P proxy) "
                  f"throw={r['median_throw']:.2f} gap_ON={r['median_gap_on']:+.3f} diff={r['median_diff']:+.3f} "
                  f"-> {v['verdict']} ({_lab.get(v['verdict'], '?')}) sign_p={v.get('sign_p')}")
        _pos = [r for r in rows if r["verdict"]["verdict"] == "GRADIENT_GAGNE"]
        if _pos:
            print(f"CONCLUSION: DOSE_REPONSE_rP -> BINDING EMERGE des prey>={_pos[0]['prey_count']} "
                  f"(kills~{_pos[0]['median_kills']:.0f}) => plancher r.P FRANCHI, cause CONFIRMEE")
        else:
            print("CONCLUSION: PAS_DE_BINDING meme a forte densite -> CONFOND PLUS PROFOND que r.P")
    elif os.environ.get("TTG_MODE") == "factorial":
        ps = int(os.environ.get("TTG_PREY_SPARSE", "15"))
        pd = int(os.environ.get("TTG_PREY_DENSE", "300"))
        # Le regime (energy=250, base_metabolism=0.05, respawn_p=0.06, forage_payoff=3.0, spear_weight=2.0,
        # antisat=0.3, penalty=0.0, night=False) est FIXE pour l'isolation (couche-1 neutralisee, non-biaise).
        # On laisse les defauts de compare_factorial s'appliquer plutot que les TTG_* partages du fichier
        # (dont les defauts 80/0.25/0.5 confondraient la couche 1). Seuls les knobs OPERATIONNELS restent
        # pilotables (seeds, densites, ticks, warmup, n_agents).
        cells = compare_factorial(seeds=seeds, prey_sparse=ps, prey_dense=pd, ticks=ticks,
                                  warmup=warmup, n_agents=agents)
        _lab = {"GRADIENT_GAGNE": "BINDE", "HEBBIEN_GAGNE": "SHUFFLE_BINDE_PLUS", "NEUTRE": "PLAT"}

        def _tag(c):
            return ("N" if c["no_consume"] else ".") + ("W" if c["weightless"] else ".") + \
                   ("D" if c["dense"] else ".") + ("K" if c["conditional_credit"] else ".")

        for c in sorted(cells, key=lambda c: c["median_diff"], reverse=True):
            v = c["verdict"]
            print(f"[{_tag(c)}] diff={c['median_diff']:+.3f} gap_ON={c['median_gap_on']:+.3f} "
                  f"kills={c['median_kills']:.0f} throw={c['median_throw']:.2f} "
                  f"-> {v['verdict']} ({_lab.get(v['verdict'], '?')}) sign_p={v.get('sign_p')}")
        eff = _factorial_effects(cells)
        print("\nEFFETS PRINCIPAUX (diff propre - diff confound) :")
        for f, e in eff["main"].items():
            print(f"  {f:22s} {e:+.3f}")
        print("INTERACTIONS 2-way :")
        for p, e in eff["interactions"].items():
            print(f"  {p:34s} {e:+.3f}")
        c0 = next(c for c in cells if c["no_consume"] and c["weightless"] and c["dense"]
                  and c["conditional_credit"])
        v0 = c0["verdict"]
        print(f"\nCELLULE-0 (tout-propre NWDK) : diff={c0['median_diff']:+.3f} gap_ON={c0['median_gap_on']:+.3f} "
              f"-> {v0['verdict']} sign_p={v0.get('sign_p')}")
        if v0["verdict"] == "GRADIENT_GAGNE" and len(seeds) >= 12:
            print("CONCLUSION: SUBSTRAT_BINDE_IN_WORLD_PROPRE")
        elif v0["verdict"] == "GRADIENT_GAGNE":
            print(f"CONCLUSION: BINDING_APPARENT mais n={len(seeds)}<12 -> NON-CONCLUANT "
                  "(garde-fou power-evaporation ; relancer avec TTG_SEEDS>=12)")
        else:
            print("CONCLUSION: VERROU_IN_WORLD_PLUS_PROFOND")
    else:
        out = compare(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents,
                      base_metabolism=bm, forage_payoff=fp)
        for r in out["rows"]:
            print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_SHUF={r['shuffle']:+.3f} "
                  f"diff={r['diff']:+.3f} | throw_ON={r['on_throw']:.3f} spear_n={r['on_sn']} "
                  f"nospear_n={r['on_nn']} alive={r['alive']} kills_ON={r['kills_on']}")
        print("VERDICT:", out["verdict"])
