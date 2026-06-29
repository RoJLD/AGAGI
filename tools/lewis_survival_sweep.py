# tools/lewis_survival_sweep.py
"""tools/lewis_survival_sweep.py — EDR 093 : un premier barreau survivable en Lewis existe-t-il ?
Balaye forage_payoff (revenu/kill) et mesure la survie mediane des champions stoneage en Lewis a
letalite 0 (isole l'energie). PAS d'evolution, PAS de langage. Fonde sur le diagnostic post-090 :
mort par FAMINE (actions -10 x densite apex >> forage), pas letalite.
Pre-enregistrement : docs/superpowers/specs/2026-06-24-EDR093-Lewis-Survival-Sweep-design.md
"""
import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.harness import Harness, seed_at
from src.seed_ai import exp_stats as st
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.mamba_agent import MambaAgent
from tools.evolve_competence import _reproduce
from tools.robust_eval import _load_champions
from tools.lewis_critical import _setup_critical
from tools.lethality_curriculum import _disable_kuzu
from src.seed_ai.persistence import calculate_life_score

METAB = 0.25                       # sweet-spot energie 085 (fixe)
LEVELS = (3, 6, 12, 24, 48)        # forage_payoff balaye : de 085 vers x16
N_APEX = 12                        # densite d'apex (fixe, comme 088/090)
PREY_COUNT = 15                    # forage food non-rare (= defaut WorldConfig)
MAX_TICKS = 300
NUM_AGENTS = 24
GATE = 120.0                       # survie mediane minimale d'un barreau survivable (089/090)
CHEAP_MAX = 24                     # forage_payoff <= 24 (x8) = barreau "acceptable" ; 48 (x16) = trop cher
APEX_LEVELS = (12, 9, 6, 3, 0)     # N_APEX balaye : de la densite 093 (12) au Lewis vide (0)
METAB_LEVELS = (0.25, 0.1, 0.05, 0.025, 0.0)   # base_metabolism balaye : de 085 (0.25) vers 0
SURPRISE_LEVELS = (1.0, 0.5, 0.25, 0.0)   # ttc_surprise_scale : baseline 094 (1.0) -> brain_cost decouple (0.0)


def _cfg(forage_payoff, ttc_surprise_scale=None, trace_energy_sinks=False, base_metabolism=METAB,
         trace_forage=False, prey_speed_scale=1.0, scaffold_land=0.0, reach_oracle=False):
    cfg = WorldConfig()
    cfg.base_metabolism = float(base_metabolism)             # EDR101 : sweepable (defaut METAB=0.25)
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098
    cfg.trace_energy_sinks = bool(trace_energy_sinks)         # EDR099
    cfg.trace_forage = bool(trace_forage)                     # EDR105
    cfg.prey_speed_scale = float(prey_speed_scale)            # EDR106
    cfg.scaffold_land = float(scaffold_land)                  # EDR113
    cfg.reach_oracle = bool(reach_oracle)                     # EDR114
    return cfg


def _fresh_genome(n_hidden):
    """EDR110 : genome frais a capacite cachee n_hidden (num_nodes=167+n_hidden, I=59, O=108,
    W dense aleatoire x0.1). Reutilise la construction par defaut de MambaAgent ; seule la bande
    mediane [59, 59+n_hidden) grossit. La graine RNG doit etre posee par l'appelant (seed_at)
    pour le determinisme."""
    return MambaAgent(num_inputs=59, num_outputs=108, num_nodes=167 + n_hidden).genome


def _capacity_mc():
    """EDR110 : MutationConfig a CAPACITE FIGEE (num_nodes constant) pour que n_hidden soit la
    seule variable entre bras. Gele TOUTES les ops qui inserent des noeuds :
      - add_node_rate=0.0  : insertion directe d'un noeud (chemin standard)
      - meso_gate_rate=0.0 : add_meso_gated_unit insere 2 noeuds via np.insert ; sans ce gel,
                             num_nodes derive dans ~67% des seeds et crash le assert de _capacity_arm
      - meso_skip_rate=0.0 : add_meso_skip_connection (macro motif, ajoute une connexion) gele aussi
                             pour correspondre a l'intention du spec (seul le niveau connexion reste)
    Mutations conservees (identiques entre bras = bruit de recherche commun, pas un confound) :
      - mutation de poids (weight_init_std=2.0 comme EDR107)
      - add_connection (niveau connexion uniquement)
    NOTE : prune_rate=0.0 est INERTE (la fonction prune lit genome.mutation_genes[4], pas le config),
    mais prune ne change jamais num_nodes -> la garantie de capacite figee tient quand meme."""
    return MutationConfig(weight_init_std=2.0, add_node_rate=0.0, prune_rate=0.0,
                          meso_skip_rate=0.0, meso_gate_rate=0.0)


def _capacity_arm(cfg, mc, n_hidden, generations, num_agents, max_ticks, base_seed):
    """EDR110 : un bras = evolue la navigation a capacite cachee FIXEE n_hidden. Calque
    main_evolve_nav (EDR107) mais (a) seme best_ever depuis _fresh_genome(n_hidden) au lieu de
    _load_champions, (b) utilise mc a capacite figee, (c) assert num_nodes==167+n_hidden a chaque
    generation (garde-fou anti-derive). Renvoie un dict {n_hidden, num_nodes, traj, gen0, first,
    plateau, stats}. gen0 = p_reach de la 1re generation (capacite BRUTE) ; plateau = mediane des
    k dernieres (k=5 si gen>=10) ; first = mediane des k premieres."""
    expected_nodes = 167 + n_hidden
    seed_at(base_seed, 0)
    best_ever = [(0.0, _fresh_genome(n_hidden)) for _ in range(5)]
    traj, stats_hist = [], []
    for gen in range(1, generations + 1):
        seed_at(base_seed + gen, 0)
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents, mc)
        assert all(g.num_nodes == expected_nodes for g in genomes), (
            f"capacity drift: n_hidden={n_hidden} attendu {expected_nodes} noeuds")
        scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=max_ticks)
        # In-world reproduction (energy/MATE/HGT, world_1_stoneage) spawns offspring via
        # MambaAgent.mutate() (meso_*_rate left at 0.05 -> add_meso_gated_unit inserts 2 nodes) or
        # HGT crossover -> their num_nodes can drift off the seeded capacity. Exclude any off-capacity
        # genome from the best-ever ratchet so the seeded N stays the only variable across arms
        # (Phase 1 holds capacity FIXED; in-world-grown offspring are evaluated for p_reach but never
        # selected). This is what keeps the per-generation guard-rail assert from ever firing.
        scored = [(s, g) for (s, g) in scored if g.num_nodes == expected_nodes]
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        traj.append(p_reach)
        stats_hist.append(stats)
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    return {
        "n_hidden": n_hidden, "num_nodes": expected_nodes,
        "traj": traj, "gen0": float(traj[0]) if traj else 0.0,
        "first": float(np.median(traj[:k])) if traj else 0.0,
        "plateau": float(np.median(traj[-k:])) if traj else 0.0,
        "stats": stats_hist,
    }


def _landing_arm(cfg, generations, num_agents, max_ticks, base_seed):
    """EDR113 : un bras = evolue la navigation sous un cfg portant un scaffold_land donne. Calque
    main_evolve_nav (EDR107) : best_ever seedé par _load_champions, _reproduce (mc standard, add_node ON
    comme 107), _evolve_nav_gen, cliquet best-ever top-5. La SEULE variable entre bras est
    cfg.scaffold_land. Renvoie {scaffold_land, traj, gen0, first, plateau, stats}."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(base_seed, 0)
    champs = _load_champions()
    best_ever = [(0.0, g) for g in champs]
    traj, stats_hist = [], []
    for gen in range(1, generations + 1):
        seed_at(base_seed + gen, 0)
        champ_genomes = [g for (_s, g) in best_ever]
        genomes = _reproduce(champ_genomes, num_agents, mc)
        scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=max_ticks)
        best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
        traj.append(p_reach)
        stats_hist.append(stats)
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    return {
        "scaffold_land": float(cfg.scaffold_land), "traj": traj,
        "gen0": float(traj[0]) if traj else 0.0,
        "first": float(np.median(traj[:k])) if traj else 0.0,
        "plateau": float(np.median(traj[-k:])) if traj else 0.0,
        "stats": stats_hist,
    }


def _verdict_landing(arms):
    """EDR113 : verdict pre-enregistre sur l'effet de scaffold_land (recompense du pas final) sur le
    plateau de navigation. delta = plateau(max) - plateau(0) ; slope = pente du plateau vs scaffold_land
    (echelle lineaire 0-10). AFFORDANCE LEVE si delta>=0.10 ET slope>0. AFFORDANCE INERTE si
    abs(delta)<0.10 ET abs(slope)<0.01. AFFORDANCE AMBIGUE sinon (signal partiel/non-monotone)."""
    arms = sorted(arms, key=lambda a: a["scaffold_land"])
    plateaus = [a["plateau"] for a in arms]
    delta = plateaus[-1] - plateaus[0]
    x = [a["scaffold_land"] for a in arms]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms) >= 2 else 0.0
    if delta >= 0.10 and slope > 0:
        return "AFFORDANCE LEVE"
    if abs(delta) < 0.10 and abs(slope) < 0.01:
        return "AFFORDANCE INERTE"
    return "AFFORDANCE AMBIGUE"


def _report_landing(h, arms, generations, num_agents, max_ticks, _return):
    """Table ASCII (1 ligne/bras : scaffold_land, gen0, first, plateau, delta_vs_base) + pente +
    delta(max-base) + verdict pre-enregistre. Sauvegarde JSON. Tout ASCII (cp1252)."""
    verdict = _verdict_landing(arms)
    arms_sorted = sorted(arms, key=lambda a: a["scaffold_land"])
    base_plateau = arms_sorted[0]["plateau"]
    plateaus = [a["plateau"] for a in arms_sorted]
    x = [a["scaffold_land"] for a in arms_sorted]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms_sorted) >= 2 else 0.0
    print("\n=== EDR113 scaffold_land (recompense pas final) -> plafond navigation Lewis ===")
    print("  land | gen0  first plateau | delta_vs_base")
    for a in arms_sorted:
        print(f"  {a['scaffold_land']:4.1f} | {a['gen0']:.3f} {a['first']:.3f} "
              f"{a['plateau']:.3f} | {a['plateau'] - base_plateau:+.3f}")
    print(f"  pente plateau vs scaffold_land = {slope:+.4f}  delta(max-base) = "
          f"{plateaus[-1] - plateaus[0]:+.3f} (gate +0.10)")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "scaffold_land", "land_levels": [a["scaffold_land"] for a in arms_sorted],
            "generations": generations, "num_agents": num_agents, "max_ticks": max_ticks,
            "slope": slope, "delta": plateaus[-1] - plateaus[0], "verdict": verdict,
            "arms": arms_sorted})
    if _return:
        return {"verdict": verdict, "arms": arms_sorted, "slope": slope,
                "delta": plateaus[-1] - plateaus[0]}


def main_landing_nav(land_levels=(0.0, 2.0, 5.0, 10.0), generations=20, num_agents=24,
                     max_ticks=80, seed=113, _return=False):
    """EDR 113 : balaye scaffold_land (recompense du pas final) et evolue la navigation a chaque niveau
    (boucle evolve_nav EDR107, metab=0, Lewis vide d'apex, forage_payoff=3). Lit gen0 + plateau.
    Verdict AFFORDANCE LEVE / INERTE / AMBIGUE. Bras land=0 reproduit EDR107 (controle)."""
    with Harness(seed=seed, name="lewis_landing_nav", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR113 : scaffold_land nav, levels={land_levels}, gen={generations}, "
              f"pop={num_agents}, max_ticks={max_ticks}, seed={base}.")
        prog = h.progress(len(land_levels), label="niveaux scaffold_land")
        arms = []
        for land in land_levels:
            cfg = _cfg(3, base_metabolism=0.0, trace_forage=True, scaffold_land=land)
            arms.append(_landing_arm(cfg, generations, num_agents, max_ticks,
                                     base + int(round(land * 10))))
            prog.update()
        return _report_landing(h, arms, generations, num_agents, max_ticks, _return)


def _verdict_capacity(arms):
    """EDR110 : verdict pre-enregistre sur l'effet de la capacite cachee sur le plateau de navigation.
    delta = plateau(N_max) - plateau(N_min) ; slope = pente du plateau vs log2(N) (lisse l'echelle
    geometrique 5->80). CAPACITE LEVE si delta>=0.10 ET slope>0. CAPACITE INERTE si abs(delta)<0.10
    ET abs(slope)<0.05. CAPACITE AMBIGUE sinon (signal partiel/non-monotone)."""
    arms = sorted(arms, key=lambda a: a["n_hidden"])
    plateaus = [a["plateau"] for a in arms]
    delta = plateaus[-1] - plateaus[0]
    x = [float(np.log2(a["n_hidden"])) for a in arms]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms) >= 2 else 0.0
    if delta >= 0.10 and slope > 0:
        return "CAPACITE LEVE"
    if abs(delta) < 0.10 and abs(slope) < 0.05:
        return "CAPACITE INERTE"
    return "CAPACITE AMBIGUE"


def _report_capacity_nav(h, arms, generations, num_agents, max_ticks, _return):
    """Table ASCII (1 ligne/bras : n_hidden, num_nodes, gen0, first, plateau, delta_vs_base) +
    pente plateau vs log2(N) + delta(max-min) + verdict pre-enregistre. Sauvegarde JSON. Tout ASCII."""
    verdict = _verdict_capacity(arms)
    arms_sorted = sorted(arms, key=lambda a: a["n_hidden"])
    base_plateau = arms_sorted[0]["plateau"]
    plateaus = [a["plateau"] for a in arms_sorted]
    x = [float(np.log2(a["n_hidden"])) for a in arms_sorted]
    slope = float(np.polyfit(x, plateaus, 1)[0]) if len(arms_sorted) >= 2 else 0.0
    print("\n=== EDR110 capacite cachee -> plafond navigation Lewis ===")
    print("  n_hidden | num_nodes | gen0  first plateau | delta_vs_base")
    for a in arms_sorted:
        print(f"  {a['n_hidden']:8d} | {a['num_nodes']:9d} | {a['gen0']:.3f} {a['first']:.3f} "
              f"{a['plateau']:.3f} | {a['plateau'] - base_plateau:+.3f}")
    print(f"  pente plateau vs log2(N) = {slope:+.4f}  delta(max-min) = "
          f"{plateaus[-1] - plateaus[0]:+.3f} (gate +0.10)")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "n_hidden", "hidden_levels": [a["n_hidden"] for a in arms_sorted],
            "generations": generations, "num_agents": num_agents, "max_ticks": max_ticks,
            "slope_vs_log2N": slope, "delta": plateaus[-1] - plateaus[0], "verdict": verdict,
            "arms": arms_sorted})
    if _return:
        return {"verdict": verdict, "arms": arms_sorted, "slope": slope,
                "delta": plateaus[-1] - plateaus[0]}


def main_capacity_nav(hidden_levels=(5, 20, 40, 80), generations=20, num_agents=24,
                      max_ticks=80, seed=110, _return=False):
    """EDR 110 : seme une echelle de capacite cachee (n_hidden) figee et evolue la navigation a
    chaque palier (boucle evolve_nav EDR107, metab=0, Lewis vide d'apex, forage_payoff=3). Lit
    gen0 (capacite brute) + plateau evolue. Verdict CAPACITE LEVE / INERTE / AMBIGUE."""
    with Harness(seed=seed, name="lewis_capacity_nav", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR110 : capacite cachee nav, hidden={hidden_levels}, gen={generations}, "
              f"pop={num_agents}, max_ticks={max_ticks}, seed={base}.")
        mc = _capacity_mc()
        cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
        prog = h.progress(len(hidden_levels), label="paliers de capacite")
        arms = []
        for n_hidden in hidden_levels:
            arms.append(_capacity_arm(cfg, mc, n_hidden, generations, num_agents,
                                      max_ticks, base + n_hidden))
            prog.update()
        return _report_capacity_nav(h, arms, generations, num_agents, max_ticks, _return)


def _measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS,
                      max_ticks=MAX_TICKS, collect_surprise=False):
    """Mesure la survie des CHAMPIONS (repliques, pas d'evolution) en Lewis a letalite leurre_frac.
    Une ere par seed (appariement entre niveaux : meme seed -> meme monde initial). memory_retriever
    stoppe avant la boucle. Renvoie ages (pool), causes de mort (famine/combat), kills moyens/ere.
    Si collect_surprise : ajoute 'surprise' = stats de agent['model'].surprise_momentum par ere
    (mean_abs_finite, max_finite, frac_nonfinite) -> diagnostic du brain_cost (EDR098)."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)                  # graine fixe pour _load_champions (HoF vide -> fallback random)
    champs = _load_champions()
    ticks, famine, combat, kills, surprise = [], 0, 0, [], []
    for s in seeds:
        seed_at(s, 0)
        genomes = _reproduce(champs, num_agents, mc)
        env = Biosphere3D(cfg)
        _setup_critical(env, leurre_frac, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()   # vide le cache timing-dependant -> reproductible
        env.use_ref_head = False
        env.decode_act = False
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        ticks.extend(int(ag.get("age", 0)) for ag in pool)
        famine += sum(1 for ag in pool if ag.get("energy", 1.0) <= 0)
        combat += sum(1 for ag in pool if ag.get("hp", 1.0) <= 0 and ag.get("energy", 1.0) > 0)
        kills.append(float(np.mean([ag.get("mammoth_kills", 0) for ag in pool])) if pool else 0.0)
        if collect_surprise:
            surprise.append(_surprise_stats(pool))
    result = {"ticks": ticks, "famine": famine, "combat": combat, "kills": kills}
    if collect_surprise:
        result["surprise"] = surprise
    return result


def _measure_drain(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS):
    """Decompose le drain energetique par phase (brain/action/biologie/mouvement) a N_APEX=0. Lit
    agent['_e_phases'] (pose par les hooks trace_energy_sinks) sur le pool, normalise par l'age
    (energie/tick), moyenne sur les agents. cfg DOIT avoir trace_energy_sinks=True."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)
    champs = _load_champions()
    brain, action, biologie, mouvement = [], [], [], []
    bmetab, bterrain, bcarry, bautres = [], [], [], []
    for s in seeds:
        seed_at(s, 0)
        genomes = _reproduce(champs, num_agents, mc)
        env = Biosphere3D(cfg)
        _setup_critical(env, 0.0, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        env.use_ref_head = False
        env.decode_act = False
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        for ag in pool:
            ph = ag.get("_e_phases")
            if not ph:
                continue
            age = max(1, int(ag.get("age", 1)))
            brain.append(ph["brain"] / age)
            action.append(ph["action"] / age)
            biologie.append(ph["biologie"] / age)
            mouvement.append(ph["mouvement"] / age)
            bio = ag.get("_e_bio")
            if bio:
                bmetab.append(bio["metab"] / age)
                bterrain.append(bio["terrain"] / age)
                bcarry.append(bio["carry"] / age)
                bautres.append(bio["autres"] / age)
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    b, a_, bio, mv = mean(brain), mean(action), mean(biologie), mean(mouvement)
    return {"brain": b, "action": a_, "biologie": bio, "mouvement": mv,
            "net": b + a_ + bio + mv, "n_agents": len(brain),
            "bio_metab": mean(bmetab), "bio_terrain": mean(bterrain),
            "bio_carry": mean(bcarry), "bio_autres": mean(bautres)}


def _measure_forage(cfg, seeds, n_apex=0, num_agents=NUM_AGENTS, max_ticks=150):
    """EDR105 : decompose l'entonnoir de forage a N_APEX=0. Lit les compteurs _forage_* (poses par
    trace_forage) + preys_eaten + les buckets de pure depense _e_phases/_e_bio (trace_energy_sinks
    co-active) sur le pool, agrege par agent. cfg DOIT avoir trace_forage=True ET trace_energy_sinks=True.
    drain_t = cout structurel FORAGE-INDEPENDANT/tick (le revenu vit dans _e_bio['autres'], jamais somme
    ici) -> la comparaison income_t<drain_t est non circulaire (cf. spec EDR105)."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)
    champs = _load_champions()
    reached, captured_if_reached = [], []
    income_t, drain_t, captures, contacts, min_dists = [], [], [], [], []
    cap_lapin, cap_cerf, cap_sanglier = [], [], []
    for s in seeds:
        seed_at(s, 0)
        genomes = _reproduce(champs, num_agents, mc)
        env = Biosphere3D(cfg)
        _setup_critical(env, 0.0, n_apex=n_apex)
        env.config.target_prey_count = PREY_COUNT
        if hasattr(env, "memory_retriever"):
            env.memory_retriever.stop()
            env.memory_retriever.clear()
        env.use_ref_head = False
        env.decode_act = False
        for g in genomes:
            a = MambaAgent()
            a.from_genome(g)
            env.add_agent(a, energy=80.0)
        env.current_era = 1
        t = 0
        while env.agents and t < max_ticks:
            env.step()
            t += 1
        pool = list(env.agents) + list(getattr(env, "dead_agents", []))
        for ag in pool:
            ph = ag.get("_e_phases")
            bio = ag.get("_e_bio")
            if not ph or not bio:
                continue
            age = max(1, int(ag.get("age", 1)))
            md = float(ag.get("_forage_min_dist", 9999.0))
            inc = float(ag.get("_forage_income", 0.0))
            structural = (bio["metab"] + bio["terrain"] + bio["carry"]
                          + ph["brain"] + ph["action"] + ph["mouvement"])
            is_reached = md <= 0
            reached.append(1.0 if is_reached else 0.0)
            if is_reached:
                captured_if_reached.append(1.0 if int(ag.get("preys_eaten", 0)) >= 1 else 0.0)
            income_t.append(inc / age)
            drain_t.append(structural / age)
            captures.append(float(ag.get("preys_eaten", 0)))
            contacts.append(float(ag.get("_forage_contacts", 0)))
            min_dists.append(md)
            sp = ag.get("_forage_species", {})
            cap_lapin.append(float(sp.get("Lapin", 0)))
            cap_cerf.append(float(sp.get("Cerf", 0)))
            cap_sanglier.append(float(sp.get("Sanglier", 0)))
    med = lambda xs: float(np.median(xs)) if xs else 0.0
    mean = lambda xs: float(np.mean(xs)) if xs else 0.0
    return {"p_reach": mean(reached),
            "p_cap": mean(captured_if_reached),
            "income_t": med(income_t),
            "drain_t": med(drain_t),
            "mean_captures": mean(captures),
            "mean_contacts": mean(contacts),
            "mean_min_dist": mean(min_dists),
            "cap_lapin": mean(cap_lapin),
            "cap_cerf": mean(cap_cerf),
            "cap_sanglier": mean(cap_sanglier),
            "reached_raw": reached,
            "n_agents": len(income_t)}


def _surprise_stats(pool):
    """Stats de surprise_momentum sur le pool (read-only) : moyenne des |finies|, max fini, fraction
    non-finie (inf/nan -> detecte l'overflow brain_cost)."""
    vals = []
    for ag in pool:
        m = ag.get("model")
        try:
            vals.append(float(getattr(m, "surprise_momentum", np.nan)))
        except (TypeError, ValueError):
            vals.append(np.nan)
    arr = np.array(vals, dtype=float)
    finite = arr[np.isfinite(arr)]
    return {"mean_abs_finite": float(np.mean(np.abs(finite))) if finite.size else 0.0,
            "max_finite": float(np.max(np.abs(finite))) if finite.size else 0.0,
            "frac_nonfinite": float(np.mean(~np.isfinite(arr))) if arr.size else 0.0}


def _verdict(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau) -> 3 branches pre-enregistrees. Le 1er niveau qui franchit
    le gate determine le verdict : <=CHEAP_MAX -> barreau trouve ; sinon (seulement 48) -> trop cher ;
    aucun -> pas de rung (la depense est le mur)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "PAS DE RUNG"
    return "BARREAU TROUVE" if min(crossed) <= CHEAP_MAX else "BARREAU TROP CHER"


def _verdict_apex(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau de densite d'apex) -> 3 branches pre-enregistrees.
    Un N_APEX > 0 franchit le gate -> barreau trouve (densite reduite survivable) ; seul N_APEX=0
    franchit -> rung degenere (survie uniquement dans un Lewis vide) ; aucun -> mur intrinseque
    (le drain n'est pas l'environnement)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "MUR INTRINSEQUE"
    return "BARREAU TROUVE" if max(crossed) > 0 else "RUNG DEGENERE"


def _verdict_metab(levels, medians, gate=GATE):
    """Mappe (medianes de survie par niveau de base_metabolism) -> 3 branches pre-enregistrees. Un
    base_metabolism > 0 franchit le gate -> rescale suffit (mur supprimable par config) ; seul 0 franchit ->
    rescale extreme (metabolisme nul requis) ; aucun -> pas le metabolisme seul (la suppression ne sauve pas)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if not crossed:
        return "PAS LE METABOLISME SEUL"
    return "RESCALE SUFFIT" if max(crossed) > 0 else "RESCALE EXTREME"


def _verdict_surprise(levels, medians, frac_nonfinite, gate=GATE):
    """Mappe (medianes, fractions non-finies de surprise par niveau) -> 3 branches pre-enregistrees.
    Un ttc_surprise_scale franchit le gate -> TARIF=SURPRISE (le brain_cost surprise-amplifie est le mur) ;
    aucun ne franchit + une surprise non-finie (overflow) -> OVERFLOW=RACINE ; aucun + surprises finies ->
    PAS LE BRAIN_COST (le drain est ailleurs, ex. throw)."""
    crossed = [lv for lv, m in zip(levels, medians) if m > gate]
    if crossed:
        return "TARIF=SURPRISE"
    if any(f > 0 for f in frac_nonfinite):
        return "OVERFLOW=RACINE"
    return "PAS LE BRAIN_COST"


def _verdict_drain(phases):
    """Mappe la decomposition (brain/action/biologie/mouvement + net) -> 5 branches. La phase qui porte
    > 50% du drain net nomme le coupable ; aucune > 50% (ou net <= 0) -> drain diffus."""
    net = phases["net"]
    if net <= 0:
        return "DRAIN DIFFUS"
    keys = ("brain", "action", "biologie", "mouvement")
    shares = {k: phases[k] / net for k in keys}
    top = max(shares, key=shares.get)
    if shares[top] <= 0.5:
        return "DRAIN DIFFUS"
    return {"action": "TARIF=THROW", "biologie": "TARIF=BIOLOGIE",
            "brain": "TARIF=BRAIN", "mouvement": "TARIF=MOUVEMENT"}[top]


def _verdict_bio(agg):
    """Mappe les sous-postes biologie (bio_metab/terrain/carry/autres) -> 4 branches. Le sous-poste (parmi
    metab/terrain/carry) qui porte > 50% du drain biologie nomme le coupable ; aucun (ou bio_net<=0) ->
    drain bio diffus. 'autres' (gains) n'est pas une cible de tarif."""
    bio_net = agg["bio_metab"] + agg["bio_terrain"] + agg["bio_carry"] + agg["bio_autres"]
    if bio_net <= 0:
        return "DRAIN BIO DIFFUS"
    keys = ("bio_metab", "bio_terrain", "bio_carry")
    shares = {k: agg[k] / bio_net for k in keys}
    top = max(shares, key=shares.get)
    if shares[top] <= 0.5:
        return "DRAIN BIO DIFFUS"
    return {"bio_metab": "TARIF=METABOLISME", "bio_terrain": "TARIF=TERRAIN",
            "bio_carry": "TARIF=CARRY"}[top]


def _verdict_forage(agg):
    """Cascade 'premier etage casse' de l'entonnoir de forage (seuils geles, cf. spec EDR105). Evalue
    sur l'agg de metab=0. p_reach<0.5 -> APPROCHE (navigation) ; sinon p_cap<0.5 -> CAPTURE (atteint
    mais ne tue pas) ; sinon income_t<drain_t -> REVENU (tue mais ne couvre pas le cout structurel) ;
    sinon FORAGE SUFFISANT (l'entonnoir tient, le mur est ailleurs)."""
    if agg["p_reach"] < 0.5:
        return "GOULOT=APPROCHE"
    if agg["p_cap"] < 0.5:
        return "GOULOT=CAPTURE"
    if agg["income_t"] < agg["drain_t"]:
        return "GOULOT=REVENU"
    return "FORAGE SUFFISANT"


def _report(h, levels, groups, R, n_eval, _return, knob="forage_payoff", verdict_fn=_verdict):
    """Medianes par niveau + Jonckheere-Terpstra (tendance) + verdict + provenance.
    knob = nom du parametre balaye ; verdict_fn = mapping medianes->verdict. Si les groupes portent une
    cle 'surprise' (EDR098), ajoute une colonne surprise et appelle verdict_fn(levels, medians, frac_nf)."""
    medians = [float(np.median(g["ticks"])) if g["ticks"] else 0.0 for g in groups]
    jt = st.jonckheere_terpstra([g["ticks"] for g in groups])
    has_surprise = all("surprise" in g for g in groups)
    if has_surprise:
        frac_nf = [float(np.mean([s["frac_nonfinite"] for s in g["surprise"]])) if g["surprise"] else 0.0
                   for g in groups]
        verdict = verdict_fn(levels, medians, frac_nf)
    else:
        verdict = verdict_fn(levels, medians)
    table = {}
    print(f"\n=== EDR sweep {knob} : survie mediane (gate >{GATE:.0f}) ===")
    for lv, g, med in zip(levels, groups, medians):
        mk = float(np.mean(g["kills"])) if g["kills"] else 0.0
        n = len(g["ticks"])
        row = {"median": med, "famine": g["famine"], "combat": g["combat"], "mean_kills": mk, "n": n}
        line = (f"  {knob}={lv:<4} | survie mediane={med:6.1f} | famine={g['famine']:<4} "
                f"combat={g['combat']:<4} | kills/agent~{mk:.2f} | n={n}")
        if has_surprise:
            ms = float(np.mean([s["mean_abs_finite"] for s in g["surprise"]])) if g["surprise"] else 0.0
            fnf = float(np.mean([s["frac_nonfinite"] for s in g["surprise"]])) if g["surprise"] else 0.0
            row["mean_surprise"] = ms
            row["frac_nonfinite"] = fnf
            line += f" | surprise~{ms:.1f} nonfini={fnf:.2f}"
        table[lv] = row
        print(line)
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(croissance)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": knob, "levels": list(levels), "R": R, "n_eval": n_eval, "medians": medians,
            "jt": jt, "verdict": verdict, "table": {str(k): v for k, v in table.items()}})
    if _return:
        return {"levels": list(levels), "medians": medians, "jt": jt,
                "verdict": verdict, "table": table}


def main(levels=LEVELS, n_eval=8, R=4, seed=None, _return=False):
    with Harness(seed=seed, name="lewis_survival_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR093 : sweep forage_payoff={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux forage_payoff")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(lv), seeds))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return)


def main_apex(levels=APEX_LEVELS, n_eval=8, R=4, seed=None, _return=False):
    """EDR 094 : sweep N_APEX (densite d'apex) a forage_payoff=3 fixe, Lewis letalite 0."""
    with Harness(seed=seed, name="lewis_apex_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR094 : sweep N_APEX={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux N_APEX")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(3), seeds, n_apex=lv))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return, knob="N_APEX", verdict_fn=_verdict_apex)


def main_metab(levels=METAB_LEVELS, n_eval=8, R=4, seed=None, _return=False):
    """EDR 101 : sweep base_metabolism a N_APEX=0 (monde vide), forage_payoff=3 fixe, Lewis letalite 0.
    1ere intervention : teste si reduire le multiplicateur de metabolisme debloque la survie."""
    with Harness(seed=seed, name="lewis_metab_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR101 : sweep base_metabolism={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux base_metabolism")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(3, base_metabolism=lv), seeds, n_apex=0))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return, knob="base_metab", verdict_fn=_verdict_metab)


def main_surprise(levels=SURPRISE_LEVELS, n_eval=8, R=4, seed=None, _return=False):
    """EDR 098 : sweep ttc_surprise_scale a N_APEX=0 (monde vide), forage_payoff=3 fixe, Lewis letalite 0.
    Instrumente surprise_momentum -> teste si le brain_cost surprise-amplifie est le mur intrinseque."""
    with Harness(seed=seed, name="lewis_surprise_sweep", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR098 : sweep ttc_surprise_scale={levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(levels), label="niveaux ttc_surprise_scale")
        groups = []
        for lv in levels:
            groups.append(_measure_survival(_cfg(3, ttc_surprise_scale=lv), seeds, n_apex=0,
                                            collect_surprise=True))
            prog.update()
        return _report(h, levels, groups, R, n_eval, _return, knob="surprise_scale",
                       verdict_fn=_verdict_surprise)


def _report_drain(h, agg, R, n_eval, _return):
    """Table des 4 phases + sous-table biologie (EDR100) + verdicts + provenance. Tout ASCII (cp1252)."""
    verdict = _verdict_drain(agg)
    bio_verdict = _verdict_bio(agg)
    net = agg["net"]
    print(f"\n=== EDR099 decomposition drain a N_APEX=0 (energie/tick/agent) ===")
    for ph in ("brain", "action", "biologie", "mouvement"):
        pct = (100.0 * agg[ph] / net) if net else 0.0
        print(f"  {ph:<9} | {agg[ph]:7.2f}/tick | {pct:6.1f}% du net")
    print(f"  {'NET':<9} | {net:7.2f}/tick | n_agents={agg['n_agents']}")
    bio_net = agg["bio_metab"] + agg["bio_terrain"] + agg["bio_carry"] + agg["bio_autres"]
    print("=== EDR100 sous-decomposition de la phase biologie ===")
    for sp in ("bio_metab", "bio_terrain", "bio_carry", "bio_autres"):
        pct = (100.0 * agg[sp] / bio_net) if bio_net else 0.0
        print(f"  {sp:<11} | {agg[sp]:7.2f}/tick | {pct:6.1f}% du drain bio")
    print("=== VERDICT (pre-enregistre, >50%) ===")
    print(f"  -> phases : {verdict}")
    print(f"  -> biologie : {bio_verdict}")
    h.save({"phases": agg, "verdict": verdict, "bio_verdict": bio_verdict, "R": R, "n_eval": n_eval})
    if _return:
        return {"phases": agg, "verdict": verdict, "bio_verdict": bio_verdict, "R": R, "n_eval": n_eval}


def main_decompose(n_eval=8, R=4, seed=None, _return=False):
    """EDR 099 : decompose le drain intrinseque a N_APEX=0 (monde vide), forage_payoff=3, en 3 phases."""
    with Harness(seed=seed, name="lewis_drain_decompose", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR099 : decomposition drain N_APEX=0, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]
        agg = _measure_drain(_cfg(3, trace_energy_sinks=True), seeds, n_apex=0)
        return _report_drain(h, agg, R, n_eval, _return)


def _report_forage(h, aggs, R, n_eval, _return):
    """Table entonnoir (1 ligne/niveau de metab) + verdict (porte par metab=0) + provenance.
    Tout ASCII (cp1252). aggs = liste de (metab_level, agg)."""
    agg0 = next((a for lv, a in aggs if lv == 0.0), aggs[0][1])
    verdict = _verdict_forage(agg0)
    print("\n=== EDR105 entonnoir de forage a N_APEX=0 (verdict sur metab=0) ===")
    print("  metab | p_reach p_cap | income/t drain/t | captures contacts min_dist | n")
    for lv, a in aggs:
        print(f"  {lv:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['income_t']:8.3f} {a['drain_t']:7.3f} | "
              f"{a['mean_captures']:8.2f} {a['mean_contacts']:8.2f} {a['mean_min_dist']:8.2f} | "
              f"{a['n_agents']}")
    print("=== VERDICT (pre-enregistre, cascade premier etage casse) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "base_metab", "metab_levels": [lv for lv, _ in aggs], "R": R, "n_eval": n_eval,
            "verdict": verdict, "table": {str(lv): a for lv, a in aggs}})
    if _return:
        return {"verdict": verdict, "table": {lv: a for lv, a in aggs}, "R": R, "n_eval": n_eval}


def main_forage(metab_levels=(0.0, 0.25), n_eval=8, R=4, seed=None, _return=False):
    """EDR 105 : decompose l'entonnoir de forage (APPROCHE/CAPTURE/REVENU) a N_APEX=0, forage_payoff=3.
    Variable = base_metabolism ; metab=0 porte le verdict (acquisition isolee), 0.25 en contraste.
    Co-active trace_forage ET trace_energy_sinks (instruments inertes, pas des variables)."""
    with Harness(seed=seed, name="lewis_forage_funnel", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR105 : entonnoir forage metab={metab_levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(metab_levels), label="niveaux base_metab")
        aggs = []
        for lv in metab_levels:
            cfg = _cfg(3, base_metabolism=lv, trace_energy_sinks=True, trace_forage=True)
            aggs.append((lv, _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)))
            prog.update()
        return _report_forage(h, aggs, R, n_eval, _return)


def _p_reach_of_pool(pool):
    """EDR107 : fraction des agents du pool ayant atteint une cellule-proie (_forage_min_dist<=0).
    Pool vide -> 0.0. Necessite trace_forage=True (sinon cle absente -> defaut 9999 -> non atteint)."""
    if not pool:
        return 0.0
    reached = sum(1 for ag in pool if float(ag.get("_forage_min_dist", 9999.0)) <= 0)
    return reached / len(pool)


def _verdict_evolve_nav(traj):
    """EDR107 : verdict sur la trajectoire p_reach par generation. NAVIGATION EVOLUE si la mediane des
    k dernieres generations depasse celle des k premieres de >= 0.15 (ancre sur l'effet +0.05 d'EDR106) ;
    sinon SUBSTRAT BLOQUE. k=5 si >=10 generations, sinon max(1, n//2). traj vide -> SUBSTRAT BLOQUE."""
    if not traj:
        return "SUBSTRAT BLOQUE"
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    first = float(np.median(traj[:k]))
    last = float(np.median(traj[-k:]))
    return "NAVIGATION EVOLUE" if last >= first + 0.15 else "SUBSTRAT BLOQUE"


def _evolve_nav_gen(cfg, genomes, max_ticks=80):
    """EDR107 : lance UNE generation (ere fraiche, current_era=1 -> scaffold chaud) en Lewis vide d'apex.
    cfg DOIT avoir trace_forage=True. Renvoie (scored, p_reach, stats) : scored = top-5 (life_score, genome)
    pour le cliquet best-ever ; p_reach = _p_reach_of_pool(pool) ; stats = {ticks, eaten, p_reach}.
    Calque run_era d'evolve_competence + setup Lewis de _measure_forage."""
    env = Biosphere3D(cfg)
    _setup_critical(env, 0.0, n_apex=0)
    env.config.target_prey_count = PREY_COUNT
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
        env.memory_retriever.clear()
    env.use_ref_head = False
    env.decode_act = False
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    env.current_era = 1
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(getattr(env, "dead_agents", []))
    ranked = sorted(pool, key=calculate_life_score, reverse=True)
    scored = []
    for ag in ranked[:5]:
        g = ag["model"].genome if "model" in ag else ag.get("genome")
        if g is not None:
            scored.append((float(calculate_life_score(ag)), g))
    p_reach = _p_reach_of_pool(pool)
    eaten = int(sum(ag.get("preys_eaten", 0) for ag in pool))
    return scored, p_reach, {"ticks": t, "eaten": eaten, "p_reach": p_reach}


def _verdict_approach(aggs):
    """EDR106 : verdict porte par le niveau FIGE (prey_speed_scale=0.0). p_reach>=0.5 -> KINEMATIQUE
    (proies immobiles atteintes -> le mur etait la fuite, vitesse relative) ; sinon POLITIQUE (la
    navigation est le mur, meme sans fuite). aggs = liste (prey_speed_scale, agg)."""
    frozen = next((a for s, a in aggs if s == 0.0), None)
    if frozen is None:
        return "INDETERMINE"
    return "KINEMATIQUE" if frozen["p_reach"] >= 0.5 else "POLITIQUE"


def _report_approach(h, aggs, R, n_eval, _return):
    """Table APPROCHE (1 ligne/vitesse : p_reach, p_cap, captures totales + par espece) + Jonckheere-
    Terpstra (tendance p_reach quand la vitesse baisse) + verdict (porte par le niveau fige) + provenance.
    Tout ASCII (cp1252). aggs = liste de (prey_speed_scale, agg). reached_raw est retire avant sauvegarde."""
    verdict = _verdict_approach(aggs)
    jt = st.jonckheere_terpstra([a["reached_raw"] for _, a in aggs])
    print("\n=== EDR106 decomposition APPROCHE a N_APEX=0 (verdict sur prey_speed_scale=0) ===")
    print("  speed | p_reach p_cap | cap_tot cap_lapin cap_cerf cap_sanglier | min_dist | n")
    for s, a in aggs:
        print(f"  {s:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['mean_captures']:7.2f} {a['cap_lapin']:9.2f} {a['cap_cerf']:8.2f} "
              f"{a['cap_sanglier']:12.2f} | {a['mean_min_dist']:8.2f} | {a['n_agents']}")
    print(f"  Jonckheere-Terpstra z={jt['z']:.2f}, p(p_reach croit qd vitesse baisse)={jt['p_one_sided']:.3f}")
    print("=== VERDICT (pre-enregistre, porte par le niveau fige) ===")
    print(f"  -> {verdict}")
    slim = {str(s): {k: v for k, v in a.items() if k != "reached_raw"} for s, a in aggs}
    h.save({"knob": "prey_speed_scale", "speed_levels": [s for s, _ in aggs], "R": R, "n_eval": n_eval,
            "jt": jt, "verdict": verdict, "table": slim})
    if _return:
        return {"verdict": verdict, "jt": jt, "table": slim, "R": R, "n_eval": n_eval}


def main_approach(speed_levels=(1.0, 0.5, 0.25, 0.0), n_eval=8, R=4, seed=None, _return=False):
    """EDR 106 : decompose l'APPROCHE en balayant prey_speed_scale a N_APEX=0/metab=0, forage_payoff=3.
    Verdict KINEMATIQUE (p_reach>=0.5 au niveau fige) vs POLITIQUE. Reutilise l'entonnoir trace_forage
    (EDR105). Co-active trace_forage ET trace_energy_sinks (instruments inertes)."""
    with Harness(seed=seed, name="lewis_approach_kinematics", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR106 : approche prey_speed_scale={speed_levels}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]  # memes seeds/niveau
        prog = h.progress(len(speed_levels), label="niveaux prey_speed_scale")
        aggs = []
        for s in speed_levels:
            cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True,
                       prey_speed_scale=s)
            aggs.append((s, _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)))
            prog.update()
        return _report_approach(h, aggs, R, n_eval, _return)


def _verdict_reach(aggs):
    """EDR114 : verdict pre-enregistre porte par la cellule (oracle=True, speed=0.0). FERME si son
    p_reach>=0.90 (le monde permet d'atteindre une cible immobile -> mur = POLITIQUE/substrat) ;
    NE FERME PAS si <0.50 (mecanique-monde cassee) ; PARTIELLE sinon. aggs = liste (oracle, speed, agg)."""
    cell = next((a for o, s, a in aggs if o is True and s == 0.0), None)
    if cell is None:
        return "INDETERMINE"
    pr = cell["p_reach"]
    if pr >= 0.90:
        return "PRIMITIVE FERME"
    if pr < 0.50:
        return "PRIMITIVE NE FERME PAS"
    return "PRIMITIVE PARTIELLE"


def _report_reach(h, aggs, R, n_eval, _return):
    """Table 2x2 (1 ligne/cellule : oracle, speed, p_reach, p_cap, min_dist, n) + lecture cinematique
    (oracle figees vs mobiles) + verdict pre-enregistre + provenance. reached_raw retire avant save.
    Tout ASCII (cp1252). aggs = liste (oracle, speed, agg)."""
    verdict = _verdict_reach(aggs)
    print("\n=== EDR114 borne-sup primitive d'atteinte (verdict sur oracle=True, figees) ===")
    print("  oracle | speed | p_reach p_cap | min_dist | n")
    for o, s, a in aggs:
        print(f"  {str(bool(o)):<6} | {s:<5.3g} | {a['p_reach']:7.2f} {a['p_cap']:5.2f} | "
              f"{a['mean_min_dist']:8.2f} | {a['n_agents']}")
    orc_frozen = next((a['p_reach'] for o, s, a in aggs if o is True and s == 0.0), None)
    orc_moving = next((a['p_reach'] for o, s, a in aggs if o is True and s == 1.0), None)
    if orc_frozen is not None and orc_moving is not None:
        print(f"  cinematique (oracle) : figees={orc_frozen:.2f} vs mobiles={orc_moving:.2f} "
              f"(delta={orc_frozen - orc_moving:+.2f})")
    print("=== VERDICT (pre-enregistre, porte par oracle+figees) ===")
    print(f"  -> {verdict}")
    table = [{"oracle": bool(o), "speed": s, **{k: v for k, v in a.items() if k != "reached_raw"}}
             for o, s, a in aggs]
    h.save({"knob": "reach_oracle x prey_speed_scale", "R": R, "n_eval": n_eval,
            "verdict": verdict, "table": table})
    if _return:
        return {"verdict": verdict, "table": table, "R": R, "n_eval": n_eval}


def main_reach_oracle(speeds=(1.0, 0.0), n_eval=8, R=1, seed=114, _return=False):
    """EDR 114 : sonde borne-sup. Mesure p_reach sous l'oracle d'atteinte (override action) vs politique
    apprise, x {proies mobiles, figees}, a N_APEX=0/metab=0/forage_payoff=3, SANS evolution (replicas
    via _measure_forage). Verdict PRIMITIVE FERME/NE FERME PAS/PARTIELLE (porte par oracle+figees)."""
    with Harness(seed=seed, name="lewis_reach_oracle", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR114 : borne-sup oracle, speeds={speeds}, R={R}, n_eval={n_eval}, seed={base}.")
        seeds = [base + r * 1000 + i for r in range(R) for i in range(n_eval)]   # memes seeds/cellule
        prog = h.progress(2 * len(speeds), label="cellules (oracle x speed)")
        aggs = []
        for oracle in (False, True):
            for s in speeds:
                cfg = _cfg(3, base_metabolism=0.0, trace_energy_sinks=True, trace_forage=True,
                           prey_speed_scale=s, reach_oracle=oracle)
                aggs.append((oracle, s, _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)))
                prog.update()
        return _report_reach(h, aggs, R, n_eval, _return)


def _report_evolve_nav(h, traj, stats_hist, generations, num_agents, max_ticks, _return):
    """Trajectoire p_reach par generation + first/last medianes + pente lineaire + verdict.
    Tout ASCII (cp1252)."""
    verdict = _verdict_evolve_nav(traj)
    n = len(traj)
    k = 5 if n >= 10 else max(1, n // 2)
    first = float(np.median(traj[:k]))
    last = float(np.median(traj[-k:]))
    slope = float(np.polyfit(range(1, n + 1), traj, 1)[0]) if n >= 2 else 0.0
    print("\n=== EDR107 evolution navigation Lewis : trajectoire p_reach ===")
    print("  gen | p_reach | ticks eaten")
    for i, (p, sd) in enumerate(zip(traj, stats_hist), 1):
        print(f"  {i:3d} | {p:7.3f} | {sd['ticks']:5d} {sd['eaten']:5d}")
    print(f"  first-{k} median={first:.3f}  last-{k} median={last:.3f}  delta={last - first:+.3f} (gate +0.15)")
    print(f"  pente lineaire p_reach/gen = {slope:+.4f}")
    print("=== VERDICT (pre-enregistre) ===")
    print(f"  -> {verdict}")
    h.save({"knob": "generation", "generations": generations, "num_agents": num_agents,
            "max_ticks": max_ticks, "traj": traj, "first_median": first, "last_median": last,
            "slope": slope, "verdict": verdict, "stats": stats_hist})
    if _return:
        return {"verdict": verdict, "traj": traj, "first_median": first, "last_median": last,
                "slope": slope}


def main_evolve_nav(generations=20, num_agents=24, max_ticks=80, seed=None, _return=False):
    """EDR 107 : re-evolue la navigation EN Lewis (N_APEX=0, metab=0, forage_payoff=3) sur la fitness
    de prod calculate_life_score. Cliquet best-ever (top-5 global). Mesure p_reach par generation ->
    verdict NAVIGATION EVOLUE (last>=first+0.15) vs SUBSTRAT BLOQUE."""
    with Harness(seed=seed, name="lewis_evolve_nav", with_db=False) as h:
        base = h.seed
        _disable_kuzu()
        print(f"EDR107 : evolution navigation Lewis, gen={generations}, pop={num_agents}, "
              f"max_ticks={max_ticks}, seed={base}.")
        mc = MutationConfig(weight_init_std=2.0)
        seed_at(base, 0)
        champs = _load_champions()
        best_ever = [(0.0, g) for g in champs]
        cfg = _cfg(3, base_metabolism=0.0, trace_forage=True)
        traj, stats_hist = [], []
        prog = h.progress(generations, label="generations")
        for gen in range(1, generations + 1):
            seed_at(base + gen, 0)
            champ_genomes = [g for (_s, g) in best_ever]
            genomes = _reproduce(champ_genomes, num_agents, mc)
            scored, p_reach, stats = _evolve_nav_gen(cfg, genomes, max_ticks=max_ticks)
            best_ever = sorted(best_ever + scored, key=lambda sg: sg[0], reverse=True)[:5]
            traj.append(p_reach)
            stats_hist.append(stats)
            prog.update()
        return _report_evolve_nav(h, traj, stats_hist, generations, num_agents, max_ticks, _return)


if __name__ == "__main__":
    main()
