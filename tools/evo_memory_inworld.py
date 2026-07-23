"""EDR-EVO-003 — PONT IN-WORLD : la demande de mémoire d'EVO-002 survit-elle à l'embarquement ?

⚠️ STATUT (cf. docs/EDR/EVO-003…) : infra bâtie et VALIDÉE, mais le verdict mémoire in-world reste NON établi
(3 murs distincts). `MemoryDemandBiosphere` (occlusion dist-2 + ablation) crée une VRAIE demande de rappel ;
levier = STAKES (Leurre létal), pas corps insuffisant (-> plancher EDR-090). Contrôle positif PARTIEL trouvé
(discrimination VISIBLE s'évolue). ⚠️ La sonde dense isolée `_approach_rate` est INVALIDE : l'agent hors-contexte
NE BOUGE PAS (agent_moved=0.00) -> engage≈0 est un artefact d'agent figé, PAS une absence de navigation (contrôle
positif de la sonde ÉCHOUE). La mesure dense valide doit rester IN-CONTEXTE. Effort dédié — cf. le record.

[[EDR-EVO-002]] a montré HORS-MONDE qu'un objectif à rappel différé fait évoluer un substrat qui MAÎTRISE
la mémoire (1.00 sur 8/8). Question du pont : dans le VRAI monde (corps + économie d'énergie qui peuvent
court-circuiter la cognition, cf. le gap « proxy 9 / in-world 0 »), l'évolution construit-elle encore la
mémoire quand la survie l'exige ?

## L'angle (re-mesurer un null d'INSTRUMENT)
La SEULE demande de rappel différé in-world existante est `transient_apex` (EDR 058/062, world_1_stoneage.py:
464-472) : au contact d'un apex, son TYPE (Mammouth récompense / Leurre piège damage=50) est révélé UN tick
puis caché → il faut le RETENIR pour décider frapper vs fuir. EDR 058/062 ont conclu « la demande mord mais
ne fait PAS grandir l'archi » — mais mesuraient la TAILLE. Or EVO-002 montre que la mémoire se bâtit via les
forget-gates de nœuds EXISTANTS, PAS par la taille. Donc « pas de croissance » n'est peut-être qu'un null
d'instrument (mauvaise grandeur), comme sep dans EVO-002 ou le plancher d'AUDIT-001. On re-mesure par la
CAPACITÉ : la discrimination Mammouth/Leurre SOUS occultation du type (= mémoire requise).

## Design (cheap, sans toucher au cœur du monde)
- Évolution IN-WORLD auto-contenue (soupe FRAÎCHE aux dims du monde -> pas de contamination par le HoF
  global ; sélection par life_score en mémoire ; kuzu NEUTRALISÉ pour repro + vitesse, cf. INFRA-001).
- Deux bras, MÊME monde (Lewis : 5 Mammouth + 5 Leurre) — seule la demande change : `transient_apex` ON
  (mémoire requise) vs OFF (type toujours visible -> perception suffit).
- Mesure = discrimination du CHAMPION en benchmark (cohorte fixe, pas de repro qui dilue) : big_kills
  (attaque Mammouth = bon) vs leurre_hits (attaque Leurre = piège). disc = big_kills/(big_kills+leurre_hits).
- Unité de réplication = SEED. Contraste : le champion évolué SOUS demande (ON) discrimine-t-il mieux SOUS
  occultation (benchmark transient=ON) que le champion évolué SANS demande (OFF) ?

⚠️ Ce module est EXPLORATOIRE (cheap first, cf. décision utilisateur « sonde cheap puis recette complète »).
Le verdict formel + calibration d'instrument arrivent SI le signal existe. `transient_apex` = délai 1 tick,
contournable (re-révélation au re-contact) : demande FAIBLE assumée — un positif serait d'autant plus fort.

Usage : python -m tools.evo_memory_inworld   (env: EVO3_SEEDS, EVO3_ERAS, EVO3_TICKS, EVO3_AGENTS)
"""
import os
import statistics
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# HoF vide AVANT tout import de persistence -> init_primordial_soup rend une soupe FRAÎCHE (tabula rasa).
os.environ.setdefault("HOF_PATH", os.path.join(os.environ.get("TMPDIR", "/tmp"), "evo003_empty_hof.pkl"))


def _disable_kuzu():
    """Neutralise l'async_logger AVANT toute création de monde (lethality_curriculum.py:36-49, CLAUDE.md) :
    worker Kuzu jamais démarré (pas de contention/fuite), `in_mem`=zéros -> substrat 100 % reproductible,
    et le run passe de minutes à secondes. Idempotent. Corrige la contamination d'INFRA-001."""
    from src.graph_rag.async_logger import logger as al
    al._running = False
    al.start = lambda *a, **k: None
    al.emit = lambda *a, **k: None
    al.emit_sync = lambda *a, **k: False


_disable_kuzu()

import numpy as np  # noqa: E402

from src.environments.config import WorldConfig  # noqa: E402
from src.worlds.world_1_stoneage import Biosphere3D  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402
from main_biosphere import init_primordial_soup  # noqa: E402
from src.seed_ai.persistence import calculate_life_score  # noqa: E402
from src.seed_ai.mutation import apply_mutations, MutationConfig  # noqa: E402
from tools.lewis_world import _setup_lewis  # noqa: E402


# --- Leviers de la recette S2-005 in-world (Level B), réglés par la calibration de régime ci-dessous ---
BODY_METAB = 0.25          # cfg.base_metabolism (0.25 = sweet-spot survie EDR-085 ; ↑ = corps moins suffisant)
BODY_PAYOFF = 3.0          # cfg.forage_payoff  (3.0 = sweet-spot ; ↓ = foraging moins nourrissant -> pousse à chasser)
N_APEX = 5                 # Mammouth+Leurre spawnés (↑ = rencontres plus DENSES, sans affamer -> évite le plancher EDR-090)
LEURRE_DAMAGE = None       # None = défaut _setup_lewis (50) ; 100 = LÉTAL -> discrimination vitale (sur-pondère
                           # l'apex dans une survie sinon dominée par le foraging -> établit le contrôle positif)


_APEX_TYPEVAL = {"Mammouth": 1.0, "Ours": 0.5, "Leurre": -1.0}
_APEX_COL = 4                    # index de on_apex_type dans le vecteur d'obs (world_1_stoneage.py:611-612)


class MemoryDemandBiosphere(Biosphere3D):
    """Durcit la demande de rappel différé (Level B) SANS réécrire get_batch_observations : le type d'apex
    est révélé à DISTANCE 2 (Manhattan) et CACHÉ dans la fenêtre d'attaque (dist<=1) -> l'agent doit RETENIR
    le type vu de loin pour décider l'attaque de près (délai réel >= 1 tick, non contournable au contact,
    contrairement à `transient_apex` délai-0). `ablate_memory` : révèle un type ALÉATOIRE à dist 2 (mémoire
    portée DÉCORRÉLÉE) = le marqueur within-subject calibré (S2-005/MEM-001).
    hide_on_approach=False : type révélé à d<=2 EN CONTINU (pas de mémoire requise) = contrôle POSITIF."""
    ablate_memory = False
    hide_on_approach = True

    def get_batch_observations(self):
        obs = super().get_batch_observations()
        if getattr(obs, "size", 0) == 0 or not self.preys:
            return obs
        ax = np.array([a["x"] for a in self.agents])
        ay = np.array([a["y"] for a in self.agents])
        px = np.array([p["x"] for p in self.preys])
        py = np.array([p["y"] for p in self.preys])
        types = [p["type"] for p in self.preys]
        for i in range(len(self.agents)):
            d = np.abs(px - ax[i]) + np.abs(py - ay[i])
            ci = int(np.argmin(d))
            if types[ci] not in _APEX_TYPEVAL:
                obs[i, _APEX_COL] = 0.0
                continue
            val = np.random.choice([1.0, 0.5, -1.0]) if self.ablate_memory else _APEX_TYPEVAL[types[ci]]
            if self.hide_on_approach:            # MÉMOIRE : révélé à d==2, CACHÉ dès l'approche (d<=1) -> retenir
                obs[i, _APEX_COL] = val if d[ci] == 2 else 0.0
            else:                                # VISIBLE : révélé à d<=2 en continu -> perception suffit (contrôle +)
                obs[i, _APEX_COL] = val if d[ci] <= 2 else 0.0
        return obs


def _cfg():
    cfg = WorldConfig()
    cfg.base_metabolism = BODY_METAB
    cfg.forage_payoff = BODY_PAYOFF
    return cfg


def _fresh_soup(num_agents, cfg, add_node_rate):
    genomes, _ = init_primordial_soup(num_agents=num_agents, config=cfg, add_node_rate=add_node_rate)
    return genomes


def _run_era(genomes, memory_regime, cfg, max_ticks, era, ablate=False, benchmark=False):
    """Instancie un monde Lewis, y met les génomes, tourne <= max_ticks. Renvoie (env, pool).

    memory_regime=True  : MemoryDemandBiosphere (type révélé à dist 2, CACHÉ à l'attaque -> mémoire requise).
    memory_regime=False : Biosphere3D standard, type VISIBLE à l'attaque -> perception suffit (contrôle).
    ablate=True (memory_regime seul) : type révélé ALÉATOIRE = ablation within-subject de la mémoire portée."""
    if memory_regime:
        env = MemoryDemandBiosphere(cfg)
        env.ablate_memory = ablate
    else:
        env = Biosphere3D(cfg)
        env.transient_apex = False               # contrôle : type visible dans la fenêtre d'attaque
    _setup_lewis(env, n_each=N_APEX)
    if LEURRE_DAMAGE is not None:                 # stakes : Leurre létal -> discrimination VITALE (contrôle positif)
        from src.environments.config import PreyConfig
        env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=float(LEURRE_DAMAGE), moves_per_tick=0.2)
    if benchmark:
        env.benchmark_mode = True         # cohorte fixe : pas de repro qui dilue le champion (cf. g_fidelity)
        env.night_enabled = False
        env.current_era = 10_000
    else:
        env.current_era = era
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    pool = list(env.agents) + list(env.dead_agents)
    return env, pool


def evolve_inworld(memory_regime, seed, eras=15, max_ticks=120, num_agents=30, add_node_rate=0.4):
    """Évolution in-world auto-contenue : soupe fraîche -> ères -> sélection élitiste par life_score en
    mémoire -> reséminage (élites + enfants mutés). Renvoie le meilleur génome (cloné) + son score + nodes.
    Aucune écriture du HoF global (pas de contamination inter-sessions).
    memory_regime=True -> évolue SOUS demande de mémoire (type caché à l'attaque) ; False -> contrôle."""
    np.random.seed(seed)
    cfg = _cfg()
    mc = MutationConfig()
    mc.add_node_rate = add_node_rate
    genomes = _fresh_soup(num_agents, cfg, add_node_rate)
    n_elite = max(3, num_agents // 4)
    best_g, best_score = genomes[0].clone(), -1.0
    for era in range(1, eras + 1):
        _, pool = _run_era(genomes, memory_regime, cfg, max_ticks, era)
        pool.sort(key=calculate_life_score, reverse=True)
        if pool and calculate_life_score(pool[0]) > best_score:
            best_score = calculate_life_score(pool[0])
            best_g = pool[0]["model"].genome.clone()
        elites = [ag["model"].genome.clone() for ag in pool[:n_elite]]
        children = []
        while len(children) < num_agents - len(elites):
            parent = elites[np.random.randint(len(elites))]
            children.append(apply_mutations(parent, mc))
        genomes = elites + children
    return {"genome": best_g, "score": best_score, "nodes": best_g.num_nodes}


def benchmark_discrimination(genome, memory_regime, seed, num_agents=24, ticks=150, ablate=False):
    """Benchmark d'un champion (cohorte de clones, pas de repro) : discrimination Mammouth/Leurre SOUS le
    régime donné. Renvoie big_kills, leurre_hits, disc (=big/(big+leurre)), med_age. ablate=True (memory
    seul) : mémoire portée décorrélée (marqueur within-subject)."""
    np.random.seed(seed)
    cfg = _cfg()
    cohort = [genome.clone() for _ in range(num_agents)]
    env, pool = _run_era(cohort, memory_regime, cfg, ticks, era=10_000, ablate=ablate, benchmark=True)
    big = int(getattr(env, "big_kills", 0))
    leurre = int(getattr(env, "leurre_hits", 0))
    disc = big / (big + leurre) if (big + leurre) > 0 else float("nan")
    ages = [ag["age"] for ag in pool] or [0]
    return {"big_kills": big, "leurre_hits": leurre, "disc": disc, "med_age": float(statistics.median(ages)),
            "encounters": big + leurre}


def _approach_rate(genome, apex_type, mode, seed, n_trials=40, steps=12, sep=2):
    """MESURE DENSE (rencontre CONTRÔLÉE) de l'APPROCHE/FUITE : 1 agent au centre + 1 apex STATIQUE à
    distance `sep`. Les champions sont RÉACTIFS (n'attaquent que l'adjacent) -> on mesure la NAVIGATION :
    l'agent s'APPROCHE-t-il de l'apex (pour l'attaquer) ou le FUIT-il ? Renvoie la fraction d'essais où il
    a engagé (tué OU fini plus près qu'au départ OU mort en attaquant). Chaque essai = UNE décision.

    mode : 'visible' (type révélé à d<=2 en continu, mémoire inutile = contrôle POSITIF) |
           'memory'  (type révélé à d==2 puis caché -> il faut RETENIR) |
           'ablate'  (memory + type révélé ALÉATOIRE = mémoire portée décorrélée, marqueur causal)."""
    from src.environments.config import PreyConfig
    np.random.seed(seed)
    env = MemoryDemandBiosphere(_cfg())              # la sous-classe pilote la révélation dans les 3 modes
    env.hide_on_approach = (mode != "visible")
    env.ablate_memory = (mode == "ablate")
    env.night_enabled = False
    env.benchmark_mode = True
    dmg = float(LEURRE_DAMAGE) if LEURRE_DAMAGE is not None else 50.0
    env.config.preys["Leurre"] = PreyConfig(hp=100.0, damage=dmg, moves_per_tick=0.0)
    if "Mammouth" in env.config.preys:
        env.config.preys["Mammouth"].moves_per_tick = 0.0   # MÊME mobilité -> pas de confond mouvement
    cx = cy = env.size // 2
    apx = min(cx + sep, env.size - 1)
    engaged = 0
    for _ in range(n_trials):                        # env RÉUTILISÉ ; agent+apex reset/essai
        env.agents, env.dead_agents = [], []
        env.big_kills, env.leurre_hits = 0, 0
        a = MambaAgent()
        a.from_genome(genome)
        env.add_agent(a, x=cx, y=cy, energy=80.0)
        env.preys = [{"x": apx, "y": cy, "type": apex_type, "stunned": 0, "hp": 1.0}]
        for _ in range(steps):
            if not env.agents:
                break
            env.step()
        killed = int(env.big_kills) > 0 or int(env.leurre_hits) > 0
        if not env.agents:                           # mort en attaquant (riposte Leurre) -> a engagé
            engaged += 1
        elif killed:
            engaged += 1
        else:
            ag = env.agents[0]
            final = abs(ag["x"] - apx) + abs(ag["y"] - cy)
            engaged += 1 if final < sep else 0        # a fini PLUS PRÈS = s'est approché
    return engaged / n_trials


def probe_memory_discrimination(genome, mode, seed, n_trials=40):
    """disc = engage(Mammouth) − engage(Leurre) sur rencontres contrôlées. >0 = discrimine (approche le
    Mammouth, fuit le Leurre) ; ~0 = indiscriminé. Dense (n_trials décisions/type). mode : visible|memory|
    ablate (cf. _approach_rate)."""
    p_mam = _approach_rate(genome, "Mammouth", mode, seed, n_trials)
    p_leu = _approach_rate(genome, "Leurre", mode, seed + 7, n_trials)
    return {"disc": p_mam - p_leu, "engage_mammouth": p_mam, "engage_leurre": p_leu}


def run_contrast(seeds, eras=15, max_ticks=120, num_agents=30, bench_ticks=150):
    """EXPLORATOIRE : évolue ON vs OFF par seed, benchmarke chaque champion SOUS occultation (transient=ON,
    mémoire requise) ET sous type visible (transient=OFF, contrôle). Le champion ON discrimine-t-il mieux
    sous occultation que le champion OFF ? (n'affirme pas de verdict formel — cheap first)."""
    rows = []
    for s in seeds:
        rON = evolve_inworld(True, s, eras, max_ticks, num_agents)
        rOFF = evolve_inworld(False, s, eras, max_ticks, num_agents)
        # benchmark : occultation (mémoire requise) et type-visible (perception suffit)
        on_occ = benchmark_discrimination(rON["genome"], True, 1000 + s, ticks=bench_ticks)
        on_vis = benchmark_discrimination(rON["genome"], False, 1000 + s, ticks=bench_ticks)
        off_occ = benchmark_discrimination(rOFF["genome"], True, 1000 + s, ticks=bench_ticks)
        off_vis = benchmark_discrimination(rOFF["genome"], False, 1000 + s, ticks=bench_ticks)
        rows.append({"seed": s, "score_on": rON["score"], "score_off": rOFF["score"],
                     "nodes_on": rON["nodes"], "nodes_off": rOFF["nodes"],
                     "on_occ": on_occ, "on_vis": on_vis, "off_occ": off_occ, "off_vis": off_vis})
        print(f"  seed {s}: EVOL-ON score={rON['score']:.0f} N={rON['nodes']} | EVOL-OFF score={rOFF['score']:.0f} N={rOFF['nodes']}")
        print(f"    champion ON : occ disc={on_occ['disc']:.2f} ({on_occ['big_kills']}/{on_occ['leurre_hits']}, enc={on_occ['encounters']}) | vis disc={on_vis['disc']:.2f} ({on_vis['big_kills']}/{on_vis['leurre_hits']})")
        print(f"    champion OFF: occ disc={off_occ['disc']:.2f} ({off_occ['big_kills']}/{off_occ['leurre_hits']}, enc={off_occ['encounters']}) | vis disc={off_vis['disc']:.2f} ({off_vis['big_kills']}/{off_vis['leurre_hits']})")
    return rows


def main():
    seeds = list(range(int(os.environ.get("EVO3_SEEDS", "3"))))
    eras = int(os.environ.get("EVO3_ERAS", "15"))
    ticks = int(os.environ.get("EVO3_TICKS", "120"))
    agents = int(os.environ.get("EVO3_AGENTS", "30"))
    print(f"EVO-003a (EXPLORATOIRE) : évolution in-world ON vs OFF | {len(seeds)} seeds x {eras} ères x {ticks} ticks x {agents} agents")
    print("Question : le champion évolué SOUS occultation (transient=ON) discrimine-t-il Mammouth/Leurre mieux que le champion évolué SANS ?")
    rows = run_contrast(seeds, eras, ticks, agents)
    occ_on = [r["on_occ"]["disc"] for r in rows if not _isnan(r["on_occ"]["disc"])]
    occ_off = [r["off_occ"]["disc"] for r in rows if not _isnan(r["off_occ"]["disc"])]
    print("\n=== SYNTHÈSE EXPLORATOIRE (discrimination sous occultation, mémoire requise) ===")
    print(f"  champion ÉVOLUÉ-ON  : disc méd={_med(occ_on)} (n={len(occ_on)})")
    print(f"  champion ÉVOLUÉ-OFF : disc méd={_med(occ_off)} (n={len(occ_off)})")
    print("  (si ON > OFF nettement -> l'évolution sous demande a bâti de la mémoire in-world -> formaliser verdict+calibration.)")


def _isnan(x):
    return x != x


def _med(xs):
    return f"{statistics.median(xs):.2f}" if xs else "n/a"


if __name__ == "__main__":
    main()
