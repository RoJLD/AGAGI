"""
World 3 : L'Âge Industriel, Métallurgie & Énergie (Étape 3 / Option 2).
Hérite de Biosphere3D avec minage (fer, charbon), hauts fourneaux,
outillage métallique et équilibre thermodynamique / pollution.
Conforme aux 12 Commandements AGIseed (Hyper-configurabilité, Modularité, Vectorisation).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


@dataclass
class IndustrialConfig(WorldConfig):
    """Configuration hyper-paramétrable pour le Monde 3 (Âge Industriel)."""
    iron_nodes_count: int = 6           # Nombre de gisements de fer
    coal_nodes_count: int = 6           # Nombre de gisements de charbon
    enable_blast_furnace: bool = True   # Présence du haut fourneau
    furnace_x: int = 7                  # Position X du haut fourneau
    furnace_y: int = 7                  # Position Y du haut fourneau
    pollution_per_smelt: float = 0.04   # Rejet de suie par cycle de fusion
    plant_depollution_rate: float = 0.005 # Absorption naturelle par la végétation
    smelt_energy_reward: float = 15.0   # Surplus calorique obtenu par forge
    metal_efficiency_boost: float = 2.5  # Multiplicateur d'efficacité des outils métalliques


class IndustrialWorld(Biosphere3D):
    """
    Monde 3 : L'Âge Industriel & Métallurgie.
    Introduit la métallurgie, la machine thermique et l'impact écologique :
    - Extraction de ressources minérales : Minerai de fer (IronOre) et Charbon (Coal).
    - Haut Fourneau (BlastFurnace) : Fusion thermo-chimique IronOre + Coal -> IronIngot.
    - Forge Métallique : Fabrication d'outils durables (IronSpear, IronPickaxe).
    - Jauge de Pollution : Effet de serre et smog industriel régulé par la couverture végétale.
    """
    def __init__(self, config: Optional[IndustrialConfig] = None):
        cfg = config or IndustrialConfig()
        super().__init__(cfg)
        self.indus_config = cfg

        # Métriques industrielles
        self.pollution: float = 0.0
        self.iron_smelted: int = 0
        self.metal_tools_crafted: int = 0
        self.pollution_absorbed: float = 0.0

        # Haut fourneau communautaire
        if cfg.enable_blast_furnace:
            self.furnace = {
                "type": "BlastFurnace",
                "x": cfg.furnace_x,
                "y": cfg.furnace_y,
                "z": 0,
                "temperature": 1200.0,
                "fuel_stored": 10.0,
            }
            self.items.append(self.furnace)
        else:
            self.furnace = None

        # Gisements miniers initiaux
        for _ in range(cfg.iron_nodes_count):
            self.items.append({
                "type": "IronOre",
                "x": int(np.random.randint(0, self.size)),
                "y": int(np.random.randint(0, self.size)),
                "z": 0,
                "weight": 2.0,
            })

        for _ in range(cfg.coal_nodes_count):
            self.items.append({
                "type": "Coal",
                "x": int(np.random.randint(0, self.size)),
                "y": int(np.random.randint(0, self.size)),
                "z": 0,
                "weight": 1.0,
            })

    def step(self):
        # 1. Gestion des interactions au Haut Fourneau
        if self.furnace:
            fx, fy = self.furnace["x"], self.furnace["y"]
            for a in self.agents:
                dist = abs(a["x"] - fx) + abs(a["y"] - fy)
                if dist <= 1:
                    inv = a.get("inventory", [])
                    has_iron = any(it.get("type") == "IronOre" for it in inv)
                    has_coal = any(it.get("type") == "Coal" for it in inv) or (self.furnace["fuel_stored"] >= 1.0)

                    # Réaction métallurgique : Fer + Charbon -> Lingot d'Acier
                    if has_iron and has_coal:
                        # Consommer le minerai
                        a["inventory"] = [it for it in inv if it.get("type") != "IronOre"]
                        if any(it.get("type") == "Coal" for it in inv):
                            a["inventory"] = [it for it in a["inventory"] if it.get("type") != "Coal"]
                        else:
                            self.furnace["fuel_stored"] -= 1.0

                        # Ajouter le lingot d'acier
                        is_master = a.get("role") == "CRAFTER"
                        reward = self.indus_config.smelt_energy_reward * (1.3 if is_master else 1.0)
                        # Un maître-artisan produit moins de suie grâce à une combustion plus propre
                        pollution_delta = self.indus_config.pollution_per_smelt * (0.7 if is_master else 1.0)

                        a["inventory"].append({
                            "type": "IronIngot",
                            "weight": 1.5,
                            "tier": "METAL"
                        })
                        self.iron_smelted += 1
                        a["energy"] = min(self.config.agent.energy_max, a["energy"] + reward)
                        self.pollution += pollution_delta
                        if is_master:
                            a["tribal_craft_bonus"] = True

                    # Crafting d'outil métallique à la forge si lingot en poche
                    ingots = [it for it in a.get("inventory", []) if it.get("type") == "IronIngot"]
                    if len(ingots) >= 1 and not any(it.get("type") == "IronSpear" for it in a["inventory"]):
                        a["inventory"] = [it for it in a["inventory"] if it.get("type") != "IronIngot"]
                        is_master = a.get("role") == "CRAFTER"
                        mult = self.indus_config.metal_efficiency_boost * (1.2 if is_master else 1.0)
                        a["inventory"].append({
                            "type": "IronSpear",
                            "damage_mult": mult,
                            "tier": "METAL"
                        })
                        self.metal_tools_crafted += 1
                        a["spears_crafted"] = a.get("spears_crafted", 0) + 1

        # 2. Dépollution naturelle par la canopée végétale
        num_plants = sum(1 for it in self.items if it.get("type") in ["Plant", "Tree"])
        if num_plants > 0 and self.pollution > 0.0:
            cleaned = min(self.pollution, num_plants * self.indus_config.plant_depollution_rate)
            self.pollution -= cleaned
            self.pollution_absorbed += cleaned

        # 3. Pression écologique de la pollution (Smog toxique si pollution élevée)
        if self.pollution >= 0.7:
            for a in self.agents:
                # Perte de confort et léger drain d'endurance
                a["confort"] = max(0.0, a.get("confort", 50.0) - 0.5)
                if self.pollution >= 1.0:
                    a["energy"] = max(0.0, a["energy"] - 0.1)

        # 4. Cycle de base (Physique & tensorielle)
        super().step()

        # Réapprovisionnement occasionnel de veines minérales si épuisées
        if self.ticks % 50 == 0:
            iron_count = sum(1 for it in self.items if it.get("type") == "IronOre")
            if iron_count < self.indus_config.iron_nodes_count:
                self.items.append({
                    "type": "IronOre",
                    "x": int(np.random.randint(0, self.size)),
                    "y": int(np.random.randint(0, self.size)),
                    "z": 0,
                    "weight": 2.0,
                })
