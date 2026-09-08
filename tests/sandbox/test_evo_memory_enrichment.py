# -*- coding: utf-8 -*-
"""PASSE DE REFUTATION (2026-09-08) de `tools/evo_memory_enrichment.py` -- les instruments PRIS UN A
UN, la ou `test_inj_run_experiment.py` ne tenait que l'ORCHESTRATEUR.

Ce que la passe precedente avait ferme EN AVAL (garde de `run_experiment`, refus du nan dans
`compute_enrichment_verdict`) etait encore OUVERT en tete des fonctions elles-memes : tout appelant
direct -- et `evolve`, qui appelle `eval_genome` `generations x pop` fois -- obtenait une mesure
ABSENTE deguisee en mesure. Les quatre defauts confrontes ici a une reponse connue :

  1. `evolve` a pop<=2 : `n_elite = max(2, pop//4)` couvre toute la population, ZERO mutant est cree
     -- une ABSENCE DE RECHERCHE qui alimentait le verdict `SUBSTRATE_OR_SEARCH_LIMITED`, c'est-a-dire
     « verrou = substrat OU RECHERCHE ». Le falsificateur d'EVO-001 grave depuis un bras incapable.
  2. `eval_genome(trials<=0)` -> `float(np.mean([]))` = nan, en silence.
  3. `measure_cue_saliency(trials<=0)` -> `sign_flip` = nan. C'est l'instrument PUBLIE d'EDR-EVO-004,
     et `sign_flip` est, mot pour mot, « LA MESURE QUI TRANCHE » + le contre-exemple GELE de la
     classe E17. Un nan y franchit `> 0.95` ET `< 0.05` a False : l'absence se lit « ignore l'indice ».
  4. `compute_enrichment_verdict` : `n = min(len(acc_demand), len(acc_fresh))` TRONQUAIT en silence
     (forme (c) du biais listee par CLAUDE.md), et la longueur de `acc_memoryless_own` -- qui DECIDE
     du verdict depuis le 2026-09-08 -- n'etait controlee par rien.

REGLE TENUE PARTOUT (classe E1) : chaque garde ajoutee est testee des DEUX cotes dans le MEME test --
le refus ET le regime minimal LEGITIME qu'elle doit laisser passer. Une garde qu'aucun cas ne peut
franchir n'interdit pas une absence de mesure, elle interdit une mesure.
AUCUN monde n'est construit : le fichier entier est du numpy pur sur des genomes de 19 noeuds.
"""
import numpy as np
import pytest

from src.seed_ai.mutation import Genome
from tools.evo_memory_enrichment import (
    I_DIM, O_DIM, compute_enrichment_verdict, eval_genome, evolve, measure_cue_saliency)

_N = I_DIM + O_DIM + 3


def _g(seed=0, echelle=0.4):
    return Genome((np.random.RandomState(seed).randn(_N, _N) * echelle).astype(np.float32),
                  I_DIM, O_DIM)


# ======================================================================================================
# 1. `eval_genome` : le budget d'essais est garde EN TETE, pas en aval
# ======================================================================================================

def test_eval_genome_REFUSES_a_zero_trial_budget_instead_of_returning_NaN():
    """Reponse connue des DEUX cotes.

    * REFUS : trials=0 et trials<0 rendaient `float(np.mean([]))` = **nan** (mesure du 2026-09-08).
      Le nan n'est pas une accuracy basse : il traverse `>`, `<` et `<=` a False, donc il ressort
      d'un verdict comme un resultat DEFAVORABLE -- une affirmation de FOND tiree d'une absence.
    * ACCEPTATION : trials=1 est un budget PAUVRE mais REEL. Il doit rendre une accuracy dans [0, 1],
      sinon la garde interdit un regime legitime au lieu d'une absence de mesure (classe E1)."""
    g = _g()
    for trials in (0, -1, -32):
        with pytest.raises(ValueError, match="degenere"):
            eval_genome(g, 2, 3, True, trials)
    for trials in (1, 2):
        for demanding in (True, False):
            v = eval_genome(g, 2, 3, demanding, trials, seed=0)
            assert 0.0 <= v <= 1.0 and v == v, (trials, demanding, v)


def test_eval_genome_REFUSES_a_K_that_does_not_FIT_the_observation_but_ACCEPTS_the_largest_that_does():
    """`go[0, K] = 1.0` place le signal « recall » a l'indice K d'un vecteur de taille I_DIM : K doit
    donc tenir STRICTEMENT sous I_DIM. Mesure avant correctif : `eval_genome(g, 8, ...)` levait
    `IndexError: index 8 is out of bounds for axis 1 with size 8` a huit appels de profondeur, et
    `eval_genome(g, 9, ...)` un `ValueError` de broadcast au message sans rapport.

    Cas NEGATIF apparie : K = I_DIM - 1 = 7 est le plus grand K valide, et il DOIT passer."""
    g = _g()
    for K in (0, -2, I_DIM, I_DIM + 1, 64):
        with pytest.raises(ValueError, match="degenere"):
            eval_genome(g, K, 3, True, 8)
    for K in (1, I_DIM - 1):
        assert 0.0 <= eval_genome(g, K, 3, True, 8, seed=0) <= 1.0


def test_eval_genome_ACCEPTS_a_zero_delay_and_REFUSES_a_negative_one():
    """D=0 (aucun delai) est un regime REEL et degenere-mais-legitime : la tache devient un rappel
    immediat. D<0 est le trou INVERSE -- `range(D)` est vide, le delai DISPARAIT sans le dire, et la
    tache mesuree n'est plus celle qu'on croit annoncer."""
    g = _g()
    assert 0.0 <= eval_genome(g, 2, 0, True, 8, seed=0) <= 1.0
    for D in (-1, -3):
        with pytest.raises(ValueError, match="degenere"):
            eval_genome(g, 2, D, True, 8)


# ======================================================================================================
# 2. `measure_cue_saliency` (instrument PUBLIE d'EDR-EVO-004, contre-exemple gele de la classe E17)
# ======================================================================================================

def test_cue_saliency_REFUSES_a_zero_trial_budget_instead_of_a_NaN_sign_flip():
    """Le MEME trou que `eval_genome`, mais sur la grandeur qui TRANCHE.

    Mesure avant correctif : `measure_cue_saliency(g, 2, 3, trials=0)` rendait
    `{'immediate': nan, 'delayed': nan, 'sign_flip': nan}`. La calibration E17 gelee lit
    `sign_flip > 0.95` (lecteur) et `sign_flip < 0.05` (non-lecteur) : un nan echoue les DEUX, donc
    l'absence de mesure se lit exactement comme « n'a pas lu l'indice » -- l'affirmation NEGATIVE.

    Cas NEGATIF apparie : trials=1 rend TROIS nombres finis, dans les echelles annoncees par la
    docstring (`sign_flip` dans [0, 1], amplitudes >= 0)."""
    g = _g()
    for trials in (0, -1):
        with pytest.raises(ValueError, match="degenere"):
            measure_cue_saliency(g, 2, 3, trials=trials)
    out = measure_cue_saliency(g, 2, 3, trials=1, seed=0)
    assert set(out) == {"immediate", "delayed", "sign_flip"}
    assert all(v == v for v in out.values()), f"une sortie est nan : {out}"
    assert 0.0 <= out["sign_flip"] <= 1.0 and out["immediate"] >= 0.0 and out["delayed"] >= 0.0


def test_cue_saliency_REFUSES_a_bit_OUTSIDE_the_cue_it_claims_to_perturb():
    """`bit` designe le bit d'indice PERTURBE : il doit tomber dans [0, K[. Mesure avant correctif :
    `bit >= K` levait un IndexError depuis le coeur de la boucle, apres avoir simule tous les essais.
    Cas NEGATIF apparie : bit = K - 1 est le plus grand indice valide, et il DOIT passer."""
    g = _g()
    for bit in (-1, 2, 5):
        with pytest.raises(ValueError, match="degenere"):
            measure_cue_saliency(g, 2, 3, trials=4, bit=bit)
    for bit in (0, 1):
        assert 0.0 <= measure_cue_saliency(g, 2, 3, trials=4, bit=bit)["sign_flip"] <= 1.0


def test_cue_saliency_guards_are_placed_BEFORE_any_simulation():
    """Un refus doit etre INSTANTANE : la garde est en tete, avant la moindre construction. On mesure
    le refus sur un budget qui, s'il etait accepte, prendrait un temps NON nul (trials=100000)."""
    import time
    g = _g()
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        measure_cue_saliency(g, I_DIM, 3, trials=100_000)
    assert time.time() - t0 < 0.5, "refus trop lent : la garde n'est pas EN TETE"


# ======================================================================================================
# 3. `evolve` : la RECHERCHE existe-t-elle ? (le defaut dominant de cette passe)
# ======================================================================================================

def test_evolve_REFUSES_a_population_with_NO_variation_operator_and_ACCEPTS_the_smallest_that_has_one():
    """Reponse connue, calculee et MESUREE : le nombre d'enfants par generation est
    `pop - max(2, pop // 4)`, donc 0 pour pop in {1, 2} et 1 pour pop = 3.

    * REFUS a pop <= 2 : ce n'est pas une recherche pauvre, c'est l'ABSENCE de l'operateur de
      variation -- et le verdict qu'elle alimentait (`SUBSTRATE_OR_SEARCH_LIMITED`) affirme
      precisement que la RECHERCHE a echoue.
    * ACCEPTATION a pop = 3, avec la PREUVE que la mutation mord : `final_nodes` depasse la taille
      initiale (19 = I_DIM + O_DIM + hidden0), donc `add_node` s'est applique. Sans cette moitie, la
      garde pourrait avoir rendu le falsificateur d'EVO-001 inatteignable."""
    for pop in (2, 1, 0, -5):
        with pytest.raises(ValueError, match="degenere"):
            evolve(K=2, D=3, seed=0, generations=4, pop=pop, eval_trials=4)
    r = evolve(K=2, D=3, seed=1, generations=6, pop=3, eval_trials=8)
    assert r["final_nodes"] > float(I_DIM + O_DIM + 3), (
        f"pop=3 doit MUTER : final_nodes={r['final_nodes']} (initial {I_DIM + O_DIM + 3})")
    assert 0.0 <= r["best_acc"] <= 1.0 and len(r["acc_history"]) == 6


def test_evolve_REFUSES_the_other_degenerate_budgets_and_ACCEPTS_their_minimum():
    """Les autres termes de la meme garde, chacun avec son minimum LEGITIME : generations=1 (une
    seule ronde de selection est un regime reel : la recherche aleatoire sur `pop` tirages),
    eval_trials=1, D=0, hidden0=0 (un genome sans noeud cache, la memoire vivant sur les sorties)."""
    for kw in (dict(generations=0), dict(generations=-1), dict(eval_trials=0), dict(eval_trials=-2),
               dict(D=-1), dict(K=0), dict(K=I_DIM), dict(hidden0=-1)):
        plein = dict(K=2, D=3, seed=0, generations=4, pop=6, eval_trials=4)
        plein.update(kw)
        with pytest.raises(ValueError, match="degenere"):
            evolve(**plein)
    for kw in (dict(generations=1), dict(eval_trials=1), dict(D=0), dict(hidden0=0),
               dict(K=I_DIM - 1)):
        plein = dict(K=2, D=3, seed=0, generations=3, pop=4, eval_trials=4)
        plein.update(kw)
        r = evolve(**plein)
        assert 0.0 <= r["best_acc"] <= 1.0, (kw, r["best_acc"])


def test_evolve_REFUSES_to_return_the_INITIAL_genome_when_every_score_is_a_NaN(monkeypatch):
    """`best_acc` part de la SENTINELLE -1.0 et `scores[gi] >= best_acc` vaut False pour TOUT nan :
    si aucune generation n'a produit de score comparable, `evolve` renvoyait le genome INITIAL non
    selectionne avec `best_acc = -1.0`, sans un mot, et l'aval l'evaluait comme un champion.
    Mesure avant correctif (mesure remplacee par nan) : `best_acc = -1.0`, `acc_history = [nan]*5`.

    La garde en tete rend ce cas inatteignable PAR `eval_trials` ; ce test ferme le MECANISME, quelle
    que soit la provenance du nan -- et il est teste des DEUX cotes : une mesure VALIDE, meme
    constante et basse, doit toujours produire un champion."""
    import tools.evo_memory_enrichment as M

    monkeypatch.setattr(M, "eval_genome", lambda *a, **k: float("nan"))
    with pytest.raises(ValueError, match="sentinelle"):
        M.evolve(K=2, D=3, seed=0, generations=5, pop=8, eval_trials=4)

    monkeypatch.setattr(M, "eval_genome", lambda *a, **k: 0.0)
    r = M.evolve(K=2, D=3, seed=0, generations=5, pop=8, eval_trials=4)
    assert r["best_acc"] == 0.0, "une mesure VALIDE mais nulle doit produire un champion, pas un refus"


# ======================================================================================================
# 4. `compute_enrichment_verdict` : l'appariement des listes n'est plus TRONQUE en silence
# ======================================================================================================

def test_verdict_REFUSES_lists_of_MISMATCHED_length_instead_of_truncating_with_min():
    """`n = min(len(acc_demand), len(acc_fresh))` est la forme (c) du biais listee par CLAUDE.md
    (« zip / min / [-1] qui TRONQUE en silence »). DEUX mesures avant correctif, sur une cohorte de
    8 seeds :
      * (demand=8, mless=8, fresh=2) -> n=2, sign_p=0.50 publie pour 8 lignees ;
      * (demand=8, mless=2, fresh=8) -> OBJECTIVE_IS_LEVER, la SPECIFICITE lue sur 2 valeurs.
    Les trois sources sont APPARIEES seed a seed : des longueurs differentes ne sont pas une cohorte
    plus petite, ce sont des mesures manquantes dont on ne sait pas lesquelles.

    Cas NEGATIF apparie : a longueurs EGALES, y compris n=1, la fonction tranche normalement."""
    d8, m8, f8 = [1.0] * 8, [0.5] * 8, [0.5] * 8
    for kw in (dict(acc_fresh=[0.5] * 2), dict(acc_memoryless_xeval=[0.5] * 2),
               dict(acc_demand=[1.0] * 7), dict(acc_demand=[]), dict(acc_fresh=[]),
               dict(acc_memoryless_xeval=[])):
        args = dict(acc_demand=d8, acc_memoryless_xeval=m8, acc_fresh=f8)
        args.update(kw)
        with pytest.raises(ValueError, match="degenerees"):
            compute_enrichment_verdict(**args)

    assert compute_enrichment_verdict(d8, m8, f8)["n"] == 8
    un = compute_enrichment_verdict([1.0], [0.5], [0.5])
    assert un["n"] == 1 and un["verdict"] != "OBJECTIVE_IS_LEVER"     # 1 seed : aucune puissance


def test_verdict_REFUSES_an_inverse_control_NOT_paired_to_the_cohort_it_decides_for():
    """Depuis que `acc_memoryless_own` DECIDE (verrou INDETERMINATE_INVERSE_CONTROL_VOID), sa
    longueur decide aussi -- et rien ne la controlait. Mesure avant correctif :
    `acc_memoryless_own=[0.5]` face a 8 seeds faisait basculer OBJECTIVE_IS_LEVER en
    INDETERMINATE_INVERSE_CONTROL_VOID : un verdict retourne par UNE valeur non appariee.

    Cas NEGATIF apparie, des DEUX cotes de la decision : a longueur EGALE, le verrou sait encore se
    declencher (own bas) ET ne pas se declencher (own haut). Une garde de longueur qui aurait fige
    le verrou dans un seul etat serait pire que le defaut (classe E1)."""
    d8, m8, f8 = [1.0] * 8, [0.5] * 8, [0.5] * 8
    for own in ([0.5], [0.5] * 7, [0.5] * 9, [0.95] * 2):
        with pytest.raises(ValueError, match="degenere"):
            compute_enrichment_verdict(d8, m8, f8, acc_memoryless_own=own)

    haut = compute_enrichment_verdict(d8, m8, f8, acc_memoryless_own=[0.95] * 8)
    bas = compute_enrichment_verdict(d8, m8, f8, acc_memoryless_own=[0.50] * 8)
    assert haut["verdict"] == "OBJECTIVE_IS_LEVER" and haut["inverse_control_learned"] is True
    assert bas["verdict"] == "INDETERMINATE_INVERSE_CONTROL_VOID"
    assert bas["inverse_control_learned"] is False


def test_the_published_EVO_002_record_still_reads_the_SAME_verdict():
    """NON-REGRESSION du record PUBLIE (EDR-EVO-002), rejoue depuis ses valeurs gravees : DEMAND 1.00
    sur 8/8, FRESH mediane 0.495, MLESS-xeval mediane ~0.474 avec DEUX fuites incidentes a 1.00,
    MLESS sur sa propre tache 1.00.

    Les correctifs du 2026-09-08 font ENTRER `acc_memoryless_own` dans la decision : c'est un
    changement de contrat, donc il faut PROUVER qu'il ne retourne pas ce qui est deja publie.
    Verifie : verdict, sign_p et les trois medianes sont INCHANGES, et le nouveau drapeau confirme
    que le controle inverse avait bien maitrise sa propre tache."""
    dem = [1.0] * 8
    fresh = [0.24, 0.44, 0.48, 0.49, 0.50, 0.55, 0.62, 0.76]
    mless = [0.30, 0.40, 0.45, 0.47, 0.48, 0.50, 1.00, 1.00]
    ancien = compute_enrichment_verdict(dem, mless, fresh)                       # contrat historique
    nouveau = compute_enrichment_verdict(dem, mless, fresh, acc_memoryless_own=[1.0] * 8)
    for cle in ("verdict", "acc_demand", "acc_memoryless_xeval", "acc_fresh", "n", "n_favorable",
                "sign_p", "masters", "beats_fresh", "specific_to_demand"):
        assert ancien[cle] == nouveau[cle], (cle, ancien[cle], nouveau[cle])
    assert nouveau["verdict"] == "OBJECTIVE_IS_LEVER"
    assert nouveau["sign_p"] == pytest.approx(2.0 / 256.0, rel=1e-12)            # 8/8 -> 0.0078
    assert nouveau["acc_fresh"] == pytest.approx(0.495)
    assert nouveau["inverse_control_learned"] is True
    assert ancien["inverse_control_learned"] is None                             # NON FOURNI != True


# ======================================================================================================
# 5. La PREMISSE de la deduplication (elle n'avait jamais ete testee, seulement son EFFET)
# ======================================================================================================

def test_a_seed_determines_its_WHOLE_row_independently_of_its_NEIGHBOURS():
    """La deduplication des seeds (correctif du 2026-09-08) n'est LEGITIME que si un seed determine
    ENTIEREMENT sa ligne. Si deux occurrences du meme seed pouvaient differer, dedupliquer
    DETRUIRAIT des replicats REELS -- un correctif pire que le defaut. La passe precedente avait
    teste l'EFFET du dedoublonnage (le `n` publie, l'ordre, l'avertissement) mais jamais sa PREMISSE.

    Reponse connue, MESUREE sur le VRAI code (aucun monde, parametres minuscules) : la ligne du seed
    7 est BIT-IDENTIQUE qu'il soit seul, deuxieme d'une cohorte, ou aborde dans l'ordre inverse.
    Mecanisme : `evolve` fait `np.random.seed(seed)` en tete de chaque bras, donc le flux global est
    REMIS A ZERO a chaque ligne et rien ne fuit d'un seed a l'autre ; le genome frais, l'evaluation
    et sep tirent chacun d'un `RandomState` derive du seed."""
    kw = dict(K=2, D=1, generations=2, pop=4, eval_trials=2, sep_pairs=2, oos_trials=8)
    from tools.evo_memory_enrichment import run_experiment

    cles = ("acc_demand_list", "acc_mless_xeval_list", "acc_fresh_list")
    seul = run_experiment([7], **kw)
    milieu = run_experiment([9, 7, 5], **kw)
    inverse = run_experiment([5, 7, 9], **kw)
    for c in cles:
        assert seul[c][0] == milieu[c][1] == inverse[c][1], (
            f"{c} : la ligne du seed 7 depend de ses voisins -> dedupliquer detruirait un replicat "
            f"REEL (seul={seul[c][0]} milieu={milieu[c][1]} inverse={inverse[c][1]})")
    # ...et le contraire pour des seeds DIFFERENTS : sinon le test ci-dessus passerait sur un banc mort.
    assert milieu["acc_demand_list"][0] != milieu["acc_demand_list"][1] or \
        milieu["acc_fresh_list"][0] != milieu["acc_fresh_list"][1], (
        "deux seeds DISTINCTS rendent la meme ligne : le seed ne pilote rien")
