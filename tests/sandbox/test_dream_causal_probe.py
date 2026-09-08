from tools.dream_causal_probe import dose_response_verdict


def test_dose_response_benefique_when_survival_rises_with_K():
    per_arm = {"off": [0.10, 0.10, 0.10, 0.10, 0.10],
               1: [0.12, 0.12, 0.12, 0.12, 0.12],
               4: [0.16, 0.16, 0.16, 0.16, 0.16],
               8: [0.20, 0.20, 0.20, 0.20, 0.20]}     # K8/off = 2.0 partout
    v = dose_response_verdict(per_arm)
    assert v["verdict"] == "CAUSE_BENEFIQUE"
    assert v["ratio"] > 1.0 and v["ratios_par_K"]["8"] > v["ratios_par_K"]["1"]


def test_dose_response_nuisible_when_survival_falls_with_K():
    per_arm = {"off": [0.20]*5, 1: [0.18]*5, 4: [0.14]*5, 8: [0.10]*5}
    assert dose_response_verdict(per_arm)["verdict"] == "CAUSE_NUISIBLE"


def test_dose_response_neutre_when_flat():
    per_arm = {"off": [0.15]*5, 1: [0.15]*5, 4: [0.151]*5, 8: [0.149]*5}
    assert dose_response_verdict(per_arm)["verdict"] == "NEUTRE"
    # ⚠️ CORRIGE le 2026-09-08. Cette ligne assertait `dose_response_verdict({})["verdict"] ==
    # "NEUTRE"` : elle GELAIT le defaut au lieu de l'attraper. Un `per_arm` VIDE n'est pas une
    # egalite entre les bras — aucune paire n'a jamais ete formee. La fonction LEVE desormais ;
    # le cas negatif apparie (`test_dose_response_empty_input_...`) prouve que ce refus sait
    # aussi NE PAS se declencher.


import pytest


@pytest.mark.slow
def test_run_causal_smoke_resets_flag(monkeypatch):
    """Smoke biosphère : 1 seed, ks=(1,) -> forme du retour ET FORCE_DREAM remis à None après."""
    monkeypatch.setenv("AGISEED_QUIET_LOG", "1")
    from src.graph_rag.async_logger import logger as async_logger
    from src.agents.mamba_agent import MambaBatchModel
    from tools.dream_causal_probe import run_causal
    from main_curriculum import _acquire_shared_db
    async_logger.start()
    try:
        db = _acquire_shared_db()
        res = run_causal([0], "stoneage", num_agents=20, max_ticks=40, shared_db=db, ks=(1,))
    finally:
        async_logger.stop()
    assert MambaBatchModel.FORCE_DREAM is None          # reset garanti (try/finally)
    assert "verdict" in res and set(res["per_arm"]) == {"off", "1"}


import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.dream_causal_probe as dc
    monkeypatch.setattr(dc, "run_causal", lambda *a, **k: {
        "ratio": 1.5, "sign_p": 0.05, "n_favorable": 5, "n": 5, "verdict": "CAUSE_BENEFIQUE",
        "ratios_par_K": {"1": 1.1, "4": 1.3, "8": 1.5},
        "per_arm": {"off": [0.1], "1": [0.11], "4": [0.13], "8": [0.15]},
        "config": {"target": "stoneage", "seeds": [0], "ks": [1, 4, 8]}})
    monkeypatch.setattr(dc.async_logger, "start", lambda: None)
    monkeypatch.setattr(dc.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dc, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DC_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dc.main()
    assert result["verdict"] == "CAUSE_BENEFIQUE"
    files = glob.glob(str(tmp_path / "results" / "dream_causal_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict"] == "CAUSE_BENEFIQUE"
    assert "commit" in data and "git_dirty" in data


# ======================================================================================================
# P2.40-bis (2026-09-08) : les TROIS defauts exposes en xfail(strict) dans
# tests/sandbox/test_orchestrator_injection.py, corriges et geles ici avec, pour CHAQUE comportement
# ajoute, son cas NEGATIF apparie (classe E1 : un correctif qui rend un controle INCREVABLE est pire
# que le defaut). Aucun monde n'est construit : injection a dose connue / verdict PUR, donc aucun bail.
#
# Les trois defauts sont la MEME forme, celle que le depot traque : une ABSENCE de mesure ressortait
# avec la valeur qui signifie « mesure nulle » (verdict NEUTRE, ratio 1.0).
# ======================================================================================================

_ATTENDU_PLANCHER = {1: 1.0, 2: 0.5, 3: 0.25, 4: 0.125, 5: 0.0625, 10: 0.001953125}


def test_sign_p_plancher_is_the_design_property_it_claims():
    """ETALON du drapeau de puissance, en FORME CLOSE : le plancher du test de signe bilateral vaut
    `2/2**n`. Il ne depend d'AUCUNE donnee — c'est ce qui en fait une propriete du DESIGN.

    Le point qui decide la frontiere du verdict : a n=1 il vaut EXACTEMENT 1.0, donc le test rend
    1.0 pour toute donnee imaginable (aucune resolution) ; des n=2 il descend a 0.5, donc la
    p-valeur VARIE avec les donnees."""
    from tools.dream_causal_probe import _sign_p_plancher
    for n, attendu in _ATTENDU_PLANCHER.items():
        assert _sign_p_plancher(n) == pytest.approx(attendu, rel=1e-12), n
    assert _sign_p_plancher(0) == 1.0


# ---------------------------------------------------------------- (a) sous-puissance STRUCTURELLE

def _dose(off, deep, k=8):
    return dose_response_verdict({"off": list(off), k: list(deep)})


def test_underpowered_single_pair_is_NOT_reported_as_a_measured_null():
    """LE DEFAUT (a), branche extreme. Reponse connue : UNE seule paire, effet x10. Le test de signe
    y est force a 1.0 quelles que soient les valeurs -> ce n'est pas « pas d'effet », c'est
    « pas de mesure ». Mesure AVANT correctif : `verdict=NEUTRE, ratio=10.0` — indiscernable, dans
    le champ lu par l'aval, d'une egalite mesuree sur 10 seeds."""
    v = _dose([0.05], [0.50])
    assert v["ratio"] == pytest.approx(10.0)
    assert v["verdict"] == "INCONCLUSIVE_UNDERPOWERED", v
    assert v["underpowered"] is True and v["sign_p_plancher"] == 1.0
    assert "SOUS-PUISSANT" in v["why"]


def test_underpowered_flag_is_raised_below_five_pairs_without_erasing_the_reading():
    """LE DEFAUT (a), le cas qui se PUBLIE vraiment : `DC_SEEDS=0,1,2` par defaut -> 3 paires, dont
    le plancher vaut 0.25 > alpha 0.1. Le verdict reste NEUTRE (a partir de 2 paires la p-valeur
    VARIE avec les donnees, donc la lecture est reelle) mais il est DRAPEAUTE, et le drapeau porte
    le chiffre qui le justifie."""
    for n in (2, 3, 4):
        v = _dose([0.10] * n, [0.20] * n)          # effet x2, separation parfaite
        assert v["verdict"] == "NEUTRE", (n, v)
        assert v["underpowered"] is True, (n, v)
        assert v["sign_p_plancher"] == pytest.approx(_ATTENDU_PLANCHER[n]), n
        assert v["n"] == n and v["why"]


def test_underpowered_flag_KNOWS_HOW_TO_STAY_DOWN_when_the_design_can_conclude():
    """CAS NEGATIF APPARIE (E1) — sans lui les deux tests ci-dessus ne prouvent rien : un drapeau
    toujours leve ne distingue rien.

    Trois etalons a reponse connue, tous a n >= 5 :
    * effet x2 sur 5 seeds -> CAUSE_BENEFIQUE, drapeau BAS (le drapeau ne mange pas un verdict) ;
    * bras STRICTEMENT identiques sur 10 seeds -> NEUTRE, drapeau BAS : c'est un vrai nul MESURE,
      et c'est exactement de ce NEUTRE-la que le NEUTRE sous-puissant devait etre distingue ;
    * le drapeau ne depend QUE du nombre de paires : a n=10, effet present ou absent, il reste bas ;
      a n=3, effet present ou absent, il reste leve."""
    v5 = _dose([0.10] * 5, [0.20] * 5)
    assert v5["verdict"] == "CAUSE_BENEFIQUE" and v5["underpowered"] is False
    assert v5["sign_p"] == pytest.approx(0.0625)

    plat = _dose([0.15] * 10, [0.15] * 10)
    assert plat["verdict"] == "NEUTRE" and plat["underpowered"] is False, plat
    assert "why" not in plat, "un nul MESURE ne doit porter aucune explication de sous-puissance"

    assert _dose([0.15] * 10, [0.30] * 10)["underpowered"] is False
    assert _dose([0.15] * 3, [0.15] * 3)["underpowered"] is True   # plat ET sous-puissant


def test_underpowered_verdict_KNOWS_HOW_TO_STAY_NEUTRE_on_two_pairs():
    """CAS NEGATIF APPARIE de la FRONTIERE elle-meme (n<2). Si le verdict basculait des que le
    design est sous-puissant, le n=3 du run par defaut deviendrait INCONCLUSIVE — ce n'est PAS ce
    qui est livre. Reponse connue : a 2 paires le plancher vaut 0.5 (< 1.0), donc la p-valeur
    discrimine encore une direction CONSTANTE d'une direction INCOHERENTE, et le verdict reste une
    lecture NEUTRE drapeautee."""
    coherent = _dose([0.10, 0.10], [0.20, 0.20])
    incoherent = _dose([0.10, 0.10], [0.20, 0.05])
    assert (coherent["verdict"], incoherent["verdict"]) == ("NEUTRE", "NEUTRE")
    assert coherent["sign_p"] == pytest.approx(0.5) and incoherent["sign_p"] == pytest.approx(1.0)


# ------------------------------------------------------- (b) bras SANS AUCUNE paire informative

def test_arm_without_a_single_informative_pair_is_NOT_published_as_ratio_one():
    """LE DEFAUT (b). Reponse connue : off et K1 tous ETEINTS, K8 seul vivant. AVANT correctif la
    courbe rendue etait `{1: 1.0, 8: 5e4}` et se lisait « K1 neutre, K8 spectaculaire » — alors que
    K1 n'a AUCUNE paire informative. 1.0 est precisement la valeur qui signifie « aucun effet » :
    la publier pour une absence de mesure melange les deux dans la MEME courbe.

    `None` (et pas `nan`) parce que le resultat est persiste en JSON par `Harness.save`."""
    v = dose_response_verdict({"off": [0.0] * 5, 1: [0.0] * 5, 8: [0.05] * 5})
    assert v["ratios_par_K"]["1"] is None, v["ratios_par_K"]
    assert v["n_par_K"]["1"] == 0 and v["n_ecartees_par_K"]["1"] == 5
    assert v["ratios_par_K"]["8"] > 1000.0            # artefact connu du plancher eps=1e-6
    assert v["n_par_K"]["8"] == 5 and v["n_ecartees_par_K"]["8"] == 0
    import json
    assert json.loads(json.dumps(v["ratios_par_K"]))["1"] is None   # serialisable


def test_a_REAL_ratio_of_one_is_still_published_as_one():
    """CAS NEGATIF APPARIE (E1). Le correctif (b) doit distinguer « pas de mesure » de « mesure
    nulle », PAS effacer la seconde : un bras dont toutes les paires sont informatives et
    rigoureusement egales a `off` vaut bien 1.0, et doit continuer a le dire.

    Sans ce cas, remplacer tous les 1.0 par `None` passerait le test precedent."""
    v = dose_response_verdict({"off": [0.10] * 5, 1: [0.10] * 5, 8: [0.20] * 5})
    assert v["ratios_par_K"]["1"] == pytest.approx(1.0), v["ratios_par_K"]
    assert v["n_par_K"]["1"] == 5 and v["n_ecartees_par_K"]["1"] == 0
    assert v["ratios_par_K"]["8"] == pytest.approx(2.0)


def test_empty_input_is_REFUSED_instead_of_being_called_neutral():
    """LE DEFAUT (c), cote verdict PUR. AVANT correctif, `dose_response_verdict({})` rendait
    `{'verdict': 'NEUTRE', 'ratio': 1.0, 'sign_p': 1.0, 'n': 0}` : l'affirmation de FOND « le reve
    n'a aucun effet causal » sans qu'AUCUNE ere n'ait ete comparee. C'est cette valeur que
    `run_causal` publiait quand sa garde avait consomme ses iterateurs."""
    for entree in ({}, {"off": []}, {"off": [0.1, 0.2]}, {"off": [], 8: [0.1]},
                   {8: [0.1, 0.2]}, {"off": [0.1, 0.2], 8: []}):
        with pytest.raises(ValueError, match="degenere"):
            dose_response_verdict(entree)


def test_empty_input_refusal_KNOWS_HOW_TO_STAY_DOWN_on_the_smallest_valid_input():
    """CAS NEGATIF APPARIE (E1) : le refus doit savoir NE PAS se declencher. Le plus petit `per_arm`
    valide (un `off` et un bras K, une seule valeur chacun) passe la garde et rend un resultat —
    marque INCONCLUSIVE_UNDERPOWERED, ce qui est le bon aveu et pas un refus."""
    v = dose_response_verdict({"off": [0.10], 8: [0.10]})
    assert v["verdict"] == "INCONCLUSIVE_UNDERPOWERED" and v["n"] == 1
    v2 = dose_response_verdict({"off": [0.10] * 5, 8: [0.10] * 5})
    assert v2["verdict"] == "NEUTRE" and v2["underpowered"] is False


# --------------------------------------------------- (c) iterateurs CONSOMMES par la garde d'entree

_AGE_REF = 200.0            # src/curriculum/competence.AGE_REF


def _injecte_eres(monkeypatch, doses, journal=None):
    """Injection a DOSE CONNUE : remplace `run_era_organ` DANS le module de la sonde. La fausse ere
    lit `MambaBatchModel.FORCE_DREAM` pour connaitre son bras -> aucun monde, aucun bail."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    def _fausse_ere(target, seed, organ_fraction=None, metab=None, payoff=None,
                    num_agents=None, max_ticks=None, shared_db=None):
        bras = MambaBatchModel.FORCE_DREAM
        if journal is not None:
            journal.append({"seed": seed, "bras": bras})
        return [{"age": float(doses[bras if bras is not None else "off"]) * _AGE_REF,
                 "founder": True}]

    monkeypatch.setattr(M, "run_era_organ", _fausse_ere)
    return M


def test_run_causal_reads_seeds_and_ks_given_as_ITERATORS(monkeypatch):
    """LE DEFAUT (c). `if not list(seeds) or not list(ks)` CONSOMMAIT ses deux entrees : la garde
    passait, puis la boucle tournait a VIDE (seeds) ou n'ouvrait que le bras `off` (ks), et le
    verdict nul etait FABRIQUE. Aggravant sur `ks` : les eres `off` etaient reellement simulees,
    donc le cout etait paye avant que le nul ne soit invente.

    Reponse connue : dose x3 sur 5 seeds -> CAUSE_BENEFIQUE des DEUX cotes, et les eres vraiment
    lancees sont 5 x (off + 3 bras) = 20."""
    doses = {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.30}
    journal = []
    M = _injecte_eres(monkeypatch, doses, journal)

    r_seeds = M.run_causal((s for s in range(5)), target="stoneage", num_agents=4, max_ticks=10,
                           shared_db=None, ks=(8,))
    assert r_seeds["verdict"] == "CAUSE_BENEFIQUE", r_seeds
    assert r_seeds["n"] == 5 and r_seeds["config"]["seeds"] == [0, 1, 2, 3, 4]

    journal.clear()
    r_ks = M.run_causal([0, 1, 2, 3, 4], target="stoneage", num_agents=4, max_ticks=10,
                        shared_db=None, ks=(k for k in (1, 4, 8)))
    assert r_ks["verdict"] == "CAUSE_BENEFIQUE", r_ks
    assert set(r_ks["ratios_par_K"]) == {"1", "4", "8"} and r_ks["config"]["ks"] == [1, 4, 8]
    assert len(journal) == 20, "les bras K n'ont pas ete ouverts (ou l'ont ete deux fois)"


def test_run_causal_STILL_REFUSES_an_EXHAUSTED_iterator(monkeypatch):
    """CAS NEGATIF APPARIE (E1), et c'est le plus important de ce fichier : materialiser l'entree ne
    doit pas rendre la garde INCREVABLE. Un iterateur DEJA EPUISE (le cas reel : une comprehension
    filtrante qui ne retient rien) est une cohorte vide et doit LEVER — instantanement, sans qu'une
    seule ere soit lancee (la fausse ere explose si elle est appelee)."""
    import tools.dream_causal_probe as M
    import time

    def _interdit(*a, **kw):
        raise AssertionError("la garde est posee APRES la construction du monde")

    monkeypatch.setattr(M, "run_era_organ", _interdit)
    epuise = iter([0, 1])
    list(epuise)                                    # consomme : l'iterateur est mort
    base = dict(target="stoneage", num_agents=4, max_ticks=10, shared_db=None)
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        M.run_causal(epuise, ks=(1, 4, 8), **base)
    with pytest.raises(ValueError, match="degenere"):
        M.run_causal((s for s in []), ks=(1, 4, 8), **base)
    with pytest.raises(ValueError, match="degenere"):
        M.run_causal([0, 1], ks=(k for k in []), **base)
    with pytest.raises(ValueError, match="degenere"):
        M.run_causal(map(int, "01"), ks=(1,), num_agents=0, max_ticks=10, target="stoneage",
                     shared_db=None)
    assert time.time() - t0 < 0.5, "refus trop lent : la garde n'est plus en tete"


def test_run_founder_matched_reads_an_ITERATOR_and_still_refuses_an_empty_one(monkeypatch):
    """MEME defaut, MEME correctif, dans l'autre orchestrateur du fichier (`run_founder_matched`
    ecrivait lui aussi `if not list(seeds)`), avec son cas negatif apparie dans le meme test.

    Reponse connue : fondateurs off=20 ticks / on=60 ticks sur 5 seeds -> med_founder ratio 3.0 ;
    et un generateur VIDE leve toujours."""
    import tools.dream_causal_probe as M

    def _fausse_ere(target, seed, organ_fraction=None, metab=None, payoff=None,
                    num_agents=None, max_ticks=None, shared_db=None):
        from src.agents.mamba_agent import MambaBatchModel
        age = 20.0 if MambaBatchModel.FORCE_DREAM == "off" else 60.0
        return [{"age": age, "founder": True}, {"age": 1.0, "founder": False}]

    monkeypatch.setattr(M, "run_era_organ", _fausse_ere)
    out = M.run_founder_matched((s for s in range(5)), num_agents=4, max_ticks=10)
    assert out["config"]["seeds"] == [0, 1, 2, 3, 4] and len(out["rows"]) == 5
    assert out["med_founder"]["ratio"] == pytest.approx(3.0)

    with pytest.raises(ValueError, match="degenere"):
        M.run_founder_matched((s for s in []), num_agents=4, max_ticks=10)


# ======================================================================================================
# REFUTATION du correctif P2.40-bis (2026-09-08). Ces cas ne relisent pas le correctif : ils l'ont
# CASSE. Trois defauts REELS confirmes par sonde, tous de la famille que le depot traque -- une
# absence de mesure ressortant avec la valeur qui signifie « mesure nulle ».
#
# Comme au-dessus : aucun monde construit (verdict PUR / injection a dose connue), donc aucun bail.
# ======================================================================================================


def test_the_n_that_is_published_is_the_DENOMINATOR_of_the_sign_test():
    """DEFAUT (d) TROUVE EN REFUTATION. Le test de signe JETTE les ex aequo (`r != 1.0`) mais `n`,
    `underpowered` et `sign_p_plancher` etaient calcules sur TOUTES les paires : ils decrivaient un
    test qui n'a pas tourne.

    Reponse connue, en forme close : 6 paires dont 3 EX AEQUO exacts et 3 favorables x2. Le test de
    signe tourne sur 3 paires, dont le plancher vaut 0.25 -- soit >= alpha 0.1 : ce NEUTRE ne POUVAIT
    pas etre autre chose. Mesure AVANT correctif : `underpowered=False, sign_p_plancher=0.03125`, et
    AUCUN champ ne disait que le sign_p 0.25 reposait sur 3 paires et non sur les 6 annoncees.

    Les ex aequo ne sont pas exotiques : `survival_competence` est une mediane d'ages ENTIERS / 200,
    donc une grille discrete -- en regime plancher, 13.9 % des paires sont ex aequo sous H0."""
    v = _dose([0.10] * 6, [0.10, 0.10, 0.10, 0.20, 0.20, 0.20])
    assert (v["verdict"], v["n"]) == ("NEUTRE", 6)          # le VERDICT est inchange (contrainte gelee)
    assert v["ratio"] == pytest.approx(1.5) and v["sign_p"] == pytest.approx(0.25)
    assert v["n_effectif"] == 3 and v["n_ex_aequo"] == 3
    assert v["sign_p_plancher_effectif"] == pytest.approx(0.25)
    assert v["sans_resolution"] is True, v
    assert "3 paire(s)" in v["why_resolution"] and "6 annoncees" in v["why_resolution"]
    assert v["sign_p"] >= v["sign_p_plancher_effectif"]     # coherence : le plancher est un plancher


def test_resolution_flag_KNOWS_HOW_TO_STAY_DOWN():
    """CAS NEGATIF APPARIE (E1) du drapeau ci-dessus -- sans lui il ne prouverait rien.

    Trois etalons :
    * l'ARTEFACT REELLEMENT PUBLIE (`results/dream_causal_0.json`, EDR-095, 10 seeds sans un seul
      ex aequo) : drapeau BAS, et les cinq champs publies re-tombent A L'IDENTIQUE -- le correctif
      ne retro-agit sur aucun chiffre grave ;
    * 5 paires toutes informatives : drapeau BAS et verdict causal (le drapeau ne mange pas un
      verdict) ;
    * un seul ex aequo suffit a le lever a n=5 : c'est exactement le n a partir duquel cette sonde
      s'autorise un verdict causal, et 52.8 % des tirages en regime plancher y ont au moins un ex
      aequo (grille discrete de survival_competence, 2000 tirages/point)."""
    import json
    import os
    racine = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    chemin = os.path.join(racine, "results", "dream_causal_0.json")
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as fh:
            d = json.load(fh)["data"]
        rejeu = dose_response_verdict({("off" if a == "off" else int(a)): v
                                       for a, v in d["per_arm"].items()})
        for champ in ("verdict", "ratio", "sign_p", "n", "n_favorable"):
            assert rejeu[champ] == d[champ], (champ, rejeu[champ], d[champ])
        assert rejeu["ratios_par_K"] == d["ratios_par_K"]
        assert rejeu["sans_resolution"] is False and rejeu["n_effectif"] == 10
        assert "why_resolution" not in rejeu

    net = _dose([0.10] * 5, [0.20] * 5)
    assert net["sans_resolution"] is False and net["verdict"] == "CAUSE_BENEFIQUE"
    assert net["n_effectif"] == 5 and net["n_ex_aequo"] == 0 and "why_resolution" not in net

    un_ex_aequo = _dose([0.10] * 5, [0.20, 0.20, 0.20, 0.20, 0.10])
    assert un_ex_aequo["n_effectif"] == 4 and un_ex_aequo["sans_resolution"] is True
    assert un_ex_aequo["underpowered"] is False, "le drapeau de DESIGN, lui, reste fonction du n"


def test_a_null_measured_on_tied_pairs_is_still_a_measured_null():
    """CAS NEGATIF APPARIE le plus important : le nouveau drapeau ne doit PAS transformer le nul
    MESURE de reference (bras strictement identiques sur 10 seeds, contrainte gelee par
    `test_run_causal_READS_the_dose_response_it_claims`, non modifiable) en indetermination.

    Le verdict reste NEUTRE, `underpowered` reste BAS, `why` (sous-puissance de DESIGN) reste ABSENT.
    Seul `why_resolution` apparait, et il dit un FAIT sur le test, pas un verdict."""
    plat = _dose([0.15] * 10, [0.15] * 10)
    assert plat["verdict"] == "NEUTRE" and plat["underpowered"] is False
    assert "why" not in plat
    assert plat["n"] == 10 and plat["n_effectif"] == 0 and plat["n_ex_aequo"] == 10
    assert plat["sans_resolution"] is True
    assert "nul MESURE" in plat["why_resolution"], plat["why_resolution"]


def test_arms_of_DIFFERENT_lengths_are_REFUSED_instead_of_being_MISPAIRED():
    """DEFAUT (e) TROUVE EN REFUTATION. `_paired_ratios` tronque par `min(len(arm), len(off))` et
    l'appariement est POSITIONNEL (aucun seed n'est porte par `per_arm`) : un bras plus long ne perd
    pas seulement des paires, il compare `arm[i]` au `off` d'un AUTRE seed.

    Reponse connue : le bras 8 porte deux fois le seed 0 (0.30) puis les seeds 1-2 ; contre un `off`
    de 3 valeurs, l'ancienne troncature rendait ratio 3.0 sur un appariement DECALE."""
    with pytest.raises(ValueError, match="degenere"):
        dose_response_verdict({"off": [0.10, 0.10, 0.10], 8: [0.30, 0.30, 0.10, 0.10, 0.10, 0.10]})
    with pytest.raises(ValueError, match="degenere"):        # bras plus COURT que off
        dose_response_verdict({"off": [0.10] * 5, 8: [0.20, 0.20]})
    with pytest.raises(ValueError, match="degenere"):        # c'est un bras SUPERFICIEL qui deraille
        dose_response_verdict({"off": [0.10] * 5, 1: [0.10, 0.10], 8: [0.20] * 5})


def test_length_refusal_KNOWS_HOW_TO_STAY_DOWN_on_rectangular_input():
    """CAS NEGATIF APPARIE (E1) : le refus de longueur ne doit pas rendre la fonction increvable.
    Toute entree RECTANGULAIRE passe -- y compris celles ou un bras entier est eteint (cas (b), qui
    doit continuer a rendre `None` et ses comptes, PAS une exception)."""
    v = dose_response_verdict({"off": [0.0] * 5, 1: [0.0] * 5, 8: [0.05] * 5})
    assert v["ratios_par_K"]["1"] is None and v["n_par_K"]["1"] == 0
    assert dose_response_verdict({"off": [0.10] * 5, 8: [0.20] * 5})["verdict"] == "CAUSE_BENEFIQUE"
    assert dose_response_verdict({"off": [0.10], 8: [0.10]})["verdict"] == "INCONCLUSIVE_UNDERPOWERED"


def test_run_causal_REFUSES_duplicate_seeds_and_duplicate_ks(monkeypatch):
    """DEFAUT TROUVE EN REFUTATION -- le plus grave des trois, et il traverse la garde que le
    correctif venait de reecrire.

    Mesure AVANT correctif, par injection a dose connue : `run_causal([0,0,0,0,0], ks=(8,))` rendait
    CAUSE_BENEFIQUE, sign_p=0.0625, n=5 a partir d'UN SEUL tirage (le seed determine entierement
    l'ere). 5 est exactement le n a partir duquel cette sonde s'autorise un verdict causal : le
    duplicat ne gonfle pas seulement le n, il FRANCHIT la frontiere du verdict.
    `ks=(8,8)` lancait 9 eres au lieu de 6 et desappariait le bras le plus profond.

    Le refus doit etre INSTANTANE : la fausse ere explose si elle est appelee."""
    import tools.dream_causal_probe as M
    import time

    def _interdit(*a, **kw):
        raise AssertionError("la garde est posee APRES la construction du monde")

    monkeypatch.setattr(M, "run_era_organ", _interdit)
    base = dict(target="stoneage", num_agents=4, max_ticks=10, shared_db=None)
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        M.run_causal([0, 0, 0, 0, 0], ks=(8,), **base)
    with pytest.raises(ValueError, match="degenere"):
        M.run_causal([0, 1, 2], ks=(8, 8), **base)
    with pytest.raises(ValueError, match="degenere"):
        M.run_founder_matched([0, 0, 1], num_agents=4, max_ticks=10)
    assert time.time() - t0 < 0.5, "refus trop lent : la garde n'est plus en tete"


def test_duplicate_refusal_KNOWS_HOW_TO_STAY_DOWN_on_distinct_seeds(monkeypatch):
    """CAS NEGATIF APPARIE (E1) du refus ci-dessus : des seeds DISTINCTS (y compris non consecutifs,
    non tries, negatifs) passent et rendent le verdict attendu a dose connue -- sinon le refus serait
    une garde increvable qui condamne l'usage normal."""
    M = _injecte_eres(monkeypatch, {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.30})
    v = M.run_causal([7, 3, 11, -2, 5], target="stoneage", num_agents=4, max_ticks=10,
                     shared_db=None, ks=(1, 4, 8))
    assert v["verdict"] == "CAUSE_BENEFIQUE" and v["n"] == 5
    assert v["config"]["seeds"] == [7, 3, 11, -2, 5]


def test_founder_matched_does_NOT_publish_a_ratio_of_ZERO_from_an_UNMEASURABLE_arm(monkeypatch):
    """DEFAUT TROUVE EN REFUTATION dans l'AUTRE orchestrateur du fichier -- la garde de
    `_paired_ratios` (2026-07-21 : deux bras identiques et eteints rendaient CAUSE_NUISIBLE,
    ratio 0.0) n'avait JAMAIS ete retro-appliquee a `_pair`, dans le meme fichier (classe E14).

    Trois portes d'entree mesurees, toutes rendant `ratio = 0.0`, c.-a-d. « le reve ANNULE la survie
    des fondateurs » -- le negatif maximal, a partir d'AUCUNE mesure :
      (1) eres rendant une cohorte VIDE ; (2) des agents mais AUCUN fondateur ;
      (3) deux bras strictement identiques et ETEINTS (ages nuls des deux cotes).

    ⚠️ CONTRAT DURCI le 2026-09-08 (classe E14 : une garde ajoutee change le contrat de TOUTES ses
    fixtures, et re-ecrire les tests existants fait partie du correctif). La premiere version de ce
    test exigeait `n_cellules_doublement_nulles == 5` sur les TROIS doses -- c.-a-d. qu'elle
    demandait a l'instrument d'affirmer « les deux bras sont ETEINTS » pour les doses (1) et (2),
    ou AUCUN age n'a jamais ete lu. C'etait la meme confusion, d'un cran plus haut : le compte de
    cellules eteintes est une MESURE, et une cellule non mesurable n'en est pas une.
    Ces trois doses ne sont plus une seule reponse mais TROIS, et c'est le progres :
      (1) et (2) -> INDETERMINE, `n_non_mesurables = 5`, `n_cellules_doublement_nulles = 0` ;
      (3)        -> MESURE (un fondateur existe, son age vaut 0.0), donc `n = 5`,
                    `n_cellules_doublement_nulles = 5` et le `why` du ratio indefini.
    La difference entre (1)/(2) et (3) est exactement celle entre « pas de mesure » et « mesure
    nulle » ; l'ancien contrat les rendait indiscernables."""
    import json
    import tools.dream_causal_probe as M

    for nom, ere, attendu in (
        ("cohorte VIDE", lambda *a, **k: [],
         {"statut": "INDETERMINE_AUCUNE_PAIRE_MESURABLE", "n": 0, "n_non_mesurables": 5,
          "n_cellules_doublement_nulles": 0, "marqueur_why": "ABSENCE DE MESURE"}),
        ("aucun FONDATEUR", lambda *a, **k: [{"age": 7.0, "founder": False}],
         {"statut": "INDETERMINE_AUCUNE_PAIRE_MESURABLE", "n": 0, "n_non_mesurables": 5,
          "n_cellules_doublement_nulles": 0, "marqueur_why": "ABSENCE DE MESURE"}),
        ("doublement ETEINT", lambda *a, **k: [{"age": 0.0, "founder": True}],
         {"statut": "MESURE", "n": 5, "n_non_mesurables": 0,
          "n_cellules_doublement_nulles": 5, "marqueur_why": "annule la survie"}),
    ):
        monkeypatch.setattr(M, "run_era_organ", ere)
        out = M.run_founder_matched([0, 1, 2, 3, 4], num_agents=4, max_ticks=10)
        bloc = out["med_founder"]
        assert bloc["ratio"] is None, (nom, bloc)
        for champ in ("statut", "n", "n_non_mesurables", "n_cellules_doublement_nulles"):
            assert bloc[champ] == attendu[champ], (nom, champ, bloc)
        assert attendu["marqueur_why"] in bloc["why"], (nom, bloc.get("why"))
        assert json.loads(json.dumps(bloc))["ratio"] is None, nom      # serialisable (out_path)


def test_founder_matched_ratio_KNOWS_HOW_TO_BE_A_NUMBER(monkeypatch):
    """CAS NEGATIF APPARIE (E1) : le correctif ci-dessus doit distinguer « pas de mesure » de
    « mesure », PAS effacer les ratios. Reponse connue : fondateurs off=20 / on=60 -> ratio 3.0,
    `n_effectif` = le denominateur reel du test de signe, `why` ABSENT.

    Et le cas limite qui compte : un bras `on` ETEINT alors que `off` est mesurable est un vrai
    ratio de 0.0 (le reve a bien tue les fondateurs) -- il doit continuer a se publier."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    def _ere(target, seed, *a, **k):
        return [{"age": 20.0 if MambaBatchModel.FORCE_DREAM == "off" else 60.0, "founder": True}]

    monkeypatch.setattr(M, "run_era_organ", _ere)
    bloc = M.run_founder_matched([0, 1, 2, 3, 4], num_agents=4, max_ticks=10)["med_founder"]
    assert bloc["ratio"] == pytest.approx(3.0) and "why" not in bloc
    assert bloc["n"] == 5 and bloc["n_effectif"] == 5 and bloc["n_ex_aequo"] == 0
    assert bloc["n_cellules_doublement_nulles"] == 0

    def _ere_on_mort(target, seed, *a, **k):
        return [{"age": 20.0 if MambaBatchModel.FORCE_DREAM == "off" else 0.0, "founder": True}]

    monkeypatch.setattr(M, "run_era_organ", _ere_on_mort)
    mort = M.run_founder_matched([0, 1, 2, 3, 4], num_agents=4, max_ticks=10)["med_founder"]
    assert mort["ratio"] == pytest.approx(0.0), "un VRAI zero mesure doit rester publie"
    assert mort["n_cellules_doublement_nulles"] == 0 and "why" not in mort


# ------------------------------------------------------------ (f) L'ERE QUI NE REND RIEN (2e refuteur)
# DEFAUT CONFIRME PAR INJECTION, et il etait SIGNALE mais LAISSE OUVERT par la passe precedente,
# au motif que le corriger exigerait de « changer la SIGNATURE et le contrat de
# `dose_response_verdict` ». C'est faux, et c'est ce qui a fait rester le defaut : la garde se pose
# dans `run_causal`, sur la valeur que `run_era_organ` vient de rendre, sans toucher a
# `dose_response_verdict` ni a aucun de ses tests geles.

def test_run_causal_REFUSES_an_era_that_returned_NO_agent_at_all(monkeypatch):
    """DEFAUT NEUF-ANCIEN, le biais negatif #1 du depot, un etage AU-DESSUS de celui corrige dans
    `run_founder_matched` -- et jamais retro-applique ici (classe E14).

    Le mecanisme : `run_causal` appelle `survival_competence(stats)` et JETTE `len(stats)`.
    `survival_competence([])` vaut 0.0 (`src/curriculum/competence.py:18`, `_median_norm` :
    `if not values or ref <= 0: return 0.0`), donc une ere qui n'a RIEN rendu devient une
    competence 0.0 STRICTEMENT indiscernable d'une competence 0.0 MESUREE. Et `_paired_ratios`
    n'ecarte une paire que si les DEUX bras sont sous eps : un seul bras vide passe.

    Mesure AVANT correctif, par injection a dose connue, sans monde (bras K=8 rendant [] sur les
    10 seeds, les autres a 40 ticks) :
        {'verdict': 'CAUSE_NUISIBLE', 'ratio': 0.0, 'sign_p': 0.001953125, 'n': 10,
         'n_favorable': 0, 'n_ecartees': 0, 'underpowered': False, 'sans_resolution': False}
        per_arm['8'] = [0.0] * 10
    Soit le negatif MAXIMAL et SIGNIFICATIF, sans qu'un seul age ait ete lu -- et aucun des trois
    drapeaux poses le meme jour ne s'allume, parce qu'ils portent tous sur des COMPTES DE PAIRES,
    et que les paires, elles, sont bien la.

    Pourquoi LEVER et pas exclure (a l'inverse de `_pair_rows`) : `run_era_organ` rend TOUS les
    agents, morts compris (FIX A d'EDR-092), donc au minimum les `num_agents` fondateurs. Zero
    agent est un compte IMPOSSIBLE, pas un petit compte : etat invalide, pas mesure manquante. Et
    `run_causal` ne persiste aucune trace par seed, donc exclure retrancherait du `n` publie en
    silence, sans rien laisser a diagnostiquer."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    def _ere_muette(target, seed, *a, **k):
        if MambaBatchModel.FORCE_DREAM == 8:
            return []                                        # l'ere ne rend RIEN
        return [{"age": 40.0, "founder": True} for _ in range(5)]

    monkeypatch.setattr(M, "run_era_organ", _ere_muette)
    with pytest.raises(ValueError, match="AUCUN agent"):
        M.run_causal(list(range(10)), target="stoneage", num_agents=5, max_ticks=10,
                     shared_db=None, ks=(8,))


def test_run_causal_STILL_says_HARMFUL_on_a_MEASURED_collapse(monkeypatch):
    """CAS NEGATIF APPARIE (E1) du refus ci-dessus -- le plus important des deux.

    Un correctif qui rendrait `CAUSE_NUISIBLE` INATTEIGNABLE serait pire que le defaut : la sonde
    existe precisement pour pouvoir prononcer ce verdict (c'est celui d'EDR-095). La garde doit
    donc separer « aucun agent rendu » (mesure ABSENTE) de « des agents rendus, tous morts a t=0 »
    (effondrement MESURE) -- deux etats que `survival_competence` ecrase tous les deux sur 0.0, et
    que seul `len(stats)` distingue.

    Reponse connue : cohorte NON VIDE de 5 agents a age=0 dans le bras profond, 40 ticks ailleurs
    -> CAUSE_NUISIBLE, ratio 0.0, sign_p 2/2**10 = 0.001953125. Et le no-op exact : bras
    identiques -> NEUTRE."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    def _fabrique(age_profond):
        def _ere(target, seed, *a, **k):
            age = age_profond if MambaBatchModel.FORCE_DREAM == 8 else 40.0
            return [{"age": float(age), "founder": True} for _ in range(5)]
        return _ere

    monkeypatch.setattr(M, "run_era_organ", _fabrique(0.0))
    base = dict(target="stoneage", num_agents=5, max_ticks=10, shared_db=None, ks=(8,))
    mort = M.run_causal(list(range(10)), **base)
    assert mort["verdict"] == "CAUSE_NUISIBLE", mort
    assert mort["ratio"] == pytest.approx(0.0), mort
    assert mort["sign_p"] == pytest.approx(2.0 / 2 ** 10), mort
    assert mort["per_arm"]["8"] == [0.0] * 10, mort

    monkeypatch.setattr(M, "run_era_organ", _fabrique(40.0))
    plat = M.run_causal(list(range(10)), **base)
    assert plat["verdict"] == "NEUTRE" and plat["ratio"] == pytest.approx(1.0), plat


def test_run_causal_empty_era_refusal_NAMES_the_seed_and_the_arm(monkeypatch):
    """Le refus doit etre DIAGNOSTIQUE, pas seulement correct.

    `run_causal` ne persiste rien par seed : si le message ne nomme pas OU l'ere s'est tue, la
    seule information disponible sur un run de plusieurs heures est « ca a leve ». On exige donc
    le seed ET le bras. Dose : la 4e ere du bras `off` (seed 3) est la seule muette -- les trois
    seeds precedents ont bien tourne, ce qui prouve aussi que la garde n'est pas un refus pose en
    tete qui n'aurait jamais rien mesure."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    def _ere(target, seed, *a, **k):
        if int(seed) == 3 and MambaBatchModel.FORCE_DREAM == "off":
            return []
        return [{"age": 40.0, "founder": True} for _ in range(5)]

    monkeypatch.setattr(M, "run_era_organ", _ere)
    with pytest.raises(ValueError) as exc:
        M.run_causal([0, 1, 2, 3, 4], target="stoneage", num_agents=5, max_ticks=10,
                     shared_db=None, ks=(8,))
    msg = str(exc.value)
    assert "seed=3" in msg and "off" in msg, msg
    assert "MESURE ABSENTE" in msg, msg
    assert MambaBatchModel.FORCE_DREAM is None, "etat global de classe non restaure (classe E5)"
