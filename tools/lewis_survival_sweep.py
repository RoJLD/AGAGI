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
         trace_forage=False, prey_speed_scale=1.0):
    cfg = WorldConfig()
    cfg.base_metabolism = float(base_metabolism)             # EDR101 : sweepable (defaut METAB=0.25)
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098
    cfg.trace_energy_sinks = bool(trace_energy_sinks)         # EDR099
    cfg.trace_forage = bool(trace_forage)                     # EDR105
    cfg.prey_speed_scale = float(prey_speed_scale)            # EDR106
    return cfg


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


if __name__ == "__main__":
    main()
