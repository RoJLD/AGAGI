"""G1 (north-star) : soup câblé dans WORLD_FACTORY pour le transfert soup->stoneage.

Vérifie le câblage ET la compatibilité d'interface (le vrai SoupWorld hérite du moteur canonique
Biosphere3D -> add_agent(model), PAS l'interface legacy add_agent(genome)). Non-régression : la ladder
par défaut et les clés existantes restent intactes.
Spec : docs/superpowers/specs/2026-06-29-G1-Soup-Stoneage-Transfer-design.md (section 4, 7)."""
from main_curriculum import WORLD_FACTORY, DEFAULT_LADDER
from src.worlds.world_0_soup import SoupWorld
from src.worlds.world_1_stoneage import Biosphere3D


def test_soup_is_wired_into_world_factory():
    assert WORLD_FACTORY["soup"] is SoupWorld


def test_soup_uses_canonical_model_add_agent_not_legacy_genome():
    # Le moteur canonique (Biosphere3D) expose add_agent(model). SoupWorld DOIT en hériter
    # (EDR 033) -> sinon le curriculum (qui passe un MambaAgent) casserait.
    assert SoupWorld.add_agent is Biosphere3D.add_agent


def test_default_ladder_and_existing_keys_unchanged():
    # Non-régression : l'ajout de soup est purement additif.
    assert DEFAULT_LADDER == ["stoneage", "agricultural", "industrial"]
    for k in ("stoneage", "agricultural", "industrial"):
        assert k in WORLD_FACTORY
