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
    measure_convergence (deux points fixes DISTINCTS gardent sep>0 = retenus)."""
    N = genome.num_nodes
    I = genome.num_inputs
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
    return float(statistics.median(ratios)) if ratios else 0.0


# ============================================================ FITNESS (tâche de rappel)

def eval_genome(genome, K, D, demanding=True, trials=32, seed=0):
    """Rappel parallèle de K bits après délai D (chance=0.5). La CIBLE à restituer est toujours `target`.

    - demanding=True  : la cible est ENCODÉE (t=0) puis CACHÉE à la sonde -> il faut la MÉMOIRE.
    - demanding=False : à l'encode on montre un LEURRE aléatoire (à ignorer), et la cible n'apparaît qu'à la
      SONDE -> résoluble en feedforward, et tenir l'encode est CONTRE-productif (leurre != cible). C'est la
      vraie manipulation INVERSE : le contrôle ne se contente pas de « ne pas exiger » la mémoire, il la
      REND INUTILE, sinon l'évolution la construit quand même (tenir 2 bits/3 ticks est facile).

    Un génome évolué en memoryless, CROSS-ÉVALUÉ en demanding, lit l'entrée de sonde (=0) -> ~chance : il
    n'a AUCUNE mémoire. C'est ce contraste (et non sep) qui tranche EVO-001."""
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
    champion MEMORYLESS (leurre à l'encode) est bas (il a appris à IGNORER l'encode)."""
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
    pour la sonde de rétention hors-ligne. np.random est semé GLOBALEMENT (apply_mutations tire dessus)."""
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
    return {"best_acc": best_acc, "best_genome": best_g, "acc_history": hist,
            "final_nodes": float(np.mean([g.num_nodes for g in genomes]))}


# ============================================================ VERDICT (sous cliquet)

def compute_enrichment_verdict(acc_demand, acc_memoryless_xeval, acc_fresh,
                               acc_pos=0.85, acc_floor=0.60, inverse_max=0.75):
    """Tranche EVO-001 sur la CAPACITÉ DE RAPPEL (l'instrument robuste : la grandeur qui agit, pas un proxy).

    Toutes les entrées = accuracy sur le MÊME test DEMANDING tenu à l'écart (une valeur/seed) :
      * acc_demand           : génomes évolués SOUS demande de mémoire.
      * acc_fresh            : génomes NON évolués (plancher — contrôle « pas d'évolution »).
      * acc_memoryless_xeval : génomes évolués sur un objectif qui REND la mémoire inutile (leurre), puis
                               cross-évalués sur le test DEMANDING (contrôle de SPÉCIFICITÉ « pas juste
                               l'évolution en général »). ⚠️ fuite incidente possible : le substrat bâtit
                               la mémoire si facilement qu'elle apparaît parfois NON sélectionnée -> on
                               teste la MÉDIANE, pas chaque seed.

    Puissance : test de signe apparié DEMAND vs FRESH (garde-fou du dépôt ; n=seeds) — le contraste PROPRE
    (DEMAND maîtrise, FRESH à chance sur tous les seeds). MLESS-xeval borne la spécificité par sa médiane.

    - OBJECTIVE_IS_LEVER : DEMAND maîtrise (médiane > acc_pos) ET bat FRESH (sign_p<0.05) ET la mémoire est
      SPÉCIFIQUE à la demande (médiane MLESS-xeval < inverse_max) -> un objectif qui EXIGE la mémoire produit
      une capacité que ni l'absence d'évolution (FRESH) ni une évolution SANS demande (MLESS) ne produisent.
    - SUBSTRATE_OR_SEARCH_LIMITED : DEMAND reste au plancher (<= acc_floor) même sous demande -> l'évolution
      ne construit pas la mémoire quand elle est récompensée (verrou = substrat OU recherche).
    - INCONCLUSIVE : sinon (effet présent mais sous un seuil de puissance/positivité/spécificité)."""
    med = statistics.median
    ad, am, af = med(acc_demand), med(acc_memoryless_xeval), med(acc_fresh)
    n = min(len(acc_demand), len(acc_fresh))
    fav = sum(1 for i in range(n) if acc_demand[i] > acc_fresh[i])
    sign_p = _two_sided_sign_p(fav, n)
    masters = ad > acc_pos
    beats_fresh = sign_p < 0.05 and ad > af
    specific = am < inverse_max
    if masters and beats_fresh and specific:
        verdict = "OBJECTIVE_IS_LEVER"
    elif ad <= acc_floor:
        verdict = "SUBSTRATE_OR_SEARCH_LIMITED"
    else:
        verdict = "INCONCLUSIVE"
    return {"verdict": verdict, "acc_demand": ad, "acc_memoryless_xeval": am, "acc_fresh": af,
            "n": n, "n_favorable": fav, "sign_p": sign_p,
            "masters": masters, "beats_fresh": beats_fresh, "specific_to_demand": specific}


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
    XEVAL est bien « pas de mémoire », pas « rien appris »). sep(D) : corroboration dynamique SECONDAIRE
    (on documente qu'elle NE tracke PAS la capacité — le signe survit à la contraction)."""
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
    v = compute_enrichment_verdict(acc_dd, acc_mx, acc_ff)
    return {**v, "acc_memoryless_own": statistics.median(acc_mm),
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
    else:
        print("  INCONCLUSIF : régime à ajuster (contrôle positif ou puissance).")


if __name__ == "__main__":
    main()
