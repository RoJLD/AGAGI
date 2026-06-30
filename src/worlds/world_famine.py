"""FamineWorld (axe causalité temporelle) — pénurie cyclique + stockage à coût.

2e monde GENUINEMENT distinct (spec 2026-06-30-FamineWorld). Hérite du moteur canonique
Biosphere3D (contrat I/O 59/108 partagé) ; la distinctness est dans les mécaniques AJOUTÉES :
régénération de nourriture cyclique (gelée en famine) + cache d'inventaire auto-consommé à la
disette, dont le coût est le drain de portage existant. Survivre exige de STOCKER pendant
l'abondance -> gratification différée, que stoneage n'exige ni n'enseigne."""
from src.worlds.world_1_stoneage import Biosphere3D


class FamineWorld(Biosphere3D):
    def __init__(self, config=None):
        super().__init__(config)
        self.cycle_abundance = 60      # ticks d'abondance (variable d'expérience)
        self.cycle_famine = 40         # ticks de famine
        self.starve_threshold = 25.0   # sous ce niveau d'énergie, auto-consommation du cache

    def is_famine(self) -> bool:
        period = self.cycle_abundance + self.cycle_famine
        return (self.ticks % period) >= self.cycle_abundance

    def step(self):
        self.food_regen_scale = 0.0 if self.is_famine() else 1.0
        super().step()
