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
            energy=80.0, spear_weight=2.0, shaping=False, antisat=None):
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
    if antisat is not None:
        w.torch_throw_antisat = antisat          # modere l'anti-sat (defaut 6.0 ecrase p->0 => throw_rate~0)
    w.torch_throw_shuffle = shuffle
    rng = np.random.RandomState(seed + 100)
    _seed_spears(w, weight=spear_weight)
    spear_n = spear_thr = nospear_n = nospear_thr = 0
    for t in range(ticks):
        if not w.agents:
            break
        w.step()
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
    else:
        out = compare(seeds=seeds, ticks=ticks, warmup=warmup, n_agents=agents,
                      base_metabolism=bm, forage_payoff=fp)
        for r in out["rows"]:
            print(f"seed={r['seed']} gap_ON={r['on']:+.3f} gap_SHUF={r['shuffle']:+.3f} "
                  f"diff={r['diff']:+.3f} | throw_ON={r['on_throw']:.3f} spear_n={r['on_sn']} "
                  f"nospear_n={r['on_nn']} alive={r['alive']} kills_ON={r['kills_on']}")
        print("VERDICT:", out["verdict"])
