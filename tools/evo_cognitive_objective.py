"""EDR-EVO-005 — La fitness in-world est-elle un NON-LEVIER, ou n'a-t-elle jamais été mesurée
de façon FIABLE par agent ?

Le dépôt porte deux verdicts incompatibles sur le même levier :
  * EDR-056 (fitness alignée sur le langage -> BACKFIRE) et EDR-WLD-002 (les termes de life_score sont
    INERTES pour la sélection) concluent « muter la fitness ne débloque rien, le verrou est en amont
    (crédit/comportement) » ;
  * l'arc EDR-EVO-001→004 conclut l'inverse : le verrou est l'OBJECTIF — l'évolution bâtit un lecteur
    PARFAIT dès qu'un objectif l'exige (EVO-002, 8/8 seeds), et ne lit RIEN quand la survie seule note
    (EVO-004, saillance au plancher sur tous les canaux).

Les deux échecs historiques partagent un CONFOND que ni l'un ni l'autre n'a contrôlé : **le comportement
noté était RARE**. Craft 1.4 % des agents (WLD-002), autels 0 %, distinction référentielle sur des comptes
de 1-2 (EDR-056, qui l'écrit lui-même : « on ne peut pas récompenser un trait qu'on ne mesure pas de façon
fiable PAR AGENT »). Aucun n'a testé un terme de fitness sur un comportement qui se produit À CHAQUE TICK.

Ce banc remplit cette cellule vide, en transplantant la tâche du proxy EVO-002 DANS le monde :
  * un signal i.i.d. ±1 est injecté dans le canal d'obs 5 — un `np.zeros(N)` CÂBLÉ EN DUR
    (world_1_stoneage.py:610) donc à information NULLE par construction (vérifié : 0.0 exact) ;
  * la réponse exigée est une ACTION du monde (Est si +1, Ouest si −1 ; world_1_stoneage.py:1559-1562),
    donc la grandeur notée est exactement celle qui AGIT — et exactement la DV d'EVO-004 ;
  * le score est mesuré à CHAQUE TICK (~120 échantillons/agent vs 1-2 dans EDR-056) et lissé par
    pseudo-comptes vers ZÉRO -> le bruit à faible compte ne peut PAS gagner la sélection. C'est la
    traduction quantitative de la leçon d'EDR-056 (cf. `measure_cognitive_rate` pour la raison, mesurée,
    du lissage vers 0 plutôt que vers la chance).

⚠️ Ce banc teste l'ÉVOLUTION (sélection sur les génomes), pas le CRÉDIT. Le fil S2 a établi in-world que
le crédit (REINFORCE intra-vie) n'apprend PAS la carte signal→action, à froid comme sous curriculum
([[EDR-S2-010]], [[EDR-S2-011]]) — mais AUCUNE de ses sondes n'appelle `apply_mutations`. La cellule
« in-world × évolution × objectif cognitif fiablement mesuré » est vide, et c'est celle-ci ; S2-011 la
nomme d'ailleurs dans son prochain pas (« Alt : warm-start par évolution courte in-world »).

Plan FACTORIEL à deux facteurs (cf. `ARMS`) : le POIDS du terme cognitif × l'ATTEIGNABILITÉ dans le
substrat. Le second facteur est né du pré-vol : le contrôle positif n'a fonctionné qu'en `reflex=True`
(cf. `synthetic_reader`), donc bâtir un lecteur réactif exige une CONJONCTION — câbler le canal ET
dé-mémoriser la sortie. Tout le reste — substrat, opérateur de mutation, monde, sélection épisodique,
pression de survie — est tenu CONSTANT.

⚠️ `calculate_life_score` (fitness de PROD, partagée par toutes les sessions //) n'est JAMAIS mutée :
la pondération se fait dans une fonction LOCALE (leçon de blast-radius d'EDR-WLD-002).
"""
import os
import statistics
import sys

import numpy as np

# `_disable_kuzu()` est exécuté à l'import de ce module (contention + non-repro, CLAUDE.md)
from tools.evo_memory_inworld import (  # noqa: E402
    _cfg, _fresh_soup, N_APEX, measure_channel_saliency,
)
from src.worlds.world_1_stoneage import Biosphere3D  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402
from src.seed_ai.persistence import calculate_life_score  # noqa: E402
from src.seed_ai.mutation import apply_mutations, MutationConfig, Genome  # noqa: E402
from tools.lewis_world import _setup_lewis  # noqa: E402


SIG_COL = 5            # canal d'obs câblé à `np.zeros(N)` (world_1_stoneage.py:610) -> information NULLE
ACT_POS, ACT_NEG = 2, 3    # signal +1 -> Est (action 2) ; signal −1 -> Ouest (action 3) — cf. :1559-1562
PSEUDO = 20.0          # pseudo-comptes du prior Beta(PSEUDO/2, PSEUDO/2) : corrige le backfire EDR-056
CHANCE = 0.5           # plafond d'une politique FIXE : toujours-Est matche la moitié des ticks (signal 50/50)


def measure_cognitive_rate(agent) -> float:
    """Taux de réponse correcte au signal, lissé par pseudo-comptes vers ZÉRO : `succès / (ticks + PSEUDO)`.

    C'est le cœur de la correction d'EDR-056 : un agent qui n'a vécu que 3 ticks et « réussi » 3 fois par
    hasard rend 0.13, pas 1.0 -> le bruit à faible compte NE PEUT PAS gagner la sélection, alors qu'il la
    gagnait dans EDR-056 (distinction fortuite à compte 1, amplifiée ×400 dans la fitness).

    ⚠️ Le lissage va vers 0, PAS vers la chance. Un lissage vers 0.5 (prior Beta(10,10)) crée une
    incitation PERVERSE mesurée pendant le pré-vol : les agents réels plafonnent vers 0.10, donc un agent
    mort à 3 ticks serait tiré vers 0.435 tandis qu'un agent vivant 120 ticks et lisant mal tomberait à
    0.157 -> à poids fort la sélection optimiserait la MORT PRÉCOCE, et le banc rendrait un faux négatif
    (« l'objectif ne produit pas de lecture ») qui ne mesurerait que l'estimateur. Avec un prior à 0, un
    tick réussi de plus AMÉLIORE toujours le score (t + PSEUDO > h toujours vrai) : pas de récompense
    pour l'absence de preuve, pas d'incitation à mourir."""
    t = int(agent.get("_cog_ticks", 0))
    h = int(agent.get("_cog_hits", 0))
    return h / (t + PSEUDO)


def cognitive_fitness(agent, weight: float) -> float:
    """Fitness LOCALE = life_score de prod + poids × taux cognitif (lissé vers 0).

    ⚠️ `calculate_life_score` n'est jamais mutée (blast-radius, EDR-WLD-002 : la fitness de prod est
    partagée par toutes les sessions parallèles)."""
    return calculate_life_score(agent) + weight * measure_cognitive_rate(agent)


class CognitiveSignalBiosphere(Biosphere3D):
    """Monde de base + un signal i.i.d. ±1 par agent et par tick dans `obs[:, SIG_COL]`, et comptage
    de la réponse (l'action choisie est-elle celle qu'exige le signal ?).

    `inject=False` : le signal est TIRÉ et noté mais PAS montré -> bras aveugle. C'est le contrôle
    négatif exact du banc : la tâche est identique, seule l'INFORMATION est retirée, donc aucun génome
    ne peut dépasser la chance. `assert_ablation_changes_something` du pré-vol."""

    inject = True

    def get_batch_observations(self):
        obs = super().get_batch_observations()
        if getattr(obs, "size", 0) == 0:
            return obs
        for i, ag in enumerate(self.agents):
            if i >= obs.shape[0]:
                continue
            s = 1.0 if np.random.rand() < 0.5 else -1.0
            ag["_cog_sig"] = s                  # stocké sur le DICT (robuste à un réordonnancement)
            if self.inject:
                obs[i, SIG_COL] = s
        return obs

    def step(self):
        super().step()                          # obs (signal injecté) -> logits -> `last_action`
        for ag in self.agents:
            s = ag.pop("_cog_sig", None)        # consommé : jamais compté deux fois
            if s is None:
                continue
            a = int(ag.get("last_action", -1))
            if a < 0:
                continue
            ag["_cog_ticks"] = int(ag.get("_cog_ticks", 0)) + 1
            ag["_cog_hits"] = int(ag.get("_cog_hits", 0)) + int(a == (ACT_POS if s > 0 else ACT_NEG))


def _make_env(cfg, inject=True, benchmark=False, era=1):
    env = CognitiveSignalBiosphere(cfg)
    env.inject = inject
    _setup_lewis(env, n_each=N_APEX)
    if benchmark:
        env.benchmark_mode = True               # cohorte fixe : pas de repro qui dilue le champion
        env.night_enabled = False
        env.current_era = 10_000
    else:
        env.current_era = era
    return env


def _run_era(genomes, cfg, max_ticks, era, inject=True, benchmark=False):
    env = _make_env(cfg, inject=inject, benchmark=benchmark, era=era)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    t = 0
    while env.agents and t < max_ticks:
        env.step()
        t += 1
    return env, list(env.agents) + list(env.dead_agents)


def _make_reflex(genomes, diag=10.0):
    """Met la diagonale de W à `diag` -> δ = sigmoid(diag) ≈ 1 -> `H_new = f(excitation)` : substrat SANS
    report d'état. C'est la moitié « dé-mémoriser » de la conjonction qu'exige un lecteur réactif.

    Motivé par une mesure du pré-vol : `init_primordial_soup` tire `W = randn·0.1`, donc diag ≈ 0 et
    δ ≈ 0.5 -> l'état s'ACCUMULE et (l'activation ayant f(0) ≠ 0) même les sorties non câblées dérivent
    à +7.45 ± 9.8, ce qui NOIE une marge de signal de ±2.5. Bâtir un lecteur réactif demande donc DEUX
    mutations conjointes — câbler le canal ET dé-mémoriser la sortie. Ce bras fournit la seconde
    gratuitement : il sépare « l'objectif ne demande pas » de « le substrat ne l'atteint pas »."""
    out = []
    for g in genomes:
        h = g.clone()
        np.fill_diagonal(h.W, diag)
        out.append(h)
    return out


def evolve_cognitive(weight, seed, eras=15, max_ticks=120, num_agents=30, add_node_rate=0.4,
                     inject=True, reflex_init=False):
    """Évolution in-world auto-contenue sous fitness = survie + `weight` × lecture du signal.

    `weight=0` -> la sélection est EXACTEMENT celle de prod (le signal est présent mais non noté) : c'est
    le bras de contrôle, et il reproduit le régime d'EVO-004. Aucune écriture du HoF global.
    `reflex_init=True` -> soupe initiale sans report d'état (cf. `_make_reflex`), facteur croisé avec le
    poids pour séparer OBJECTIF et ATTEIGNABILITÉ.

    Renvoie aussi `traj` = meilleur taux BRUT par ère : une trajectoire PLATE dit « la recherche ne
    progresse pas » (verrou en amont), une trajectoire qui MONTE encore à la fin dit « pas assez d'ères »
    — distinction qu'un chiffre final seul ne permet pas de faire."""
    np.random.seed(seed)
    cfg = _cfg()
    mc = MutationConfig()
    mc.add_node_rate = add_node_rate
    genomes = _fresh_soup(num_agents, cfg, add_node_rate)
    if reflex_init:
        genomes = _make_reflex(genomes)
    n_elite = max(3, num_agents // 4)
    best_g, best_fit, best_rate = genomes[0].clone(), -1e18, 0.0
    traj = []
    for era in range(1, eras + 1):
        _, pool = _run_era(genomes, cfg, max_ticks, era, inject=inject)
        if not pool:
            break
        pool.sort(key=lambda ag: cognitive_fitness(ag, weight), reverse=True)
        traj.append(max((int(a.get("_cog_hits", 0)) / max(1, int(a.get("_cog_ticks", 0)))) for a in pool))
        top = cognitive_fitness(pool[0], weight)
        if top > best_fit:
            best_fit, best_rate = top, measure_cognitive_rate(pool[0])
            best_g = pool[0]["model"].genome.clone()
        elites = [ag["model"].genome.clone() for ag in pool[:n_elite]]
        children = []
        while len(children) < num_agents - len(elites):
            parent = elites[np.random.randint(len(elites))]
            children.append(apply_mutations(parent, mc))
        genomes = elites + children
    return {"genome": best_g, "fitness": best_fit, "rate_evo": best_rate,
            "nodes": best_g.num_nodes, "traj": traj}


def benchmark_cognitive(genome, seed, num_agents=24, ticks=150, inject=True):
    """INSTRUMENT PRIMAIRE (calibré) — taux de réponse correcte d'un champion, sur cohorte de clones.

    Renvoie `raw` (= succès/ticks, LA grandeur du verdict, à lire contre le plafond analytique CHANCE),
    `rate` (lissé vers 0, la grandeur de SÉLECTION), `ticks`, et des témoins de survie (`med_age`,
    `preys`) pour lire le COÛT de la cognition.

    Vérité-terrain analytique (calibration) : toute politique FIXE plafonne à raw = CHANCE = 0.5
    (toujours-Est ne matche que les ticks à signal +1) -> raw > 0.5 EXIGE de lire le canal. Mesuré au
    pré-vol : lecteur réflexe câblé -> 0.856 ; même génome avec l'information RETIRÉE -> 0.123 ;
    non-lecteur réflexe -> 0.100 (les politiques qui n'utilisent jamais Est/Ouest tendent vers 0)."""
    np.random.seed(seed)
    cfg = _cfg()
    cohort = [genome.clone() for _ in range(num_agents)]
    env, pool = _run_era(cohort, cfg, ticks, era=10_000, inject=inject, benchmark=True)
    hits = sum(int(ag.get("_cog_hits", 0)) for ag in pool)
    tk = sum(int(ag.get("_cog_ticks", 0)) for ag in pool)
    ages = [ag["age"] for ag in pool] or [0]
    return {
        "rate": hits / (tk + PSEUDO) if tk else float("nan"),
        "raw": hits / tk if tk else float("nan"),
        "ticks": tk,
        "med_age": float(statistics.median(ages)),
        "preys": sum(int(ag.get("preys_eaten", 0)) for ag in pool),
    }


def synthetic_reader(num_inputs, num_outputs, num_nodes, w=8.0, reflex=True):
    """CONTRÔLE POSITIF de la TÂCHE (générateur A du pré-vol) : génome câblé à la main qui lit le canal
    du signal et pousse Est/Ouest en conséquence. Si LUI ne dépasse pas la chance in-world, la tâche est
    irréalisable et aucun verdict négatif sur l'évolution ne serait interprétable.
    Convention de layout : entrées = premiers `num_inputs` noeuds, sorties = `num_outputs` DERNIERS.

    ⚠️ `reflex=True` met TOUTE la diagonale à +10 -> δ = sigmoid(diag) ≈ 1 -> `H_new = f(excitation)`,
    aucun report d'état. Indispensable, et mesuré : avec une diagonale nulle (δ=0.5) l'état s'ACCUMULE
    et, l'activation METAPROG ayant f(0) ≠ 0, même les sorties JAMAIS câblées dérivent (logit d'une
    action non câblée mesuré à +7.45 ± 9.8 après 25 ticks). L'`argmax` est alors arbitré par les
    fluctuations de la dérive, pas par le signal : le contrôle positif tombait à 0.53 (= la chance)
    alors que le MÊME génome est parfait sur un état frais. Un lecteur RÉFLEXE n'a pas ce défaut."""
    W = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    if reflex:
        np.fill_diagonal(W, 10.0)          # δ≈1 -> substrat sans mémoire : pas de dérive accumulée
    W[SIG_COL, num_nodes - num_outputs + ACT_POS] = +w
    W[SIG_COL, num_nodes - num_outputs + ACT_NEG] = -w
    return Genome(W, num_inputs, num_outputs)


def _med(xs):
    return statistics.median(xs) if xs else float("nan")


ARMS = [                     # (poids cognitif, soupe sans report d'état) — plan FACTORIEL
    (0.0, False),            # contrôle : sélection de PROD (signal présent, non noté) = régime EVO-004
    (200.0, False),          # le poids commence à mordre sur la sélection (jaccard top-7 ≈ 0.65)
    (800.0, False),          # mord fort (jaccard ≈ 0.53)
    (5000.0, False),         # domine la fitness (jaccard ≈ 0.28) : la lecture PRIME sur la survie
    (0.0, True),             # atteignabilité SEULE (substrat réflexe, aucune demande cognitive)
    (800.0, True),           # les DEUX : l'objectif demande ET le substrat rend la lecture atteignable
]


def main():
    seeds = list(range(int(os.environ.get("EVO5_SEEDS", "5"))))
    eras = int(os.environ.get("EVO5_ERAS", "35"))
    ticks = int(os.environ.get("EVO5_TICKS", "120"))
    agents = int(os.environ.get("EVO5_AGENTS", "30"))
    print(f"EVO-005 : plan factoriel OBJECTIF × ATTEIGNABILITÉ | {len(ARMS)} bras x {len(seeds)} seeds "
          f"x {eras} ères x {ticks} ticks x {agents} agents")
    print(f"  tâche : obs[{SIG_COL}]=±1 (canal à information NULLE) -> action {ACT_POS} (Est) / {ACT_NEG} (Ouest)")
    print(f"  plafond d'une politique FIXE = {CHANCE} | pré-vol : lecteur câblé 0.856, non-lecteur 0.100\n")
    table = {}
    for w, refl in ARMS:
        rows = []
        for s in seeds:
            r = evolve_cognitive(w, s, eras, ticks, agents, reflex_init=refl)
            b = benchmark_cognitive(r["genome"], 1000 + s)
            sal = measure_channel_saliency(r["genome"], 2000 + s, channels=[SIG_COL], decision=True)
            tr = r["traj"]
            rows.append({"seed": s, **b, "sal": sal[SIG_COL], "nodes": r["nodes"], "traj": tr})
            half = len(tr) // 2
            print(f"  W={w:<6} reflex={int(refl)} seed {s}: raw={b['raw']:.3f} sal={sal[SIG_COL]:.3f} | "
                  f"traj 1re/2de moitié={_med(tr[:half]):.3f}/{_med(tr[half:]):.3f} max={max(tr) if tr else float('nan'):.3f} | "
                  f"age={b['med_age']:.0f} proies={b['preys']} N={r['nodes']}")
        table[(w, refl)] = rows
    print("\n=== PLAN FACTORIEL (médianes sur seeds) ===")
    print(f"{'W':>7} {'reflex':>7} | {'raw':>6} | {'sal argmax':>10} | {'traj max':>8} | {'age':>5} | {'proies':>6}")
    for key in ARMS:
        rr = table[key]
        print(f"{key[0]:>7} {int(key[1]):>7} | {_med([r['raw'] for r in rr]):>6.3f} | "
              f"{_med([r['sal'] for r in rr]):>10.3f} | {_med([max(r['traj']) for r in rr if r['traj']]):>8.3f} | "
              f"{_med([r['med_age'] for r in rr]):>5.0f} | {_med([r['preys'] for r in rr]):>6.0f}")
    print(f"\n  (chance={CHANCE} : toute valeur raw > {CHANCE} EXIGE de lire obs[{SIG_COL}])")
    print("  lecture : si raw monte avec W à reflex=0 -> l'OBJECTIF est le levier ; si ça ne monte QUE")
    print("  à reflex=1 -> le verrou était l'ATTEIGNABILITÉ ; si rien ne monte -> verrou crédit/recherche.")
    return table


if __name__ == "__main__":
    sys.exit(0 if main() else 0)
