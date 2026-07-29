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
from tools.cost_guard import CostGuard  # noqa: E402


SIG_COL = 5            # canal d'obs câblé à `np.zeros(N)` (world_1_stoneage.py:610) -> information NULLE
ACT_POS, ACT_NEG = 2, 3    # signal +1 -> Est (action 2) ; signal −1 -> Ouest (action 3) — cf. :1559-1562
PSEUDO = 20.0          # pseudo-comptes du prior Beta(PSEUDO/2, PSEUDO/2) : corrige le backfire EDR-056
CHANCE = 0.5           # plafond d'une politique FIXE : toujours-Est matche la moitié des ticks (signal 50/50)

# --- EVO-006 : crédit PARTIEL (K sous-tâches indépendantes) ------------------------------------------
# EVO-005 a laissé UNE différence structurelle non testée entre le proxy qui réussit et l'in-world qui
# échoue : le proxy note K bits INDÉPENDAMMENT (câbler 1 bit sur K gagne 1/K même si les autres sont
# faux = un GRADIENT), l'in-world n'en notait qu'un (tout ou rien). Le monde consomme pourtant PLUSIEURS
# décisions indépendantes par tick — pas seulement `argmax(logits[:8])` mais aussi `do_throw =
# logits[8] > 0` (:1319) et `out_accept = logits[14] > 0` (:957). Chacune a le MÊME plafond de politique
# fixe (0.5), donc le repère d'EVO-005 est conservé À L'IDENTIQUE et une seule variable change.
SIG_COLS = (5, 10, 23, 24, 30)   # canaux `np.zeros` câblés en dur — vérifiés à 0.0 EXACT dans le monde de base
THROW_IDX, ACCEPT_IDX = 8, 14
AIM_X_IDX, AIM_Y_IDX = 11, 12    # `aim_vec = [logits[11], logits[12]]` (world_1_stoneage.py:1321)


def _resp_move(agent, logits, s):
    """Sous-tâche 0 — l'ACTION réellement exécutée par le monde (pas un logit) : Est si +1, Ouest si −1."""
    a = int(agent.get("last_action", -1))
    return None if a < 0 else int(a == (ACT_POS if s > 0 else ACT_NEG))


def _resp_sign(idx):
    """Sous-tâches 1..n — variable de DÉCISION binaire que le monde lit (`logit > 0`), capturée après
    `_apply_social_consensus`, donc telle que le monde l'utilise. ⚠️ Le monde peut ensuite GATER l'effet
    (un throw sans lance ne part pas) : on note la décision, pas son effet — hedge à porter au record."""
    def f(agent, logits, s):
        if logits is None or idx >= len(logits):
            return None
        return int((float(logits[idx]) > 0.0) == (s > 0))
    return f


SUBTASKS = (
    ("move", _resp_move),                 # 0 — DURE : gagner un `argmax` à 8 voies
    ("throw", _resp_sign(THROW_IDX)),     # 1 — seuil de SIGNE : un seul poids suffit
    ("accept", _resp_sign(ACCEPT_IDX)),   # 2 — idem
    ("aim_x", _resp_sign(AIM_X_IDX)),     # 3 — idem (ajoutées pour APPARIER la difficulté, EVO-007)
    ("aim_y", _resp_sign(AIM_Y_IDX)),     # 4 — idem
)
SUB_OUT = {"move": None, "throw": THROW_IDX, "accept": ACCEPT_IDX,
           "aim_x": AIM_X_IDX, "aim_y": AIM_Y_IDX}

# Jeux de sous-tâches (EVO-007) — le confond qu'EVO-006 n'a PAS démêlé : ses 3 sous-tâches n'étaient pas
# d'égale difficulté (`move` exige un argmax, `throw`/`accept` un simple signe), et c'est `throw` qui a été
# appris. Une part du gain venait donc peut-être de sous-tâches plus FACILES, pas seulement plus NOMBREUSES.
# Pire : EVO-005 (K=1) n'utilisait QUE `move`, la plus DURE -> son échec confondait « pas de crédit
# partiel » et « tâche unique trop dure ». Ces trois jeux séparent les deux facteurs.
TASKS_EVO006 = (0, 1, 2)     # mixte, tel quel : reproduit EVO-006
TASKS_MATCHED = (1, 3, 4)    # 3 sous-tâches au MÊME opérateur (signe) -> difficulté APPARIÉE + crédit partiel
TASKS_EASY1 = (1,)           # UNE sous-tâche facile, SANS crédit partiel -> le contrôle décisif


def _tasks_of(K=None, tasks=None):
    """`tasks` = indices explicites dans SUBTASKS ; `K` = raccourci rétro-compatible (K premières)."""
    if tasks is not None:
        return tuple(tasks)
    return tuple(range(int(K or 1)))


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
    tasks = (0,)                                # indices dans SUBTASKS ; la i-ᵉ tâche ACTIVE lit SIG_COLS[i]

    def get_batch_observations(self):
        obs = super().get_batch_observations()
        if getattr(obs, "size", 0) == 0:
            return obs
        for i, ag in enumerate(self.agents):
            if i >= obs.shape[0]:
                continue
            sigs = [1.0 if np.random.rand() < 0.5 else -1.0 for _ in self.tasks]
            ag["_cog_sig"] = sigs               # stocké sur le DICT (robuste à un réordonnancement)
            if self.inject:
                for i_t, s in enumerate(sigs):
                    obs[i, SIG_COLS[i_t]] = s
        return obs

    def _apply_social_consensus(self, batch_logits):
        """Seam de capture : le monde appelle ceci JUSTE après le forward et AVANT la boucle d'action
        (world_1_stoneage.py:1225), donc `out[i]` est exactement le vecteur de logits sur lequel les
        décisions du tick sont prises. Rangé sur le DICT de l'agent -> insensible aux morts/réordres."""
        out = super()._apply_social_consensus(batch_logits)
        for i, ag in enumerate(self.agents):
            if i < len(out):
                ag["_cog_logits"] = np.asarray(out[i], dtype=np.float32).copy()
        return out

    def step(self):
        super().step()                          # obs (signaux injectés) -> logits -> `last_action`
        for ag in self.agents:
            sigs = ag.pop("_cog_sig", None)     # consommé : jamais compté deux fois
            lg = ag.pop("_cog_logits", None)
            if sigs is None:
                continue
            per = ag.setdefault("_cog_hits_k", [0] * len(SUBTASKS))
            tk = ag.setdefault("_cog_ticks_k", [0] * len(SUBTASKS))
            for i_t, s in enumerate(sigs):
                k = self.tasks[i_t]
                r = SUBTASKS[k][1](ag, lg, s)
                if r is None:
                    continue
                # `_cog_ticks` compte les ESSAIS (K par tick) -> `measure_cognitive_rate` et le plafond
                # CHANCE=0.5 restent valides sans changement, K quelconque.
                ag["_cog_ticks"] = int(ag.get("_cog_ticks", 0)) + 1
                ag["_cog_hits"] = int(ag.get("_cog_hits", 0)) + r
                per[k] += r
                tk[k] += 1


def _make_env(cfg, inject=True, benchmark=False, era=1, K=1, tasks=None):
    env = CognitiveSignalBiosphere(cfg)
    env.inject = inject
    env.tasks = _tasks_of(K, tasks)
    _setup_lewis(env, n_each=N_APEX)
    if benchmark:
        env.benchmark_mode = True               # cohorte fixe : pas de repro qui dilue le champion
        env.night_enabled = False
        env.current_era = 10_000
    else:
        env.current_era = era
    return env


MAX_AGENTS = 200      # plafond DETERMINISTE de population par ere (garde de cout, classe E13)


def _run_era(genomes, cfg, max_ticks, era, inject=True, benchmark=False, K=1, tasks=None,
             max_agents=MAX_AGENTS):
    """⚠️ `max_agents` borne l'UNITE DE TRAVAIL ATOMIQUE, pas la boucle qui l'appelle.

    Mesure qui l'impose (2026-07-27) : à l'ère 13 du seed 8, la population passe de ~33 à **962 agents**
    en 84 ticks — la reproduction s'emballe quand un seed trouve un fourrageur très survivant. Une garde
    posée ENTRE les ères (`CostGuard` dans `evolve_cognitive`) ne peut rien : on ne lui rend jamais la
    main. Deux runs ont été tués comme ça (187 min / 8 seeds, puis 7 h).

    Le plafond porte sur le NOMBRE D'AGENTS, pas sur le temps : une échéance en secondes rendrait la
    troncature dépendante de la machine et de sa charge, donc le banc NON REPRODUCTIBLE. Un plafond de
    population est déterministe — même seed, même troncature, partout. Pics normaux mesurés : 30-44."""
    env = _make_env(cfg, inject=inject, benchmark=benchmark, era=era, K=K, tasks=tasks)
    for g in genomes:
        a = MambaAgent()
        a.from_genome(g)
        env.add_agent(a, energy=80.0)
    t = 0
    env.pop_capped = False
    while env.agents and t < max_ticks:
        env.step()
        t += 1
        if max_agents and len(env.agents) > max_agents:
            env.pop_capped = True          # troncature DÉTERMINISTE, à rapporter et non à taire
            break
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
                     inject=True, reflex_init=False, K=1, tasks=None, budget_s=None):
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
    # Garde de COÛT (classe E13). Le coût de cette boucle dépend du SEED — il suit le succès évolutif
    # (`CLAUDE.md` §Coût des runs) : mesuré, les seeds 0-4 coûtent ~35 s et le seed 8 n'a pas fini 35 ères
    # en 10 min. Aucune projection linéaire ne borne cette queue -> il faut un plafond AU RUNTIME, qui
    # abandonne l'unité coûteuse au lieu de laisser un seed pathologique tuer le run entier
    # (4ᵉ run abandonné du dépôt, 2026-07-27 : 187 min pour 8 seeds sur 36).
    guard = CostGuard(budget_s, label=f"seed {seed}") if budget_s else None
    for era in range(1, eras + 1):
        if guard is not None and guard.would_exceed():
            return {"genome": best_g, "fitness": best_fit, "rate_evo": best_rate,
                    "nodes": best_g.num_nodes, "traj": traj,
                    "aborted": f"budget {budget_s:.0f}s dépassé à l'ère {era}/{eras} "
                               f"({guard.spent_s:.0f}s) — seed EXCLU, à COMPTER dans le rapport"}
        _, pool = _run_era(genomes, cfg, max_ticks, era, inject=inject, K=K, tasks=tasks)
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
            "nodes": best_g.num_nodes, "traj": traj, "aborted": None}


def benchmark_cognitive(genome, seed, num_agents=24, ticks=150, inject=True, K=1, tasks=None):
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
    env, pool = _run_era(cohort, cfg, ticks, era=10_000, inject=inject, benchmark=True, K=K, tasks=tasks)
    hits = sum(int(ag.get("_cog_hits", 0)) for ag in pool)
    tk = sum(int(ag.get("_cog_ticks", 0)) for ag in pool)
    ages = [ag["age"] for ag in pool] or [0]
    per, per_t = [0] * len(SUBTASKS), [0] * len(SUBTASKS)
    for ag in pool:
        for k, (h, t) in enumerate(zip(ag.get("_cog_hits_k", []), ag.get("_cog_ticks_k", []))):
            per[k] += int(h)
            per_t[k] += int(t)
    return {
        "rate": hits / (tk + PSEUDO) if tk else float("nan"),
        "raw": hits / tk if tk else float("nan"),
        "ticks": tk,
        # `sub` = taux PAR sous-tâche : c'est là que se lit le crédit PARTIEL (une sous-tâche au-dessus de
        # CHANCE pendant que les autres y restent = l'évolution a câblé UN signal sur K).
        "sub": [(per[k] / per_t[k] if per_t[k] else float("nan")) for k in range(len(SUBTASKS))],
        "med_age": float(statistics.median(ages)),
        "preys": sum(int(ag.get("preys_eaten", 0)) for ag in pool),
    }


def synthetic_reader(num_inputs, num_outputs, num_nodes, w=8.0, reflex=True, wire=1, tasks=None):
    """CONTRÔLE POSITIF de la TÂCHE (générateur A du pré-vol) : génome câblé à la main qui lit le(s)
    canal(aux) de signal et pousse la sortie correspondante. Si LUI ne dépasse pas la chance in-world, la
    tâche est irréalisable et aucun verdict négatif sur l'évolution ne serait interprétable.
    Convention de layout : entrées = premiers `num_inputs` noeuds, sorties = `num_outputs` DERNIERS.

    `wire` = nombre de sous-tâches CÂBLÉES (défaut 1 = régime EVO-005). C'est aussi l'instrument du
    CRÉDIT PARTIEL : câbler 1 sur 3 doit rendre un score STRICTEMENT entre la chance et le lecteur
    complet. Si ce n'est pas le cas, il n'y a pas de gradient à offrir et le banc K>1 ne teste rien.

    ⚠️ `reflex=True` met TOUTE la diagonale à +10 -> δ = sigmoid(diag) ≈ 1 -> `H_new = f(excitation)`,
    aucun report d'état. Indispensable, et mesuré : avec une diagonale nulle (δ=0.5) l'état s'ACCUMULE
    et, l'activation METAPROG ayant f(0) ≠ 0, même les sorties JAMAIS câblées dérivent (logit d'une
    action non câblée mesuré à +7.45 ± 9.8 après 25 ticks). L'`argmax` est alors arbitré par les
    fluctuations de la dérive, pas par le signal : le contrôle positif tombait à 0.53 (= la chance)
    alors que le MÊME génome est parfait sur un état frais. Un lecteur RÉFLEXE n'a pas ce défaut."""
    W = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    if reflex:
        np.fill_diagonal(W, 10.0)          # δ≈1 -> substrat sans mémoire : pas de dérive accumulée
    o = num_nodes - num_outputs
    active = tuple(tasks) if tasks is not None else (0, 1, 2)
    for i_t, k in enumerate(active[:int(wire)]):
        name = SUBTASKS[k][0]
        if name == "move":                          # Est vs Ouest : il faut GAGNER l'argmax -> 2 poids
            W[SIG_COLS[i_t], o + ACT_POS] = +w
            W[SIG_COLS[i_t], o + ACT_NEG] = -w
        else:                                       # seuil de SIGNE : un seul poids suffit
            W[SIG_COLS[i_t], o + SUB_OUT[name]] = +w
    return Genome(W, num_inputs, num_outputs)


def measure_decision_saliency(genome, seed, channel, out_idx, num_agents=24, ticks=80, K=3, tasks=None):
    """Saillance FONCTIONNELLE d'une DÉCISION BINAIRE : perturber `obs[channel]` = ±1 change-t-il le SIGNE
    de `logits[out_idx]` — l'opérateur exact par lequel le monde décide (`do_throw = logits[8] > 0`,
    world_1_stoneage.py:1319 ; `out_accept = logits[14] > 0`, :957) ?

    Nécessaire parce que `measure_channel_saliency(decision=True)` lit la bascule d'`argmax(logits[:8])` :
    elle est AVEUGLE par construction aux sous-tâches `throw`/`accept` d'EVO-006, qui ne passent pas par
    l'argmax. Mesurer la mauvaise sortie rendrait « 0.000 » sur un lecteur parfait — la classe E17 déplacée
    du choix de la GRANDEUR (amplitude vs signe) au choix de la SORTIE.

    In-contexte (obs réelles), forward NON destructif sur le H courant. Renvoie le taux de bascule.
    Vérité-terrain : un génome câblant `channel -> out_idx` rend ~1.0 ; un non-câblé ~0.0."""
    from src.seed_ai.rl_evolution import recurrent_forward
    # ⚠️ `np.random.seed` REECRIT le RNG GLOBAL. Appelee APRES un run c'est inoffensif ; appelee PENDANT
    # (p.ex. pour tracer une lignee ere par ere) elle detourne l'evolution qu'elle est censee OBSERVER —
    # l'acte de mesurer mute le systeme mesure, meme forme que l'aliasing memoire de la classe E5.
    # Detecte le 2026-07-28 par un cas a REPONSE CONNUE : le seed 0, lecteur avere (4 reproductions),
    # rendait une courbe de saillance PLATE. Sans ce temoin, l'artefact se lisait comme un resultat.
    # L'etat est donc restaure a la sortie : la valeur rendue est inchangee, le flux de l'appelant intact.
    _rng_state = np.random.get_state()
    np.random.seed(seed)
    env = _make_env(_cfg(), inject=True, benchmark=True, K=K, tasks=tasks)
    for _ in range(num_agents):
        a = MambaAgent()
        a.from_genome(genome)
        env.add_agent(a, energy=80.0)
    flips = []
    for _ in range(ticks):
        if not env.agents:
            break
        obs = np.asarray(env.get_batch_observations(), dtype=np.float32)
        for i, ag in enumerate(env.agents):
            if i >= obs.shape[0]:
                continue
            m = ag["model"]
            op = obs[i:i + 1].copy(); op[0, channel] = 1.0
            om = obs[i:i + 1].copy(); om[0, channel] = -1.0
            pp = recurrent_forward(genome, op, m.H_prev, m.H_history, m.H_potentials)[0]
            pm = recurrent_forward(genome, om, m.H_prev, m.H_history, m.H_potentials)[0]
            if out_idx < pp.shape[1]:
                flips.append(float((float(pp[0, out_idx]) > 0.0) != (float(pm[0, out_idx]) > 0.0)))
        env.step()
    np.random.set_state(_rng_state)      # l'instrument ne laisse AUCUNE trace sur le RNG de l'appelant
    return float(np.mean(flips)) if flips else 0.0


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
    K = int(os.environ.get("EVO5_K", "1"))
    arms = ARMS if K == 1 else [(w, False) for w in (0.0, 200.0, 800.0, 5000.0)]
    names = [s[0] for s in SUBTASKS][:K]
    print(f"{'EVO-005' if K == 1 else 'EVO-006'} : K={K} sous-tâche(s) {names} | {len(arms)} bras x "
          f"{len(seeds)} seeds x {eras} ères x {ticks} ticks x {agents} agents")
    print(f"  signaux dans obs{list(SIG_COLS[:K])} (canaux à information NULLE, vérifiés à 0.0 exact)")
    print(f"  plafond d'une politique FIXE = {CHANCE} sur CHAQUE sous-tâche -> même repère qu'à K=1")
    if K > 1:
        print("  pré-vol : câblé 0/3=0.378  1/3=0.581  2/3=0.751  3/3=0.939 -> le CRÉDIT PARTIEL existe\n")
    else:
        print("  pré-vol : lecteur câblé 0.856, non-lecteur 0.100\n")
    table = {}
    for w, refl in arms:
        rows = []
        for s in seeds:
            r = evolve_cognitive(w, s, eras, ticks, agents, reflex_init=refl, K=K)
            b = benchmark_cognitive(r["genome"], 1000 + s, K=K)
            sal = measure_channel_saliency(r["genome"], 2000 + s, channels=[SIG_COL], decision=True)
            rows.append({"seed": s, **b, "sal": sal[SIG_COL], "nodes": r["nodes"], "traj": r["traj"]})
            subs = " ".join(f"{names[k]}={b['sub'][k]:.3f}" for k in range(K))
            print(f"  W={w:<6} reflex={int(refl)} seed {s}: raw={b['raw']:.3f} [{subs}] "
                  f"sal={sal[SIG_COL]:.3f} | age={b['med_age']:.0f} proies={b['preys']} N={r['nodes']}")
        table[(w, refl)] = rows
    print(f"\n=== SYNTHÈSE K={K} (médianes sur seeds) ===")
    head = " ".join(f"{n:>8}" for n in names)
    print(f"{'W':>7} {'reflex':>7} | {'raw':>6} | {head} | {'sal':>6} | {'age':>5} | {'proies':>6} | max raw")
    for key in arms:
        rr = table[key]
        subs = " ".join(f"{_med([r['sub'][k] for r in rr]):>8.3f}" for k in range(K))
        print(f"{key[0]:>7} {int(key[1]):>7} | {_med([r['raw'] for r in rr]):>6.3f} | {subs} | "
              f"{_med([r['sal'] for r in rr]):>6.3f} | {_med([r['med_age'] for r in rr]):>5.0f} | "
              f"{_med([r['preys'] for r in rr]):>6.0f} | {max(r['raw'] for r in rr):.3f}")
    print(f"\n  (règle PRÉ-ENREGISTRÉE : raw > {CHANCE} = affirmation d'EXISTENCE contre un plafond")
    print("   ANALYTIQUE ; contrastes entre bras DIRECTIONNELS seulement à n=5.)")
    if K > 1:
        print("  lecture : une SOUS-TÂCHE au-dessus de 0.5 pendant que les autres y restent = l'évolution")
        print("  a saisi le crédit PARTIEL -> le verrou d'EVO-005 était la GRANULARITÉ du gradient.")
        print("  Si rien ne dépasse 0.5 malgré un gradient VÉRIFIÉ -> « verrou = paysage » est RÉFUTÉ.")
    return table


if __name__ == "__main__":
    sys.exit(0 if main() else 0)
