"""FamineWorld (axe causalité temporelle) — pénurie cyclique + stockage à coût.

2e monde GENUINEMENT distinct (spec 2026-06-30-FamineWorld). Hérite du moteur canonique
Biosphere3D (contrat I/O 59/108 partagé) ; la distinctness est dans les mécaniques AJOUTÉES :
régénération de nourriture cyclique (gelée en famine) + cache d'inventaire auto-consommé à la
disette, dont le coût est le drain de portage existant. Survivre exige de STOCKER pendant
l'abondance -> gratification différée, que stoneage n'exige ni n'enseigne."""
from src.worlds.world_1_stoneage import Biosphere3D

FOOD_VALUE = 30.0   # énergie rendue par un fruit consommé depuis le cache
RESERVE_CAP = 150.0  # plafond d'énergie via cache (réserve > energy_max stoneage)


class FamineWorld(Biosphere3D):
    def __init__(self, config=None):
        super().__init__(config)
        self.cycle_abundance = 60      # ticks d'abondance (variable d'expérience)
        self.cycle_famine = 40         # ticks de famine
        self.starve_threshold = 25.0   # sous ce niveau d'énergie, auto-consommation du cache
        # FamineWorld isole la pression de PÉNURIE (pas de nuit) : le défi est la
        # gestion du cache, pas la thermodynamique nocturne (distinctness propre).
        self.night_enabled = False

    def is_famine(self) -> bool:
        period = self.cycle_abundance + self.cycle_famine
        return (self.ticks % period) >= self.cycle_abundance

    def _auto_consume_cache(self, agent):
        """Consomme un Fruit de l'inventaire si l'agent est sous starve_threshold.

        Retourne True si un fruit a été consommé. Appelé deux fois par step : une fois
        avant le moteur (urgence, évite la mort pendant le step) et une fois après
        (agents passés sous le seuil pendant le step).
        """
        if agent["energy"] < self.starve_threshold:
            for i, it in enumerate(agent["inventory"]):
                if isinstance(it, dict) and it.get("type") == "Fruit":
                    agent["inventory"].pop(i)
                    agent["energy"] = min(RESERVE_CAP, agent["energy"] + FOOD_VALUE)
                    return True
        return False

    def step(self):
        self.food_regen_scale = 0.0 if self.is_famine() else 1.0
        # Passe PRÉ-step : auto-consommation d'urgence pour les agents déjà sous le seuil.
        # Cela évite qu'un agent meure pendant super().step() avant d'avoir pu consommer
        # son cache (les agents morts sont retirés de self.agents avant la passe post-step).
        for a in self.agents:
            self._auto_consume_cache(a)
        # Masquer les Fruits restants : le moteur stoneage les consommerait au seuil 80
        # alors qu'en FamineWorld ils sont des réserves de famine (seuil=starve_threshold).
        # Les fruits-réserves sont aussi exemptés du coût de portage (poids mis à 0) :
        # le "sac de stockage" est un équipement, son coût est le stockage lui-même
        # (FOOD_VALUE réduit par rapport à un repas direct), pas le drain de portage.
        for a in self.agents:
            for it in a["inventory"]:
                if isinstance(it, dict) and it.get("type") == "Fruit":
                    it["type"] = "_FruitReserve"
                    it["_orig_weight"] = it.get("weight", 0.5)
                    it["weight"] = 0.0
        super().step()
        # Démasquer (restaurer type et poids), puis passe POST-step.
        for a in self.agents:
            for it in a["inventory"]:
                if isinstance(it, dict) and it.get("type") == "_FruitReserve":
                    it["type"] = "Fruit"
                    it["weight"] = it.pop("_orig_weight", 0.5)
            self._auto_consume_cache(a)
