import numpy as np
from types import SimpleNamespace
from tools.dreaming_probe import organ_prevalence, _has_organ, q2_split
from src.curriculum.competence import AGE_REF


def _agent(organ_on):
    g = SimpleNamespace(organ_genes=np.array([organ_on, False], dtype=bool))
    return {"model": SimpleNamespace(genome=g)}


def test_organ_prevalence_known_fractions():
    # REFUTATION 2026-09-08 : la ligne `organ_prevalence([]) == 0.0` qui vivait ici GELAIT la
    # convention fautive -- cf. `test_organ_prevalence_returns_nan_on_an_EMPTY_cohort` plus bas.
    # Les fractions MESUREES, elles, sont inchangees.
    assert organ_prevalence([_agent(True), _agent(True)]) == 1.0
    assert organ_prevalence([_agent(False), _agent(False)]) == 0.0
    assert organ_prevalence([_agent(True), _agent(False)]) == 0.5


def test_has_organ_robust_to_missing():
    assert _has_organ({"model": SimpleNamespace(genome=SimpleNamespace(organ_genes=None))}) is False
    assert _has_organ({"model": None}) is False
    assert _has_organ(_agent(True)) is True


def test_q2_split_separates_dreamers():
    stats = [
        {"age": int(AGE_REF), "total_dreams": 3},      # rêveur, compétence haute
        {"age": int(AGE_REF), "total_dreams": 1},      # rêveur
        {"age": 10, "total_dreams": 0},                # non-rêveur, basse
        {"age": 10, "total_dreams": 0},                # non-rêveur
    ]
    out = q2_split(stats)
    assert out["n_dreamers"] == 2 and out["n_nondreamers"] == 2
    assert out["dreamers_competence"] == 1.0           # médiane âge = AGE_REF
    assert out["delta"] > 0                             # rêveurs > non-rêveurs


def test_q2_split_handles_zero_dreamers():
    """REECRIT le 2026-09-08 (classe E14 : le correctif change le contrat de SES fixtures).

    La ligne `dreamers_competence == 0.0` qui vivait ici GELAIT la convention fautive -- exactement
    le motif deja rencontre sur `test_organ_prevalence_known_fractions` : un defaut protege par un
    test vert. Un groupe VIDE n'a pas une competence de 0.0, il n'en a AUCUNE ; et c'est ce 0.0 qui
    faisait de `delta` la competence ABSOLUE des reveurs au lieu d'un contraste."""
    import math
    out = q2_split([{"age": 10, "total_dreams": 0}])
    assert out["n_dreamers"] == 0 and out["n_nondreamers"] == 1
    assert math.isnan(out["dreamers_competence"]), "groupe VIDE -> INDETERMINE, pas 0.0"
    assert math.isnan(out["delta"]), "sans groupe de reference, le contraste n'existe pas"
    assert out["nondreamers_competence"] == pytest.approx(10 / AGE_REF)


def test_q2_split_STILL_returns_0_for_a_group_that_REALLY_died_at_birth():
    """NEGATIF APPARIE au precedent (classe E1). Le correctif ne doit PAS rendre l'instrument muet
    sur une survie REELLEMENT nulle : un groupe NON VIDE dont tous les agents meurent a l'age 0 vaut
    0.0, exactement, et le contraste reste MESURE. Sans ce cas, remplacer tout 0.0 par nan passerait
    le test positif tout en detruisant la mesure."""
    out = q2_split([{"age": 0, "total_dreams": 3}, {"age": 100, "total_dreams": 0}])
    assert out["dreamers_competence"] == 0.0            # mesure REELLE : ils sont morts a la naissance
    assert out["nondreamers_competence"] == pytest.approx(0.5)
    assert out["delta"] == pytest.approx(-0.5), "un prejudice MESURE doit rester publiable"


def test_q2_split_partitions_EVERY_agent_between_the_two_groups():
    """Specificite (forme (c) du biais : troncature muette). La partition est `> 0` / `<= 0` : aucun
    agent ne peut tomber HORS des deux groupes. Avant, `== 0` laissait un `total_dreams` negatif
    disparaitre des DEUX medianes sans que rien ne le signale. Le seuil du split reste STRICT."""
    stats = [{"age": 10, "total_dreams": 1}, {"age": 10, "total_dreams": 0},
             {"age": 10, "total_dreams": -1}]
    out = q2_split(stats)
    assert out["n_dreamers"] + out["n_nondreamers"] == len(stats)
    assert out["n_dreamers"] == 1, "le seuil du split reste `> 0`, strictement"


from tools.dreaming_probe import dreaming_verdict


def test_verdict_four_cases():
    # survit (sweet toléré ET pression>0) ET paye (q2a delta>pay_eps OU q2b ratio>1+pay_eps)
    assert dreaming_verdict(0.0, -0.3, 0.10, 1.20) == "SURVIT_ET_PAYE"
    assert dreaming_verdict(0.0, -0.3, 0.00, 1.00) == "SURVIT_PAS_PAYE"
    # ne survit pas (sweet purgé) mais paye
    assert dreaming_verdict(-0.4, -0.45, 0.10, 1.20) == "PAYE_PAS_SURVIT"
    assert dreaming_verdict(-0.4, -0.45, 0.00, 1.00) == "MORT"


import pytest


import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dreaming_probe as dp
    monkeypatch.setattr(dp, "run_q1", lambda *a, **k: {
        "delta_prev_sweet": 0.0, "delta_prev_lethal": -0.3, "pressure": 0.3,
        "per_seed_sweet": [0.0], "per_seed_lethal": [-0.3]})
    monkeypatch.setattr(dp, "run_q2", lambda *a, **k: {
        "q2a_delta": 0.10, "q2b_ratio": 1.20, "n_favorable": 1, "n": 1, "sign_p": 1.0,
        "total_dreams_seen": 12, "per_seed_delta": [0.10], "per_seed_ratio": [1.20]})
    monkeypatch.setattr(dp.async_logger, "start", lambda: None)
    monkeypatch.setattr(dp.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dp, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DP_SEEDS", "0")
    monkeypatch.setenv("DP_MODE", "both")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> faire en sorte que monkeypatch POSSEDE la cle pour
    # la restaurer au teardown (sinon fuite vers les autres tests de la session, ex. test_async_logger).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dp.main()
    assert result["verdict"] == "SURVIT_ET_PAYE"
    files = glob.glob(str(tmp_path / "results" / "dreaming_probe_*.json"))
    assert files, "provenance non écrite"
    data = json.loads(open(files[0], encoding="utf-8").read())
    assert data["data"]["verdict"] == "SURVIT_ET_PAYE"
    assert "commit" in data and "git_dirty" in data


@pytest.mark.slow
def test_run_era_organ_smoke_seeds_organ(monkeypatch):
    """Smoke biosphère : une ère courte, ~50% organe semé -> renvoie des stats avec has_organ booléen."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from tools.dreaming_probe import run_era_organ, _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        # db appartient au worker async_logger -> libere par stop()
        stats = run_era_organ("stoneage", seed=0, organ_fraction=0.5, metab=0.25, payoff=3.0,
                              num_agents=20, max_ticks=40, shared_db=db)
    finally:
        async_logger.stop()
    assert isinstance(stats, list)
    for s in stats:
        # Sur-ensemble, PAS égalité : la sonde expose désormais `founder` (appariement de cohorte,
        # EDR-DREAM-001) et `altars_solved`/`spears_crafted`/`preys_eaten` (fil exploration,
        # EDR-DREAM-002). Une égalité STRICTE de clés transforme tout enrichissement de sortie en
        # FAUSSE régression — 2ᵉ occurrence du motif dans la journée (cf. test_cognitive_demand_inworld,
        # où la variante `skipif RUN_SLOW` du même motif aurait cassé EN SILENCE).
        assert {"age", "total_dreams", "has_organ"} <= set(s)
        assert isinstance(s["has_organ"], bool)


# ======================================================================================================
# 2026-09-08 -- CALIBRATION de `run_q1` / `_prevalence_from_stats` sur DEUX defauts REELS, exposes par
# `tests/sandbox/test_orchestrator_injection.py` (injection a dose connue) :
#
#   (a) la garde CONSOMMAIT les seeds (`not list(seeds)`) sans les materialiser -> avec un iterateur la
#       garde passait, la boucle ne tournait ZERO fois, et les defauts `else 0.0` rendaient
#       `pressure=0.0` comme une MESURE (verdict MORT fabrique a partir de RIEN).
#   (b) une ere rendant une cohorte VIDE donnait `_prevalence_from_stats -> 0.0`, converti en
#       `delta = 0.0 - 0.5 = -0.5`, c.-a-d. l'affirmation MAXIMALE « organe INTEGRALEMENT purge », que
#       `dreaming_verdict` transforme en MORT. Forme (a) du biais systematique du depot : entree vide
#       -> affirmation NEGATIVE de fond.
#
# CHAQUE comportement ajoute a ici son CAS NEGATIF APPARIE (classe E1) : un correctif qui rendrait la
# garde INCREVABLE (elle refuse tout) ou l'instrument MUET (il ne sait plus dire « purge totale » quand
# la purge est REELLEMENT observee) serait pire que le defaut. Les paires sont explicitement etiquetees.
# ======================================================================================================


def _dp_agent(has_organ):
    """Cellule-agent factice portant TOUTES les cles que `run_era_organ` produit."""
    return {"age": 10, "total_dreams": 0, "has_organ": bool(has_organ), "founder": True,
            "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}


def _dp_cohorte(prevalence, n=8):
    """Cohorte de `n` agents dont exactement `prevalence*n` portent l'organe (dose EXACTE a n=8)."""
    k = int(round(prevalence * n))
    return [_dp_agent(i < k) for i in range(n)]


def _dp_injecte(monkeypatch, fabrique):
    """Remplace `run_era_organ` DANS le module (global resolu a l'appel) et rend le module."""
    import tools.dreaming_probe as dp
    if fabrique is not None:
        monkeypatch.setattr(dp, "run_era_organ", fabrique)
    return dp


def _dp_par_regime(prev_sweet, prev_lethal, n=8, journal=None):
    """Fabrique distinguant les regimes par leur DOSE ENERGETIQUE : (0.25, 3.0)=sweet, (1.0, 1.0)=letal."""
    def _f(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        if journal is not None:
            journal.append((seed, metab, payoff))
        p = prev_sweet if (metab, payoff) == (0.25, 3.0) else prev_lethal
        return _dp_cohorte(p, n=n)
    return _f


# ------------------------------------------------------------------------------------------------------
# (a) MATERIALISATION DES SEEDS
# ------------------------------------------------------------------------------------------------------

def test_run_q1_MEASURES_every_seed_of_an_ITERATOR(monkeypatch):
    """POSITIF. Dose connue : 4 seeds passes en GENERATEUR, sweet 0.75 / letal 0.25 -> pressure=+0.50.
    Avant le correctif, `not list(seeds)` mangeait le generateur : 0 seed mesure, pressure=0.0 rendue
    comme une mesure. On verifie AUSSI le nombre d'appels (2 par seed = 8) : une materialisation qui
    consommerait DEUX fois (garde puis boucle) laisserait 0 appel, une qui bouclerait deux fois en
    ferait 16."""
    appels = []
    dp = _dp_injecte(monkeypatch, _dp_par_regime(0.75, 0.25, journal=appels))
    r = dp.run_q1((s for s in (3, 5, 7, 11)), "stoneage", 8, 5, None)
    assert len(r["per_seed_sweet"]) == 4 and len(r["per_seed_lethal"]) == 4
    assert r["per_seed_sweet"] == pytest.approx([0.25] * 4)
    assert r["per_seed_lethal"] == pytest.approx([-0.25] * 4)
    assert r["pressure"] == pytest.approx(0.50)
    assert len(appels) == 8, appels
    assert sorted({s for s, _, _ in appels}) == [3, 5, 7, 11], "les seeds du generateur, tels quels"


def test_run_q1_STILL_REFUSES_an_EMPTY_iterator_before_any_era(monkeypatch):
    """NEGATIF APPARIE au precedent (classe E1). Materialiser les seeds pourrait rendre la garde
    INCAPABLE DE SE DECLENCHER si on l'avait au passage relachee. Reponse connue : les formes
    d'iterable VIDE (generateur epuise, `iter([])`, `map` sur du vide, tuple/liste vides) doivent
    TOUJOURS lever, et lever EN TETE -- ZERO appel a `run_era_organ`, donc refus instantane."""
    compteur = {"n": 0}

    def _compte(*a, **kw):
        compteur["n"] += 1
        return _dp_cohorte(0.5)

    dp = _dp_injecte(monkeypatch, _compte)
    for vide in ((s for s in ()), iter([]), map(int, []), (), []):
        with pytest.raises(ValueError, match="degenere"):
            dp.run_q1(vide, "stoneage", 8, 5, None)
        assert compteur["n"] == 0, ("la garde doit rester EN TETE, avant toute ere", vide)
    # contre-epreuve : la garde n'est pas devenue increvable non plus
    dp.run_q1(iter([0]), "stoneage", 8, 5, None)
    assert compteur["n"] == 2, "un iterateur NON vide doit franchir la garde et produire 2 eres"


def test_run_q1_does_NOT_consume_the_seeds_TWICE(monkeypatch):
    """Specificite : le `list()` doit etre pose UNE fois, DEVANT la garde. Un correctif naif qui
    laisserait `not list(seeds)` en place ET ajouterait `seeds = list(seeds)` APRES rendrait encore 0
    seed mesure. Reponse connue : un iterateur d'UN seed -> exactement 1 valeur par bras."""
    dp = _dp_injecte(monkeypatch, _dp_par_regime(1.0, 0.0))
    r = dp.run_q1(iter([42]), "stoneage", 8, 5, None)
    assert r["per_seed_sweet"] == pytest.approx([0.5])
    assert r["per_seed_lethal"] == pytest.approx([-0.5])
    assert r["pressure"] == pytest.approx(1.0)


# ------------------------------------------------------------------------------------------------------
# (b) COHORTE VIDE -> INDETERMINE, JAMAIS « purge totale »
# ------------------------------------------------------------------------------------------------------

def test_prevalence_from_stats_returns_nan_on_an_EMPTY_cohort():
    """POSITIF. Reponse connue : sans agent il n'y a pas de prevalence -> nan (INDETERMINE), pas 0.0."""
    import math
    from tools.dreaming_probe import _prevalence_from_stats
    assert math.isnan(_prevalence_from_stats([]))


def test_prevalence_from_stats_STILL_returns_0_on_a_REAL_total_purge():
    """NEGATIF APPARIE au precedent (classe E1). Le correctif ne doit PAS rendre l'instrument muet sur
    une purge REELLEMENT observee : une cohorte NON VIDE dont aucun agent ne porte l'organe vaut 0.0,
    exactement, et les fractions intermediaires sont inchangees. Sans ce cas, remplacer tout 0.0 par
    nan passerait le test positif tout en detruisant la mesure."""
    from tools.dreaming_probe import _prevalence_from_stats
    assert _prevalence_from_stats(_dp_cohorte(0.0)) == 0.0
    assert _prevalence_from_stats(_dp_cohorte(0.25)) == pytest.approx(0.25)
    assert _prevalence_from_stats(_dp_cohorte(0.5)) == pytest.approx(0.5)
    assert _prevalence_from_stats(_dp_cohorte(1.0)) == 1.0


def test_run_q1_REFUSES_an_empty_era_and_NAMES_the_seed_and_the_regime(monkeypatch):
    """POSITIF. Reponse connue : une ere qui ne rend AUCUN agent est une absence de mesure. `run_q1`
    doit lever (et non rendre -0.5), en NOMMANT le seed et le regime fautifs -- un refus anonyme
    obligerait a re-simuler pour savoir ou regarder. Les deux regimes sont testes separement : un
    correctif qui n'aurait garde qu'un des deux bras passerait sinon."""
    dp = _dp_injecte(monkeypatch, None)

    def _sweet_vide(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        return [] if (metab, payoff) == (0.25, 3.0) else _dp_cohorte(0.25)

    def _letal_vide(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        return [] if (metab, payoff) == (1.0, 1.0) else _dp_cohorte(0.75)

    monkeypatch.setattr(dp, "run_era_organ", _sweet_vide)
    with pytest.raises(ValueError, match=r"ere sweet du seed 5 .*cohorte VIDE"):
        dp.run_q1([5, 6, 7], "stoneage", 8, 5, None)

    monkeypatch.setattr(dp, "run_era_organ", _letal_vide)
    with pytest.raises(ValueError, match=r"ere letal du seed 5 .*cohorte VIDE"):
        dp.run_q1([5, 6, 7], "stoneage", 8, 5, None)


def test_run_q1_REFUSES_at_the_FIRST_offending_seed_not_after_burning_the_others(monkeypatch):
    """POSITIF (cout). Reponse connue : 12 seeds, la cohorte est vide DES LE PREMIER -> au plus 2 eres
    doivent avoir tourne (le sweet et le letal du seed 0), pas 24. Une verification repoussee apres la
    boucle serait correcte sur le verdict et RUINEUSE sur le budget (les eres sont des simulations)."""
    appels = []

    def _vide(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        appels.append(seed)
        return []

    dp = _dp_injecte(monkeypatch, _vide)
    with pytest.raises(ValueError, match="cohorte VIDE"):
        dp.run_q1(list(range(12)), "stoneage", 8, 5, None)
    assert set(appels) == {0} and len(appels) <= 2, appels


def test_run_q1_STILL_REPORTS_a_REAL_total_purge_as_MORT(monkeypatch):
    """NEGATIF APPARIE aux deux precedents (classe E1) -- LE cas qui empeche le correctif d'etre un
    baillon. Une purge REELLE (8 agents mesures, AUCUN porteur, dans les deux regimes) doit toujours
    produire delta_sweet = -0.5, et la chaine complete doit toujours pouvoir prononcer MORT. Sans lui,
    « refuser la cohorte vide » aurait pu devenir « ne plus jamais rendre de negatif fort », ce qui
    detruirait la seule affirmation que la sonde existe pour pouvoir faire."""
    dp = _dp_injecte(monkeypatch, _dp_par_regime(0.0, 0.0))
    r = dp.run_q1([0, 1, 2], "stoneage", 8, 5, None)
    assert r["delta_prev_sweet"] == pytest.approx(-0.5)
    assert r["delta_prev_lethal"] == pytest.approx(-0.5)
    assert r["pressure"] == pytest.approx(0.0)
    assert dp.dreaming_verdict(r["delta_prev_sweet"], r["delta_prev_lethal"], 0.0, 1.0) == "MORT"


def test_run_q1_never_lets_a_nan_reach_the_gate(monkeypatch):
    """La grandeur mesuree est-elle celle qui AGIT ? `dreaming_verdict` compare avec `>` : TOUTE
    comparaison a nan vaut False -> `survives=False` -> MORT. Propager l'INDETERMINE au lieu de lever
    aurait donc DEPLACE le defaut d'un cran, pas corrige. Ce test fige les deux moities : (1) la porte
    prononcerait bien MORT sur du nan -- c'est la raison de lever ; (2) `run_q1` ne laisse jamais un
    nan sortir, meme quand une seule ere sur 3 seeds est vide."""
    import math
    from tools.dreaming_probe import dreaming_verdict
    nan = float("nan")
    assert dreaming_verdict(nan, nan, 0.0, 1.0) == "MORT", (
        "la porte lit nan comme un negatif de fond : c'est pourquoi run_q1 doit REFUSER, pas propager")

    def _vide_au_seed_2(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        return [] if seed == 2 else _dp_cohorte(0.75 if (metab, payoff) == (0.25, 3.0) else 0.25)

    dp = _dp_injecte(monkeypatch, _vide_au_seed_2)
    with pytest.raises(ValueError, match="cohorte VIDE"):
        dp.run_q1([0, 1, 2], "stoneage", 8, 5, None)
    # contre-epreuve : sans le seed fautif, la meme fabrique mesure normalement (aucun nan en sortie)
    r = dp.run_q1([0, 1], "stoneage", 8, 5, None)
    assert not math.isnan(r["delta_prev_sweet"]) and not math.isnan(r["delta_prev_lethal"])
    assert r["pressure"] == pytest.approx(0.5)


def test_run_q1_measured_values_are_UNCHANGED_by_the_fix(monkeypatch):
    """NON-REGRESSION de la MESURE. Les cinq prevalences exactement representables a n=8 doivent rendre
    les memes deltas qu'avant le correctif : 0.0/0.25/0.5/0.75/1.0 -> -0.5/-0.25/0.0/+0.25/+0.5."""
    dp = _dp_injecte(monkeypatch, None)
    for prev, attendu in ((0.0, -0.5), (0.25, -0.25), (0.5, 0.0), (0.75, 0.25), (1.0, 0.5)):
        monkeypatch.setattr(dp, "run_era_organ", _dp_par_regime(prev, 0.5))
        r = dp.run_q1([0, 1, 2], "stoneage", 8, 5, None)
        assert r["delta_prev_sweet"] == pytest.approx(attendu), prev
        assert r["delta_prev_lethal"] == pytest.approx(0.0)


def test_run_q2_is_UNTOUCHED_by_the_run_q1_fix(monkeypatch):
    """Perimetre. `run_q2` vit dans le meme fichier et n'a PAS ete modifie (une autre session en ecrit
    peut-etre les tests). Reponse connue minimale : sa garde d'arguments leve toujours, et un appel
    valide traverse toujours -- 2 eres par seed, ratio 1.0 sur des bras identiques."""
    import tools.dreaming_probe as dp
    with pytest.raises(ValueError, match="degenere"):
        dp.run_q2((), "stoneage", 4, 10, None)
    with pytest.raises(ValueError, match="degenere"):
        dp.run_q2((0,), "stoneage", 0, 10, None)

    appels = []

    def _ere(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        appels.append((seed, organ_fraction))
        return [{"age": 100, "total_dreams": 0, "has_organ": bool(organ_fraction), "founder": True}]

    monkeypatch.setattr(dp, "run_era_organ", _ere)
    r = dp.run_q2([0, 1], "stoneage", 4, 10, None)
    assert len(appels) == 4 and {f for _, f in appels} == {0.0, 1.0}
    assert r["n"] == 2 and r["q2b_ratio"] == pytest.approx(1.0)


# ======================================================================================================
# REFUTATION 2026-09-08 -- ce que le correctif de `run_q1` a LAISSE derriere lui.
#
# Le correctif du meme jour a redresse `run_q1` (materialisation des seeds) et `_prevalence_from_stats`
# (cohorte vide -> nan). Deux defauts de la MEME CLASSE, dans le MEME fichier, sont restes en place et
# ont ete mesures par sonde directe :
#
#   (c) `run_q2` portait le defaut d'iterateur MOT POUR MOT (`not list(seeds)`). Sonde :
#       `run_q2(iter([0,1,2]), ...)` -> 0 appel a `run_era_organ`, sortie
#       {'q2a_delta': 0.0, 'q2b_ratio': 1.0, 'sign_p': 1.0, 'n': 0}, et la chaine complete prononce
#       SURVIT_PAS_PAYE : l'affirmation de FOND << le reve ne paye pas >>, fabriquee sans une seule ere.
#       Le test `test_run_q2_is_UNTOUCHED_by_the_run_q1_fix` livre avec le correctif ne pouvait PAS le
#       voir : il n'appelle `run_q2` qu'avec des LISTES.
#   (d) `organ_prevalence` -- jumeau PUBLIC de `_prevalence_from_stats` -- gardait la convention 0.0
#       sur cohorte vide, et cette convention etait GELEE par un test vert. Un defaut protege par un
#       test est le pire etat possible : le prochain correcteur doit d'abord casser du vert.
#
# Chaque comportement corrige ici a son CAS NEGATIF APPARIE (classe E1), etiquete.
# ======================================================================================================


def _dp_agent_q2(age, dreams, organ):
    return {"age": age, "total_dreams": dreams, "has_organ": bool(organ), "founder": True,
            "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}


def _dp_q2_par_bras(age_on, age_off, dreams_on=3, n=6, journal=None):
    """Fabrique d'eres pour `run_q2` : le bras est identifie par `organ_fraction` (1.0=ON, 0.0=OFF).
    Dose connue -- les ages fixent la competence-survie, donc le ratio q2b."""
    def _f(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        if journal is not None:
            journal.append((seed, organ_fraction))
        if organ_fraction >= 0.5:
            # bras ON : moitie reveurs (dreams>0), moitie non-reveurs -> q2a mesurable
            return [_dp_agent_q2(age_on, dreams_on if i % 2 == 0 else 0, True) for i in range(n)]
        return [_dp_agent_q2(age_off, 0, False) for i in range(n)]
    return _f


def test_run_q2_MEASURES_every_seed_of_an_ITERATOR(monkeypatch):
    """POSITIF. Dose connue : 3 seeds en GENERATEUR, bras ON plus vieux que OFF -> ratio > 1 et
    `n == 3`. AVANT correctif la sonde mesurait : 0 appel a `run_era_organ`, `n=0`, `q2a_delta=0.0`,
    `q2b_ratio=1.0`, `sign_p=1.0` -- soit << le reve ne paye pas >> fabrique a partir de RIEN. Le
    compte d'appels (2 par seed = 6) distingue une double consommation (0 appel) d'une double
    boucle (12)."""
    import tools.dreaming_probe as dp
    appels = []
    monkeypatch.setattr(dp, "run_era_organ", _dp_q2_par_bras(200, 20, journal=appels))
    r = dp.run_q2((s for s in (4, 5, 6)), "stoneage", 6, 5, None)
    assert len(appels) == 6, appels
    assert sorted({s for s, _ in appels}) == [4, 5, 6]
    assert r["n"] == 3 and len(r["per_seed_ratio"]) == 3
    assert r["q2b_ratio"] > 1.0, r
    assert r["total_dreams_seen"] > 0


def test_run_q2_STILL_REFUSES_an_EMPTY_iterator_before_any_era(monkeypatch):
    """NEGATIF APPARIE au precedent (classe E1). Materialiser les seeds pourrait avoir relache la
    garde. Reponse connue : toutes les formes d'iterable VIDE doivent TOUJOURS lever, EN TETE --
    ZERO appel a `run_era_organ`. Contre-epreuve incluse : la garde n'est pas devenue increvable."""
    import tools.dreaming_probe as dp
    compteur = {"n": 0}

    def _compte(*a, **kw):
        compteur["n"] += 1
        return [_dp_agent_q2(50, 1, True)]

    monkeypatch.setattr(dp, "run_era_organ", _compte)
    for vide in ((s for s in ()), iter([]), map(int, []), (), []):
        with pytest.raises(ValueError, match="degenere"):
            dp.run_q2(vide, "stoneage", 6, 5, None)
        assert compteur["n"] == 0, ("garde de run_q2 plus EN TETE", vide)
    # les autres arguments degeneres restent refuses, iterateur NON vide compris
    for na, mt in ((6, 0), (0, 5)):
        with pytest.raises(ValueError, match="degenere"):
            dp.run_q2(iter([0]), "stoneage", na, mt, None)
        assert compteur["n"] == 0
    dp.run_q2(iter([0]), "stoneage", 6, 5, None)
    assert compteur["n"] == 2, "un iterateur NON vide doit franchir la garde et produire 2 eres"


def test_run_q2_refusal_message_NAMES_the_true_number_of_seeds(monkeypatch):
    """Le MESSAGE etait la 2e consommation. Reponse connue : 3 seeds REELS passes en iterateur, refuses
    pour `num_agents=0` -> le refus doit annoncer n_seeds=3. Avant, il annoncait n_seeds=0 et accusait
    donc le mauvais argument (un refus qui ment sur sa cause envoie corriger ce qui va bien)."""
    import tools.dreaming_probe as dp
    with pytest.raises(ValueError, match=r"n_seeds=3 num_agents=0"):
        dp.run_q2(iter([7, 8, 9]), "stoneage", 0, 10, None)
    # negatif apparie : sur un iterable REELLEMENT vide, n_seeds=0 est la VERITE, pas un artefact
    with pytest.raises(ValueError, match=r"n_seeds=0"):
        dp.run_q2(iter([]), "stoneage", 6, 10, None)


def test_run_q2_measured_values_are_UNCHANGED_by_the_fix(monkeypatch):
    """NON-REGRESSION de la MESURE. Sur des LISTES (la seule forme qu'utilisent les appelants reels,
    `main` compris) le correctif ne doit RIEN changer : memes ratios, meme n, memes cles. Trois doses :
    ON>OFF, ON==OFF (ratio exactement 1.0), ON<OFF."""
    import tools.dreaming_probe as dp
    for age_on, age_off, sens in ((200, 20, "sup"), (60, 60, "egal"), (20, 200, "inf")):
        monkeypatch.setattr(dp, "run_era_organ", _dp_q2_par_bras(age_on, age_off))
        r = dp.run_q2([0, 1, 2], "stoneage", 6, 5, None)
        assert r["n"] == 3
        if sens == "sup":
            assert r["q2b_ratio"] > 1.0
        elif sens == "egal":
            assert r["q2b_ratio"] == pytest.approx(1.0)
        else:
            assert r["q2b_ratio"] < 1.0
        # SUR-ENSEMBLE, PAS EGALITE (corrige le 2026-09-08, classe E14). L'egalite STRICTE
        # transformait tout ENRICHISSEMENT de sortie en FAUSSE regression -- la lecon est ecrite
        # 350 lignes plus haut dans CE fichier (`test_run_era_organ_smoke_seeds_organ`, « Une
        # egalite STRICTE de cles transforme tout enrichissement de sortie en FAUSSE regression »)
        # et n'avait pas ete appliquee ici. Ce que le test doit garantir, c'est qu'aucune cle ne
        # DISPARAISSE pour un appelant existant : c'est exactement `<=`.
        assert {"q2a_delta", "q2b_ratio", "n_favorable", "n", "sign_p",
                "total_dreams_seen", "per_seed_delta", "per_seed_ratio"} <= set(r), (
            "aucune cle ne doit disparaitre pour un appelant existant")
        assert r["n_ecartees"] == 0 and r["n_seeds"] == 3, (
            "contre-epreuve appariee : sur une dose entierement MESURABLE, le compte de cellules "
            "ecartees doit valoir ZERO -- une garde de degenerescence qui ecarterait tout serait "
            "pire que le defaut (classe E1)")


def test_organ_prevalence_returns_nan_on_an_EMPTY_cohort():
    """POSITIF (jumeau public). Reponse connue : sans agent il n'y a pas de prevalence -> nan."""
    import math
    assert math.isnan(organ_prevalence([]))


def test_organ_prevalence_STILL_returns_0_on_a_REAL_total_purge():
    """NEGATIF APPARIE au precedent (classe E1). Une cohorte NON VIDE sans aucun porteur est une purge
    OBSERVEE : elle vaut 0.0, exactement, et les fractions intermediaires sont inchangees. Sans ce cas,
    transformer tout 0.0 en nan passerait le test positif en detruisant la mesure."""
    assert organ_prevalence([_agent(False)]) == 0.0
    assert organ_prevalence([_agent(False)] * 5) == 0.0
    assert organ_prevalence([_agent(True), _agent(False), _agent(False), _agent(False)]) == 0.25


def test_the_two_prevalence_twins_AGREE():
    """Specificite : les deux fonctions de prevalence du module repondent desormais la MEME chose aux
    memes questions. C'est ce desaccord (privee corrigee / publique laissee a 0.0) qui faisait du
    jumeau public un piege arme."""
    import math
    from tools.dreaming_probe import _prevalence_from_stats
    assert math.isnan(organ_prevalence([])) and math.isnan(_prevalence_from_stats([]))
    assert organ_prevalence([_agent(False)] * 4) == _prevalence_from_stats(_dp_cohorte(0.0, n=4)) == 0.0
    assert organ_prevalence([_agent(True)] * 4) == _prevalence_from_stats(_dp_cohorte(1.0, n=4)) == 1.0


# ======================================================================================================
# 2026-09-08 -- CALIBRATION de `run_q2` sur les QUATRE defauts REELS exposes par
# `tests/sandbox/test_inj_run_q2.py` (injection a dose connue, aucun monde construit) :
#
#   #1 GROUPE DE REFERENCE VIDE : bras ON force a 100 % d'organe -> quand tous revent,
#      `nondreamers=[]`, `survival_competence([])` valait 0.0, et `q2a_delta` cessait d'etre un
#      CONTRASTE pour devenir la competence ABSOLUE des reveurs. Dose : deux bras STRICTEMENT
#      identiques sortaient q2a_delta=0.5 (25x `pay_eps`) -> SURVIT_ET_PAYE sur un effet NUL.
#   #2 DRAPEAU `founder` PRODUIT ET JAMAIS LU : `survival_competence` sur TOUS les agents compare
#      deux populations dont l'une s'est reproduite x20. Dose : cohortes fondatrices IDENTIQUES ->
#      q2b_ratio 0.05, << l'organe divise la survie par 20 >>.
#   #3 DEGENERESCENCE DETECTEE PUIS AVALEE : `c_on<=1e-6 and c_off<=1e-6 -> ratio=1.0`, la valeur
#      qui signifie << aucun effet >>, puis la cellule sortait de `effective` -> dict indiscernable
#      d'une egalite MESUREE.
#   #4 GARDE SUR UN `and` : denominateur SEUL eteint -> `max(c_off,1e-6)` faisait exploser le ratio
#      (5000 pour UN tick d'ecart) -> RATIO_CAP 5.0 -> SURVIT_ET_PAYE.
#
# CHAQUE comportement ajoute a ici son CAS NEGATIF APPARIE (classe E1), etiquete : un correctif qui
# rendrait la garde increvable (elle ecarte tout) ou l'instrument muet (il ne sait plus rapporter un
# prejudice REEL) serait pire que le defaut.
# ======================================================================================================


def _dp_agent_f(age, dreams=0, founder=True):
    """Cellule-agent factice portant TOUTES les cles que `run_era_organ` produit."""
    return {"age": float(age), "total_dreams": int(dreams), "has_organ": True,
            "founder": bool(founder), "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}


def _dp_bras(cohorte_on, cohorte_off, journal=None):
    """Fabrique d'eres distinguant les bras par leur DOSE D'ORGANE (1.0=ON, 0.0=OFF), pas par
    l'ordre d'appel. `cohorte_on`/`cohorte_off` : liste, ou callable(seed) -> liste."""
    def _f(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        if journal is not None:
            journal.append((seed, organ_fraction))
        c = cohorte_on if organ_fraction == 1.0 else cohorte_off
        return list(c(seed)) if callable(c) else list(c)
    return _f


def _dp_q2(monkeypatch, cohorte_on, cohorte_off, seeds=(0, 1, 2), journal=None):
    import tools.dreaming_probe as dp
    monkeypatch.setattr(dp, "run_era_organ", _dp_bras(cohorte_on, cohorte_off, journal))
    return dp, dp.run_q2(list(seeds), "stoneage", 8, 5, None)


# ------------------------------------------------------------------------------------------------------
# #2 APPARIEMENT SUR LA COHORTE FONDATRICE
# ------------------------------------------------------------------------------------------------------

def test_run_q2_ratio_is_MATCHED_on_the_FOUNDERS_under_a_reproductive_explosion(monkeypatch):
    """POSITIF. Dose connue en forme close : bras ON = 12 fondateurs d'age 100 + 240 nes-tard d'age 5
    (l'explosion x20 documentee dans `run_era_organ`) ; bras OFF = les MEMES 12 fondateurs, sans
    explosion. Apparie sur les fondateurs -> mediane 100 des deux cotes -> ratio 1.0. Sur TOUS les
    agents -> mediane ON = 5 -> competence 0.025 contre 0.5 -> ratio 0.05. Les DEUX lectures sont
    publiees par cellule : le chiffre dilue (celui d'EDR-093) reste re-derivable."""
    on = [_dp_agent_f(100, 3) for _ in range(12)] + [_dp_agent_f(5, 3, founder=False) for _ in range(240)]
    off = [_dp_agent_f(100, 0) for _ in range(12)]
    dp, r = _dp_q2(monkeypatch, on, off)
    assert r["q2b_ratio"] == pytest.approx(1.0), r["per_seed_cellules"][0]
    c = r["per_seed_cellules"][0]
    assert (c["c_on_founder"], c["c_off_founder"]) == pytest.approx((0.5, 0.5))
    assert (c["c_on_tous"], c["c_off_tous"]) == pytest.approx((0.025, 0.5))
    assert (c["n_founder_on"], c["n_tous_on"]) == (12, 252)
    assert dp.dreaming_verdict(0.25, -0.25, 0.0, r["q2b_ratio"]) == "SURVIT_PAS_PAYE"


def test_run_q2_founder_matching_CHANGES_NOTHING_when_there_is_no_explosion(monkeypatch):
    """NEGATIF APPARIE au precedent (classe E1). Sans nes-tard, la lecture << fondateurs >> et la
    lecture << tous agents >> COINCIDENT : le filtre ne doit RIEN inventer et la dose doit ressortir
    intacte (ON 100 / OFF 50 -> 2.0). Sans ce cas, un filtre qui rendrait 1.0 quoi qu'il arrive
    passerait le test positif."""
    on = [_dp_agent_f(100, 3), _dp_agent_f(100, 0)] * 4
    off = [_dp_agent_f(50, 0) for _ in range(8)]
    _dp, r = _dp_q2(monkeypatch, on, off)
    assert r["q2b_ratio"] == pytest.approx(2.0)
    c = r["per_seed_cellules"][0]
    assert c["c_on_founder"] == c["c_on_tous"] and c["c_off_founder"] == c["c_off_tous"]


def test_run_q2_REFUSES_an_era_WITHOUT_a_single_founder_and_NAMES_seed_and_arm(monkeypatch):
    """POSITIF. Une ere sans AUCUN fondateur n'a rien produit : c'est une absence de mesure, pas une
    survie nulle. `run_q2` doit LEVER en nommant le seed ET le bras (un refus anonyme obligerait a
    re-simuler pour savoir ou regarder), et lever DES LE PREMIER seed fautif -- au plus 2 eres
    tournees sur 12 seeds, pas 24. Les deux bras sont testes separement : un correctif qui n'aurait
    garde qu'un des deux passerait sinon. La cohorte VIDE est le meme cas."""
    import tools.dreaming_probe as dp
    normale = [_dp_agent_f(100, 3), _dp_agent_f(100, 0)]

    monkeypatch.setattr(dp, "run_era_organ", _dp_bras([_dp_agent_f(100, 3, founder=False)], normale))
    with pytest.raises(ValueError, match=r"ere ON du seed 5 .*AUCUN agent fondateur"):
        dp.run_q2([5, 6, 7], "stoneage", 8, 5, None)

    monkeypatch.setattr(dp, "run_era_organ", _dp_bras(normale, [_dp_agent_f(50, 0, founder=False)]))
    with pytest.raises(ValueError, match=r"ere OFF du seed 5 .*AUCUN agent fondateur"):
        dp.run_q2([5, 6, 7], "stoneage", 8, 5, None)

    monkeypatch.setattr(dp, "run_era_organ", _dp_bras([], normale))   # cohorte VIDE = meme refus
    with pytest.raises(ValueError, match=r"AUCUN agent fondateur"):
        dp.run_q2([5], "stoneage", 8, 5, None)

    appels = []
    monkeypatch.setattr(dp, "run_era_organ", _dp_bras([_dp_agent_f(1, 0, founder=False)], normale,
                                                      journal=appels))
    with pytest.raises(ValueError, match=r"AUCUN agent fondateur"):
        dp.run_q2(list(range(12)), "stoneage", 8, 5, None)
    assert {s for s, _ in appels} == {0} and len(appels) <= 2, appels


def test_run_q2_founder_refusal_is_NOT_unkillable(monkeypatch):
    """NEGATIF APPARIE au precedent (classe E1). Un refus qui se declencherait TOUJOURS passerait le
    test ci-dessus. Reponse connue : une cohorte MIXTE (fondateurs + nes-tard) traverse, et la mesure
    est celle des fondateurs -- ON 200 / OFF 100 -> 2.0, malgre 40 nes-tard d'age 1 de chaque cote."""
    on = [_dp_agent_f(200, 3) for _ in range(6)] + [_dp_agent_f(1, 0, founder=False) for _ in range(40)]
    off = [_dp_agent_f(100, 0) for _ in range(6)] + [_dp_agent_f(1, 0, founder=False) for _ in range(40)]
    _dp, r = _dp_q2(monkeypatch, on, off)
    assert r["n"] == 3 and r["q2b_ratio"] == pytest.approx(2.0)


# ------------------------------------------------------------------------------------------------------
# #3 / #4 DEGENERESCENCE : ECARTEE ET COMPTEE, PLUS AVALEE
# ------------------------------------------------------------------------------------------------------

def test_run_q2_DISCARDS_a_cell_whose_DENOMINATOR_is_extinct_and_SAYS_so(monkeypatch):
    """POSITIF, les deux formes du defaut d'un coup. (a) les DEUX bras eteints (age 0 partout) :
    l'ancien code rendait `ratio=1.0`, la valeur qui signifie << aucun effet >> -> dict indiscernable
    d'une egalite MESUREE. (b) le SEUL denominateur eteint (ON age 1 / OFF age 0) : l'ancien code
    divisait par le plancher 1e-6 -> ratio brut 5000 -> RATIO_CAP 5.0 -> SURVIT_ET_PAYE pour UN tick
    d'ecart entre deux populations eteintes. Reponse connue : dans les deux cas, ZERO cellule
    informative -> q2b_ratio nan, n=0, n_ecartees=3, seeds nommes, `why_q2b` present, et la porte
    NOMME l'indecidable au lieu de prononcer PAS_PAYE."""
    import math
    for age_on, age_off in ((0, 0), (1, 0)):
        dp, r = _dp_q2(monkeypatch, [_dp_agent_f(age_on, 3)] * 8, [_dp_agent_f(age_off, 0)] * 8)
        assert math.isnan(r["q2b_ratio"]), (age_on, age_off, r)
        assert r["n"] == 0 and r["n_ecartees"] == 3 and r["seeds_ecartes"] == [0, 1, 2]
        assert r["n_seeds"] == 3 and "why_q2b" in r
        assert r["per_seed_ratio"] == [] and r["n_favorable"] == 0
        assert dp.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"]) \
            == "SURVIT_PAYE_INDETERMINE"


def test_run_q2_STILL_REPORTS_a_REAL_harm_when_only_the_NUMERATOR_is_extinct(monkeypatch):
    """NEGATIF APPARIE au precedent (classe E1) -- LE cas qui empeche le correctif d'etre un
    baillon. Un bras ON eteint face a un bras OFF VIVANT est une cellule parfaitement INFORMATIVE :
    le denominateur existe, le ratio vaut 0.0, et c'est le prejudice maximal MESURE. Une garde posee
    sur << l'un OU l'autre est eteint >> aurait rendu l'instrument incapable de le dire."""
    _dp, r = _dp_q2(monkeypatch, [_dp_agent_f(0, 3)] * 8, [_dp_agent_f(100, 0)] * 8)
    assert r["n"] == 3 and r["n_ecartees"] == 0
    assert r["q2b_ratio"] == 0.0 and r["n_favorable"] == 0
    assert r["sign_p"] == pytest.approx(0.25), "3 cellules toutes defavorables : le signe tourne"


def test_run_q2_aggregates_on_the_MEASURED_cells_only(monkeypatch):
    """POSITIF (specificite du melange). Reponse connue : 3 seeds dont UN SEUL a un denominateur
    eteint. La mediane doit porter sur les DEUX cellules mesurees (ratio 2.0), `n` doit valoir 2,
    `n_seeds` 3, `n_ecartees` 1, et le seed ecarte doit etre NOMME -- sans quoi une cellule perdue
    serait invisible dans le chiffre publie."""
    def _on(seed):
        return [_dp_agent_f(100, 3), _dp_agent_f(100, 0)] * 4

    def _off(seed):
        return [_dp_agent_f(0 if seed == 1 else 50, 0)] * 8

    _dp, r = _dp_q2(monkeypatch, _on, _off)
    assert r["n"] == 2 and r["n_seeds"] == 3 and r["n_ecartees"] == 1
    assert r["seeds_ecartes"] == [1]
    assert r["q2b_ratio"] == pytest.approx(2.0) and r["per_seed_ratio"] == pytest.approx([2.0, 2.0])
    assert "why_q2b" not in r, "il RESTE des cellules mesurees : ce n'est pas un indetermine"


def test_run_q2_publishes_the_TRUE_denominator_of_its_sign_test(monkeypatch):
    """Le test de signe JETTE les ex aequo : le `n` publie N'EST PAS son denominateur. Meme
    correctif que `dose_response_verdict`, jamais retro-applique ici (classe E14). Reponse connue :
    3 seeds dont un seul favorable (ratio 2.0) et deux ex aequo exacts -> n=3, n_effectif=1,
    n_ex_aequo=2, sign_p=1.0. Sans `n_effectif`, un lecteur lirait << 1/3, p=1.0 >> comme un test sur
    3 replicats alors qu'il a tourne sur UN."""
    def _on(seed):
        age = 200 if seed == 0 else 100
        return [_dp_agent_f(age, 3), _dp_agent_f(age, 0)] * 4

    _dp, r = _dp_q2(monkeypatch, _on, [_dp_agent_f(100, 0)] * 8)
    assert r["per_seed_ratio"] == pytest.approx([2.0, 1.0, 1.0])
    assert r["n"] == 3 and r["n_effectif"] == 1 and r["n_ex_aequo"] == 2
    assert r["sign_p"] == 1.0


# ------------------------------------------------------------------------------------------------------
# #1 GROUPE DE REFERENCE VIDE
# ------------------------------------------------------------------------------------------------------

def test_run_q2_q2a_is_INDETERMINATE_when_NO_seed_has_a_reference_group(monkeypatch):
    """POSITIF. Dose connue : bras ON = 8 agents qui revent TOUS, bras OFF identique en age -> effet
    reel de l'organe ZERO (ratio 1.0 exact). L'ancien code rendait q2a_delta = competence ABSOLUE des
    reveurs = 0.5, soit 25x `pay_eps`, et la porte prononcait SURVIT_ET_PAYE. Attendu : nan, les
    seeds NOMMES, `why_q2a`, et une porte qui dit INDETERMINE au lieu de trancher."""
    import math
    dp, r = _dp_q2(monkeypatch, [_dp_agent_f(100, 3)] * 8, [_dp_agent_f(100, 0)] * 8)
    assert r["q2b_ratio"] == 1.0, "controle : les deux bras sont identiques"
    assert math.isnan(r["q2a_delta"]) and "why_q2a" in r
    assert r["n_sans_reference"] == 3 and r["seeds_sans_reference"] == [0, 1, 2]
    assert r["per_seed_delta"] == [None, None, None], "JSON-serialisable, et LISIBLE comme manquant"
    assert dp.dreaming_verdict(0.25, -0.25, r["q2a_delta"], r["q2b_ratio"]) \
        == "SURVIT_PAYE_INDETERMINE"


def test_run_q2_q2a_is_STILL_MEASURED_when_both_groups_exist(monkeypatch):
    """NEGATIF APPARIE au precedent (classe E1). Le correctif ne doit pas rendre `q2a_delta`
    perpetuellement indetermine : quand le groupe de reference EXISTE, le contraste est mesure, dans
    les DEUX directions. Reveurs 160 / non-reveurs 40 -> +0.6 ; l'inverse -> -0.6 ; et un seul seed
    sans reference sur 3 ne doit PAS effacer les deux autres (mediane sur les cellules mesurees)."""
    for a_rev, a_autres, attendu in ((160, 40, 0.6), (40, 160, -0.6)):
        _dp, r = _dp_q2(monkeypatch,
                        [_dp_agent_f(a_rev, 5)] * 4 + [_dp_agent_f(a_autres, 0)] * 4,
                        [_dp_agent_f(100, 0)] * 8)
        assert r["q2a_delta"] == pytest.approx(attendu)
        assert r["n_sans_reference"] == 0 and "why_q2a" not in r

    def _on(seed):
        if seed == 1:
            return [_dp_agent_f(100, 5)] * 8                       # aucun non-reveur
        return [_dp_agent_f(160, 5)] * 4 + [_dp_agent_f(40, 0)] * 4

    _dp, r = _dp_q2(monkeypatch, _on, [_dp_agent_f(100, 0)] * 8)
    assert r["q2a_delta"] == pytest.approx(0.6), "mediane des cellules MESUREES, pas des trois"
    assert r["n_sans_reference"] == 1 and r["seeds_sans_reference"] == [1]
    assert r["per_seed_delta"][1] is None and r["per_seed_delta"][0] == pytest.approx(0.6)


# ------------------------------------------------------------------------------------------------------
# LA PORTE : un `nan` du cote PAYE n'est plus avale
# ------------------------------------------------------------------------------------------------------

def test_dreaming_verdict_NAMES_an_undecidable_pay_side():
    """POSITIF. Toute comparaison a nan vaut False : un cote PAYE indetermine faisait donc prononcer
    << PAS PAYE >>, l'affirmation de FOND sur zero observation. La porte doit le NOMMER, dans les
    deux etats du cote SURVIT."""
    nan = float("nan")
    assert dreaming_verdict(0.25, -0.25, nan, 1.0) == "SURVIT_PAYE_INDETERMINE"
    assert dreaming_verdict(0.25, -0.25, 0.0, nan) == "SURVIT_PAYE_INDETERMINE"
    assert dreaming_verdict(-0.4, -0.45, nan, nan) == "PAS_SURVIT_PAYE_INDETERMINE"


def test_dreaming_verdict_STILL_CONCLUDES_when_the_measured_half_of_the_OR_decides():
    """NEGATIF APPARIE au precedent (classe E1), en TROIS morceaux -- sans eux, << ne plus conclure
    des qu'il y a un nan >> passerait le test positif en detruisant la porte :
      1. le `or` tranche POSITIVEMENT sur sa moitie MESUREE malgre un nan sur l'autre ;
      2. un nul REELLEMENT mesure reste SURVIT_PAS_PAYE -- la porte sait encore dire << ne paye pas >> ;
      3. le cote SURVIT n'est PAS touche : nan sur Q1 rend toujours MORT, ce qui est precisement
         POURQUOI `run_q1` doit REFUSER une cohorte vide plutot que propager."""
    nan = float("nan")
    assert dreaming_verdict(0.25, -0.25, nan, 2.0) == "SURVIT_ET_PAYE"
    assert dreaming_verdict(0.25, -0.25, 0.10, nan) == "SURVIT_ET_PAYE"
    assert dreaming_verdict(-0.4, -0.45, nan, 2.0) == "PAYE_PAS_SURVIT"
    assert dreaming_verdict(0.25, -0.25, 0.0, 1.0) == "SURVIT_PAS_PAYE"
    assert dreaming_verdict(-0.4, -0.45, 0.0, 1.0) == "MORT"
    assert dreaming_verdict(nan, nan, 0.0, 1.0) == "MORT"
