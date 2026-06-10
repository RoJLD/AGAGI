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
PREY_REWARD_BASE = 25.0   # recalibrage C : camp de base survivable (Lapin ~25.8)
PREY_REWARD_SCALE = 0.8   # prime de difficulté (Mammouth hp100 -> ~105) : gradient préservé


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


def state_signature(inventory) -> tuple:
    """Signature discrete d'un etat pour la nouveaute count-based : la composition
    d'inventaire (triee). () = vide (ultra-frequent) ; ('rock','stick') = precurseur
    du craft (quasi jamais vu) -> forte nouveaute. Cf. EDR 014 (mur d'exploration)."""
    return tuple(sorted(_item_type(i) for i in inventory))


def novelty_bonus(count: int, scale: float) -> float:
    """Recompense de nouveaute count-based : scale / sqrt(count). Decroit avec la
    frequence -> ne sature pas (contrairement a la surprise du World Model)."""
    return scale / (count ** 0.5) if count > 0 else scale


def anneal(era: int, n_eras: int) -> float:
    """Facteur d'annelage developpemental : 1 au depart, 0 a la fin (clamp >=0).
    Rend le scaffold (cheatcode) fort tot puis l'efface, pour que le comportement
    devienne auto-suffisant via la recompense reelle. Cf. roadmap Vague 0 / Step A."""
    if n_eras <= 0:
        return 0.0
    return max(0.0, 1.0 - float(era) / float(n_eras))


def crit_chance(base: float, era: int, n_eras: int) -> float:
    """Proba de coup CRITIQUE, scaffold annelé (EDR 022, idée « forcer le destin »).

    Élevée tôt -> l'agent armé terrasse *parfois* l'apex (Mammouth) malgré la riposte
    mortelle -> un signal de récompense apparaît pour que l'évolution s'empare du lien
    lance->gros gibier. Décroît vers 0 par monde (via anneal) : la béquille se retire, et
    le comportement doit ensuite tenir sur une vraie stratégie (feu, retraite, coopération).
    Amorcer la découverte par le hasard, puis sevrer — sans *entretenir* un acquis."""
    return base * anneal(era, n_eras)


def attack_damage(weapon_dmg: float, is_crit: bool, crit_mult: float = 3.0) -> float:
    """Dégâts d'une attaque ; un coup critique les multiplie (lance 50 -> 150 = one-shot
    du Mammouth hp100, avant qu'une 2e riposte ne soit létale). Pur et testable (EDR 022)."""
    return weapon_dmg * (crit_mult if is_crit else 1.0)


def approach_reward(d_before: float, d_after: float, eps: float, lam: float) -> float:
    """Recompense de shaping : +eps*lam si l'agent s'est RAPPROCHE du gibier le plus
    proche (distance reduite). Enseigne 'va vers la nourriture' — fix du goulot de
    competence de chasse (EDR 012, constat C). lam = facteur d'annelage (anneal())."""
    return eps * lam if d_after < d_before else 0.0


def try_craft_spear(phys_list, do_rub, craft_level, sharp_min: float = 0.4, haft_min: float = 0.5):
    """Indices (i, j) des 2 items d'inventaire a consommer pour former une lance, ou None.

    AXE CRAFT (EDR 018) : la mecanique se complexifie par paliers, chacun ajoutant UN
    gate (apprenable), au lieu de tous d'un coup (inemergeable, EDR 017) :
      L0 (auto)    : tenir un tranchant + un manche n'importe ou -> lance (AUCUNE action).
      L1 (action)  : idem, mais exige l'action do_rub (le geste).
      L2 (position): exige do_rub ET les ingredients en positions 0 et 1 (recette positionnelle).

    phys = (weight, sharp, edible, friction, flammable).
    """
    if len(phys_list) < 2:
        return None
    if craft_level >= 1 and not do_rub:
        return None
    if craft_level >= 2:
        a, b = phys_list[0], phys_list[1]
        if (a[1] >= sharp_min and b[4] >= haft_min) or (b[1] >= sharp_min and a[4] >= haft_min):
            return (0, 1)
        return None
    # L0 / L1 : un tranchant et un manche, n'importe ou dans l'inventaire.
    sharp_i = next((i for i, p in enumerate(phys_list) if p[1] >= sharp_min), None)
    if sharp_i is None:
        return None
    haft_i = next((j for j, p in enumerate(phys_list) if p[4] >= haft_min and j != sharp_i), None)
    if haft_i is None:
        return None
    return (sharp_i, haft_i)


def is_craft_ingredient(phys, sharp_min: float = 0.4, haft_min: float = 0.5) -> bool:
    """Item utile a une lance : un tranchant (rock) OU un manche (stick/wood).
    Sert au scaffold de collecte (A) — phys = (weight, sharp, edible, friction, flammable)."""
    return phys[1] >= sharp_min or phys[4] >= haft_min


def can_craft_spear(phys_a, phys_b, sharp_min: float = 0.4, haft_min: float = 0.5) -> bool:
    """Deux items forment-ils une lance ? Il faut un tranchant (sharp) ET un manche
    (flammable : stick/wood). Piloté par la physique, pas par des types codés en dur.

    phys = (weight, sharp, edible, friction, flammable).
    """
    sharp = max(phys_a[1], phys_b[1])
    haft = max(phys_a[4], phys_b[4])
    return sharp >= sharp_min and haft >= haft_min
