"""
World 2 : L'Âge Agricole & Révolution Néolithique (Étape 3 / Option B).
Hérite de Biosphere3D avec cycle saisonnier, semailles/croissance/récolte,
greniers communautaires et synergie de coordination par Gigatokens LU.
Conforme aux 12 Commandements AGIseed (Configurable, Modulaire, Vectorisé).
"""
from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any, Optional

from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D


@dataclass
class AgriculturalConfig(WorldConfig):
    """Configuration hyper-paramétrable pour le Monde 2 (Âge Agricole)."""
    season_duration: int = 50          # Ticks par saison
    winter_energy_penalty: float = 0.2  # Pénalité de froid hivernal par tick sans abri/feu
    enable_granary: bool = True         # Présence du grenier communautaire
    granary_x: int = 5                  # Position X du grenier
    granary_y: int = 5                  # Position Y du grenier
    sprout_chance: float = 0.08         # Probabilité de germination au printemps
    growth_rate: float = 0.02           # Vitesse de maturation des plants en été
    lu_agricultural_synergy: float = 1.5  # Multiplicateur de rendement si coordination LU


class AgriculturalWorld(Biosphere3D):
    """
    Monde 2 : L'Âge Agricole.
    Introduit les 4 saisons (Printemps, Été, Automne, Hiver) et la domestication végétale :
    - Printemps : Semailles (Seed -> Planted_Seed -> Plant)
    - Été : Maturation végétative (growth)
    - Automne : Récolte abondante (Fruit) & Stockage en Grenier
    - Hiver : Rigueur thermique (les réserves du grenier et les feux assurent la survie)
    - Coordination LU : Les agents coordonnés par Gigatokens maximisent le rendement.
    """
    def __init__(self, config: Optional[AgriculturalConfig] = None):
        cfg = config or AgriculturalConfig()
        super().__init__(cfg)
        self.agri_config = cfg
        self.season = "spring"
        self.season_ticks = 0
        self.season_duration = cfg.season_duration

        # Métriques agricoles auditables
        self.harvested_crops = 0
        self.granary_reserves = 20.0  # Réserves initiales du grenier
        self.granary_deposits = 0
        self.granary_withdrawals = 0
        self.crops_coordinated_lu = 0

        # Grenier communautaire (structure fixe)
        if cfg.enable_granary:
            self.granary = {
                "type": "Granary",
                "x": cfg.granary_x,
                "y": cfg.granary_y,
                "z": 0,
                "reserves": self.granary_reserves
            }
            self.items.append(self.granary)
        else:
            self.granary = None

        # Semer des graines sauvages initiales
        for _ in range(25):
            self.items.append({
                "type": "Seed",
                "x": int(np.random.randint(0, self.size)),
                "y": int(np.random.randint(0, self.size)),
                "z": 0,
                "weight": 0.1
            })

    def step(self):
        # 1. Gestion du cycle saisonnier
        self.season_ticks += 1
        if self.season_ticks >= self.season_duration:
            self.season_ticks = 0
            seasons = ["spring", "summer", "autumn", "winter"]
            current_idx = seasons.index(self.season)
            self.season = seasons[(current_idx + 1) % 4]

            # Événements de transition saisonnière
            if self.season == "winter":
                # Le gel élimine les plantes non récoltées dans la nature
                self.items = [i for i in self.items if i.get("type") not in ["Plant", "Fruit"] or i.get("type") == "Granary"]
                # Du bois apparaît pour permettre d'allumer des feux protecteurs
                for _ in range(8):
                    self.items.append({
                        "type": "Wood",
                        "x": int(np.random.randint(0, self.size)),
                        "y": int(np.random.randint(0, self.size)),
                        "z": 0,
                        "weight": 1.0
                    })
            elif self.season == "spring":
                # Renaissance printanière : réapparition de graines sauvages
                for _ in range(15):
                    self.items.append({
                        "type": "Seed",
                        "x": int(np.random.randint(0, self.size)),
                        "y": int(np.random.randint(0, self.size)),
                        "z": 0,
                        "weight": 0.1
                    })

        # 2. Dynamique de culture et croissance des plantes
        for item in self.items:
            itype = item.get("type")
            # Germination printanière : Seed / Planted_Seed -> Plant
            if itype in ["Planted_Seed", "Seed"] and self.season == "spring":
                if np.random.rand() < self.agri_config.sprout_chance:
                    item["type"] = "Plant"
                    item["growth"] = 0.0

            # Maturation estivale / automnale : Plant -> Fruit
            elif itype == "Plant" and self.season in ["summer", "autumn"]:
                item["growth"] = item.get("growth", 0.0) + self.agri_config.growth_rate
                if item["growth"] >= 1.0:
                    # Vérifier si des agents à proximité communiquent en LU
                    synergy_mult = 1.0
                    for a in self.agents:
                        dist = abs(a["x"] - item["x"]) + abs(a["y"] - item["y"])
                        if dist <= 3 and a.get("active_lu_mode", False):
                            synergy_mult = self.agri_config.lu_agricultural_synergy
                            self.crops_coordinated_lu += 1
                            break

                    # Production de fruits
                    num_fruits = int(np.round(1 * synergy_mult))
                    for _ in range(num_fruits):
                        self.items.append({
                            "type": "Fruit",
                            "x": min(self.size - 1, max(0, item["x"] + int(np.random.randint(-1, 2)))),
                            "y": min(self.size - 1, max(0, item["y"] + int(np.random.randint(-1, 2)))),
                            "z": item.get("z", 0),
                            "weight": 0.5
                        })
                    self.harvested_crops += num_fruits
                    item["growth"] = 0.0  # Réinitialisation après floraison

        # 3. Thermodynamique et rigueur de l'hiver
        if self.season == "winter":
            for a in self.agents:
                # Protection thermique si l'agent est adjacent à un feu ou au grenier
                near_fire = any(
                    it.get("type") == "Fire" and abs(a["x"] - it["x"]) <= 1 and abs(a["y"] - it["y"]) <= 1
                    for it in self.items
                )
                near_granary = False
                if self.granary:
                    near_granary = (abs(a["x"] - self.granary["x"]) <= 1 and abs(a["y"] - self.granary["y"]) <= 1)

                if near_granary and self.granary["reserves"] > 0:
                    # Ravitaillement automatique au grenier pour compenser le froid
                    ration = min(0.5, self.granary["reserves"])
                    self.granary["reserves"] -= ration
                    a["energy"] = min(self.config.agent.energy_max, a["energy"] + ration * 10.0)
                    self.granary_withdrawals += 1
                elif not near_fire:
                    # Pénalité de froid si isolé
                    a["energy"] = max(0.0, a["energy"] - self.agri_config.winter_energy_penalty)

        # 4. Stockage automatique dans le grenier en automne/été
        if self.granary:
            for a in self.agents:
                if abs(a["x"] - self.granary["x"]) <= 1 and abs(a["y"] - self.granary["y"]) <= 1:
                    # Si l'agent porte des fruits, il peut les déposer au grenier
                    fruits = [it for it in a.get("inventory", []) if it.get("type") == "Fruit"]
                    if fruits:
                        deposited = len(fruits)
                        a["inventory"] = [it for it in a["inventory"] if it.get("type") != "Fruit"]
                        role = a.get("role", "")
                        # Synergie tribale : bonus d'efficience si l'agent est spécialisé (CRAFTER ou HUNTER)
                        role_mult = 1.5 if role in ["CRAFTER", "HUNTER"] else 1.0
                        deposit_val = deposited * 2.0 * role_mult
                        self.granary["reserves"] += deposit_val
                        self.granary_deposits += deposited
                        reward = 5.0 * role_mult
                        a["energy"] = min(self.config.agent.energy_max, a["energy"] + reward)  # Récompense sociale
                        if role:
                            a["tribal_synergy_active"] = True

        # Appel du step physique & écologique de base
        super().step()

        # 5. Interception de l'ensemencement (Graine lâchée au sol -> Planted_Seed)
        for item in self.items:
            if item.get("type") == "Seed" and item.get("_just_dropped", False):
                item["type"] = "Planted_Seed"
                item["_just_dropped"] = False

    def _apply_action(self, agent, action):
        # Action DROP (8) marque la graine comme semée
        if action == 8:
            if len(agent.get("inventory", [])) > 0:
                item_to_drop = agent["inventory"][-1]
                if item_to_drop.get("type") == "Seed":
                    item_to_drop["_just_dropped"] = True
        super()._apply_action(agent, action)
