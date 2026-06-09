"""
Économie de l'Âge de Pierre — Monde exigeant (roadmap Vague 0 / Step 2 ; EDR 010 levier 2).

Fonctions PURES qui rendent l'intelligence *instrumentale* au lieu de subventionnée :

  - prey_reward  : la récompense de chasse ∝ difficulté de la proie. Le Lapin
                   sustente à peine ; le Mammouth est le vrai gain.
  - weapon_damage: les dégâts dépendent d'un outil crafté. Sans lance, le gros
                   gibier (qui riposte) est injouable ; avec, il tombe.
  - can_craft_spear : un tranchant + un manche -> Lance (physique-driven).

C'est la première chaîne moyens→fins du monde : nourriture facile rare → gros
gibier nécessaire → mais il faut une lance → donc planifier, mémoriser, crafter.

Convention du tuple de physique d'un item : (weight, sharp, edible, friction, flammable).
"""

# Constantes = variables d'expérience (Commandement 15) : à calibrer/mesurer.
BASE_DAMAGE = 10.0
SPEAR_DAMAGE = 50.0
PREY_REWARD_BASE = 9.0    # subsistance d'un petit gibier (Lapin ~9.8)
PREY_REWARD_SCALE = 0.8   # prime de difficulté (Mammouth hp100 -> ~89)


def prey_reward(max_hp: float, base: float = PREY_REWARD_BASE, scale: float = PREY_REWARD_SCALE) -> float:
    """Récompense énergétique d'une mise à mort, proportionnelle à la difficulté (HP max)."""
    return float(base + scale * float(max_hp))


def _item_type(item) -> str:
    return item.get("type", "") if isinstance(item, dict) else str(item)


def has_spear(inventory) -> bool:
    """L'agent tient-il une lance ?"""
    return any(_item_type(it) == "Spear" for it in inventory)


def weapon_damage(holds_spear: bool, base: float = BASE_DAMAGE, spear: float = SPEAR_DAMAGE) -> float:
    """Dégâts d'une attaque : faibles à mains nues, élevés avec une lance."""
    return spear if holds_spear else base


def can_craft_spear(phys_a, phys_b, sharp_min: float = 0.4, haft_min: float = 0.5) -> bool:
    """Deux items forment-ils une lance ? Il faut un tranchant (sharp) ET un manche
    (flammable : stick/wood). Piloté par la physique, pas par des types codés en dur.

    phys = (weight, sharp, edible, friction, flammable).
    """
    sharp = max(phys_a[1], phys_b[1])
    haft = max(phys_a[4], phys_b[4])
    return sharp >= sharp_min and haft >= haft_min
