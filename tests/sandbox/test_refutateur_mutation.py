"""HARNAIS DE MUTATION du Refutateur : chaque garde est cassee d'UN cran, EN MEMOIRE, et doit ROUGIR.

Meme mecanisme que `tools/check_gate_mutation.py` (le cliquet DES cliquets), applique a l'instrument
de revue. Il repond a la question que les gardes ne se posent jamais elles-memes : « ce test
discrimine-t-il ? ». Trois regles du depot sont appliquees a la lettre :

* **L'arbre est PARTAGE : rien n'est jamais ecrit sur disque.** Les mutations remplacent, le temps
  d'un appel, la lecture d'un fichier ou le chargement du roster.
* **Un CONTROLE INTACT precede chaque mutation.** Sans lui, des temoins deja rouges « tueraient »
  tous les mutants et le harnais annoncerait une couverture parfaite en ne mesurant RIEN.
* **Chaque mutation asserte qu'elle a bien MUTE.** Mesure du 2026-09-23 : apres un renommage des
  temoins, une mutation ciblait un nom qui n'existait plus, ne mutait donc rien, et son test passait
  -- le harnais a rendu un FAUX VERT qu'il a fallu lire pour voir.

Un resultat non rejouable n'est pas un resultat : ce harnais vivait hors du depot, « 9/9 rouges »
n'etait verifiable par personne. Il y entre.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_refutateur_temoins as S  # noqa: E402  (les gardes MUTEES vivent la)

_LIRE_ORIG = S._lire


def _lecture_mutee(chemin_cible, transformer):
    """Remplace le CONTENU rendu pour un seul fichier ; le fichier sur disque n'est jamais touche."""
    def _lire(chemin):
        texte = _LIRE_ORIG(chemin)
        if os.path.abspath(chemin) == os.path.abspath(chemin_cible):
            mute = transformer(texte)
            assert mute != texte, f"la mutation ne change RIEN dans {os.path.basename(chemin_cible)}"
            return mute
        return texte
    return _lire


def _rougit(test, lire=None, charger=None):
    """(a rougi, message) — le test echoue-t-il sous la mutation ?"""
    charger_orig = S.T.charger
    if lire:
        S._lire = lire
    if charger:
        S.T.charger = charger
    try:
        test()
    except AssertionError as exc:
        return True, (str(exc).splitlines() or ["(sans message)"])[0][:120]
    finally:
        S._lire = _LIRE_ORIG
        S.T.charger = charger_orig
    return False, ""


def test_CONTROLE_INTACT_toutes_les_gardes_mutees_sont_VERTES_sans_mutation():
    """Sans lui, des temoins deja rouges tueraient tous les mutants et le harnais ne mesurerait rien."""
    for _, test, _, _ in _MUTATIONS:
        rouge, message = _rougit(test)
        assert not rouge, f"{test.__name__} est DEJA rouge sans mutation : {message}"


def _mut_ref(transformer):
    return {"lire": lambda: _lecture_mutee(S._REF, transformer)}


def _mut_workflow(transformer):
    return {"lire": lambda: _lecture_mutee(S._WORKFLOW, transformer)}


_ROSTER_REEL = S.T.charger()


def _renomme_le_noop(libelle):
    def _t(tem):
        return [dict(x, nom=libelle) if x["genre"] == "noop" else x for x in tem]
    return _t


def _fichiers_dans_l_ordre(tem):
    return [dict(x, fichier=f"temoin-{i}.md") for i, x in enumerate(tem, 1)]


def _fichier_parlant(tem):
    return [dict(x, fichier="GRAB-COST.md") if "GRAB" in x["nom"] else x for x in tem]


#: (nom, test qui doit rougir, fabrique de mutation, assertion « j'ai bien mute »)
_MUTATIONS = [
    ("le REF republie un token attendu",
     S.test_le_REF_ne_publie_NI_identite_NI_nombre_NI_genre_NI_seuil_des_temoins,
     _mut_ref(lambda t: t + "\nune critique nommant `forage_payoff`\n"), None),
    ("le REF renomme les temoins",
     S.test_le_REF_ne_publie_NI_identite_NI_nombre_NI_genre_NI_seuil_des_temoins,
     _mut_ref(lambda t: t + "\nLe roster gele EDR-GRAB-COST-1828371 et LOCK-002-286f244.\n"), None),
    ("le REF republie la composition des temoins",
     S.test_le_REF_ne_publie_NI_identite_NI_nombre_NI_genre_NI_seuil_des_temoins,
     _mut_ref(lambda t: t + "\nQuatre temoins : trois defauts et un quatrieme, sain.\n"), None),
    ("le recapitulatif du REF se desynchronise",
     S.test_le_recapitulatif_du_REF_se_derive_du_TABLEAU_et_non_de_la_memoire,
     _mut_ref(lambda t: t.replace("**DÉLÈGUENT** : P2, P3, P9", "**DÉLÈGUENT** : P2, P3")), None),
    ("le REF delegue a une porte inexistante",
     S.test_le_REF_dit_pour_CHAQUE_prompt_s_il_DELEGUE_a_une_porte_ou_s_il_JUGE,
     _mut_ref(lambda t: t.replace("tools/check_regime_claims.py", "tools/check_fantome.py")), None),
    ("le workflow rejuge (double bareme)",
     S.test_le_workflow_ne_contient_AUCUN_bareme_et_fait_lancer_le_CLI_python,
     _mut_workflow(lambda t: t + "\nfunction retrouve(t, c) { return new RegExp(t.attendu).test(c) }\n"),
     None),
    ("le workflow cesse de publier le plancher",
     S.test_le_workflow_ne_contient_AUCUN_bareme_et_fait_lancer_le_CLI_python,
     _mut_workflow(lambda t: t.replace("--plancher", "--rien")), None),
    ("le workflow reaccepte le roster de l'appelant",
     S.test_le_workflow_n_accepte_de_l_appelant_que_des_CHEMINS,
     _mut_workflow(lambda t: t.replace("args.fichiers || []", "args.temoins || []")), None),
    ("le workflow ne declare plus les chemins des critiques",
     S.test_le_workflow_fait_DECLARER_les_chemins_pour_que_le_controleur_relance_le_CLI,
     _mut_workflow(lambda t: t.replace("fichier_critiques", "fichier_interne")), None),
    # Le harnais a REFUSE de charger le script le 2026-09-24 sur ce backtick exact (116:62), et
    # `node --check` rendait 0 : la garde ne peut pas s'appuyer sur lui.
    ("un backtick NU revient dans un litteral gabarit",
     S.test_le_workflow_n_a_AUCUN_backtick_NU_dans_ses_litteraux_gabarits,
     _mut_workflow(lambda t: t.replace("dans le champ plancher.", "dans le champ `plancher`.")), None),
    # Le premier Step 4 reel a rendu NUL parce que `relectures` n'atteignait pas le verificateur :
    # un prompt qui dit « ci-dessus » sans rien interpoler demande de relayer ce qu'il n'a pas recu.
    ("le verificateur ne recoit plus les relectures",
     S.test_le_prompt_du_VERIFICATEUR_recoit_bien_les_relectures_et_les_jugements,
     _mut_workflow(lambda t: t.replace(
         "Relectures, une par temoin (JSON) : ${JSON.stringify(relectures)}\n", "")), None),
    ("un prompt deictique n'interpole plus rien",
     S.test_chaque_prompt_qui_dit_CI_DESSOUS_interpole_vraiment_une_donnee,
     _mut_workflow(lambda t: t.replace(
         "Relectures a juger (JSON) : ${JSON.stringify(relecturesJugees)}",
         "Relectures a juger : voir plus bas")), None),
    ("le juge recoit TOUTES les relectures, no-op compris",
     S.test_le_JUGE_ne_recoit_QUE_les_relectures_a_juger_pas_celle_du_noop,
     _mut_workflow(lambda t: t.replace("JSON.stringify(relecturesJugees)",
                                       "JSON.stringify(relectures)")), None),
]

_MUTATIONS_ROSTER = [
    ("un nom de temoin renomme a la main",
     S.test_le_nom_d_un_temoin_est_une_FORME_DERIVEE_et_non_un_libelle_libre,
     _renomme_le_noop("LOCK-002-sain")),
    ("le nom que la liste noire laissait passer",
     S.test_le_nom_d_un_temoin_est_une_FORME_DERIVEE_et_non_un_libelle_libre,
     _renomme_le_noop("RETAIN-COMPOSE-pre-retractation")),
    ("les fichiers suivent l'ordre du roster",
     S.test_les_fichiers_d_extraction_sont_NEUTRES_et_decorreles_de_l_ordre_du_roster,
     _fichiers_dans_l_ordre),
    ("un fichier d'extraction parlant",
     S.test_les_fichiers_d_extraction_sont_NEUTRES_et_decorreles_de_l_ordre_du_roster,
     _fichier_parlant),
]


@pytest.mark.parametrize("nom,test,mutation,_", _MUTATIONS, ids=[m[0] for m in _MUTATIONS])
def test_chaque_mutation_de_DOCUMENT_est_tuee_par_un_temoin(nom, test, mutation, _):
    rouge, message = _rougit(test, lire=mutation["lire"]())
    assert rouge, f"MUTATION NON TUEE — {nom} : la garde {test.__name__} reste VERTE"
    assert message, "la garde rougit sans message : on ne saurait pas POURQUOI"


@pytest.mark.parametrize("nom,test,transformer", _MUTATIONS_ROSTER,
                         ids=[m[0] for m in _MUTATIONS_ROSTER])
def test_chaque_mutation_du_ROSTER_est_tuee_par_un_temoin(nom, test, transformer):
    mute = transformer([dict(t) for t in _ROSTER_REEL])
    assert mute != _ROSTER_REEL, f"la mutation « {nom} » ne mute RIEN"
    rouge, message = _rougit(test, charger=lambda: mute)
    assert rouge, f"MUTATION NON TUEE — {nom} : la garde {test.__name__} reste VERTE"
    assert message


def test_la_REDACTION_de_la_calibration_est_mutee_et_son_temoin_rougit(capsys):
    """Si `cas_du_juge()` cesse de rediger, le juge lit sa propre reponse et sa calibration ne prouve
    plus rien. La garde doit le voir -- c'est le seul rempart, une consigne de « ne pas regarder »
    n'en est pas un."""
    garde = (lambda: S.test_les_cas_servis_au_JUGE_sont_REDIGES_et_la_vue_complete_est_le_controle_positif(
        capsys))
    rouge, message = _rougit(garde)
    assert not rouge, f"garde DEJA rouge sans mutation : {message}"
    capsys.readouterr()

    vrai = S.T._REPONSES_DU_JUGE
    S.T._REPONSES_DU_JUGE = ()          # la redaction ne retire plus rien
    assert S.T._REPONSES_DU_JUGE != vrai, "la mutation ne mute RIEN"
    try:
        servi = S.T.cas_du_juge()
        assert any("juge" in c for c in servi), "la mutation n'a pas eu d'effet sur la vue servie"
        rouge, message = _rougit(garde)
    finally:
        S.T._REPONSES_DU_JUGE = vrai
        capsys.readouterr()
    assert rouge, "MUTATION NON TUEE : la vue servie au juge publie sa reponse et la garde reste VERTE"
    assert message


def test_le_bareme_lui_meme_est_mute_le_plancher_remonte(tmp_path):
    """La mutation la plus importante : desarmer un etage doit faire REMONTER le plancher.

    C'est la mesure qui manquait le 2026-09-23. Un plancher nul ne vaut que si on a montre qu'il
    SAIT remonter : sinon « 0/5 » peut vouloir dire « l'instrument ne voit plus rien du tout ».
    """
    dossier = str(tmp_path)
    S.T.extraire_tous(dossier)
    intact = S.T.plancher(dossier)
    assert intact["majorant_fausses_retrouvailles"] == 0, "controle INTACT"

    vraie_preuve = S.T.preuve_de_forme
    S.T.preuve_de_forme = lambda c: (True, "garde DESARMEE")
    try:
        sans_preuve = S.T.plancher(dossier)
    finally:
        S.T.preuve_de_forme = vraie_preuve
    assert sans_preuve["majorant_fausses_retrouvailles"] >= 3, (
        "desarmer la preuve de forme doit laisser repasser l'attaque universelle sur les trois "
        f"defauts, or le plancher reste a {sans_preuve['majorant_fausses_retrouvailles']}")

    vrai_seuil = S.T.mots_recopie
    S.T.mots_recopie = lambda: 10 ** 6
    try:
        sans_recopie = S.T.plancher(dossier)
    finally:
        S.T.mots_recopie = vrai_seuil
    assert sans_recopie["majorant_fausses_retrouvailles"] >= 2, (
        "desarmer l'anti-recopie doit laisser repasser les deux recopies de ligne, or le plancher "
        f"reste a {sans_recopie['majorant_fausses_retrouvailles']}")
