"""Contre-exemples GELÉS de la GARDE DE BAIL (`tests/conftest.py`) — classe E10, occurrence 7.

La garde saute les tests simulant un monde quand un bail `kuzu` est détenu par un autre processus.
Sans les tests ci-dessous, elle pourrait :
  * ne jamais rien sauter (garde absente déguisée en garde) ;
  * tout sauter en permanence (suite silencieusement désactivée — pire que le problème d'origine).

Le second risque est le plus grave et c'est celui que le test de SPÉCIFICITÉ ferme.
"""
import os
import sys

import pytest

# ⚠️ Ce module NE SIMULE JAMAIS de monde : il ne fait que MENTIONNER les symboles de monde dans des
# chaînes de fixture. Sans cette exemption, la garde qu'il teste sauterait ses propres tests — elle
# serait invérifiable précisément quand elle agit. Mesuré en l'écrivant, le 2026-09-01.
_LEASE_GUARD_EXEMPT = True

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_CONFTEST = os.path.join(os.path.dirname(__file__), "..", "conftest.py")


def _load_conftest():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_agagi_conftest", os.path.abspath(_CONFTEST))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Item:
    """Un item pytest minimal : un module (donc un fichier source) et des marqueurs collectés."""

    def __init__(self, path):
        self.module = type("M", (), {"__file__": path})
        self.marks = []

    def add_marker(self, m):
        self.marks.append(m)

    def get_closest_marker(self, _name):
        return None


def _items(tmp_path, monde: bool):
    p = tmp_path / ("test_monde.py" if monde else "test_pur.py")
    p.write_text(
        "from src.agents.mamba_agent import MambaAgent\ndef test_x(): pass\n" if monde
        else "import math\ndef test_x(): assert math.pi > 3\n", encoding="utf-8")
    return [_Item(str(p))]


def test_the_guard_SKIPS_world_tests_when_a_lease_is_held(tmp_path, monkeypatch):
    """⚠️ LE test : bail détenu par un tiers -> un test simulant un monde doit être SAUTÉ, et la raison
    doit NOMMER le détenteur (sinon on ne sait pas s'il faut attendre ou tuer)."""
    C = _load_conftest()
    monkeypatch.setattr(C, "_foreign_kuzu_holder", lambda: "un-run (pid=4242)")
    items = _items(tmp_path, monde=True)
    C.pytest_collection_modifyitems(None, items)
    assert items[0].marks, "un test simulant un monde doit être sauté quand le bail est pris"
    raison = items[0].marks[0].kwargs.get("reason", "")
    assert "un-run" in raison and "4242" in raison, f"la raison doit nommer le détenteur : {raison!r}"


def test_the_guard_SKIPS_NOTHING_when_no_lease_is_held(tmp_path, monkeypatch):
    """⚠️ SPÉCIFICITÉ — LE risque majeur. Une garde qui saute sans bail détenu désactiverait la suite
    entière en silence : tout serait vert, plus rien ne serait vérifié (classe E4). Si ce test tombe,
    la suite ne teste PLUS RIEN et il faut le traiter comme une urgence, pas ajuster le test."""
    C = _load_conftest()
    monkeypatch.setattr(C, "_foreign_kuzu_holder", lambda: None)
    items = _items(tmp_path, monde=True)
    C.pytest_collection_modifyitems(None, items)
    assert not items[0].marks, "sans bail détenu, RIEN ne doit être sauté"


def test_the_guard_SPARES_pure_tests_even_when_a_lease_is_held(tmp_path, monkeypatch):
    """Un test qui ne simule aucun monde n'a aucune raison d'être sauté : la garde doit rester ciblée,
    sinon un run en vol bloque tout le travail méthodologique — celui qu'on peut justement faire
    pendant qu'un run tourne."""
    C = _load_conftest()
    monkeypatch.setattr(C, "_foreign_kuzu_holder", lambda: "un-run (pid=4242)")
    items = _items(tmp_path, monde=False)
    C.pytest_collection_modifyitems(None, items)
    assert not items[0].marks, "un test pur ne doit pas être sauté"


def test_the_holder_detector_ignores_our_own_process():
    """La garde ne doit jamais se bloquer elle-même : un bail détenu par ce processus ou l'un de ses
    ancêtres n'est pas « étranger ». Sinon un run gouverné qui lance ses propres tests se saborde."""
    C = _load_conftest()
    try:
        from tools.jobs import doctor as D
    except Exception:
        pytest.skip("tools.jobs indisponible")
    protege = set(D._protected_pids()) | {os.getpid()}
    detenteur = C._foreign_kuzu_holder()
    if detenteur is None:
        return                                    # aucun bail vivant : rien à vérifier
    pid = int(detenteur.rsplit("pid=", 1)[1].rstrip(")"))
    assert pid not in protege, f"le détenteur signalé {pid} est nous-même ou un ancêtre"


# --------------------------------------------------------------------------------------------------
# P2.69 (ii), 2026-09-15 — le FILET RUNTIME : la garde textuelle laissait passer 58 fichiers qui
# simulent un monde par import indirect. Ici : bail tenu par un tiers -> CONSTRUIRE un monde saute
# le test, au point exact, avec la raison ; sans bail -> le constructeur est celui d'origine.
# --------------------------------------------------------------------------------------------------

def test_the_runtime_net_SKIPS_at_world_construction_when_a_lease_is_held(monkeypatch):
    C = _load_conftest()
    from src.worlds.world_1_stoneage import Biosphere3D
    orig = Biosphere3D.__init__
    C._arm_runtime_net("un-run (pid=4242) tient kuzu")
    try:
        assert Biosphere3D.__init__ is not orig
        with pytest.raises(pytest.skip.Exception) as exc:
            Biosphere3D()
        assert "4242" in str(exc.value)
    finally:
        C._disarm_runtime_net()
    assert Biosphere3D.__init__ is orig, "le filet doit se retirer sans trace"


def test_the_runtime_net_is_NOT_armed_when_no_lease_is_held(tmp_path, monkeypatch):
    """NO-OP apparié : sans bail, `pytest_collection_modifyitems` rend avant d'armer quoi que ce soit."""
    C = _load_conftest()
    monkeypatch.setattr(C, "_foreign_kuzu_holder", lambda: None)
    from src.worlds.world_1_stoneage import Biosphere3D
    orig = Biosphere3D.__init__
    C.pytest_collection_modifyitems(None, _items(tmp_path, monde=True))
    assert Biosphere3D.__init__ is orig and not C._NET["armed"]


def test_the_runtime_net_is_armed_by_the_collection_hook_when_a_lease_is_held(tmp_path, monkeypatch):
    """Le chemin RÉEL : détenteur étranger -> le hook de collecte arme le filet (pas seulement les
    marqueurs textuels). C'est ce qui couvre les 58 fichiers sans indice."""
    C = _load_conftest()
    monkeypatch.setattr(C, "_foreign_kuzu_holder", lambda: "un-run (pid=4242)")
    from src.worlds.world_1_stoneage import Biosphere3D
    orig = Biosphere3D.__init__
    try:
        C.pytest_collection_modifyitems(None, _items(tmp_path, monde=False))   # aucun indice textuel
        assert C._NET["armed"] and Biosphere3D.__init__ is not orig
        with pytest.raises(pytest.skip.Exception):
            Biosphere3D()
    finally:
        C._disarm_runtime_net()
    assert Biosphere3D.__init__ is orig
