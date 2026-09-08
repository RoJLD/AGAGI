# -*- coding: utf-8 -*-
# P2.44 (2026-09-08) -- INJECTION A DOSE CONNUE, suite de `test_orchestrator_injection.py` (les 5
# prioritaires, la veille). Meme technique : monkeypatch de l'attribut de MODULE appele, cellules
# imposees a DOSE CONNUE, verdict exige en forme close, branches NEGATIVES comprises. AUCUN monde
# construit -> cout nul. Controle E1 PAR MUTATION effectue : l'orchestrateur rendu aveugle a la dose
# fait MOURIR les tests passants. 2026-09-08, apres REFUTATION : il ne reste AUCUN xfail --
# les quatre defauts exposes sont corriges, et leurs tests sont devenus des NON-REGRESSIONS.
# -*- coding: utf-8 -*-
"""INJ-6 (2026-09-08) -- calibration par INJECTION A DOSE CONNUE de
`tools/evo_memory_enrichment.py::run_experiment` (EDR-EVO-002, le record qui TRANCHE EVO-001 :
« l'OBJECTIF est le levier »).

`run_experiment` est un ORCHESTRATEUR : il ne fait evoluer ni ne mesure lui-meme, il APPELLE
`evolve`, `_fresh_genome`, `eval_genome` et `measure_retention_separation` (quatre attributs de
MODULE, resolus par nom global au moment de l'appel -> l'attribut a monkeypatcher est
`tools.evo_memory_enrichment.<nom>`), puis AGREGE en verdict via `compute_enrichment_verdict`.

Ce qui etait deja calibre :
  * `compute_enrichment_verdict` en PUR (3 cas, tests/sandbox/test_instrument_calibration.py:1567+) ;
  * `measure_retention_separation` par PREDICTION ((1-delta)^D, meme fichier:1516+) ;
  * la GARDE D'ARGUMENTS de `run_experiment` (declaration "empty-cohort:raises",
    "guard-before-world").
Ce qui n'etait calibre par RIEN, et que ce fichier confronte a une reponse connue : la couche qui
transforme des mesures en affirmation -- APPARIEMENT des trois sources (DEMAND / MLESS-XEVAL /
FRESH) au sein d'un MEME seed, CABLAGE de la tache demandee a chaque bras, graine d'evaluation
HORS-ECHANTILLON, UNITE DE REPLICATION (le seed), et les TROIS branches de verdict.

TECHNIQUE. Les cellules sont imposees a dose connue et le verdict est calculable EN FORME CLOSE
(medianes imposees, test de signe binomial exact). AUCUN monde n'est construit, aucune evolution
n'est lancee : le fichier entier s'execute en une fraction de seconde. Les genomes factices sont
de VRAIS `Genome` etiquetes par (bras, seed) -- c'est cette etiquette qui rend un croisement de
bras VISIBLE, la ou deux tableaux de flottants seraient indiscernables.

CONTROLE E1 PAR MUTATION (2026-09-08), DEUX mutations temporaires, source restauree ensuite :
  * M1 -- orchestrateur AVEUGLE A LA DOSE : les quatre `eval_genome` (:295-298) recables sur le
    MEME genome (`rd`), la MEME tache (`True`) et une graine EN ECHANTILLON (`seed=s`).
    -> 6/6 des tests de dose MEURENT (seul survit le test de LOCALISATION de la garde, qui ne lit
    aucune dose -- il est hors du perimetre de M1 par construction).
  * M2 -- garde d'arguments NEUTRALISEE (`if False and (...)` en :284).
    -> 1/1 : le test de localisation meurt aussi (et `seeds=[]` remonte alors « no median for
    empty data », ce que la garde existe precisement pour eviter).
Total : 7/7 des tests passants meurent sous la mutation qui les concerne. Un test qui survit a la
mutation ne mesure pas ce qu'il croit.

2026-09-08, PASSE DE REFUTATION. Les quatre `xfail(strict=True)` de la section 5 avaient ete
ECRITS pour tomber « d'eux-memes le jour ou le defaut sera repare » -- et le jour est venu SANS que
le marqueur soit retire : la suite rendait `4 failed, 16 passed`, quatre tests ROUGES derriere un
correctif pourtant valide. Le marqueur est parti, les tests sont devenus des NON-REGRESSIONS, et le
texte forensique de chaque defaut est conserve mot pour mot dans `_DEFAUT_n_CORRIGE_LE_2026_09_08`.
La meme passe a trouve, par sondes propres, cinq defauts DE PLUS (dont un verdict de fond fabrique
par une ABSENCE DE RECHERCHE) : cf. la section 7 et `tests/sandbox/test_evo_memory_enrichment.py`.
"""
import numpy as np
import pytest


# ======================================================================================================
# Harnais d'injection
# ======================================================================================================

I_ATT, O_ATT = 8, 8              # tools/evo_memory_enrichment.py:57 (I_DIM, O_DIM)
_N_TINY = I_ATT + O_ATT + 3      # la taille que `run_experiment` demande au genome FRAIS (:293)
_OFFSET_EVAL = 10_000            # graine d'eval HORS-ECHANTILLON (:294)
_OFFSET_FRESH = 9_000            # graine du genome FRAIS         (:293)


def _inj6_genome(bras, seed):
    """Genome REEL (donc consommable par la VRAIE `measure_retention_separation`) mais ETIQUETE par
    (bras, seed). L'etiquette est le seul moyen de voir un croisement : `run_experiment` manipule
    trois genomes indiscernables l'un de l'autre, et les intervertir n'aurait AUCUNE consequence
    visible dans les chiffres publies -- seulement dans leur signification."""
    from src.seed_ai.mutation import Genome
    g = Genome(np.zeros((_N_TINY, _N_TINY), np.float32), I_ATT, O_ATT)
    g.tag = (bras, int(seed))
    return g


def _inj6_dose(demand, mless_xeval, fresh, mless_own=0.95):
    """Dose imposee par (bras, tache). Chaque valeur est soit un scalaire (meme dose a tous les
    seeds), soit une liste INDEXEE PAR SEED (les tests utilisent seeds = 0..n-1).

    Les QUATRE cellules sont distinctes par construction :
      DEMAND -> tache demanding        (l'instrument primaire)
      MLESS  -> tache demanding        (XEVAL : le controle de SPECIFICITE)
      MLESS  -> sa PROPRE tache        (le controle « a-t-il seulement appris ? »)
      FRESH  -> tache demanding        (le plancher)
    Un croisement de deux d'entre elles change le SENS du verdict sans rien casser."""
    def _v(x, seed):
        return float(x[seed]) if isinstance(x, (list, tuple)) else float(x)

    def _f(bras, seed, demanding):
        if bras == "DEMAND":
            return _v(demand, seed)
        if bras == "FRESH":
            return _v(fresh, seed)
        return _v(mless_xeval, seed) if demanding else _v(mless_own, seed)
    return _f


def _inj6_injecte(monkeypatch, dose_eval, dose_sep=None, nodes=None, sep_reelle=False,
                  bombe=False):
    """Remplace, DANS `tools.evo_memory_enrichment`, les QUATRE attributs de module que
    `run_experiment` resout par nom global. Renvoie (module, journaux).

    `dose_sep(bras, seed)` : dose de l'instrument SECONDAIRE. `sep_reelle=True` laisse la VRAIE
    `measure_retention_separation` en place (utile pour le cas `sep_pairs=0`, qui rend
    instantanement). `bombe=True` : toutes les fonctions explosent -- sert a prouver OU la garde
    d'arguments est posee, pas seulement QU'elle leve."""
    import tools.evo_memory_enrichment as M
    J = {"evolve": [], "eval": [], "sep": [], "fresh": []}

    def _explose(*a, **k):                       # pragma: no cover - ne doit jamais etre atteint
        raise AssertionError(
            "une mesure a ete lancee APRES un argument degenere : la garde n'est pas EN TETE")

    def _evolve(K, D, seed, demanding=True, generations=25, pop=24, hidden0=3,
                add_node_rate=0.4, eval_trials=32):
        bras = "DEMAND" if demanding else "MLESS"
        J["evolve"].append({"bras": bras, "K": K, "D": D, "seed": seed, "generations": generations,
                            "pop": pop, "hidden0": hidden0, "add_node_rate": add_node_rate,
                            "eval_trials": eval_trials})
        n = float(nodes(bras, seed)) if nodes is not None else (30.0 + seed if bras == "DEMAND"
                                                                else 99.0)
        acc = dose_eval(bras, seed, bras == "DEMAND")
        # TOUTES les cles que la VRAIE `evolve` renvoie (:211) -- pas seulement celles lues
        # aujourd'hui : si l'orchestrateur se met a en lire une autre, ce test ne doit pas mentir.
        return {"best_acc": float(acc), "best_genome": _inj6_genome(bras, seed),
                "acc_history": [float(acc)] * int(generations), "final_nodes": n}

    def _eval(genome, K, D, demanding=True, trials=32, seed=0):
        bras, s = genome.tag
        J["eval"].append({"bras": bras, "seed_genome": s, "K": K, "D": D,
                          "demanding": bool(demanding), "trials": trials, "seed": seed})
        return float(dose_eval(bras, s, bool(demanding)))

    def _sep(genome, D, n_pairs=64, seed=0, eps=1e-9):
        bras, s = genome.tag
        J["sep"].append({"bras": bras, "seed_genome": s, "D": D, "n_pairs": n_pairs, "seed": seed})
        return float(dose_sep(bras, s)) if dose_sep is not None else 0.5

    def _fresh(N, rng):
        # MT19937 : `RandomState(k).get_state()[1][0] == k`. C'est le SEUL canal par lequel la
        # graine du genome frais voyage -- on la relit donc a la source plutot que de la supposer.
        graine = int(rng.get_state()[1][0])
        J["fresh"].append({"N": N, "graine": graine})
        return _inj6_genome("FRESH", graine - _OFFSET_FRESH)

    monkeypatch.setattr(M, "evolve", _explose if bombe else _evolve)
    monkeypatch.setattr(M, "eval_genome", _explose if bombe else _eval)
    monkeypatch.setattr(M, "_fresh_genome", _explose if bombe else _fresh)
    if bombe:
        monkeypatch.setattr(M, "measure_retention_separation", _explose)
    elif not sep_reelle:
        monkeypatch.setattr(M, "measure_retention_separation", _sep)
    return M, J


def _inj6_run(monkeypatch, dose_eval, n_seeds=6, K=2, D=3, generations=5, pop=8,
              eval_trials=4, sep_pairs=3, oos_trials=7, dose_sep=None, nodes=None,
              seeds=None, sep_reelle=False):
    M, J = _inj6_injecte(monkeypatch, dose_eval, dose_sep=dose_sep, nodes=nodes,
                         sep_reelle=sep_reelle)
    graines = list(range(n_seeds)) if seeds is None else seeds
    rep = M.run_experiment(graines, K, D, generations, pop, eval_trials=eval_trials,
                           sep_pairs=sep_pairs, oos_trials=oos_trials)
    return rep, J


# ======================================================================================================
# 1. LES BRANCHES DE VERDICT, a dose imposee -- c'est LA que se decide ce qui est publie
# ======================================================================================================

def test_run_experiment_READS_the_dose_of_recall_it_claims(monkeypatch):
    """Reponse connue x4, une par lecture que le code peut rendre, en FORME CLOSE a 6 seeds.

    Le test de signe est exact : a n=6 unanime, p = 2 x C(6,0)/2^6 = 2/64 = 0.03125 (< 0.05).

    * OBJECTIVE_IS_LEVER : DEMAND 1.00 (> acc_pos 0.85), FRESH 0.50 (6/6 favorables),
      MLESS-XEVAL 0.50 (< inverse_max 0.75) -> les TROIS conditions tiennent.
    * SUBSTRATE_OR_SEARCH_LIMITED : DEMAND 0.55 <= acc_floor 0.60 -> le FALSIFICATEUR d'EVO-001.
      Sans cette branche, l'instrument n'aurait qu'une seule issue (classe E1).
    * INCONCLUSIVE par FUITE : DEMAND maitrise et bat FRESH, mais MLESS-XEVAL 0.90 >= 0.75 -> la
      memoire n'est PAS specifique a la demande. C'est la branche qui interdit de publier « le
      levier est l'objectif » quand une evolution SANS demande construit la meme memoire.
    * INCONCLUSIVE par NON-MAITRISE : DEMAND 0.70, strictement entre le plancher 0.60 et la barre
      de positivite 0.85 -> effet reel mais insuffisant.

    Chaque cas exige AUSSI les trois medianes separement : c'est ce qui rend le test mortel a la
    mutation « les quatre bras lisent la meme cellule » (deux verdicts sur quatre y restent
    inchanges, seules les medianes les distinguent)."""
    cas = (
        ("OBJECTIVE_IS_LEVER", _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50),
         dict(masters=True, beats_fresh=True, specific_to_demand=True)),
        ("SUBSTRATE_OR_SEARCH_LIMITED", _inj6_dose(demand=0.55, mless_xeval=0.50, fresh=0.50),
         dict(masters=False, beats_fresh=True, specific_to_demand=True)),
        ("INCONCLUSIVE", _inj6_dose(demand=1.00, mless_xeval=0.90, fresh=0.50),
         dict(masters=True, beats_fresh=True, specific_to_demand=False)),
        ("INCONCLUSIVE", _inj6_dose(demand=0.70, mless_xeval=0.50, fresh=0.50),
         dict(masters=False, beats_fresh=True, specific_to_demand=True)),
    )
    for attendu, dose, drapeaux in cas:
        rep, _ = _inj6_run(monkeypatch, dose, n_seeds=6)
        assert rep["verdict"] == attendu, (attendu, rep)
        for cle, val in drapeaux.items():
            assert rep[cle] is val, (attendu, cle, rep[cle])
        assert rep["n"] == 6 and rep["n_favorable"] == 6
        assert rep["sign_p"] == pytest.approx(2.0 / 64.0, rel=1e-12)
        assert rep["acc_fresh"] == pytest.approx(0.50)
        assert rep["acc_demand"] == pytest.approx(dose("DEMAND", 0, True))
        assert rep["acc_memoryless_xeval"] == pytest.approx(dose("MLESS", 0, True))


def test_run_experiment_READS_the_REVERSED_contrast_too(monkeypatch):
    """Branche NEGATIVE de l'APPARIEMENT (classe E1). On inverse la dose : c'est le champion MLESS
    qui maitrise le test demanding (1.00) pendant que le champion DEMAND reste au plancher (0.50).

    Un orchestrateur dont le bras primaire serait cable en dur -- ou qui lirait `rd` la ou il croit
    lire `rc` -- publierait ici EXACTEMENT le meme OBJECTIVE_IS_LEVER que dans le cas precedent.
    La reponse juste est le falsificateur (DEMAND au plancher) AVEC la specificite REFUTEE : la
    memoire existe, mais elle n'est pas construite par la demande."""
    rep, _ = _inj6_run(monkeypatch, _inj6_dose(demand=0.50, mless_xeval=1.00, fresh=0.50),
                       n_seeds=6)
    assert rep["verdict"] == "SUBSTRATE_OR_SEARCH_LIMITED", rep
    assert rep["acc_demand"] == pytest.approx(0.50)
    assert rep["acc_memoryless_xeval"] == pytest.approx(1.00)
    assert rep["specific_to_demand"] is False
    assert rep["masters"] is False and rep["n_favorable"] == 0


# ======================================================================================================
# 2. L'UNITE DE REPLICATION et l'APPARIEMENT (ce que les stats en aval ne peuvent pas verifier)
# ======================================================================================================

def test_run_experiment_KEEPS_one_value_per_SEED_and_pairs_them_IN_ORDER(monkeypatch):
    """L'unite de replication declaree par EVO-002 est le SEED (« la lignee evolutive
    independante, PAS le genome d'une lignee ») et le test de signe est APPARIE seed a seed.

    Reponse connue : 5 seeds, DEMAND = [0.90, 0.40, 0.90, 0.40, 0.90], FRESH = 0.50 partout.
      * une valeur par seed, DANS L'ORDRE -> les listes publiees doivent etre celles-la ;
      * appariement -> 3 seeds sur 5 favorables (les seeds 0, 2, 4) ;
      * test de signe exact a n=5, k=3 : kk = min(3, 2) = 2, queue = (1+5+10)/32 = 0.5, p = 1.0.
    Un orchestrateur qui trierait, moyennerait ou desapparierait les listes rendrait le MEME
    `acc_demand` median (0.90) tout en changeant `n_favorable` -- c'est cette difference-la que le
    test mesure, et c'est elle qui porte tout le p publie."""
    dose = _inj6_dose(demand=[0.90, 0.40, 0.90, 0.40, 0.90], mless_xeval=0.50, fresh=0.50)
    rep, _ = _inj6_run(monkeypatch, dose, n_seeds=5)

    assert rep["acc_demand_list"] == [0.90, 0.40, 0.90, 0.40, 0.90]
    assert rep["acc_fresh_list"] == [0.50] * 5
    assert rep["acc_mless_xeval_list"] == [0.50] * 5
    assert rep["n"] == 5 and rep["n_favorable"] == 3
    assert rep["sign_p"] == pytest.approx(1.0, rel=1e-12)
    assert rep["acc_demand"] == pytest.approx(0.90)     # la mediane, elle, ne voit pas le desordre
    assert rep["verdict"] == "INCONCLUSIVE", rep        # maitrise SANS puissance -> pas de positif


def test_run_experiment_at_THREE_seeds_cannot_produce_a_positive_verdict(monkeypatch):
    """Le `n` du test de signe vient de la LONGUEUR des listes, donc du nombre de seeds passes a
    l'orchestrateur -- et de rien d'autre. Reponse connue : la dose PARFAITE du cas positif
    (DEMAND 1.00 / FRESH 0.50 / MLESS 0.50), servie a 3 seeds seulement. Le p exact unanime vaut
    2 x C(3,0)/2^3 = 0.25 : la barre de puissance du depot (< 0.05) ne PEUT pas etre franchie.

    Ce que ce test interdit : qu'un jour la puissance soit calculee sur autre chose que l'unite de
    replication declaree (le nombre d'AGENTS, de generations, de trials d'evaluation...). Aucun de
    ces nombres n'a bouge ici, seul le nombre de seeds."""
    rep, _ = _inj6_run(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50),
                       n_seeds=3)
    assert rep["n"] == 3 and rep["n_favorable"] == 3
    assert rep["sign_p"] == pytest.approx(0.25, rel=1e-12)
    assert rep["masters"] is True and rep["beats_fresh"] is False
    assert rep["verdict"] != "OBJECTIVE_IS_LEVER", rep
    assert rep["acc_demand"] == pytest.approx(1.00) and rep["acc_fresh"] == pytest.approx(0.50)


def test_run_experiment_WIRES_each_source_to_the_TASK_and_the_SEED_it_claims(monkeypatch):
    """LE test de CABLAGE : quatre mesures par seed, et chacune doit porter le bon genome sur la
    bonne tache, avec la bonne graine. Doses toutes distinctes (1.00 / 0.20 / 0.99 / 0.30) pour
    qu'AUCUN croisement ne puisse passer inapercu.

    Ce que l'injection prouve, et qu'aucun chiffre publie ne montrerait :
    (a) les DEUX bras evolutifs recoivent le MEME seed et le MEME regime (generations, pop,
        eval_trials) -- un bras evolue plus longtemps que l'autre rendrait le contraste
        ininterpretable sans rien casser ;
    (b) seul le drapeau `demanding` les separe (True puis False, dans cet ordre) ;
    (c) le champion MLESS est evalue DEUX fois -- sur sa propre tache PUIS en XEVAL demanding --
        et jamais le champion DEMAND a sa place ;
    (d) les quatre evaluations publiees se font a la graine 10_000 + s, donc HORS-ECHANTILLON :
        elle n'est ni la graine d'evolution `s` (fuite train/test) ni celle du genome frais ;
    (e) le genome FRAIS est tire a 9_000 + s, une troisieme graine, a la taille demandee ;
    (f) `oos_trials` va bien aux mesures PUBLIEES et `eval_trials` a l'evolution -- deux budgets
        distincts, que rien d'autre ne distingue ;
    (g) `nodes_demand` vient du bras DEMAND (30+s) et pas du bras MLESS (99.0)."""
    dose = _inj6_dose(demand=1.00, mless_xeval=0.20, mless_own=0.99, fresh=0.30)
    graines = [0, 1, 2, 3]
    rep, J = _inj6_run(monkeypatch, dose, seeds=graines, n_seeds=4, K=5, D=4, generations=6,
                       pop=9, eval_trials=11, sep_pairs=13, oos_trials=17)

    # --- les quatre cellules arrivent chacune a sa place dans le verdict
    assert rep["acc_demand"] == pytest.approx(1.00)
    assert rep["acc_memoryless_xeval"] == pytest.approx(0.20)
    assert rep["acc_memoryless_own"] == pytest.approx(0.99)
    assert rep["acc_fresh"] == pytest.approx(0.30)
    assert rep["nodes_demand"] == pytest.approx(np.median([30.0 + s for s in graines]))

    # --- (a) + (b) : deux evolutions par seed, meme seed, meme regime, seul `demanding` differe
    assert len(J["evolve"]) == 2 * len(graines)
    for i, s in enumerate(graines):
        d, m = J["evolve"][2 * i], J["evolve"][2 * i + 1]
        assert (d["bras"], m["bras"]) == ("DEMAND", "MLESS"), J["evolve"]
        assert d["seed"] == m["seed"] == s, "les deux bras ne sont pas apparies sur le meme seed"
        for cle, attendu in (("K", 5), ("D", 4), ("generations", 6), ("pop", 9),
                             ("eval_trials", 11)):
            assert d[cle] == m[cle] == attendu, (cle, d, m)

    # --- (c) + (d) + (f) : quatre evaluations publiees par seed, dans l'ordre, hors-echantillon
    assert len(J["eval"]) == 4 * len(graines)
    for i, s in enumerate(graines):
        quatre = J["eval"][4 * i:4 * i + 4]
        assert [(e["bras"], e["demanding"]) for e in quatre] == [
            ("DEMAND", True), ("MLESS", False), ("MLESS", True), ("FRESH", True)], quatre
        for e in quatre:
            assert e["seed_genome"] == s, "un genome d'un AUTRE seed est evalue ici"
            assert e["seed"] == _OFFSET_EVAL + s, "graine d'eval EN ECHANTILLON : fuite train/test"
            assert e["trials"] == 17 and e["K"] == 5 and e["D"] == 4, e
    graines_eval = {e["seed"] for e in J["eval"]}
    assert graines_eval.isdisjoint(set(graines)), "la mesure publiee reutilise une graine d'evolution"
    assert graines_eval.isdisjoint({_OFFSET_FRESH + s for s in graines})

    # --- (e) : le genome FRAIS, une fois par seed, a sa propre graine et a la taille demandee
    assert [f["graine"] for f in J["fresh"]] == [_OFFSET_FRESH + s for s in graines]
    assert {f["N"] for f in J["fresh"]} == {_N_TINY}

    # --- l'instrument SECONDAIRE voit les TROIS genomes du seed, au budget demande
    assert len(J["sep"]) == 3 * len(graines)
    for i, s in enumerate(graines):
        trois = J["sep"][3 * i:3 * i + 3]
        assert [x["bras"] for x in trois] == ["DEMAND", "MLESS", "FRESH"], trois
        assert all(x["seed_genome"] == s and x["n_pairs"] == 13 and x["D"] == 4 for x in trois)


# ======================================================================================================
# 3. SPECIFICITE : ce que l'instrument SECONDAIRE ne doit PAS pouvoir faire
# ======================================================================================================

def test_run_experiment_publishes_sep_WITHOUT_letting_it_move_the_verdict(monkeypatch):
    """No-op EXACT (controle de specificite). EVO-002 documente `sep(D)` comme CORROBORANT
    SECONDAIRE explicitement TROMPEUR (« un proxy dynamique plausible qui n'agit PAS ») : le
    verdict doit venir de la capacite de rappel, et de rien d'autre.

    Reponse connue : le MEME jeu de doses de rappel, joue deux fois avec des doses de retention
    DIAMETRALEMENT opposees (DEMAND retient 0.95 / oublie 0.05, et inversement). Les trois
    medianes de `sep` doivent bouger -- preuve que la manipulation a bien eu lieu -- et le bloc de
    verdict rester BIT-IDENTIQUE. Sans la premiere moitie, le test passerait sur un `sep` mort."""
    dose = _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50)
    haut = {"DEMAND": 0.95, "MLESS": 0.50, "FRESH": 0.05}
    bas = {"DEMAND": 0.05, "MLESS": 0.50, "FRESH": 0.95}

    a, _ = _inj6_run(monkeypatch, dose, n_seeds=6, dose_sep=lambda b, s: haut[b])
    b, _ = _inj6_run(monkeypatch, dose, n_seeds=6, dose_sep=lambda b, s: bas[b])

    assert (a["sep_demand"], a["sep_fresh"]) == (0.95, 0.05)      # la dose EST lue...
    assert (b["sep_demand"], b["sep_fresh"]) == (0.05, 0.95)      # ...et elle a bien ete inversee
    cles = ("verdict", "acc_demand", "acc_memoryless_xeval", "acc_fresh", "acc_memoryless_own",
            "n", "n_favorable", "sign_p", "masters", "beats_fresh", "specific_to_demand",
            "acc_demand_list", "acc_mless_xeval_list", "acc_fresh_list", "nodes_demand")
    assert {k: a[k] for k in cles} == {k: b[k] for k in cles}, (
        "sep(D) a deplace le verdict : le corroborant DOCUMENTE COMME TROMPEUR est devenu decisif")
    assert a["verdict"] == "OBJECTIVE_IS_LEVER"                  # ...sur une dose de rappel REELLE


# ======================================================================================================
# 4. La garde d'ARGUMENTS : non pas QU'elle leve, mais OU elle est posee
# ======================================================================================================

def test_run_experiment_REFUSES_degenerate_arguments_BEFORE_any_evolution(monkeypatch):
    """La garde (:284) doit lever AVANT la moindre evolution : les quatre fonctions injectees sont
    des BOMBES, donc un refus qui coute une seule generation fait echouer le test. Cinq doses, une
    par terme de la garde. Sans elle, une cohorte vide produirait des listes vides que
    `compute_enrichment_verdict` transforme en `StatisticsError` -- ou, pire, qu'un aval plus
    tolerant lirait comme une mesure nulle OBSERVEE."""
    M, J = _inj6_injecte(monkeypatch, _inj6_dose(1.0, 0.5, 0.5), bombe=True)
    base = dict(seeds=[0, 1], K=2, D=3, generations=5, pop=8, eval_trials=4)
    for cle, valeur in (("seeds", []), ("K", 0), ("generations", 0), ("pop", 0),
                        ("eval_trials", 0)):
        kw = dict(base, **{cle: valeur})
        with pytest.raises(ValueError, match="degenere"):
            M.run_experiment(kw["seeds"], kw["K"], kw["D"], kw["generations"], kw["pop"],
                             eval_trials=kw["eval_trials"])
    assert J["evolve"] == [] and J["eval"] == [], "une mesure a eu lieu malgre le refus"


# ======================================================================================================
# 5. NON-REGRESSION -- les QUATRE defauts que l'injection avait exposes, et qui sont CORRIGES.
#    ⚠️ 2026-09-08, REFUTATION : ces quatre tests etaient encore decores `xfail(strict=True)` APRES
#    l'application des correctifs. Un `xfail` strict qui PASSE est un ECHEC : la suite rendait
#    « 4 failed, 16 passed » -- quatre tests ROUGES laisses derriere le correctif, exactement le
#    scenario que la docstring du fichier annoncait (« ils tomberont d'eux-memes le jour ou le defaut
#    sera repare (strict -> un XPASS echoue) »). Retirer le marqueur FAIT PARTIE du correctif : sans
#    quoi le test qui prouve le correctif est indiscernable d'une regression.
# ======================================================================================================

_DEFAUT_1_CORRIGE_LE_2026_09_08 = """
    "DEFAUT REEL (controle de specificite VIDE, classes E1+E2). `run_experiment` MESURE le champion "
    "MLESS sur SA PROPRE tache (tools/evo_memory_enrichment.py:296) et la PUBLIE "
    "(`acc_memoryless_own`, :307) -- la docstring dit mot pour mot a quoi elle sert : « a-t-il "
    "appris ? -> son echec en XEVAL est bien 'pas de memoire', pas 'rien appris' ». Mais elle "
    "n'entre JAMAIS dans le verdict : `compute_enrichment_verdict` n'en recoit que trois listes "
    "(:306) et `specific = am < inverse_max` (:246) ne regarde que le XEVAL. Consequence PUBLIEE : "
    "quand l'evolution MEMORYLESS echoue COMPLETEMENT (elle ne resout meme pas sa propre tache "
    "feedforward, ~chance), son XEVAL est a chance POUR UNE AUTRE RAISON que l'absence de memoire, "
    "et EDR-EVO-002 grave quand meme « la memoire est SPECIFIQUE a la demande » (OBJECTIVE_IS_LEVER, "
    "specific_to_demand=True). Le controle inverse est alors un bras qui ne POUVAIT pas reussir. "
    "Correctif attendu : faire ENTRER acc_memoryless_own dans la decision (verdict indetermine, ou "
    "drapeau bloquant, tant que le controle inverse n'a pas maitrise SA tache)."""


def test_run_experiment_REFUSES_a_SPECIFICITY_claim_when_the_INVERSE_control_learned_NOTHING(
        monkeypatch):
    """Reponse connue : DEMAND maitrise (1.00), FRESH au plancher (0.50), MLESS-XEVAL a chance
    (0.50) -- MAIS le champion MLESS est a chance SUR SA PROPRE TACHE aussi (0.50), alors qu'elle
    est resoluble en FEEDFORWARD (la cible est montree a la sonde). Son evolution a echoue tout
    court. Rien dans ces chiffres ne permet de dire que la memoire est specifique a la demande :
    le controle de specificite est VIDE. Le verdict juste est un indetermine ; le code publie
    OBJECTIVE_IS_LEVER."""
    rep, _ = _inj6_run(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, mless_own=0.50,
                                               fresh=0.50), n_seeds=6)
    assert rep["acc_memoryless_own"] == pytest.approx(0.50)     # constat : le bras inverse est MORT
    assert rep["verdict"] != "OBJECTIVE_IS_LEVER", (
        "specificite AFFIRMEE alors que le controle inverse n'a rien appris du tout : "
        f"{rep['verdict']} / specific_to_demand={rep['specific_to_demand']}")


_DEFAUT_2_CORRIGE_LE_2026_09_08 = """
    "DEFAUT REEL (la garde anti-negatif FABRIQUE le vide qu'elle refuse). La garde d'arguments "
    "evalue `not list(seeds)` (tools/evo_memory_enrichment.py:284), ce qui CONSOMME un iterateur ; "
    "la boucle `for s in seeds` (:290) tourne alors ZERO fois. Trois seeds fournis -> zero mesure, "
    "puis `statistics.median([])` -> StatisticsError depuis compute_enrichment_verdict:240, sans "
    "un mot sur la cause. C'est EXACTEMENT le defaut corrige le 2026-09-07 sur "
    "`evo_memory_inworld.run_contrast` (non-regression "
    "`test_run_contrast_REFUSES_to_silently_empty_a_consumed_iterator`) : il n'a pas ete propage "
    "ici. Correctif attendu : `seeds = list(seeds)` UNE fois, en tete, avant la garde."""


def test_run_experiment_REFUSES_to_EMPTY_a_seed_ITERATOR_it_was_given(monkeypatch):
    """Reponse connue : trois seeds sont fournis -- sous forme d'iterateur, la forme naturelle d'un
    `map`, d'un `range` filtre ou d'un generateur. Il doit donc y avoir trois lignes de mesure, ou
    un refus EXPLICITE. Ni l'un ni l'autre aujourd'hui."""
    M, J = _inj6_injecte(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50))
    rep = M.run_experiment(iter([0, 1, 2]), 2, 3, 5, 8, eval_trials=4, sep_pairs=3, oos_trials=7)
    assert len(rep["acc_demand_list"]) == 3, (
        f"iterateur consomme par la garde : {len(J['evolve'])} evolution(s) lancee(s) pour 3 seeds")


_DEFAUT_3_CORRIGE_LE_2026_09_08 = """
    "DEFAUT REEL (pseudo-replication -- l'unite de replication DECLAREE n'est pas celle qui est "
    "comptee). Le seed determine ENTIEREMENT une ligne : `evolve` fait `np.random.seed(seed)` puis "
    "`RandomState(seed)` (tools/evo_memory_enrichment.py:189-190), le genome frais vient de "
    "`RandomState(9000+s)` (:293), l'evaluation de `seed=10000+s` (:294) et sep de `seed=s` (:299). "
    "MESURE sur le VRAI code, sans aucun monde (64 ms) : run_experiment([7,7], K=2, D=1, "
    "generations=1, pop=4, eval_trials=2, sep_pairs=2, oos_trials=4) imprime DEUX lignes "
    "BIT-IDENTIQUES et rapporte n=2. A 12 seeds dupliques le test de signe publierait "
    "p = 2^-11 = 0.00049 depuis UN SEUL replicat -- alors que EVO-002 declare explicitement « unite "
    "de replication : le SEED (lignee evolutive independante), PAS le genome d'une lignee ». "
    "Correctif attendu : refuser ou dedupliquer les seeds en tete de fonction."""


def test_run_experiment_REFUSES_duplicate_seeds(monkeypatch):
    """Reponse connue : [7, 7] ne contient qu'UN replicat. Volontairement joue sur le VRAI code
    (aucun monde n'est construit -- `evolve` est du numpy pur sur un genome de 19 noeuds), a
    parametres minuscules : c'est la preuve directe que les deux lignes sont le meme calcul, et
    non une propriete de mon injection."""
    from tools.evo_memory_enrichment import run_experiment

    try:
        rep = run_experiment([7, 7], K=2, D=1, generations=1, pop=4, eval_trials=2, sep_pairs=2,
                             oos_trials=4)
    except ValueError as exc:                      # correctif par REFUS explicite : acceptable
        assert "degenere" in str(exc) or "seed" in str(exc).lower()
        return
    if len(rep["acc_demand_list"]) == 2:           # constat : les deux lignes sont indiscernables
        assert rep["acc_demand_list"][0] == rep["acc_demand_list"][1]
        assert rep["acc_fresh_list"][0] == rep["acc_fresh_list"][1]
    assert rep["n"] == 1, (
        f"pseudo-replication : n={rep['n']} pour UN seul seed distinct "
        f"(listes {rep['acc_demand_list']})")


_DEFAUT_4_CORRIGE_LE_2026_09_08 = """
    "DEFAUT REEL (le budget de MESURE n'est pas garde, et le nan est avale). La garde (:284) "
    "controle `eval_trials` -- le budget de la fitness INTERNE a l'evolution -- mais PAS "
    "`oos_trials`, qui est le budget des QUATRE mesures effectivement PUBLIEES (:295-298). A "
    "oos_trials=0 la VRAIE `eval_genome` rend `float(np.mean([]))` = nan (:127, verifie ici sur le "
    "vrai code) ; les quatre listes deviennent des nan, `median` les propage, et TOUTES les "
    "comparaisons du verdict s'evaluent silencieusement a False (`nan > 0.85`, `nan <= 0.60`, "
    "`nan < 0.75`). MESURE sur le vrai code, 6 seeds : verdict INCONCLUSIVE, acc_demand=nan, et "
    "n=6 avec sign_p=0.03125 -- un p SIGNIFICATIF publie depuis ZERO mesure (nan > nan est False, "
    "donc les 6 seeds comptent comme unanimement DEFAVORABLES, ce qui est un verdict de FOND tire "
    "d'une absence). `sep_pairs=0` est le meme trou en pire : `measure_retention_separation` rend "
    "alors 0.0 (:91, mesure : 0.0), publie comme « le substrat ne retient RIEN ». Correctif "
    "attendu : ajouter oos_trials et sep_pairs a la garde d'arguments."""


def test_run_experiment_REFUSES_a_measurement_budget_of_ZERO(monkeypatch):
    """Reponse connue en deux temps.
    1. Le VRAI `eval_genome` a trials=0 ne peut plus rendre une mesure : il REFUSE.
    2. L'orchestrateur, servi par cette mesure absente, doit REFUSER comme il refuse deja
       eval_trials=0 : la seule difference entre les deux arguments est lequel produit les
       chiffres du record.

    ⚠️ CLASSE E14 (retro-application). Ce constat prealable exigeait, jusqu'au 2026-09-08,
    `math.isnan(eval_genome(..., trials=0))` : c'etait la MESURE du defaut. La garde posee depuis
    EN TETE de `eval_genome` change le contrat de cette fixture -- corriger le test fait partie du
    correctif, pas du nettoyage. Le constat devient : la mesure absente LEVE, elle ne rend plus un
    nan que l'aval lirait comme DEFAVORABLE."""
    import tools.evo_memory_enrichment as M

    vraie_mesure = M.eval_genome                  # capturee AVANT toute injection
    g = _inj6_genome("DEMAND", 0)
    with pytest.raises(ValueError, match="degenere"):
        vraie_mesure(g, 2, 3, True, 0, seed=0)
    assert vraie_mesure(g, 2, 3, True, 1, seed=0) == pytest.approx(0.0, abs=1.0), (
        "cas NEGATIF apparie : trials=1 est un budget PAUVRE mais REEL, il doit rendre une mesure")

    _inj6_injecte(monkeypatch, _inj6_dose(1.0, 0.5, 0.5))
    monkeypatch.setattr(M, "eval_genome", vraie_mesure)    # la VRAIE mesure, budget ZERO
    with pytest.raises(ValueError, match="degenere"):
        M.run_experiment([0, 1, 2], 2, 3, 5, 8, eval_trials=4, sep_pairs=3, oos_trials=0)


# ======================================================================================================
# 6. CAS NEGATIFS APPARIES des correctifs du 2026-09-08 (classe E1 : un correctif qui rend le refus
#    INCREVABLE est PIRE que le defaut). Pour CHAQUE comportement ajoute a `run_experiment`, le cas qui
#    prouve qu'il sait encore NE PAS se declencher -- et la BARRE qu'il lit, mesuree de part et d'autre.
# ======================================================================================================

def test_materializing_the_seeds_does_NOT_disarm_the_empty_cohort_guard(monkeypatch):
    """Cas negatif apparie de `seeds = list(seeds)` (correctif de l'iterateur consomme).

    Materialiser en tete ne doit PAS transformer « cohorte vide » en run silencieux : un ITERATEUR
    VIDE est toujours une cohorte vide, et le refus doit rester INSTANTANE (les quatre fonctions sont
    des bombes). Sans ce cas, le correctif pourrait avoir desarme la garde qu'il traverse."""
    M, J = _inj6_injecte(monkeypatch, _inj6_dose(1.0, 0.5, 0.5), bombe=True)
    for cohorte_vide in (iter([]), (s for s in []), [], ()):
        with pytest.raises(ValueError, match="degenere"):
            M.run_experiment(cohorte_vide, 2, 3, 5, 8, eval_trials=4)
    assert J["evolve"] == [] and J["eval"] == [], "une mesure a eu lieu malgre le refus"


def test_an_ITERATOR_of_seeds_gives_the_SAME_result_as_the_equivalent_LIST(monkeypatch):
    """Le correctif doit rendre les deux formes EQUIVALENTES, pas seulement non vides. Reponse connue :
    le bloc de verdict d'un `iter([0,1,2,3,4,5])` doit etre BIT-IDENTIQUE a celui de la liste, et
    l'orchestrateur doit avoir lance 2 evolutions x 6 seeds dans les deux cas."""
    dose = _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50)
    M, Ji = _inj6_injecte(monkeypatch, dose)
    par_iterateur = M.run_experiment(iter(range(6)), 2, 3, 5, 8, eval_trials=4, sep_pairs=3,
                                     oos_trials=7)
    M, Jl = _inj6_injecte(monkeypatch, dose)
    par_liste = M.run_experiment([0, 1, 2, 3, 4, 5], 2, 3, 5, 8, eval_trials=4, sep_pairs=3,
                                 oos_trials=7)
    assert par_iterateur == par_liste, "iterateur et liste ne donnent pas la meme mesure"
    assert par_iterateur["n"] == 6 and par_iterateur["verdict"] == "OBJECTIVE_IS_LEVER"
    assert len(Ji["evolve"]) == len(Jl["evolve"]) == 12


def test_DISTINCT_seeds_are_NOT_deduplicated_and_duplicates_keep_FIRST_ORDER(monkeypatch):
    """Cas negatif apparie de la deduplication (pseudo-replication). DEUX reponses connues :

    * 5 seeds DISTINCTS -> AUCUN ecart : n=5, les cinq lignees sont evoluees, aucun avertissement.
      Un dedoublonnage trop large ecraserait des replicats REELS et baisserait la puissance publiee.
    * [4, 2, 4, 2, 7] -> 3 lignees distinctes, dans l'ORDRE DE PREMIERE APPARITION [4, 2, 7] (la trace
      doit rester reproductible), et un avertissement EXPLICITE (jamais un ecart silencieux)."""
    dose = _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50)
    rep, J = _inj6_run(monkeypatch, dose, seeds=[10, 11, 12, 13, 14], n_seeds=5)
    assert rep["n"] == 5 and len(J["evolve"]) == 10
    assert [e["seed"] for e in J["evolve"]] == [10, 10, 11, 11, 12, 12, 13, 13, 14, 14]

    rep2, J2 = _inj6_run(monkeypatch, dose, seeds=[4, 2, 4, 2, 7], n_seeds=5)
    assert rep2["n"] == 3, f"pseudo-replication : n={rep2['n']} pour 3 lignees distinctes"
    assert [e["seed"] for e in J2["evolve"]] == [4, 4, 2, 2, 7, 7], (
        "ordre de premiere apparition non preserve, ou un doublon a coute un run")
    assert len(rep2["acc_demand_list"]) == 3


def test_run_experiment_warns_OUT_LOUD_when_it_drops_duplicate_seeds(monkeypatch, capsys):
    """Un ecart de seed change le `n` PUBLIE : il doit s'ecrire. Reponse connue : [7, 7] -> le mot
    DUPLIQUE(S) apparait sur la sortie, et il n'apparait PAS quand les seeds sont distincts (sinon
    l'avertissement serait du bruit constant, donc invisible)."""
    dose = _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50)
    _inj6_run(monkeypatch, dose, seeds=[7, 7], n_seeds=2)
    assert "DUPLIQUE" in capsys.readouterr().out
    _inj6_run(monkeypatch, dose, seeds=[7, 8], n_seeds=2)
    assert "DUPLIQUE" not in capsys.readouterr().out


def test_the_measurement_budget_guard_REFUSES_zero_but_ACCEPTS_one(monkeypatch):
    """Cas negatif apparie de la garde sur `oos_trials` / `sep_pairs` / `D`.

    * REFUS, avant toute mesure (bombes) : oos_trials=0 ou negatif, sep_pairs=0 ou negatif, D<0 --
      trois budgets dont l'absence produit respectivement nan (avale en verdict de fond), sep=0.0
      (« ne retient RIEN ») et un delai qui disparait (sep=1.0, « retient tout »).
    * ACCEPTATION du MINIMUM : oos_trials=1, sep_pairs=1, D=0 sont des budgets pauvres mais REELS ;
      la garde ne doit pas les refuser, sinon elle interdit un regime legitime au lieu d'une absence
      de mesure. Le run doit aller au bout et publier un verdict."""
    M, J = _inj6_injecte(monkeypatch, _inj6_dose(1.0, 0.5, 0.5), bombe=True)
    for kw in (dict(oos_trials=0), dict(oos_trials=-1), dict(sep_pairs=0), dict(sep_pairs=-4)):
        plein = dict(dict(sep_pairs=3, oos_trials=7), **kw)
        with pytest.raises(ValueError, match="degenere"):
            M.run_experiment([0, 1], 2, 3, 5, 8, eval_trials=4, **plein)
    with pytest.raises(ValueError, match="degenere"):        # D negatif : le delai disparait
        M.run_experiment([0, 1], 2, -1, 5, 8, eval_trials=4, sep_pairs=3, oos_trials=7)
    assert J["evolve"] == [] and J["eval"] == [], "une mesure a eu lieu malgre le refus"

    rep, J2 = _inj6_run(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50),
                        n_seeds=6, D=0, sep_pairs=1, oos_trials=1)
    assert rep["verdict"] == "OBJECTIVE_IS_LEVER", rep
    assert len(J2["eval"]) == 24 and all(e["trials"] == 1 for e in J2["eval"])
    assert all(x["n_pairs"] == 1 and x["D"] == 0 for x in J2["sep"])


def test_the_INVERSE_control_gate_fires_ONLY_on_the_branch_that_CLAIMS_specificity(monkeypatch):
    """Cas negatif apparie du verrou « controle inverse VIDE » (le correctif du 1er xfail).

    Trois reponses connues, meme dose de rappel a la seule exception de `mless_own` :
    * mless_own=0.95 (le bras MLESS a maitrise SA tache) -> OBJECTIVE_IS_LEVER reste ATTEIGNABLE :
      le verrou sait ne pas se declencher, et le drapeau publie le dit (`inverse_control_learned`).
    * mless_own=0.50 avec DEMAND au PLANCHER -> SUBSTRATE_OR_SEARCH_LIMITED reste INCHANGE : cette
      branche compare DEMAND au plancher et ne revendique AUCUNE specificite ; un verrou qui la
      recouvrirait effacerait le FALSIFICATEUR d'EVO-001, c'est-a-dire la seule issue negative.
    * la BARRE lue est `acc_pos` (0.85), la MEME que pour DEMAND -- mesuree de part et d'autre
      (0.86 -> LEVER, 0.84 -> INDETERMINATE), donc aucun nombre libre supplementaire."""
    ok, _ = _inj6_run(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, mless_own=0.95,
                                              fresh=0.50), n_seeds=6)
    assert ok["verdict"] == "OBJECTIVE_IS_LEVER" and ok["inverse_control_learned"] is True

    plancher, _ = _inj6_run(monkeypatch, _inj6_dose(demand=0.50, mless_xeval=1.00, mless_own=0.50,
                                                    fresh=0.50), n_seeds=6)
    assert plancher["verdict"] == "SUBSTRATE_OR_SEARCH_LIMITED", plancher
    assert plancher["inverse_control_learned"] is False   # le constat est PUBLIE, il ne recouvre rien

    for own, attendu in ((0.86, "OBJECTIVE_IS_LEVER"), (0.84, "INDETERMINATE_INVERSE_CONTROL_VOID")):
        r, _ = _inj6_run(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, mless_own=own,
                                                 fresh=0.50), n_seeds=6)
        assert r["verdict"] == attendu, (own, r["verdict"])
        assert r["acc_memoryless_own"] == pytest.approx(own)


def test_compute_enrichment_verdict_says_UNKNOWN_when_the_inverse_control_is_NOT_supplied():
    """Le contrat HISTORIQUE a trois listes (celui que calibre `test_instrument_calibration.py`) reste
    intact : `acc_memoryless_own=None` = controle NON FOURNI -> `inverse_control_learned` vaut None,
    un INCONNU explicite, JAMAIS un True tacite. Et une liste VIDE n'est pas la meme chose que None :
    elle est refusee, parce qu'un controle mesure-et-nul et un controle absent ne doivent pas se
    confondre (c'est le biais « absence -> affirmation » que ce depot traque)."""
    from tools.evo_memory_enrichment import compute_enrichment_verdict as V
    dem, mless, fresh = [1.0] * 6, [0.5] * 6, [0.5] * 6
    sans = V(dem, mless, fresh)
    assert sans["verdict"] == "OBJECTIVE_IS_LEVER"          # contrat historique inchange
    assert sans["inverse_control_learned"] is None and sans["acc_memoryless_own"] is None
    avec = V(dem, mless, fresh, acc_memoryless_own=[0.5] * 6)
    assert avec["verdict"] == "INDETERMINATE_INVERSE_CONTROL_VOID"
    with pytest.raises(ValueError, match="degenere"):
        V(dem, mless, fresh, acc_memoryless_own=[])


def test_measure_retention_separation_REFUSES_an_unmeasurable_pair_instead_of_saying_ZERO():
    """Le defaut adjacent nomme par le meme xfail (« sep_pairs=0 -> 0.0, publie comme le substrat ne
    retient RIEN ») : `sep = 0` est la valeur de l'OUBLI PARFAIT, donc une absence de mesure y prenait
    la forme d'une affirmation de FOND. Reponse connue, des DEUX cotes :

    * REFUS, instantane (garde en tete, aucune simulation) : n_pairs=0 et n_pairs negatif, D<0 (le
      delai disparait et sep vaudrait 1.0 -- l'affirmation INVERSE), et un genome sans aucun noeud
      au-dela des entrees (N<=I : les deux histoires sont identiques par construction).
    * ACCEPTATION du minimum : n_pairs=1 et D=0 sur un genome normal rendent une VRAIE valeur dans
      [0, 1]. Sans ce second volet, la garde pourrait avoir rendu l'instrument increvable (classe E1).
    """
    import time
    import numpy as _np
    from src.seed_ai.mutation import Genome
    from tools.evo_memory_enrichment import measure_retention_separation as SEP

    g = _inj6_genome("DEMAND", 0)                       # 19 noeuds, 8 entrees -> 11 hors-entree
    for kw in (dict(n_pairs=0), dict(n_pairs=-3)):
        with pytest.raises(ValueError, match="degenere"):
            SEP(g, 3, **kw)
    with pytest.raises(ValueError, match="degenere"):
        SEP(g, -1, n_pairs=4)

    plat = Genome(_np.zeros((I_ATT, I_ATT), _np.float32), I_ATT, I_ATT)   # N == I : aucune memoire
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        SEP(plat, 3, n_pairs=64)
    assert time.time() - t0 < 0.5, "refus trop lent : la garde n'est pas EN TETE"

    for D, n in ((0, 1), (3, 2)):
        got = SEP(g, D, n_pairs=n, seed=0)
        assert 0.0 <= got <= 1.0000001, (D, n, got)


def test_compute_enrichment_verdict_REFUSES_a_NaN_instead_of_reading_it_as_UNFAVORABLE():
    """Le MECANISME que le 4e xfail nomme dans son titre (« et le nan est avale »), ferme au niveau du
    verdict et plus seulement a sa cause connue (budget de mesure nul).

    Reponse connue, des DEUX cotes :
    * REFUS : un seul nan dans l'une des QUATRE listes -> ValueError qui NOMME la liste. Sans lui,
      `nan > 0.85`, `nan <= 0.60` et `nan < 0.75` valent toutes False, les seeds comptent unanimement
      DEFAVORABLES, et le verdict sort INCONCLUSIVE avec sign_p=0.03125 -- un p significatif publie
      depuis ZERO mesure.
    * ACCEPTATION : les memes listes SANS nan tranchent normalement. La garde ne rend donc pas
      l'instrument increvable (classe E1) ; elle ne refuse que l'absence de mesure."""
    from tools.evo_memory_enrichment import compute_enrichment_verdict as V
    nan = float("nan")
    dem, mless, fresh, own = [1.0] * 6, [0.5] * 6, [0.5] * 6, [0.95] * 6

    assert V(dem, mless, fresh, acc_memoryless_own=own)["verdict"] == "OBJECTIVE_IS_LEVER"

    for nom, kw in (("acc_demand", dict(acc_demand=[nan] * 6)),
                    ("acc_memoryless_xeval", dict(acc_memoryless_xeval=[nan] * 6)),
                    ("acc_fresh", dict(acc_fresh=[nan] * 6)),
                    ("acc_memoryless_own", dict(acc_memoryless_own=[nan] * 6))):
        args = dict(acc_demand=dem, acc_memoryless_xeval=mless, acc_fresh=fresh,
                    acc_memoryless_own=own)
        args.update(kw)
        with pytest.raises(ValueError, match="NaN"):
            V(**args)

    # UN SEUL nan, noye dans des valeurs valides : la mediane ne le verrait pas passer.
    boiteux = [1.0, 1.0, nan, 1.0, 1.0, 1.0]
    with pytest.raises(ValueError, match="acc_demand"):
        V(boiteux, mless, fresh, acc_memoryless_own=own)


# ======================================================================================================
# 7. PASSE DE REFUTATION (2026-09-08) -- ce que la passe precedente n'avait PAS ferme au niveau de
#    l'orchestrateur. Chaque garde AJOUTEE ici a son cas NEGATIF APPARIE dans le meme test (classe E1).
# ======================================================================================================

def test_run_experiment_REFUSES_a_population_too_small_to_SEARCH_but_ACCEPTS_three(monkeypatch):
    """LE defaut le plus grave trouve par la refutation : un verdict de FOND fabrique par une ABSENCE
    DE RECHERCHE.

    `evolve` fixe `n_elite = max(2, pop // 4)`. A pop <= 2 l'elite EST la population entiere, donc
    `while len(children) < pop - len(elite)` ne tourne JAMAIS : ZERO mutant est cree, a toutes les
    generations. L'operateur de variation -- le seul objet de l'experience -- n'existe pas.
    MESURE (VRAI code, pop=2, gen=8, seed=0) : acc_history PLAT [0.562]x8, final_nodes = 19.0 = le
    genome INITIAL (aucun add_node). Et `run_experiment(range(6), pop=2, ...)` ACCEPTAIT, puis
    publiait `SUBSTRATE_OR_SEARCH_LIMITED` -- « verrou = substrat OU RECHERCHE », le FALSIFICATEUR
    d'EVO-001 -- depuis un bras qui ne POUVAIT pas chercher (classes E1+E2).

    Reponse connue des DEUX cotes, et la barre mesuree de part et d'autre :
    * REFUS INSTANTANE (bombes) a pop=2, pop=1, et a K >= I_DIM (le meme trou en version bruyante :
      `go[0, K] = 1.0` levait un IndexError a huit appels de profondeur).
    * ACCEPTATION de pop=3, la valeur EXACTE ou un enfant apparait : le run va au bout et publie.
      Sans ce second volet, la garde aurait pu rendre le falsificateur INATTEIGNABLE, ce qui est
      pire que le defaut."""
    M, J = _inj6_injecte(monkeypatch, _inj6_dose(1.0, 0.5, 0.5), bombe=True)
    for pop in (2, 1, 0, -3):
        with pytest.raises(ValueError, match="degenere"):
            M.run_experiment([0, 1], 2, 3, 5, pop, eval_trials=4, sep_pairs=3, oos_trials=7)
    for K in (I_ATT, I_ATT + 1, 0):
        with pytest.raises(ValueError, match="degenere"):
            M.run_experiment([0, 1], K, 3, 5, 8, eval_trials=4, sep_pairs=3, oos_trials=7)
    assert J["evolve"] == [] and J["eval"] == [], "une mesure a eu lieu malgre le refus"

    rep, J2 = _inj6_run(monkeypatch, _inj6_dose(demand=1.00, mless_xeval=0.50, fresh=0.50),
                        n_seeds=6, pop=3, K=I_ATT - 1)
    assert rep["verdict"] == "OBJECTIVE_IS_LEVER", rep
    assert all(e["pop"] == 3 and e["K"] == I_ATT - 1 for e in J2["evolve"])


def test_the_search_operator_is_PROVABLY_absent_below_the_bar_and_PRESENT_at_it():
    """La barre `pop >= 3` n'est pas un nombre libre : c'est la valeur ou `pop - max(2, pop//4)`
    devient positif. On le MESURE sur la VRAIE `evolve`, sans aucun monde, plutot que de le
    raisonner -- c'est la difference entre une garde justifiee et une garde decretee.

    * pop=2 (regime refuse) : la population ne bouge pas d'un iota -- meme si on desarme la garde,
      `final_nodes` reste a 19.0 et `acc_history` est constant. On le verifie en appelant
      l'INTERNE (`_fresh_genome` + la meme boucle) plutot qu'en desarmant la source.
    * pop=3 (regime accepte) : `final_nodes` DEPASSE 19.0 -> `add_node` a mordu, la recherche
      existe."""
    from tools.evo_memory_enrichment import evolve

    with pytest.raises(ValueError, match="degenere"):
        evolve(K=2, D=3, seed=0, generations=8, pop=2, eval_trials=8)

    r3 = evolve(K=2, D=3, seed=1, generations=6, pop=3, eval_trials=8)
    assert r3["final_nodes"] > 19.0, (
        f"pop=3 devait MUTER (mesure attendue 19.33) : final_nodes={r3['final_nodes']}")
    assert 0.0 <= r3["best_acc"] <= 1.0
