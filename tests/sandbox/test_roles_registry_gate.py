"""Porte 21 : une ligne de ROLES.md sans ses cinq colonnes est une regle documentee, pas un role."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_roles_registry as R  # noqa: E402

ENTETE = ("| Rôle | Statut | Instrument | Contrôle positif | Coût mesuré | Compteurs | Dissolution / naissance |\n"
          "| --- | --- | --- | --- | --- | --- | --- |\n")
PLEINE = "| **PM** | instancié | `tools/pm/board.py::compute` | fixtures A1-A8 + no-op | tokens/tick : non mesuré | `ROLES_COUNTS.json` | précision < 1/10 sur 30 j |\n"
CREUSE = "| **Stratège** | instancié | workflow figé | témoin périmé tué | — | propositions / acceptées | deux passes sans changement |\n"
CANDIDAT_OK = "| **Régisseur des runs** | candidat | — | — | — | — | deux runs abandonnés en 30 j |\n"
CANDIDAT_NU = "| **Intégrateur** | candidat | — | — | — | — | |\n"
STATUT_INCONNU = "| **X** | en cours | a | b | c | d | e |\n"


def test_lignes_lit_role_statut_et_sept_cellules():
    L = R.lignes(ENTETE + PLEINE)
    assert len(L) == 1 and L[0]["role"] == "PM" and L[0]["statut"] == "instancié" and len(L[0]["cellules"]) == 7


def test_une_ligne_instanciee_COMPLETE_ne_produit_aucun_defaut():
    assert R.defauts(R.lignes(ENTETE + PLEINE)) == []


def test_CONTRE_EXEMPLE_GELE_une_cellule_vide_sur_un_role_instancie_est_un_defaut():
    d = R.defauts(R.lignes(ENTETE + CREUSE))
    assert len(d) == 1 and d[0]["role"] == "Stratège" and "Coût mesuré" in d[0]["raison"]


def test_un_candidat_doit_porter_son_critere_de_naissance_et_rien_d_autre():
    assert R.defauts(R.lignes(ENTETE + CANDIDAT_OK)) == []
    d = R.defauts(R.lignes(ENTETE + CANDIDAT_NU))
    assert len(d) == 1 and "naissance" in d[0]["raison"]


def test_un_statut_hors_vocabulaire_est_un_defaut():
    d = R.defauts(R.lignes(ENTETE + STATUT_INCONNU))
    assert len(d) == 1 and "statut" in d[0]["raison"]


def test_le_registre_REEL_du_depot_passe_la_porte():
    with open(os.path.join(R._ROOT, "docs", "roadmap", "ROLES.md"), encoding="utf-8") as fh:
        L = R.lignes(fh.read())
    assert len(L) >= 3, "le périmètre est vide, le test ne prouverait rien"
    assert R.defauts(L) == []


def test_main_rend_1_sur_un_defaut_et_0_sinon(tmp_path, monkeypatch):
    p = tmp_path / "ROLES.md"
    p.write_text(ENTETE + CREUSE, encoding="utf-8")
    monkeypatch.setattr(R, "_REGISTRE", str(p))
    assert R.main([]) == 1
    p.write_text(ENTETE + PLEINE, encoding="utf-8")
    assert R.main([]) == 0
