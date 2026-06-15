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
