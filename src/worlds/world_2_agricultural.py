from src.worlds.world_1_stoneage import Biosphere3D
import numpy as np

class AgriculturalWorld(Biosphere3D):
    """
    World 2: L'Âge Agricole.
    Introduit les saisons et l'agriculture.
    Les agents doivent planter des graines (Seed) au printemps pour récolter des fruits (Fruit) en été/automne.
    L'hiver est rude et nécessite des réserves (feu ou inventaire plein).
    """
    def __init__(self, config=None):
        super().__init__(config)
        self.season = "spring"
        self.season_ticks = 0
        self.season_duration = 50  # Reduced for faster testing, was 500
        
        # Override initial spawns to include seeds
        for _ in range(30):
            self.items.append({
                "type": "Seed",
                "x": np.random.randint(0, self.config.size),
                "y": np.random.randint(0, self.config.size),
                "z": 0,
                "weight": 0.1
            })
        
    def step(self):
        # 1. Gestion des saisons
        self.season_ticks += 1
        if self.season_ticks >= self.season_duration:
            self.season_ticks = 0
            seasons = ["spring", "summer", "autumn", "winter"]
            current_idx = seasons.index(self.season)
            self.season = seasons[(current_idx + 1) % 4]
            # Transition effect
            if self.season == "winter":
                # Kill most non-fire plants
                self.items = [i for i in self.items if i.get("type") not in ["Plant", "Fruit"]]
                # Spawn some wood for fire
                for _ in range(10):
                    self.items.append({"type": "Wood", "x": np.random.randint(0, self.config.size), "y": np.random.randint(0, self.config.size), "weight": 1.0})
            elif self.season == "spring":
                # Spawn new wild seeds
                for _ in range(20):
                    self.items.append({"type": "Seed", "x": np.random.randint(0, self.config.size), "y": np.random.randint(0, self.config.size), "weight": 0.1})

        # 2. Gestion de l'environnement (croissance)
        for item in self.items:
            # Seed -> Plant (Spring)
            if item.get("type") == "Planted_Seed" and self.season == "spring":
                if np.random.rand() < 0.05:  # 5% chance per tick to sprout in spring
                    item["type"] = "Plant"
                    item["growth"] = 0.0
            
            # Plant -> Fruit (Summer/Autumn)
            elif item.get("type") == "Plant" and self.season in ["summer", "autumn"]:
                item["growth"] = item.get("growth", 0.0) + 0.01
                if item["growth"] >= 1.0:
                    # Spawn a fruit nearby
                    self.items.append({
                        "type": "Fruit",
                        "x": min(self.config.size - 1, max(0, item["x"] + np.random.randint(-1, 2))),
                        "y": min(self.config.size - 1, max(0, item["y"] + np.random.randint(-1, 2))),
                        "z": item.get("z", 0),
                        "weight": 0.5
                    })
                    item["growth"] = 0.0 # Reset growth after bearing fruit

        # Pression sélective environnementale (Hiver = froid, perte d'énergie)
        if self.season == "winter":
            for a in self.agents:
                # S'il y a un feu à côté, ça va, sinon perte d'énergie continue
                is_near_fire = any(f.get("type") == "Fire" and abs(a["x"] - f["x"]) <= 1 and abs(a["y"] - f["y"]) <= 1 for f in self.items)
                if not is_near_fire:
                    a["energy"] -= 0.2  # Severe winter penalty
                    a["confort"] -= 0.5

        # Appel du comportement de base (StoneAge)
        super().step()

        # 3. Interception des Actions Agricoles
        # Si un agent lâche un objet "Seed", il devient "Planted_Seed"
        for item in self.items:
            if item.get("type") == "Seed" and item.get("_just_dropped", False):
                item["type"] = "Planted_Seed"
                item["_just_dropped"] = False
                
    def _apply_action(self, agent, action):
        # On intercepte DROP pour flagger la graine
        if action == 8: # DROP
            if len(agent["inventory"]) > 0:
                item_to_drop = agent["inventory"][-1]
                if item_to_drop.get("type") == "Seed":
                    item_to_drop["_just_dropped"] = True
        super()._apply_action(agent, action)
