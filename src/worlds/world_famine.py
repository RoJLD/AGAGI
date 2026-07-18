"""FamineWorld (axe causalité temporelle) — pénurie cyclique + stockage à coût réel.

2e monde GENUINEMENT distinct (spec 2026-06-30-FamineWorld). Hérite du moteur canonique
Biosphere3D (contrat I/O 59/108 partagé) ; la distinctness est dans les mécaniques AJOUTÉES :
régénération de nourriture cyclique (gelée en famine) + cache d'inventaire auto-consommé à la
disette, dont le coût est COMPOSITE = (1) drain de portage réel (carry_weight×0.5/tick, fruit
poids=0.5 → 0.25/tick/fruit) + (2) péremption (valeur décroît de SPOIL_RATE/tick depuis le
stockage). Survivre exige de STOCKER pendant l'abondance -> gratification différée, que stoneage
n'exige ni n'enseigne."""
import os

from src.worlds.world_1_stoneage import Biosphere3D

FOOD_VALUE = 25.0    # énergie rendue par un fruit FRAIS consommé depuis le cache
                     # (à peine > manger direct +20 pour justifier le report sans upgrade gratuit)
SPOIL_RATE = 0.1     # énergie perdue par tick de stockage
MIN_FOOD_VALUE = 5.0  # valeur plancher d'un fruit très vieux (évite valeur négative)
RESERVE_CAP = 150.0  # plafond d'énergie via cache (réserve > energy_max stoneage)
BANK_THRESHOLD = 90.0   # en abondance, energie au-dessus de ce seuil = VRAI surplus (proche du
                        # plafond energie_max, sinon gaspille) -> banquer ne ponctionne PAS l'energie
                        # necessaire (un seuil bas ecremait l'energie vitale -> stockage net-nuisible)
BANK_RATE = 8.0         # max d'energie banque par tick
BANK_EFFICIENCY = 1.0   # depot sans perte : le COUT du stockage est le verrou d'opportunite
                        # (l'energie en reserve n'est retiree qu'en famine quand on starve ; si
                        # l'agent meurt avant, elle est perdue) -> affordance EQUITABLE (storage
                        # net-positif ssi la famine est letale), l'evolution decide honnetement.
WITHDRAW_RATE = 25.0    # max retire de la reserve par tick en famine


class FamineWorld(Biosphere3D):
    def __init__(self, config=None):
        super().__init__(config)
        # Seam de dureté (durcir la famine, EDR-157) : env-vars FAMINE_CYCLE_* pilotent le régime
        # sans toucher main_biosphere (comme HOF_PATH/MAX_ERAS, EDR-155). Défaut = régime EDR-118/155.
        # Régime dur calibré : abondance 30 / famine 120 -> buffer naturel épuisé (~96 ticks), le
        # stockage devient load-bearing (oracle-storer ~223) -> le monde EXIGE une réserve.
        self.cycle_abundance = int(os.environ.get("FAMINE_CYCLE_ABUNDANCE", "60"))  # ticks d'abondance
        self.cycle_famine = int(os.environ.get("FAMINE_CYCLE_FAMINE", "40"))        # ticks de famine
        self.starve_threshold = 25.0   # sous ce niveau d'énergie, auto-consommation du cache
        # Seam d'ablation (probe d'évolvabilité) : à False, l'auto-consommation du cache est
        # désactivée -> les fruits stockés deviennent du poids mort (le coût de portage reste).
        # Défaut True = comportement EDR-118 / distinctness inchangé (non-régressif).
        self.cache_enabled = True
        # FamineWorld hérite la nuit (night_enabled=True par défaut du moteur).
        # On N'ÉCRASE PAS night_enabled : FamineWorld AJOUTE des mécaniques, n'en retire pas
        # (spec §3). Le coût nocturne ×2.5 renforce l'intérêt du stockage préventif.

    def is_famine(self) -> bool:
        period = self.cycle_abundance + self.cycle_famine
        return (self.ticks % period) >= self.cycle_abundance

    def _auto_consume_cache(self, agent):
        """Consomme un Fruit de l'inventaire si l'agent est sous starve_threshold.

        La valeur effective tient compte de la péremption : un fruit stocké depuis longtemps
        vaut moins qu'un fruit frais. Retourne True si un fruit a été consommé.

        Appelé une fois AVANT super().step() (urgence : évite la mort mid-step) et une fois
        APRÈS (agents passés sous le seuil pendant le step). Deux passes conservées car le
        moteur retire les agents morts PENDANT le step ; sans passe pré-step un agent déjà
        sous le seuil serait éliminé avant de pouvoir consommer son cache.
        """
        if agent["energy"] < self.starve_threshold:
            for i, it in enumerate(agent["inventory"]):
                if isinstance(it, dict) and it.get("type") == "Fruit":
                    stored_tick = it.get("_stored_tick", self.ticks)
                    age = self.ticks - stored_tick
                    effective_value = max(MIN_FOOD_VALUE, FOOD_VALUE - SPOIL_RATE * age)
                    agent["inventory"].pop(i)
                    agent["energy"] = min(RESERVE_CAP, agent["energy"] + effective_value)
                    return True
        return False

    def _bank_or_withdraw(self):
        """Banque d'energie (affordance de stockage exploitable en jeu). En ABONDANCE : le surplus
        au-dessus de BANK_THRESHOLD passe en reserve (perte BANK_EFFICIENCY = cout). En FAMINE : on
        retire de la reserve quand l'agent starve. Gate par cache_enabled (ablation)."""
        famine = self.is_famine()
        for a in self.agents:
            if not famine:
                surplus = a["energy"] - BANK_THRESHOLD
                if surplus > 0:
                    amt = min(surplus, BANK_RATE)
                    a["energy"] -= amt
                    a["reserve"] = min(RESERVE_CAP, a.get("reserve", 0.0) + amt * BANK_EFFICIENCY)
            elif a["energy"] < self.starve_threshold and a.get("reserve", 0.0) > 0:
                amt = min(a.get("reserve", 0.0), WITHDRAW_RATE)
                a["reserve"] = a.get("reserve", 0.0) - amt
                a["energy"] += amt

    def step(self):
        self.food_regen_scale = 0.0 if self.is_famine() else 1.0
        # Passe PRÉ-step : auto-consommation d'urgence pour les agents déjà sous le seuil.
        # Cela évite qu'un agent meure pendant super().step() avant d'avoir pu consommer
        # son cache (les agents morts sont retirés de self.agents avant la passe post-step).
        if self.cache_enabled:
            for a in self.agents:
                self._auto_consume_cache(a)
        # Banque d'énergie : avant super().step() pour garantir le retrait même si l'agent meurt
        # en famine. En abondance, les surplus sont stockés avec un coût réel (BANK_EFFICIENCY).
        if self.cache_enabled:
            self._bank_or_withdraw()
        # Masquer les Fruits restants en _FruitReserve : le moteur stoneage consomme
        # automatiquement le 1er Fruit de l'inventaire si energy<80 (ligne 672 stoneage).
        # En FamineWorld, ces fruits sont des réserves de famine (seuil=starve_threshold=25),
        # donc on masque le TYPE pour que le moteur ne les touche pas.
        # NOTE : on NE TOUCHE PAS au poids — le drain de portage (carry_weight×0.5/tick)
        # s'applique NORMALEMENT. C'est le 1er coût du modèle composite de stockage.
        for a in self.agents:
            for it in a["inventory"]:
                if isinstance(it, dict) and it.get("type") == "Fruit":
                    it["type"] = "_FruitReserve"
                    # Enregistrer le tick de stockage si pas encore fait (péremption)
                    if "_stored_tick" not in it:
                        it["_stored_tick"] = self.ticks
        super().step()
        # Démasquer (restaurer type), puis passe POST-step.
        for a in self.agents:
            for it in a["inventory"]:
                if isinstance(it, dict) and it.get("type") == "_FruitReserve":
                    it["type"] = "Fruit"
            if self.cache_enabled:
                self._auto_consume_cache(a)
