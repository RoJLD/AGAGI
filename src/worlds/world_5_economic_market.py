"""
World 5 : Le Marché Économique Décentralisé, Monnaie & Négociation Multi-Agents.
Hérite de Biosphere3D avec division du travail, carnet d'ordres décentralisé,
monnaie d'échange (Coins), contrats d'achat/vente et fixation dynamique des prix.
Conforme aux 12 Commandements AGIseed (Flexible, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


@dataclass
class EconomicConfig(WorldConfig):
    """Configuration hyper-paramétrable pour le Monde 5 (Marché Économique)."""
    initial_coins_per_agent: float = 50.0   # Solde initial par agent
    market_stall_x: int = 10                # Coordonnée X du comptoir central
    market_stall_y: int = 10                # Coordonnée Y du comptoir central
    base_food_price: float = 5.0            # Prix plancher d'une unité de nourriture
    base_tool_price: float = 12.0           # Prix plancher d'un outil
    base_ore_price: float = 8.0             # Prix plancher d'un minerai
    elasticity: float = 0.5                 # Élasticité-prix (sensibilité à l'offre/demande)
    transaction_tax_rate: float = 0.05      # Taxe sur transactions reversée au bien commun
    contract_penalty: float = 10.0          # Pénalité de réputation/argent en cas de rupture de contrat
    trade_distance_threshold: float = 3.5   # Distance maximale pour négocier


class EconomicMarketWorld(Biosphere3D):
    """
    Monde 5 : Le Marché Économique.
    Introduit la division du travail, la monnaie fiduciaire et le commerce structuré :
    - Échange bilatéral ou via Comptoir : Achat / Vente de Food, Tool, Ore contre Coins.
    - Fluctuation dynamique des prix : Loi de l'offre et de la demande avec élasticité.
    - Contrats à terme (Futures/Engagements) : Livraisons programmées de biens contre rétribution.
    - Réputation marchande : Détection et pénalisation des défections de livraison.
    """
    def __init__(self, config: Optional[EconomicConfig] = None):
        cfg = config or EconomicConfig()
        super().__init__(cfg)
        self.econ_config = cfg

        # Carnet de marché
        self.prices: Dict[str, float] = {
            "Food": cfg.base_food_price,
            "Tool": cfg.base_tool_price,
            "Ore": cfg.base_ore_price,
        }
        self.supply: Dict[str, float] = {"Food": 10.0, "Tool": 5.0, "Ore": 8.0}
        self.demand: Dict[str, float] = {"Food": 10.0, "Tool": 5.0, "Ore": 8.0}

        # Trésor public & Métriques
        self.public_treasury: float = 0.0
        self.successful_trades: int = 0
        self.failed_contracts: int = 0
        self.total_volume_traded: float = 0.0

        # Comptoir central
        self.market_stall = {
            "type": "MarketStall",
            "x": cfg.market_stall_x,
            "y": cfg.market_stall_y,
            "z": 0,
            "stock": {"Food": 20, "Tool": 10, "Ore": 15},
        }
        self.items.append(self.market_stall)

    def register_agent_wallet(self, agent_dict: Dict) -> None:
        """Initialise le portefeuille économique d'un agent s'il est absent."""
        if "wallet" not in agent_dict:
            agent_dict["wallet"] = {
                "coins": float(self.econ_config.initial_coins_per_agent),
                "reputation": 1.0,
                "inventory": {"Food": 2, "Tool": 1, "Ore": 0},
            }

    def update_market_prices(self) -> None:
        """
        Ajuste les prix des commodités en fonction de l'offre et de la demande.
        P_t = P_base * (1 + elasticity * (Demand - Supply) / (Supply + 1.0))
        """
        for item in ["Food", "Tool", "Ore"]:
            base = getattr(self.econ_config, f"base_{item.lower()}_price")
            s = max(0.1, self.supply[item])
            d = max(0.1, self.demand[item])
            ratio = (d - s) / s
            new_price = base * (1.0 + self.econ_config.elasticity * ratio)
            self.prices[item] = float(np.clip(new_price, base * 0.2, base * 5.0))

    def execute_trade(
        self,
        buyer: Dict,
        seller: Optional[Dict],
        commodity: str,
        quantity: int = 1
    ) -> bool:
        """
        Exécute une transaction d'achat-vente au prix du marché.
        Si seller est None, l'achat s'effectue auprès du comptoir central (MarketStall).
        """
        self.register_agent_wallet(buyer)
        if seller is not None:
            self.register_agent_wallet(seller)

        if commodity not in self.prices:
            return False

        unit_price = self.prices[commodity]
        total_price = unit_price * quantity
        tax = total_price * self.econ_config.transaction_tax_rate
        net_price = total_price + tax

        # Vérification des fonds de l'acheteur
        if buyer["wallet"]["coins"] < net_price:
            self.demand[commodity] += quantity * 0.2  # Signal de demande insatisfaite
            return False

        # Vérification des stocks du vendeur
        if seller is not None:
            if seller["wallet"]["inventory"].get(commodity, 0) < quantity:
                seller["wallet"]["reputation"] = max(0.0, seller["wallet"]["reputation"] - 0.1)
                self.failed_contracts += 1
                return False
            seller["wallet"]["inventory"][commodity] -= quantity
            seller["wallet"]["coins"] += total_price
            seller["wallet"]["reputation"] = min(2.0, seller["wallet"]["reputation"] + 0.05)
        else:
            if self.market_stall["stock"].get(commodity, 0) < quantity:
                return False
            self.market_stall["stock"][commodity] -= quantity

        # Débit acheteur & Crédit acheteur
        buyer["wallet"]["coins"] -= net_price
        buyer["wallet"]["inventory"][commodity] = buyer["wallet"]["inventory"].get(commodity, 0) + quantity
        self.public_treasury += tax

        # Mise à jour des flux
        self.demand[commodity] += quantity
        self.supply[commodity] = max(0.1, self.supply[commodity] - quantity * 0.5)
        self.successful_trades += 1
        self.total_volume_traded += total_price

        # Conversion directe si nourriture : regain énergétique
        if commodity == "Food" and buyer["energy"] < 80.0:
            buyer["energy"] = min(100.0, buyer["energy"] + 15.0 * quantity)
            buyer["wallet"]["inventory"]["Food"] -= quantity

        return True

    def step(self):
        """Avance la simulation d'un tick avec interactions économiques."""
        super().step()

        # Enregistrer les portefeuilles pour tous les agents vivants
        for a in self.agents:
            self.register_agent_wallet(a)

        # Simulation d'échanges économiques entre agents proches
        n_agents = len(self.agents)
        for i in range(n_agents):
            a_i = self.agents[i]
            # Si l'agent a faim et a des coins, il achète de la nourriture
            if a_i["energy"] < 50.0 and a_i["wallet"]["coins"] >= self.prices["Food"]:
                # Chercher un vendeur proche ou acheter au comptoir
                bought = False
                for j in range(n_agents):
                    if i != j:
                        a_j = self.agents[j]
                        dist = np.linalg.norm(np.array(a_i["pos"][:2]) - np.array(a_j["pos"][:2]))
                        if dist <= self.econ_config.trade_distance_threshold:
                            if a_j["wallet"]["inventory"].get("Food", 0) > 0:
                                bought = self.execute_trade(a_i, a_j, "Food", 1)
                                if bought:
                                    break
                if not bought:
                    # Achat au comptoir
                    dist_stall = np.linalg.norm(
                        np.array(a_i["pos"][:2]) - np.array([self.econ_config.market_stall_x, self.econ_config.market_stall_y])
                    )
                    if dist_stall <= self.econ_config.trade_distance_threshold * 2.0:
                        self.execute_trade(a_i, None, "Food", 1)

            # Si l'agent est bien nourri et a des minerais ou outils en excès, il vend
            elif a_i["energy"] > 70.0 and a_i["wallet"]["inventory"].get("Ore", 0) > 2:
                self.supply["Ore"] += 1.0
                a_i["wallet"]["inventory"]["Ore"] -= 1
                a_i["wallet"]["coins"] += self.prices["Ore"] * 0.95
                self.market_stall["stock"]["Ore"] = self.market_stall["stock"].get("Ore", 0) + 1
                self.successful_trades += 1

        # Réajustement périodique des prix du marché
        if self.age % 10 == 0:
            self.update_market_prices()

    def get_economic_metrics(self) -> Dict[str, Any]:
        """Retourne les métriques économiques consolidées."""
        return {
            "successful_trades": self.successful_trades,
            "failed_contracts": self.failed_contracts,
            "total_volume_traded": self.total_volume_traded,
            "public_treasury": self.public_treasury,
            "current_prices": dict(self.prices),
            "market_stock": dict(self.market_stall["stock"]),
        }
