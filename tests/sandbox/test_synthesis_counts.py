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
