"""Fixtures partagées des tests.

Les tests `tests/test_backend.py` interrogent les endpoints `/api/experiments`, qui lisent le dossier
`results/`. Or `results/` est GITIGNORÉ (`.gitignore`), donc ABSENT en CI propre -> les endpoints
renvoyaient 404 / crashaient (`max()` sur vide). C'était la dette CI.

Remède : rendre les tests backend SELF-CONTAINED en pointant le service vers des fixtures versionnées
(`tests/fixtures/results/`), sans jamais toucher au vrai `results/`. Tolérant : si le backend n'est pas
importable (run sandbox-only sans deps backend), la fixture ne fait rien.

Garde-fou pour ne pas re-accumuler la dette : `.githooks/pre-push` (lance les tests CI avant push).
"""
import os
import pathlib

import pytest


# ----------------------------------------------------------------------------------------------------
# GARDE DES ARBRES (P2.142, 2026-09-29) — aucune entrée de sys.path ne pointe vers un AUTRE arbre du dépôt, et aucun
# module tools.* / src.* n'en est chargé : sinon un test de worktree peut passer au VERT en exerçant le code d'un autre
# arbre (E35). Tout est dans tests/garde_arbres.py, chargé ici par CHEMIN — jamais par `import tools…`, pour ne pas
# dépendre du paquet qu'elle surveille. Ses crochets sont EXPOSÉS comme attributs de ce module (pytest ne lit que ceux-
# là) : ⚠️ ne jamais redéfinir plus bas un crochet du même nom — une seconde définition REMPLACE la première sans un mot.
def _charger_garde_arbres():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_garde_arbres_p2142",
                                                  pathlib.Path(__file__).with_name("garde_arbres.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_GARDE_ARBRES = _charger_garde_arbres()
pytest_sessionstart = _GARDE_ARBRES.pytest_sessionstart
pytest_report_header = _GARDE_ARBRES.pytest_report_header
pytest_runtest_setup = _GARDE_ARBRES.pytest_runtest_setup
pytest_runtest_teardown = _GARDE_ARBRES.pytest_runtest_teardown
# (le contrôle de COLLECTE passe par l'unique pytest_collection_modifyitems, plus bas : _GARDE_ARBRES.controle_collecte)


@pytest.fixture(autouse=True)
def _env_git_neutralise(monkeypatch):
    """⚠️ **Aucun test ne voit les variables `GIT_*` de son appelant** — E5, DEUX occurrences le même jour.

    Pendant tout `git commit`, git EXPORTE `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE`… vers le hook
    pre-commit et, de là, vers TOUS ses sous-processus — donc vers `pytest` quand le hook lance le harnais
    de mutation. Un test qui croit travailler sur un dépôt jetable travaille alors sur le dépôt RÉEL :
    `git init` hérité d'un `GIT_DIR` sans `GIT_WORK_TREE` **réinitialise le dépôt pointé et y pose
    `core.bare = true`** — quand ce `GIT_DIR` ne finit pas par « /.git », ce qui est le cas du gitdir d'un
    WORKTREE, la forme que git exporte quand on committe depuis un worktree (depuis l'arbre principal il est
    absent) ; mesuré sur Linux et Windows le 2026-09-26, P2.121 famille 6 — (mesuré deux fois — le 2026-09-23 vers 20:03 et le 2026-09-24 à 13:30:13 ; dans
    les deux cas `git status` a rendu « must be run in a work tree » pour TOUTES les sessions, et seule la
    plomberie passait encore). Le `git config user.email` qui suit un tel init écrase de plus l'identité du
    dépôt réel : c'est le mécanisme des commits signés `Test <test@example.com>` de P2.86.

    Trois décisions, toutes payées :
      * **Toute la famille `GIT_*`, jamais une énumération.** Deux correctifs successifs n'ont listé que
        `GIT_INDEX_FILE` et ont laissé passer `GIT_DIR` — c'est l'énumération qui a échoué, pas l'idée.
      * **Portée FONCTION, pas session.** Une fixture de session nettoie l'environnement HÉRITÉ une seule
        fois ; elle ne protège pas du second chemin, un test qui pose `os.environ["GIT_DIR"]` sans
        `monkeypatch` et empoisonne tous les tests suivants de la même exécution. Coût nul.
      * **`monkeypatch` plutôt qu'une mutation directe** : l'environnement est restauré après chaque test,
        et un test qui a BESOIN d'une de ces variables la pose lui-même (`monkeypatch.setenv`) — la fixture
        nettoie AVANT, elle ne l'empêche pas.

    ⚠️ **Réserve honnête : ceci ne ferme pas la classe, seulement sa surface `pytest`.** Un script lancé à
    la main pendant un hook, ou un sous-processus qui reconstruit son environnement avec un `env=` explicite,
    garde la fuite. Et le SITE qui a réellement emprunté le trou le 2026-09-24 n'est pas identifié à ce jour
    (P2.107) : cette fixture supprime la classe d'accidents, elle ne dispense pas de le trouver.
    Contre-exemple gelé : `tests/sandbox/test_git_env_leak.py`.
    """
    for nom in [k for k in os.environ if k.startswith("GIT_")]:
        monkeypatch.delenv(nom, raising=False)


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: test lent (lance la biosphere), deselectionne par defaut en CI rapide")


_DELAI_SLOW_S = 600


def _delai_global(config):
    """Le délai par test EFFECTIF de pytest-timeout : la ligne de commande (--timeout), sinon le pytest.ini ; None si
    aucun n'est lisible (plugin absent, config absente)."""
    if config is None:
        return None
    v = config.getoption("timeout", None)
    if v is None:
        try:
            v = config.getini("timeout")
        except (ValueError, KeyError):
            v = None
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _delais_slow(config, items):
    """Garde-fou anti-hang (P1.1, 2026-07-22) : le timeout global de 120 s (pytest.ini) catche les hangs de la CI
    RAPIDE, mais couperait les tests `@slow` légitimement longs (edr114 = 270 s). On leur donne 600 s, sauf s'ils
    portent un `@pytest.mark.timeout(N)` explicite — et un slow qui HANGE pour de bon échoue quand même (à 600 s).

    ⚠️ MORT du 2026-09-01 au 2026-09-29 (P2.152) : cette logique était un SECOND `pytest_collection_modifyitems`,
    et la définition de la garde de bail, plus bas, portant le même nom, le REMPLAÇAIT sans un mot (E32). Ressuscitée
    comme fonction NOMMÉE, appelée par l'unique crochet de collecte. Et bornée, pour ne rien RÉDUIRE : elle ne relève
    que le délai PAR DÉFAUT (sous 600 s) ; un délai explicite plus long (la CI passe --timeout=900) ou l'illimité
    (--timeout=0, la voie documentée de `pytest -m slow`) restent tels quels — un marqueur l'emporterait sur eux.
    Rend le nombre de tests relevés."""
    g = _delai_global(config)
    if g is None or g <= 0 or g >= _DELAI_SLOW_S:
        return 0
    n = 0
    for item in items:
        if item.get_closest_marker("slow") and item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(_DELAI_SLOW_S))
            n += 1
    return n


_FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "experiments"


@pytest.fixture(autouse=True)
def _experiments_use_fixtures():
    """Pointe le service /api/experiments vers les fixtures versionnées le temps de chaque test."""
    try:
        from backend.app.routes import experiments
    except Exception:
        # Backend non importable (ex. run sandbox-only) : rien à faire.
        yield
        return

    original = experiments.service.results_path
    experiments.service.results_path = _FIXTURES
    try:
        yield
    finally:
        experiments.service.results_path = original


# ----------------------------------------------------------------------------------------------------
# GARDE DE BAIL (classe E10, occurrence 7 — commise le 2026-09-01 par la session qui écrit ces lignes)
#
# CLAUDE.md dit « toute simulation de monde doit tenir la ressource `kuzu` », et `tools/jobs` rend deux
# RUNS concurrents impossibles. Mais **la SUITE DE TESTS ne prend aucun bail** : rien n'empêchait de
# lancer les tests de calibration pendant qu'une expérience détenait `kuzu`. Mesuré : 4 tests simulant
# un monde ont échoué (`test_perception_ablation_*`, `test_linear_sanity_*`) pendant EVO-026-bis.
# Règle documentée sans application exécutable = règle violée : c'est la définition de la classe E10.
#
# ⚠️ CHOIX DE CONCEPTION — SKIP, jamais un faux vert. Ces tests sont marqués SKIPPED avec une raison qui
# NOMME le détenteur. Les faire « passer » en les neutralisant fabriquerait la classe E4 (vérification
# vide) qu'on corrige ailleurs ; les faire échouer en masse noierait un vrai échec. Un test sauté est
# VISIBLE dans le rapport, et sa raison dit quoi faire : attendre la fin du run, ou le tuer.
#
# L'heuristique de détection est volontairement large, et son asymétrie est BÉNIGNE : un faux positif
# saute un test pendant qu'un run est en vol (sans danger — il sera rejoué après), un faux négatif
# laisse le statu quo. Ce n'est pas le cas d'un cliquet, où un faux positif crée du bruit permanent.
_WORLD_HINTS = (
    "Biosphere", "_setup_lewis", "MambaAgent", "world_1_stoneage", "lewis_world",
    "_torch_survival_eras", "_mamba_survival_eras", "run_linear_sanity", "ground_truth_worlds",
)


def _foreign_kuzu_holder():
    """Détenteur d'un bail `kuzu` VIVANT qui n'est ni nous ni un ancêtre — sinon None."""
    import os
    try:
        from tools.jobs import doctor as _doctor
        etat = _doctor.classify_leases()
        protege = set(_doctor._protected_pids()) | {os.getpid()}
    except Exception:
        return None                     # module absent ou illisible : ne rien bloquer, ne rien prétendre
    for lz in etat.get("live", []):
        if getattr(lz, "resource", None) != "kuzu":
            continue
        if getattr(lz, "pid", None) in protege:
            continue                    # c'est nous : ne pas s'auto-bloquer
        return f"{getattr(lz, 'owner', None) or '?'} (pid={getattr(lz, 'pid', '?')})"
    return None


def _garde_de_bail(items):
    """La garde de bail à la COLLECTE (E10 occ. 7). Fonction NOMMÉE depuis P2.152 : elle était définie comme un second
    `pytest_collection_modifyitems` (« noqa: F811 — complète le hook ci-dessus ») et REMPLAÇAIT celui des délais @slow
    — Python ne complète pas une fonction, il la rebinde."""
    detenteur = _foreign_kuzu_holder()
    if not detenteur:
        return
    raison = (f"bail « kuzu » détenu par {detenteur} : une simulation de monde concurrente contamine "
              f"silencieusement la mesure (classe E10). Attendre la fin du run, ou le tuer via "
              f"`python -m tools.jobs.doctor`.")
    n = 0
    for item in items:
        src = ""
        mod = getattr(item, "module", None)
        # ⚠️ EXEMPTION DÉCLARÉE. Défaut trouvé en écrivant les tests de cette garde : ils MENTIONNENT
        # les symboles de monde (dans des chaînes de fixture) sans jamais en simuler un, donc la garde
        # sautait SES PROPRES TESTS — elle devenait invérifiable exactement quand elle agit. Un module
        # peut se déclarer exempt ; c'est explicite et relisible, là où une exception sur le nom de
        # fichier serait une devinette de plus.
        if getattr(mod, "_LEASE_GUARD_EXEMPT", False):
            continue
        f = getattr(mod, "__file__", None)
        if f:
            try:
                src = open(f, encoding="utf-8", errors="ignore").read()
            except OSError:
                src = ""
        if any(h in src for h in _WORLD_HINTS):
            item.add_marker(pytest.mark.skip(reason=raison))
            n += 1
    if n:
        print(f"\n⚠️  GARDE DE BAIL : {n} test(s) simulant un monde SAUTÉS — {detenteur} tient « kuzu ».")
    _arm_runtime_net(raison)


def pytest_collection_modifyitems(config, items):
    """L'UNIQUE crochet de collecte de ce conftest (P2.152, 2026-09-29). Trois fonctions NOMMÉES, chacune testable
    seule : les délais @slow, la garde de bail, la garde des arbres (P2.142). ⚠️ Ne JAMAIS redéfinir ce nom plus bas : une
    seconde définition remplace la première sans un mot — c'est ainsi que les délais @slow sont restés morts quatre
    semaines. Témoin : `tests/sandbox/test_garde_arbres.py`, les trois effets sur une collecte réelle."""
    _delais_slow(config, items)
    _garde_de_bail(items)
    _GARDE_ARBRES.controle_collecte()


_NET = {"armed": False, "orig": None}


try:
    from tools.jobs.lease import ResourceBusy as _ResourceBusy
except Exception:                                   # noqa: BLE001 — module absent : la garde ne convertit rien
    class _ResourceBusy(Exception):
        """Substitut jamais levé : sans `tools.jobs`, aucun bail n'existe."""


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    """P2.82 (2026-09-23) — GARDE À LA PRISE. Un test qui prend `hold("kuzu")` LUI-MÊME sans porter d'indice
    de monde échappe à la garde de collecte, et `ResourceBusy` (bail détenu par un run étranger) devenait
    FAIL — mesuré : 2 rouges de `test_s2_ablation_real_path.py` dans la suite de nuit du PM sous le bail de
    P4.16. Un test qui tient un bail est par définition un test de monde : la même issue que la garde de
    collecte, au MÉCANISME (la prise) plutôt qu'à l'heuristique (un indice de plus). Toute autre exception
    passe inchangée (spécificité, `test_lease_skip_guard.py`)."""
    try:
        return (yield)
    except _ResourceBusy as exc:
        pytest.skip(f"[garde de bail, prise] {exc} — un run tient la ressource : attendre sa fin, ou "
                    f"python -m tools.jobs.doctor (P2.82)")


def _skip_si_bail_etranger():
    """La DÉCISION de la fixture `sans_bail_etranger`, isolée pour être calibrée sans monde."""
    detenteur = _foreign_kuzu_holder()
    if detenteur:
        pytest.skip(f"[garde de bail, fixture] bail « kuzu » détenu par {detenteur} : ce test sert un monde "
                    f"dans une app ASGI, où un Skipped levé côté serveur deviendrait un RuntimeError (P2.82)")


@pytest.fixture
def sans_bail_etranger():
    """P2.82 (2026-09-23) — le skip se décide DANS LE TEST, jamais dans le code servi. Les tests backend qui
    construisent un monde à travers l'app ASGI (`test_flatland_runs_crud`, `test_ws_flatland_run_id_streams_frames`)
    voyaient le `Skipped` du filet runtime traverser Starlette et ressortir en « RuntimeError: No response
    returned » = FAIL (mesuré sous le bail de P4.16). Prendre cette fixture décide le skip AVANT la requête."""
    _skip_si_bail_etranger()


def _arm_runtime_net(raison):
    """P2.69 (ii), 2026-09-15 — FILET RUNTIME de la garde de bail. L'heuristique textuelle ci-dessus
    devine ; mesuré ce jour : **58 fichiers** de tests importent un module qui construit un monde SANS
    porter un indice (`test_p_reach_deconfound.py` via `_measure_forage`, `test_s2_ablation_real_path.py`
    via `run_ablation_map`, …) — pendant le run P4.9, 503 tests simulant un monde ont TOURNÉ. Ajouter un
    indice de plus ne ferme pas la classe ; intercepter le MÉCANISME la ferme : quand un bail étranger
    est détenu, la CONSTRUCTION d'un monde (`Biosphere3D.__init__`, dont héritent soup / agricultural /
    industrial / famine / ground-truth, et sur lequel Lewis est monté) SAUTE le test qui la tente — au
    point exact, avec la même raison. Importé ici seulement quand un bail est pris (sinon rien n'est
    touché, et le coût est nul). Restaurable par `_disarm_runtime_net()` (tests de la garde)."""
    if _NET["armed"]:
        return
    try:
        from src.worlds.world_1_stoneage import Biosphere3D
    except Exception:                               # noqa: BLE001 — monde inimportable : rien à filtrer
        return
    orig = Biosphere3D.__init__

    def __init__(self, *a, **k):
        pytest.skip("[filet runtime] " + raison)

    __init__._lease_net = True
    Biosphere3D.__init__ = __init__
    _NET.update(armed=True, orig=orig)


def _disarm_runtime_net():
    if not _NET["armed"]:
        return
    from src.worlds.world_1_stoneage import Biosphere3D
    Biosphere3D.__init__ = _NET["orig"]
    _NET.update(armed=False, orig=None)
