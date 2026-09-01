"""Fixtures partagées des tests.

Les tests `tests/test_backend.py` interrogent les endpoints `/api/experiments`, qui lisent le dossier
`results/`. Or `results/` est GITIGNORÉ (`.gitignore`), donc ABSENT en CI propre -> les endpoints
renvoyaient 404 / crashaient (`max()` sur vide). C'était la dette CI.

Remède : rendre les tests backend SELF-CONTAINED en pointant le service vers des fixtures versionnées
(`tests/fixtures/results/`), sans jamais toucher au vrai `results/`. Tolérant : si le backend n'est pas
importable (run sandbox-only sans deps backend), la fixture ne fait rien.

Garde-fou pour ne pas re-accumuler la dette : `.githooks/pre-push` (lance les tests CI avant push).
"""
import pathlib

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: test lent (lance la biosphere), deselectionne par defaut en CI rapide")


def pytest_collection_modifyitems(config, items):
    """Garde-fou anti-hang (P1.1, 2026-07-22) : le timeout global de 120 s (pytest.ini) catche les hangs
    de la CI RAPIDE, mais couperait les tests `@slow` légitimement longs (edr114 = 270 s). On leur donne
    donc 600 s automatiquement (assez pour tout lent légitime, catche quand même un vrai infini), sauf
    si le test porte déjà un `@pytest.mark.timeout(N)` explicite. Résultat : `pytest -m slow` marche
    sans `--timeout=0`, et un slow qui HANGE pour de bon échoue quand même (à 600 s)."""
    for item in items:
        if item.get_closest_marker("slow") and item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(600))

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


def pytest_collection_modifyitems(config, items):  # noqa: F811 — complète le hook ci-dessus
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
