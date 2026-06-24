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

METAB = 0.25                       # sweet-spot energie 085 (fixe)
LEVELS = (3, 6, 12, 24, 48)        # forage_payoff balaye : de 085 vers x16
N_APEX = 12                        # densite d'apex (fixe, comme 088/090)
PREY_COUNT = 15                    # forage food non-rare (= defaut WorldConfig)
MAX_TICKS = 300
NUM_AGENTS = 24
GATE = 120.0                       # survie mediane minimale d'un barreau survivable (089/090)
CHEAP_MAX = 24                     # forage_payoff <= 24 (x8) = barreau "acceptable" ; 48 (x16) = trop cher
APEX_LEVELS = (12, 9, 6, 3, 0)     # N_APEX balaye : de la densite 093 (12) au Lewis vide (0)
SURPRISE_LEVELS = (1.0, 0.5, 0.25, 0.0)   # ttc_surprise_scale : baseline 094 (1.0) -> brain_cost decouple (0.0)


def _cfg(forage_payoff, ttc_surprise_scale=None):
    cfg = WorldConfig()
    cfg.base_metabolism = METAB
    cfg.forage_payoff = float(forage_payoff)
    cfg.max_population = 150        # defensif (PR #29) ; jamais atteint ici
    if ttc_surprise_scale is not None:
        cfg.ttc_surprise_scale = float(ttc_surprise_scale)   # EDR098 ; sinon defaut config (1.0)
    return cfg


def _measure_survival(cfg, seeds, leurre_frac=0.0, n_apex=N_APEX, num_agents=NUM_AGENTS, max_ticks=MAX_TICKS):
    """Mesure la survie des CHAMPIONS (repliques, pas d'evolution) en Lewis a letalite leurre_frac.
    Une ere par seed (appariement entre niveaux : meme seed -> meme monde initial). memory_retriever
    stoppe avant la boucle. Renvoie ages (pool), causes de mort (famine/combat), kills moyens/ere."""
    mc = MutationConfig(weight_init_std=2.0)
    seed_at(0, 0)                  # graine fixe pour _load_champions (HoF vide -> fallback random)
    champs = _load_champions()
    ticks, famine, combat, kills = [], 0, 0, []
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
    return {"ticks": ticks, "famine": famine, "combat": combat, "kills": kills}


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


def _report(h, levels, groups, R, n_eval, _return, knob="forage_payoff", verdict_fn=_verdict):
    """Medianes par niveau + Jonckheere-Terpstra (tendance) + verdict + provenance.
    knob = nom du parametre balaye (impression/provenance) ; verdict_fn = mapping medianes->verdict."""
    medians = [float(np.median(g["ticks"])) if g["ticks"] else 0.0 for g in groups]
    jt = st.jonckheere_terpstra([g["ticks"] for g in groups])
    verdict = verdict_fn(levels, medians)
    table = {}
    print(f"\n=== EDR sweep {knob} : survie mediane (gate >{GATE:.0f}) ===")
    for lv, g, med in zip(levels, groups, medians):
        mk = float(np.mean(g["kills"])) if g["kills"] else 0.0
        n = len(g["ticks"])
        table[lv] = {"median": med, "famine": g["famine"], "combat": g["combat"],
                     "mean_kills": mk, "n": n}
        print(f"  {knob}={lv:<3} | survie mediane={med:6.1f} | famine={g['famine']:<4} "
              f"combat={g['combat']:<4} | kills/agent~{mk:.2f} | n={n}")
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


if __name__ == "__main__":
    main()
