"""CALIBRATION des instruments d'EVO-011-PREVOL (colle-pret pour tests/sandbox/).

Quatre instruments y sont confrontes a une REPONSE CONNUE :

  * `verdict_evo011_prevol` -- la fonction de verdict. Ses QUATRE branches (NE PAIE PAS / LE LECTEUR
    PAIE / INDETERMINE / INDETERMINE-HARNAIS), le sous-cas nomme par le sceau (INDETERMINE-PLAFOND),
    et surtout les TROIS facons de fabriquer un NEGATIF : entree vide/nan/denominateur nul, cle de
    controles ABSENTE, et SOUS-PUISSANCE. Cette derniere est un defaut REEL trouve en revue : a n=1
    (un smoke !) la branche basse rendait « NE PAIE PAS » avec un `sign_p` egal a 1.0 PAR
    CONSTRUCTION. C'est la direction d'erreur constante du depot -- ici, elle est gelee par un test.

  * le CABLAGE -- contre-exemple a reponse connue, SANS MONDE : `W[4, o+8] == 8.0` chez le LECTEUR,
    `0.0` chez le TEMOIN, la saillance de decision separe les deux (1.000 vs 0.000), et le logit non
    cable du TEMOIN vaut 0 EXACTEMENT (donc `do_throw = logits[8] > 0` est FAUX : aucun biais n'est
    necessaire pour qu'il ne lance jamais).

  * le BALLAST -- `phenotype_hp_bonus` / `phenotype_energy_drain` derivent de `sum|W[0:5]|`
    (mamba_agent.py:47-50) et l'arete du lecteur EST en ligne 4. Sans compensation, cabler la lecture
    donne aussi +80 hp et +0.8 de drain. Les tests gelent (a) l'egalisation, (b) le fait que le
    ballast est BIT-IDENTIQUE sur les logits.

  * `_carry_matched` + `saturation_flags` -- les deux instruments ajoutes par la REVUE ADVERSARIALE.
    `_carry_matched` corrige un defaut de MON PROPRE controle : compare a age APPARIE, parce que le
    port cumule est downstream de la duree de vie (causalite INVERSEE -- mesure : le brut donnait
    0.832/0.846/0.661 et faisait echouer le controle sur un artefact de mortalite).
    `saturation_flags` dit qu'une DV secondaire est AU PLAFOND au lieu de laisser lire son egalite
    entre bras comme une absence d'effet.

Les helpers sont prefixes `_e11_` (collision de noms = 8 definitions invisibles au cliquet, cf.
CLAUDE.md) et les imports sont DANS les corps (aucun monde n'est construit a l'import).
"""
import os

import numpy as np
import pytest



# --------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------
def _e11_rows(ratios, den=10.0, fails=None, brouille=None):
    """Lignes APPARIEES synthetiques : un ratio LECTEUR/TEMOIN impose par seed (dose CONNUE)."""
    rows = []
    for i, r in enumerate(ratios):
        b = den if brouille is None else den * float(brouille[i])
        rows.append({"seed": i, "age_TEMOIN": den, "age_LECTEUR": den * float(r), "age_BROUILLE": b,
                     "control_failures": list(fails or [])})
    return rows


def _e11_obs(n=16, seed=0):
    """Observations synthetiques plausibles (dn,ds,de,dw dans [0,0.9], le reste petit). PUR."""
    rng = np.random.default_rng(seed)
    obs = rng.normal(0.0, 0.2, size=(n, 59)).astype(np.float32)
    obs[:, 0:4] = rng.integers(0, 10, size=(n, 4)) / 10.0
    return obs


def _e11_res(**over):
    """Un `res` minimal pour `saturation_flags` : trois bras identiques, surchargeables par bras."""
    from tools.evo_runs.evo011_preflight import ARMS
    base = dict(apex0=10, apex_end=0, big_kills=6, leurre_hits=5, riposte_hp=100.0,
                hp_start=1320.0, n=24, died_energy=24, died_hp=0)
    res = {a: dict(base) for a in ARMS}
    for arm, patch in over.items():
        res[arm].update(patch)
    return res


# ==================================================================================================
# `verdict_evo011_prevol` -- les 4 branches + les 3 degenerescences
# ==================================================================================================
def test_e11_verdict_branch_ne_paie_pas():
    """BRANCHE 1 -- r <= 1.10 : non-paiement, QUEL QUE SOIT sign_p (regle_de_lecture_continue)."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol
    v = verdict_evo011_prevol(_e11_rows([1.05] * 12))          # 12/12 favorables -> sign_p = 0.00049
    assert v["verdict"] == "NE PAIE PAS", v
    assert v["r"] == pytest.approx(1.05) and v["sign_p"] < 0.001, v
    v0 = verdict_evo011_prevol(_e11_rows([0.5] * 12))
    assert v0["verdict"] == "NE PAIE PAS", v0


def test_e11_verdict_branch_le_lecteur_paie_et_les_3_sous_lectures():
    """BRANCHE 2 -- r >= 1.25 ET sign_p < 0.05, puis LECTEUR vs BROUILLE aux MEMES seuils."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol
    v = verdict_evo011_prevol(_e11_rows([1.5] * 12, brouille=[1.0] * 12))
    assert v["verdict"] == "LE LECTEUR PAIE" and v["sign_p"] < 0.05, v
    assert v["discrimination"] == "DISCRIMINATION DE TYPE", v   # 1.5 / 1.0 = 1.5 >= 1.25
    v2 = verdict_evo011_prevol(_e11_rows([1.5] * 12, brouille=[1.5] * 12))
    assert v2["discrimination"] == "LE LANCER SEUL (type indifferent)", v2   # ratio 1.0 <= 1.10
    v3 = verdict_evo011_prevol(_e11_rows([1.5] * 12, brouille=[1.30] * 12))
    assert v3["discrimination"] == "INDETERMINE-DISCRIMINATION", v3          # 1.1538 dans la bande


def test_e11_verdict_branch_indetermine_les_deux_trous():
    """BRANCHE 3 -- les DEUX facons de tomber entre les branches (E11 occ.3 : le trou du milieu)."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol
    v = verdict_evo011_prevol(_e11_rows([1.18] * 12))                       # 1.10 < r < 1.25
    assert v["verdict"] == "INDETERMINE", v
    rows = _e11_rows([3.0, 0.9] * 6)                                        # r=1.95 mais sign_p=1.0
    v2 = verdict_evo011_prevol(rows)
    assert v2["verdict"] == "INDETERMINE" and v2["sign_p"] >= 0.05, v2


def test_e11_verdict_branch_harnais_prime_sur_la_dv():
    """BRANCHE 4 -- un controle qui echoue rend un verdict sur l'INSTRUMENT, jamais sur le monde.

    ⚠️ Le cas qui compte : les ages disent « ne paie pas » ET un controle a echoue. L'instrument doit
    rendre INDETERMINE-HARNAIS -- sinon un defaut de harnais se PUBLIE comme un resultat negatif."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol
    v = verdict_evo011_prevol(_e11_rows([1.0] * 12, fails=["(i) in situ TEMOIN throws=3 != 0"]))
    assert v["verdict"] == "INDETERMINE-HARNAIS", v
    assert "throws=3" in " ".join(v["raisons"]), v
    v2 = verdict_evo011_prevol(_e11_rows([1.0] * 12, fails=["(v) censure LECTEUR = 80% > 50%"]))
    assert v2["verdict"] == "INDETERMINE-PLAFOND", v2       # sous-cas NOMME par le sceau


def test_e11_verdict_degenere_ne_fabrique_jamais_un_negatif():
    """DEGENERESCENCE 1 (le defaut STRUCTUREL du depot) : entree vide / nan / denominateur nul."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol
    for rows in ([], None):
        v = verdict_evo011_prevol(rows)
        assert v["verdict"] == "INDETERMINE-HARNAIS", (rows, v)
        assert v["verdict"] != "NE PAIE PAS"
    nan_rows = _e11_rows([1.0] * 12)
    nan_rows[1]["age_LECTEUR"] = float("nan")
    assert verdict_evo011_prevol(nan_rows)["verdict"] == "INDETERMINE-HARNAIS"
    zero_rows = _e11_rows([1.0] * 12)
    zero_rows[2]["age_TEMOIN"] = 0.0                        # extinction totale du temoin
    assert verdict_evo011_prevol(zero_rows)["verdict"] == "INDETERMINE-HARNAIS"
    miss = _e11_rows([1.0] * 12)
    del miss[3]["age_LECTEUR"]                              # cle de DV absente
    assert verdict_evo011_prevol(miss)["verdict"] == "INDETERMINE-HARNAIS"
    txt = _e11_rows([1.0] * 12)
    txt[4]["age_TEMOIN"] = "n/a"                            # sentinelle textuelle d'un run rate
    assert verdict_evo011_prevol(txt)["verdict"] == "INDETERMINE-HARNAIS"
    # SPECIFICITE (calibree, pas supposee) : une chaine qui PARSE n'est pas une donnee manquante --
    # un aller-retour JSON reste lisible, et le ratio garde sa valeur exacte.
    num = _e11_rows([1.05] * 12)
    num[4]["age_TEMOIN"], num[4]["age_LECTEUR"] = "10.0", "10.5"
    v = verdict_evo011_prevol(num)
    assert v["verdict"] == "NE PAIE PAS" and v["r"] == pytest.approx(1.05), v


def test_e11_verdict_controles_ABSENTS_ne_valent_pas_controles_PASSES():
    """DEGENERESCENCE 2 (defaut REEL, trouve en revue) : `rows[i]` sans cle `control_failures`.

    L'ancien code faisait `r.get("control_failures") or []` : une ligne MUETTE etait donc lue comme
    une ligne PROPRE, et un run dont les controles n'ont jamais tourne pouvait rendre « NE PAIE PAS ».
    « Pas de rapport d'echec » n'est pas « rapport sans echec »."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol
    rows = _e11_rows([1.0] * 12)
    del rows[5]["control_failures"]
    v = verdict_evo011_prevol(rows)
    assert v["verdict"] == "INDETERMINE-HARNAIS", v
    assert "ABSENTE" in " ".join(v["raisons"]), v
    rows2 = _e11_rows([1.0] * 12)
    rows2[6]["control_failures"] = None                     # explicitement nul != liste vide
    assert verdict_evo011_prevol(rows2)["verdict"] == "INDETERMINE-HARNAIS"
    rows3 = _e11_rows([1.0] * 12)
    rows3[7]["control_failures"] = "aucun"                  # str : iterable mais pas une liste
    assert verdict_evo011_prevol(rows3)["verdict"] == "INDETERMINE-HARNAIS"


def test_e11_verdict_refuse_de_conclure_SOUS_PUISSANCE():
    """DEGENERESCENCE 3 (defaut REEL, trouve en revue) : le sceau dit 12 seeds, le smoke en fait 1.

    A n=1, `sign_p` vaut 1.0 PAR CONSTRUCTION -> la branche haute est inatteignable et la branche
    basse est la seule qui puisse tomber : un smoke a r=1.05 aurait imprime « NE PAIE PAS » et cette
    phrase serait un negatif FABRIQUE PAR LA TAILLE D'ECHANTILLON. Reponse connue, calculee a la
    main : les MEMES lignes rendent le verdict de fond a n=12 et le refus a n<12."""
    from tools.evo_runs.evo011_preflight import verdict_evo011_prevol, SEALED_SEEDS
    assert SEALED_SEEDS == 12
    for n in (1, 3, 11):
        v = verdict_evo011_prevol(_e11_rows([1.05] * n))
        assert v["verdict"] == "INDETERMINE-HARNAIS", (n, v)
        assert "SOUS-PUISSANCE" in " ".join(v["raisons"]), (n, v)
    assert verdict_evo011_prevol(_e11_rows([1.05] * 12))["verdict"] == "NE PAIE PAS"
    # ... et la garde est DESARMABLE explicitement (extension scellee a 24, ou test de branche)
    assert verdict_evo011_prevol(_e11_rows([1.05] * 3), n_required=3)["verdict"] == "NE PAIE PAS"


def test_e11_sign_p_repond_a_une_valeur_connue():
    """Le test des signes est la STATISTIQUE du sceau : reponse analytique connue."""
    from tools.evo_runs.evo011_preflight import _sign_p
    assert _sign_p(12, 12) == pytest.approx(2 * (1 / 4096))
    assert _sign_p(6, 12) == pytest.approx(1.0)
    assert _sign_p(0, 0) == 1.0                             # n=0 -> aucune preuve, pas une preuve nulle


# ==================================================================================================
# CABLAGE -- contre-exemple a reponse connue, SANS MONDE
# ==================================================================================================
def test_e11_arete_du_lecteur_est_exactement_celle_du_sceau():
    """(ii) `W[4, o+8] == 8.0` EXACT chez LECTEUR/BROUILLE, `== 0.0` chez le TEMOIN."""
    from tools.evo_runs.evo011_preflight import build_genome, OUT0, THROW_IDX, TYPE_COL, READER_W
    gl, gt, gb = build_genome("LECTEUR"), build_genome("TEMOIN"), build_genome("BROUILLE")
    assert float(gl.W[TYPE_COL, OUT0 + THROW_IDX]) == READER_W == 8.0
    assert float(gt.W[TYPE_COL, OUT0 + THROW_IDX]) == 0.0
    assert np.array_equal(gl.W, gb.W), "LECTEUR et BROUILLE doivent etre BIT-IDENTIQUES (le brouillage "
    assert not np.array_equal(gl.W, gt.W)                   # ... est dans le MONDE, pas le genome)
    assert float(gl.W[TYPE_COL, TYPE_COL]) == 10.0 == float(gt.W[TYPE_COL, TYPE_COL])  # reflexe partout


def test_e11_saillance_de_decision_separe_lecteur_et_temoin_sans_monde():
    """CONTROLE POSITIF + PLANCHER de la saillance, avec l'operateur EXACT du monde (bascule du SIGNE
    de logits[8]) mais sans monde : LECTEUR ~1.000, TEMOIN 0.000."""
    from tools.evo_runs.evo011_preflight import build_genome, decision_flip_rate_pure
    obs = _e11_obs(24, seed=7)
    on = decision_flip_rate_pure(build_genome("LECTEUR"), obs)
    floor = decision_flip_rate_pure(build_genome("TEMOIN"), obs)
    assert on > 0.99, f"le lecteur cable doit basculer a chaque fois : {on:.3f}"
    assert floor == 0.0, f"le temoin ne peut RIEN basculer : {floor:.3f}"


def test_e11_specificite_de_canal_le_lecteur_ne_lit_QUE_obs4():
    """SPECIFICITE : perturber un canal SANS RAPPORT ne bascule pas la decision de lancer."""
    from tools.evo_runs.evo011_preflight import build_genome, decision_flip_rate_pure
    obs = _e11_obs(24, seed=7)
    off = decision_flip_rate_pure(build_genome("LECTEUR"), obs, channel=7)
    assert off == 0.0, f"canal 7 (pheromone) : aucune bascule attendue, mesure {off:.3f}"


def test_e11_le_temoin_a_un_logit_de_lancer_NUL_EXACT():
    """La brique du controle (i) : `do_throw = logits[8] > 0` est FAUX pour le temoin par ARITHMETIQUE
    (activation tanh, seuils nuls, colonne du logit vide) -> `throws == 0` sans aucun biais ajoute."""
    from tools.evo_runs.evo011_preflight import build_genome, THROW_IDX
    from src.seed_ai.rl_evolution import recurrent_forward
    g = build_genome("TEMOIN")
    H = np.zeros((1, g.num_nodes), dtype=np.float32)
    for row in _e11_obs(8, seed=3):
        preds, H = recurrent_forward(g, row.reshape(1, -1), H,
                                     np.zeros((1, 5, g.num_nodes), np.float32),
                                     np.zeros((1, g.num_nodes), np.float32))[:2]
        assert float(preds[0, THROW_IDX]) == 0.0            # EXACT, pas « proche de 0 »


def test_e11_le_lecteur_suit_le_SIGNE_du_type_apex():
    """PREDICTION (dose imposee) : depuis un etat frais, logits[8] = delta * tanh(8*obs4) avec
    delta = sigmoid(diagonale reflexe) -> lance sur Mammouth(+1) et Ours(+0.5), ne lance PAS sur
    Leurre(-1) ni hors adjacence (0.0). La forme close vaut mieux que le signe seul : elle attrape
    aussi une diagonale reflexe qui aurait bouge."""
    from tools.evo_runs.evo011_preflight import build_genome, THROW_IDX, REFLEX_DIAG, READER_W
    from src.seed_ai.rl_evolution import recurrent_forward
    delta = 1.0 / (1.0 + np.exp(-REFLEX_DIAG))
    g = build_genome("LECTEUR")
    for val, expect in ((1.0, True), (0.5, True), (-1.0, False), (0.0, False)):
        row = np.zeros((1, 59), dtype=np.float32)
        row[0, 4] = val
        preds = recurrent_forward(g, row, np.zeros((1, g.num_nodes), np.float32),
                                  np.zeros((1, 5, g.num_nodes), np.float32),
                                  np.zeros((1, g.num_nodes), np.float32))[0]
        got = float(preds[0, THROW_IDX])
        assert (got > 0.0) is expect, f"obs4={val} -> logits[8]={got:.4f}"
        assert got == pytest.approx(delta * np.tanh(READER_W * val), abs=1e-5)


# ==================================================================================================
# BALLAST -- le defaut trouve EN IMPLEMENTANT, gele en test
# ==================================================================================================
def test_e11_sans_ballast_l_arete_change_AUSSI_le_phenotype():
    """⚠️ DEFAUT MESURE : `hp_bonus` et `energy_drain` derivent de `sum|W[0:5]|` et l'arete de lecture
    est en LIGNE 4. Lecture litterale du sceau -> le LECTEUR gagne +80 hp et +0.8 de drain EN PLUS de
    la lecture. Reponse connue, calculee a la main. Verifiee IN SITU par le smoke `--no-ballast` :
    phenotypes (1140, 50, 17.4) contre (1220, 50, 18.2), et l'empreinte de monde diverge."""
    from tools.evo_runs.evo011_preflight import build_genome, phenotype_of
    pl = phenotype_of(build_genome("LECTEUR"))
    pt_no = phenotype_of(build_genome("TEMOIN", ballast=False))
    assert pl["hp_bonus"] - pt_no["hp_bonus"] == pytest.approx(80.0)      # 8.0 * 10
    assert pl["energy_drain"] - pt_no["energy_drain"] == pytest.approx(0.8)
    pt = phenotype_of(build_genome("TEMOIN", ballast=True))
    assert pt == pl, f"le ballast doit EGALISER les phenotypes : {pt} vs {pl}"


def test_e11_phenotype_of_est_la_MEME_formule_que_le_monde():
    """SPECIFICITE de l'etalon : `phenotype_of` doit coincider avec `MambaAgent.update_phenotype`
    -- sinon le controle (ii-bis) comparerait deux grandeurs qui portent le meme nom (classe E17)."""
    from tools.evo_runs.evo011_preflight import build_genome, phenotype_of
    from src.agents.mamba_agent import MambaAgent
    for arm, bal in (("LECTEUR", True), ("TEMOIN", True), ("TEMOIN", False)):
        g = build_genome(arm, ballast=bal)
        a = MambaAgent()
        a.from_genome(g)
        p = phenotype_of(g)
        assert (p["hp_bonus"], p["inv_capacity"], p["energy_drain"]) == pytest.approx(
            (a.phenotype_hp_bonus, a.phenotype_inv_capacity, a.phenotype_energy_drain))


def test_e11_le_ballast_est_bit_identique_sur_les_sorties():
    """SPECIFICITE du correctif : le noeud de ballast est CACHE et n'a aucune arete sortante, donc sa
    colonne n'est lue par personne. no-op EXACT sur les logits (sinon le correctif serait une 2e
    intervention non scellee)."""
    from tools.evo_runs.evo011_preflight import build_genome, BALLAST_NODE, N_IN, N_OUT, N_NODES
    from src.seed_ai.rl_evolution import recurrent_forward
    g_with, g_without = build_genome("TEMOIN", ballast=True), build_genome("TEMOIN", ballast=False)
    assert N_IN <= BALLAST_NODE < N_NODES - N_OUT, "le ballast DOIT etre un noeud cache"
    W = g_with.W.copy()
    np.fill_diagonal(W, 0.0)
    assert float(np.abs(W[BALLAST_NODE, :]).sum()) == 0.0, "aucune arete SORTANTE -> inerte"
    Ha = np.zeros((1, N_NODES), np.float32); Hb = np.zeros((1, N_NODES), np.float32)
    z3 = np.zeros((1, 5, N_NODES), np.float32); z1 = np.zeros((1, N_NODES), np.float32)
    for row in _e11_obs(8, seed=11):
        pa, Ha = recurrent_forward(g_with, row.reshape(1, -1), Ha, z3, z1)[:2]
        pb, Hb = recurrent_forward(g_without, row.reshape(1, -1), Hb, z3, z1)[:2]
        assert np.array_equal(pa, pb), "le ballast doit etre BIT-IDENTIQUE sur les logits"


# ==================================================================================================
# GEL DE LA PLASTICITE -- la garde de la garde (aucun monde construit)
# ==================================================================================================
def test_e11_le_gel_neutralise_la_plasticite_intra_vie_et_peut_etre_desarme():
    """⚠️ DEFAUT MESURE, et le plus grave : `Biosphere3D.step` appelle
    `batch_model.compute_policy_gradient(...)` a chaque tick (world_1_stoneage.py:1734), qui ecrit
    `genome.W = clip(W + dW, -5, +5)` (mamba_agent.py:913-915). Un genome CABLE A LA MAIN n'est donc
    PAS fixe dans ce monde : mesure sur `--no-freeze`, l'arete du lecteur tombe de 8.0 a **5.0** et le
    genome derive de 11 a 15 en norme max, dans LES TROIS bras.

    PUR : la classe est construite mais AUCUN monde ne l'est (le parent est stubbe)."""
    from unittest.mock import patch
    from tools.evo_runs.evo011_preflight import _world_class
    from src.worlds.world_1_stoneage import Biosphere3D

    class _Sentinel:
        def compute_policy_gradient(self, *a, **k):
            raise AssertionError("plasticite NON gelee : le genome cable serait ecrase")

    cls = _world_class()
    for freeze, doit_lever in ((True, False), (False, True)):
        env = object.__new__(cls)                       # pas de __init__ -> aucun monde
        env.freeze = freeze
        with patch.object(Biosphere3D, "_get_batch_model", lambda self, models: _Sentinel()):
            bm = cls._get_batch_model(env, [])
        if doit_lever:
            with pytest.raises(AssertionError):
                bm.compute_policy_gradient([], [])      # CONTRE-EXEMPLE : la garde peut echouer
        else:
            assert bm.compute_policy_gradient([], []) is None


# ==================================================================================================
# LES DEUX INSTRUMENTS AJOUTES PAR LA REVUE ADVERSARIALE
# ==================================================================================================
def test_e11_carry_matched_neutralise_la_CAUSALITE_INVERSEE():
    """⚠️ DEFAUT DE MON PROPRE CONTROLE, trouve en le faisant echouer. Le port cumule d'un bras est
    DOWNSTREAM de sa duree de vie (l'epsilon-greedy `force_grab` accumule avec l'age) : le comparer
    brut entre bras teste la DV avec elle-meme. Mesure sur le smoke : brut 0.832 / 0.846 / 0.661 ->
    mon controle (vii) ECHOUAIT sur un artefact de mortalite ; a age apparie (fenetre 1-5) :
    0.583 / 0.542 / 0.533, n=120 par bras. Reponse connue, calculee a la main ci-dessous."""
    from tools.evo_runs.evo011_preflight import _carry_matched
    by_age = {1: [10.0, 10], 2: [20.0, 10], 9: [900.0, 10]}     # le vieux porte 90, le jeune 1-2
    got, n = _carry_matched(by_age, window=(1, 5))
    assert (got, n) == (pytest.approx(1.5), 20), (got, n)       # (10+20)/(10+10)
    biaise = sum(v[0] for v in by_age.values()) / sum(v[1] for v in by_age.values())
    assert biaise == pytest.approx(31.0)                        # 20x l'ecart -- le brut MENT
    assert _carry_matched({}, window=(1, 5))[1] == 0            # vide -> n=0, PAS une moyenne de 0
    assert np.isnan(_carry_matched({}, window=(1, 5))[0])
    assert _carry_matched({9: [900.0, 10]}, window=(1, 5))[1] == 0   # hors fenetre -> non evaluable


def test_e11_saturation_dit_le_PLAFOND_au_lieu_de_le_laisser_lire_comme_un_nul():
    """⚠️ MESURE : `big_kills` 6/6/6 et `leurre_hits` 5/5/5 IDENTIQUES dans les trois bras alors que
    la DV primaire varie de 10.0 a 19.0 -- parce que la population d'apex est EPUISEE partout
    (11 -> 1). Une egalite au plafond n'est pas une absence d'effet. Le drapeau le DIT ; il ne bloque
    pas (la DV primaire est l'age, pas ces compteurs). Contre-exemple : ressource NON epuisee."""
    from tools.evo_runs.evo011_preflight import saturation_flags
    plein = saturation_flags(_e11_res(TEMOIN={"apex_end": 1}, LECTEUR={"apex_end": 1},
                                      BROUILLE={"apex_end": 1}))
    assert any("PLAFOND" in f for f in plein), plein
    libre = saturation_flags(_e11_res(TEMOIN={"apex_end": 8}, LECTEUR={"apex_end": 7},
                                      BROUILLE={"apex_end": 9}))
    assert not any("PLAFOND" in f for f in libre), libre      # CONTRE-EXEMPLE : le drapeau peut se taire
    vide = saturation_flags(_e11_res(TEMOIN={"apex0": 0}, LECTEUR={"apex0": 0},
                                     BROUILLE={"apex0": 0}))      # 0 apex au depart : rien a epuiser
    assert not any("PLAFOND" in f for f in vide), vide            # ... et surtout pas de 0/0


def test_e11_saturation_dit_que_le_MAILLON_SCELLE_est_inerte():
    """⚠️ MESURE : le sceau nomme la chaine « ... -> melee SANS riposte -> survie ». Or la diagonale
    reflexe +10 qu'il impose porte `phenotype_hp_bonus` a 1220 -> hp 1320, contre une riposte de 50.
    Mesure sur le smoke : 450-980 hp de riposte encaisses par bras (23-41/agent, 3.1 % de hp), et
    **24/24 morts par ENERGIE, 0 par hp**, dans les trois bras. Le dernier maillon ne peut pas porter
    l'effet ; il faut le DIRE dans le record. Contre-exemple : une riposte qui mord vraiment."""
    from tools.evo_runs.evo011_preflight import saturation_flags
    inerte = saturation_flags(_e11_res())                          # 100 hp encaisses / 24 agents
    assert any("MAILLON FAIBLE" in f for f in inerte), inerte
    mordant = saturation_flags(_e11_res(TEMOIN={"riposte_hp": 24 * 500.0},
                                        LECTEUR={"riposte_hp": 24 * 500.0},
                                        BROUILLE={"riposte_hp": 24 * 500.0}))
    assert not any("MAILLON FAIBLE" in f for f in mordant), mordant   # CONTRE-EXEMPLE


def test_e11_ratio_stats_refuse_les_entrees_non_numeriques():
    """`_ratio_stats` est la brique de la DV : une entree None/str doit REFUSER, pas lever ni deviner."""
    from tools.evo_runs.evo011_preflight import _ratio_stats
    ok, r, p = _ratio_stats([(12.0, 10.0), (11.0, 10.0)])
    assert ok is not None and r == pytest.approx(1.15) and p == pytest.approx(0.5)
    for bad in ([(None, 10.0)], [("12", "dix")], [(12.0, 0.0)], [(float("inf"), 10.0)]):
        assert _ratio_stats(bad)[0] is None, bad
    # ex aequo ECARTES du test des signes (convention `tools/substrate_ab.py`), pas de la mediane
    ratios, r2, p2 = _ratio_stats([(10.0, 10.0)] * 6 + [(12.0, 10.0)] * 6)
    assert r2 == pytest.approx(1.1) and p2 == pytest.approx(2 / 64)


# ==================================================================================================
# monde (ne tourne QUE sous bail, hors suite normale)
# ==================================================================================================
@pytest.mark.skipif(not os.environ.get("EVO011_WORLD_TESTS"), reason="construit un monde : exige le bail kuzu")
def test_e11_instrument_calibre_du_depot_confirme_la_version_pure():
    """Le sceau exige `measure_decision_saliency` (instrument CALIBRE) : sa reponse doit coincider avec
    la version pure ci-dessus -- sinon l'une des deux ment."""
    from tools.evo_runs.evo011_preflight import build_genome, TYPE_COL, THROW_IDX
    from tools.jobs.run import hold
    with hold("kuzu", owner="evo011-calibration", ttl_s=600):
        import tools.evo_cognitive_objective as M
        on = M.measure_decision_saliency(build_genome("LECTEUR"), seed=11_000, channel=TYPE_COL,
                                         out_idx=THROW_IDX, num_agents=6, ticks=20)
        floor = M.measure_decision_saliency(build_genome("TEMOIN"), seed=11_000, channel=TYPE_COL,
                                            out_idx=THROW_IDX, num_agents=6, ticks=20)
    assert on > 0.5 and floor < 0.05, (on, floor)


# ==================================================================================================
# REGLE -bis (2026-09-07) : le controle (i) BROUILLE etait une bande FIXE sur une proportion par seed,
# appliquee a une famille de 24 cellules sans controle du taux de fausse alarme. Les trois proprietes
# qui suivent sont EXIGEES par le sceau -bis -- dont la troisieme, sans laquelle le correctif serait
# un controle qui ne peut plus echouer (classe E1), c.-a-d. pire que le defaut qu'il repare.
# ==================================================================================================

def _p_hors_bande(n, lo=0.25, hi=0.75):
    """P(la proportion observee sorte de l'ANCIENNE bande) sous un brouillage PARFAIT (p=0.5)."""
    import math
    return sum(math.comb(n, k) for k in range(n + 1) if not (lo < k / n < hi)) / 2 ** n


# n REELLEMENT observes au premier run (results/evo011_preflight.json, 12 seeds) -- pas des n supposes.
_N_MOINS = [26, 23, 25, 20, 26, 27, 22, 31, 25, 25, 26, 20]
_N_PLUS = [24, 31, 40, 38, 35, 27, 45, 38, 37, 56, 39, 33]


def test_e11bis_l_ANCIEN_controle_echouait_une_fois_sur_cinq_sur_un_harnais_PARFAIT():
    """RÉPONSE CONNUE, calculée en forme close : c'est le MOTIF du -bis, et il se mesure sans run.
    Sous un brouillage parfait, la probabilité qu'AU MOINS une des 24 cellules sorte de la bande vaut
    0.216. Un contrôle qui rejette un harnais correct une fois sur cinq ne mesure pas le harnais."""
    aucune = 1.0
    for n in _N_MOINS + _N_PLUS:
        aucune *= (1 - _p_hors_bande(n))
    assert 0.20 < 1 - aucune < 0.23, f"taux de fausse alarme mesuré = {1 - aucune:.3f}"


def test_e11bis_le_NOUVEAU_controle_tient_le_FWER_a_5_pourcent():
    """Le correctif, sur les MÊMES n : Bonferroni sur la famille scellée borne la fausse alarme à 5 %.
    Vérifié en forme close, cellule par cellule, contre le seuil réellement codé."""
    import math
    from tools.evo_runs.evo011_preflight import ALPHA_CELL, FAMILY_CELLS, _sign_p

    assert FAMILY_CELLS == 24 and abs(ALPHA_CELL - 0.05 / 24) < 1e-12
    aucune = 1.0
    for n in _N_MOINS + _N_PLUS:
        rejet = sum(math.comb(n, k) for k in range(n + 1) if _sign_p(k, n) < ALPHA_CELL) / 2 ** n
        aucune *= (1 - rejet)
    assert 1 - aucune <= 0.05, f"FWER = {1 - aucune:.4f} > 0.05"


def test_e11bis_le_controle_SAIT_ENCORE_ECHOUER_sur_un_brouilleur_CASSE():
    """BRANCHE NÉGATIVE, exigée par le sceau. Un correctif qui rendrait le contrôle increvable serait
    pire que le défaut. Un brouilleur réellement cassé (p_vrai = 0.9 sur n = 25, soit k = 23) doit
    être REFUSÉ ; et la cellule qui a fait échouer le premier run (seed 9 : k = 20, n = 25, binomial
    p = 0.004) doit désormais PASSER — c'est exactement la discrimination qu'on achète."""
    from tools.evo_runs.evo011_preflight import ALPHA_CELL, _sign_p

    assert _sign_p(23, 25) < ALPHA_CELL, "un brouilleur cassé passerait : contrôle désarmé"
    assert _sign_p(20, 25) >= ALPHA_CELL, "le seed 9 serait encore rejeté : le correctif ne mord pas"
    # ...et le contrôle reste bilatéral : un brouilleur cassé dans l'AUTRE sens est refusé aussi.
    assert _sign_p(2, 25) < ALPHA_CELL
