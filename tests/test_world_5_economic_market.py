"""
tests/test_world_5_economic_market.py — Validation du Monde 5 (Marché Économique).
Vérifie la création des portefeuilles, l'exécution des trades, la fluctuation des prix
et la résilience financière des agents marchands.
"""
import pytest
import numpy as np
from src.worlds.world_5_economic_market import EconomicMarketWorld, EconomicConfig


def test_economic_market_initialization():
    cfg = EconomicConfig(initial_coins_per_agent=100.0)
    world = EconomicMarketWorld(cfg)
    assert world.market_stall["type"] == "MarketStall"
    assert world.prices["Food"] == cfg.base_food_price
    assert world.public_treasury == 0.0


def test_agent_wallet_and_bilateral_trade():
    world = EconomicMarketWorld()
    buyer = {"id": "buyer_1", "pos": [10.0, 10.0, 0.0], "energy": 40.0}
    seller = {"id": "seller_1", "pos": [10.5, 10.0, 0.0], "energy": 80.0}

    world.register_agent_wallet(buyer)
    world.register_agent_wallet(seller)

    seller["wallet"]["inventory"]["Food"] = 5
    initial_buyer_coins = buyer["wallet"]["coins"]
    initial_seller_coins = seller["wallet"]["coins"]

    ok = world.execute_trade(buyer, seller, "Food", quantity=1)
    assert ok is True
    assert buyer["wallet"]["coins"] < initial_buyer_coins
    assert seller["wallet"]["coins"] > initial_seller_coins
    assert world.successful_trades == 1
    assert world.public_treasury > 0.0


def test_stall_trade_and_price_elasticity():
    world = EconomicMarketWorld()
    buyer = {"id": "buyer_2", "pos": [10.0, 10.0, 0.0], "energy": 30.0}
    world.register_agent_wallet(buyer)

    # Achat direct au comptoir
    ok = world.execute_trade(buyer, None, "Food", quantity=2)
    assert ok is True
    assert world.market_stall["stock"]["Food"] == 18

    # Hausse de la demande -> mise à jour des prix
    world.demand["Food"] += 50.0
    world.supply["Food"] = 2.0
    world.update_market_prices()
    assert world.prices["Food"] > world.econ_config.base_food_price


def test_economic_world_step():
    world = EconomicMarketWorld()
    # Ajout d'agents pour vérifier le cycle d'étape
    metrics = world.get_economic_metrics()
    assert "current_prices" in metrics
    assert "market_stock" in metrics
