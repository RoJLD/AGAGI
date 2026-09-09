"""Contre-exemples GELÉS du cliquet de fraîcheur du backlog — il doit pouvoir ÉCHOUER.

Sans ces tests, `tools/check_backlog_freshness.py` serait un outil qui passe au vert quoi qu'il arrive :
exactement le défaut qu'il est censé empêcher ailleurs.

Chaque test forge un backlog minimal contenant UNE péremption connue, et vérifie que le cliquet la voit.
Le dernier vérifie l'inverse — un backlog sain ne doit rien déclencher — parce qu'un détecteur qui
signale tout passerait les autres tests tout en étant inutilisable.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_backlog_freshness as B  # noqa: E402


def _backlog(tmp_path, monkeypatch, texte):
    p = tmp_path / "BACKLOG.md"
    p.write_text(texte, encoding="utf-8")
    monkeypatch.setattr(B, "_BACKLOG", str(p))
    return p


def test_a_dead_record_link_is_DETECTED(tmp_path, monkeypatch):
    """⚠️ Citer un record qui n'existe pas : le lecteur suit un renvoi vers le vide."""
    _backlog(tmp_path, monkeypatch, "Voir [[EDR-NEXISTE-PAS-999]] pour le détail.\n")
    trouve = B.scan()
    assert any(k.startswith("lien-mort:") for k in trouve), (
        f"un lien de record mort doit être détecté, or : {trouve}")


def test_a_real_record_link_is_SPARED(tmp_path, monkeypatch):
    """Spécificité : un renvoi valide ne doit PAS être signalé."""
    _backlog(tmp_path, monkeypatch, "Mesuré par [[EDR-EVO-010]], sans appel.\n")
    assert not any(k.startswith("lien-mort:") for k in B.scan()), (
        "un record qui existe ne doit pas être signalé comme lien mort")


def test_memory_slugs_are_NOT_treated_as_records(tmp_path, monkeypatch):
    """DÉFAUT MESURÉ (2026-09-01) : deux espaces de noms cohabitent dans les `[[...]]`. Les slugs de
    mémoire de session (kebab minuscule) vivent hors du dépôt ; les signaler comme records manquants
    exigeait qu'un fichier existe là où la convention dit qu'il n'existe pas."""
    _backlog(tmp_path, monkeypatch, "Recoupe [[warm-start-transversal-law]] et [[s2-world-demand-thread]].\n")
    assert B.scan() == {}, "les slugs de mémoire ne sont pas des records et ne doivent rien déclencher"


def test_a_duplicated_task_number_is_DETECTED(tmp_path, monkeypatch):
    """Deux entrées sous le même numéro : l'une est forcément périmée et rien ne dit laquelle."""
    _backlog(tmp_path, monkeypatch,
             "**P2.4 — première version, présentée comme ouverte.**\n\n"
             "**P2.4 — ✅ FAIT, deuxième version.**\n")
    assert "numero-double:P2.4" in B.scan()


def test_a_dead_file_path_is_DETECTED(tmp_path, monkeypatch):
    """Un backlog qui pointe un fichier disparu envoie le lecteur dans le vide."""
    _backlog(tmp_path, monkeypatch, "Le correctif vit dans `tools/ce_fichier_nexiste_pas.py`.\n")
    assert any(k.startswith("chemin-mort:") for k in B.scan())


def test_an_existing_file_path_is_SPARED(tmp_path, monkeypatch):
    """Spécificité du volet chemins."""
    _backlog(tmp_path, monkeypatch, "Le cliquet vit dans `tools/check_backlog_freshness.py`.\n")
    assert not any(k.startswith("chemin-mort:") for k in B.scan())


def test_a_clean_backlog_triggers_NOTHING(tmp_path, monkeypatch):
    """⚠️ Sans ce test, un détecteur qui signale TOUT passerait tous les autres."""
    _backlog(tmp_path, monkeypatch,
             "**P9.1 — une tâche unique.**\n\nMesuré par [[EDR-EVO-010]], code dans "
             "`tools/check_backlog_freshness.py`.\n")
    assert B.scan() == {}, "un backlog sain ne doit rien déclencher"


def test_the_real_backlog_has_no_NEW_staleness():
    """L'état gelé du dépôt. Si ce test tombe, une péremption mécanique vient d'être introduite."""
    base = B._load_baseline()
    nouvelles = {k: v for k, v in B.scan().items() if k not in base}
    assert not nouvelles, (
        f"nouvelles péremptions du backlog : {nouvelles}. Corriger, ou les déclarer explicitement "
        f"avec `--update-baseline` en disant POURQUOI.")


def test_a_PROPOSED_path_is_not_a_dead_path(tmp_path, monkeypatch):
    """⚠️ FAUX POSITIF MESURE (2026-09-01), corrige plutot que gele. Un backlog PROPOSE legitimement des
    fichiers qui n'existent pas encore -- c'est sa fonction. Le detecteur avait signale
    `tools/check_staged_authorship.py`, introduit par « *Correctif candidat, plus fort* : un script ...
    A evaluer ». Le geler dans la baseline aurait masque une classe de faux positifs qui se reproduira
    a chaque proposition."""
    _backlog(tmp_path, monkeypatch,
             "*Correctif candidat* : un script `tools/pas_encore_ecrit.py` qui ferait X. À évaluer.\n")
    assert not any(k.startswith("chemin-mort:") for k in B.scan()), (
        "un chemin PROPOSE ne doit pas etre signale comme mort")


def test_a_path_CITED_AS_EXISTING_is_still_detected(tmp_path, monkeypatch):
    """⚠️ SPECIFICITE de la correction : sans elle, on aurait desactive le detecteur de chemins morts.
    Une citation SANS marqueur de proposition doit toujours etre attrapee."""
    _backlog(tmp_path, monkeypatch,
             "La garde vit dans `tools/ce_fichier_a_ete_supprime.py` et bloque les commits.\n")
    assert any(k.startswith("chemin-mort:") for k in B.scan())


# --- GARDE D'AMPUTATION (2026-09-09) : le cliquet rendait OK sur un backlog VIDE ---------------------
#
# ⚠️ ARMEE SUR UN INCIDENT REEL, subi par la session qui ecrit ces lignes. Une reecriture
# programmatique a vide `PRIORITES_ET_DETTES.md` -- 2352 lignes -> 0 -- SANS LEVER :
#     io.open(p, "w").write(io.open(p).read().replace(old, new))
# Python evalue les arguments de GAUCHE A DROITE : le mode "w" TRONQUE le fichier avant que le
# `read()` interne ne le lise. Le read rend "", le replace rend "", le fichier est ecrase par du vide.
# Meme famille qu'E22 (une suppression rend le signal plus vert) avec un mecanisme NEUF : l'ordre
# d'evaluation des arguments.
#
# Ce cliquet a alors rendu `exit 0` et « OK » -- et il a INVITE a resserrer sa baseline
# (« 2 resorbee(s) -> --update-baseline »), ce qui aurait fige l'amputation. Entree vide -> succes,
# commis par une GARDE : exactement le biais que ce depot traque chez ses sondes.
#
# ⚠️ ET LA PREMIERE VERSION DE LA GARDE ETAIT ELLE-MEME INERTE : elle lisait
# `_load_baseline().get("plancher_entrees")`, or `_load_baseline()` rend le sous-dictionnaire
# `legataires`, donc le plancher valait TOUJOURS 0. Elle a passe son propre contre-exemple. Classe E1,
# commise en armant une garde contre exactement ca -- seul le contre-exemple GELE l'a dit.

def test_the_ratchet_REFUSES_an_amputated_backlog(monkeypatch):
    """CONTRE-EXEMPLE GELE : l'incident rejoue. Un backlog vide doit faire ECHOUER le cliquet."""
    import sys

    import tools.check_backlog_freshness as m
    # `main()` lit `sys.argv` : sous pytest il y trouverait les arguments de pytest et argparse
    # sortirait en erreur. On lui donne un argv NU.
    monkeypatch.setattr(sys, "argv", ["check_backlog_freshness.py"])
    monkeypatch.setattr(m, "compter_entrees", lambda txt=None: 0)
    monkeypatch.setattr(m, "_charger_plancher", lambda: 68)
    assert m.main() == 1, "un backlog AMPUTE doit faire echouer le cliquet, pas passer"


def test_the_ratchet_SPARES_an_intact_backlog(monkeypatch):
    """NO-OP APPARIE, indispensable : une garde qui refuserait TOUT passerait le cas precedent
    sans rien mesurer. Au plancher exact, le cliquet doit se taire."""
    import sys

    import tools.check_backlog_freshness as m
    # `main()` lit `sys.argv` : sous pytest il y trouverait les arguments de pytest et argparse
    # sortirait en erreur. On lui donne un argv NU.
    monkeypatch.setattr(sys, "argv", ["check_backlog_freshness.py"])
    monkeypatch.setattr(m, "compter_entrees", lambda txt=None: 68)
    monkeypatch.setattr(m, "_charger_plancher", lambda: 68)
    assert m.main() == 0, "un backlog au plancher exact ne doit pas etre refuse"


def test_the_FLOOR_can_only_go_UP():
    """Le plancher est un CLIQUET. Geler une baseline contre un backlog ampute figerait l'amputation :
    `--update-baseline` prend donc le MAX de l'ancien et du courant. Verifie sur le code, car c'est
    une propriete du chemin `--update-baseline` qu'aucun appel normal n'exerce."""
    import inspect
    import tools.check_backlog_freshness as m
    src = inspect.getsource(m.main)
    assert "max(n_entrees, plancher)" in src, (
        "le plancher doit etre gele au MAX -- sinon une amputation devient la nouvelle norme")
    assert src.index("if n_entrees < plancher") < src.index("if args.update_baseline"), (
        "la garde doit passer AVANT --update-baseline, sinon on gele l'amputation qu'on refuse")


def test_the_REAL_backlog_is_ABOVE_its_frozen_floor():
    """Ancrage sur le reel : le fichier vivant doit etre au-dessus de son plancher, et le plancher
    doit etre non nul (un plancher a zero serait une garde desarmee)."""
    import tools.check_backlog_freshness as m
    plancher = m._charger_plancher()
    assert plancher > 0, "plancher a zero = garde desarmee"
    assert m.compter_entrees() >= plancher
