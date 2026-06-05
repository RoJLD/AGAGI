import numpy as np

class SpaceWorld:
    """
    A pure NumPy 3D Volumetric Simulator.
    Actions: 0=Haut(Y-), 1=Bas(Y+), 2=Droite(X+), 3=Gauche(X-), 4=Monter(Z+), 5=Descendre(Z-)
    """
    def __init__(self, size: int = 10, max_steps: int = 50, prey_mode: str = "semi", num_altars: int = 3):
        self.size = size
        self.max_steps = max_steps
        self.prey_mode = prey_mode
        self.num_altars = num_altars
        self.pheromone_map = np.zeros((size, size, size), dtype=np.float32)
        self.reset()
        
    def reset(self):
        self.player_x = np.random.randint(0, self.size)
        self.player_y = np.random.randint(0, self.size)
        self.player_z = np.random.randint(0, self.size)
        
        self._spawn_food()
        
        self.altars = []
        for _ in range(self.num_altars):
            self.altars.append({
                "x": np.random.randint(0, self.size),
                "y": np.random.randint(0, self.size),
                "z": np.random.randint(0, self.size),
                "bit_a": np.random.choice([-1.0, 1.0]),
                "bit_b": np.random.choice([-1.0, 1.0])
            })
            
        self.steps = 0
        self.prey_paralyzed = 0
        self.pheromone_map.fill(0.0)
        return self._get_observation()
        
    def _spawn_food(self):
        while True:
            self.food_x = np.random.randint(0, self.size)
            self.food_y = np.random.randint(0, self.size)
            self.food_z = np.random.randint(0, self.size)
            if not (self.food_x == self.player_x and self.food_y == self.player_y and self.food_z == self.player_z):
                break

    def _get_observation(self) -> np.ndarray:
        """
        Renvoie un vecteur d'état : [dn, ds, de, dw, dup, ddown, Biais, Phero, AbsX, AbsY, AbsZ, AltarActive, BitA, BitB]
        Total: 14 Entrées
        """
        # Distances relatives
        dn = max(0, self.player_y - self.food_y) / self.size
        ds = max(0, self.food_y - self.player_y) / self.size
        de = max(0, self.food_x - self.player_x) / self.size
        dw = max(0, self.player_x - self.food_x) / self.size
        dup = max(0, self.food_z - self.player_z) / self.size
        ddown = max(0, self.player_z - self.food_z) / self.size
        
        # Senseur Olfactif 3D
        pheromone = min(1.0, self.pheromone_map[self.player_z, self.player_y, self.player_x])
        
        # Senseur Topologique 3D
        abs_x = self.player_x / self.size
        abs_y = self.player_y / self.size
        abs_z = self.player_z / self.size
        
        # Senseurs Cognitifs (Autels Logiques)
        altar_active = 0.0
        bit_a = 0.0
        bit_b = 0.0
        
        for altar in self.altars:
            if altar["x"] == self.player_x and altar["y"] == self.player_y and altar["z"] == self.player_z:
                altar_active = 1.0
                bit_a = altar["bit_a"]
                bit_b = altar["bit_b"]
                break
        
        return np.array([[dn, ds, de, dw, dup, ddown, 1.0, pheromone, abs_x, abs_y, abs_z, altar_active, bit_a, bit_b]], dtype=np.float32)
        
    def _move_prey(self):
        if self.prey_paralyzed > 0:
            self.prey_paralyzed -= 1
            return
            
        if self.prey_mode == "static":
            return
            
        if np.random.rand() > 0.5:
            return
            
        action = -1
        if self.prey_mode == "semi":
            if np.random.rand() > 0.3:
                action = np.random.randint(0, 6)
            else:
                dx = self.player_x - self.food_x
                dy = self.player_y - self.food_y
                dz = self.player_z - self.food_z
                
                # Fuite sur l'axe le plus menaçant
                adx, ady, adz = abs(dx), abs(dy), abs(dz)
                if adx >= ady and adx >= adz:
                    action = 3 if dx > 0 else 2
                elif ady >= adx and ady >= adz:
                    action = 0 if dy > 0 else 1
                else:
                    action = 5 if dz > 0 else 4
                    
        # Mouvement effectif de la proie
        if action == 0 and self.food_y > 0: self.food_y -= 1
        elif action == 1 and self.food_y < self.size - 1: self.food_y += 1
        elif action == 2 and self.food_x < self.size - 1: self.food_x += 1
        elif action == 3 and self.food_x > 0: self.food_x -= 1
        elif action == 4 and self.food_z < self.size - 1: self.food_z += 1
        elif action == 5 and self.food_z > 0: self.food_z -= 1

    def step(self, action: int, cognitive_out: float = 0.0):
        self.steps += 1
        reward = -0.01 
        done = False
        
        self.pheromone_map[self.player_z, self.player_y, self.player_x] += 1.0
        self.pheromone_map *= 0.90
        
        # Logique des Autels (XOR)
        for altar in self.altars:
            if altar["x"] == self.player_x and altar["y"] == self.player_y and altar["z"] == self.player_z:
                expected_sign = -1.0 if altar["bit_a"] == altar["bit_b"] else 1.0
                if cognitive_out * expected_sign > 0: # Succès cognitif !
                    reward += 5.0
                    self.prey_paralyzed = 3
                    # L'autel s'épuise et réapparait ailleurs
                    altar["x"] = np.random.randint(0, self.size)
                    altar["y"] = np.random.randint(0, self.size)
                    altar["z"] = np.random.randint(0, self.size)
                    altar["bit_a"] = np.random.choice([-1.0, 1.0])
                    altar["bit_b"] = np.random.choice([-1.0, 1.0])
                break
        
        self._move_prey()
        
        if action == 0 and self.player_y > 0: self.player_y -= 1
        elif action == 0: reward -= 0.1
        
        if action == 1 and self.player_y < self.size - 1: self.player_y += 1
        elif action == 1: reward -= 0.1
        
        if action == 2 and self.player_x < self.size - 1: self.player_x += 1
        elif action == 2: reward -= 0.1
        
        if action == 3 and self.player_x > 0: self.player_x -= 1
        elif action == 3: reward -= 0.1
        
        if action == 4 and self.player_z < self.size - 1: self.player_z += 1
        elif action == 4: reward -= 0.1
        
        if action == 5 and self.player_z > 0: self.player_z -= 1
        elif action == 5: reward -= 0.1
            
        if self.player_x == self.food_x and self.player_y == self.food_y and self.player_z == self.food_z:
            reward += 1.0
            done = True
            
        if self.steps >= self.max_steps:
            done = True
            
        return self._get_observation(), reward, done

    def render(self):
        print(f"--- 3D SPACE WORLD | Z-Level: {self.player_z} ---")
        if self.food_z > self.player_z:
            print("[^ Cible au-dessus ^]")
        elif self.food_z < self.player_z:
            print("[v Cible en-dessous v]")
        else:
            print("[= Cible sur le meme plan =]")
            
        print("=" * (self.size * 2))
        for y in range(self.size):
            row = ""
            for x in range(self.size):
                if x == self.player_x and y == self.player_y:
                    row += "X "
                elif x == self.food_x and y == self.food_y and self.food_z == self.player_z:
                    row += "@ "
                else:
                    is_altar = False
                    for altar in self.altars:
                        if altar["x"] == x and altar["y"] == y and altar["z"] == self.player_z:
                            is_altar = True
                            break
                    if is_altar:
                        row += "A "
                    else:
                        row += ". "
            print(row)
        print("=" * (self.size * 2))
