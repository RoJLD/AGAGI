"""P2.142 — témoins de la GARDE DES ARBRES (`tests/garde_arbres.py`, branchée par `tests/conftest.py`).

Contre-exemple gelé : la racine de l'arbre PRINCIPAL en tête du `sys.path` d'un worktree, en DEUX graphies (antislashs,
puis barres obliques à « c: » minuscule) — la forme exacte relevée par la session E34 le 2026-09-28. Les témoins
exercent d'abord les fonctions pures (racines injectées, disposition réelle : les worktrees SOUS la racine principale),
puis la vraie garde sur un dépôt git JETABLE : un pytest interne qu'elle doit REFUSER (code 4, écrivain nommé), sa
spécificité, et un COMMIT d'essai depuis un worktree dont le crochet lance pytest — la couverture par le crochet.

Tout sous-processus git et pytest retire `GIT_*` (règle à deux faces, E5 : ces dépôts ne sont pas le dépôt courant) et
`PYTHONPATH` ; un `pytest.ini` est posé à la racine de chaque arbre interne (sans lui, la collecte remonte le Temp)."""
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

_ICI = pathlib.Path(__file__).resolve().parents[2]
_GA_CHEMIN = _ICI / "tests" / "garde_arbres.py"


def _charger(chemin=_GA_CHEMIN, nom="_ga_temoin_p2142"):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


GA = _charger()


def _env_propre():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("PYTHONPATH", None)
    return env


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), env=_env_propre(), capture_output=True, text=True, check=True)


# --- fonctions pures : racines injectées ------------------------------------------------------------------------------
@pytest.fixture
def arbres(tmp_path):
    """Un faux dépôt, sans git : la racine principale et deux worktrees SOUS elle (la disposition réelle)."""
    principal = tmp_path / "AGAGI"
    w1, w2 = principal / ".worktrees" / "w1", principal / ".worktrees" / "w2"
    for d in (principal / "tools", w1 / "tools", w2 / "tools"):
        d.mkdir(parents=True)
    racines = sorted({GA._norm(str(p)) for p in (principal, w1, w2)}, key=len, reverse=True)
    return principal, w1, w2, racines


def test_P2_142_CONTRE_EXEMPLE_la_racine_principale_en_DEUX_graphies_est_ETRANGERE_depuis_un_worktree(arbres):
    principal, w1, _w2, racines = arbres
    antislashs = str(principal)
    obliques = str(principal).replace("\\", "/")
    obliques = obliques[0].lower() + obliques[1:]             # « c: » minuscule, comme relevé par E34
    sys_path = [antislashs, obliques, str(w1), sys.base_prefix]
    assert GA.entrees_etrangeres(sys_path, GA._norm(str(w1)), racines) == [antislashs, obliques]


def test_P2_142_SPECIFICITE_l_arbre_courant_ses_sous_dossiers_et_le_hors_depot_ne_sont_PAS_etrangers(arbres):
    principal, w1, _w2, racines = arbres
    sys_path = [str(w1), str(w1 / "tests"), str(w1 / "tools"), sys.base_prefix, str(principal.parent)]
    assert GA.entrees_etrangeres(sys_path, GA._norm(str(w1)), racines) == []


def test_P2_142_IMBRICATION_la_racine_la_plus_LONGUE_gagne_et_un_worktree_frere_est_etranger(arbres):
    principal, w1, w2, racines = arbres
    assert GA.proprietaire(str(w1 / "tools"), racines) == GA._norm(str(w1))     # pas la racine principale
    assert GA.entrees_etrangeres([str(w2)], GA._norm(str(w1)), racines) == [str(w2)]
    # depuis l'arbre PRINCIPAL : un worktree est étranger, la racine principale ne l'est pas
    assert GA.entrees_etrangeres([str(w1), str(principal)], GA._norm(str(principal)), racines) == [str(w1)]


def test_P2_142_CWD_une_entree_vide_ou_relative_suit_le_cwd_vers_l_autre_arbre(arbres):
    principal, w1, _w2, racines = arbres
    ici = GA._norm(str(w1))
    assert GA.entrees_etrangeres(["", "."], ici, racines, cwd=str(principal)) == ["", "."]
    assert GA.entrees_etrangeres(["", "."], ici, racines, cwd=str(w1)) == []


def test_P2_142_CONSOMMATION_le_module_tools_charge_depuis_l_autre_arbre_est_NOMME(arbres):
    principal, w1, _w2, racines = arbres

    class _M:
        pass

    dehors, dedans, paquet = _M(), _M(), _M()
    dehors.__file__ = str(principal / "tools" / "slot_identity.py")
    dedans.__file__ = str(w1 / "tools" / "grid_compare.py")
    paquet.__path__ = [str(principal / "tools"), str(w1 / "tools")]   # espace de noms : le PREMIER chemin gagne
    mods = {"tools.slot_identity": dehors, "tools.grid_compare": dedans, "tools": paquet, "numpy": _M()}
    assert [n for n, _ in GA.modules_etrangers(mods, GA._norm(str(w1)), racines)] == ["tools", "tools.slot_identity"]


# --- la vraie garde, sur un dépôt git JETABLE ------------------------------------------------------------------------
@pytest.fixture
def depot_reel(tmp_path):
    """Un dépôt git jetable et un worktree SOUS sa racine (.worktrees/b), comme celui du projet."""
    principal = tmp_path / "depot"
    principal.mkdir()
    _git("init", "-q", "-b", "main", cwd=principal)
    (principal / "LISEZMOI").write_text("x\n", encoding="utf-8")
    _git("add", "LISEZMOI", cwd=principal)
    _git("-c", "user.name=T", "-c", "user.email=t@e.x", "commit", "-q", "-m", "init", cwd=principal)
    wt = principal / ".worktrees" / "b"
    _git("worktree", "add", "-q", str(wt), "-b", "b", cwd=principal)
    return principal, wt


def test_P2_142_racines_du_depot_voit_l_arbre_principal_et_son_worktree_REELS(depot_reel):
    principal, wt = depot_reel
    racines = GA.racines_du_depot(str(wt))
    assert racines is not None and set(racines) == {GA._norm(str(principal)), GA._norm(str(wt))}
    assert racines[0] == GA._norm(str(wt))                    # la plus LONGUE d'abord


_COLLE = '''import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("_garde_arbres_p2142", pathlib.Path(__file__).with_name("garde_arbres.py"))
_GA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_GA)
pytest_sessionstart = _GA.pytest_sessionstart
pytest_report_header = _GA.pytest_report_header
pytest_collection_finish = _GA.pytest_collection_finish
pytest_runtest_setup = _GA.pytest_runtest_setup
pytest_runtest_teardown = _GA.pytest_runtest_teardown
'''


def _armer(arbre, nom_test, cible):
    """Arme `arbre` avec la VRAIE garde (copiée de cet arbre-ci) et un test qui insère `cible` dans sys.path."""
    (arbre / "tests").mkdir(exist_ok=True)
    (arbre / "tests" / "garde_arbres.py").write_bytes(_GA_CHEMIN.read_bytes())
    (arbre / "tests" / "conftest.py").write_text(_COLLE, encoding="utf-8")
    (arbre / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (arbre / "tests" / f"{nom_test}.py").write_text(
        f"import sys\n\n\ndef {nom_test}():\n    sys.path.insert(0, {cible!r})\n", encoding="utf-8")


def _pytest(arbre, *args):
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *args], cwd=str(arbre),
                          env=_env_propre(), capture_output=True, text=True, timeout=300)


def test_P2_142_TEMOIN_la_garde_REFUSE_un_test_qui_met_l_autre_arbre_dans_sys_path(depot_reel):
    principal, wt = depot_reel
    _armer(wt, "test_intrus", str(principal).replace("\\", "/"))
    r = _pytest(wt, "tests/test_intrus.py")
    sortie = r.stdout + r.stderr
    assert r.returncode == 4, sortie
    assert "REFUS (garde des arbres, P2.142)" in sortie
    assert "test_intrus" in sortie                            # l'écrivain est NOMMÉ


def test_P2_142_SPECIFICITE_la_garde_laisse_passer_un_test_qui_ajoute_SON_propre_arbre(depot_reel):
    _principal, wt = depot_reel
    _armer(wt, "test_sage", str(wt / "tests"))
    r = _pytest(wt, "tests/test_sage.py")
    assert r.returncode == 0, r.stdout + r.stderr


# --- P2.152 : l'UNIQUE crochet de collecte du conftest et ses trois fonctions nommées --------------------------------
_CONFTEST = _ICI / "tests" / "conftest.py"


class _Item:
    def __init__(self, *marques):
        self.marques = {m.name: m for m in marques}

    def get_closest_marker(self, nom):
        return self.marques.get(nom)

    def add_marker(self, m):
        self.marques[m.mark.name if hasattr(m, "mark") else m.name] = getattr(m, "mark", m)


class _Config:
    def __init__(self, delai_cli=None, delai_ini=None):
        self.cli, self.ini = delai_cli, delai_ini

    def getoption(self, nom, defaut=None):
        return self.cli if nom == "timeout" else defaut

    def getini(self, nom):
        if nom != "timeout" or self.ini is None:
            raise ValueError(nom)
        return self.ini


def test_P2_152_les_delais_slow_RESSUSCITES_relevent_le_defaut_sans_jamais_REDUIRE():
    C = _charger(_CONFTEST, "_conftest_temoin_p2152")

    def lot():
        return [_Item(pytest.mark.slow.mark), _Item(), _Item(pytest.mark.slow.mark, pytest.mark.timeout(30).mark)]

    items = lot()
    assert C._delais_slow(_Config(delai_ini="120"), items) == 1           # le défaut du pytest.ini : relevé à 600 s
    assert items[0].get_closest_marker("timeout").args == (600,)
    assert items[1].get_closest_marker("timeout") is None                  # non @slow : intact
    assert items[2].get_closest_marker("timeout").args == (30,)            # délai explicite du test : intact
    for cfg in (_Config(delai_cli=900), _Config(delai_cli=0), _Config(), None):   # CI 900, illimité, rien : intacts
        items = lot()
        assert C._delais_slow(cfg, items) == 0 and items[0].get_closest_marker("timeout") is None


_SONDE = '''import json, os
def pytest_collection_finish(session):
    out = {}
    for it in session.items:
        t, s = it.get_closest_marker("timeout"), it.get_closest_marker("skip")
        out[it.name] = {"timeout": list(t.args) if t else None, "skip": (s.kwargs.get("reason") if s else None)}
    with open(os.environ["SONDE_COLLECTE"], "w", encoding="utf-8") as fh:
        json.dump(out, fh)
'''


def _armer_conftest_reel(arbre):
    """L'arbre reçoit le VRAI conftest et la VRAIE garde, plus un bail étranger SIMULÉ (jamais un vrai bail : le
    répertoire des bails est commun à la flotte) et trois tests : lent, de monde, simple."""
    (arbre / "tests").mkdir(exist_ok=True)
    (arbre / "tests" / "garde_arbres.py").write_bytes(_GA_CHEMIN.read_bytes())
    (arbre / "tests" / "conftest.py").write_text(
        _CONFTEST.read_text(encoding="utf-8") + '\n\n_foreign_kuzu_holder = lambda: "temoin (pid=1)"\n',
        encoding="utf-8")
    (arbre / "pytest.ini").write_text("[pytest]\ntimeout = 120\n", encoding="utf-8")
    (arbre / "sonde_collecte.py").write_text(_SONDE, encoding="utf-8")
    (arbre / "tests" / "test_lent.py").write_text(
        "import pytest\n\n\n@pytest.mark.slow\ndef test_lent():\n    pass\n", encoding="utf-8")
    (arbre / "tests" / "test_monde.py").write_text(
        "def test_monde():\n    assert 'Biosphere'\n", encoding="utf-8")
    (arbre / "tests" / "test_simple.py").write_text("def test_simple():\n    pass\n", encoding="utf-8")


def test_P2_152_TROIS_EFFETS_sur_une_collecte_REELLE_delais_slow_garde_de_bail_garde_des_arbres(depot_reel, tmp_path):
    principal, wt = depot_reel
    _armer_conftest_reel(wt)
    sortie_json = tmp_path / "collecte.json"
    env = dict(_env_propre(), PYTHONPATH=str(wt), SONDE_COLLECTE=str(sortie_json))
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "-p", "sonde_collecte", "tests/test_lent.py", "tests/test_monde.py", "tests/test_simple.py"],
                       cwd=str(wt), env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    import json
    vu = json.loads(sortie_json.read_text(encoding="utf-8"))
    assert vu["test_lent"]["timeout"] == [600]                             # effet 1 : les délais @slow
    assert "temoin (pid=1)" in (vu["test_monde"]["skip"] or "")            # effet 2 : la garde de bail
    assert vu["test_simple"] == {"timeout": None, "skip": None}
    # effet 3 : la garde des arbres, dans la MÊME collecte, dès qu'un module de test importe l'autre arbre
    (wt / "tests" / "test_intrus_collecte.py").write_text(
        f"import sys\nsys.path.insert(0, {str(principal).replace(chr(92), '/')!r})\n\n\ndef test_x():\n    pass\n",
        encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "-p", "sonde_collecte", "tests/"], cwd=str(wt), env=env, capture_output=True, text=True,
                       timeout=300)
    sortie = r.stdout + r.stderr
    assert r.returncode == 4 and "pendant la COLLECTE" in sortie, sortie


def test_P2_142_COUVERTURE_un_commit_d_essai_depuis_le_worktree_est_REFUSE_par_le_crochet(depot_reel):
    """Le crochet pre-commit lance pytest depuis le worktree du commit, git exportant ses GIT_* au crochet : la garde de
    CE worktree s'applique, et le commit est refusé. Le crochet est désigné par -c core.hooksPath, jamais hérité."""
    principal, wt = depot_reel
    _armer(wt, "test_intrus", str(principal).replace("\\", "/"))
    crochets = principal / ".git" / "hooks"
    crochets.mkdir(exist_ok=True)
    py = sys.executable.replace("\\", "/")
    crochet = crochets / "pre-commit"
    crochet.write_text(f'#!/bin/sh\nexec "{py}" -m pytest -q -p no:cacheprovider tests/test_intrus.py\n',
                       encoding="utf-8", newline="\n")
    crochet.chmod(0o755)
    (wt / "fichier.txt").write_text("y\n", encoding="utf-8")
    _git("add", "fichier.txt", cwd=wt)
    avant = _git("rev-parse", "HEAD", cwd=wt).stdout.strip()
    r = subprocess.run(["git", "-c", f"core.hooksPath={crochets.as_posix()}", "-c", "user.name=T",
                        "-c", "user.email=t@e.x", "commit", "-q", "-m", "essai"],
                       cwd=str(wt), env=_env_propre(), capture_output=True, text=True, timeout=300)
    sortie = r.stdout + r.stderr
    assert r.returncode != 0, "le commit est PASSÉ : la garde n'a pas couvert le pytest du crochet\n" + sortie
    assert "REFUS (garde des arbres, P2.142)" in sortie
    assert _git("rev-parse", "HEAD", cwd=wt).stdout.strip() == avant, "un commit a été créé malgré le refus"
