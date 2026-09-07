"""Cas de CALIBRATION du runner S6 (`s2_fallback_rate_probe.py`).

Destination : `tests/sandbox/test_instrument_calibration.py` (helpers prefixes `_s6_`, imports dans
les corps de test -- conventions du fichier d'accueil).

Ce que ces cas confrontent a une REPONSE CONNUE, dans l'ordre des trois formes du protocole :

  * NO-OP EXACT (specificite)  -- sigma=0 rend une trajectoire BIT-IDENTIQUE a `fit_policy`
    d'origine, y compris DANS LA CELLULE OU LE HILL-CLIMB ACCEPTE (sans quoi on ne testerait que
    la branche ou la boucle ne fait rien) ; le plancher mesure vaut sa FORME CLOSE ; le barreau
    'true' ne touche pas l'entree ; `zero` est le seul barreau a CRN exact, et on le MESURE.
  * PREDICTION (linearite en la dose imposee) -- l'echelle de l'init est lineaire en sigma ; la
    couche d'agregation, alimentee par INJECTION a dose connue, rend le verdict predit ; le GATE
    d'admissibilite bascule exactement ou il est pre-enregistre.
  * MONOTONIE / DIRECTION -- le compteur de morsure bascule au bon endroit ; une politique qui LIT
    fait diverger les bras, une politique constante les rend identiques point par point.

Le cas central est le CONTRE-EXEMPLE CONSTRUIT : il prouve que l'enonce "corps suffisant =>
ablation inerte" est FAUX comme propriete des POLITIQUES. L'inertie de S2-004 est une propriete de
l'INIT (W=0 jamais quittee), pas du REGIME. Un second contre-exemple construit prouve que le
barreau `zero` RATE des lecteurs -- c'est le defaut qui a fait changer le DV du runner.
"""


def _s6_probe():
    """Le runner S6, integre au depot le 2026-09-07 (il vivait dans le scratchpad pendant sa mise au
    point). ⚠️ Import par le PAQUET `tools.` : un import par nom nu ne marcherait que si `tools/`
    etait dans sys.path, ce qui masquerait un deplacement du fichier."""
    import importlib
    import os
    import sys
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("tools.s2_fallback_rate_probe")


def _s6_cell(body_gain=1.2, cog_gain=2.0, currency="energy", K=5, ticks=300):
    return {"body_gain": body_gain, "cog_gain": cog_gain, "currency": currency,
            "K": K, "ticks": ticks}


def _s6_lives(W, b, mode, cell, seed=0, n_eval=24):
    """24 vies d'une politique DONNEE, dans le mesureur IMPORTE, sur les graines CRN du runner."""
    import numpy as np
    from tools.cognitive_demand_world_probe import survive
    P = _s6_probe()
    return [int(survive(W, b, mode, cell["body_gain"], cell["cog_gain"], cell["currency"],
                        cell["K"], np.random.RandomState(ls), cell["ticks"]))
            for ls in P.life_seeds(seed, n_eval)]


def _s6_reading_policy(K=5, bias_action=1, bias=0.5):
    """La politique CONSTRUITE qui LIT : W = identite (lecture directe de l'obs one-hot), plus un
    biais sur une action NON-corps -- de sorte que, obs mise a zero, la politique tombe sur une
    action CONSTANTE qui n'est PAS l'action corps."""
    import numpy as np
    W = np.eye(K)
    b = np.zeros(K)
    b[bias_action] = bias
    return W, b


def _s6_reading_policy_body_default(K=5):
    """LA MEME politique lectrice, mais SANS biais : obs mise a zero -> W@0 + 0 = vecteur nul ->
    argmax = 0 = l'action CORPS. Elle LIT autant que la precedente, et pourtant le barreau `zero`
    la declarera inerte. C'est le contre-exemple qui condamne `zero` comme DV."""
    import numpy as np
    return np.eye(K), np.zeros(K)


def _s6_record(cell="c1-N", sigma=0.3, seed=0, intact=300.0, abl=300.0, floor=300.0, ticks=300,
               obs_weight=0.0, n_accepted=0, b_argmax=0, n_eval=24, body_gain=1.2,
               iters=300, episodes=5, abl_by_mode=None):
    """Record FABRIQUE : teste la couche d'AGREGATION par injection, a cout de simulation NUL.

    Les champs derives passent par les VRAIES fonctions du runner (`bites`, `win_frac`,
    `original_ladder_verdict`), pour que le test porte sur le code livre et non sur une copie."""
    P = _s6_probe()
    lives = {"true": [int(intact)] * n_eval}
    for m in ("permuted", "noise", "zero"):
        v = float(abl if abl_by_mode is None else abl_by_mode.get(m, abl))
        lives[m] = [int(v)] * n_eval
    dv = {m: float(sorted(v)[len(v) // 2]) for m, v in lives.items()}
    ratios = {m: float(dv["true"] / max(dv[m], 1e-9)) for m in ("permuted", "noise", "zero")}
    rec = {"schema": P.SCHEMA, "cell": cell, "sigma": float(sigma), "seed": int(seed),
           "ticks": ticks, "body_gain": body_gain, "cog_gain": 2.0, "currency": "energy", "K": 5,
           "iters": iters, "episodes": episodes, "n_eval": n_eval,
           "floor": float(floor), "floor_lives": [int(floor)] * n_eval,
           "floor_deterministic": True,
           "obs_weight": float(obs_weight), "n_accepted": int(n_accepted),
           "best_score": float(intact), "init_score": float(intact),
           "b_argmax": int(b_argmax), "lives": lives, "dv": dv, "ratios": ratios,
           "bites": {m: P.bites(r) for m, r in ratios.items()},
           "bites_strict": {m: bool(r >= P.BITE_STRICT) for m, r in ratios.items()},
           "win_frac": {m: P.win_frac(lives["true"], lives[m])
                        for m in ("permuted", "noise", "zero")},
           "arms_identical": {m: lives["true"] == lives[m] for m in ("permuted", "noise", "zero")},
           "secs": 0.0}
    rec["original_ladder_verdict"] = P.original_ladder_verdict(rec)
    return rec


# ---------------------------------------------------------------- 1. LES CONTRE-EXEMPLES CONSTRUITS
def test_s6_contre_exemple_construit_corps_suffisant_ablation_MORD():
    """REPONSE CONNUE : en corps SUFFISANT, une politique qui LIT s'effondre sous ablation.

    Enonce refute : "corps suffisant (body_gain > metab) => l'ablation est inerte". C'est vrai de
    l'INIT W=0 de `fit_policy` (qui ne quitte jamais son zero), FAUX de l'espace des politiques.
    W = identite -> la politique suit l'obs et prend le gain cognitif (net +1.0/tick) -> plafond
    300. Obs mise a 0 -> action CONSTANTE hors-corps -> 1 tick sur 4 paye -> net -0.5/tick -> mort
    vers 30. Ratio predit ~10, exige >= 6."""
    import statistics
    cell = _s6_cell(body_gain=1.2)
    W, b = _s6_reading_policy(cell["K"])
    intact = _s6_lives(W, b, "true", cell)
    able = _s6_lives(W, b, "zero", cell)
    mi, ma = statistics.median(intact), statistics.median(able)
    assert mi == float(cell["ticks"]), (
        "la politique lectrice devrait survivre au plafond en corps suffisant, mediane=%s" % mi)
    assert ma < 60, "l'ablation devrait effondrer la survie, mediane ablatee=%s" % ma
    assert mi / ma >= 6.0, "ratio %.2f -- l'ablation doit MORDRE dans ce regime" % (mi / ma)
    assert intact != able, "les deux bras ne doivent PAS etre identiques ici (l'obs est lue)"


def test_s6_le_barreau_zero_RATE_un_lecteur_dont_le_defaut_est_le_CORPS():
    """DEFAUT TROUVE EN RE-EXAMINANT LE RUNNER, ET CAUSE DU CHANGEMENT DE DV -- reponse connue.

    MEME politique lectrice, biais NUL. Obs mise a zero -> `W@0 + 0` = vecteur nul -> argmax = 0 =
    l'action CORPS -> le sujet survit au plafond. Le barreau `zero` lit donc ratio = 1.00 et conclut
    "inerte" sur une politique qui lit l'obs a chaque tick. Le barreau `permuted` (obs REELLE d'un
    autre tick : meme distribution, information detruite) l'attrape.

    Sur le plan complet, ce faux negatif frappe 5 des 60 points reels (`permuted` effondre 2.9x a
    7.1x pendant que `zero` annonce 1.00). C'est pour cela que DV_MODE vaut `permuted`."""
    import statistics
    P = _s6_probe()
    cell = _s6_cell(body_gain=1.2)
    W, b = _s6_reading_policy_body_default(cell["K"])
    mi = statistics.median(_s6_lives(W, b, "true", cell))
    mz = statistics.median(_s6_lives(W, b, "zero", cell))
    mp = statistics.median(_s6_lives(W, b, "permuted", cell))
    assert mi == 300.0, "la politique lit et survit au plafond : %s" % mi
    assert mz == 300.0 and P.bites(mi / mz) is False, (
        "le barreau `zero` DOIT rater ce lecteur (c'est le defaut demontre) : zero=%s" % mz)
    assert mp < 60 and P.bites(mi / mp) is True, (
        "le barreau `permuted` DOIT l'attraper : permuted=%s ratio=%.2f" % (mp, mi / mp))
    assert P.DV_MODE == "permuted", "le DV du runner doit etre le barreau qui ne rate pas ce cas"


def test_s6_contre_exemple_specificite_politique_constante_bras_IDENTIQUES():
    """Le pendant : la politique CORPS-SEUL (W=0) rend TOUS les bras identiques POINT PAR POINT.
    C'est le no-op litteral de S2-004 -- et ce que le CRN doit rendre visible."""
    P = _s6_probe()
    cell = _s6_cell(body_gain=1.2)
    W, b = P.body_only_policy(cell["K"])
    ref = _s6_lives(W, b, "true", cell)
    for m in ("permuted", "noise", "zero"):
        assert _s6_lives(W, b, m, cell) == ref, "bras %s different d'intact" % m


# ------------------------------------------------------------------------ 2. NO-OP EXACT (ANCRE)
def test_s6_sigma_zero_est_bit_identique_y_compris_quand_le_hill_climb_ACCEPTE():
    """SPECIFICITE, ET LA VERSION FORTE DU TEST.

    A sigma=0 le RNG d'init n'est pas consomme -> meme suite de candidates -> (W, b) EXACTEMENT
    egaux a ceux de `fit_policy`. Verifier cela UNIQUEMENT dans la cellule a corps suffisant ne
    prouverait presque rien : la boucle y n'accepte JAMAIS, donc W reste zeros des deux cotes quoi
    qu'il arrive au RNG. Le test porte donc AUSSI sur c1-P, ou `n_accepted > 0` : c'est la que
    l'egalite bit a bit contraint reellement la trajectoire du hill-climb."""
    import numpy as np
    from tools.cognitive_demand_world_probe import fit_policy
    P = _s6_probe()
    vu_accepte = False
    for body_gain in (1.2, 0.5):
        for seed in (0, 3):
            W0, b0 = fit_policy(body_gain, 2.0, "energy", 5, seed, iters=40, ticks=300)
            W1, b1, n_acc, best, init = P.fit_policy_sigma(0.0, body_gain, 2.0, "energy", 5, seed,
                                                           iters=40, ticks=300)
            assert np.array_equal(W0, W1) and np.array_equal(b0, b1), (
                "trajectoire divergente a body_gain=%s seed=%s" % (body_gain, seed))
            if body_gain > 1.0:
                assert n_acc == 0 and float(np.mean(np.abs(W1))) == 0.0
                assert init == best == 300.0, "l'init survit deja au plafond : %s" % init
            else:
                vu_accepte = vu_accepte or n_acc > 0
    assert vu_accepte, ("aucun seed n'a fait ACCEPTER le hill-climb : le test d'identite ne "
                        "couvrirait alors que la branche inerte")


def test_s6_sigma_zero_reproduit_l_ancre_S2_004():
    """ANCRE : |W| = 0.0000 EXACT, 300/300, TOUS les bras identiques, et le compteur qui NOMME la
    cause (n_accepted = 0 : |W|=0 est l'INIT, jamais un poids appris)."""
    P = _s6_probe()
    for seed in (0, 1):
        rec = P.run_seed("c1-N", 0.0, seed, iters=40, episodes=5, n_eval=12)
        assert rec["obs_weight"] == 0.0
        assert rec["n_accepted"] == 0
        assert rec["dv"]["true"] == 300.0
        assert all(rec["arms_identical"].values()), rec["arms_identical"]
        assert all(r == 1.0 for r in rec["ratios"].values())


# ----------------------------------------------------------------- 3. PLANCHER MESURE, PAS DEVINE
def test_s6_plancher_mesure_vaut_sa_forme_close():
    """REPONSE CONNUE en forme close. Corps seul : E += body_gain - metab a chaque tick.
    - corps INSUFFISANT (0.5) : E0=15, derive -0.5/tick -> E<=0 au tick 30 -> 30 EXACT, sans
      variance. C'est la valeur `PLANCHER_AVEUGLE` du probe, RETROUVEE par mesure, pas recopiee.
    - corps SUFFISANT (1.2) : derive +0.2/tick -> jamais de mort -> 300 (= le plafond).
    Un plancher DEVINE ou IMPORTE (classe E8) n'aurait pas cette propriete : celui-ci passe par le
    MEME mesureur, sur les MEMES graines de vie que les bras."""
    from tools.cognitive_demand_world_probe import PLANCHER_AVEUGLE
    P = _s6_probe()
    f_p, lives_p = P.measured_floor(_s6_cell(body_gain=0.5), seed=0, n_eval=24)
    assert f_p == 30.0 == PLANCHER_AVEUGLE
    assert set(lives_p) == {30}, "le plancher corps-seul est DETERMINISTE : %s" % sorted(set(lives_p))
    f_n, lives_n = P.measured_floor(_s6_cell(body_gain=1.2), seed=0, n_eval=24)
    assert f_n == 300.0 and set(lives_n) == {300}


def test_s6_le_plancher_du_depot_SOUS_ESTIME_la_meilleure_aveugle_de_1_tick():
    """DEFAUT MESURE DU PLANCHER DU DEPOT, trouve en ecrivant ce test (il a d'abord ECHOUE).

    J'affirmais que le plancher "privee de X seulement" est la MEILLEURE politique aveugle. Le scan
    des K actions constantes dit autre chose : en corps INSUFFISANT, une action cognitive constante
    a la MEME esperance de gain que le corps (cog_gain/(K-1) = 0.5 = body_gain) mais une VARIANCE
    non nulle, et la mediane du temps d'atteinte d'une marche bruitee est LEGEREMENT AU-DESSUS de
    celle d'une derive deterministe. Reponse connue mesuree (24 vies, seed 0) :
        a=0 (CORPS) -> 30 EXACT [30..30]  |  a=1 -> 31  a=2 -> 26  a=3 -> 29  a=4 -> 31
    `PLANCHER_AVEUGLE = 30.0` est donc la valeur de la politique CORPS, pas celle de la meilleure
    aveugle (31) : le plancher du depot SOUS-ESTIME de 1 tick (+3 %), ce qui rend la garde de
    degenerescence marginalement MOINS conservatrice que ce qu'elle annonce.

    IMMATERIEL DANS CE PLAN, et on le mesure au lieu de l'esperer : le bras intact vaut 300 dans
    les DEUX cellules, donc `med_i <= floor` se decide pareil a 30 ou a 31. En corps SUFFISANT
    l'ecart est nul (le corps EST la meilleure aveugle : 300 contre 26-31)."""
    from tools.cognitive_demand_world_probe import PLANCHER_AVEUGLE
    P = _s6_probe()
    scan_p = P.blind_floor_scan(_s6_cell(body_gain=0.5), seed=0)
    corps_p = P.measured_floor(_s6_cell(body_gain=0.5), seed=0)[0]
    assert corps_p == scan_p[P.BODY_ACTION] == 30.0 == PLANCHER_AVEUGLE
    assert max(scan_p.values()) == 31.0, scan_p
    assert max(scan_p.values()) - corps_p == 1.0, "l'ecart mesure est de +1 tick"
    scan_n = P.blind_floor_scan(_s6_cell(body_gain=1.2), seed=0)
    corps_n = P.measured_floor(_s6_cell(body_gain=1.2), seed=0)[0]
    assert corps_n == 300.0 and max(scan_n.values()) == corps_n, (
        "en corps suffisant le CORPS est la meilleure aveugle : %s" % scan_n)
    # ... et la consequence sur le verdict est NULLE ici, parce que le bras intact est a 300.
    a30 = P.aggregate([_s6_record(cell="c1-P", sigma=0.3, seed=s, intact=300.0, abl=30.0,
                                  floor=30.0, body_gain=0.5) for s in range(12)])
    a31 = P.aggregate([_s6_record(cell="c1-P", sigma=0.3, seed=s, intact=300.0, abl=30.0,
                                  floor=31.0, body_gain=0.5) for s in range(12)])
    assert a30["verdicts"]["permuted"]["verdict"] == a31["verdicts"]["permuted"]["verdict"]


def test_s6_plancher_au_plafond_bloque_le_NUL_pas_le_POSITIF():
    """Consequence LUE, pas supposee : en corps suffisant le plancher mesure EST le plafond (300),
    donc un ratio ~1 y est INDECIDABLE (INCONCLUSIVE_DEGENERATE) et non "X_DECOY". La meme garde ne
    doit PAS effacer un vrai effondrement. Injection a dose connue, cout de simulation nul."""
    P = _s6_probe()
    nul = P.aggregate([_s6_record(seed=s, intact=300.0, abl=300.0, floor=300.0) for s in range(12)])
    assert nul["verdicts"]["permuted"]["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert nul["verdicts"]["permuted"]["degenerate"] is True and nul["k_dv"] == 0
    pos = P.aggregate([_s6_record(seed=s, intact=300.0, abl=30.0, floor=300.0) for s in range(12)])
    assert pos["verdicts"]["permuted"]["verdict"] == "X_DEMANDED", "un POSITIF ne doit pas etre efface"
    assert pos["k_dv"] == 12 and pos["verdicts"]["permuted"]["censored"] is True


# ------------------------------------------------------ 4. L'INTERVENTION AGIT SUR L'ENTREE (Q1)
def test_s6_ablation_perturbe_l_entree_et_true_ne_la_touche_pas():
    P = _s6_probe()
    assert P.assert_intervention_perturbs_input() == {"permuted": True, "noise": True, "zero": True}


def test_s6_UN_SEUL_barreau_est_a_CRN_exact_et_on_le_MESURE():
    """DEFAUT MESURE, PAS SUPPOSE. La politique CORPS ignore l'obs -> meme duree de vie sous tous
    les barreaux -> toute difference d'ETAT du RandomState apres la vie est PUREMENT la
    consommation de tirages par l'ablation.
      * `zero`  ne tire RIEN                     -> etat identique -> apparie VIE par VIE ;
      * `permuted` tire 1 randint + K randn      -> etat different -> apparie au SEED seulement ;
      * `noise` tire K randn                     -> etat different -> idem.
    Le runner l'expose au lieu de promettre un CRN exact qu'il n'a pas sur son DV."""
    P = _s6_probe()
    crn = P.assert_crn_exactness()
    assert crn == {"permuted": False, "noise": False, "zero": True}, crn
    assert P.CRN_EXACT_MODE == "zero"


def test_s6_crn_les_bras_partagent_les_memes_graines_de_vie():
    """L'appariement se fait sur la VIE : `life_seeds` est deterministe et partage par tous les
    bras. Sinon la difference entre bras melangerait ablation et alea."""
    P = _s6_probe()
    a, b = P.life_seeds(4, 24), P.life_seeds(4, 24)
    assert a == b and len(a) == 24 and len(set(a)) == 24
    assert P.life_seeds(5, 24) != a, "des seeds differents doivent donner des vies differentes"


def test_s6_le_contrat_de_intervention_verified_est_AMBIGU_mais_la_borne_rattrape_ICI():
    """DETTE DE CONTRAT DANS `demand_marker`, et la NUANCE que ma premiere version ratait.

    `_degeneracy` bloque les bras identiques sauf si l'appelant passe `intervention_verified=True`,
    defini comme "l'appelant atteste que l'ablation perturbe bien l'ENTREE". Or le cas que sa PROPRE
    docstring nomme comme devant etre BLOQUE (S2-004 : politique constante car W gele) SATISFAIT
    cette attestation : l'entree EST perturbee, c'est la POLITIQUE qui ne la lit pas. Attester
    l'entree ne dit rien de la lecture -- le flag ne peut donc pas separer (a) de (b), qui est
    exactement ce qu'il pretend arbitrer.

    CE QUE J'AI AFFIRME DE TROP, ET QUE LA MESURE A CORRIGE : j'ai d'abord ecrit que le flag
    deverrouillerait le cas S2-004. FAUX dans NOTRE regime -- la garde de PLAFOND le rattrape
    independamment (les deux bras sont a 300 = ceiling). La dette est donc reelle mais NON
    ATTEIGNABLE ici, et c'est pour cela que ne pas passer le flag ne nous coute rien.

    Le contre-exemple ou elle MORD vraiment : des bras identiques LOIN des bornes declarees. Ce cas
    ne peut pas naitre dans ce monde-ci (une politique constante y survit 30 ou 300, jamais 100),
    mais `demand_marker` est un instrument TRANSVERSAL -- ailleurs, il est atteignable."""
    P = _s6_probe()
    from tools.demand_marker import ablation_verdict
    assert P.assert_intervention_perturbs_input()          # l'ENTREE est bien perturbee
    rec = P.run_seed("c1-N", 0.0, 0, iters=5, episodes=1, n_eval=12)
    assert rec["arms_identical"]["zero"] is True           # et les bras sont identiques
    lives = rec["lives"]
    assert ablation_verdict(lives["true"], lives["zero"], floor=300.0,
                            ceiling=300.0)["verdict"] == "INCONCLUSIVE_DEGENERATE"
    quand_meme = ablation_verdict(lives["true"], lives["zero"], ceiling=300.0,
                                  intervention_verified=True)
    assert quand_meme["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert "PLAFOND" in quand_meme["why"], (
        "ce n'est PAS le flag qui protege ici, c'est la garde de plafond : %s" % quand_meme["why"])
    # Le cas ou le flag deverrouille vraiment : bras identiques, loin du plancher ET du plafond.
    milieu = [100.0] * 12
    assert ablation_verdict(milieu, milieu, floor=30.0,
                            ceiling=300.0)["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert ablation_verdict(milieu, milieu, floor=30.0, ceiling=300.0,
                            intervention_verified=True)["verdict"] == "X_DECOY", (
        "la dette de contrat est reelle : attester l'ENTREE deverrouille un nul dont la cause peut "
        "etre une politique CONSTANTE -- simplement inatteignable dans ce monde-ci")


# ------------------------------------------------------------ 5. DOSE / LINEARITE / MONOTONIE
def test_s6_sigma_controle_lineairement_l_echelle_de_l_init():
    """PREDICTION : W0 = sigma * N(0,1) -> E|W0| = sigma * sqrt(2/pi). On identifie la nuisance en
    sigma=1 et on PREDIT en sigma=0.3 (facteur exactement 0.3), au lieu de lire une valeur absolue."""
    import numpy as np
    P = _s6_probe()
    ref = None
    for sigma in (1.0, 0.3, 0.1):
        W, b, _, _, _ = P.fit_policy_sigma(sigma, 1.2, 2.0, "energy", 5, 0, iters=0, ticks=300)
        m = float(np.mean(np.abs(W)))
        if ref is None:
            ref = m
            assert abs(m - np.sqrt(2 / np.pi)) < 0.25
        else:
            assert abs(m - sigma * ref) < 1e-12, "echelle non lineaire en sigma"
    W0, _, _, _, _ = P.fit_policy_sigma(0.0, 1.2, 2.0, "energy", 5, 0, iters=0, ticks=300)
    assert float(np.mean(np.abs(W0))) == 0.0


def test_s6_sigma_ne_change_PAS_la_politique_initiale_mais_son_echelle():
    """DEFAUT DU DESIGN, TROUVE EN L'IMPLEMENTANT -- epingle pour qu'il ne se relise plus mal.

    L'action est `argmax(W @ o + b)`, INVARIANTE par multiplication par un scalaire POSITIF : pour
    un meme seed, sigma=0.1, 0.3 et 1.0 donnent la MEME politique initiale (la meme application
    obs -> action), a l'echelle pres, donc le MEME init_score.

    Consequence pour la LECTURE de k(sigma) : le balayage de sigma n'est PAS un balayage de "a quel
    point l'init LIT l'obs" -- c'est un balayage du RAPPORT entre l'echelle de l'init et le pas du
    hill-climb (step=0.5), i.e. de la facilite avec laquelle la recherche EFFACE l'init. Seule
    discontinuite reelle : sigma=0 (init = politique corps, gelee) vs sigma>0. Lire k(0.1) vs
    k(1.0) comme une dose-reponse en "force de lecture" serait FAUX."""
    import numpy as np
    from tools.cognitive_demand_world_probe import _obs
    P = _s6_probe()
    scores, actions = [], []
    for sigma in (0.1, 0.3, 1.0):
        W, b, _, _, init = P.fit_policy_sigma(sigma, 1.2, 2.0, "energy", 5, 1, iters=0, ticks=300)
        scores.append(init)
        rng = np.random.RandomState(7)
        actions.append([int(np.argmax(W @ _obs(1 + rng.randint(4), 5, rng) + b)) for _ in range(60)])
    assert actions[0] == actions[1] == actions[2], "l'argmax doit etre invariant d'echelle"
    assert scores[0] == scores[1] == scores[2], (
        "init_score doit etre identique pour tout sigma>0 : %s" % scores)
    W0, b0, _, _, init0 = P.fit_policy_sigma(0.0, 1.2, 2.0, "energy", 5, 1, iters=0, ticks=300)
    assert init0 == 300.0 and init0 != scores[0]


def test_s6_compteur_de_morsure_reponses_connues_et_seuil_non_porteur():
    """Le seuil de morsure est celui de `demand_marker` (decoy_ceiling=1.3), borne STRICTE. Et le
    runner rapporte AUSSI k au seuil `collapse_factor`=1.5 : sur les 60 points reels, aucun ratio
    ne tombe dans la zone grise (1.3, 1.5), donc le choix du seuil ne porte AUCUNE conclusion."""
    P = _s6_probe()
    assert P.bites(1.0) is False and P.bites(1.30) is False
    assert P.bites(1.3001) is True and P.bites(10.0) is True
    assert P.bites(0.5) is False, "une ablation qui AMELIORE n'est pas une morsure"
    assert P.BITE == 1.3 and P.BITE_STRICT == 1.5
    recs = [_s6_record(seed=s, intact=300.0, abl=30.0, floor=30.0) for s in range(12)]
    agg = P.aggregate(recs)
    assert agg["k"]["permuted"] == 12 and agg["k_strict"]["permuted"] == 12


def test_s6_k_compte_par_seed_et_pas_par_vie():
    """k se compte PAR SEED. Melange connu : 3 seeds mordent, 9 non -> k=3, et `ablation_verdict`
    recoit n=12 (l'unite de replication), jamais 288 vies."""
    P = _s6_probe()
    recs = ([_s6_record(seed=s, intact=300.0, abl=30.0, floor=30.0) for s in range(3)] +
            [_s6_record(seed=s, intact=300.0, abl=300.0, floor=30.0) for s in range(3, 12)])
    agg = P.aggregate(recs)
    assert agg["k_dv"] == 3 and agg["n_seeds"] == 12
    assert agg["verdicts"]["permuted"]["n"] == 12, "unite de replication = le seed, jamais la vie"
    assert agg["median_ratio"]["permuted"] == 1.0


def test_s6_mediane_des_ratios_n_est_PAS_le_ratio_des_medianes():
    """DEFAUT TROUVE EN IMPLEMENTANT -- les deux nombres cohabitaient sous l'intitule "ratio".

    Dose connue : 6 seeds sur 12 mordent a 300/30, les 6 autres sont plats a 300/300.
      * mediane DES RATIOS par seed = (10 + 1)/2 = 5.5      -> ce qui fonde k
      * ratio DES MEDIANES          = 300 / 165 = 1.818...  -> ce que `ablation_verdict` tranche
    Ils different d'un facteur 3, et parce que le second est une mediane le verdict de CELLULE
    bascule exactement a 50 % de seeds mordants : k=5/12 reste sous 1.5, k=6/12 passe X_DEMANDED.
    C'est k, pas le verdict de cellule, qui est la grandeur robuste dans ce plan."""
    P = _s6_probe()
    recs = ([_s6_record(seed=s, intact=300.0, abl=30.0, floor=300.0) for s in range(6)] +
            [_s6_record(seed=s, intact=300.0, abl=300.0, floor=300.0) for s in range(6, 12)])
    agg = P.aggregate(recs)
    assert agg["k_dv"] == 6
    assert abs(agg["median_ratio"]["permuted"] - 5.5) < 1e-9
    assert abs(agg["verdicts"]["permuted"]["ratio"] - 300.0 / 165.0) < 1e-9
    assert agg["verdicts"]["permuted"]["verdict"] == "X_DEMANDED"
    assert agg["verdicts"]["permuted"]["censored"] is True, "positif CENSURE : ratio = borne INF"
    recs5 = ([_s6_record(seed=s, intact=300.0, abl=30.0, floor=300.0) for s in range(5)] +
             [_s6_record(seed=s, intact=300.0, abl=300.0, floor=300.0) for s in range(5, 12)])
    agg5 = P.aggregate(recs5)
    assert agg5["k_dv"] == 5 and agg5["verdicts"]["permuted"]["verdict"] != "X_DEMANDED"


def test_s6_le_verdict_du_PROTOCOLE_D_ORIGINE_est_reproduit_et_il_BASCULE():
    """Rend la comparaison avec S2-004 DIRECTE au lieu d'une re-lecture. `original_ladder_verdict`
    reproduit `ladder` du probe, y compris ses deux choix qui ne sont pas les notres (n = 24 VIES ;
    `floor=` seulement si body_gain<1.0). Reponses connues :
      * bras tous egaux (l'ancre sigma=0) -> INDETERMINE_DEGENERATE (la garde de 2026-09-02 mord ;
        c'est AVANT elle que ce cas se publiait "SURVIVAL_NEUTRAL") ;
      * bras ablate effondre en corps SUFFISANT -> SURVIVAL_SENSITIVE, alors meme que le corps
        suffit a survivre seul : c'est la bascule que S6 mesure ;
      * effondrement en corps INSUFFISANT -> SURVIVAL_SENSITIVE aussi, mais la c'est correct."""
    P = _s6_probe()
    plat = _s6_record(intact=300.0, abl=300.0, body_gain=1.2)
    assert plat["original_ladder_verdict"] == "INDETERMINE_DEGENERATE"
    mord = _s6_record(intact=300.0, abl=30.0, body_gain=1.2)
    assert mord["original_ladder_verdict"] == "SURVIVAL_SENSITIVE"
    vrai = _s6_record(intact=300.0, abl=30.0, body_gain=0.5, floor=30.0)
    assert vrai["original_ladder_verdict"] == "SURVIVAL_SENSITIVE"
    agg = P.aggregate([_s6_record(seed=s, intact=300.0, abl=30.0, body_gain=1.2)
                       for s in range(12)])
    assert agg["original_ladder_majority"] == "SURVIVAL_SENSITIVE"
    assert agg["original_ladder_tie"] is False


def test_s6_la_MAJORITE_du_probe_d_origine_n_est_pas_REPRODUCTIBLE_sur_une_egalite():
    """DEFAUT DU DEPOT, TROUVE PARCE QUE NOS DONNEES TOMBENT DESSUS (a consigner au registre).

    `cognitive_demand_world_probe.main` publie le verdict d'une cellule par
    `maj = max(set(verdicts), key=verdicts.count)`. Sur une EGALITE, c'est l'ordre d'iteration du
    `set` qui tranche -- et pour des CHAINES cet ordre depend de PYTHONHASHSEED. Le verdict PUBLIE
    d'une cellule depend donc du process qui l'a calcule.

    Ce n'est pas theorique : nos cellules c1-N a sigma=0.3 et sigma=1.0 rendent EXACTEMENT 6
    INDETERMINE_DEGENERATE contre 6 SURVIVAL_SENSITIVE. Mesure sur 8 valeurs de PYTHONHASHSEED :
    5 fois INDETERMINE_DEGENERATE, 3 fois SURVIVAL_SENSITIVE, pour les MEMES donnees.

    Notre agregation ne reproduit pas ce tirage : `_majority` a un ordre TOTAL (compte decroissant
    puis alphabetique) et `_is_tie` DRAPEAUTE l'egalite au lieu de la trancher en silence."""
    P = _s6_probe()
    egalite = ["INDETERMINE_DEGENERATE"] * 6 + ["SURVIVAL_SENSITIVE"] * 6
    assert P._is_tie(egalite) is True
    assert P._majority(egalite) == "INDETERMINE_DEGENERATE"
    assert P._majority(list(reversed(egalite))) == "INDETERMINE_DEGENERATE", (
        "la majorite ne doit dependre NI de l'ordre d'entree NI du hash des chaines")
    franche = ["INDETERMINE_DEGENERATE"] * 5 + ["SURVIVAL_SENSITIVE"] * 7
    assert P._is_tie(franche) is False and P._majority(franche) == "SURVIVAL_SENSITIVE"
    assert P._majority([]) is None and P._is_tie([]) is None, "aucun verdict sur une entree vide"
    agg = P.aggregate([_s6_record(seed=s, intact=300.0, abl=30.0, body_gain=1.2)
                       for s in range(6)]
                      + [_s6_record(seed=s, intact=300.0, abl=300.0, body_gain=1.2)
                         for s in range(6, 12)])
    assert agg["original_ladder_tie"] is True, (
        "6 SENSIBLE contre 6 DEGENERATE : l'egalite doit etre SIGNALEE, pas tranchee")


# ------------------------------------------------- 6. LE GATE : LES DEUX ISSUES SONT-ELLES LA ?
def test_s6_le_gate_refuse_de_conclure_si_le_CONTROLE_POSITIF_ne_mord_pas():
    """SANS CE GATE, k(c1-N) peut etre mesure sur un instrument qui ne peut rendre QUE 0 (E1/E2) et
    la table s'imprime quand meme. Trois reponses connues, par injection :
      * ancre plate + controle positif mordant  -> GO
      * controle positif INERTE                 -> NO-GO (meme si la cellule testee a l'air propre)
      * controle positif ABSENT du plan         -> NO-GO (l'absence n'est pas un succes)."""
    P = _s6_probe()
    ancre = P.aggregate([_s6_record(cell="c1-N", sigma=0.0, seed=s, intact=300.0, abl=300.0,
                                    floor=300.0, obs_weight=0.0, n_accepted=0)
                         for s in range(12)], expect_n=12)
    pos_ok = P.aggregate([_s6_record(cell="c1-P", sigma=0.3, seed=s, intact=300.0, abl=30.0,
                                     floor=30.0, body_gain=0.5) for s in range(12)], expect_n=12)
    pos_ko = P.aggregate([_s6_record(cell="c1-P", sigma=0.3, seed=s, intact=30.0, abl=30.0,
                                     floor=30.0, body_gain=0.5) for s in range(12)], expect_n=12)
    go, _ = P.admissibility([ancre, pos_ok])
    assert go is True
    go, lines = P.admissibility([ancre, pos_ko])
    assert go is False and any("NO-GO" in l for l in lines)
    go, _ = P.admissibility([ancre])
    assert go is False, "un controle positif ABSENT doit donner NO-GO, pas un silence"


def test_s6_le_gate_refuse_une_ancre_qui_a_appris():
    """L'autre moitie du gate : si l'ancre sigma=0 se met a mordre, ou si |W| n'est plus nul, ce
    n'est plus l'ancre de S2-004 et la comparaison n'a plus de reference."""
    P = _s6_probe()
    pos_ok = P.aggregate([_s6_record(cell="c1-P", sigma=0.3, seed=s, intact=300.0, abl=30.0,
                                     floor=30.0, body_gain=0.5) for s in range(12)], expect_n=12)
    ancre_ko = P.aggregate([_s6_record(cell="c1-N", sigma=0.0, seed=s, intact=300.0, abl=30.0,
                                       floor=300.0, obs_weight=0.5, n_accepted=3)
                            for s in range(12)], expect_n=12)
    go, lines = P.admissibility([ancre_ko, pos_ok])
    assert go is False and any("ANCRE" in l and "NO-GO" in l for l in lines)


def test_s6_un_plan_PARTIEL_est_drapeaute_et_ne_passe_pas_le_gate():
    """Un `--run` interrompu ne doit pas rendre un GO sur 4 seeds. `partial` est pose par
    comparaison a `expect_n`, et le gate le refuse."""
    P = _s6_probe()
    ancre = P.aggregate([_s6_record(cell="c1-N", sigma=0.0, seed=s, intact=300.0, abl=300.0,
                                    floor=300.0) for s in range(12)], expect_n=12)
    partiel = P.aggregate([_s6_record(cell="c1-P", sigma=0.3, seed=s, intact=300.0, abl=30.0,
                                      floor=30.0, body_gain=0.5) for s in range(4)], expect_n=12)
    assert partiel["partial"] is True and partiel["k_dv"] == 4
    go, _ = P.admissibility([ancre, partiel])
    assert go is False, "un plan partiel ne doit pas rendre GO"


# -------------------------------------------------------------- 7. PAS DE VERDICT SUR RIEN (biais)
def test_s6_agregation_sur_entree_vide_ne_fabrique_PAS_de_negatif():
    """Le defaut le plus frequent du depot : entree vide -> affirmation NEGATIVE de fond.
    `aggregate([])` doit rendre une ERREUR explicite, jamais k=0 / "NEUTRE"."""
    P = _s6_probe()
    out = P.aggregate([])
    assert "error" in out and "k_dv" not in out and "verdicts" not in out


def test_s6_agregation_refuse_de_melanger_cellules_sigmas_ou_PARAMETRES():
    """Une agregation qui melange (cellule, sigma) produirait un k(sigma) qui n'est le k de rien ;
    melanger des iters/n_eval differents comparerait deux protocoles sous un seul intitule."""
    import pytest
    P = _s6_probe()
    with pytest.raises(ValueError):
        P.aggregate([_s6_record(cell="c1-N", sigma=0.0), _s6_record(cell="c1-P", sigma=0.3)])
    with pytest.raises(ValueError):
        P.aggregate([_s6_record(sigma=0.1), _s6_record(sigma=0.3)])
    with pytest.raises(ValueError):
        P.aggregate([_s6_record(seed=0, iters=300), _s6_record(seed=1, iters=50)])


# ------------------------------------------------------------------------ 8. INFRA : cache et bail
def test_s6_la_cle_de_cache_porte_les_PARAMETRES():
    """DEFAUT TROUVE EN RE-EXAMINANT LE RUNNER. L'ancienne cle etait (cellule, sigma, seed) : un
    `--smoke --iters 50` (qui ecrit en force=True) empoisonnait silencieusement le point seed=0
    d'un `--run` a iters=300, sous le MEME nom de fichier. La cle porte desormais iters/episodes/
    n_eval, et deux protocoles ne peuvent plus se recouvrir."""
    P = _s6_probe()
    a = P.record_path("d", "c1-N", 0.3, 0, iters=300, episodes=5, n_eval=24)
    b = P.record_path("d", "c1-N", 0.3, 0, iters=50, episodes=5, n_eval=24)
    c = P.record_path("d", "c1-N", 0.3, 0, iters=300, episodes=5, n_eval=8)
    assert a != b != c and a != c


def test_s6_un_record_INCOMPATIBLE_est_refuse_au_lieu_d_etre_servi():
    """La ceinture apres les bretelles : meme si un fichier se retrouvait au bon chemin avec un
    contenu d'un autre protocole (schema anterieur, autre seed), `load_or_run` LEVE. Servir
    silencieusement un resultat obtenu sous d'autres parametres est la forme la plus discrete de
    contamination."""
    import json
    import os
    import tempfile
    import pytest
    P = _s6_probe()
    with tempfile.TemporaryDirectory() as d:
        p = P.record_path(d, "c1-N", 0.0, 0, iters=1, episodes=1, n_eval=2)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"schema": 1, "cell": "c1-N", "sigma": 0.0, "seed": 0,
                       "iters": 1, "episodes": 1, "n_eval": 2}, fh)
        with pytest.raises(ValueError):
            P.load_or_run(d, "c1-N", 0.0, 0, iters=1, episodes=1, n_eval=2)
        os.remove(p)


def test_s6_persistance_est_resumable_et_ne_recalcule_pas():
    import tempfile
    P = _s6_probe()
    with tempfile.TemporaryDirectory() as d:
        a = P.load_or_run(d, "c1-N", 0.0, 0, iters=1, episodes=1, n_eval=2)
        assert a["_from_cache"] is False
        b = P.load_or_run(d, "c1-N", 0.0, 0, iters=1, episodes=1, n_eval=2)
        assert b["_from_cache"] is True and b["dv"] == a["dv"] and b["lives"] == a["lives"]
        c = P.load_or_run(d, "c1-N", 0.0, 0, iters=1, episodes=1, n_eval=2, force=True)
        assert c["_from_cache"] is False and c["dv"] == a["dv"], "meme seed -> meme resultat"


def test_s6_aucun_monde_aucun_bail_kuzu():
    """Le runner est pur numpy : s'il chargeait le monde ou `tools.jobs`, il faudrait un bail
    exclusif et la mesure serait contaminable par une sonde concurrente."""
    import sys
    P = _s6_probe()
    assert P.assert_no_world() is True
    assert "kuzu" not in sys.modules


def test_s6_le_plan_est_borne_et_connu_d_avance():
    """Le cout se borne DANS le design : 5 cellules x 12 seeds = 60 points, pas un balayage ouvert."""
    P = _s6_probe()
    pts = P.plan()
    assert len(pts) == 60
    assert sorted({(c, s) for c, s, _ in pts}) == [("c1-N", 0.0), ("c1-N", 0.1), ("c1-N", 0.3),
                                                   ("c1-N", 1.0), ("c1-P", 0.3)]
