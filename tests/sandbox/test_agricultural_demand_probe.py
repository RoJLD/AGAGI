"""Tests du probe de demande agricole (world 2) : verdict pur + saisons + fait statique world 3."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.agricultural_demand_probe import agri_verdict, _season_of_tick
from src.worlds.world_1_stoneage import Biosphere3D
from src.worlds.world_3_industrial import IndustrialWorld


def test_verdict_cosmetic_when_no_planting():
    assert agri_verdict(max_planted=0, max_fruit=0) == "AGRICULTURE_COSMETIC"


def test_verdict_chain_incomplete_when_planted_but_no_fruit():
    assert agri_verdict(max_planted=3, max_fruit=0) == "CHAIN_INCOMPLETE"


def test_verdict_active_when_fruit_produced():
    assert agri_verdict(max_planted=3, max_fruit=2) == "AGRICULTURE_ACTIVE"


def test_season_cycle():
    assert _season_of_tick(1) == "spring"
    assert _season_of_tick(50) == "spring"
    assert _season_of_tick(51) == "summer"
    assert _season_of_tick(151) == "winter"
    assert _season_of_tick(201) == "spring"     # cycle boucle


def test_world3_is_stoneage_in_disguise():
    # fait statique : world 3 industriel = sous-classe de stoneage (pollution ajoutee mais jamais lue)
    assert issubclass(IndustrialWorld, Biosphere3D)
    # aucune methode CALLABLE propre au-dela de __init__/step (delegue tout a Biosphere3D)
    own_methods = {k for k, v in IndustrialWorld.__dict__.items()
                   if callable(v) and not k.startswith("__")}
    assert own_methods == {"step"}    # seul override comportemental = step (qui n'ajoute que pollution)
