"""tools/lewis_critical.py — EDR 088 : le CONTENU paye-t-il quand la distinction devient décisive ?

Sweep dose-réponse de la fraction de Leurres-pièges (le levier explicite d'EDR 087). Réutilise les
briques feuilles de relang_sweet/referential_head MAIS écrira son propre moteur 3-bras (Task 5) pour
NE PAS altérer l'artefact 087. Pré-enregistrement :
docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md
"""
import numpy as np

from src.environments.config import WorldConfig, PreyConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.persistence import calculate_life_score
from src.seed_ai.referential_head import new_head, train_population
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions

METAB, PAYOFF = 0.25, 3.0          # sweet spot (EDR 085)
LEURRE_FRACS = (0.33, 0.50, 0.67, 0.83)
N_APEX = 12


def _sweet_cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = PAYOFF
    return cfg


def _setup_critical(env, leurre_frac, n_apex=N_APEX):
    """Monde de Lewis a criticalite reglable : n_apex apex au total, dont round(leurre_frac*n_apex)
    Leurres-pieges ; le reste reparti Mammouth/Ours (positifs). Nuit OFF (correctif audit 086).
    Quand n_apex=0, retire aussi Mammouth/Ours de config.preys : le respawn aleatoire du monde
    ne peut plus produire d'apex (hp<50) -> mammoth_kills reste nul (cablage n_apex=0)."""
    env.config.active_exp_variable = "LANGUAGE"
    env.hear_radius = 3
    env.night_enabled = False
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)
    env.config.preys["Ours"] = PreyConfig(hp=60.0, damage=30.0, moves_per_tick=0.3)
    # Purger les apex spawned by __init__ pour avoir un controle exact du ratio
    env.preys = [p for p in env.preys if p.get("type") not in ("Mammouth", "Ours", "Leurre")]
    n_leurre = int(round(leurre_frac * n_apex))
    n_pos = n_apex - n_leurre
    positifs = [("Mammouth" if i % 2 == 0 else "Ours") for i in range(n_pos)]  # alterne les 2 food
    for ref in positifs:
        env._spawn_prey_instance(ref)
    for _ in range(n_leurre):
        env._spawn_prey_instance("Leurre")
    if n_apex == 0:
        # Retire Mammouth/Ours de config.preys -> respawn aleatoire ne produira que des
        # petites proies (hp=1.0 < 50) -> chemin mammoth_kills inaccessible -> kills=0.
        env.config.preys.pop("Mammouth", None)
        env.config.preys.pop("Ours", None)


def _run_arm(cfg, genomes, leurre_frac, use_head, decode_act, scramble, heads,
             world_seed, max_ticks=300):
    """Un bras apparié : seed la frontière (monde identique entre bras du même world_seed), construit
    le monde critique, ajoute les agents (têtes optionnelles), simule, renvoie la métrique NETTE."""
    seed_at(world_seed, 0)                       # APPARIEMENT (D1) : même monde entre bras
    env = Biosphere3D(cfg)
    _setup_critical(env, leurre_frac)
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
    kills = int(sum(ag.get("mammoth_kills", 0) for ag in pool))
    hits = int(getattr(env, "leurre_hits", 0))
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    return {"net": kills - hits, "kills": kills, "leurre_hits": hits, "ticks": t,
            "fires": int(getattr(env, "decode_act_fires", 0))}


def main(num_agents=24, seeds=range(12), levels=LEURRE_FRACS, max_ticks=300, seed=None):
    with Harness(seed=seed, name="lewis_critical", with_db=False) as h:
        base = h.seed
        cfg = _sweet_cfg()
        mc = MutationConfig(weight_init_std=2.0)
        seeds = list(seeds)
        champions = _load_champions()            # substrat HoF (cohérent 087 ; pas de ré-évolution)
        print(f"EDR088 sweep criticalite : seed={base}, niveaux={levels}, {len(seeds)} seeds apparies.")

        table = {}
        prog = h.progress(len(levels) * len(seeds) * 3, label="sweep FIABLE/BROUILLE/SOLO")
        for lf in levels:
            dc, fia, scr, solo, fires = [], [], [], [], []
            for s in seeds:
                ws = base + int(round(lf * 1000)) * 100 + s    # frontière disjointe par (niveau, seed)
                seed_at(ws, 0)
                genomes = _reproduce(champions, num_agents, mc)
                rng = np.random.RandomState(s)
                heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(len(genomes))]
                train_population(heads, steps=5000, seed=s)
                rf = _run_arm(cfg, genomes, lf, True, True, False, heads, ws, max_ticks); prog.update()
                rs = _run_arm(cfg, genomes, lf, True, True, True, heads, ws, max_ticks); prog.update()
                ro = _run_arm(cfg, genomes, lf, True, False, False, heads, ws, max_ticks); prog.update()
                dc.append(rf["net"] - rs["net"])               # CONTENU : FIABLE - BROUILLE (net)
                fia.append(rf["net"]); scr.append(rs["net"]); solo.append(ro["net"])
                fires.append(rf["fires"])
            table[lf] = {"dc": dc, "fia": fia, "scr": scr, "solo": solo, "fires": fires,
                         "summary": st.paired_summary(dc)}
            sm = table[lf]["summary"]
            print(f"  Leurre={lf:.2f} : FIABLE-BROUILLE(net) = {sm['mean']:+.2f} +/- {sm['se']:.2f} SE "
                  f"(win {sm['win_rate']*100:.0f}%, Wilcoxon p={sm['wilcoxon_p']:.3f}, fires~{np.mean(fires):.0f})")

        groups = [table[lf]["dc"] for lf in levels]
        jt = st.jonckheere_terpstra(groups)
        slope = st.ols_slope([lf for lf in levels for _ in table[lf]["dc"]],
                             [d for lf in levels for d in table[lf]["dc"]])
        print(f"\n=== TENDANCE (le contenu paye-t-il PLUS quand la distinction devient critique ?) ===")
        print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f} ; pente OLS={slope:+.3f}")
        hi = table[levels[-1]]["summary"]
        hi_lo, hi_hi = st.bootstrap_ci(table[levels[-1]]["dc"], np.mean, seed=base)  # IC95 apparié, niveau haut
        print(f"  niveau haut {levels[-1]:.2f} : FIABLE-BROUILLE IC95 bootstrap = [{hi_lo:+.2f}, {hi_hi:+.2f}]")
        print("=== VERDICT (pre-enregistre) ===")
        if jt["p_one_sided"] < 0.05 and hi["mean"] > 0 and hi["wilcoxon_p"] < 0.05 and hi_lo > 0:
            print(f"  -> ARC 4 CLOS : le CONTENU paye quand la distinction est decisive (tendance +, "
                  f"FIABLE-BROUILLE={hi['mean']:+.1f} a {levels[-1]:.2f} pieges, p={hi['wilcoxon_p']:.3f}, "
                  f"IC_inf={hi_lo:+.2f}).")
        elif jt["p_one_sided"] >= 0.05 and abs(hi["mean"]) < hi["se"]:
            print(f"  -> NEGATIF PROFOND : pas de tendance, FIABLE~BROUILLE meme a {levels[-1]:.2f} pieges.")
        else:
            print(f"  -> PARTIEL/GATE : tendance/effet sous-puissant ou niveaux VOID. Reporter + re-regler.")
        h.save({"levels": list(levels), "seeds": seeds, "jt": jt, "slope": slope,
                "high_level_ci": [hi_lo, hi_hi],
                "table": {f"{lf:.2f}": table[lf] for lf in levels}})


if __name__ == "__main__":
    main()
