# EXEMPTION DECLAREE de la garde de bail (convention `_LEASE_GUARD_EXEMPT` du conftest).
# Ce module ne simule AUCUN monde : les tests de verdict sont purs, et les deux tests d'orchestrateur
# ajoutes le 2026-09-07 injectent `run_fn` ET `champion_genome`, donc `run_condition` n'est jamais
# appele et aucune classe de monde n'est instanciee (`wcls` ne sert qu'a nommer la cellule). Sans
# cette declaration, importer `tools.s2_cognition_body` suffisait a faire SAUTER les 9 tests purs des
# qu'un run tenait le bail -- une suite qui se tait au moment ou l'on en a le plus besoin.
_LEASE_GUARD_EXEMPT = True

import numpy as np

from src.seed_ai.s2_stats import verdict_cognition_body


def _cond(center, n=12, spread=4.0):
    era = list(np.linspace(center - spread, center + spread, n))
    pooled = list(np.linspace(center - spread, center + spread, 4 * n))
    return {"survival": pooled, "era_survival": era, "life_score": pooled, "era_life": era}


def test_verdict_cognition():
    # C(45) >> B(12) ; B(12) ~ R(12) -> la POLITIQUE porte la survie -> COGNITION
    r = verdict_cognition_body(_cond(45), _cond(12), _cond(20), _cond(12))
    assert r["verdict"] == "COGNITION"
    assert r["policy_sig"] and not r["body_sig"]


def test_verdict_body():
    # C(45) ~ B(44) ; B(44) >> R(12) -> le CORPS/genome porte la survie -> BODY
    r = verdict_cognition_body(_cond(45), _cond(44), _cond(20), _cond(12))
    assert r["verdict"] == "BODY"
    assert r["body_sig"] and not r["policy_sig"]


def test_verdict_both():
    # C(45) >> B(28) >> R(12) -> corps ET politique -> BOTH
    r = verdict_cognition_body(_cond(45), _cond(28), _cond(20), _cond(12))
    assert r["verdict"] == "BOTH"
    assert r["policy_sig"] and r["body_sig"]


def test_verdict_neither():
    # C(20) ~ B(20) ~ R(20) -> aucun -> NEITHER
    r = verdict_cognition_body(_cond(20), _cond(20), _cond(20), _cond(20))
    assert r["verdict"] == "NEITHER"


def test_verdict_metric_life_score():
    # metric="life_score" utilise era_life/life_score ; ici life=survie synthetique -> meme verdict COGNITION
    r = verdict_cognition_body(_cond(45), _cond(12), _cond(20), _cond(12), metric="life_score")
    assert r["metric"] == "life_score"
    assert r["verdict"] == "COGNITION"


from tools.s2_cognition_body import cognition_body_study, CELLS


def test_cells_registered():
    assert set(CELLS) == {"champion", "champion_body", "random_genome", "random_action"}
    assert CELLS["champion"]["fresh_genome"] is False
    assert CELLS["champion_body"]["fresh_genome"] is False           # MÊME génome champion
    from src.agents.baseline_models import RandomActionBatchModel
    assert CELLS["champion_body"]["batch_model_cls"] is RandomActionBatchModel
    assert CELLS["champion"]["batch_model_cls"] is None              # moteur normal


def test_study_contract_with_stub():
    # stub run_fn : evite la biosphere. Rend une survie par cellule -> verdict structurel.
    surv = {"champion": _cond(45), "champion_body": _cond(12),
            "random_genome": _cond(20), "random_action": _cond(12)}
    def stub_run(world_cls, batch_model_cls, genome, seed, num_agents, max_ticks, n_eras):
        # associe la cellule par (batch_model_cls, genome is None)
        from src.agents.baseline_models import RandomActionBatchModel
        rnd = batch_model_cls is RandomActionBatchModel
        champ = genome is not None
        key = ("champion" if (champ and not rnd) else "champion_body" if (champ and rnd)
               else "random_genome" if (not champ and not rnd) else "random_action")
        return surv[key]
    rep = cognition_body_study(worlds=["stoneage"], seed=1, K=2, num_agents=4, max_ticks=10,
                               run_fn=stub_run, champion_genome="dummy")
    w = rep["worlds"]["stoneage"]
    assert w["verdict"] in {"COGNITION", "BODY", "BOTH", "NEITHER"}
    assert w["verdict"] == "COGNITION"                              # C(45)>>B(12), B(12)~R(12)
    assert set(w["survivals"]) == set(CELLS)


# ==================================================================================================
# NON-REGRESSION (2026-09-07) -- DEUX defauts corriges dans `cognition_body_study`, retro-application
# du correctif pose le meme jour sur `run_s2`. Cet orchestrateur porte le verdict FONDATEUR S2-012 :
# `run_fn` est injectable, donc AUCUN monde n'est construit ici et le cout est nul.
# ==================================================================================================
import pytest

from tools.s2_cognition_body import cognition_body_study


def _cellule(centre):
    """Cellule factice au format que `run_condition` rend et que l'orchestrateur relit."""
    return _cond(centre)


def _run_fn_dose(dose_par_monde):
    """`run_fn` injecte : impose la survie de chaque cellule, monde par monde. Aucune simulation."""
    ordre = {}

    def run_fn(wcls, batch_model_cls, genome, seed, **kw):
        nom = wcls.__name__
        i = ordre.setdefault(nom, 0)
        ordre[nom] = i + 1
        # les 4 cellules sortent dans l'ordre de CELLS : champion, champion_body, random_genome, random_action
        return _cellule(dose_par_monde[nom][i])
    return run_fn


def test_cognition_body_study_REFUSE_une_famille_de_mondes_VIDE():
    """DEFAUT CORRIGE : `worlds or list(WORLDS)` traitait une selection VIDE comme une absence de
    choix -- demander ZERO monde lancait la grille COMPLETE (4 cellules x 5 mondes x K eres). La
    sentinelle explose au premier appel : si la garde tombe, le test le dit sans rien simuler."""
    def _sentinelle(wcls, *a, **kw):
        raise AssertionError(f"worlds=[] a lance un run sur {wcls.__name__} : la liste vide a ete "
                             "remplacee par tous les mondes")
    with pytest.raises(ValueError, match="degenere"):
        cognition_body_study(worlds=[], run_fn=_sentinelle, champion_genome="G", K=2)


def test_cognition_body_study_GARDE_la_correction_de_Holm_quand_worlds_est_un_ITERATEUR():
    """DEFAUT CORRIGE, le plus grave : `worlds` etait ITERE DEUX FOIS -- la boucle de mesure, puis la
    famille Holm. Passe en ITERATEUR (forme naturelle : `map`, un generateur), la seconde passe etait
    VIDE : aucun `policy_p_holm` n'etait ecrit et l'affichage retombait EN SILENCE sur le `p` NON
    corrige. Reponse connue : 2 mondes a dose IDENTIQUE doivent recevoir p_holm = 2 x p."""
    dose = {"Biosphere3D": [45, 12, 20, 12], "SoupWorld": [45, 12, 20, 12]}
    from tools.s2_cognition_body import WORLDS
    noms = [w for w in WORLDS if WORLDS[w].__name__ in dose][:2]
    if len(noms) < 2:                                  # le nom des classes a change : ne pas mentir
        pytest.skip("les deux mondes attendus n'existent plus sous ces classes")

    rep = cognition_body_study(worlds=iter(noms), run_fn=_run_fn_dose(dose),
                               champion_genome="G", K=12)
    for w in noms:
        v = rep["worlds"][w]
        assert "policy_p_holm" in v, (
            "la correction de Holm a disparu : `worlds` est re-itere apres avoir ete consomme")
        assert v["policy_p_holm"] >= v["policy_cmp"]["p"]
