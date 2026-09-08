"""EDR-EVO-002 — TEST DISCRIMINANT de EVO-001 : un objectif qui EXIGE la mémoire enrichit-il le substrat ?

[[EDR-EVO-001]] a montré que la sélection par la SURVIE n'enrichit pas la dynamique du substrat (champions
évolués aussi contractifs que frais) et a conclu « le verrou du gap in-world est l'OBJECTIF, pas la
capacité ». Ce record TRANCHE cette conclusion par sa falsification directe : si l'objectif est le levier,
alors un objectif qui RÉCOMPENSE le calcul récurrent (rappel différé) DOIT produire un substrat qui
RETIENT — sinon le verrou est le substrat/l'évolution, pas l'objectif.

## Le piège d'instrument évité (pourquoi PAS measure_convergence)
`measure_convergence` (EVO-001) décide « l'état bouge-t-il encore ? ». Or une MÉMOIRE parfaite est un état
qui NE BOUGE PAS (δ→0 : H_new=H) : il la classerait « gelée/contractive », CONFONDANT rétention et oubli.
Une mémoire à attracteur-ligne (deux encodages -> deux points fixes distincts) « converge » aussi. Le bon
instrument mesure ce que la tâche récompense vraiment : la SÉPARATION de deux histoires après le délai.

## Instrument PRIMAIRE : la CAPACITÉ DE RAPPEL (la grandeur qui agit, pas un proxy)
On mesure directement « l'évolution a-t-elle construit la mémoire ? » = accuracy sur un test de rappel
DEMANDING tenu à l'écart (cf. eval_genome + compute_enrichment_verdict). Contraste tranchant :
  * DEMAND (objectif exige la mémoire) : doit MAÎTRISER (positif fort, pas 0.7 marginal).
  * MEMORYLESS-XEVAL : évolué sur un objectif qui rend la mémoire INUTILE (leurre à l'encode, cible à la
    sonde), puis CROSS-ÉVALUÉ sur le test DEMANDING -> ~chance : il n'a AUCUNE mémoire. Manipulation
    INVERSE (REF-EXPERIMENT-PREFLIGHT) qui REND la mémoire inutile, pas qui « ne la demande pas » (sinon
    l'évolution la construit quand même : tenir 2 bits/3 ticks est trivial).
  * FRESH : plancher.
Prédiction si EVO-001 vrai (objectif = levier) : DEMAND maîtrise ; MEMORYLESS-XEVAL ≈ FRESH ≈ chance.
Falsificateur (verrou = substrat/recherche) : DEMAND reste au plancher malgré la demande.

## Instrument SECONDAIRE, DOCUMENTÉ COMME TROMPEUR : sep(D)
`measure_retention_separation` (calibré par construction : δ=1&W_off=0 -> sep=0 ; δ=0 -> sep=1 ; monotone) a
été conçu d'abord comme instrument primaire, PUIS réfuté par calibration-contre-tâche : un rappel par
`sign(preds)` est résolu par un substrat CONTRACTIF (le signe survit à (1−δ)^D), et sep(init aléatoire)
mesure la rétention d'une perturbation GÉNÉRIQUE, PAS le sous-espace signé bas-dim que la tâche utilise.
Mesuré : DEMAND maîtrise (acc 1.0) avec sep≈0.6-0.75, indiscernable de MEMORYLESS/FRESH. On le garde
comme CORROBORANT dynamique et surtout comme cas d'école (un proxy dynamique plausible qui n'agit PAS).

## Design (à joindre au record — declare_design)
- Unité de réplication : le SEED (lignée évolutive indépendante), comme EVO-001. PAS le génome d'une lignée.
- Trois sources, MÊME opérateur / dims (I=O=8), MÊME test DEMANDING — seul l'OBJECTIF D'ÉVOLUTION change.
- Contrôle positif (générateur A) : DEMAND doit MAÎTRISER (sinon un nul = échec de l'évolution, pas
  propriété de l'objectif). Contrôle inverse (générateur A, règle 1) : MEMORYLESS-XEVAL, qui PEUT échouer.

Usage : python -m tools.evo_memory_enrichment   (env: EVO2_SEEDS, EVO2_K, EVO2_D, EVO2_GEN, EVO2_POP)
Rapide (ni DB ni Biosphere). Réutilise le VRAI substrat récurrent (recurrent_forward) et la VRAIE mutation.
"""
import os
import statistics
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.mutation import Genome, apply_mutations, MutationConfig
from src.seed_ai.rl_evolution import recurrent_forward

I_DIM, O_DIM = 8, 8          # slots fixes (>= K) -> génomes comparables entre bras


# ============================================================ INSTRUMENT (sous cliquet)

def measure_retention_separation(genome, D, n_pairs=64, seed=0, eps=1e-9):
    """sep(D) : le substrat RETIENT-il la différence entre deux histoires après D pas d'ENTRÉE NULLE ?

    Deux états cachés aléatoires (nœuds >= I seulement — les I premiers sont clampés à 0 par la récurrence,
    donc la mémoire ne peut vivre qu'au-delà), conduits D pas sous obs=0 (le régime EXACT du délai de la
    tâche -> la grandeur mesurée est celle qui agit), puis médiane de ‖H_A(D)−H_B(D)‖/‖H_A(0)−H_B(0)‖.

    Calibré PAR CONSTRUCTION (test_instrument_calibration) : δ=1 & W_off=0 -> H_new=tanh(0)=0 -> sep=0 ;
    δ=0 -> H_new=H -> sep=1 ; monotone décroissant en δ. Immunisé contre le confond attracteur-ligne de
    measure_convergence (deux points fixes DISTINCTS gardent sep>0 = retenus).

    ⚠️ 2026-09-08 : le `return 0.0` de sortie était le biais N°1 du dépôt — une absence de mesure
    (aucune paire tirée) publiée comme l'affirmation de FOND « le substrat ne retient RIEN », qui est
    précisément la valeur d'un OUBLI PARFAIT. Trois entrées la produisaient sans un mot : n_pairs<=0,
    D<0 (délai muet -> sep=1.0, l'affirmation INVERSE), et un génome sans aucun nœud au-delà des
    entrées (N<=I -> les deux histoires sont identiques, d0=0, toutes les paires écartées). Elles
    LÈVENT désormais, en tête (refus instantané, aucune simulation)."""
    N = genome.num_nodes
    I = genome.num_inputs
    # GARDE D'ARGUMENTS, EN TETE, AVANT toute simulation : ces trois cas ne sont pas « sep = 0 »,
    # ils sont « sep NON MESURABLE ». Un refus doit etre instantane.
    if int(n_pairs) <= 0 or int(D) < 0 or N <= I:
        raise ValueError(
            f"measure_retention_separation : argument degenere (n_pairs={n_pairs} D={D} "
            f"num_nodes={N} num_inputs={I}) -- aucune paire d'histoires mesurable ; ne pas confondre "
            "avec une retention nulle OBSERVEE (sep=0 est la valeur de l'OUBLI PARFAIT).")
    rng = np.random.RandomState(seed)
    zero = np.zeros((1, I), np.float32)
    Hh = np.zeros((1, 5, N), np.float32)                  # buffers inertes (recurrent_forward ne les lit pas ici)
    Hp = np.zeros((1, N), np.float32)
    ratios = []
    for _ in range(n_pairs):
        HA = np.zeros((1, N), np.float32)
        HB = np.zeros((1, N), np.float32)
        HA[0, I:] = rng.randn(N - I).astype(np.float32)   # ne différer que sur les nœuds NON-entrée
        HB[0, I:] = rng.randn(N - I).astype(np.float32)
        d0 = float(np.linalg.norm(HA - HB))
        if d0 < eps:
            continue
        for _ in range(D):
            _, HA, _, _, _ = recurrent_forward(genome, zero, HA, Hh, Hp)
            _, HB, _, _, _ = recurrent_forward(genome, zero, HB, Hh, Hp)
        ratios.append(float(np.linalg.norm(HA - HB) / d0))
    if not ratios:                       # toutes les paires ecartees (d0 < eps) : RIEN n'a ete mesure
        raise ValueError(
            f"measure_retention_separation : {n_pairs} paire(s) tiree(s), AUCUNE separable (d0 < "
            f"{eps}) sur un genome a {N - I} noeud(s) hors-entree -- aucune mesure ; ne pas confondre "
            "avec une retention nulle OBSERVEE.")
    return float(statistics.median(ratios))


# ============================================================ FITNESS (tâche de rappel)

def eval_genome(genome, K, D, demanding=True, trials=32, seed=0):
    """Rappel parallèle de K bits après délai D (chance=0.5). La CIBLE à restituer est toujours `target`.

    - demanding=True  : la cible est ENCODÉE (t=0) puis CACHÉE à la sonde -> il faut la MÉMOIRE.
    - demanding=False : à l'encode on montre un LEURRE aléatoire (à ignorer), et la cible n'apparaît qu'à la
      SONDE -> résoluble en feedforward, et tenir l'encode est CONTRE-productif (leurre != cible). C'est la
      vraie manipulation INVERSE : le contrôle ne se contente pas de « ne pas exiger » la mémoire, il la
      REND INUTILE, sinon l'évolution la construit quand même (tenir 2 bits/3 ticks est facile).

    Un génome évolué en memoryless, CROSS-ÉVALUÉ en demanding, lit l'entrée de sonde (=0) -> ~chance : il
    n'a AUCUNE mémoire. C'est ce contraste (et non sep) qui tranche EVO-001.

    ⚠️ 2026-09-08 (refutation) : `trials<=0` rendait `float(np.mean([]))` = **nan**, EN SILENCE. La
    garde de `run_experiment` fermait la cause connue EN AVAL ; tout appelant DIRECT (et `evolve`,
    qui appelle cette fonction `generations x pop` fois) obtenait toujours nan sans un mot. Le nan
    n'est pas une accuracy basse : `nan > x` vaut False pour TOUTE comparaison, donc il traverse un
    verdict comme un resultat DEFAVORABLE. Il LEVE desormais, EN TETE. Meme garde pour `K` : a
    `K >= I_DIM` la ligne `go[0, K] = 1.0` levait un IndexError a huit appels de profondeur."""
    if int(trials) <= 0 or int(K) <= 0 or int(K) >= I_DIM or int(D) < 0:
        raise ValueError(
            f"eval_genome : argument degenere (trials={trials} K={K} D={D} I_DIM={I_DIM}) -- "
            "aucun essai mesurable ; `np.mean([])` rend nan, qui n'est PAS une accuracy nulle "
            "OBSERVEE et qui s'evalue a False contre TOUTE barre de verdict.")
    N = genome.num_nodes
    Hh = np.zeros((1, 5, N), np.float32)
    Hp = np.zeros((1, N), np.float32)
    rng = np.random.RandomState(seed)
    accs = []
    for _ in range(trials):
        target = rng.choice([-1.0, 1.0], size=K).astype(np.float32)   # ce qu'il faut restituer
        H = np.zeros((1, N), np.float32)
        obs = np.zeros((1, I_DIM), np.float32)
        obs[0, :K] = target if demanding else rng.choice([-1.0, 1.0], size=K).astype(np.float32)  # cible | LEURRE
        _, H, _, _, _ = recurrent_forward(genome, obs, H, Hh, Hp)
        for _ in range(D):                                # délai (entrées nulles) -> seule la récurrence porte
            _, H, _, _, _ = recurrent_forward(genome, np.zeros((1, I_DIM), np.float32), H, Hh, Hp)
        go = np.zeros((1, I_DIM), np.float32)
        go[0, K] = 1.0                                    # signal "recall"
        if not demanding:
            go[0, :K] = target                            # MEMORYLESS : la cible n'apparaît qu'ICI -> feedforward
        preds, H, _, _, _ = recurrent_forward(genome, go, H, Hh, Hp)
        recalled = np.sign(preds[0, :K])
        accs.append(float(np.mean(recalled == target)))
    return float(np.mean(accs))


def measure_cue_saliency(genome, K, D, trials=64, seed=0, bit=0):
    """EDR-EVO-004 — CONTRÔLE POSITIF AU NIVEAU DE L'OBJECTIF (le maillon que le génome câblé à la main ne
    fournit pas) : l'ÉVOLUTION sait-elle produire une politique qui LIT son entrée, quand l'objectif l'exige ?

    Même épisode que `eval_genome` (encode -> D pas d'entrée NULLE -> sonde), joué DEUX fois à l'identique
    (design apparié : mêmes autres bits, même H initial) sauf l'indice `bit` mis à +1 vs −1. On lit |Δ preds| :
      * `delayed`   : Δ à l'étape de RAPPEL, après D pas nuls -> saillance INTÉGRÉE sur D+1 ticks (il faut
                      avoir LU l'indice PUIS l'avoir PORTÉ dans l'état récurrent).
      * `immediate` : Δ à l'étape d'ENCODE -> saillance instantanée, l'analogue exact de
                      `measure_channel_saliency` (in-world) sur ce banc.
      * `sign_flip` : ⚠️ LA MESURE QUI TRANCHE. Fraction des essais où le SIGNE de la sortie s'inverse avec
                      l'indice, au RAPPEL. Le substrat est CONTRACTIF et la tâche se lit sur `np.sign(preds)`
                      : une AMPLITUDE faible qui inverse SYSTÉMATIQUEMENT le signe est fonctionnellement
                      décisive, là où une grosse amplitude de direction aléatoire ne l'est pas. Mesuré :
                      un champion DEMAND à acc 1.00 a une saillance en amplitude (0.13) NON supérieure à un
                      génome frais (0.10) — même piège que la réfutation de `sep(D)` dans EDR-EVO-002.
                      Échelle (politique déterministe) : 0 = ignore strictement l'indice, 1 = le suit toujours.
    Prédiction : un champion DEMAND (acc 1.00) a `sign_flip` ≈ 1 (il ne peut pas répondre sans lire) ; un
    champion MEMORYLESS (leurre à l'encode) est bas (il a appris à IGNORER l'encode).

    ⚠️ 2026-09-08 (refutation) : le MEME trou que `eval_genome`, sur l'instrument PUBLIE d'EDR-EVO-004.
    Mesure avant correctif : `measure_cue_saliency(trials=0)` rendait
    `{'immediate': nan, 'delayed': nan, 'sign_flip': nan}` -- et `sign_flip` est, la docstring le dit,
    « LA MESURE QUI TRANCHE » et le contre-exemple GELE de la classe E17. Un nan y franchit
    `> 0.95` et `< 0.05` a False dans les deux sens : l'absence de mesure se lit comme « n'a pas lu
    l'indice », l'affirmation NEGATIVE de fond. `K >= I_DIM` et `bit` hors de [0, K[ levaient un
    IndexError depuis le coeur de la boucle. Tout cela LEVE desormais, EN TETE."""
    if (int(trials) <= 0 or int(K) <= 0 or int(K) >= I_DIM or int(D) < 0
            or not 0 <= int(bit) < int(K)):
        raise ValueError(
            f"measure_cue_saliency : argument degenere (trials={trials} K={K} D={D} bit={bit} "
            f"I_DIM={I_DIM}) -- aucun essai apparie mesurable ; les trois sorties vaudraient nan, "
            "et `sign_flip` (LA mesure qui tranche) franchirait a False toute barre de verdict, "
            "ce qui deguiserait une ABSENCE de mesure en « ignore l'indice ».")
    N = genome.num_nodes
    Hh = np.zeros((1, 5, N), np.float32)
    Hp = np.zeros((1, N), np.float32)
    rng = np.random.RandomState(seed)
    d_imm, d_del, flips = [], [], []
    for _ in range(trials):
        other = rng.choice([-1.0, 1.0], size=K).astype(np.float32)   # bits NON perturbés, PARTAGÉS (apparié)
        outs = {}
        for sign in (+1.0, -1.0):
            H = np.zeros((1, N), np.float32)
            obs = np.zeros((1, I_DIM), np.float32)
            obs[0, :K] = other
            obs[0, bit] = sign                                        # seule différence entre les deux runs
            p_enc, H, _, _, _ = recurrent_forward(genome, obs, H, Hh, Hp)
            enc = p_enc[0, :K].copy()
            for _ in range(D):
                _, H, _, _, _ = recurrent_forward(genome, np.zeros((1, I_DIM), np.float32), H, Hh, Hp)
            go = np.zeros((1, I_DIM), np.float32)
            go[0, K] = 1.0
            p_rec, H, _, _, _ = recurrent_forward(genome, go, H, Hh, Hp)
            outs[sign] = (enc, p_rec[0, :K].copy())
        d_imm.append(float(np.mean(np.abs(outs[+1.0][0] - outs[-1.0][0]))))
        d_del.append(float(np.mean(np.abs(outs[+1.0][1] - outs[-1.0][1]))))
        # FONCTIONNEL : le signe de la sortie du bit sondé s'inverse-t-il avec l'indice ? (la tâche lit `sign`)
        flips.append(float(np.sign(outs[+1.0][1][bit]) != np.sign(outs[-1.0][1][bit])))
    return {"immediate": float(np.mean(d_imm)), "delayed": float(np.mean(d_del)),
            "sign_flip": float(np.mean(flips))}


# ============================================================ ÉVOLUTION (unité = seed)

def _fresh_genome(N, rng):
    W = (rng.randn(N, N) * 0.4).astype(np.float32)
    return Genome(W, I_DIM, O_DIM)


def evolve(K, D, seed, demanding=True, generations=25, pop=24, hidden0=3,
           add_node_rate=0.4, eval_trials=32):
    """Neuro-évolution (élitisme + mutation) sous l'objectif de rappel. Renvoie le meilleur génome (cloné)
    pour la sonde de rétention hors-ligne. np.random est semé GLOBALEMENT (apply_mutations tire dessus).

    ⚠️ 2026-09-08 (refutation) : `pop <= 2` est une ABSENCE DE RECHERCHE, pas une recherche pauvre.
    `n_elite = max(2, pop // 4)` vaut 2 des que pop <= 8, donc a pop <= 2 l'elite EST la population
    entiere et la boucle `while len(children) < pop - len(elite)` ne tourne JAMAIS : ZERO mutant est
    cree, a toutes les generations. MESURE (pop=2, gen=8, seed=0) : `acc_history` PLAT
    [0.562]x8 et `final_nodes` = 19.0 = le genome INITIAL, aucun `add_node`. L'operateur de variation
    -- le seul objet de l'experience -- n'existe simplement pas. Or `run_experiment` ACCEPTAIT pop=2
    (garde `pop <= 0`) et publiait alors SUBSTRATE_OR_SEARCH_LIMITED, c'est-a-dire « l'evolution ne
    construit pas la memoire quand elle est recompensee -- verrou = substrat OU RECHERCHE » : le
    FALSIFICATEUR d'EVO-001 grave depuis un bras qui ne POUVAIT pas chercher (classes E1+E2, et le
    biais N°1 du depot : absence -> affirmation NEGATIVE de fond). Barre = `pop >= 3`, la valeur
    EXACTE a laquelle un enfant apparait -- aucun nombre libre, et pop=3 reste accepte (mesure :
    final_nodes 19.33 > 19, la mutation mord)."""
    if (int(pop) < 3 or int(generations) <= 0 or int(eval_trials) <= 0 or int(K) <= 0
            or int(K) >= I_DIM or int(D) < 0 or int(hidden0) < 0):
        raise ValueError(
            f"evolve : argument degenere (pop={pop} generations={generations} "
            f"eval_trials={eval_trials} K={K} D={D} hidden0={hidden0}) -- a pop<3 l'elite "
            f"max(2, pop//4) couvre toute la population et AUCUN mutant n'est cree : ce n'est pas "
            "une recherche pauvre, c'est l'ABSENCE de l'operateur de variation ; ne pas confondre "
            "avec un echec de recherche OBSERVE (c'est exactement ce que tranche le verdict).")
    np.random.seed(seed)
    rng = np.random.RandomState(seed)
    mc = MutationConfig()
    mc.add_node_rate = add_node_rate
    N0 = I_DIM + O_DIM + hidden0
    genomes = [_fresh_genome(N0, rng) for _ in range(pop)]
    n_elite = max(2, pop // 4)
    best_acc, best_g = -1.0, genomes[0].clone()
    hist = []
    for _ in range(generations):
        scores = [eval_genome(g, K, D, demanding, eval_trials, seed) for g in genomes]
        gi = int(np.argmax(scores))
        if scores[gi] >= best_acc:
            best_acc, best_g = scores[gi], genomes[gi].clone()
        hist.append(float(max(scores)))
        order = list(np.argsort(scores)[::-1])
        elite = [genomes[i] for i in order[:n_elite]]
        children = []
        while len(children) < pop - len(elite):
            parent = elite[np.random.randint(len(elite))]
            children.append(apply_mutations(parent, mc))  # clone interne -> renvoie le mutant
        genomes = elite + children
    # ⚠️ 2026-09-08 : `best_acc` part de la SENTINELLE -1.0 et `scores[gi] >= best_acc` vaut False
    # pour TOUT nan -- si aucune generation n'a produit de score comparable, la fonction renvoyait
    # le genome INITIAL non selectionne avec best_acc=-1.0, sans un mot, et l'aval l'evaluait comme
    # un champion. La garde en tete rend le cas inatteignable PAR eval_trials ; celle-ci ferme le
    # MECANISME (nan de toute provenance), et se teste en imposant une mesure nan.
    if not (best_acc >= 0.0):
        raise ValueError(
            f"evolve : aucune generation n'a produit de score COMPARABLE (best_acc reste la "
            f"sentinelle {best_acc}) -- des scores nan traversent `>=` a False ; le champion "
            "renvoye serait le genome INITIAL non selectionne, pas un resultat de recherche.")
    return {"best_acc": best_acc, "best_genome": best_g, "acc_history": hist,
            "final_nodes": float(np.mean([g.num_nodes for g in genomes]))}


# ============================================================ VERDICT (sous cliquet)

def compute_enrichment_verdict(acc_demand, acc_memoryless_xeval, acc_fresh,
                               acc_pos=0.85, acc_floor=0.60, inverse_max=0.75,
                               acc_memoryless_own=None):
    """Tranche EVO-001 sur la CAPACITÉ DE RAPPEL (l'instrument robuste : la grandeur qui agit, pas un proxy).

    Toutes les entrées = accuracy sur le MÊME test DEMANDING tenu à l'écart (une valeur/seed) :
      * acc_demand           : génomes évolués SOUS demande de mémoire.
      * acc_fresh            : génomes NON évolués (plancher — contrôle « pas d'évolution »).
      * acc_memoryless_xeval : génomes évolués sur un objectif qui REND la mémoire inutile (leurre), puis
                               cross-évalués sur le test DEMANDING (contrôle de SPÉCIFICITÉ « pas juste
                               l'évolution en général »). ⚠️ fuite incidente possible : le substrat bâtit
                               la mémoire si facilement qu'elle apparaît parfois NON sélectionnée -> on
                               teste la MÉDIANE, pas chaque seed.

    `acc_memoryless_own` (une valeur/seed, tâche PROPRE du bras MLESS — feedforward, chance 0.5) est le
    contrôle qui rend le contrôle de spécificité LISIBLE, et il ENTRE dans la décision (2026-09-08) :

    ⚠️ POURQUOI (défaut réel, exposé par injection à dose connue). « MLESS-xeval ≈ chance » ne veut dire
    « il n'a pas de MÉMOIRE » que si le bras MLESS a par ailleurs MAÎTRISÉ sa propre tâche. Si son
    évolution a échoué tout court (il ne résout même pas un rappel FEEDFORWARD où la cible est montrée à
    la sonde), son échec en XEVAL a une AUTRE cause que l'absence de mémoire : le contrôle inverse est
    alors un bras qui ne POUVAIT pas réussir (classes E1+E2), et la spécificité n'est pas établie. On
    refuse donc d'affirmer OBJECTIVE_IS_LEVER dans ce cas, et on le NOMME
    (INDETERMINATE_INVERSE_CONTROL_VOID) au lieu de le taire. Barre de maîtrise = `acc_pos`, la MÊME que
    pour DEMAND : aucun nouveau nombre libre.
    `acc_memoryless_own=None` = contrôle NON FOURNI (contrat historique à trois listes, calibré tel quel) :
    la fonction publie alors `inverse_control_learned=None` — un INCONNU explicite, jamais un True — et
    c'est à l'appelant de vérifier son contrôle inverse. `run_experiment` le fournit TOUJOURS.

    Puissance : test de signe apparié DEMAND vs FRESH (garde-fou du dépôt ; n=seeds) — le contraste PROPRE
    (DEMAND maîtrise, FRESH à chance sur tous les seeds). MLESS-xeval borne la spécificité par sa médiane.

    - OBJECTIVE_IS_LEVER : DEMAND maîtrise (médiane > acc_pos) ET bat FRESH (sign_p<0.05) ET la mémoire est
      SPÉCIFIQUE à la demande (médiane MLESS-xeval < inverse_max) -> un objectif qui EXIGE la mémoire produit
      une capacité que ni l'absence d'évolution (FRESH) ni une évolution SANS demande (MLESS) ne produisent.
    - INDETERMINATE_INVERSE_CONTROL_VOID : les trois conditions ci-dessus tiennent, MAIS le bras MLESS n'a
      pas maîtrisé sa PROPRE tâche -> le contrôle de spécificité est VIDE, rien n'est tranché.
    - SUBSTRATE_OR_SEARCH_LIMITED : DEMAND reste au plancher (<= acc_floor) même sous demande -> l'évolution
      ne construit pas la mémoire quand elle est récompensée (verrou = substrat OU recherche). Cette branche
      ne s'appuie PAS sur le contrôle inverse (elle compare DEMAND au plancher) -> il ne l'invalide pas.
      ⚠️ 2026-09-08 : c'est la branche la plus FRAGILE du fait, parce qu'elle IMPUTE l'échec à la recherche.
      Elle n'est lisible que si la recherche a EU LIEU — ce que ce verdict, qui ne voit que des accuracies,
      ne peut pas vérifier lui-même. La condition est portée en amont, par la garde `pop >= 3` d'`evolve`
      et de `run_experiment` : sous cette barre AUCUN mutant n'est créé et le « verrou = recherche » serait
      fabriqué par une ABSENCE de recherche. Tout autre appelant de cette fonction doit tenir la même
      obligation avant de publier cette branche-là.
    - INCONCLUSIVE : sinon (effet présent mais sous un seuil de puissance/positivité/spécificité)."""
    med = statistics.median
    # Matérialisation UNE fois : un itérateur lu deux fois se vide en silence (classe E23, corrigée le
    # 2026-09-07 sur s2_demand.run_s2 et evo_memory_inworld.run_contrast).
    acc_demand, acc_memoryless_xeval, acc_fresh = (
        list(acc_demand), list(acc_memoryless_xeval), list(acc_fresh))
    # ⚠️ 2026-09-08 (refutation) : `n = min(len(acc_demand), len(acc_fresh))` TRONQUAIT EN SILENCE
    # -- la troisieme forme du biais listee par CLAUDE.md (« zip / min / [-1] qui TRONQUE »). MESURE
    # avant correctif : (demand=8, mless=8, fresh=2) publiait n=2 et sign_p=0.50 sur une cohorte de
    # 8 seeds ; (demand=8, mless=2, fresh=8) publiait OBJECTIVE_IS_LEVER avec une SPECIFICITE lue
    # sur 2 valeurs. Les listes sont apparieees SEED A SEED : des longueurs differentes ne sont pas
    # une cohorte plus petite, ce sont des mesures MANQUANTES dont on ne sait pas lesquelles.
    _lg = {"acc_demand": len(acc_demand), "acc_memoryless_xeval": len(acc_memoryless_xeval),
           "acc_fresh": len(acc_fresh)}
    if not all(_lg.values()) or len(set(_lg.values())) > 1:
        raise ValueError(
            f"compute_enrichment_verdict : listes degenerees {_lg} -- les trois sources sont "
            "APPARIEES seed a seed ; une liste vide ou de longueur differente n'est pas une cohorte "
            "plus petite mais une mesure MANQUANTE, et `min(len(...))` la tronquerait en silence.")
    # ⚠️ LE NAN NE DOIT PAS ETRE AVALE (2026-09-08). `nan > acc_pos`, `nan <= acc_floor` et
    # `nan < inverse_max` valent TOUTES False : une mesure manquante ressortait en INCONCLUSIVE avec
    # un `sign_p` significatif (les seeds comptés unanimement DEFAVORABLES) — un verdict de FOND tiré
    # d'une absence. La garde de `run_experiment` ferme la cause CONNUE (budget de mesure nul) ; celle-ci
    # ferme le MECANISME, quelle que soit la provenance du nan.
    _nan = [nom for nom, xs in (("acc_demand", acc_demand),
                                ("acc_memoryless_xeval", acc_memoryless_xeval),
                                ("acc_fresh", acc_fresh))
            if any(x != x for x in xs)]
    if _nan:
        raise ValueError(
            f"compute_enrichment_verdict : NaN dans {_nan} -- mesure ABSENTE, pas mesure nulle ; "
            "toutes les comparaisons du verdict s'evalueraient a False en silence (nan > x est False), "
            "ce qui fabriquerait un verdict de fond depuis une absence.")
    ad, am, af = med(acc_demand), med(acc_memoryless_xeval), med(acc_fresh)
    n = min(len(acc_demand), len(acc_fresh))
    fav = sum(1 for i in range(n) if acc_demand[i] > acc_fresh[i])
    sign_p = _two_sided_sign_p(fav, n)
    masters = ad > acc_pos
    beats_fresh = sign_p < 0.05 and ad > af
    specific = am < inverse_max
    if acc_memoryless_own is None:
        ao, inverse_learned = None, None            # NON FOURNI -> inconnu EXPLICITE, pas un True tacite
    else:
        acc_memoryless_own = list(acc_memoryless_own)
        if not acc_memoryless_own:
            raise ValueError(
                "compute_enrichment_verdict : acc_memoryless_own FOURNI mais VIDE -- argument degenere ; "
                "passer None (contrôle non mesuré) plutôt qu'une liste vide, qui ne se distingue pas "
                "d'un contrôle inverse mesuré et NUL.")
        # ⚠️ 2026-09-08 : depuis que ce controle DECIDE, sa longueur decide aussi. MESURE avant
        # correctif : `acc_memoryless_own=[0.5]` face a 8 seeds faisait basculer OBJECTIVE_IS_LEVER
        # en INDETERMINATE_INVERSE_CONTROL_VOID -- un verdict retourne par UNE valeur non appariee.
        if len(acc_memoryless_own) != len(acc_demand):
            raise ValueError(
                f"compute_enrichment_verdict : acc_memoryless_own a {len(acc_memoryless_own)} "
                f"valeur(s) pour {len(acc_demand)} seed(s) -- argument degenere ; ce controle DECIDE "
                "du verdict depuis 2026-09-08, il doit etre APPARIE a la meme cohorte.")
        if any(x != x for x in acc_memoryless_own):
            raise ValueError(
                "compute_enrichment_verdict : NaN dans acc_memoryless_own -- le controle inverse n'a "
                "pas ete MESURE ; `nan > acc_pos` vaut False, ce qui le declarerait NUL par defaut.")
        ao = med(acc_memoryless_own)
        inverse_learned = bool(ao > acc_pos)
    if masters and beats_fresh and specific:
        verdict = "OBJECTIVE_IS_LEVER"
    elif ad <= acc_floor:
        verdict = "SUBSTRATE_OR_SEARCH_LIMITED"
    else:
        verdict = "INCONCLUSIVE"
    if verdict == "OBJECTIVE_IS_LEVER" and inverse_learned is False:
        verdict = "INDETERMINATE_INVERSE_CONTROL_VOID"
    return {"verdict": verdict, "acc_demand": ad, "acc_memoryless_xeval": am, "acc_fresh": af,
            "n": n, "n_favorable": fav, "sign_p": sign_p,
            "masters": masters, "beats_fresh": beats_fresh, "specific_to_demand": specific,
            "acc_memoryless_own": ao, "inverse_control_learned": inverse_learned}


def _two_sided_sign_p(k, n):
    """p bilatéral d'un test de signe (binomiale 0.5). n petit -> exact."""
    if n == 0:
        return 1.0
    from math import comb
    kk = min(k, n - k)
    tail = sum(comb(n, i) for i in range(kk + 1)) / (2.0 ** n)
    return float(min(1.0, 2.0 * tail))


# ============================================================ ORCHESTRATION

def run_experiment(seeds, K, D, generations, pop, eval_trials=32, sep_pairs=64, oos_trials=400):
    """N'affirme rien que compute_enrichment_verdict ne tranche.

    Instrument PRIMAIRE = capacité de rappel sur un test DEMANDING tenu à l'écart (seed d'éval décalé ->
    pas de fuite train/test). Trois sources de génomes, MÊME test :
      * DEMAND     : évolué demanding=True.
      * MLESS-XEVAL: évolué demanding=False (leurre) puis testé en demanding -> contrôle inverse (~chance).
      * FRESH      : non évolué -> plancher.
    On rapporte aussi l'accuracy du génome MLESS sur SA PROPRE tâche (a-t-il appris ? -> son échec en
    XEVAL est bien « pas de mémoire », pas « rien appris ») — et depuis le 2026-09-08 elle ENTRE dans la
    décision : sans elle, le contrôle de spécificité est VIDE (cf. compute_enrichment_verdict).
    sep(D) : corroboration dynamique SECONDAIRE (on documente qu'elle NE tracke PAS la capacité — le
    signe survit à la contraction)."""
    # GARDE D'ARGUMENTS, EN TETE (2026-09-06). Orchestrateur : il n'entraine pas lui-meme mais
    # AGREGE en verdict -- une cohorte/liste de seeds vide produit une agregation VIDE que l'aval
    # lit comme une mesure (biais negatif systematique). Refus instantane, avant tout appel de run.
    # ⚠️ Corrige le 2026-09-08 : `list(seeds)` dans la garde CONSOMMAIT un iterateur -- la boucle qui
    # suit ne voyait plus rien, les quatre listes restaient vides et `median([])` levait une
    # StatisticsError sans un mot sur la cause. La garde ecrite POUR empecher un negatif fabrique le
    # fabriquait donc elle-meme. On materialise AVANT de tester (meme correctif que
    # `evo_memory_inworld.run_contrast`, 2026-09-07 -- il n'avait pas ete propage ici).
    seeds = list(seeds)
    # ⚠️ Ajoute le 2026-09-08 : `oos_trials` et `sep_pairs` sont les budgets des mesures PUBLIEES ;
    # `eval_trials` n'est que celui de la fitness INTERNE. A oos_trials=0 la vraie `eval_genome` rend
    # `np.mean([])` = nan, les quatre medianes deviennent nan, TOUTES les comparaisons du verdict
    # s'evaluent a False en silence (nan > x est False) et le test de signe publie n=6, p=0.031 depuis
    # ZERO mesure. A sep_pairs=0, `measure_retention_separation` rend 0.0, publie comme « le substrat
    # ne retient RIEN ». Deux absences de mesure transformees en affirmation de FOND. D negatif est le
    # meme trou : `range(D)` est vide, donc le delai disparait et sep(D) rend 1.0 (« retient tout »).
    # ⚠️ Ajoute le 2026-09-08 (refutation) : `pop <= 0` etait la MAUVAISE barre. A pop <= 2,
    # `n_elite = max(2, pop//4)` couvre la population entiere et `evolve` ne cree AUCUN mutant
    # (mesure : acc_history PLAT sur 8 generations, final_nodes = 19.0 = le genome initial). Le
    # verdict alors publie etait SUBSTRATE_OR_SEARCH_LIMITED -- « verrou = substrat OU RECHERCHE » --
    # depuis un bras ou la recherche n'existait pas : le FALSIFICATEUR d'EVO-001 fabrique par une
    # ABSENCE. `K >= I_DIM` est le meme trou en version bruyante (IndexError a huit appels de fond).
    if (not seeds or int(K) <= 0 or int(K) >= I_DIM or int(generations) <= 0 or int(pop) < 3
            or int(eval_trials) <= 0 or int(oos_trials) <= 0 or int(sep_pairs) <= 0 or int(D) < 0):
        raise ValueError(
            f"run_experiment : argument degenere (n_seeds={len(seeds)} K={K} D={D} generations={generations} pop={pop} eval_trials={eval_trials} oos_trials={oos_trials} sep_pairs={sep_pairs}) -- aucune mesure possible ; "
            f"ne pas confondre avec une mesure nulle OBSERVEE (K doit tenir dans I_DIM={I_DIM} ; "
            "pop<3 = AUCUN mutant cree, donc aucune recherche a laquelle imputer un echec).")
    # PSEUDO-REPLICATION (2026-09-08, defaut expose par injection). Le seed determine ENTIEREMENT une
    # ligne : `evolve` fait `np.random.seed(seed)` puis `RandomState(seed)`, le genome frais vient de
    # `RandomState(9000+s)`, l'evaluation de `seed=10000+s` et sep de `seed=s`. Deux occurrences du
    # MEME seed sont donc le MEME calcul (mesure : deux lignes BIT-IDENTIQUES), pas un second
    # replicat -- et elles gonflaient le `n` du test de signe (a 12 seeds dupliques : p=2^-11 depuis
    # UN replicat), alors que EVO-002 declare l'unite de replication = le SEED, pas le genome d'une
    # lignee. On DEDUPLIQUE en le DISANT, et AVANT toute evolution : un doublon ne doit pas non plus
    # couter un run. Ordre de premiere apparition preserve (reproductibilite de la trace).
    uniques = list(dict.fromkeys(seeds))
    n_dup = len(seeds) - len(uniques)
    if n_dup:
        # (message volontairement sans symbole hors-cp1252 : la console Windows par defaut ne sait
        #  pas encoder les emojis et le print leverait UnicodeEncodeError la ou « e » passe.)
        print(f"  ATTENTION run_experiment : {n_dup} seed(s) DUPLIQUE(S) ecarte(s) -- {len(seeds)} fournis, "
              f"{len(uniques)} lignees DISTINCTES retenues {uniques} ; un seed repete est le MEME "
              "tirage (np.random.seed), pas un replicat de plus.")
        seeds = uniques
    acc_dd, acc_mx, acc_ff, acc_mm = [], [], [], []
    sep_d, sep_m, sep_f, nodes_d = [], [], [], []
    for s in seeds:
        rd = evolve(K, D, s, demanding=True, generations=generations, pop=pop, eval_trials=eval_trials)
        rc = evolve(K, D, s, demanding=False, generations=generations, pop=pop, eval_trials=eval_trials)
        fresh = _fresh_genome(I_DIM + O_DIM + 3, np.random.RandomState(9000 + s))
        ev = 10_000 + s                                    # seed d'éval HORS-ÉCHANTILLON
        acc_dd.append(eval_genome(rd["best_genome"], K, D, True, oos_trials, seed=ev))   # DEMAND -> demanding
        acc_mm.append(eval_genome(rc["best_genome"], K, D, False, oos_trials, seed=ev))  # MLESS -> sa tâche
        acc_mx.append(eval_genome(rc["best_genome"], K, D, True, oos_trials, seed=ev))   # MLESS -> demanding (XEVAL)
        acc_ff.append(eval_genome(fresh, K, D, True, oos_trials, seed=ev))               # FRESH -> demanding
        sep_d.append(measure_retention_separation(rd["best_genome"], D, sep_pairs, seed=s))
        sep_m.append(measure_retention_separation(rc["best_genome"], D, sep_pairs, seed=s))
        sep_f.append(measure_retention_separation(fresh, D, sep_pairs, seed=s))
        nodes_d.append(rd["final_nodes"])
        print(f"  seed {s}: DEMAND->dem={acc_dd[-1]:.2f} | MLESS(propre)={acc_mm[-1]:.2f} "
              f"MLESS->dem(xeval)={acc_mx[-1]:.2f} | FRESH->dem={acc_ff[-1]:.2f} | "
              f"sep D/M/F={sep_d[-1]:.2f}/{sep_m[-1]:.2f}/{sep_f[-1]:.2f}")
    # acc_mm ENTRE dans la decision (2026-09-08) : un contrôle inverse qui n'a pas maîtrisé sa PROPRE
    # tâche ne peut pas étayer une affirmation de spécificité (cf. compute_enrichment_verdict).
    v = compute_enrichment_verdict(acc_dd, acc_mx, acc_ff, acc_memoryless_own=acc_mm)
    return {**v,
            "acc_demand_list": acc_dd, "acc_mless_xeval_list": acc_mx, "acc_fresh_list": acc_ff,
            "sep_demand": statistics.median(sep_d), "sep_mless": statistics.median(sep_m),
            "sep_fresh": statistics.median(sep_f), "nodes_demand": statistics.median(nodes_d)}


def main():
    seeds = list(range(int(os.environ.get("EVO2_SEEDS", "8"))))
    K = int(os.environ.get("EVO2_K", "2"))
    D = int(os.environ.get("EVO2_D", "3"))
    gen = int(os.environ.get("EVO2_GEN", "40"))
    pop = int(os.environ.get("EVO2_POP", "32"))
    print(f"EVO-002 : rappel différé K={K} D={D} | {len(seeds)} seeds x {gen} gén x pop {pop} | chance=0.5")
    print("Prédiction (EVO-001 vrai) : DEMAND MAÎTRISE le rappel ; MLESS-xeval ≈ FRESH ≈ chance (mémoire IFF exigée).")
    r = run_experiment(seeds, K, D, gen, pop)
    print("\n=== VERDICT (capacité de rappel sur test DEMANDING) ===")
    print(f"  DEMAND    -> dem   : méd={r['acc_demand']:.2f}")
    print(f"  MLESS     -> dem   : méd={r['acc_memoryless_xeval']:.2f}  (spécificité ; sa propre tâche={r['acc_memoryless_own']:.2f})")
    print(f"  FRESH     -> dem   : méd={r['acc_fresh']:.2f}  (plancher)")
    print(f"  DEMAND>FRESH       : {r['n_favorable']}/{r['n']} seeds (sign_p={r['sign_p']:.4f})")
    print(f"  sep(D) méd (SECONDAIRE, ne tracke PAS la capacité) : DEMAND={r['sep_demand']:.2f} "
          f"MLESS={r['sep_mless']:.2f} FRESH={r['sep_fresh']:.2f}")
    print(f"  -> {r['verdict']}")
    if r["verdict"] == "OBJECTIVE_IS_LEVER":
        print("  L'OBJECTIF est le levier : la mémoire est construite IFF l'objectif l'EXIGE — DEMAND maîtrise,")
        print("  MLESS/FRESH restent à chance sur le test mémoire. La survie n'exigeait rien (EVO-001) -> rien bâti.")
    elif r["verdict"] == "SUBSTRATE_OR_SEARCH_LIMITED":
        print("  DEMAND reste au plancher même sous demande -> verrou = substrat OU recherche (hand-built tranche).")
    elif r["verdict"] == "INDETERMINATE_INVERSE_CONTROL_VOID":
        print("  INDÉTERMINÉ : le bras MLESS n'a pas maîtrisé sa PROPRE tâche (feedforward) — son échec en")
        print("  xeval n'établit donc PAS « pas de mémoire », et la spécificité n'est pas tranchée. RIEN")
        print("  n'est conclu tant que le contrôle inverse n'est pas remonté (régime d'évolution du bras MLESS).")
    else:
        print("  INCONCLUSIF : régime à ajuster (contrôle positif ou puissance).")


if __name__ == "__main__":
    main()
