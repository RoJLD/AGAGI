"""tools/coevolve_use_long.py — EDR 089 : l'usage co-évolué du langage paye-t-il sur substrat à survie
LONGUE ? Power EDR 083 sur son levier #1 (la survie). Réutilise le moteur d'083 (coevolve + _run_era_lewis ;
_setup met déjà night OFF) avec un cfg SWEET-SPOT (085) ; ajoute mesure à composantes + boucle R appariée
+ stats rigoureuses. N'altère pas coevolve_language.py.
Pré-enregistrement : docs/superpowers/specs/2026-06-15-EDR089-Coevolve-Use-Long-design.md
"""
import sys
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lexicon import _setup as _setup3

METAB, PAYOFF = 0.25, 3.0          # sweet spot survie longue (EDR 085)
PREY_COUNT = 15                    # EDR089 addendum : _setup3 met 4 (food-scarce -> survie ~20, VOID) ;
                                   # on remonte au defaut WorldConfig (celui d'087 qui passait le gate >120).
                                   # Neutre au contraste FIABLE/BRUITE (la nourriture n'est pas le signal).


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _run_era_clean(cfg, genomes, use_head=False, decode_act=False, heads=None, max_ticks=300, measure=True):
    """Variante DÉTERMINISTE de _run_era_lewis : stoppe le memory_retriever (thread KuzuDB ambiant)
    AVANT la boucle de simulation (sinon in_mem timing-dépendant -> non reproductible). measure=True
    -> {ticks,mammoth,leurre,survivors} ; measure=False -> {scored} (génomes triés par life_score)."""
    env = Biosphere3D(cfg)
    _setup3(env)
    env.config.target_prey_count = PREY_COUNT   # EDR089 addendum : substrat NON food-scarce -> survie LONGUE (gate)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    env.use_ref_head = use_head
    env.decode_act = decode_act
    for k, g in enumerate(genomes):
        a = MambaAgent()
        a.from_genome(g)
        if heads is not None:
            a.ref_head = heads[k]
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    if measure:
        return {"ticks": t, "mammoth": sum(ag.get("mammoth_kills", 0) for ag in pool),
                "leurre": int(getattr(env, "leurre_hits", 0)), "survivors": len(env.agents)}
    scored = sorted([(calculate_life_score(a), a["model"].genome if "model" in a else a.get("genome"))
                     for a in pool], key=lambda sg: sg[0], reverse=True)[:5]
    return {"scored": scored}


def _measure_full(cfg, champions, mc, use_head, heads, num_agents, n, base):
    """Mesure sur n ères propres (seedées, plage 1000+ disjointe de coevolve) : kills (primaire),
    net (kills − leurre_hits), survie (ticks). decode_act=False (l'usage émerge, n'est pas imposé)."""
    out = {"kills": [], "nets": [], "survs": []}
    for i in range(n):
        seed_at(base, 1000 + i)
        genomes = _reproduce(champions, num_agents, mc)
        hd = heads[:len(genomes)] if heads else None
        r = _run_era_clean(cfg, genomes, use_head=use_head, decode_act=False, heads=hd, measure=True)
        k = int(r["mammoth"]); le = int(r["leurre"])
        out["kills"].append(k)
        out["nets"].append(k - le)
        out["survs"].append(int(r["ticks"]))
    return out


def _coevolve(cfg, mc, use_head, heads, gens, num_agents, K, base):
    """Co-évolution CLEAN des auditeurs dans Lewis (runner déparasité -> reproductible). use_head ->
    locuteurs fiables. seed_at(base, gen) -> MÊME monde pour FIABLE et BRUITÉ d'une même répétition."""
    best = [(0.0, g) for g in _load_champions()]
    for gen in range(gens):
        seed_at(base, gen)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        hd = heads[:len(genomes)] if heads else None
        scored = _run_era_clean(cfg, genomes, use_head=use_head, decode_act=False, heads=hd, measure=False)["scored"]
        if scored and K > 1:
            g0 = scored[0][1]
            vals = [_run_era_clean(cfg, [g0] * num_agents, use_head=use_head, decode_act=False,
                                   heads=(heads[:num_agents] if heads else None), measure=False)["scored"][0][0]
                    for _ in range(K)]
            scored[0] = (float(np.mean(vals)), g0)
        best = sorted(best + scored, key=lambda sg: sg[0], reverse=True)[:5]
    return [g for _s, g in best]


def _report(h, d_kills, d_nets, fia_k, bru_k, survs, R, gens, _return):
    summ = st.paired_summary(d_kills)
    med = float(np.median(d_kills))
    lo, hi = st.bootstrap_ci(d_kills, np.mean, seed=h.seed)
    surv_med = float(np.median(survs))
    print(f"\n=== Mammouths : FIABLE {np.mean(fia_k):.2f} vs BRUITE {np.mean(bru_k):.2f} ({R} reps appariees) ===")
    print(f"  d (FIABLE-BRUITE kills) = {summ['mean']:+.2f} +/- {summ['se']:.2f} SE ; win {summ['win_rate']*100:.0f}% ; "
          f"Wilcoxon p={summ['wilcoxon_p']:.3f} ; IC95=[{lo:+.2f},{hi:+.2f}]")
    print(f"  net (diagnostic) d = {np.mean(d_nets):+.2f} ; survie mediane = {surv_med:.0f} ticks (gate >120)")
    print("=== VERDICT (pre-enregistre) ===")
    if surv_med <= 120:
        verdict = "VOID"
        print(f"  -> VOID : substrat pas assez long (survie {surv_med:.0f} <= 120). Re-regler l'energie.")
    elif summ["wilcoxon_p"] < 0.05 and med > 0 and lo > 0:
        verdict = "USAGE SELECTIONNE"
        print(f"  -> USAGE SELECTIONNE : ecouter un signal FIABLE est selectionne a survie longue "
              f"(median +{med:.1f} kills, p={summ['wilcoxon_p']:.3f}, IC_inf={lo:+.2f}). Langage fonctionnel EMERGE.")
    elif med > 0:
        verdict = "TENDANCE SOUS-SEUIL"
        print(f"  -> TENDANCE sous 2 SE (+{med:.1f}, comme 083) : la survie longue ne suffit pas. "
              f"Goulot = selection EXPLICITE de l'usage (levier #2).")
    else:
        verdict = "NEGATIF ROBUSTE"
        print(f"  -> NEGATIF : meme a survie longue, le signal fiable n'est pas exploite ({med:+.1f}).")
    h.save({"R": R, "gens": gens, "d_kills": d_kills, "d_nets": d_nets, "fia_k": fia_k, "bru_k": bru_k,
            "summary": summ, "median": med, "ci": [lo, hi], "surv_med": surv_med, "verdict": verdict})
    if _return:
        return {"d_kills": d_kills, "summary": summ, "median": med, "ci": [lo, hi], "surv_med": surv_med, "verdict": verdict}


def main(R=8, gens=20, num_agents=24, K=4, n_eval=8, seed=None, _return=False):
    with Harness(seed=seed, name="coevolve_use_long", with_db=False) as h:
        base = h.seed
        cfg = _sweet_cfg()
        mc = MutationConfig(weight_init_std=2.0)
        print(f"EDR089 : usage co-evolue sur substrat LONG (sweet-spot, memoire OFF). R={R}, gens={gens}, seed={base}.")
        d_kills, fia_k, bru_k, d_nets, survs = [], [], [], [], []
        prog = h.progress(R, label="repetitions FIABLE vs BRUITE")
        for r in range(R):
            rb = base + r * 100000          # base disjointe par répétition (>> gens + 1000+n_eval)
            np.random.seed(rb)              # état global identique entre séquentiel et mp (isolement par rep)
            rng = np.random.RandomState(rb)
            heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(num_agents)]
            train_population(heads, steps=5000, seed=rb)        # locuteurs fiables (par répétition)
            cf = _coevolve(cfg, mc, True, heads, gens, num_agents, K, base=rb)
            cb = _coevolve(cfg, mc, False, None, gens, num_agents, K, base=rb)
            mf = _measure_full(cfg, cf, mc, True, heads, num_agents, n_eval, base=rb)
            mb = _measure_full(cfg, cb, mc, False, None, num_agents, n_eval, base=rb)
            d_kills.append(float(np.mean(mf["kills"]) - np.mean(mb["kills"])))
            d_nets.append(float(np.mean(mf["nets"]) - np.mean(mb["nets"])))
            fia_k.append(float(np.mean(mf["kills"]))); bru_k.append(float(np.mean(mb["kills"])))
            survs.extend(mf["survs"] + mb["survs"])
            prog.update()
        return _report(h, d_kills, d_nets, fia_k, bru_k, survs, R, gens, _return)


def _one_rep(args):
    """Une répétition (process isolé) : entraîne les têtes, co-évolue FIABLE & BRUITÉ (appariés au même
    rb), mesure les deux. Déterministe par rb -> identique au séquentiel. Silence le bruit par process."""
    import logging, warnings, os
    logging.disable(logging.CRITICAL)
    warnings.filterwarnings("ignore")
    rb, gens, num_agents, K, n_eval, work_dir = args
    os.chdir(work_dir)   # synchronise le cwd du worker sur celui du parent -> hall_of_fame.pkl identique
    np.random.seed(rb)   # état global identique au séquentiel (Harness seed_at(base,0) avant rep 0)
    rng = np.random.RandomState(rb)
    heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(num_agents)]
    train_population(heads, steps=5000, seed=rb)
    cfg = _sweet_cfg()
    mc = MutationConfig(weight_init_std=2.0)
    cf = _coevolve(cfg, mc, True, heads, gens, num_agents, K, base=rb)
    cb = _coevolve(cfg, mc, False, None, gens, num_agents, K, base=rb)
    mf = _measure_full(cfg, cf, mc, True, heads, num_agents, n_eval, base=rb)
    mb = _measure_full(cfg, cb, mc, False, None, num_agents, n_eval, base=rb)
    return {"d_kills": float(np.mean(mf["kills"]) - np.mean(mb["kills"])),
            "d_nets": float(np.mean(mf["nets"]) - np.mean(mb["nets"])),
            "fia_k": float(np.mean(mf["kills"])), "bru_k": float(np.mean(mb["kills"])),
            "survs": list(mf["survs"]) + list(mb["survs"])}


def main_mp(R=8, gens=20, num_agents=24, K=4, n_eval=8, seed=None, n_procs=4, _return=False):
    from concurrent.futures import ProcessPoolExecutor
    with Harness(seed=seed, name="coevolve_use_long", with_db=False) as h:
        base = h.seed
        print(f"EDR089 MULTIPROCESS : R={R}, gens={gens}, n_procs={n_procs}, seed={base}.")
        import os as _os
        cwd = _os.getcwd()
        args = [(base + r * 100000, gens, num_agents, K, n_eval, cwd) for r in range(R)]
        with ProcessPoolExecutor(max_workers=n_procs) as ex:
            results = list(ex.map(_one_rep, args))   # ordre préservé -> déterministe
        d_kills = [r["d_kills"] for r in results]
        d_nets = [r["d_nets"] for r in results]
        fia_k = [r["fia_k"] for r in results]
        bru_k = [r["bru_k"] for r in results]
        survs = [s for r in results for s in r["survs"]]
        return _report(h, d_kills, d_nets, fia_k, bru_k, survs, R, gens, _return)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()
