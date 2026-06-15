"""tools/coevolve_language.py — Co-évoluer l'USAGE du langage sous sélection (EDR 083).

EDR 082 : imposer le décode-et-agis ne paye pas ; il faut SÉLECTIONNER l'usage. Ici on ne l'impose
pas : les agents ÉCOUTENT via leur connectome (in_hear -> action) et ÉVOLUENT sous sélection (life_score
robuste). On compare deux régimes d'évolution dans Lewis : locuteurs FIABLES (têtes co-entraînées,
in_hear cohérent) vs BRUITÉS (connectome, in_hear ~ loterie 053). Si écouter un signal fiable est
sélectionné, la chasse (Mammouths) doit MIEUX évoluer avec des locuteurs fiables.

Usage : HEADLESS=1 python -m tools.coevolve_language
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import seed_at, Harness
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lang_on_competent import _run_era_lewis


def coevolve(cfg, mc, use_head, heads, gens, num_agents, K, prog, base=0):
    """Évolution robuste dans Lewis ; les auditeurs (connectomes) évoluent. use_head -> locuteurs fiables."""
    best = [(0.0, g) for g in _load_champions()]
    for gen in range(gens):
        seed_at(base, gen)           # APPARIEMENT (D1) : gen identique -> MÊME monde pour FIABLE et BRUITE
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        hd = heads[:len(genomes)] if heads else None
        scored = _run_era_lewis(cfg, genomes, use_head=use_head, decode_act=False, heads=hd)["scored"]
        if scored and K > 1:
            g0 = scored[0][1]
            vals = [_run_era_lewis(cfg, [g0] * num_agents, use_head=use_head, decode_act=False,
                                   heads=(heads[:num_agents] if heads else None))["scored"][0][0]
                    for _ in range(K)]
            scored[0] = (float(np.mean(vals)), g0)
        best = sorted(best + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
    return [g for _s, g in best]


def _measure(cfg, champions, mc, use_head, heads, num_agents, n=8, base=0):
    """Mammouths tués (moyenne sur n ères propres) par une population issue des champions."""
    mk = []
    for i in range(n):
        seed_at(base, 1000 + i)      # plage disjointe de coevolve (D1) : 1000+ -> pas de collision
        genomes = _reproduce(champions, num_agents, mc)
        hd = heads[:len(genomes)] if heads else None
        r = _run_era_lewis(cfg, genomes, use_head=use_head, decode_act=False, heads=hd, measure=True)
        mk.append(r["mammoth"])
    return mk


def main(gens=15, num_agents=24, K=4, n_eval=8, seed=None):
    with Harness(seed=seed, name="coevolve_language", with_db=True) as h:
        cfg = WorldConfig()
        mc = MutationConfig(weight_init_std=2.0)
        base = h.seed
        rng = np.random.RandomState(base)
        heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(num_agents)]
        train_population(heads, steps=5000, seed=base)       # code partagé fiable (locuteurs)

        print(f"CO-EVOLUTION DE L'USAGE : auditeurs evoluent ; locuteurs FIABLES vs BRUITES. {gens} gens. seed={base}.")
        champ_fiable = coevolve(cfg, mc, True, heads, gens, num_agents, K,
                                h.progress(gens, label="evo FIABLE"), base=base)
        champ_bruite = coevolve(cfg, mc, False, None, gens, num_agents, K,
                                h.progress(gens, label="evo BRUITE"), base=base)

        pe = h.progress(2, label="mesure Mammouths")
        mf = _measure(cfg, champ_fiable, mc, True, heads, num_agents, n_eval, base=base); pe.update()
        mb = _measure(cfg, champ_bruite, mc, False, None, num_agents, n_eval, base=base); pe.update()

        print(f"\n=== Mammouths tues par les champions evolues (moyenne +/- ecart, {n_eval} eres) ===")
        print(f"  locuteurs FIABLES : {np.mean(mf):.2f} +/- {np.std(mf):.2f}")
        print(f"  locuteurs BRUITES : {np.mean(mb):.2f} +/- {np.std(mb):.2f}")
        d = np.mean(mf) - np.mean(mb)
        se = np.sqrt(np.var(mf, ddof=1)/len(mf) + np.var(mb, ddof=1)/len(mb)) if min(len(mf), len(mb)) > 1 else float("inf")
        print(f"  ecart = {d:+.2f} +/- {se:.2f} (SE)")
        print("\n=== VERDICT ===")
        if d > 2 * se and d > 0:
            print(f"  -> ECOUTER un signal FIABLE est SELECTIONNE : la chasse evolue mieux ({np.mean(mf):.1f} vs {np.mean(mb):.1f}, >2 SE).")
            print(f"     Le langage fonctionnel EMERGE sous selection (la vraie reponse a 053/082).")
        elif d > 0:
            print(f"  -> tendance ({d:+.1f}) mais sous 2 SE : effet possible, a powerer (plus de seeds/gens).")
        else:
            print(f"  -> pas d'avantage ({d:+.1f}) : meme co-evolue, le signal fiable n'est pas exploite ici.")
        h.save({
            "mf": [float(x) for x in mf],
            "mb": [float(x) for x in mb],
            "mean_fiable": float(np.mean(mf)),
            "mean_bruite": float(np.mean(mb)),
            "ecart": float(d),
            "se": float(se),
        })


if __name__ == "__main__":
    main()
