# -*- coding: utf-8 -*-
# P2.44 (2026-09-08) -- INJECTION A DOSE CONNUE, suite de `test_orchestrator_injection.py` (les 5
# prioritaires, la veille). Meme technique : monkeypatch de l'attribut de MODULE appele, cellules
# imposees a DOSE CONNUE, verdict exige en forme close, branches NEGATIVES comprises. AUCUN monde
# construit -> cout nul. Controle E1 PAR MUTATION effectue : l'orchestrateur rendu aveugle a la dose
# fait MOURIR les tests passants. Les `xfail(strict=True)` restants sont des DEFAUTS REELS ouverts ;
# les blocs NON-REGRESSION sont d'anciens xfail dont le defaut a ete corrige.
# 2026-09-08, REFUTATEUR : les QUATRE xfail de la section 3 avaient ete corriges dans le module sans
# que ce fichier bouge -> quatre XPASS(strict), donc quatre tests ROUGES. Convertis en
# NON-REGRESSION, avec le statut EXACT exige et un contre-exemple apparie par bloc. Il ne reste
# AUCUN xfail dans ce fichier.
# -*- coding: utf-8 -*-
"""INJ6 (2026-09-08) -- calibration par INJECTION A DOSE CONNUE de
`tools/dream_distress_probe.py::run_distress`.

`run_distress` est un ORCHESTRATEUR : il ne simule pas, il appelle `run_era_organ` (une ere par seed,
organe a 100 %) puis AGREGE les mesures en verdict de detresse (DETRESSE / BENEFIQUE / NEUTRE).
Sa garde d'ARGUMENTS etait deja calibree (`empty-cohort:raises`, `guard-before-world`) ; la couche qui
transforme des mesures en AFFIRMATION -- appariement seed<->mesure, unite de replication, cablage du
regime, branches de verdict -- ne l'etait par rien. C'est pourtant la que se decide ce qui est publie.

SEAM : `run_era_organ` est importe AU NIVEAU MODULE (`from tools.dreaming_probe import run_era_organ`,
tools/dream_distress_probe.py:64) -> l'attribut a monkeypatcher est
`tools.dream_distress_probe.run_era_organ`, PAS `tools.dreaming_probe.run_era_organ`. Verifie par
`test_run_distress_MEASURES_without_building_any_world` (un monde construit coute des minutes ; ici la
suite entiere mesure en millisecondes) et par le piege de
`test_run_distress_REFUSES_degenerate_arguments_BEFORE_any_era`.

DOSE : chaque ere factice rend une cohorte dont le TAUX DE REVE median est impose de part et d'autre du
split d'age, donc `delta` (= rate_short - rate_long) est connu en FORME CLOSE, et le verdict avec lui
(sign_p binomial exact : 5/5 -> 0.0625 ; 4/4 -> 0.125 ; 3/3 -> 0.25).

Les branches NEGATIVES sont exigees (BENEFIQUE, NEUTRE mixte, NEUTRE sous-puissant) : sans elles, un
orchestrateur qui rendrait DETRESSE quoi qu'il arrive passerait (classe E1).

Les `xfail(strict=True)` sont des DEFAUTS REELS, NON corriges ici (ce fichier n'ecrit rien dans le
depot) : ils tombent d'eux-memes le jour ou le defaut est corrige.
"""
import time

import pytest


_INJ6_DB = "DB-SENTINELLE-INJ6"        # sentinelle : `shared_db` doit traverser jusqu'a chaque ere


def _inj6_agent(age, dreams, organ=True, founder=True):
    """Un agent tel que `run_era_organ` le rend, avec TOUTES ses cles (tools/dreaming_probe.py:128-132)
    -- pas seulement `age`/`total_dreams` que l'orchestrateur lit aujourd'hui. Si `run_distress` se
    mettait a lire `founder`, `has_organ` ou `altars_solved`, ce test ne mentirait pas pour autant."""
    return {"age": float(age), "total_dreams": float(dreams), "has_organ": bool(organ),
            "founder": bool(founder), "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}


def _inj6_cellule(rate_short, rate_long, n=2, age_court=10, age_long=30):
    """Cellule d'UNE ere a dose connue : `n` agents COURT-vivants (age 10) au taux de reve
    `rate_short` et `n` LONG-vivants (age 30) au taux `rate_long`.

    Forme close : tous les ages sont >= age_floor(10) donc rien n'est filtre ; la mediane des ages vaut
    20 -> short = les 10, long = les 30 ; `dream_rate = total_dreams / max(age,1)` rend exactement le
    taux impose, et `delta = rate_short - rate_long`. `n` ne change RIEN au delta : c'est ce qui rend
    l'unite de replication testable (cf. test_..._COUNTS_seeds_not_agents)."""
    return ([_inj6_agent(age_court, rate_short * age_court) for _ in range(n)]
            + [_inj6_agent(age_long, rate_long * age_long) for _ in range(n)])


def _inj6_injecte(monkeypatch, doses, journal=None):
    """Remplace `run_era_organ` DANS `tools.dream_distress_probe` par une ere factice a dose connue.

    `doses` : {seed -> cohorte}. Un seed absent leve KeyError -> un orchestrateur qui inventerait,
    decalerait ou dupliquerait un seed le dit tout de suite au lieu de rendre un verdict plausible.
    Aucun monde n'est construit, aucun bail `kuzu` n'est pris."""
    import tools.dream_distress_probe as D

    def _fausse_ere(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        if journal is not None:
            journal.append({"target": target, "seed": seed, "organ_fraction": organ_fraction,
                            "metab": metab, "payoff": payoff, "num_agents": num_agents,
                            "max_ticks": max_ticks, "shared_db": shared_db})
        return doses[seed]

    _fausse_ere._inj6 = True
    # Controle de SEAM, a chaque injection : l'attribut qu'on remplace doit etre CELUI de
    # `tools.dreaming_probe` (ou deja l'une de nos fausses eres, quand un meme test injecte
    # plusieurs doses). S'il changeait -- import deplace, indirection ajoutee -- l'injection
    # deviendrait un no-op silencieux et 12 mondes seraient construits pour de vrai.
    import tools.dreaming_probe as _src
    assert D.run_era_organ is _src.run_era_organ or getattr(D.run_era_organ, "_inj6", False), (
        "le seam a bouge : `tools.dream_distress_probe.run_era_organ` n'est plus l'import de module "
        "attendu -- l'injection ne controle plus le chemin d'appel")
    monkeypatch.setattr(D, "run_era_organ", _fausse_ere)
    return D


def _inj6_run(monkeypatch, doses, seeds=None, journal=None, **kw):
    D = _inj6_injecte(monkeypatch, doses, journal)
    kw.setdefault("target", "stoneage")
    kw.setdefault("num_agents", 4)
    kw.setdefault("max_ticks", 10)
    kw.setdefault("shared_db", _INJ6_DB)
    return D.run_distress(seeds=list(doses) if seeds is None else seeds, **kw)


# ---------------------------------------------------------------------------------------------------
# 1. Les TROIS branches de verdict, a dose imposee.
# ---------------------------------------------------------------------------------------------------

def test_run_distress_READS_the_dose_of_dream_rate_it_claims(monkeypatch):
    """Reponse connue x3, en forme close sur 5 seeds (sign_p unanime a n=5 : 2*C(5,5)/2^5 = 0.0625).

      DETRESSE  : court-vivants a 1.0 reve/tick, long-vivants a 0.5 -> delta = +0.5 sur les 5 seeds.
                  C'est le POSITIF, celui qui declencherait la Phase 2 causale.
      BENEFIQUE : dose EXACTEMENT inversee -> delta = -0.5. Branche negative n1 : sans elle, un
                  instrument aveugle au SIGNE passerait (classe E1).
      NEUTRE    : 3 seeds a +0.5, 2 seeds a -0.5 -> mediane +0.5 mais sign_p = 1.0 (k=3/n=5).
                  Branche negative n2, et la plus instructive : elle prouve que le verdict n'est PAS
                  porte par la seule mediane -- une mediane franchement positive ne suffit pas.
    On verifie aussi que `per_seed` transporte les DEUX taux mesures, pas seulement leur difference."""
    v = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5) for s in range(5)})
    assert v["verdict"] == "DETRESSE", v
    assert v["median_delta"] == pytest.approx(0.5)
    assert v["sign_p"] == pytest.approx(0.0625) and v["n_favorable"] == 5
    assert v["per_seed"][0]["rate_short"] == pytest.approx(1.0)
    assert v["per_seed"][0]["rate_long"] == pytest.approx(0.5)
    assert v["per_seed"][0]["n_short"] == 2 and v["per_seed"][0]["n_long"] == 2

    v = _inj6_run(monkeypatch, {s: _inj6_cellule(0.5, 1.0) for s in range(5)})
    assert v["verdict"] == "BENEFIQUE", v
    assert v["median_delta"] == pytest.approx(-0.5)
    assert v["sign_p"] == pytest.approx(0.0625) and v["n_favorable"] == 0

    mixte = {0: _inj6_cellule(1.0, 0.5), 1: _inj6_cellule(0.5, 1.0), 2: _inj6_cellule(1.0, 0.5),
             3: _inj6_cellule(0.5, 1.0), 4: _inj6_cellule(1.0, 0.5)}
    v = _inj6_run(monkeypatch, mixte)
    assert v["verdict"] == "NEUTRE", v
    assert v["median_delta"] == pytest.approx(0.5) and v["n_favorable"] == 3
    assert v["sign_p"] == pytest.approx(1.0)


def test_run_distress_REFUSES_a_unanimous_four_seed_run_and_ACCEPTS_five(monkeypatch):
    """La frontiere qui declenche la Phase 2 causale est `sign_p < 0.1`, et a effet UNANIME elle ne
    depend que du NOMBRE DE SEEDS : 4/4 -> 0.125 (refus), 5/5 -> 0.0625 (verdict). Dose STRICTEMENT
    identique dans les deux bras (delta = +0.5 partout), seul le nombre de seeds change : le refus ne
    peut donc venir que de la puissance. C'est le contre-exemple apparie de la branche DETRESSE --
    sans lui, un orchestrateur qui declarerait DETRESSE des que la mediane est positive passerait."""
    v4 = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5) for s in range(4)})
    assert v4["median_delta"] == pytest.approx(0.5) and v4["n_favorable"] == 4
    assert v4["sign_p"] == pytest.approx(0.125)
    assert v4["verdict"] == "NEUTRE", v4

    v5 = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5) for s in range(5)})
    assert v5["median_delta"] == pytest.approx(0.5) and v5["verdict"] == "DETRESSE"


# ---------------------------------------------------------------------------------------------------
# 2. Ce que les fonctions pures en aval ne peuvent PAS verifier : appariement, replication, cablage.
# ---------------------------------------------------------------------------------------------------

def test_run_distress_COUNTS_seeds_not_agents_as_replicates(monkeypatch):
    """Unite de replication du depot : l'ERE/le SEED, jamais l'agent (les agents d'une ere partagent
    monde, init et optimiseur). Reponse connue : 3 seeds unanimes -> sign_p = 2*C(3,3)/2^3 = 0.25,
    au-dessus de 0.1 -> NEUTRE malgre un effet parfaitement net et unanime.

    Contre-epreuve appariee : la MEME dose avec 100 agents par ere (50 courts / 50 longs) doit rendre
    EXACTEMENT le meme sign_p. Si l'orchestrateur poolait les individus, la puissance exploserait
    (300 individus tous du meme cote) et le verdict basculerait en DETRESSE -- c'est la
    pseudo-replication mesuree le 2026-09-01 (n=900 ticks au lieu de 3 seeds), qui avait NEUTRALISE une
    garde `sign_p` posee le matin meme."""
    petit = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5, n=2) for s in range(3)})
    assert petit["sign_p"] == pytest.approx(0.25) and petit["verdict"] == "NEUTRE", petit
    assert len(petit["per_seed"]) == 3

    gros = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5, n=50) for s in range(3)})
    assert gros["per_seed"][0]["n_short"] == 50 and gros["per_seed"][0]["n_long"] == 50
    assert gros["median_delta"] == pytest.approx(petit["median_delta"])
    assert gros["sign_p"] == pytest.approx(0.25), (
        "la puissance a suivi le nombre d'AGENTS : l'unite de replication n'est plus le seed")
    assert gros["verdict"] == "NEUTRE", gros


def test_run_distress_PAIRS_each_split_with_the_seed_that_produced_it(monkeypatch):
    """Appariement : chaque ligne de `per_seed` doit porter la mesure DU seed qu'elle nomme. Dose
    volontairement TOUTE DIFFERENTE et non ordonnee (seeds 7, 3, 5 ; deltas +0.5, -0.5, 0.0), donc
    n'importe quelle permutation, duplication ou decalage d'indice est visible dans les taux eux-memes
    -- pas seulement dans le verdict, qui est ici insensible a l'ordre (mediane 0.0 -> NEUTRE).
    Un seed non prevu leverait KeyError dans l'ere factice."""
    doses = {7: _inj6_cellule(1.0, 0.5), 3: _inj6_cellule(0.25, 0.75), 5: _inj6_cellule(0.9, 0.9)}
    v = _inj6_run(monkeypatch, doses, seeds=[7, 3, 5])

    attendu = {7: (1.0, 0.5, 0.5), 3: (0.25, 0.75, -0.5), 5: (0.9, 0.9, 0.0)}
    assert [p["seed"] for p in v["per_seed"]] == [7, 3, 5], v["per_seed"]
    for p in v["per_seed"]:
        rs, rl, d = attendu[p["seed"]]
        assert p["rate_short"] == pytest.approx(rs) and p["rate_long"] == pytest.approx(rl), p
        assert p["delta"] == pytest.approx(d), p
    assert v["median_delta"] == pytest.approx(0.0) and v["verdict"] == "NEUTRE"
    assert v["n_favorable"] == 1
    # le delta NUL est retire du test de signe (evite k>n) : effectifs = {+0.5, -0.5} -> p = 1.0
    assert v["sign_p"] == pytest.approx(1.0)


def test_run_distress_WIRES_the_sweet_spot_regime_into_EVERY_era(monkeypatch):
    """Le verdict n'a de sens qu'au regime que la docstring annonce : organe a 100 %
    (organ_fraction=1.0) au SWEET SPOT (metab 0.25, payoff 3.0). Reponse connue : 3 seeds, cible
    `famine`, 7 agents, 33 ticks, base partagee sentinelle -> 3 eres, une par seed, dans l'ordre, TOUTES
    au meme regime, et le bloc `config` archive doit dire la meme chose que ce qui a ete lance.

    Ce que ce test attrape et qu'aucun verdict ne montrerait : une ere lancee a organ_fraction=0.5
    (la moitie de la cohorte SANS organe -> le taux de reve median tombe mecaniquement sans que le
    reve ait rien fait), un `metab`/`payoff` letal au lieu du sweet spot, un `shared_db` perdu en
    route, ou un seed reutilise (qui rendrait deux replicats identiques passes pour independants)."""
    journal = []
    doses = {11: _inj6_cellule(1.0, 0.5), 12: _inj6_cellule(1.0, 0.5), 13: _inj6_cellule(1.0, 0.5)}
    v = _inj6_run(monkeypatch, doses, seeds=[11, 12, 13], journal=journal,
                  target="famine", num_agents=7, max_ticks=33)

    assert len(journal) == 3, journal
    assert [e["seed"] for e in journal] == [11, 12, 13], journal
    assert all(e["organ_fraction"] == 1.0 for e in journal), (
        "une ere n'est PAS a organe 100 % : le taux de reve mesure n'est plus celui d'une cohorte "
        "entierement porteuse")
    assert all(e["metab"] == 0.25 and e["payoff"] == 3.0 for e in journal), (
        "le regime passe n'est pas le sweet spot documente")
    assert all(e["target"] == "famine" for e in journal)
    assert all(e["num_agents"] == 7 and e["max_ticks"] == 33 for e in journal)
    assert all(e["shared_db"] == _INJ6_DB for e in journal)
    assert v["config"] == {"target": "famine", "seeds": [11, 12, 13],
                           "num_agents": 7, "max_ticks": 33,
                           "organ_fraction": 1.0, "metab": 0.25, "payoff": 3.0,
                           "age_floor": 10}, v["config"]
    # Le bloc archive doit dire ce qui a REELLEMENT tourne. Compare au JOURNAL, pas a une constante
    # recopiee : une derive entre l'appel et la provenance rougit ICI. Avant le 2026-09-08 le bloc
    # `config` taisait entierement le regime (organ_fraction, sweet spot, plancher d'age) -- le
    # verdict n'a de sens qu'a ce regime, et aucun rapport archive ne pouvait dire lequel.
    assert all(e["organ_fraction"] == v["config"]["organ_fraction"] for e in journal), journal
    assert all(e["metab"] == v["config"]["metab"] and e["payoff"] == v["config"]["payoff"]
               for e in journal), journal


def test_run_distress_REFUSES_degenerate_arguments_BEFORE_any_era(monkeypatch):
    """La garde d'arguments doit lever AVANT la moindre ere : un `run_era_organ` piege prouve OU elle
    est posee, pas seulement QU'elle leve. Trois doses degenerees : aucun seed, 0 agent, 0 tick.

    Contre-exemple apparie (classe E1) : avec les MEMES arguments rendus valides, le piege DOIT etre
    atteint. Sans lui, un `run_distress` qui ne lancerait jamais rien passerait ce test."""
    import tools.dream_distress_probe as D

    atteint = []

    def _piege(*a, **kw):
        atteint.append(a)
        raise AssertionError("run_era_organ atteint : la garde d'arguments est posee TROP TARD")

    monkeypatch.setattr(D, "run_era_organ", _piege)
    for kw in ({"seeds": []}, {"num_agents": 0}, {"max_ticks": 0}):
        args = {"seeds": [0], "target": "stoneage", "num_agents": 4, "max_ticks": 10,
                "shared_db": None}
        args.update(kw)
        with pytest.raises(ValueError, match="degenere"):
            D.run_distress(**args)
    assert atteint == [], "une ere a demarre malgre un argument degenere"

    with pytest.raises(AssertionError, match="TROP TARD"):
        D.run_distress(seeds=[0], target="stoneage", num_agents=4, max_ticks=10, shared_db=None)
    assert len(atteint) == 1, "le piege n'est jamais atteint : le test precedent ne prouvait rien"


def test_run_distress_MEASURES_without_building_any_world(monkeypatch):
    """Controle du SEAM et du COUT en une reponse connue : 12 eres injectees doivent se mesurer en une
    fraction de seconde. Si `run_distress` appelait `tools.dreaming_probe.run_era_organ` (le module
    source) au lieu de son propre attribut de module, l'injection serait un NO-OP silencieux : 12
    mondes seraient construits (minutes, bail `kuzu`, non-reproductibilite) et le verdict ci-dessous
    ne serait pas celui de la dose. Le budget est genereux (5 s) : c'est un garde-fou de seam, pas un
    benchmark."""
    t0 = time.time()
    v = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5) for s in range(12)})
    ecoule = time.time() - t0
    assert v["verdict"] == "DETRESSE" and v["sign_p"] == pytest.approx(2.0 / 4096)
    assert ecoule < 5.0, f"{ecoule:.1f} s pour 12 eres injectees : un monde a ete construit"


# ---------------------------------------------------------------------------------------------------
# 3. NON-REGRESSION -- anciens `xfail(strict=True)` de ce fichier, defauts CORRIGES dans
#    `tools/dream_distress_probe.py` le 2026-09-08 (INJ6). Le correctif avait laisse les quatre
#    marqueurs en place : ils sont devenus des XPASS(strict), donc QUATRE TESTS ROUGES, et la suite
#    passait de 11 verts a « 4 failed, 7 passed » sans que rien ne l'annonce (classe E14 -- une garde
#    ajoutee change le contrat de TOUTES ses fixtures ; relancer et reparer les tests existants fait
#    partie du correctif). Trouve par le refutateur, qui a relance la suite SOEUR en entier.
#
#    Regle du depot : une entree ABSENTE, VIDE ou SANS AMPLITUDE rend un INDETERMINE explicite ou
#    leve. Jamais une affirmation de FOND. Chaque bloc exige desormais le statut EXACT (un
#    `startswith('INDETERMINE')` accepterait n'importe quelle cause, y compris la mauvaise) et porte
#    son CONTRE-EXEMPLE APPARIE (classe E1) : une garde qui refuserait TOUJOURS est pire que le
#    defaut, et sans la moitie negative ces quatre tests la laisseraient passer.
# ---------------------------------------------------------------------------------------------------

def test_run_distress_REFUSES_a_split_whose_short_lived_group_is_EMPTY(monkeypatch):
    """Reponse connue : 5 seeds ou les 4 agents de chaque ere ont le MEME age (20) et le MEME taux de
    reve (1.0). Il n'y a donc AUCUN contraste court/long a mesurer -- ni detresse ni benefice.

    DEFAUT CORRIGE (historique, garde par ce test) : `r_short = median(...) if short else 0.0` posait
    le taux du groupe ABSENT a 0.0 comme une MESURE. Quand tous les agents meurent au MEME age
    (extinction totale a `max_ticks`, cf. tools/dreaming_probe.py « la population s'eteint a 100 % »),
    la mediane d'age EGALE cet age, le groupe court-vivant est VIDE, et delta = 0.0 - rate_long = -1.0
    sur CHAQUE seed -> verdict=BENEFIQUE, median_delta=-1.0, sign_p=0.0625 : « les long-vivants revent
    plus, le reve protege », affirmation de fond PUBLIEE depuis un split dont un cote n'existe pas."""
    plat = [_inj6_agent(20, 20) for _ in range(4)]          # ages identiques, taux identique 1.0
    v = _inj6_run(monkeypatch, {s: list(plat) for s in range(5)})
    assert v["per_seed"][0]["n_short"] == 0, v["per_seed"][0]   # le groupe compare est VIDE
    assert all(p["status"] == "INDETERMINE_GROUPE_VIDE" for p in v["per_seed"]), v["per_seed"]
    assert all(p["delta"] is None and p["rate_short"] is None for p in v["per_seed"]), v["per_seed"]
    assert all(p["rate_long"] == pytest.approx(1.0) for p in v["per_seed"]), (
        "le cote REELLEMENT mesure doit rester publie : l'indetermination porte sur le CONTRASTE")
    assert v["verdict"] == "INDETERMINE_AUCUNE_MESURE", (v["verdict"], v["median_delta"])
    assert v["median_delta"] is None and v["sign_p"] is None, v
    assert v["n_mesurable"] == 0 and v["n_indetermine"] == 5, v
    # Le POURQUOI voyage avec l'indetermination -- sans ce compte, l'INDETERMINE est ANONYME et se
    # relit comme un incident d'outil au lieu de nommer un regime du monde. (Trouve decoratif par
    # mutation : neutraliser le bloc `raisons` ne faisait rougir AUCUN test.)
    assert v["raisons"] == {"INDETERMINE_GROUPE_VIDE": 5}, v["raisons"]

    # CONTRE-EXEMPLE APPARIE (classe E1) : deux groupes PEUPLES a la meme dose -> la garde se tait,
    # le contraste est MESURE et le verdict revient. Sans lui, un run_distress qui refuserait tout
    # passerait les assertions ci-dessus.
    ok = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5) for s in range(5)})
    assert ok["verdict"] == "DETRESSE" and ok["raisons"] == {}, ok
    assert all(p["status"] == "OK" for p in ok["per_seed"]), ok["per_seed"]


def test_run_distress_REFUSES_a_cohort_with_nothing_left_to_measure(monkeypatch):
    """Deux portes d'entree du meme defaut, en reponse connue : (a) chaque ere rend une liste VIDE ;
    (b) chaque ere rend 4 agents tous plus jeunes que `age_floor=10`. Dans les deux cas `n_short` et
    `n_long` valent 0 -- l'instrument SAIT qu'il n'a rien retenu.

    DEFAUT CORRIGE (historique, garde par ce test) : `if not kept: return {'rate_short': 0.0,
    'rate_long': 0.0, 'delta': 0.0, ...}` rendait un delta NUL comme une MESURE dans ces deux
    regimes, et `run_distress` agregeait ces zeros en verdict=NEUTRE, median_delta=0.0 -- « les reves
    ne se concentrent pas chez les mourants », le resultat NEGATIF que la sonde cherchait, obtenu sans
    une seule mesure. La garde d'ARGUMENTS ne couvre pas ce cas : elle refuse `num_agents<=0` A
    L'APPEL, pas une cohorte vide MESUREE."""
    vide = _inj6_run(monkeypatch, {s: [] for s in range(5)})
    assert all(p["n_short"] == 0 and p["n_long"] == 0 for p in vide["per_seed"]), vide["per_seed"]
    assert all(p["status"] == "INDETERMINE_AUCUN_AGENT_MESURABLE" for p in vide["per_seed"]), \
        vide["per_seed"]
    assert all(p["delta"] is None and p["rate_short"] is None for p in vide["per_seed"])
    assert vide["verdict"] == "INDETERMINE_AUCUNE_MESURE", (vide["verdict"], vide["median_delta"])
    assert vide["median_delta"] is None and vide["n_mesurable"] == 0
    assert vide["raisons"] == {"INDETERMINE_AUCUN_AGENT_MESURABLE": 5}, vide["raisons"]

    jeunes = [_inj6_agent(3, 3), _inj6_agent(4, 8), _inj6_agent(5, 0), _inj6_agent(2, 2)]
    sous_plancher = _inj6_run(monkeypatch, {s: list(jeunes) for s in range(5)})
    assert sous_plancher["verdict"] == "INDETERMINE_AUCUNE_MESURE", sous_plancher["verdict"]
    assert sous_plancher["raisons"] == {"INDETERMINE_AUCUN_AGENT_MESURABLE": 5}, sous_plancher

    # CONTRE-EXEMPLE APPARIE (classe E1) : les MEMES agents, memes `total_dreams`, VIEILLIS au-dessus
    # du plancher. Seul l'age change -> le refus vient bien du plancher d'age, pas d'une garde qui
    # refuserait toute cohorte. Forme close : ages [30,40,50,20] -> mediane 35 -> short {30,20} taux
    # {0.1,0.1} -> 0.1 ; long {40,50} taux {0.2,0.0} -> 0.1 ; delta = 0.0 -> NEUTRE MESURE.
    vieux = [_inj6_agent(30, 3), _inj6_agent(40, 8), _inj6_agent(50, 0), _inj6_agent(20, 2)]
    mesure = _inj6_run(monkeypatch, {s: list(vieux) for s in range(5)})
    assert all(p["status"] == "OK" for p in mesure["per_seed"]), mesure["per_seed"]
    assert mesure["per_seed"][0]["delta"] == pytest.approx(0.0), mesure["per_seed"][0]
    assert mesure["n_mesurable"] == 5 and mesure["raisons"] == {}, mesure
    assert mesure["verdict"] == "NEUTRE", mesure


def test_run_distress_REFUSES_a_cohort_where_NOBODY_dreamt(monkeypatch):
    """Reponse connue : 12 seeds, cohortes bien formees (ages 10 et 30, au-dessus du plancher, les
    deux groupes peuples) mais `total_dreams=0` partout. Le split est valide, la mesure ne l'est pas.

    DEFAUT CORRIGE (historique, garde par ce test) : la grandeur mesuree est un TAUX DE REVE. Quand
    une cohorte entierement porteuse de l'organe (`organ_fraction=1.0`) ne reve PAS UNE SEULE FOIS,
    la question « les reves se concentrent-ils chez les mourants ? » n'a pas d'objet -- c'est une
    panne d'INTERVENTION, pas un fait sur la detresse. Le code rendait delta = 0.0 - 0.0 sur chaque
    seed et publiait verdict=NEUTRE, sign_p=1.0, n_favorable=0/12, qui se lit sur un record comme un
    negatif solide a 12 seeds. Aucune amplitude n'etait verifiee nulle part."""
    sans_reve = [_inj6_agent(10, 0), _inj6_agent(10, 0), _inj6_agent(30, 0), _inj6_agent(30, 0)]
    v = _inj6_run(monkeypatch, {s: list(sans_reve) for s in range(12)})
    assert v["per_seed"][0]["n_short"] == 2 and v["per_seed"][0]["n_long"] == 2  # split VALIDE
    assert all(p["status"] == "INDETERMINE_AUCUN_REVE" for p in v["per_seed"]), v["per_seed"]
    assert all(p["delta"] is None for p in v["per_seed"]), v["per_seed"]
    assert all(p["rate_short"] == 0.0 and p["rate_long"] == 0.0 for p in v["per_seed"]), (
        "les taux ONT ete mesures (et valent zero) : c'est leur DIFFERENCE qui n'a pas d'objet")
    assert v["verdict"] == "INDETERMINE_AUCUNE_MESURE", (v["verdict"], v["sign_p"], v["n_favorable"])
    assert v["sign_p"] is None and v["median_delta"] is None, v
    assert v["n_favorable"] == 0 and v["n_mesurable"] == 0 and v["n_indetermine"] == 12, v
    assert v["raisons"] == {"INDETERMINE_AUCUN_REVE": 12}, v["raisons"]

    # CONTRE-EXEMPLE APPARIE (classe E1) : UN SEUL reve dans toute la cohorte suffit a rendre la
    # mesure legitime -- la garde porte sur l'amplitude de l'INTERVENTION, pas sur son RESULTAT.
    # DETTE GELEE ICI, PAS CORRIGEE (EDR-094) : les deux taux MEDIANS valent encore 0.000 alors que
    # la cohorte a reve (le reve est une conduite de MINORITE), donc delta = 0.0 -> NEUTRE. C'est le
    # LAVAGE PAR LA MEDIANE, un defaut d'AGREGAT distinct de l'amplitude, ENCORE OUVERT :
    # docs/EDR/094_Dream_Distress_Median_Washout_Dreaming_Is_A_Minority_Behavior.md. Le geler ici
    # empeche (a) de le corriger PAR ACCIDENT en croyant durcir l'amplitude, et (b) de retirer en
    # silence le NEUTRE publie par ce record.
    rare = [_inj6_agent(10, 0), _inj6_agent(10, 0), _inj6_agent(10, 5),
            _inj6_agent(30, 0), _inj6_agent(30, 0), _inj6_agent(30, 0)]
    vr = _inj6_run(monkeypatch, {s: list(rare) for s in range(12)})
    assert all(p["status"] == "OK" for p in vr["per_seed"]), vr["per_seed"]
    assert vr["per_seed"][0]["rate_short"] == 0.0 and vr["per_seed"][0]["rate_long"] == 0.0
    assert vr["per_seed"][0]["delta"] == 0.0 and vr["raisons"] == {}, vr
    assert vr["verdict"] == "NEUTRE", vr


def test_run_distress_NAMES_the_reason_when_only_SOME_seeds_are_unmeasurable(monkeypatch):
    """Le cas MIXTE, que ni le tout-mesure ni le tout-indetermine ne couvrent, et le seul ou l'unite
    de replication peut changer EN SILENCE : 4 seeds mesures a delta=+0.5, 1 seed eteint (l'ere ne
    rend aucun agent). Laisser tomber le seed muet publierait un verdict sur n=4 en annoncant n=5 --
    et ce sont justement les seeds eteints, correles au phenomene, qui disparaitraient.

    Reponse connue : INDETERMINE_MESURES_PARTIELLES, 4 mesurables / 1 indetermine, la mediane des
    seeds MESURES reste publiee a cote (0.5) sans etre un verdict, et `raisons` NOMME la cause."""
    doses = {0: _inj6_cellule(1.0, 0.5), 1: _inj6_cellule(1.0, 0.5), 2: _inj6_cellule(1.0, 0.5),
             3: _inj6_cellule(1.0, 0.5), 4: []}
    v = _inj6_run(monkeypatch, doses, seeds=[0, 1, 2, 3, 4])
    assert v["verdict"] == "INDETERMINE_MESURES_PARTIELLES", v["verdict"]
    assert v["n_mesurable"] == 4 and v["n_indetermine"] == 1, v
    assert v["median_delta"] == pytest.approx(0.5), "la mesure des seeds mesures reste publiee"
    assert v["raisons"] == {"INDETERMINE_AUCUN_AGENT_MESURABLE": 1}, v["raisons"]
    assert v["per_seed"][4]["delta"] is None and v["per_seed"][4]["seed"] == 4

    # CONTRE-EXEMPLE APPARIE (classe E1) : les MEMES 4 mesures SANS le trou. Le verdict redevient
    # possible -- et vaut NEUTRE parce qu'a 4 seeds unanimes sign_p=0.125 > 0.1 : c'est bien le TROU
    # qui etait teste, pas la puissance, et la branche PARTIEL n'a pas avale un verdict qui existait.
    plein = _inj6_run(monkeypatch, {s: _inj6_cellule(1.0, 0.5) for s in range(4)})
    assert plein["verdict"] == "NEUTRE" and plein["n_indetermine"] == 0, plein
    assert plein["sign_p"] == pytest.approx(0.125) and plein["raisons"] == {}, plein


def test_run_distress_KEEPS_every_seed_when_seeds_is_an_ITERATOR(monkeypatch):
    """Reponse connue : la MEME dose que le cas DETRESSE (5 seeds, delta +0.5), passee en generateur.
    Les 5 eres doivent etre lancees et le verdict rester DETRESSE.

    DEFAUT CORRIGE (historique, garde par ce test) : `seeds` etait ITERE DEUX FOIS -- `not
    list(seeds)` dans la garde, puis `for seed in seeds`. Passe un iterateur (generateur, `map`,
    `zip` -- la forme meme que produit un `(int(s) for s in ...)` d'appelant), la garde le VIDAIT, la
    boucle ne tournait JAMAIS, `per_seed` restait vide et l'orchestrateur publiait
    verdict=INDETERMINE_AUCUN_SEED avec `config.seeds=[]` : le rapport ARCHIVE niait les 5 seeds
    demandes, zero ere lancee, aucune erreur levee. Meme defaut que `run_s2(worlds=<iterateur>)`."""
    doses = {s: _inj6_cellule(1.0, 0.5) for s in range(5)}
    journal = []
    D = _inj6_injecte(monkeypatch, doses, journal)
    v = D.run_distress(seeds=(s for s in range(5)), target="stoneage", num_agents=4, max_ticks=10,
                       shared_db=_INJ6_DB)
    assert len(journal) == 5, (
        f"{len(journal)} ere(s) lancee(s) pour 5 seeds demandes : la garde a consomme l'iterateur")
    assert [e["seed"] for e in journal] == [0, 1, 2, 3, 4], journal
    assert v["config"]["seeds"] == [0, 1, 2, 3, 4], v["config"]
    assert v["verdict"] == "DETRESSE", v

    # CONTRE-EXEMPLE APPARIE (classe E1) : materialiser l'iterable ne doit pas rendre la garde
    # d'ARGUMENTS increvable. Un generateur VIDE reste un argument degenere -- il doit LEVER, et
    # AVANT toute ere. Sans cette moitie, la seule assertion qui couvrait `seeds = list(seeds)`
    # etait celle du haut : mesure par mutation, retirer la materialisation ne faisait alors rougir
    # AUCUN test VERT (le seul temoin etait ce fichier, laisse ROUGE en XPASS strict).
    with pytest.raises(ValueError, match="degenere"):
        D.run_distress(seeds=(s for s in []), target="stoneage", num_agents=4, max_ticks=10,
                       shared_db=_INJ6_DB)
    assert len(journal) == 5, "une ere a demarre sur un generateur VIDE"
