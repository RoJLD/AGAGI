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
