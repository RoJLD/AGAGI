import numpy as np

class GridWorld:
    """
    A pure NumPy 2D GridWorld simulator for Embodied Evolution (RL).
    Commandement 3 : Vectorizable, Fast, No external heavy dependencies (like Gym).
    """
    def __init__(self, size: int = 10, max_steps: int = 50, prey_mode: str = "static"):
        self.size = size
        self.max_steps = max_steps
        self.prey_mode = prey_mode
        self.pheromone_map = np.zeros((size, size), dtype=np.float32)
        self.reset()
        
    def reset(self):
        # Position du joueur
        self.player_x = np.random.randint(0, self.size)
        self.player_y = np.random.randint(0, self.size)
        
        # Position de la nourriture (garantie différente du joueur)
        self._spawn_food()
        
        self.steps = 0
        self.pheromone_map.fill(0.0)
        return self._get_observation()
        
    def _spawn_food(self):
        while True:
            self.food_x = np.random.randint(0, self.size)
            self.food_y = np.random.randint(0, self.size)
            if self.food_x != self.player_x or self.food_y != self.player_y:
                break
                
    def _get_observation(self) -> np.ndarray:
        """
        Renvoie un vecteur d'état : [Dist_Nord, Dist_Sud, Dist_Est, Dist_Ouest, Biais]
        Toutes les valeurs sont normalisées entre 0 et 1.
        """
        # Distances relatives (Capteurs visuels)
        dn = max(0, self.player_y - self.food_y) / self.size
        ds = max(0, self.food_y - self.player_y) / self.size
        de = max(0, self.food_x - self.player_x) / self.size
        dw = max(0, self.player_x - self.food_x) / self.size
        
        # Senseur Olfactif (Stigmergie - Phase 7)
        pheromone = min(1.0, self.pheromone_map[self.player_y, self.player_x])
        
        # Senseur Topologique (Carte Cognitive Absolue)
        abs_x = self.player_x / self.size
        abs_y = self.player_y / self.size
        
        # Biais = 1.0 (Essentiel pour l'activation neuronale comme vu en Phase 1.5)
        return np.array([[dn, ds, de, dw, 1.0, pheromone, abs_x, abs_y]], dtype=np.float32)
        
    def _move_prey(self):
        if self.prey_mode == "static":
            return
            
        # La proie a 50% de chance de bouger à chaque tour pour laisser une chance au prédateur
        if np.random.rand() > 0.5:
            return
            
        action = -1
        if self.prey_mode == "random":
            action = np.random.randint(0, 4)
        elif self.prey_mode == "smart":
            dx = self.player_x - self.food_x
            dy = self.player_y - self.food_y
            if abs(dx) > abs(dy):
                action = 3 if dx > 0 else 2 # Fuite à l'opposé horizontal
            else:
                action = 0 if dy > 0 else 1 # Fuite à l'opposé vertical
        elif self.prey_mode == "semi":
            if np.random.rand() > 0.3:
                action = np.random.randint(0, 4)
            else:
                dx = self.player_x - self.food_x
                dy = self.player_y - self.food_y
                if abs(dx) > abs(dy):
                    action = 3 if dx > 0 else 2
                else:
                    action = 0 if dy > 0 else 1
                    
        # Mouvement effectif de la proie
        if action == 0 and self.food_y > 0: self.food_y -= 1
        elif action == 1 and self.food_y < self.size - 1: self.food_y += 1
        elif action == 2 and self.food_x < self.size - 1: self.food_x += 1
        elif action == 3 and self.food_x > 0: self.food_x -= 1

    def step(self, action: int):
        """
        Actions: 0=Haut, 1=Bas, 2=Droite, 3=Gauche
        """
        self.steps += 1
        reward = -0.01 # Pénalité de temps pour encourager la vitesse
        done = False
        
        # Déposer la phéromone (Stigmergie)
        self.pheromone_map[self.player_y, self.player_x] += 1.0
        
        # Évaporation de l'environnement temporel
        self.pheromone_map *= 0.90
        
        # Déplacement de la proie en premier !
        self._move_prey()
        
        # Mouvement de l'agent
        if action == 0: # Haut
            if self.player_y > 0: self.player_y -= 1
            else: reward -= 0.1 # Hit wall
        elif action == 1: # Bas
            if self.player_y < self.size - 1: self.player_y += 1
            else: reward -= 0.1
        elif action == 2: # Droite
            if self.player_x < self.size - 1: self.player_x += 1
            else: reward -= 0.1
        elif action == 3: # Gauche
            if self.player_x > 0: self.player_x -= 1
            else: reward -= 0.1
            
        # Vérification si la nourriture est mangée
        if self.player_x == self.food_x and self.player_y == self.food_y:
            reward += 1.0
            done = True
            
        if self.steps >= self.max_steps:
            done = True
            
        # Si la nourriture est mangée mais le jeu n'est pas terminé (multi-food future), 
        # on pourrait respawn, mais pour cet exo basique, on arrête l'épisode si mangé.
        
        return self._get_observation(), reward, done

    def render(self):
        """Affiche un rendu ASCII de la grille."""
        grid = [['.' for _ in range(self.size)] for _ in range(self.size)]
        grid[self.food_y][self.food_x] = '@' # Nourriture
        grid[self.player_y][self.player_x] = 'X' # Agent
        
        
        print("\n" + "="*(self.size*2))
        for row in grid:
            print(" ".join(row))
        print("="*(self.size*2))
