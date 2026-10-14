"""Calibration du CLIQUET DES SYNTHÈSES (`tools/check_synthesis_counts.py`, 2026-09-07).

⚠️ Un cliquet non calibré ne se contente pas d'échouer : il PRODUIT un verdict. Ces tests le
confrontent à ses trois réponses connues — et le cas qui compte est le CONTRE-EXEMPLE GELÉ, tiré des
trois péremptions réellement mesurées qui ont motivé ce cliquet (gap M5) :

  * « 19 classes sur 19 » dans `REGISTRE_ERREURS.md`, faux le jour même de l'ajout d'E20 ;
  * « 5 cliquets, tous branchés » dans `CLAUDE.md`, alors que le hook en portait 6 ;
  * « 105 détectés, 104 calibrés », alors que le cliquet en comptait 143.

Les compteurs sont injectés (`compteurs=`) : ces tests ne dépendent d'aucun état du dépôt, et ils
mesurent la LOGIQUE du cliquet, pas le dépôt du jour.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.check_synthesis_counts as S  # noqa: E402

_FAUX = {"classes_executables": lambda: 20}


def _doc(tmp_path, texte, nom="SYNTHESE.md"):
    (tmp_path / nom).write_text(texte, encoding="utf-8")
    S._ROOT = str(tmp_path)
    return (nom,)


def test_a_stale_published_count_is_DETECTED(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ — la configuration EXACTE du registre le 2026-09-02 : la doc annonce
    19 classes, il y en a 20. Sans ce cliquet, la phrase reste fausse et sert de prémisse."""
    docs = _doc(tmp_path, "Le registre compte 19 classes. <!-- count:classes_executables=19 -->\n")
    problemes, n = S.scan(docs, _FAUX)
    assert n == 1
    assert [(p[2], p[3], p[4], p[5]) for p in problemes] == [("classes_executables", 19, 20,
                                                              "chiffre_perime")]


def test_an_up_to_date_count_triggers_NOTHING(tmp_path):
    """SPÉCIFICITÉ — sans ce test, un cliquet qui signale TOUT passerait le précédent en étant
    inutilisable."""
    docs = _doc(tmp_path, "Le registre compte 20 classes. <!-- count:classes_executables=20 -->\n")
    assert S.scan(docs, _FAUX) == ([], 1)


def test_a_tag_updated_WITHOUT_its_sentence_is_DETECTED(tmp_path):
    """Le mode d'échec le PLUS PROBABLE de cette convention : on met la balise à jour et on oublie la
    phrase. La balise dit 20 (juste), le lecteur lit 19 (faux) — un cliquet qui ne comparerait que la
    balise au compteur serait vert sur une doc mensongère : il rendrait VRAI sans vérifier (E1)."""
    docs = _doc(tmp_path, "Le registre compte 19 classes. <!-- count:classes_executables=20 -->\n")
    problemes, _ = S.scan(docs, _FAUX)
    assert [p[5] for p in problemes] == ["texte_desynchro"]


def test_an_unknown_counter_is_REFUSED_not_ignored(tmp_path):
    """Une balise qui nomme une grandeur inexistante doit ÉCHOUER, pas être sautée en silence : un
    saut silencieux transformerait une faute de frappe en couverture imaginaire (classe E4 — c'est
    ainsi que trois listes blanches du dépôt ont menti)."""
    docs = _doc(tmp_path, "Total : 42 <!-- count:grandeur_inexistante=42 -->\n")
    problemes, _ = S.scan(docs, _FAUX)
    assert [p[5] for p in problemes] == ["compteur_inconnu"]


def test_a_historical_number_without_tag_is_left_alone(tmp_path):
    """Un chiffre HISTORIQUE (« 105 au 2026-09-01 ») est vrai pour toujours : non balisé, il ne doit
    JAMAIS être signalé. Le cliquet vérifie ce qu'on lui déclare — il ne devine pas."""
    docs = _doc(tmp_path, "Point de départ, 2026-09-01 : 105 détectés, 104 calibrés.\n")
    assert S.scan(docs, _FAUX) == ([], 0)


_REGISTRE_JOUET = (
    "| # | Classe d'erreur | Occurrences | Statut | Garde |\n"
    "|---|---|---|---|---|\n"
    "| **E1** | a | b | `exécutable` | g |\n"
    "| **E2** | a | b | exécutable | g |\n"
    "| **E3** | a | b | **`exécutable`** | g |\n"
    "| **E4** | a `x | y` b | occ | `documenté` **(promu le 2026-09-02 — voir)** | g |\n"
    "| **E5** | a | b | **`non automatisable`** | g |\n"
)


def test_CONTRE_EXEMPLE_GELE_P2_117_le_statut_se_lit_dans_sa_COLONNE_quelle_que_soit_sa_mise_en_forme():
    """P2.117 : le compteur lisait la FORME (« `exécutable` » après un « | ») et non la COLONNE — E28 et E29, écrites
    nues, n'étaient comptées nulle part (24 publiés, 26 réels). Trois écritures du même statut rendent 3, pas 1."""
    assert S._classes_registre("exécutable", _REGISTRE_JOUET) == 3
    assert S._classes_registre("documenté", _REGISTRE_JOUET) == 1
    assert S._classes_registre("non automatisable", _REGISTRE_JOUET) == 1
    assert S._classes_statut_inconnu(_REGISTRE_JOUET) == 0


def test_un_pipe_dans_un_CODE_SPAN_ne_decale_pas_la_colonne():
    """E4 du jouet porte « `x | y` » dans sa deuxième cellule : un split naïf lirait son statut une colonne trop
    tôt (« occ »). Mesuré sur le vrai registre : 6 lignes sur 33 désalignées par un split naïf."""
    statuts = dict(S._statuts_registre(_REGISTRE_JOUET))
    assert statuts["E4"] == "documenté", statuts
    assert len(S._cellules("| **E4** | a `x | y` b | occ | `documenté` | g |")) == 5


def test_un_statut_HORS_vocabulaire_est_COMPTE_jamais_absorbe():
    """Le no-op apparié du compteur d'inconnus : une faute de rédaction (« exécutabel ») sort du compte des
    exécutables ET entre dans celui des inconnus — publié à 0, il fait rougir la porte 8."""
    faux = _REGISTRE_JOUET.replace("| exécutable |", "| exécutabel |")
    assert S._classes_registre("exécutable", faux) == 2
    assert S._classes_statut_inconnu(faux) == 1


def test_un_registre_SANS_colonne_Statut_LEVE_au_lieu_de_rendre_zero():
    import pytest
    with pytest.raises(ValueError, match="Statut"):
        S._classes_registre("exécutable", "| **E1** | a | b | `exécutable` | g |\n")


_NULLES = ("intro\n\n| Date | Run | Cible | Classe | Constat |\n| --- | --- | --- | --- | --- |\n"
           "| d1 | wf_a | x | transport | relectures absentes |\n"
           "| d2 | wf_b | y | **témoin manqué** | un défaut non retrouvé |\n"
           "| d3 | wf_c | z | indécidable | texte illisible |\n"
           "| d4 | wf_d | t | `témoin manqué` (revue réduite) | idem |\n"
           "| d5 | wf_e | `a | b` | instrument | une barre dans un code-span ne décale pas |\n")


def test_P2_177_le_compteur_temoin_manque_ne_compte_QUE_sa_classe_lue_par_l_EN_TETE():
    """P2.177 (2026-10-14) : le compteur « témoin manqué » du Réfutateur. Seule la classe « témoin manqué » compte, quelle
    que soit sa mise en forme ; indécidable, transport et instrument n'en sont pas (la REF les distingue) ; la
    colonne se lit par l'en-tête, la ligne séparatrice ne compte pas, un « | » de code-span ne décale rien."""
    assert S._revues_nulles("témoin manqué", _NULLES) == 2
    assert S._revues_nulles("indécidable", _NULLES) == 1
    assert S._revues_nulles("transport", _NULLES) == 1
    assert S._revues_nulles("instrument", _NULLES) == 1


def test_P2_177_un_registre_des_revues_nulles_SANS_colonne_Classe_LEVE():
    import pytest
    with pytest.raises(ValueError, match="Classe"):
        S._revues_nulles("témoin manqué", "| Date | Run |\n| --- | --- |\n| d | témoin manqué |\n")
    assert S._revues_nulles("témoin manqué", "") == 0          # registre absent : rien à compter, rien à prétendre


def test_P2_177_chaque_document_de_la_porte_8_DECLENCHE_la_porte_dans_le_crochet():
    """Garde de la garde : un document lu par la porte 8 mais absent du déclencheur du crochet ne serait vérifié que si
    un AUTRE document déclencheur était committé avec lui — un compte périmé passerait seul. Le motif est relu dans
    le crochet versionné, jamais recopié ; contrôle positif : un document hors liste ne déclenche pas."""
    import re
    src = open(os.path.join(os.path.dirname(__file__), "..", "..", "tools", "hooks", "pre-commit"), encoding="utf-8").read()
    ligne = next(l for l in src.splitlines() if l.startswith("staged_syn="))
    motif = re.compile(re.search(r"grep -E '([^']+)'", ligne).group(1))
    for d in S._DOCS:
        assert motif.search(d.replace(os.sep, "/")), f"{d} est lu par la porte 8 mais ne la DÉCLENCHE pas"
    assert not motif.search("docs/EDR/UN_RECORD.md")
    assert S._REVUES_NULLES in S._DOCS, "le registre des revues nulles porte sa balise : la porte 8 doit le LIRE"


def test_the_repository_counters_all_return_an_int():
    """Les compteurs RÉELS s'exécutent et rendent un entier. ⚠️ Un compteur qui lève rend le cliquet
    ininterprétable : il doit lever BRUYAMMENT ici plutôt que rendre 0 en production, sans quoi
    « je ne sais pas » deviendrait « c'est faux » (le biais négatif constant du dépôt)."""
    import importlib
    importlib.reload(S)                       # _ROOT a pu être détourné par les tests précédents
    for nom, fn in S.COMPTEURS.items():
        v = fn()
        assert isinstance(v, int) and v >= 0, (nom, v)


def test_the_repository_published_counts_are_all_current():
    """Le dépôt RÉEL : tout compte balisé doit valoir sa grandeur recomputée (c'est ce que le hook
    exécute)."""
    import importlib
    importlib.reload(S)
    problemes, _ = S.scan()
    assert problemes == [], problemes
