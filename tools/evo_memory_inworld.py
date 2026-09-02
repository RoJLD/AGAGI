"""EDR-EVO-003 — PONT IN-WORLD : la demande de mémoire d'EVO-002 survit-elle à l'embarquement ?

✅ RÉSOLU (cf. docs/EDR/EVO-003…) : l'évolution in-world n'encode PAS de cognition d'apex par type — la POLITIQUE
IGNORE causalement le canal de type (obs[4]). Mesuré par `measure_type_sensitivity` : perturber obs[4]=+1 vs −1 et
lire Δ du logit vers l'apex -> Δ_abs ≈ 0.000-0.006 sur 8 champions (2 objectifs × 4 seeds) vs **0.65 pour un
génome-lecteur synthétique** (contrôle positif de la sonde -> instrument PROUVÉ sensible). Pas de lecture -> pas
de discrimination -> pas de mémoire (sous-question caduque). Confirme S2-012 causalement, explique proxy→monde.
Il a fallu 5 sondes : les 4 comportementales (roaming/isolé/in-contexte × statique/mobile) n'avaient pas de
contrôle positif VALIDE (champions QUASI-STATIONNAIRES, moved_frac≈0.06 -> disc≈0 ininterprétable) ; la 5ᵉ
(inspection du logit + génome-lecteur) l'a enfin. Infra + substrat capables (EVO-002 8/8) : le verrou est l'OBJECTIF.

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
    # `memory_retriever` est un OBJET SÉPARÉ que Biosphere3D.__init__ démarre inconditionnellement (thread) :
    # neutraliser son start() aussi -> pas de leak de thread ni de bruit (get_memory_vector rend déjà [0]*5,
    # cache vide -> in_mem=0, donc PAS de contamination du substrat ; on tue juste le thread). Cf. INFRA-001.
    from src.graph_rag.memory_retriever import AsyncMemoryRetriever
    AsyncMemoryRetriever.start = lambda self: None


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
    # GARDE D'ARGUMENTS, EN TETE (2026-09-02, 6e elargissement du cliquet). Un argument degenere
    # est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte vide ou un horizon
    # nul rend 0.0 comme une MESURE, que l'aval lit comme « reste au plancher » / « n'emerge pas ».
    # Posee AVANT toute construction de monde -> le refus est instantane (teste : < 0.5 s).
    if int(n_trials) <= 0:
        raise ValueError(
            f"probe_memory_discrimination : argument degenere (n_trials={n_trials}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    p_mam = _approach_rate(genome, "Mammouth", mode, seed, n_trials)
    p_leu = _approach_rate(genome, "Leurre", mode, seed + 7, n_trials)
    return {"disc": p_mam - p_leu, "engage_mammouth": p_mam, "engage_leurre": p_leu}


def probe_navigation_incontext(genome, mode, seed, num_agents=24, ticks=120, zone=3, apex_speed=0.0):
    """MESURE DENSE IN-CONTEXTE (corrige le 3e mur : l'agent isolé fige). Un env NORMAL (`_setup_lewis`,
    N_APEX apex, contexte complet -> l'agent BOUGE). À chaque tick, pour chaque agent dans la zone d'un apex,
    on lit s'il s'APPROCHE (vers Mammouth = bon) ou s'ÉLOIGNE (fuit le Leurre = bon), mesuré vs la position de
    l'apex en DÉBUT de tick (intent de l'agent, isolé du mouvement de l'apex). disc = approche(Mam)−approche(Leu).

    apex_speed=0 : apex FIGÉS (cibles statiques -> teste la navigation PROACTIVE ; les champions réactifs y
    sont passifs). apex_speed>0 : les DEUX types s'approchent à mobilité IDENTIQUE (pas de confond mouvement)
    -> teste la discrimination RÉACTIVE (fuir/engager quand l'apex vient), la « dernière marche » pour un
    verdict propre. `moved_frac` = CONTRÔLE POSITIF de la sonde (agents non figés)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-02, 6e elargissement du cliquet). Un argument degenere
    # est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte vide ou un horizon
    # nul rend 0.0 comme une MESURE, que l'aval lit comme « reste au plancher » / « n'emerge pas ».
    # Posee AVANT toute construction de monde -> le refus est instantane (teste : < 0.5 s).
    if int(num_agents) <= 0 or int(ticks) <= 0:
        raise ValueError(
            f"probe_navigation_incontext : argument degenere (num_agents={num_agents}, ticks={ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    np.random.seed(seed)
    env = MemoryDemandBiosphere(_cfg())
    env.hide_on_approach = (mode != "visible")
    env.ablate_memory = (mode == "ablate")
    env.night_enabled = False
    env.benchmark_mode = True
    env.current_era = 10_000
    _setup_lewis(env, n_each=N_APEX)
    for t in ("Mammouth", "Leurre"):                 # mobilité IDENTIQUE des deux types -> pas de confond mouvement
        if t in env.config.preys:
            env.config.preys[t].moves_per_tick = apex_speed
    if LEURRE_DAMAGE is not None:
        env.config.preys["Leurre"].damage = float(LEURRE_DAMAGE)
    for _ in range(num_agents):
        a = MambaAgent()
        a.from_genome(genome)
        env.add_agent(a, energy=80.0)
    mam, leu, moved, ntot = [], [], 0, 0
    for _ in range(ticks):
        apex = [(p["x"], p["y"], p["type"]) for p in env.preys if p["type"] in _APEX_TYPEVAL]  # recalc/tick (apex mobiles)
        if not env.agents or not apex:
            break
        before = {}
        for ag in env.agents:
            d0, tgt = min(((abs(ag["x"] - ax) + abs(ag["y"] - ay), (ax, ay, ty)) for ax, ay, ty in apex),
                          key=lambda z: z[0])
            before[ag["id"]] = (d0, tgt, ag["x"], ag["y"])
        env.step()
        alive = {ag["id"]: ag for ag in env.agents}
        for aid, (d0, (ax, ay, ty), x0, y0) in before.items():
            if d0 > zone:
                continue
            ntot += 1
            ag = alive.get(aid)
            if ag is None:                           # mort en attaquant (riposte Leurre létal) -> a engagé
                approached = 1
            else:
                if ag["x"] != x0 or ag["y"] != y0:
                    moved += 1
                approached = 1 if (abs(ag["x"] - ax) + abs(ag["y"] - ay)) < d0 else 0
            (mam if ty == "Mammouth" else leu).append(approached)
    am = float(np.mean(mam)) if mam else float("nan")
    al = float(np.mean(leu)) if leu else float("nan")
    return {"disc": am - al, "approach_mam": am, "approach_leu": al,
            "n_mam": len(mam), "n_leu": len(leu), "moved_frac": moved / max(ntot, 1)}


def _dir_toward(agx, agy, apx, apy):
    """Index d'action (0=haut y−1, 1=bas y+1, 2=gauche x−1, 3=droite x+1, cf. world_1_stoneage:683-686)
    qui rapproche l'agent de l'apex, sur l'axe dominant."""
    dx, dy = apx - agx, apy - agy
    if abs(dx) >= abs(dy):
        return 3 if dx > 0 else 2
    return 1 if dy > 0 else 0


def probe_attack_logit(genome, mode, seed, num_agents=24, ticks=120, zone=2, apex_speed=0.0):
    """MESURE NON COMPORTEMENTALE (immunisée contre l'immobilité) : « attaquer » = marcher sur la case de
    l'apex (world:769), donc l'inclination à attaquer = le LOGIT de la direction VERS l'apex (`action =
    argmax(logits[:8])`, world:1291). On capture les `batch_logits` RÉELS (monkeypatch de
    `MambaBatchModel.forward`, sans double-avancer H) et on lit, pour chaque agent près d'un apex, le logit
    de la direction vers lui. disc = logit_vers(Mammouth) − logit_vers(Leurre) : >0 = la politique INCLINE à
    approcher le Mammouth plus que le Leurre (discrimination par type dans la POLITIQUE, même sans mouvement).
    `logit_std` = contrôle positif (les logits varient ; sinon dégénéré). mode : visible|memory|ablate."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-02, 6e elargissement du cliquet). Un argument degenere
    # est une erreur d'APPEL, pas un fait sur le monde : sans elle, une cohorte vide ou un horizon
    # nul rend 0.0 comme une MESURE, que l'aval lit comme « reste au plancher » / « n'emerge pas ».
    # Posee AVANT toute construction de monde -> le refus est instantane (teste : < 0.5 s).
    if int(num_agents) <= 0 or int(ticks) <= 0:
        raise ValueError(
            f"probe_attack_logit : argument degenere (num_agents={num_agents}, ticks={ticks}) -- aucune mesure possible ; "
            "ne pas confondre avec une mesure nulle OBSERVEE.")
    from src.agents.mamba_agent import MambaBatchModel
    np.random.seed(seed)
    env = MemoryDemandBiosphere(_cfg())
    env.hide_on_approach = (mode != "visible")
    env.ablate_memory = (mode == "ablate")
    env.night_enabled = False
    env.benchmark_mode = True
    env.current_era = 10_000
    _setup_lewis(env, n_each=N_APEX)
    for t in ("Mammouth", "Leurre"):
        if t in env.config.preys:
            env.config.preys[t].moves_per_tick = apex_speed
    if LEURRE_DAMAGE is not None:
        env.config.preys["Leurre"].damage = float(LEURRE_DAMAGE)
    for _ in range(num_agents):
        a = MambaAgent()
        a.from_genome(genome)
        env.add_agent(a, energy=80.0)
    cap, orig = {}, MambaBatchModel.forward

    def _patched(self, *a, **k):
        out = orig(self, *a, **k)
        cap["logits"] = np.asarray(out[0])
        return out

    MambaBatchModel.forward = _patched
    mam, leu = [], []
    try:
        for _ in range(ticks):
            if not env.agents:
                break
            apex = [(p["x"], p["y"], p["type"]) for p in env.preys if p["type"] in _APEX_TYPEVAL]
            if not apex:
                break
            snap = []                                    # (idx agent, dir vers apex, type) — ordre = env.agents au step
            for i, ag in enumerate(env.agents):
                d0, (ax, ay, ty) = min(((abs(ag["x"] - ax) + abs(ag["y"] - ay), (ax, ay, ty))
                                        for ax, ay, ty in apex), key=lambda z: z[0])
                if 1 <= d0 <= zone:
                    snap.append((i, _dir_toward(ag["x"], ag["y"], ax, ay), ty))
            cap.clear()
            env.step()
            L = cap.get("logits")
            if L is None:
                continue
            for i, dr, ty in snap:
                if i < len(L):
                    (mam if ty == "Mammouth" else leu).append(float(L[i][dr]))
    finally:
        MambaBatchModel.forward = orig
    am = float(np.mean(mam)) if mam else float("nan")
    al = float(np.mean(leu)) if leu else float("nan")
    allv = mam + leu
    return {"disc": am - al, "logit_mam": am, "logit_leu": al, "n_mam": len(mam), "n_leu": len(leu),
            "logit_std": float(np.std(allv)) if allv else 0.0}


def measure_type_sensitivity(genome, seed, num_agents=24, ticks=120, zone=2):
    """CONTRÔLE POSITIF + mesure CAUSALE définitive : la décision d'approche du champion DÉPEND-elle du canal
    type (obs[4]) ? In-contexte (obs réelles), pour chaque agent près d'un apex, on perturbe obs[4]=+1
    (Mammouth) vs −1 (Leurre) sur la MÊME obs, forward NON destructif (`recurrent_forward` sur le H courant),
    et on lit le logit de la direction VERS l'apex. Δ = logit(+1) − logit(−1). |Δ| gros = la politique LIT le
    type (et Δ>0 = incline vers le Mammouth) ; Δ≈0 (≪ std) = elle IGNORE le canal -> « pas de cognition de
    type » DÉFINITIF, avec instrument prouvé sensible (contrairement à un disc≈0 ambigu)."""
    from src.seed_ai.rl_evolution import recurrent_forward
    np.random.seed(seed)
    env = MemoryDemandBiosphere(_cfg())
    env.hide_on_approach = False                     # type visible (on teste la LECTURE du canal, pas la mémoire)
    env.night_enabled = False
    env.benchmark_mode = True
    env.current_era = 10_000
    _setup_lewis(env, n_each=N_APEX)
    for t in ("Mammouth", "Leurre"):
        if t in env.config.preys:
            env.config.preys[t].moves_per_tick = 0.0
    if LEURRE_DAMAGE is not None:
        env.config.preys["Leurre"].damage = float(LEURRE_DAMAGE)
    for _ in range(num_agents):
        a = MambaAgent()
        a.from_genome(genome)
        env.add_agent(a, energy=80.0)
    deltas, logits_all = [], []
    for _ in range(ticks):
        if not env.agents:
            break
        apex = [(p["x"], p["y"], p["type"]) for p in env.preys if p["type"] in _APEX_TYPEVAL]
        if not apex:
            break
        obs = np.asarray(env.get_batch_observations(), dtype=np.float32)
        for i, ag in enumerate(env.agents):
            d0, (ax, ay, ty) = min(((abs(ag["x"] - ax) + abs(ag["y"] - ay), (ax, ay, ty))
                                    for ax, ay, ty in apex), key=lambda z: z[0])
            if not (1 <= d0 <= zone) or i >= obs.shape[0]:
                continue
            dr = _dir_toward(ag["x"], ag["y"], ax, ay)
            m = ag["model"]
            H, Hh, Hp = m.H_prev, m.H_history, m.H_potentials
            oM = obs[i:i + 1].copy(); oM[0, _APEX_COL] = 1.0
            oL = obs[i:i + 1].copy(); oL[0, _APEX_COL] = -1.0
            pM = recurrent_forward(genome, oM, H, Hh, Hp)[0]
            pL = recurrent_forward(genome, oL, H, Hh, Hp)[0]
            deltas.append(float(pM[0, dr] - pL[0, dr]))
            logits_all.extend([float(pM[0, dr]), float(pL[0, dr])])
        env.step()
    md = float(np.mean(deltas)) if deltas else float("nan")
    return {"delta_mean": md, "delta_abs_mean": float(np.mean(np.abs(deltas))) if deltas else float("nan"),
            "logit_std": float(np.std(logits_all)) if logits_all else 0.0, "n": len(deltas)}


def measure_channel_saliency(genome, seed, channels, num_agents=24, ticks=80, n_out=8, decision=False):
    """EDR-EVO-004 — SAILLANCE par canal d'obs (généralise measure_type_sensitivity à tous les canaux) :
    de combien la DÉCISION (logits d'action [:n_out]) change-t-elle quand on met obs[k]=+1 vs −1 ? In-contexte
    (obs réelles), forward NON destructif (`recurrent_forward` sur le H courant). Renvoie {k: mean |Δlogits|}.

    ⚠️ `decision=True` -> renvoie {k: taux de changement d'ACTION} (l'argmax des logits bascule-t-il ?), la
    mesure FONCTIONNELLE. Nécessaire parce que l'amplitude SOUS-ESTIME la dépendance sur un substrat
    contractif : mesuré sur le banc proxy, un champion à acc 1.00 (donc lecteur obligé) a une saillance en
    amplitude NON supérieure à un génome frais — le SIGNE/rang porte l'information, pas l'amplitude (même
    piège que la réfutation de `sep(D)` dans EDR-EVO-002). L'action in-world étant `argmax(logits[:8])`
    (world_1_stoneage.py:1291), le taux de bascule d'argmax est la grandeur qui AGIT.
    Révèle quels canaux la politique évoluée LIT vs IGNORE. Contrôle positif intrinsèque : au moins un canal de
    SURVIE (direction proie 0-3, hp) doit s'allumer, sinon la politique/sonde est dégénérée."""
    from src.seed_ai.rl_evolution import recurrent_forward
    np.random.seed(seed)
    env = MemoryDemandBiosphere(_cfg())
    env.hide_on_approach = False
    env.night_enabled = False
    env.benchmark_mode = True
    env.current_era = 10_000
    _setup_lewis(env, n_each=N_APEX)
    for t in ("Mammouth", "Leurre"):
        if t in env.config.preys:
            env.config.preys[t].moves_per_tick = 0.0
    for _ in range(num_agents):
        a = MambaAgent()
        a.from_genome(genome)
        env.add_agent(a, energy=80.0)
    sal = {k: [] for k in channels}
    for _ in range(ticks):
        if not env.agents:
            break
        obs = np.asarray(env.get_batch_observations(), dtype=np.float32)
        for i, ag in enumerate(env.agents):
            if i >= obs.shape[0]:
                continue
            m = ag["model"]
            H, Hh, Hp = m.H_prev, m.H_history, m.H_potentials
            for k in channels:
                if k >= obs.shape[1]:
                    continue
                op = obs[i:i + 1].copy(); op[0, k] = 1.0
                om = obs[i:i + 1].copy(); om[0, k] = -1.0
                pp = recurrent_forward(genome, op, H, Hh, Hp)[0]
                pm = recurrent_forward(genome, om, H, Hh, Hp)[0]
                if decision:   # FONCTIONNEL : la perturbation change-t-elle l'ACTION choisie (argmax) ?
                    sal[k].append(float(int(np.argmax(pp[0, :n_out])) != int(np.argmax(pm[0, :n_out]))))
                else:
                    sal[k].append(float(np.mean(np.abs(pp[0, :n_out] - pm[0, :n_out]))))
        env.step()
    return {k: (float(np.mean(v)) if v else 0.0) for k, v in sal.items()}


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
