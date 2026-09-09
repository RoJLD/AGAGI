# -*- coding: utf-8 -*-
"""Calibration de `src/paths.py` — le point d'indirection des chemins de données.

Ce que ces cas protègent, dans l'ordre d'importance :
 1. **la migration est bit-identique** sans variable d'environnement. Si ce cas tombe, brancher le
    module casse des chemins existants, et le remède serait pire que le mal ;
 2. **les trois racines sont SÉPARABLES** — c'est tout l'intérêt : le froid part sur le NAS, la base
    vivante de 2,7 Go reste sur disque rapide ;
 3. **rien ne s'exécute à l'import** — le 2026-09-08, un module posant `HOF_PATH` au niveau module a
    fait échouer `load_champion_genome()` dans tout processus qui l'importait (classe E5) ;
 4. **une racine absente le dit À L'ENDROIT où elle est absente**, et jamais sous la forme d'un jeu
    de données vide (le défaut du même jour : « HoF vide : évoluer d'abord » alors que le fichier
    existait, intact).

EXEMPTION DÉCLARÉE de la garde de bail : aucun monde n'est construit.
"""
import importlib
import os

import pytest

from src import paths

_LEASE_GUARD_EXEMPT = True


@pytest.fixture(autouse=True)
def _env_propre(monkeypatch):
    """Chaque cas part d'un environnement SANS variable de racine : sinon un test vert ici pourrait
    l'être grâce à la configuration de la machine, pas grâce au code."""
    for v in ("AGAGI_DATA_ROOT", "AGAGI_RESULTS_ROOT", "AGAGI_DB_ROOT"):
        monkeypatch.delenv(v, raising=False)


# --------------------------------------------------------------------------------------------------
# 1. La migration est BIT-IDENTIQUE sans configuration
# --------------------------------------------------------------------------------------------------

def test_sans_variable_les_chemins_sont_EXACTEMENT_ceux_d_aujourd_hui():
    """RÉPONSE CONNUE : ce sont les littéraux que l'inventaire a trouvés dans le code. Si l'un
    d'eux change, rebrancher un site le CASSE — et le module perd sa seule garantie."""
    # ⚠️ Comparaison au LITTERAL, jamais via os.path.join : c'est justement `os.path.join` qui a
    # produit `data\hall_of_fame.pkl` sous Windows et casse `tests/test_famine_pipeline_wiring.py`.
    # Un test qui joindrait des deux cotes aurait ete VERT sur le defaut.
    assert paths.hall_of_fame() == "data/hall_of_fame.pkl"
    assert paths.kuzu_graph() == "data/kuzu_graph.db"
    assert paths.experiment_graph() == "data/experiment_graph.db"
    assert paths.agent_states() == "data/agent_states"
    assert paths.agent_states("hall_of_fame") == "data/agent_states/hall_of_fame"
    assert paths.epoch_states() == "data/epoch_states"
    assert paths.genomes() == "data/genomes"
    assert paths.results_file("warm008_aux_off.json") == "results/warm008_aux_off.json"


def test_les_VARIANTES_de_hall_of_fame_suivent_la_convention_du_depot():
    """25 des 57 sites visaient cette famille, variantes comprises (`_famine`, `_famine_s43`)."""
    assert paths.hall_of_fame("famine") == "data/hall_of_fame_famine.pkl"
    assert paths.hall_of_fame("famine_s43") == "data/hall_of_fame_famine_s43.pkl"


# --------------------------------------------------------------------------------------------------
# 2. Les trois racines sont SÉPARABLES — c'est le but
# --------------------------------------------------------------------------------------------------

def test_le_FROID_part_sur_le_NAS_pendant_que_la_BASE_reste_locale(monkeypatch):
    """LE cas qui justifie trois racines et non une. `kuzu_graph.db` pèse 2 674 Mo (89 % de data/)
    et c'est une base VIVANTE : elle ne suit PAS le froid sur le partage réseau."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", "//nas/agagi/froid")
    monkeypatch.setenv("AGAGI_DB_ROOT", "D:/agagi-local")

    assert paths.hall_of_fame().startswith("//nas/agagi/froid")
    assert paths.agent_states().startswith("//nas/agagi/froid")
    assert paths.kuzu_graph().startswith("D:/agagi-local")
    assert paths.experiment_graph().startswith("D:/agagi-local")


def test_db_root_SUIT_data_root_par_defaut():
    """Branche NÉGATIVE appariée : sans `AGAGI_DB_ROOT`, la base reste où elle est aujourd'hui.
    Sans ce cas, la séparation serait un piège pour qui ne configure qu'une variable."""
    assert paths.db_root() == paths.data_root() == "data"


def test_results_est_INDEPENDANTE_des_deux_autres(monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", "/froid")
    assert paths.results_root() == "results"
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", "/mesures")
    assert paths.results_file("x.json") == "/mesures/x.json"
    assert paths.data_root() == "/froid"


def test_une_variable_VIDE_ne_vaut_pas_une_variable_POSEE(monkeypatch):
    """`AGAGI_DATA_ROOT=""` doit retomber sur le défaut, pas produire des chemins relatifs à la
    racine du disque. C'est la forme la plus courante d'un script shell mal quoté."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", "")
    assert paths.data_root() == "data"


# --------------------------------------------------------------------------------------------------
# 3. Rien ne s'exécute à l'import, et la racine est relue à CHAQUE appel
# --------------------------------------------------------------------------------------------------

def test_la_racine_est_RELUE_a_chaque_appel_et_non_figee_a_l_import(monkeypatch):
    """Si la valeur était figée à l'import, l'ordre des imports déciderait de la racine — exactement
    le défaut mesuré le 2026-09-08 avec `HOF_PATH` (classe E5). Ici, poser la variable APRÈS
    l'import doit agir."""
    avant = paths.data_root()
    monkeypatch.setenv("AGAGI_DATA_ROOT", "/tard")
    assert paths.data_root() == "/tard" != avant


def test_l_import_du_module_ne_fait_RIEN(monkeypatch):
    """Ni lecture de disque, ni création de dossier, ni écriture d'environnement. On réimporte avec
    des racines inexistantes : cela doit être parfaitement silencieux."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", "/racine/qui/n/existe/pas")
    monkeypatch.setenv("AGAGI_DB_ROOT", "/autre/absente")
    importlib.reload(paths)
    assert paths.data_root() == "/racine/qui/n/existe/pas"
    assert not os.path.exists("/racine/qui/n/existe/pas")


# --------------------------------------------------------------------------------------------------
# 4. Une racine absente le dit LÀ où elle est absente
# --------------------------------------------------------------------------------------------------

def test_une_racine_ABSENTE_leve_en_NOMMANT_sa_variable(monkeypatch):
    """Le message doit porter la variable ET la valeur : un montage NAS non monté doit se
    diagnostiquer sans fouiller. Et il doit dire que ce n'est PAS un jeu de données vide — c'est
    exactement la confusion qui a coûté une demi-journée le 2026-09-08."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", "//nas-eteint/agagi")
    with pytest.raises(RuntimeError) as e:
        paths.assert_roots_exist()
    m = str(e.value)
    assert "AGAGI_DATA_ROOT" in m and "//nas-eteint/agagi" in m and "PAS un jeu de données vide" in m


def test_la_verification_est_CIBLEE_et_ne_crie_pas_sur_ce_qu_on_ne_lui_demande_pas(monkeypatch):
    """Branche négative appariée : une garde qui exigerait les trois racines à chaque appel serait
    inutilisable pour un outil qui ne lit que `results/` — et serait donc désarmée."""
    monkeypatch.setenv("AGAGI_DB_ROOT", "//nas-eteint/base")
    assert paths.assert_roots_exist(data=False, results=False, db=False) is True
    with pytest.raises(RuntimeError, match="AGAGI_DB_ROOT"):
        paths.assert_roots_exist(data=False, db=True)


def test_describe_dit_la_valeur_ET_son_origine(monkeypatch):
    """Une mesure faite sur la mauvaise racine ne doit pas pouvoir passer inaperçue : le runner
    imprime ceci en tête."""
    monkeypatch.setenv("AGAGI_RESULTS_ROOT", "/mesures")
    d = paths.describe()
    assert d["AGAGI_RESULTS_ROOT"] == {"valeur": "/mesures", "origine": "environnement", "existe": False}
    assert d["AGAGI_DATA_ROOT"]["origine"] == "defaut"
