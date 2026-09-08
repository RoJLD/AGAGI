# -*- coding: utf-8 -*-
"""Calibration de `tools/evo_runs/s2_blind_champion.py`.

EXEMPTION DÉCLARÉE de la garde de bail : `map_fn` et `champion_fn` sont injectées, aucun monde n'est
construit, aucun génome réel n'est chargé.

L'instrument est PUR, donc chaque branche se confronte à une réponse connue. Les branches NÉGATIVES
sont exigées au même titre : un verdict qui ne pourrait rendre que `AVEUGLE_SURVIT_MIEUX` ne prouverait
rien (classe E1) — et c'est le risque réel ici, puisque l'observation d'origine (+39 %) est POSITIVE et
faite à n=1.
"""
import numpy as np
import pytest

from tools.evo_runs.s2_blind_champion import (blind_champion_verdict, check_blind, make_blind,
                                              run_blind_champion)

_LEASE_GUARD_EXEMPT = True


class _G:
    """Génome factice : juste ce que l'intervention touche."""

    def __init__(self, W, num_inputs=5, num_outputs=4):
        self.W, self.num_inputs, self.num_outputs = W, num_inputs, num_outputs


def _bras(median, within=1.0, verdict="PERCEPTION_DECOY", w_ok=True):
    return {"intact_median": median, "within_ratio": within, "verdict": verdict,
            "floor": 24.0, "w_ok": w_ok}


def _lignes(paires, within_aveugle=1.0):
    """paires : [(intact, aveugle)] -> une ligne par seed."""
    return [{"seed": 2000 + i, "intact": _bras(i_), "blind": _bras(b, within=within_aveugle)}
            for i, (i_, b) in enumerate(paires)]


# --------------------------------------------------------------------------------------------------
# 1. L'INTERVENTION — réelle, minimale, et vérifiable
# --------------------------------------------------------------------------------------------------

def test_make_blind_annule_les_entrees_et_RIEN_d_autre():
    """RÉPONSE CONNUE : les `num_inputs` premières lignes à zéro EXACT, le reste bit-identique.
    C'est la moitié du contrôle (i) — sans elle, le contraste confondrait « l'observation n'entre
    plus » avec « le génome a changé »."""
    W = np.arange(64, dtype=float).reshape(8, 8) + 1.0
    g = _G(W.copy(), num_inputs=5)
    b = make_blind(g)
    assert np.all(b.W[:5, :] == 0.0)
    assert np.array_equal(b.W[5:, :], W[5:, :])
    assert np.array_equal(g.W, W), "make_blind a MUTÉ son entrée : le bras intact serait contaminé"


def test_check_blind_REFUSE_une_intervention_qui_touche_autre_chose():
    """Branche négative du contrôle (i). Sans elle, une intervention qui écraserait tout le génome
    passerait — et le gain de survie mesuré ne voudrait rien dire."""
    W = np.ones((8, 8))
    ref = _G(W.copy(), num_inputs=5)
    assert check_blind(make_blind(ref), ref) is True

    trop = make_blind(ref)
    trop.W[6, 0] = 0.0                       # touche une ligne NON-entrée
    assert check_blind(trop, ref) is False

    pas_assez = _G(W.copy(), num_inputs=5)   # rien n'a été annulé
    assert check_blind(pas_assez, ref) is False


# --------------------------------------------------------------------------------------------------
# 2. LES CONTRÔLES passent avant la DV
# --------------------------------------------------------------------------------------------------

def test_un_AVEUGLE_encore_SENSIBLE_a_l_ablation_bloque_la_lecture():
    """Contrôle (ii) : si l'ablation de perception change encore la survie de l'AVEUGLE, c'est qu'il
    voit encore — le bras ne mesure pas ce qu'on croit, et la DV n'est pas lisible."""
    v = blind_champion_verdict(_lignes([(27.5, 38.2)] * 7, within_aveugle=0.5))
    assert v["verdict"] == "INDETERMINE-HARNAIS"
    assert "voit encore" in " ".join(v["echecs"])


def test_une_intervention_NON_MINIMALE_bloque_la_lecture():
    rows = _lignes([(27.5, 38.2)] * 7)
    rows[3]["blind"]["w_ok"] = False
    v = blind_champion_verdict(rows)
    assert v["verdict"] == "INDETERMINE-HARNAIS" and "(i)" in " ".join(v["echecs"])


def test_un_BRAS_MANQUANT_n_est_pas_un_bras_NUL():
    """Forme (a) du biais du dépôt : une cellule absente ne doit pas se lire comme une mesure."""
    rows = _lignes([(27.5, 38.2)] * 7)
    rows[2]["blind"] = None
    v = blind_champion_verdict(rows)
    assert v["verdict"] == "INDETERMINE-HARNAIS" and "un bras manque" in " ".join(v["echecs"])


def test_un_seed_dont_le_bras_INTACT_est_sous_le_plancher_est_ECARTE_et_NOMME():
    rows = _lignes([(27.5, 38.2)] * 6 + [(10.0, 40.0)])
    v = blind_champion_verdict(rows)
    assert v["ecartes"] == [rows[-1]["seed"]] and v["n"] == 6
    assert v["verdict"] == "AVEUGLE_SURVIT_MIEUX"


# --------------------------------------------------------------------------------------------------
# 3. LES TROIS BRANCHES de la DV, en forme close
# --------------------------------------------------------------------------------------------------

def test_AVEUGLE_SURVIT_MIEUX_a_la_dose_observee():
    """RÉPONSE CONNUE : la dose du n=1 (27,5 → 38,2 soit r=1,389) répliquée sur 7 seeds donne
    r_blind = 1,389 et sign_p = 2/2^7 = 0,0156 < 0,05."""
    v = blind_champion_verdict(_lignes([(27.5, 38.2)] * 7))
    assert v["verdict"] == "AVEUGLE_SURVIT_MIEUX"
    assert abs(v["r_blind"] - 38.2 / 27.5) < 1e-9
    assert v["sign_p"] < 0.05 and v["n"] == 7


def test_PAS_DE_COUT_retracte_l_observation_a_n_egal_1():
    """Branche NÉGATIVE indispensable : l'observation d'origine est positive et à n=1. Sans une
    branche qui sait la RÉTRACTER, le dispositif ne pourrait que la confirmer (classe E1)."""
    v = blind_champion_verdict(_lignes([(30.0, 30.0)] * 7))
    assert v["verdict"] == "PAS_DE_COUT" and v["r_blind"] <= 1.05
    v2 = blind_champion_verdict(_lignes([(30.0, 24.0)] * 7))        # l'aveugle survit MOINS
    assert v2["verdict"] == "PAS_DE_COUT"


def test_INDETERMINE_dans_la_bande_ET_quand_le_signe_ne_suit_pas():
    """Deux façons distinctes d'être indéterminé, et la seconde compte : un `r` au-dessus de la barre
    mais un signe incohérent entre seeds n'est PAS un résultat."""
    assert blind_champion_verdict(_lignes([(30.0, 33.0)] * 7))["verdict"] == "INDETERMINE"

    melange = _lignes([(30.0, 45.0), (30.0, 45.0), (30.0, 45.0), (30.0, 45.0),
                       (30.0, 20.0), (30.0, 20.0), (30.0, 20.0)])
    v = blind_champion_verdict(melange)
    assert v["r_blind"] >= 1.20 and v["sign_p"] >= 0.05 and v["verdict"] == "INDETERMINE"


def test_une_entree_VIDE_ne_fabrique_JAMAIS_un_verdict_de_fond():
    for vide in ([], None, ()):
        assert blind_champion_verdict(vide)["verdict"] == "INDETERMINE-SANS-MESURE"


def test_MOINS_DE_DEUX_seeds_exploitables_ne_conclut_pas():
    rows = _lignes([(27.5, 38.2)] + [(5.0, 40.0)] * 6)      # 6 seeds sous le plancher
    assert blind_champion_verdict(rows)["verdict"] == "INDETERMINE-DEGENERE"


# --------------------------------------------------------------------------------------------------
# 4. LE RUNNER — garde en tête, appariement, et intervention réellement posée
# --------------------------------------------------------------------------------------------------

def _map_fn(par_subject):
    vus = []

    def map_fn(worlds=None, seed=None, K=None, subject=None, **kw):
        aveugle = bool(np.all(subject.W[:subject.num_inputs, :] == 0.0))
        vus.append({"seed": seed, "K": K, "aveugle": aveugle, **kw})
        return {worlds[0]: {"intact_median": par_subject[aveugle], "within_ratio": 1.0,
                            "verdict": "PERCEPTION_DECOY", "floor": 24.0, "between_ratio": 1.0, "n": K}}
    map_fn.vus = vus
    return map_fn


def _champion_fn():
    W = np.ones((10, 10))
    return _G(W, num_inputs=5, num_outputs=4)


def test_le_runner_REFUSE_un_plan_VIDE_ou_un_regime_degenere():
    def _sentinelle(**kw):
        raise AssertionError("une cellule a été lancée alors que la garde aurait dû refuser AVANT")

    with pytest.raises(ValueError, match="degenere"):
        run_blind_champion(seeds=[], map_fn=_sentinelle, champion_fn=_sentinelle)
    for mauvais in ({"k": 0}, {"regime": {"num_agents": 0, "max_ticks": 200}},
                    {"regime": {"num_agents": 12, "max_ticks": 0}}):
        with pytest.raises(ValueError, match="degenere"):
            run_blind_champion(seeds=[1], map_fn=_sentinelle, champion_fn=_sentinelle, **mauvais)


def test_le_runner_APPARIE_les_deux_bras_sur_LE_MEME_seed_de_monde():
    """L'appariement est la moitié du dispositif : deux bras mesurés sur des mondes différents ne se
    contrastent pas. Réponse connue : 2 cellules par seed, mêmes graines, une aveugle et une non."""
    mf = _map_fn({False: 27.5, True: 38.2})
    rows, v = run_blind_champion(seeds=[11, 22, 33], map_fn=mf, champion_fn=_champion_fn,
                                 verbose=False)
    assert [r["seed"] for r in rows] == [11, 22, 33]
    for s in (11, 22, 33):
        cellules = [x for x in mf.vus if x["seed"] == s]
        assert len(cellules) == 2 and {c["aveugle"] for c in cellules} == {False, True}
    assert abs(v["r_blind"] - 38.2 / 27.5) < 1e-9, "le ratio apparié n'est pas celui de la dose"
    # ⚠️ A n=3, `sign_p` vaut AU MIEUX 2/2^3 = 0.25 : le verdict ne PEUT pas etre significatif, quelle
    # que soit la dose. L'instrument doit donc rendre INDETERMINE ici -- et c'est ce qu'on exige, plutot
    # que de lire un « pas d'effet » qui serait structurel (classe E2). Le meme dispositif a n=7
    # bascule, ce que le cas `test_AVEUGLE_SURVIT_MIEUX_a_la_dose_observee` verifie.
    assert v["verdict"] == "INDETERMINE" and v["sign_p"] == 0.25


def test_le_runner_POSE_reellement_l_aveuglement_et_le_VERIFIE():
    """Contrôle E1 par construction : si le runner passait le MÊME génome aux deux bras, `w_ok`
    serait faux et le verdict basculerait en INDETERMINE-HARNAIS — donc ce test mourrait."""
    mf = _map_fn({False: 27.5, True: 38.2})
    rows, _ = run_blind_champion(seeds=[11], map_fn=mf, champion_fn=_champion_fn, verbose=False)
    assert rows[0]["blind"]["w_ok"] is True
    assert {c["aveugle"] for c in mf.vus} == {False, True}
