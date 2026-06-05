from src.worlds.world_1_stoneage import Biosphere3D

class IndustrialWorld(Biosphere3D):
    """
    World 3: L'Âge Industriel.
    Introduit des ressources statiques nécessitant de la coopération et des usines.
    (Clone de Biosphere3D pour l'instant avec quelques paramètres ajustés).
    """
    def __init__(self, size=50, num_agents=50, use_3d=True):
        super().__init__(size, num_agents, use_3d)
        self.pollution = 0.0
        
    def step(self):
        # Override step or just call super
        super().step()
        # Augmentation lente de la pollution
        if self.ticks % 10 == 0:
            self.pollution += 0.01
