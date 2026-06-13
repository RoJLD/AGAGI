"""tools/relang_sweet.py — Le langage paye-t-il sur un substrat à SURVIE LONGUE ? (EDR 087)

Climax de l'arc survie→langage, DESIGN CORRIGÉ après revue adversariale (EDR 086 audit). EDR 082 : le
langage ne payait pas (agents morts ~45 ticks). EDR 085 : sweet spot d'énergie -> survie longue. On
re-teste ici, avec un design qui corrige les 3 confounds bloquants de l'audit :

  1. APPARIEMENT VRAI : np.random.seed(seed) avant CHAQUE bras -> monde identique (placements, proies,
     crit, gumbel) entre les bras d'un même seed. Sans ça la SE est invalide.
  2. NUIT DÉSACTIVÉE (night_enabled=False) + GATE sur la survie (>120 ticks) -> le substrat est
     réellement à survie longue (sinon test invalide, comme 082).
  3. BRAS DE CONTRÔLE BROUILLÉ : FIABLE (contenu vrai) vs BROUILLÉ (contenu aléatoire, MÊME mouvement
     décode-et-agis) -> isole le CONTENU LINGUISTIQUE du téléguidage spatial. Plus SOLO (n'agit pas).

Contraste clé = FIABLE − BROUILLÉ (le contenu paye-t-il ?). Métrique pré-enregistrée : Mammouths tués.
Usage : HEADLESS=1 python -m tools.relang_sweet
"""
import time
import numpy as np

from src.environments.config import WorldConfig, PreyConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.referential_head import new_head, train_population
from src.graph_rag.async_logger import logger as async_logger
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.progress import Progress

METAB, PAYOFF = 0.25, 3.0   # sweet spot (EDR 085)


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _setup_balanced(env):
    """Monde équilibré : nourriture de base (Lapins) + apex (langage). Nuit OFF (audit EDR 086)."""
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.night_enabled = False              # CORRECTIF audit : sinon drain nocturne ×2.5 -> régime létal
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)
    env.config.preys["Ours"] = PreyConfig(hp=60.0, damage=30.0, moves_per_tick=0.3)
    for _ in range(3):
        for ref in ("Mammouth", "Ours", "Leurre"):
            env._spawn_prey_instance(ref)


def _run_era(cfg, genomes, use_head=False, decode_act=False, scramble=False, heads=None,
             world_seed=0, max_ticks=300, measure=False):
    np.random.seed(world_seed)             # APPARIEMENT : monde identique entre bras (même seed)
    env = Biosphere3D(cfg)
    _setup_balanced(env)
    env.use_ref_head = use_head
    env.decode_act = decode_act
    env.scramble_signal = scramble
    env.decode_act_fires = 0
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
    out = {"ticks": t, "fires": int(getattr(env, "decode_act_fires", 0))}
    if measure:
        out["mammoth"] = sum(ag.get("mammoth_kills", 0) for ag in pool)
        out["survivors"] = len(env.agents)
    else:
        out["scored"] = sorted([(calculate_life_score(a),
                                 a["model"].genome if "model" in a else a.get("genome")) for a in pool],
                               key=lambda sg: sg[0], reverse=True)[:5]
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return out


def evolve(cfg, mc, gens, num_agents, K, prog):
    best = [(0.0, g) for g in _load_champions()]
    for gi in range(gens):
        np.random.seed(7000 + gi)
        genomes = _reproduce([g for _s, g in best], num_agents, mc)
        scored = _run_era(cfg, genomes, world_seed=gi)["scored"]
        if scored and K > 1:
            g0 = scored[0][1]
            vals = [_run_era(cfg, [g0] * num_agents, world_seed=gi * 100 + r)["scored"][0][0] for r in range(K)]
            scored[0] = (float(np.mean(vals)), g0)
        best = sorted(best + scored, key=lambda sg: sg[0], reverse=True)[:5]
        prog.update()
    return [g for _s, g in best]


def _stats(diffs):
    d = np.array(diffs, dtype=float)
    se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float("inf")
    return d.mean(), se, float(np.mean(d > 0))


def main(gens=12, num_agents=24, K=4, seeds=range(12)):
    async_logger.start()
    for _ in range(50):
        if async_logger.get_db():
            break
        time.sleep(0.1)
    cfg = _sweet_cfg()
    mc = MutationConfig(weight_init_std=2.0)
    seeds = list(seeds)
    print(f"LANGAGE SUR SURVIE LONGUE (design corrige) : sweet-spot, nuit OFF, 3 bras apparies.")

    champions = evolve(cfg, mc, gens, num_agents, K, Progress(gens, label="evolution sweet-spot"))
    surv = np.mean([_run_era(cfg, _reproduce(champions, num_agents, mc), world_seed=900 + i, measure=True)["ticks"]
                    for i in range(4)])
    print(f"  survie des champions : {surv:.0f} ticks  -> {'OK (>120)' if surv > 120 else 'INVALIDE (<120, substrat letal)'}")

    fia_m, scr_m, solo_m, dc, df, fires = [], [], [], [], [], []
    pf = Progress(len(seeds) * 3, label="FIABLE/BROUILLE/SOLO")
    for s in seeds:
        np.random.seed(2000 + s)
        genomes = _reproduce(champions, num_agents, mc)
        rng = np.random.RandomState(s)
        heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(len(genomes))]
        train_population(heads, steps=5000, seed=s)
        rf = _run_era(cfg, genomes, True, True, False, heads, world_seed=s, measure=True); pf.update()
        rs = _run_era(cfg, genomes, True, True, True, heads, world_seed=s, measure=True); pf.update()
        ro = _run_era(cfg, genomes, True, False, False, heads, world_seed=s, measure=True); pf.update()
        fia_m.append(rf["mammoth"]); scr_m.append(rs["mammoth"]); solo_m.append(ro["mammoth"])
        dc.append(rf["mammoth"] - rs["mammoth"])     # CONTENU : FIABLE - BROUILLE
        df.append(rf["mammoth"] - ro["mammoth"])     # plein : FIABLE - SOLO
        fires.append(rf["fires"])

    mc_, se_c, win_c = _stats(dc)
    mf_, se_f, win_f = _stats(df)
    print(f"\n=== LE CONTENU LINGUISTIQUE PAYE-T-IL ? (Mammouths, {len(seeds)} seeds apparies) ===")
    print(f"  FIABLE   : {np.mean(fia_m):.2f} +/- {np.std(fia_m):.2f}   (decode-et-agis declenche ~{np.mean(fires):.0f}x/run)")
    print(f"  BROUILLE : {np.mean(scr_m):.2f} +/- {np.std(scr_m):.2f}   (meme mouvement, contenu aleatoire)")
    print(f"  SOLO     : {np.mean(solo_m):.2f} +/- {np.std(solo_m):.2f}   (n'agit pas sur le signal)")
    print(f"  CONTRASTE CLE  FIABLE-BROUILLE = {mc_:+.2f} +/- {se_c:.2f} SE ; FIABLE>BROUILLE dans {win_c*100:.0f}%")
    print(f"  (secondaire)   FIABLE-SOLO     = {mf_:+.2f} +/- {se_f:.2f} SE ; {win_f*100:.0f}%")
    print("\n=== VERDICT ===")
    if surv <= 120:
        print("  -> TEST INVALIDE : substrat pas a survie longue (gate). A re-regler (energie/monde).")
    elif np.mean(fires) < 5:
        print(f"  -> INDETERMINE : le decode-et-agis ne s'est presque pas declenche ({np.mean(fires):.0f}x) -- apex trop rares.")
    elif mc_ > 2 * se_c and mc_ > 0 and win_c >= 0.7:
        print(f"  -> LE CONTENU DU LANGAGE PAYE, ROBUSTE : +{mc_:.1f} Mammouths vs BROUILLE (>2 SE, {win_c*100:.0f}%).")
        print("     Boucle fermee : a survie longue, le CONTENU referentiel (pas juste le guidage) confere un avantage.")
    elif mc_ > 0 and win_c >= 0.6:
        print(f"  -> tendance (contenu +{mc_:.1f}, {win_c*100:.0f}%) sous 2 SE : prometteur, a powerer.")
    else:
        print(f"  -> le CONTENU ne paye pas (FIABLE-BROUILLE {mc_:+.1f}, {win_c*100:.0f}%) : le gain eventuel vient")
        print(f"     du guidage spatial, pas du langage. (FIABLE-SOLO {mf_:+.1f} mesure guidage+contenu melanges.)")
    async_logger.stop()


if __name__ == "__main__":
    main()
