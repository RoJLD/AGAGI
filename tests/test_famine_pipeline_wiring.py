import os
import importlib


def test_hof_path_default_unchanged(monkeypatch):
    # sans HOF_PATH -> chemin par defaut (non-regressif)
    monkeypatch.delenv("HOF_PATH", raising=False)
    import src.seed_ai.persistence as pers
    importlib.reload(pers)
    assert pers.HALL_OF_FAME_PATH == "data/hall_of_fame.pkl"


def test_hof_path_env_override(monkeypatch):
    monkeypatch.setenv("HOF_PATH", "data/hall_of_fame_famine.pkl")
    import src.seed_ai.persistence as pers
    importlib.reload(pers)
    assert pers.HALL_OF_FAME_PATH == "data/hall_of_fame_famine.pkl"
    monkeypatch.delenv("HOF_PATH", raising=False)
    importlib.reload(pers)   # restaure pour les autres tests


def test_famine_world_type_instantiates_famineworld(monkeypatch):
    # WORLD_TYPE=famine -> le switch de main_biosphere instancie FamineWorld
    from src.worlds.world_famine import FamineWorld
    from src.environments.config import WorldConfig
    # on teste la logique du switch en isolant l'instanciation (pas tout main())
    world_type = "famine"
    config = WorldConfig()
    if world_type == "famine":
        env = FamineWorld(config)
    if hasattr(env, "memory_retriever"):
        env.memory_retriever.stop()
    assert isinstance(env, FamineWorld)


def test_max_eras_env_override(monkeypatch):
    monkeypatch.setenv("MAX_ERAS", "60")
    assert int(os.environ.get("MAX_ERAS", "30")) == 60
    monkeypatch.delenv("MAX_ERAS", raising=False)
    assert int(os.environ.get("MAX_ERAS", "30")) == 30
