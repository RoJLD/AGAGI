# tests/test_strategy.py
import gc

from fastapi.testclient import TestClient


def _empty_schema_db(tmp_path):
    """KuzuDB temp avec le schéma (Article/WorldVersion/...) mais AUCUNE donnée de stratégie."""
    from src.graph_rag.experiment_tracker import ExperimentGraph
    db_path = str(tmp_path / "strat.db")
    g = ExperimentGraph(db_path, read_only=False)   # bootstrap schema, pas de WorldVersion
    del g.conn
    del g.db
    gc.collect()
    return db_path


def test_strategy_tree_is_empty_on_schema_only_db(tmp_path, monkeypatch):
    """DB avec schéma mais sans run => source DOIT être 'empty' (honnête), pas 'error'.

    Régression historique : la table optionnelle Hyperparameters/HAS_HYPERPARAMETERS
    était créée paresseusement dans log_hyperparameters(), donc absente d'une DB fraîche.
    La requête /strategy_tree levait 'Binder exception: Table Hyperparameters does not
    exist' et retombait en source='error'. Ce test échoue si ce bug régresse.
    """
    db_path = _empty_schema_db(tmp_path)
    from backend.app.services.kuzu_service import kuzu_service
    monkeypatch.setattr(kuzu_service, "db_path", db_path)
    from backend.app.main import app
    client = TestClient(app)
    body = client.get("/api/strategy/strategy_tree").json()
    # plus AUCUN mock fantôme
    assert "StoneAge (Mock)" not in str(body)
    assert "Tabula_Rasa" not in str(body)
    # flag de source STRICT : DB schema-only sans run == empty (et surtout PAS error)
    assert body["source"] == "empty", body
    assert body["tree"] == {} and body["sankey"]["nodes"] == []


def test_strategy_tree_is_error_on_invalid_db(tmp_path, monkeypatch):
    """Vraie erreur (chemin de DB invalide / inouvrable) => source DOIT être 'error'.

    Cas distinct de 'empty' : ici l'ouverture de KuzuDB échoue réellement. Le flag source
    ne doit PAS mentir en disant 'empty' alors qu'une vraie erreur s'est produite.
    """
    # Un fichier régulier (pas un répertoire de DB Kuzu) => ouverture impossible.
    bad_path = tmp_path / "not_a_db"
    bad_path.write_text("garbage, not a kuzu database")

    from backend.app.services.kuzu_service import kuzu_service
    monkeypatch.setattr(kuzu_service, "db_path", str(bad_path))
    from backend.app.main import app
    client = TestClient(app)
    body = client.get("/api/strategy/strategy_tree").json()
    assert body["source"] == "error", body
    assert body["tree"] == {} and body["sankey"]["nodes"] == []
